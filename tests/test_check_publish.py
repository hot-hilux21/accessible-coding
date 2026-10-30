"""Tests for the check that runs before a release is published.

The two failures these guard against both end with a reader never getting an
update they were offered. One is a name that no longer matches, so the app
refuses the address as not from this project. The other is a version that goes
backwards, so the channel points at an older build than the one already out
and nobody on the newer build is ever offered anything.
"""

import pathlib
import subprocess
import sys
import unittest
from unittest import mock

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "tools"))
sys.path.insert(0, str(REPO_ROOT / "src"))

import check_publish  # noqa: E402
from accessible_ide import updater  # noqa: E402

PINNED = f"{updater.OWNER}/{updater.REPO}"
GOOD_URL = (
    f"https://github.com/{PINNED}/releases/download/v0.4.0-beta/AccessibleCoding.exe"
)


class OwnerTests(unittest.TestCase):
    def test_the_pinned_name_is_accepted(self):
        check_publish.verify_publish(PINNED, GOOD_URL, "0.4.0-beta", None)

    def test_the_name_is_matched_case_insensitively(self):
        # GitHub owner and repository names are not case sensitive, and the
        # value a workflow hands over is not guaranteed to be cased as stored.
        check_publish.verify_publish(PINNED.upper(), GOOD_URL, "0.4.0-beta", None)

    def test_a_different_repository_is_refused(self):
        # The rename that was not followed through: the app still trusts one
        # name while the build belongs to another.
        with self.assertRaises(check_publish.CheckError) as caught:
            check_publish.verify_publish(
                "someone-else/accessible-coding", GOOD_URL, "0.4.0-beta", None
            )
        self.assertIn("rename", str(caught.exception))


class AddressTests(unittest.TestCase):
    def test_an_address_from_another_owner_is_refused(self):
        url = (
            "https://github.com/someone-else/accessible-coding"
            "/releases/download/v0.4.0-beta/AccessibleCoding.exe"
        )
        with self.assertRaises(check_publish.CheckError):
            check_publish.verify_publish(PINNED, url, "0.4.0-beta", None)

    def test_an_address_that_is_not_a_release_asset_is_refused(self):
        with self.assertRaises(check_publish.CheckError):
            check_publish.verify_publish(
                PINNED, "https://example.com/AccessibleCoding.exe", "0.4.0-beta", None
            )

    def test_plain_http_is_refused(self):
        # An address that gets run has to be https, or it can be swapped on
        # the way, which is exactly what the app's own guard says.
        with self.assertRaises(check_publish.CheckError):
            check_publish.verify_publish(
                PINNED, GOOD_URL.replace("https://", "http://"), "0.4.0-beta", None
            )

    def test_an_address_that_differs_only_in_case_is_refused(self):
        # The app compares the owner character for character, so an address
        # that only differs in case would be refused there. It has to be
        # refused here instead, not by every reader.
        url = GOOD_URL.replace(
            f"github.com/{PINNED}/", f"github.com/{PINNED.upper()}/"
        )
        with self.assertRaises(check_publish.CheckError):
            check_publish.verify_publish(PINNED, url, "0.4.0-beta", None)


class VersionTests(unittest.TestCase):
    def test_nothing_published_yet_is_allowed(self):
        check_publish.verify_publish(PINNED, GOOD_URL, "0.4.0-beta", None)

    def test_a_newer_version_is_allowed(self):
        check_publish.verify_publish(PINNED, GOOD_URL, "0.4.0-beta", "0.3.5-beta")

    def test_the_same_version_is_allowed(self):
        # Re-running a tag to replace a build that failed to upload is normal.
        # The channel does not move backwards, so this is not the failure.
        check_publish.verify_publish(PINNED, GOOD_URL, "0.3.5-beta", "0.3.5-beta")

    def test_an_older_version_is_refused(self):
        with self.assertRaises(check_publish.CheckError) as caught:
            check_publish.verify_publish(
                PINNED, GOOD_URL, "0.3.4-beta", "0.3.5-beta"
            )
        self.assertIn("older", str(caught.exception))

    def test_the_suffix_ordering_the_app_uses_is_honoured(self):
        # 0.3.6-beta is newer than 0.3.5-beta, but a finished 0.3.6 is newer
        # than the 0.3.6-beta, so publishing the beta over it is a backwards
        # move and has to be refused.
        check_publish.verify_publish(PINNED, GOOD_URL, "0.3.6-beta", "0.3.5-beta")
        with self.assertRaises(check_publish.CheckError):
            check_publish.verify_publish(PINNED, GOOD_URL, "0.3.6-beta", "0.3.6")


class CommandTests(unittest.TestCase):
    def test_offline_passes_without_asking_the_network(self):
        def exploding_lookup(channel):
            raise AssertionError("offline mode used the network")

        with mock.patch.object(check_publish, "lookup_version", exploding_lookup):
            code = check_publish.main([
                "check", "--channel", "beta", "--version", "0.4.0-beta",
                "--url", GOOD_URL, "--repo", PINNED, "--offline",
            ])
        self.assertEqual(code, 0)

    def test_an_unknown_channel_is_refused(self):
        code = check_publish.main([
            "check", "--channel", "nightly", "--version", "0.4.0-beta",
            "--url", GOOD_URL, "--repo", PINNED, "--offline",
        ])
        self.assertEqual(code, 1)

    def test_a_mismatched_repository_is_refused(self):
        code = check_publish.main([
            "check", "--channel", "beta", "--version", "0.4.0-beta",
            "--url", GOOD_URL, "--repo", "someone-else/accessible-coding",
            "--offline",
        ])
        self.assertEqual(code, 1)

    def test_a_regression_is_refused(self):
        with mock.patch.object(
            check_publish, "lookup_version", lambda channel: "0.4.0-beta"
        ):
            code = check_publish.main([
                "check", "--channel", "beta", "--version", "0.3.5-beta",
                "--url", GOOD_URL, "--repo", PINNED,
            ])
        self.assertEqual(code, 1)

    def test_a_normal_publish_passes(self):
        with mock.patch.object(
            check_publish, "lookup_version", lambda channel: "0.3.5-beta"
        ):
            code = check_publish.main([
                "check", "--channel", "beta", "--version", "0.4.0-beta",
                "--url", GOOD_URL, "--repo", PINNED,
            ])
        self.assertEqual(code, 0)


class StandaloneImportTests(unittest.TestCase):
    """The tool has to run in the job that publishes, which installs nothing.

    The publish job downloads the built artifacts and moves a release. It
    never installs requirements.txt, so Flask is not there. Importing the
    package to reach the updater therefore fails before any check runs - and
    because this tool runs before the release moves, that failure blocks the
    publish it was added to protect. That happened for real on the dev
    channel the first time this tool ran in CI.
    """

    # Enough of the runtime that the package cannot be imported while these
    # are blocked.
    BLOCKER = (
        "import importlib.abc, sys\n"
        "BLOCKED = {'flask', 'werkzeug', 'jinja2', 'gunicorn', 'webview', 'yaml'}\n"
        "class Blocked(importlib.abc.MetaPathFinder):\n"
        "    def find_spec(self, fullname, path=None, target=None):\n"
        "        if fullname.split('.')[0] in BLOCKED:\n"
        "            raise ModuleNotFoundError('No module named ' + repr(fullname))\n"
        "        return None\n"
        "sys.meta_path.insert(0, Blocked())\n"
    )

    def run_without_the_app_dependencies(self, body):
        return subprocess.run(
            [sys.executable, "-c", self.BLOCKER + body],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )

    def test_the_blocker_would_stop_the_package_import(self):
        # Without this, the check below would pass just as well against a tool
        # that still imported the package, and would prove nothing.
        done = self.run_without_the_app_dependencies(
            f"sys.path.insert(0, {str(REPO_ROOT / 'src')!r})\n"
            "import accessible_ide\n"
        )
        self.assertNotEqual(done.returncode, 0)
        self.assertIn("flask", done.stderr)

    def test_the_check_runs_without_the_app_dependencies(self):
        body = (
            f"sys.path.insert(0, {str(REPO_ROOT / 'tools')!r})\n"
            "import check_publish\n"
            "raise SystemExit(check_publish.main([\n"
            "    'check', '--channel', 'beta', '--version', '0.4.0-beta',\n"
            f"    '--url', {GOOD_URL!r}, '--repo', {PINNED!r}, '--offline',\n"
            "]))\n"
        )
        done = self.run_without_the_app_dependencies(body)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn("ok: beta starts at 0.4.0-beta", done.stdout)

    def test_the_updater_can_name_itself_without_the_package(self):
        # Checking a channel reads the manifest, and reading the manifest
        # sends a request header naming the version. Going through the
        # package for that name is what broke the dev publish the second
        # time: the tool had loaded fine, and then died on the fetch.
        body = (
            f"sys.path.insert(0, {str(REPO_ROOT / 'tools')!r})\n"
            "import check_publish\n"
            "print(check_publish.updater.current_version())\n"
            "print(check_publish.updater.manifest_url('stable'))\n"
        )
        done = self.run_without_the_app_dependencies(body)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(done.stdout.strip().splitlines()[0], "unknown")


if __name__ == "__main__":
    unittest.main()
