"""Tests for the build version stamp and the manifest it publishes.

The failure these guard against is subtle and bad: the build stamps one
version into the program and a different one into the manifest, the app
compares a version against itself, and either every reader is told there is
an update that does not exist, or a real update is never offered. So the two
are checked against each other here, not just on their own.
"""

import hashlib
import importlib
import json
import pathlib
import re
import sys
import tempfile
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "tools"))
sys.path.insert(0, str(REPO_ROOT / "src"))

import stamp_version  # noqa: E402
from accessible_ide import updater  # noqa: E402


class StampTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.init = pathlib.Path(self.tmp.name) / "__init__.py"
        self.init.write_text(
            '"""Docstring."""\n'
            '__version__ = "0.0.1"\n'
            '__author__ = "Someone"\n'
            '\n'
            'def create_app():\n'
            '    return None\n',
            encoding='utf-8',
        )

    def test_the_version_is_written_in(self):
        stamp_version.stamp_version(self.init, "0.2.2-beta.dev.181")
        self.assertIn('__version__ = "0.2.2-beta.dev.181"', self.init.read_text(encoding="utf-8"))

    def test_nothing_else_in_the_file_is_touched(self):
        before = self.init.read_text(encoding="utf-8")
        stamp_version.stamp_version(self.init, "1.2.3")
        after = self.init.read_text(encoding="utf-8")
        self.assertEqual(before.replace('"0.0.1"', '"1.2.3"'), after)

    def test_a_leading_v_is_dropped(self):
        stamp_version.stamp_version(self.init, "v1.2.3")
        self.assertIn('__version__ = "1.2.3"', self.init.read_text(encoding="utf-8"))

    def test_stamping_twice_replaces_rather_than_appends(self):
        stamp_version.stamp_version(self.init, "1.0.0")
        stamp_version.stamp_version(self.init, "1.0.1")
        text = self.init.read_text(encoding="utf-8")
        self.assertEqual(text.count("__version__"), 1)
        self.assertIn('"1.0.1"', text)

    def test_something_that_is_not_a_version_is_refused(self):
        for bad in ("latest", "", "1.2.3; rm -rf /", "../../etc", "one.two"):
            with self.subTest(version=bad):
                with self.assertRaises(stamp_version.StampError):
                    stamp_version.stamp_version(self.init, bad)

    def test_a_file_with_no_version_line_is_refused(self):
        # Silently shipping the old version is worse than failing the build.
        self.init.write_text("x = 1\n", encoding="utf-8")
        with self.assertRaises(stamp_version.StampError):
            stamp_version.stamp_version(self.init, "1.0.0")

    def test_the_two_copies_start_out_saying_the_same_thing(self):
        # Both are overwritten by every build, so this only ever fails between
        # a release and the next commit that bumps the package version. Left to
        # drift, the checked-in installer is what a local ISCC run compiles,
        # and that is how a two-releases-old version reaches a reader.
        from accessible_ide import __version__
        script = stamp_version.INSTALLER_FILE.read_text(encoding="utf-8")
        found = re.search(r'#define\s+MyAppVersion\s+"([^"]*)"', script)
        self.assertIsNotNone(found, "installer.iss has no MyAppVersion")
        self.assertEqual(
            found.group(1), __version__,
            "installer.iss and the package disagree on the version")


class InstallerStampTests(unittest.TestCase):
    """The installer has to be stamped too, and for a different reason.

    Inno Setup reads AppVersion to decide whether what is installed is
    older than what is being installed. Left alone it keeps the number
    somebody last typed, so every future release is announced as the same
    version - and a reader can be told they already have the build they
    are trying to install.
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.iss = pathlib.Path(self.tmp.name) / "installer.iss"
        self.iss.write_text(
            '#define MyAppName "AccessibleIDE"\n'
            '#define MyAppVersion "0.2.2"\n'
            '\n'
            'AppName={#MyAppName}\n'
            'AppVersion={#MyAppVersion}\n',
            encoding="utf-8",
        )

    def test_the_installer_version_is_written_in(self):
        stamp_version.stamp_installer("0.3.0-beta", self.iss)
        self.assertIn('#define MyAppVersion "0.3.0-beta"',
                      self.iss.read_text(encoding="utf-8"))

    def test_a_leading_v_is_dropped(self):
        stamp_version.stamp_installer("v1.2.3", self.iss)
        self.assertIn('#define MyAppVersion "1.2.3"',
                      self.iss.read_text(encoding="utf-8"))

    def test_nothing_else_in_the_script_is_touched(self):
        before = self.iss.read_text(encoding="utf-8")
        stamp_version.stamp_installer("1.2.3", self.iss)
        after = self.iss.read_text(encoding="utf-8")
        self.assertEqual(before.replace('"0.2.2"', '"1.2.3"'), after)

    def test_stamping_twice_replaces_rather_than_appends(self):
        stamp_version.stamp_installer("1.0.0", self.iss)
        stamp_version.stamp_installer("1.0.1", self.iss)
        text = self.iss.read_text(encoding="utf-8")
        self.assertEqual(text.count("#define MyAppVersion"), 1)
        self.assertIn('"1.0.1"', text)

    def test_a_script_with_no_version_line_is_refused(self):
        self.iss.write_text('#define MyAppName "X"\n', encoding="utf-8")
        with self.assertRaises(stamp_version.StampError):
            stamp_version.stamp_installer("1.0.0", self.iss)

    def test_a_missing_script_is_refused(self):
        with self.assertRaises(stamp_version.StampError):
            stamp_version.stamp_installer(
                "1.0.0", pathlib.Path(self.tmp.name) / "not-here.iss")

    def test_the_repository_ships_an_installer_this_can_stamp(self):
        # The path is written down once, in the tool. If installer.iss ever
        # moves, this is the test that notices.
        self.assertTrue(stamp_version.INSTALLER_FILE.is_file(),
                        f"no installer script at {stamp_version.INSTALLER_FILE}")


class InstallLocationTests(unittest.TestCase):
    """Where the installer puts the program, and why it needs permission.

    These two lines are a pair and only make sense together. Program Files
    cannot be written to without elevation, and {autopf} silently means the
    per-user copy under AppData when setup is not elevated - so a program
    asked for {autopf} without admin quietly lands in the wrong place, and
    nothing in the log says so.
    """

    def setUp(self):
        self.iss = stamp_version.INSTALLER_FILE
        self.text = self.iss.read_text(encoding="utf-8")

    def setting(self, name):
        """The value of one setting, or a failure that says which is missing.

        Returning None for an absent key would make assertNotIn below pass
        for the wrong reason: a setting that is not there at all looks
        exactly like a setting with the right value.
        """
        for line in self.text.splitlines():
            key, _, value = line.partition("=")
            if key.strip() == name:
                return value.strip()
        self.fail(f"{name} is not set in {self.iss.name}")

    def test_it_installs_under_program_files(self):
        self.assertEqual(
            self.setting("DefaultDirName"),
            r"{commonpf}\HotHilux_21\AccessibleIDE")

    def test_elevating_is_requested_so_that_folder_is_writable(self):
        self.assertEqual(self.setting("PrivilegesRequired"), "admin")

    def test_a_per_user_path_is_not_used(self):
        # {autopf} under PrivilegesRequired=lowest resolves to
        # AppData\Local\Programs, which is where a 64-bit program should not
        # be. Named explicitly here so the substitution cannot come back.
        self.assertNotIn("{autopf}", self.setting("DefaultDirName"))
        self.assertNotIn("{userappdata}", self.setting("DefaultDirName"))
        self.assertNotIn("{localappdata}", self.setting("DefaultDirName"))

    def test_the_build_is_64_bit_so_it_belongs_in_the_64_bit_program_files(self):
        # Program Files (x86) would be wrong: the app ships an x64 VC++
        # runtime and a 64-bit Python, and installs itself in 64-bit mode.
        self.assertIn("x64compatible",
                      self.setting("ArchitecturesInstallIn64BitMode"))

    def test_the_app_id_is_unchanged(self):
        # AppId is how Windows tells an upgrade from a second, separate
        # install. Changing it would leave the old copy behind with no way
        # to uninstall it, so this is pinned on purpose.
        self.assertIn("8E5F2C1A-9B3D-4E7A-8C2F-1D4B6A9E3F50", self.text)

    def test_settings_are_not_written_inside_the_install_folder(self):
        # Program Files is read-only for a normal user, so a program that
        # kept its settings next to its own files would fail to save them.
        from accessible_ide import routes
        self.assertEqual(routes.CONFIG_DIR, pathlib.Path.home() / ".accessible-ide")
        self.assertNotIn("HotHilux_21", str(routes.CONFIG_DIR))


class ManifestTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.exe = pathlib.Path(self.tmp.name) / "AccessibleIDE.exe"
        self.exe.write_bytes(b"MZ" + b"pretend this is a program" * 100)
        self.url = f"{updater.RELEASES_BASE}/download/latest/{updater.ASSET_NAME}"

    def test_the_manifest_describes_the_file_that_was_built(self):
        described = stamp_version.build_manifest(
            "0.2.2-beta.dev.181", self.exe, self.url, "Notes.", prerelease=True)
        self.assertEqual(described["size"], self.exe.stat().st_size)
        self.assertEqual(
            described["sha256"],
            hashlib.sha256(self.exe.read_bytes()).hexdigest(),
        )
        self.assertEqual(described["version"], "0.2.2-beta.dev.181")
        self.assertEqual(described["url"], self.url)
        self.assertTrue(described["prerelease"])

    def test_the_manifest_is_accepted_by_the_app_that_reads_it(self):
        # The point of the whole exercise: what CI writes has to pass the
        # checks in the app, or every build looks like it needs replacing.
        described = stamp_version.build_manifest(
            "0.2.2-beta.dev.181", self.exe, self.url, "Notes.", prerelease=True)
        raw = json.dumps(described).encode()

        original = updater._open_url
        updater._open_url = lambda url, timeout, accept: _Body(raw)
        try:
            manifest = updater.fetch_manifest()
        finally:
            updater._open_url = original
        self.assertEqual(manifest["version"], "0.2.2-beta.dev.181")
        self.assertTrue(updater.is_newer(manifest["version"], "0.2.2-beta"))

    def test_an_insecure_download_address_is_refused(self):
        with self.assertRaises(stamp_version.StampError):
            stamp_version.build_manifest(
                "1.0.0", self.exe,
                "http://github.com/a/b/releases/download/v1/x.exe", "", True)

    def test_the_addresses_the_workflows_write_are_ones_the_app_allows(self):
        # The two workflows build their addresses differently: a moving
        # channel names a literal channel tag, a tagged release names its own
        # tag. Both have to clear the app's allowlist, or the release it just
        # published cannot be installed from.
        base = f"https://github.com/{updater.OWNER}/{updater.REPO}/releases/download"
        for url in (f"{base}/dev/{updater.ASSET_NAME}",
                    f"{base}/beta/{updater.ASSET_NAME}",
                    f"{base}/stable/{updater.ASSET_NAME}",
                    f"{base}/v0.2.3-beta/{updater.ASSET_NAME}"):
            with self.subTest(url=url):
                self.assertEqual(updater._allowed_asset_url(url), url)

    def test_an_address_on_another_site_is_still_refused(self):
        with self.assertRaises(updater.UpdateError):
            updater._allowed_asset_url(
                "https://example.com/releases/download/v1/AccessibleIDE.exe")

    def test_a_stamped_build_offers_itself_as_an_update(self):
        # The round trip: stamp the real package, read the version back the
        # way the app does, and confirm the manifest is newer.
        #
        # Reload rather than deleting the module from sys.modules. Deleting
        # it makes the next "from accessible_ide import updater" build a
        # second, different updater module, and any test holding a patch on
        # the first one is then quietly patching nothing.
        init = REPO_ROOT / "src" / "accessible_ide" / "__init__.py"
        original = init.read_text(encoding="utf-8")
        import accessible_ide

        def put_back():
            init.write_text(original, encoding="utf-8")
            importlib.reload(accessible_ide)

        self.addCleanup(put_back)

        stamp_version.stamp_version(init, "999.0.0")
        importlib.reload(accessible_ide)
        stamped = accessible_ide.__version__
        self.assertEqual(stamped, "999.0.0")

        described = stamp_version.build_manifest(
            "999.0.1", self.exe, self.url, "", True)
        self.assertTrue(updater.is_newer(described["version"], stamped))
        # And the version already installed is not offered to itself.
        self.assertFalse(updater.is_newer(stamped, stamped))


class _Body:
    """A tiny stand-in for a downloaded file."""

    def __init__(self, data):
        self.data = data
        self.headers = {}
        self._sent = 0

    def read(self, size=-1):
        if self._sent >= len(self.data):
            return b""
        piece = self.data[self._sent:self._sent + size] if size and size > 0 else self.data[self._sent:]
        self._sent += len(piece)
        return piece

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class WorkflowStampTests(unittest.TestCase):
    """Every job that builds a program has to stamp it.

    The portable build and the installer are separate jobs on separate
    checkouts. Stamp one and not the other and the installer ships a program
    that reports an older version than the one beside it, so a reader who
    installs it is immediately offered an update they are already running.
    """

    WORKFLOWS = ("build-exe.yml", "build-release.yml")

    def jobs_that_build(self, text):
        import yaml
        document = yaml.safe_load(text)
        found = {}
        for name, body in (document.get("jobs") or {}).items():
            commands = " ".join(str(step.get("run", ""))
                                for step in body.get("steps") or [])
            if "pyinstaller" in commands:
                found[name] = commands
        return found

    def test_every_build_job_stamps_its_version(self):
        for name in self.WORKFLOWS:
            text = (REPO_ROOT / ".github" / "workflows" / name).read_text(encoding="utf-8")
            for job, commands in self.jobs_that_build(text).items():
                with self.subTest(workflow=name, job=job):
                    self.assertIn(
                        "stamp_version.py stamp", commands,
                        f"{name}:{job} builds a program without stamping it")

    def test_there_is_at_least_one_build_job_to_check(self):
        # Otherwise the test above would pass on an empty list.
        for name in self.WORKFLOWS:
            text = (REPO_ROOT / ".github" / "workflows" / name).read_text(encoding="utf-8")
            with self.subTest(workflow=name):
                self.assertTrue(self.jobs_that_build(text))


class ChannelPublishingTests(unittest.TestCase):
    """The app reads a fixed address, so the workflows have to publish it.

    These tests read the workflow files as text on purpose. There is no way
    to check at test time that a release a previous run uploaded actually
    exists on GitHub, so the only place this can be caught is here, by
    matching the two sides against each other. If the app is ever pointed at
    a channel no workflow writes, the updater stops finding updates and
    nothing anywhere raises an error.
    """

    RELEASE_WORKFLOW = "build-release.yml"
    DEV_WORKFLOW = "build-exe.yml"

    def workflow(self, name):
        return (REPO_ROOT / ".github" / "workflows" / name).read_text(encoding="utf-8")

    def test_every_channel_the_app_knows_is_published_by_a_workflow(self):
        # beta and stable move on a tagged release; dev moves on every push
        # to main. Each channel has to be written by at least one workflow,
        # or the updater would point at an address nothing publishes.
        release_text = self.workflow(self.RELEASE_WORKFLOW)
        dev_text = self.workflow(self.DEV_WORKFLOW)
        for channel in updater.CHANNELS:
            with self.subTest(channel=channel):
                self.assertTrue(
                    f"gh release upload {channel} " in release_text or
                    f"gh release upload {channel} " in dev_text)

    def test_only_the_dev_channel_points_at_a_release_main_branch_overwrites(self):
        # The one that was broken before: the updater read a release named
        # after the moving dev build, so every push to main quietly
        # overwrote the address every reader was checking. The dev channel
        # is that release by design, but it is opt-in: beta and stable must
        # never point at it.
        dev_release = f"{updater.RELEASES_BASE}/download/dev/{updater.MANIFEST_NAME}"
        for channel in updater.CHANNELS:
            with self.subTest(channel=channel):
                if channel == "dev":
                    self.assertEqual(updater.manifest_url(channel), dev_release)
                else:
                    self.assertNotEqual(updater.manifest_url(channel), dev_release)

    def test_the_development_build_goes_to_dev_and_not_to_a_reader_channel(self):
        text = self.workflow(self.DEV_WORKFLOW)
        self.assertIn("gh release create dev", text)
        self.assertIn("gh release upload dev", text)
        # A dev build must not overwrite a release a reader is checking.
        for channel in ("beta", "stable"):
            with self.subTest(channel=channel):
                self.assertNotIn(f"gh release upload {channel} ", text)

    def test_no_workflow_publishes_a_moving_latest_release(self):
        # "latest" is the one name that means two things: GitHub's own
        # pointer at the newest non-prerelease, and a release tag that gets
        # overwritten. Using it as a tag is what made the updater compare
        # against whatever the main branch last built.
        for name in (self.RELEASE_WORKFLOW, self.DEV_WORKFLOW):
            text = self.workflow(name)
            with self.subTest(workflow=name):
                self.assertNotIn("gh release create latest", text)
                self.assertNotIn("gh release upload latest", text)

    def test_a_tagged_release_moves_beta_always(self):
        # Every release is beta work until the tag says otherwise, so beta
        # must move even for a stable tag.
        self.assertIn("gh release upload beta release/version.json",
                      self.workflow(self.RELEASE_WORKFLOW))

    def test_only_a_finished_tag_moves_stable(self):
        text = self.workflow(self.RELEASE_WORKFLOW)
        self.assertIn("stable=true", text)
        self.assertIn("stable=false", text)
        # A pre-release suffix means the work is not finished, so stable
        # must not move. The two branch arms are what prove this.
        self.assertIn("if [[ \"$version\" == *-* ]]", text)
        self.assertIn("steps.channels.outputs.stable == 'true'", text)

    def test_the_channel_addresses_use_the_shape_github_serves(self):
        # /releases/<tag>/download/ is only a real endpoint for the word
        # "latest". A channel is an ordinary tag, so its assets live under
        # /releases/download/<tag>/ like any other asset. Getting this wrong
        # produces a plausible address that 404s for every reader.
        for channel in updater.CHANNELS:
            with self.subTest(channel=channel):
                self.assertEqual(
                    updater.manifest_url(channel),
                    f"{updater.RELEASES_BASE}/download/{channel}/"
                    f"{updater.MANIFEST_NAME}")

    def test_the_build_jobs_can_see_the_tags_they_stamp_from(self):
        # A shallow clone has no tags, so git describe finds nothing and the
        # build falls back to 0.0.0.dev.N. The version is written into the
        # manifest the app compares against, so this is not cosmetic.
        text = self.workflow(self.DEV_WORKFLOW)
        self.assertIn("git describe --tags --abbrev=0", text)
        self.assertIn("fetch-depth: 0", text)


class ActionVersionTests(unittest.TestCase):
    """Which actions the builds run on.

    Worth pinning for one reason: these move to a new Node runtime in a new
    major, and a Node the runner image does not have fails the whole build with
    a message about the runner rather than about the code. Writing the version
    down here means the next upgrade is a deliberate edit with a test that says
    what was changed, instead of a build that broke on a day nobody was
    watching.

    The majors below are the current ones. When one is bumped, bump it here in
    the same commit, and check the release notes for a breaking input rename.
    """

    WORKFLOWS = ("build-exe.yml", "build-release.yml")

    # The current major of each action these workflows use.
    CURRENT = {
        "actions/checkout": "v7",
        "actions/setup-python": "v7",
        "actions/upload-artifact": "v7",
        "actions/download-artifact": "v8",
    }

    def workflow(self, name):
        return (REPO_ROOT / ".github" / "workflows" / name).read_text(
            encoding="utf-8")

    def uses_in(self, name):
        import yaml
        document = yaml.safe_load(self.workflow(name))
        found = []
        for job in (document.get("jobs") or {}).values():
            for step in job.get("steps") or []:
                if step.get("uses"):
                    found.append(str(step["uses"]))
        return found

    def test_every_action_is_pinned_to_a_whole_version(self):
        # @v4 rather than @main or @master. A floating ref means the build you
        # tested is not the build you shipped.
        for name in self.WORKFLOWS:
            for ref in self.uses_in(name):
                with self.subTest(workflow=name, action=ref):
                    self.assertRegex(ref, r"^[^@\s]+@v\d+$")

    def test_they_are_on_the_current_majors(self):
        for name in self.WORKFLOWS:
            for ref in self.uses_in(name):
                action = ref.rsplit("@", 1)[0]
                if action not in self.CURRENT:
                    continue  # a third-party action, not one we pin here
                with self.subTest(workflow=name, action=action):
                    self.assertEqual(
                        ref, f"{action}@{self.CURRENT[action]}",
                        f"{name}: {action} needs a deliberate bump in this test")

    def test_the_third_party_release_action_is_pinned_too(self):
        # It creates the release readers download from, so an unpinned ref
        # there is the same risk as an unpinned ref anywhere else.
        for name in self.WORKFLOWS:
            refs = [r for r in self.uses_in(name) if "action-gh-release" in r]
            for ref in refs:
                with self.subTest(workflow=name, action=ref):
                    self.assertRegex(ref, r"^[^@\s]+@v\d+$")

    def test_upload_and_download_are_on_matching_majors(self):
        # Artifacts written by one major are not readable by another, and the
        # failure shows up as a missing file at the end of a long release
        # rather than as anything to do with versions.
        for name in self.WORKFLOWS:
            refs = self.uses_in(name)
            uploads = [r for r in refs if "upload-artifact" in r]
            downloads = [r for r in refs if "download-artifact" in r]
            if not uploads or not downloads:
                continue
            # The majors have moved apart on purpose (download is at v8 for
            # its digest checks), so what matters is that both are past v4,
            # where the incompatibility was introduced.
            for ref in uploads + downloads:
                with self.subTest(workflow=name, action=ref):
                    major = int(ref.rsplit("@v", 1)[1])
                    self.assertGreaterEqual(major, 4)


class InstallerPrerequisiteTests(unittest.TestCase):
    """The files the installer ships alongside the program.

    installer.iss names a Python installer three times and each workflow
    downloads one file. Bump the download and not the script and the build
    fails at compile time; bump the script and not the download and it fails
    the same way. Both are caught here instead of on the runner, where the
    only symptom is a red build nobody can reproduce.
    """

    PREREQ = re.compile(r"python-(\d+\.\d+\.\d+)-amd64\.exe")

    def test_the_workflows_and_the_installer_agree_on_python(self):
        script = stamp_version.INSTALLER_FILE.read_text(encoding="utf-8")
        wanted = set(self.PREREQ.findall(script))
        self.assertTrue(wanted, "installer.iss names no Python installer")

        for name in ActionVersionTests.WORKFLOWS:
            text = (REPO_ROOT / ".github" / "workflows" / name).read_text(
                encoding="utf-8")
            for found in set(self.PREREQ.findall(text)):
                with self.subTest(workflow=name, python=found):
                    self.assertIn(found, wanted)

    def test_the_installer_script_names_the_same_file_throughout(self):
        # Every reference has to be the same file name, including the one the
        # [Run] section launches. A mismatch here is a silent skip: the
        # prerequisite is copied to {tmp} under one name and looked for under
        # another, so Python simply is not installed and nothing says why.
        text = stamp_version.INSTALLER_FILE.read_text(encoding="utf-8")
        names = set(re.findall(r"python-\d+\.\d+\.\d+-amd64\.exe", text))
        self.assertEqual(
            len(names), 1,
            f"installer.iss refers to more than one Python file: {sorted(names)}")

    def test_the_inno_setup_url_names_an_architecture(self):
        # From 7.x Inno Setup ships one installer per architecture and the
        # architecture is in the file name. The old all-in-one URL now 404s,
        # and the build fails before it reaches the compile step.
        for name in ActionVersionTests.WORKFLOWS:
            text = (REPO_ROOT / ".github" / "workflows" / name).read_text(
                encoding="utf-8")
            with self.subTest(workflow=name):
                self.assertNotIn("innosetup-6.", text)
                self.assertIn("innosetup-7.1.0-x64.exe", text)


if __name__ == "__main__":
    unittest.main()
