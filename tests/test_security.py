"""Regression tests for the security patches (pentest findings).

Four findings, four guards:

1. Access-code compare must go through hmac.compare_digest and reject
   non-string input instead of crashing or coercing.
2. Wrong access codes must lock out per client address after
   AUTH_FAIL_MAX failures inside AUTH_FAIL_WINDOW (the general rate
   limiter does not see these requests), and a right code must clear
   the address so one mistype does not count forever.
3. GET /api/config must never echo the stored access_code back.
4. POST /api/shutdown must refuse cross-site requests (foreign Origin
   or Sec-Fetch-Site: cross-site) before doing anything, while plain
   clients that send neither header (curl, the Flask test client,
   pywebview) still work.

Isolation: routes.AUTH_FAIL is module-level and shared by every test
in the process, so it is cleared before and after every test here.
CONFIG_DIR/CONFIG_FILE are repointed at a temp directory per test.

Run with:  PYTHONPATH=src python -m unittest discover -s tests -t .
"""

import json
import os
import pathlib
import sys
import tempfile
import time
import unittest
from unittest import mock

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = str(REPO_ROOT / "src")
if SRC not in sys.path:
    sys.path.append(SRC)

from accessible_ide import create_app, routes  # noqa: E402


class SecurityTestCase(unittest.TestCase):
    """Base: private config file, empty access code, clean AUTH_FAIL."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        tmp_path = pathlib.Path(self._tmp.name)

        self._saved = {
            "CONFIG_DIR": routes.CONFIG_DIR,
            "CONFIG_FILE": routes.CONFIG_FILE,
            "ACCESS_CODE": routes.ACCESS_CODE,
        }
        routes.CONFIG_DIR = tmp_path
        routes.CONFIG_FILE = tmp_path / "config.json"
        routes.ACCESS_CODE = ""

        routes.AUTH_FAIL.clear()
        self.addCleanup(routes.AUTH_FAIL.clear)
        self.addCleanup(self._restore)

        app = create_app()
        app.config["TESTING"] = True
        self.client = app.test_client()

    def _restore(self):
        for key, value in self._saved.items():
            setattr(routes, key, value)
        self._tmp.cleanup()


# -- finding 1: timing-safe compare -----------------------------------


class AccessCodeCompareTests(SecurityTestCase):
    def test_a_right_code_passes(self):
        routes.ACCESS_CODE = "letmein"
        with self.app_context():
            self.assertTrue(routes.access_code_ok({"access_code": "letmein"}))

    def test_a_wrong_code_fails(self):
        routes.ACCESS_CODE = "letmein"
        with self.app_context():
            self.assertFalse(
                routes.access_code_ok({"access_code": "letmein2"}))

    def test_a_non_string_code_is_refused_not_crashed(self):
        # Before the fix a list/dict/int reaching the compare would raise
        # (no .encode) or coerce; now anything non-str is just wrong.
        routes.ACCESS_CODE = "letmein"
        for given in (12345, ["letmein"], {"code": "letmein"}, None, True):
            with self.app_context():
                self.assertFalse(routes.access_code_ok({"access_code": given}))

    def test_a_missing_code_is_refused(self):
        routes.ACCESS_CODE = "letmein"
        with self.app_context():
            self.assertFalse(routes.access_code_ok({}))

    def test_no_configured_code_means_open(self):
        routes.ACCESS_CODE = ""
        with self.app_context():
            self.assertTrue(routes.access_code_ok({}))

    def test_compare_outside_request_context_still_works(self):
        # Unit callers (and tests) call this without a request; the
        # lockout half is skipped but the compare itself still answers.
        routes.ACCESS_CODE = "letmein"
        self.assertTrue(routes.access_code_ok({"access_code": "letmein"}))
        self.assertFalse(routes.access_code_ok({"access_code": "nope"}))

    def app_context(self):
        app = create_app()
        app.config["TESTING"] = True
        return app.test_request_context("/", base_url="http://localhost")


# -- finding 2: brute-force lockout -----------------------------------


class AuthLockoutTests(SecurityTestCase):
    def post_code(self, code):
        """Hit a guarded endpoint with the given access code."""
        routes.ACCESS_CODE = "letmein"
        return self.client.post("/api/config", json={"access_code": code})

    def test_the_limiter_counts_failures_for_the_address(self):
        for _ in range(routes.AUTH_FAIL_MAX):
            self.post_code("wrong")
        self.assertTrue(routes.AUTH_FAIL.get("127.0.0.1"))

    def test_enough_failures_lock_even_the_right_code(self):
        for _ in range(routes.AUTH_FAIL_MAX):
            self.post_code("wrong")
        response = self.post_code("letmein")
        # The guarded endpoint answers 403 (error.access_required), not
        # 401, when the code check fails.
        self.assertEqual(response.status_code, 403)

    def test_a_right_code_clears_the_failures(self):
        self.post_code("wrong")
        self.assertTrue(routes.AUTH_FAIL.get("127.0.0.1"))
        response = self.post_code("letmein")
        self.assertNotEqual(response.status_code, 401)
        self.assertFalse(routes.AUTH_FAIL.get("127.0.0.1"))

    def test_other_addresses_are_not_affected(self):
        for _ in range(routes.AUTH_FAIL_MAX):
            self.post_code("wrong")
        other = self.client.post(
            "/api/config",
            json={"access_code": "letmein"},
            headers={"X-Forwarded-For": "203.0.113.9"},
        )
        self.assertNotEqual(other.status_code, 401)

    def test_failures_older_than_the_window_do_not_count(self):
        # Fill right up to the lockout threshold, but with timestamps
        # older than the window: they must age out, so the right code
        # is still accepted instead of locked out.
        routes.ACCESS_CODE = "letmein"
        stale = time.time() - routes.AUTH_FAIL_WINDOW - 1
        routes.AUTH_FAIL["127.0.0.1"] = [stale] * routes.AUTH_FAIL_MAX
        response = self.post_code("letmein")
        self.assertNotEqual(response.status_code, 401)
        self.assertFalse(routes.AUTH_FAIL.get("127.0.0.1"))


# -- finding 3: config must not echo the access code -------------------


class ConfigLeakTests(SecurityTestCase):
    def test_get_config_never_returns_the_access_code(self):
        routes.ACCESS_CODE = "letmein"
        # Also plant it in the on-disk file, in case a future refactor
        # stops stripping it at the endpoint and starts dumping the file.
        routes.CONFIG_FILE.write_text(
            json.dumps({"access_code": "letmein", "font_size": 18}),
            encoding="utf-8",
        )
        response = self.client.get("/api/config")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertNotIn("access_code", data)
        self.assertNotIn("letmein", response.get_data(as_text=True))

    def test_get_config_without_a_code_still_works(self):
        response = self.client.get("/api/config")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("access_code", response.get_json())


# -- finding 4: shutdown CSRF -----------------------------------------


class ShutdownCsrfTests(unittest.TestCase):
    """Cross-site pages must not be able to quit the reader's app."""

    def post(self, headers=None, env=None):
        clean = {k: v for k, v in os.environ.items()
                 if k not in ("WEB", "SANDBOX", "RENDER", "RAILWAY",
                              "SERVER_SOFTWARE")}
        clean.update(env or {})
        with mock.patch.dict(os.environ, clean, clear=True):
            app = create_app()
            app.config["TESTING"] = True
            with mock.patch.object(routes.os, "_exit") as exit_mock:
                with app.test_client() as client:
                    response = client.post(
                        "/api/shutdown", headers=headers or {})
                # An accepted shutdown spawns a daemon thread that calls
                # os._exit(0) after ~0.3s. The patch must stay active
                # until that thread has fired, or the real os._exit
                # kills the test process once the patch unwinds. A 200
                # means the thread was started, so wait for the mock.
                if response.status_code == 200:
                    deadline = time.time() + 2.0
                    while not exit_mock.called and time.time() < deadline:
                        time.sleep(0.05)
                return response, exit_mock

    def test_the_desktop_still_may_quit(self):
        response, exit_mock = self.post(headers={"Host": "localhost"})
        self.assertEqual(response.status_code, 200)
        exit_mock.assert_called_once()

    def test_a_same_origin_page_may_quit(self):
        response, exit_mock = self.post(headers={
            "Host": "localhost",
            "Origin": "http://localhost",
        })
        self.assertEqual(response.status_code, 200)
        exit_mock.assert_called_once()

    def test_a_foreign_origin_is_refused(self):
        response, exit_mock = self.post(headers={
            "Host": "localhost",
            "Origin": "http://evil.example",
        })
        self.assertEqual(response.status_code, 403)
        exit_mock.assert_not_called()

    def test_a_cross_site_fetch_is_refused(self):
        response, exit_mock = self.post(headers={
            "Host": "localhost",
            "Sec-Fetch-Site": "cross-site",
        })
        self.assertEqual(response.status_code, 403)
        exit_mock.assert_not_called()

    def test_a_same_site_fetch_is_allowed(self):
        response, exit_mock = self.post(headers={
            "Host": "localhost",
            "Sec-Fetch-Site": "same-origin",
        })
        self.assertEqual(response.status_code, 200)
        exit_mock.assert_called_once()

    def test_plain_clients_without_the_headers_still_work(self):
        # curl, scripts and pywebview send neither Origin nor
        # Sec-Fetch-Site; refusing those would break the desktop app.
        response, exit_mock = self.post(headers={"Host": "localhost"})
        self.assertEqual(response.status_code, 200)
        exit_mock.assert_called_once()

    def test_the_blocked_reply_is_translated(self):
        response, _ = self.post(headers={
            "Host": "localhost",
            "Origin": "http://evil.example",
        })
        body = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 403)
        self.assertIn("blocked", body.lower())


if __name__ == "__main__":
    unittest.main()
