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
import urllib.error

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
            # Plain http, even on the right project: a download that gets run
            # has to be https or it can be swapped on the way.
            f"http://github.com/{updater.OWNER}/{updater.REPO}/releases/download/v1/a.exe",
            # The account this project was on before the rename. Same repo name,
            # different owner, so the allowlist has to key on the owner it was
            # given and not accept the old one on the strength of the name.
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


def http_says(test, status):
    """Make every request answer with an HTTP error, as GitHub really does.

    Patched at urlopen rather than at the helper above it, so the code that
    turns a status into the right kind of failure is itself under test.
    """

    def refuse(request, timeout=None):
        raise urllib.error.HTTPError(
            getattr(request, "full_url", request), status,
            "Test status", None, None)

    swapped(test, updater.urllib.request, "urlopen", refuse)


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

    def test_an_empty_channel_is_not_reported_as_a_broken_connection(self):
        # A channel nothing has been published to yet is an ordinary state.
        # Calling it a network fault tells a reader their connection is
        # broken when it is fine, and there is nothing they can do about it.
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        swapped(self, updater, "cache_path",
                lambda: pathlib.Path(tmp.name) / "check.json")
        # Updates only apply to the packaged app; in a source checkout the
        # check politely does nothing at all.
        swapped(self, updater, "is_frozen", lambda: True)
        http_says(self, 404)

        with self.assertRaises(updater.UpdateError) as caught:
            updater.fetch_manifest(channel="stable")
        self.assertEqual(caught.exception.code, "channel_empty")
        self.assertIn("stable", str(caught.exception))

        result = updater.check(force=True, channel="stable")
        self.assertEqual(result["error_code"], "channel_empty")
        self.assertFalse(result["update_available"])
        self.assertNotIn("latest", result)

    def test_a_build_that_has_gone_missing_is_its_own_problem(self):
        # The manifest named a build and the build is not there. That is not
        # the same as a channel with nothing on it, and not a network fault
        # either, so it must not borrow either of their sentences.
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        swapped(self, updater, "update_dir",
                lambda: pathlib.Path(tmp.name) / "updates")
        http_says(self, 404)
        manifest = {
            "url": f"{updater.RELEASES_BASE}/download/v0.4.0/{updater.ASSET_NAME}",
            "sha256": "0" * 64,
            "size": 10,
        }
        with self.assertRaises(updater.UpdateError) as caught:
            updater.stage(manifest)
        self.assertEqual(caught.exception.code, "missing_build")

    def test_a_404_leaves_no_half_finished_file_behind(self):
        # The same care as any other failed download: a part-file left under
        # the real name could be installed later without being checked.
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        swapped(self, updater, "update_dir",
                lambda: pathlib.Path(tmp.name) / "updates")
        http_says(self, 404)
        manifest = {
            "url": f"{updater.RELEASES_BASE}/download/v0.4.0/{updater.ASSET_NAME}",
            "sha256": "0" * 64,
            "size": 10,
        }
        with self.assertRaises(updater.UpdateError):
            updater.stage(manifest)
        self.assertEqual(list(updater.update_dir().iterdir()), [])


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

    def test_a_record_for_the_version_already_running_is_ignored(self):
        # This is what stops a loop. A record outlives the update unless
        # something clears it, and one that survived would run the same
        # installer on every close, for a build the reader already has, each
        # time asking for permission to install it again.
        updater.remember_staged(self.build(), updater.current_version())
        self.assertIsNone(updater.pending_build())

    def test_a_record_for_an_older_build_is_ignored(self):
        # A downgrade is not an update. This uses the same comparison that
        # refuses to offer one, so the two cannot disagree.
        updater.remember_staged(self.build(), "0.0.1")
        self.assertIsNone(updater.pending_build())

    def test_a_record_whose_version_cannot_be_read_is_ignored(self):
        # The record is the thing on disk most likely to be tampered with or
        # half-written. An unreadable version is never newer than anything.
        updater.remember_staged(self.build(), "not a version")
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

    def test_a_waiting_installer_is_handed_over(self):
        staged = self.stage_build()
        handed = {}
        swapped(self, updater, "is_frozen", lambda: True)
        swapped(self, updater, "install",
                lambda path: handed.update(path=path) or True)
        self.app._apply_staged_update_on_exit()
        self.assertEqual(handed["path"], staged)

    def test_a_handed_over_installer_is_not_offered_again(self):
        # Left behind, the record would run the same installer on every
        # close, for a build the reader already has, each time with its
        # permission prompt. The old updater cleared it from inside the
        # helper; there is no helper now, so this is where it has to happen.
        self.stage_build()
        swapped(self, updater, "is_frozen", lambda: True)
        swapped(self, updater, "install", lambda path: True)
        self.app._apply_staged_update_on_exit()
        self.assertIsNone(updater.pending_build())

    def test_nothing_waiting_means_nothing_handed_over(self):
        calls = []
        swapped(self, updater, "is_frozen", lambda: True)
        swapped(self, updater, "install", lambda *a, **k: calls.append(1))
        self.app._apply_staged_update_on_exit()
        self.assertEqual(calls, [])

    def test_a_refused_permission_never_stops_the_app_closing(self):
        self.stage_build()

        def explode(*args, **kwargs):
            raise updater.UpdateError("the reader said no", code="start_failed")

        swapped(self, updater, "is_frozen", lambda: True)
        swapped(self, updater, "install", explode)
        # The window is already closing. Raising here would strand the reader
        # staring at a frozen app they cannot close.
        self.app._apply_staged_update_on_exit()
        # And the record survives, so declining one prompt does not quietly
        # throw the update away: it is offered again the next time the app
        # closes, which is what the reader asked for by pressing Install.
        self.assertIsNotNone(updater.pending_build())

    def test_the_website_never_hands_anything_over(self):
        self.stage_build()
        calls = []
        swapped(self, updater, "is_frozen", lambda: False)
        swapped(self, updater, "install", lambda *a, **k: calls.append(1))
        self.app._apply_staged_update_on_exit()
        self.assertEqual(calls, [])


@unittest.skipUnless(os.name == "nt", "ShellExecuteW")
class InstallerStartTests(unittest.TestCase):
    """Starting the installer, which is the whole of what install() does.

    It used to do more: copy the app aside, run the copy as a helper, wait
    for this process to end, and swap the file. That is what broke. The copy
    had no _internal folder beside it, so it died on the way up with "failed
    to load the Python DLL" and no update ever happened. What is left is one
    decision, and these are what check it.
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.staged = pathlib.Path(self.tmp.name) / updater.ASSET_NAME
        self.staged.write_bytes(b"MZ installer")
        swapped(self, updater, "is_frozen", lambda: True)

    def started_with(self, result):
        """Record what install() asks Windows to run, and what it answers."""
        calls = []
        swapped(self, updater, "_shell_execute",
                lambda program, parameters, verb: calls.append(
                    (program, parameters, verb)) or result)
        return calls

    def test_the_installer_is_the_file_that_was_downloaded(self):
        calls = self.started_with(42)
        self.assertTrue(updater.install(self.staged))
        self.assertEqual(calls, [
            (self.staged, " ".join(updater.INSTALLER_FLAGS), "runas")])

    def test_the_flags_it_is_started_with(self):
        # Every flag is a decision, so every flag is pinned. Silent rather
        # than very silent: the reader has just been told an update is being
        # applied, and a progress window saying so is the honest thing to
        # show. /CLOSEAPPLICATIONS is what lets Setup replace a folder that
        # is in use. /NORESTART is the one that must never go missing, since
        # an update that reboots the machine is not an update.
        for flag in ("/SILENT", "/CLOSEAPPLICATIONS", "/NORESTART",
                     "/SUPPRESSMSGBOXES", "/NOCANCEL"):
            with self.subTest(flag=flag):
                self.assertIn(flag, updater.INSTALLER_FLAGS)
        self.assertNotIn("/VERYSILENT", updater.INSTALLER_FLAGS)

    def test_a_reader_who_says_no_is_not_an_install(self):
        # ERROR_CANCELLED is what a declined permission prompt returns, and it
        # is 1223. That is above 32, so "greater than 32 means it worked"
        # would read the refusal as a successful install: the app would clear
        # the record and leave the reader on the old version, silently.
        self.started_with(1223)
        with self.assertRaises(updater.UpdateError):
            updater.install(self.staged)

    def test_every_documented_refusal_above_the_line_is_caught(self):
        # The set has to be consulted, not just declared.
        for code in sorted(updater.SHELL_EXECUTE_REFUSALS):
            with self.subTest(code=code):
                self.started_with(code)
                with self.assertRaises(updater.UpdateError):
                    updater.install(self.staged)

    def test_no_handle_at_all_is_not_an_install(self):
        self.started_with(None)
        with self.assertRaises(updater.UpdateError):
            updater.install(self.staged)

    def test_a_missing_installer_is_refused_before_anything_is_started(self):
        calls = self.started_with(42)
        self.staged.unlink()
        with self.assertRaises(updater.UpdateError):
            updater.install(self.staged)
        self.assertEqual(calls, [],
                         "Windows was asked to run a file that is not there")

    def test_the_website_never_starts_an_installer(self):
        calls = self.started_with(42)
        swapped(self, updater, "is_frozen", lambda: False)
        with self.assertRaises(updater.UpdateError):
            updater.install(self.staged)
        self.assertEqual(calls, [])

    def test_the_permission_prompt_is_asked_for(self):
        # runas is the whole reason this is not subprocess. Without it the
        # installer cannot be started at all from an app that is not already
        # elevated, so an update for anyone who installed to Program Files
        # would fail every single time.
        calls = self.started_with(42)
        updater.install(self.staged)
        self.assertEqual(calls[0][2], "runas")


if __name__ == "__main__":
    unittest.main()
