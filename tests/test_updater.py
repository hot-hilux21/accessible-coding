"""Tests for the update check.

The two things that could genuinely hurt a reader are both tested here: a
comparison that offers a downgrade, and a manifest that points the download
somewhere it should not. Everything that touches the network is faked, so
these run offline and in a second.
"""

import json
import os
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from accessible_ide import updater  # noqa: E402

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]


def load_app_module():
    """The real app.py, so the exit hand-over is tested as shipped.

    Loaded rather than reimplemented. A test that copied the function would
    still pass after the real one was broken, which is the one thing a test
    of this must never do.
    """
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))
    import app
    return app


class VersionOrderingTests(unittest.TestCase):
    def test_ordinary_numbers_compare_as_expected(self):
        self.assertTrue(updater.is_newer("0.2.3", "0.2.2"))
        self.assertTrue(updater.is_newer("0.3.0", "0.2.9"))
        self.assertTrue(updater.is_newer("1.0.0", "0.9.9"))
        self.assertFalse(updater.is_newer("0.2.2", "0.2.2"))
        self.assertFalse(updater.is_newer("0.2.1", "0.2.2"))

    def test_missing_parts_are_treated_as_zero(self):
        # A tag written "0.3" must not look older than the released "0.2.9".
        self.assertTrue(updater.is_newer("0.3", "0.2.9"))
        self.assertTrue(updater.is_newer("1", "0.9.9"))
        self.assertFalse(updater.is_newer("0.2", "0.2.0"))

    def test_a_stable_build_is_newer_than_its_own_pre_releases(self):
        self.assertTrue(updater.is_newer("0.3.0", "0.3.0-dev.12"))
        self.assertTrue(updater.is_newer("0.3.0", "0.3.0-beta"))
        self.assertFalse(updater.is_newer("0.3.0-dev.12", "0.3.0"))

    def test_development_builds_follow_the_run_number(self):
        # This is what makes the ever-increasing CI run number a usable
        # ordering: a later build of the same version is a newer build.
        self.assertTrue(updater.is_newer("0.3.0-dev.121", "0.3.0-dev.120"))
        self.assertFalse(updater.is_newer("0.3.0-dev.119", "0.3.0-dev.120"))

    def test_a_leading_v_is_accepted(self):
        self.assertTrue(updater.is_newer("v0.2.3", "0.2.2"))
        self.assertFalse(updater.is_newer("v0.2.2", "0.2.2"))

    def test_surrounding_whitespace_is_accepted(self):
        self.assertTrue(updater.is_newer("  0.2.3\n", "0.2.2"))

    def test_nonsense_never_counts_as_newer(self):
        # Guessing here means offering someone a downgrade, so anything that
        # cannot be read is treated as "not newer" rather than raising.
        for bad in ("", "latest", "not-a-version", "0.2.2 and then some", None, 3):
            with self.subTest(version=bad):
                self.assertFalse(updater.is_newer(bad, "0.2.2"))

    def test_parse_version_reports_what_it_cannot_read(self):
        with self.assertRaises(updater.UpdateError):
            updater.parse_version("latest")


class DownloadAddressTests(unittest.TestCase):
    def test_a_release_asset_of_this_project_is_allowed(self):
        url = f"{updater.RELEASES_BASE}/download/v1.0/AccessibleIDE.exe"
        self.assertEqual(updater._allowed_asset_url(url), url)

    def test_somewhere_else_is_refused(self):
        # The manifest is fetched from the internet and names the file to
        # run. Anything not on this project's releases is refused outright.
        for url in (
            "https://evil.example.com/AccessibleIDE.exe",
            "https://github.com/someone-else/project/releases/download/v1/a.exe",
            f"{updater.RELEASES_BASE}/../../evil.exe",
            "http://github.com/hothilux-21/accessible-coding/releases/download/v1/a.exe",
            "https://github.com/hothilux-21/accessible-coding/releases/latest",
            "",
            None,
        ):
            with self.subTest(url=url):
                with self.assertRaises(updater.UpdateError):
                    updater._allowed_asset_url(url)

    def test_a_path_that_climbs_out_is_refused(self):
        url = f"{updater.RELEASES_BASE}/download/../../../../evil.exe"
        with self.assertRaises(updater.UpdateError):
            updater._allowed_asset_url(url)


def swapped(test, obj, name, value):
    """Replace obj.name for one test, then put the real one back.

    The original has to be captured *before* the replacement. Registering
    the cleanup with the value read after replacing it restores the fake
    instead, and because unittest orders classes by name rather than by
    where they were written, one leaking fake can quietly break a whole
    class of tests for a reason that has nothing to do with them.
    """
    original = getattr(obj, name)
    setattr(obj, name, value)
    test.addCleanup(setattr, obj, name, original)
    return original


class FakeResponse:
    """Just enough of a file-like object for the download path."""

    def __init__(self, body=b"", headers=None, chunks=1):
        self.body = body
        self.headers = headers or {}
        self._chunk_size = max(1, len(body) // chunks) if body else 1
        self._sent = 0

    def read(self, size=-1):
        if self._sent >= len(self.body):
            return b""
        if size is None or size < 0:
            size = len(self.body) - self._sent
        piece = self.body[self._sent:self._sent + min(size, self._chunk_size)]
        self._sent += len(piece)
        return piece

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class ManifestTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        # Point the cache and the download folder inside the temp directory
        # so a test never writes to the machine it runs on.
        swapped(self, updater, "cache_path",
                lambda: pathlib.Path(self.tmp.name) / "check.json")
        swapped(self, updater, "update_dir",
                lambda: pathlib.Path(self.tmp.name) / "updates")

    def serve(self, body, headers=None, chunks=1):
        swapped(self, updater, "_open_url",
                lambda url, timeout, accept: FakeResponse(body, headers, chunks))

    def good_manifest(self, **overrides):
        manifest = {
            "version": "9.9.9",
            "url": f"{updater.RELEASES_BASE}/download/v9.9.9/AccessibleIDE.exe",
            "sha256": "a" * 64,
            "size": 3,
            "notes": "A test build.",
        }
        manifest.update(overrides)
        return manifest

    def test_a_good_manifest_is_accepted(self):
        self.serve(json.dumps(self.good_manifest()).encode())
        manifest = updater.fetch_manifest()
        self.assertEqual(manifest["version"], "9.9.9")
        self.assertIn("sha256", manifest)

    def test_every_required_field_is_required(self):
        for field in ("version", "url", "sha256", "size"):
            with self.subTest(missing=field):
                broken = self.good_manifest()
                del broken[field]
                self.serve(json.dumps(broken).encode())
                with self.assertRaises(updater.UpdateError):
                    updater.fetch_manifest()

    def test_a_manifest_pointing_elsewhere_is_refused(self):
        self.serve(json.dumps(self.good_manifest(
            url="https://evil.example.com/a.exe")).encode())
        with self.assertRaises(updater.UpdateError):
            updater.fetch_manifest()

    def test_something_that_is_not_json_is_refused(self):
        self.serve(b"<html>not json</html>")
        with self.assertRaises(updater.UpdateError):
            updater.fetch_manifest()

    def test_a_json_list_is_refused(self):
        self.serve(b"[1, 2, 3]")
        with self.assertRaises(updater.UpdateError):
            updater.fetch_manifest()

    def test_an_oversized_manifest_is_refused_before_it_is_read(self):
        self.serve(b"{}", headers={"Content-Length": str(updater.MAX_MANIFEST_BYTES + 1)})
        with self.assertRaises(updater.UpdateError):
            updater.fetch_manifest()


class ChannelTests(unittest.TestCase):
    """Which set of releases a reader is offered.

    The channel is a moving release tag the manifest is published under, so
    the address is the whole mechanism. If a channel resolves to the wrong
    one the reader is silently offered the wrong builds, which is the kind
    of wrong nobody reports.
    """

    def test_each_channel_has_its_own_address(self):
        # /releases/download/<tag>/ is the shape GitHub serves assets under
        # for an ordinary tag. Only the literal word "latest" has the
        # shorter /releases/latest/download/ form, which is exactly the trap
        # the old code fell into.
        self.assertEqual(
            updater.manifest_url("beta"),
            f"{updater.RELEASES_BASE}/download/beta/{updater.MANIFEST_NAME}")
        self.assertEqual(
            updater.manifest_url("stable"),
            f"{updater.RELEASES_BASE}/download/stable/{updater.MANIFEST_NAME}")
        self.assertNotEqual(updater.manifest_url("beta"),
                            updater.manifest_url("stable"))

    def test_beta_is_the_channel_a_reader_gets_without_asking(self):
        # Nothing stable has been published yet, so defaulting there would
        # leave a new reader with an app that can never see an update.
        self.assertEqual(updater.DEFAULT_CHANNEL, "beta")
        self.assertEqual(updater.manifest_url(), updater.manifest_url("beta"))

    def test_anything_unreadable_becomes_the_default(self):
        # A hand-edited config, a value from a future version, or nothing at
        # all. None of those is a reason to show the reader an error.
        for value in (None, "", "  ", "nightly", 7, [], {}, True):
            with self.subTest(value=value):
                self.assertEqual(updater.normalise_channel(value), "beta")

    def test_the_name_is_forgiving_about_case_and_spacing(self):
        for value in ("BETA", " Stable ", "stable"):
            with self.subTest(value=value):
                self.assertEqual(updater.normalise_channel(value),
                                 value.strip().lower())

    def test_the_manifest_is_read_from_the_channel_that_was_asked_for(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        swapped(self, updater, "cache_path",
                lambda: pathlib.Path(tmp.name) / "check.json")
        manifest = {
            "version": "9.9.9",
            "url": f"{updater.RELEASES_BASE}/download/v9.9.9/AccessibleIDE.exe",
            "sha256": "a" * 64,
            "size": 3,
        }
        asked = []

        def record(url, timeout, accept):
            asked.append(url)
            return FakeResponse(json.dumps(manifest).encode(), None, 1)

        swapped(self, updater, "_open_url", record)

        updater.fetch_manifest(channel="stable")
        self.assertTrue(asked[0].startswith(
            f"{updater.RELEASES_BASE}/download/stable/"), asked[0])
        # A cache-buster on the query string is expected, so this is a
        # prefix check rather than an equality one.
        asked.clear()
        updater.fetch_manifest(channel="beta")
        self.assertTrue(asked[0].startswith(
            f"{updater.RELEASES_BASE}/download/beta/"), asked[0])

    def test_a_check_says_which_channel_it_answered_for(self):
        # A reader who is offered nothing needs to be able to tell whether
        # that is because they are up to date or because they are watching
        # a channel that has not moved.
        result = updater.check(force=True, channel="stable")
        self.assertEqual(result["channel"], "stable")
        self.assertFalse(result["applicable"])  # not frozen under test

    def test_a_junk_channel_is_answered_as_beta_rather_than_failing(self):
        self.assertEqual(updater.check(force=True, channel="nightly")["channel"],
                         "beta")


class StagingTests(unittest.TestCase):
    """The download is only trusted once the bytes have been checked."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        swapped(self, updater, "update_dir",
                lambda: pathlib.Path(self.tmp.name) / "updates")

    def serve(self, body, headers=None, chunks=1):
        swapped(self, updater, "_open_url",
                lambda url, timeout, accept: FakeResponse(body, headers, chunks))

    def manifest_for(self, body, **overrides):
        import hashlib
        manifest = {
            "version": "9.9.9",
            "url": f"{updater.RELEASES_BASE}/download/v9.9.9/AccessibleIDE.exe",
            "sha256": hashlib.sha256(body).hexdigest(),
            "size": len(body),
        }
        manifest.update(overrides)
        return manifest

    def test_a_good_download_is_kept(self):
        body = b"MZ" + b"payload" * 500
        self.serve(body, chunks=7)
        path = updater.stage(self.manifest_for(body))
        self.assertTrue(path.is_file())
        self.assertEqual(path.read_bytes(), body)
        self.assertEqual(updater.sha256_of(path), self.manifest_for(body)["sha256"])

    def test_a_download_that_does_not_match_its_checksum_is_thrown_away(self):
        body = b"MZ" + b"payload" * 500
        self.serve(body, chunks=7)
        with self.assertRaises(updater.UpdateError):
            updater.stage(self.manifest_for(body, sha256="b" * 64))
        # Nothing left behind that could be mistaken for a good build.
        leftovers = list(pathlib.Path(self.tmp.name).rglob("AccessibleIDE.exe"))
        self.assertEqual(leftovers, [])

    def test_the_wrong_size_is_refused(self):
        body = b"MZ" + b"payload" * 10
        self.serve(body, chunks=3)
        with self.assertRaises(updater.UpdateError):
            updater.stage(self.manifest_for(body, size=len(body) + 1))

    def test_an_empty_download_is_refused(self):
        self.serve(b"", chunks=1)
        with self.assertRaises(updater.UpdateError):
            updater.stage(self.manifest_for(b""))

    def test_a_checksum_that_is_not_a_checksum_is_refused(self):
        body = b"MZ" + b"payload"
        self.serve(body, chunks=2)
        with self.assertRaises(updater.UpdateError):
            updater.stage(self.manifest_for(body, sha256="not-a-checksum"))

    def test_a_download_from_somewhere_else_is_never_started(self):
        called = []
        swapped(self, updater, "_open_url",
                lambda *a, **k: called.append(a) or FakeResponse(b""))
        with self.assertRaises(updater.UpdateError):
            updater.stage({
                "url": "https://evil.example.com/a.exe",
                "sha256": "a" * 64,
                "size": 1,
            })
        self.assertEqual(called, [])


class CheckIntervalTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        swapped(self, updater, "cache_path",
                lambda: pathlib.Path(self.tmp.name) / "check.json")

    def test_a_first_launch_always_checks(self):
        self.assertTrue(updater.should_check(now=1000.0))

    def test_a_recent_check_is_not_repeated(self):
        updater.remember_check(now=1000.0)
        self.assertFalse(updater.should_check(now=1000.0 + 60))
        self.assertFalse(updater.should_check(
            now=1000.0 + updater.CHECK_INTERVAL_SECONDS - 1))

    def test_an_old_check_is_repeated(self):
        updater.remember_check(now=1000.0)
        self.assertTrue(updater.should_check(
            now=1000.0 + updater.CHECK_INTERVAL_SECONDS))

    def test_asking_by_hand_ignores_the_interval(self):
        updater.remember_check(now=1000.0)
        self.assertTrue(updater.should_check(force=True, now=1000.0 + 1))

    def test_a_corrupt_cache_file_is_not_fatal(self):
        updater.cache_path().parent.mkdir(parents=True, exist_ok=True)
        updater.cache_path().write_text("not json at all", encoding="utf-8")
        self.assertTrue(updater.should_check(now=1000.0))


class CheckResultTests(unittest.TestCase):
    def test_the_website_does_not_offer_an_exe(self):
        os.environ.pop("ACCESSIBLE_IDE_UPDATE_TEST", None)
        result = updater.check(force=True)
        self.assertFalse(result["applicable"])
        self.assertFalse(result["update_available"])

    def test_a_failure_is_reported_rather_than_raised(self):
        # The reader is trying to open an editor. A check that cannot reach
        # the network must never be the reason that fails.
        os.environ["ACCESSIBLE_IDE_UPDATE_TEST"] = "1"
        self.addCleanup(os.environ.pop, "ACCESSIBLE_IDE_UPDATE_TEST", None)

        # The stand-in takes **kwargs because check() now says which channel
        # it wanted. A double with a fixed signature would fail on the
        # keyword rather than on the thing it is standing in for.
        def explode(*args, **kwargs):
            raise updater.UpdateError("could not reach GitHub to check for updates")
        swapped(self, updater, "fetch_manifest", explode)

        result = updater.check(force=True)
        self.assertFalse(result["update_available"])
        self.assertIn("could not reach", result["error"])

    def test_a_newer_build_is_offered(self):
        os.environ["ACCESSIBLE_IDE_UPDATE_TEST"] = "1"
        self.addCleanup(os.environ.pop, "ACCESSIBLE_IDE_UPDATE_TEST", None)
        swapped(self, updater, "fetch_manifest", lambda *a, **k: {
            "version": "99.0.0",
            "url": f"{updater.RELEASES_BASE}/download/v99/AccessibleIDE.exe",
            "sha256": "a" * 64,
            "size": 1,
            "notes": "Fixed the thing.",
        })
        result = updater.check(force=True)
        self.assertTrue(result["update_available"])
        self.assertEqual(result["latest"], "99.0.0")
        self.assertEqual(result["notes"], "Fixed the thing.")

    def test_the_same_build_is_not_offered(self):
        os.environ["ACCESSIBLE_IDE_UPDATE_TEST"] = "1"
        self.addCleanup(os.environ.pop, "ACCESSIBLE_IDE_UPDATE_TEST", None)
        swapped(self, updater, "fetch_manifest", lambda *a, **k: {
            "version": updater.current_version(),
            "url": f"{updater.RELEASES_BASE}/download/v/AccessibleIDE.exe",
            "sha256": "a" * 64,
            "size": 1,
        })
        result = updater.check(force=True)
        self.assertFalse(result["update_available"])


class WaitingBuildTests(unittest.TestCase):
    """The record of a downloaded build, and what is allowed to act on it.

    This is the last thing standing between a file on disk and a file being
    swapped for the program, so it is tested against a record that lies.
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        swapped(self, updater, "update_dir",
                lambda: pathlib.Path(self.tmp.name) / "updates")

    def build(self, name=updater.ASSET_NAME, body=b"MZ new build"):
        staged = updater.update_dir() / name
        staged.parent.mkdir(parents=True, exist_ok=True)
        staged.write_bytes(body)
        return staged

    def test_a_downloaded_build_is_remembered(self):
        staged = self.build()
        updater.remember_staged(staged, "9.9.9")
        found = updater.pending_build()
        self.assertIsNotNone(found)
        self.assertEqual(found[0], staged)
        self.assertEqual(found[1], "9.9.9")

    def test_nothing_remembered_means_nothing_to_do(self):
        self.assertIsNone(updater.pending_build())

    def test_a_record_naming_some_other_file_is_ignored(self):
        elsewhere = self.build(name="something-else.exe")
        updater.remember_staged(elsewhere, "9.9.9")
        self.assertIsNone(updater.pending_build())

    def test_a_record_whose_file_is_gone_is_ignored(self):
        staged = self.build()
        updater.remember_staged(staged, "9.9.9")
        staged.unlink()
        self.assertIsNone(updater.pending_build())

    def test_a_damaged_record_is_ignored_rather_than_guessed_at(self):
        updater.update_dir().mkdir(parents=True, exist_ok=True)
        (updater.update_dir() / updater.STATE_NAME).write_text("{not json")
        self.assertIsNone(updater.pending_build())

    def test_a_record_missing_its_version_is_ignored(self):
        state = updater.update_dir() / updater.STATE_NAME
        state.parent.mkdir(parents=True, exist_ok=True)
        state.write_text(json.dumps({"staged": str(self.build())}))
        self.assertIsNone(updater.pending_build())

    def test_remembering_leaves_no_part_file_behind(self):
        updater.remember_staged(self.build(), "9.9.9")
        leftovers = [p.name for p in updater.update_dir().iterdir()
                     if p.name.endswith(".part")]
        self.assertEqual(leftovers, [])

    def test_clearing_forgets_the_build(self):
        updater.remember_staged(self.build(), "9.9.9")
        updater.clear_pending()
        self.assertIsNone(updater.pending_build())
        updater.clear_pending()  # must not mind being asked twice


class HelperCleanupTests(unittest.TestCase):
    """Helper copies are only tidied at a moment it is safe to."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        swapped(self, updater, "update_dir",
                lambda: pathlib.Path(self.tmp.name) / "updates")

    def test_leftover_helpers_go_and_other_files_stay(self):
        directory = updater.update_dir()
        directory.mkdir(parents=True, exist_ok=True)
        helper = directory / f"{updater.HELPER_PREFIX}1234.exe"
        build = directory / updater.ASSET_NAME
        helper.write_bytes(b"old helper")
        build.write_bytes(b"downloaded build")
        updater.tidy_helpers()
        self.assertFalse(helper.exists())
        self.assertTrue(build.exists())

    def test_tidying_an_absent_folder_is_not_an_error(self):
        updater.tidy_helpers()


class ExitHandOverTests(unittest.TestCase):
    """What the app does on the way out, without ever stopping the exit."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        swapped(self, updater, "update_dir",
                lambda: pathlib.Path(self.tmp.name) / "updates")
        self.app = load_app_module()

    def stage_build(self):
        staged = updater.update_dir() / updater.ASSET_NAME
        staged.parent.mkdir(parents=True, exist_ok=True)
        staged.write_bytes(b"MZ new build")
        updater.remember_staged(staged, "9.9.9")
        return staged

    def test_a_waiting_build_is_handed_to_the_helper(self):
        staged = self.stage_build()
        handed = {}
        swapped(self, updater, "is_frozen", lambda: True)
        swapped(self, updater, "install",
                lambda path, relaunch=False: handed.update(
                    path=path, relaunch=relaunch))
        self.app._apply_staged_update_on_exit()
        self.assertEqual(handed["path"], staged)
        # The reader closed the app themselves. Starting it again for them
        # would hide the fact that anything happened at all.
        self.assertFalse(handed["relaunch"])

    def test_nothing_waiting_means_nothing_handed_over(self):
        calls = []
        swapped(self, updater, "is_frozen", lambda: True)
        swapped(self, updater, "install", lambda *a, **k: calls.append(1))
        self.app._apply_staged_update_on_exit()
        self.assertEqual(calls, [])

    def test_a_failing_helper_never_stops_the_app_closing(self):
        self.stage_build()

        def explode(*args, **kwargs):
            raise OSError("no room for a second copy")

        swapped(self, updater, "is_frozen", lambda: True)
        swapped(self, updater, "install", explode)
        # The window is already closing. Raising here would strand the reader
        # staring at a frozen app they cannot close.
        self.app._apply_staged_update_on_exit()

    def test_the_website_never_hands_anything_over(self):
        self.stage_build()
        calls = []
        swapped(self, updater, "is_frozen", lambda: False)
        swapped(self, updater, "install", lambda *a, **k: calls.append(1))
        self.app._apply_staged_update_on_exit()
        self.assertEqual(calls, [])


@unittest.skipUnless(os.name == "nt", "Windows process handles")
class RealProcessWaitTests(unittest.TestCase):
    """process_has_exited against real processes, not mocks.

    This is the one place the updater can hang forever, and a fake handle
    would agree with every version of the code, so these use real ones.
    """

    def a_process_that_keeps_running(self):
        import subprocess
        child = subprocess.Popen(
            [sys.executable, "-c", "import time; time.sleep(30)"])
        # Last-in-first-out, so the wait is registered before the kill.
        self.addCleanup(child.wait, 10)
        self.addCleanup(child.kill)
        return child

    def test_a_running_process_is_reported_as_still_running(self):
        child = self.a_process_that_keeps_running()
        self.assertFalse(updater.process_has_exited(child.pid, timeout=0.4))

    def test_a_finished_process_is_reported_as_finished(self):
        child = self.a_process_that_keeps_running()
        child.kill()
        child.wait(timeout=10)
        # The handle is still open on the object above, which is exactly the
        # case os.kill gets wrong.
        self.assertTrue(updater.process_has_exited(child.pid, timeout=5))

    def test_a_process_that_never_existed_is_not_waited_for(self):
        # A pid that was never used is a pid nothing is holding open.
        self.assertTrue(updater.process_has_exited(0x7FFFFFF0, timeout=5))


@unittest.skipUnless(os.name == "nt", "Windows process handles")
class RealSwapTests(unittest.TestCase):
    """The whole hand-over, with a real waiting process and a real file.

    Windows only, like the class above. The helper recognises a finished
    process by holding a handle to it, and the fallback it uses elsewhere
    asks ``os.kill(pid, 0)`` - which reports an exited-but-unreaped child
    as alive, so on Linux the wait would never end. That fallback is not
    shipped: the updater lives inside the Windows exe, and the website
    never hands anything over (see ExitHandOverTests). Left unguarded
    here it made CI sit in this test for the full 24-hour wait limit.
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = pathlib.Path(self.tmp.name)
        # Deliberately a different folder from the target. In the real app
        # the download sits in the config folder and the program sits beside
        # its shortcut, and the two are never the same file.
        self.downloads = self.dir / "updates"
        self.downloads.mkdir()
        self.staged = self.downloads / updater.ASSET_NAME
        self.staged.write_bytes(b"new build")
        self.target = self.dir / "AccessibleIDE.exe"
        self.target.write_bytes(b"old build")

    def sleeper(self, seconds=30):
        """A child that will still be running unless the test ends it."""
        import subprocess
        child = subprocess.Popen(
            [sys.executable, "-c", f"import time; time.sleep({seconds})"])
        # Cleanups run last-in-first-out, so the wait is registered before
        # the kill on purpose: a wait that runs first would always time out.
        self.addCleanup(child.wait, 10)
        self.addCleanup(child.kill)
        return child

    def finished(self):
        """A child that has already gone, and whose handle is still open."""
        import subprocess
        child = subprocess.Popen([sys.executable, "-c", "pass"])
        child.wait(timeout=10)
        return child

    def wait_for_me(self, marker):
        import subprocess
        child = subprocess.Popen(
            [sys.executable, "-c",
             f"import time,pathlib; time.sleep(0.3); pathlib.Path(r'{marker}').write_text('x')"])
        self.addCleanup(child.wait, 10)
        return child

    def swap_against(self, child):
        return updater.run_helper([
            "--wait-for", str(child.pid),
            "--staged", str(self.staged),
            "--target", str(self.target),
        ])

    def test_the_build_is_replaced_once_the_app_has_gone(self):
        marker = self.dir / "gone"
        child = self.wait_for_me(marker)
        self.assertEqual(self.swap_against(child), 0)
        self.assertEqual(self.target.read_bytes(), b"new build")
        self.assertFalse(self.staged.exists())

    def test_a_running_app_is_never_replaced(self):
        child = self.sleeper()
        # A short cap stands in for a reader leaving the app open overnight.
        original = updater.WAIT_LIMIT_SECONDS
        updater.WAIT_LIMIT_SECONDS = 0.5
        self.addCleanup(setattr, updater, "WAIT_LIMIT_SECONDS", original)
        self.assertEqual(self.swap_against(child), 1)
        self.assertEqual(self.target.read_bytes(), b"old build")

    def test_a_missing_build_leaves_the_old_one_alone(self):
        self.staged.unlink()
        self.assertEqual(self.swap_against(self.finished()), 1)
        self.assertEqual(self.target.read_bytes(), b"old build")

    def test_an_installed_build_is_not_installed_again(self):
        updater.remember_staged(self.staged, "9.9.9")
        self.assertEqual(self.swap_against(self.finished()), 0)
        # The record has to go too, or the next close puts the same build
        # back in again.
        self.assertIsNone(updater.pending_build())

    def test_no_arguments_at_all_does_not_do_anything(self):
        self.assertEqual(updater.run_helper([]), 1)
        self.assertEqual(updater.run_helper(["--wait-for", "not-a-number"]), 1)

    def test_a_target_that_is_also_the_download_is_not_deleted(self):
        # The two paths should never be the same file, but if they ever were,
        # tidying up the download must not take the program with it.
        self.assertEqual(updater.run_helper([
            "--wait-for", str(self.finished().pid),
            "--staged", str(self.target),
            "--target", str(self.target),
        ]), 0)
        self.assertTrue(self.target.is_file())

    def test_the_new_build_is_only_started_when_asked_to_be(self):
        # Both processes made first: the stub below replaces the very call
        # used to make them.
        first = self.finished()
        second = self.finished()
        started = []
        original = updater.subprocess.Popen
        updater.subprocess.Popen = lambda command, **kw: started.append(command)
        self.addCleanup(setattr, updater.subprocess, "Popen", original)

        self.assertEqual(updater.run_helper([
            "--wait-for", str(first.pid),
            "--staged", str(self.staged),
            "--target", str(self.target),
        ]), 0)
        self.assertEqual(started, [], "the app was started without being asked")

        self.staged.write_bytes(b"newer build")
        self.assertEqual(updater.run_helper([
            "--wait-for", str(second.pid),
            "--staged", str(self.staged),
            "--target", str(self.target),
            "--relaunch",
        ]), 0)
        self.assertEqual([str(self.target)], [str(c[0]) for c in started])
        self.assertEqual(self.target.read_bytes(), b"newer build")


if __name__ == "__main__":
    unittest.main()
