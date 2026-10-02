"""Tests for the three package routes and the two ends that use them.

The rules these enforce are the ones a reader never sees and would be badly
served by their absence:

- the list says what is installed and whether installing is possible at all,
  because a button that always fails is worse than no button;
- installing is refused on the hosted copy, and behind the same access code and
  rate limit as running code, because installing changes the machine;
- a failure comes back as a reason the interface has words for, never as pip's
  output;
- a newly installed or newly removed package is not visible to a shell that has
  already imported the old world, so the session is restarted;
- a bad name is a 400 and a pip failure is a 502, so the two are told apart.

Run with:  PYTHONPATH=src python -m unittest tests.test_packages_api
"""

import os
import pathlib
import sys
import unittest
from unittest import mock

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = str(REPO_ROOT / "src")
if SRC not in sys.path:
    sys.path.append(SRC)

from accessible_ide import create_app, routes  # noqa: E402


class Base(unittest.TestCase):
    def setUp(self):
        # ACCESS_CODE is read once at import time and a developer machine may
        # have one set, which would gate every test below for the wrong reason.
        self._saved = routes.ACCESS_CODE
        routes.ACCESS_CODE = ""
        app = create_app()
        app.config["TESTING"] = True
        self.client = app.test_client()
        self.addCleanup(self._restore)

    def _restore(self):
        routes.ACCESS_CODE = self._saved

    def post(self, path, payload=None):
        return self.client.post(path, json=payload or {})

    def refuse(self, path, payload=None):
        """Open every gate, so a test can reach the real work behind them."""
        with mock.patch.object(routes, "access_code_ok", return_value=True), \
             mock.patch.object(routes, "rate_limited", return_value=False), \
             mock.patch.object(routes, "SANDBOX", False):
            return self.post(path, payload)


class Listing(Base):
    def test_it_says_what_is_installed(self):
        with mock.patch.object(routes.packages, "installed", return_value=[
                routes.packages.PackageInfo("toml", "0.10.2", "toml")]), \
             mock.patch.object(routes.packages, "pip_available", return_value=True):
            res = self.client.get("/api/packages")
        self.assertEqual(res.status_code, 200)
        body = res.get_json()
        self.assertEqual(body["installed"],
                         [{"name": "toml", "version": "0.10.2", "module": "toml"}])
        self.assertTrue(body["can_install"])

    def test_an_empty_machine_lists_nothing_without_failing(self):
        # Before anything is installed this is the normal state, not an error,
        # and the panel has to open onto it.
        with mock.patch.object(routes.packages, "installed", return_value=[]), \
             mock.patch.object(routes.packages, "pip_available", return_value=True):
            res = self.client.get("/api/packages")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.get_json()["installed"], [])

    def test_it_says_when_installing_is_not_possible(self):
        # A copy with no pip. Saying so up front is what stops the reader
        # finding out by pressing a button that does nothing.
        with mock.patch.object(routes.packages, "installed", return_value=[]), \
             mock.patch.object(routes.packages, "pip_available", return_value=False):
            res = self.client.get("/api/packages")
        self.assertFalse(res.get_json()["can_install"])

    def test_the_hosted_copy_cannot_install_even_with_pip(self):
        with mock.patch.object(routes.packages, "installed", return_value=[]), \
             mock.patch.object(routes.packages, "pip_available", return_value=True), \
             mock.patch.object(routes, "SANDBOX", True):
            res = self.client.get("/api/packages")
        self.assertFalse(res.get_json()["can_install"])

    def test_it_does_not_look_for_pip_twice_per_open(self):
        # pip_available probes real interpreters, so it is the slowest thing in
        # the panel. One call per load is the bar.
        with mock.patch.object(routes.packages, "installed", return_value=[]), \
             mock.patch.object(routes.packages, "pip_available",
                               return_value=True) as available:
            self.client.get("/api/packages")
        self.assertEqual(available.call_count, 1)


class Installing(Base):
    def test_a_name_is_installed_and_the_result_is_named(self):
        made = routes.packages.PackageInfo("toml", "0.10.2", "toml")
        with mock.patch.object(routes.packages, "install", return_value=made) as install:
            res = self.refuse("/api/packages/install", {"name": "toml"})
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.get_json()["success"])
        install.assert_called_once_with("toml")

    def test_a_missing_module_can_be_installed_by_its_package_name(self):
        # What the offer sends: the module the code asked for has already been
        # turned into the package that provides it.
        made = routes.packages.PackageInfo("Pillow", "10.0.0", "PIL")
        with mock.patch.object(routes.packages, "install", return_value=made) as install:
            res = self.refuse("/api/packages/install",
                              {"name": "Pillow", "session": ""})
        self.assertEqual(res.status_code, 200)
        install.assert_called_once_with("Pillow")

    def test_a_bad_name_is_the_readers_fault_and_says_so(self):
        error = routes.packages.PackageError("bad_name")
        with mock.patch.object(routes.packages, "install", side_effect=error):
            res = self.refuse("/api/packages/install", {"name": "../evil"})
        self.assertEqual(res.status_code, 400)
        body = res.get_json()
        self.assertFalse(body["success"])
        self.assertEqual(body["reason"], "bad_name")
        # A sentence in the reader's language, not a reason code alone.
        self.assertTrue(body["error"].strip())
        self.assertNotIn("bad_name", body["error"])

    def test_a_pip_failure_is_not_the_readers_fault(self):
        # 502 rather than 400: the name may be perfectly good and the network
        # may be down. The distinction matters to anything retrying.
        error = routes.packages.PackageError("install_failed",
                                             "ERROR: no matching distribution")
        with mock.patch.object(routes.packages, "install", side_effect=error):
            res = self.refuse("/api/packages/install", {"name": "toml"})
        self.assertEqual(res.status_code, 502)
        self.assertEqual(res.get_json()["reason"], "install_failed")

    def test_pips_own_words_never_reach_the_reader(self):
        # The detail is for the log. A resolver traceback is not an error
        # message a beginner can do anything with.
        error = routes.packages.PackageError(
            "install_failed",
            "ERROR: Could not find a version that satisfies the requirement toml")
        with mock.patch.object(routes.packages, "install", side_effect=error):
            res = self.refuse("/api/packages/install", {"name": "toml"})
        self.assertNotIn("Could not find a version", res.get_json()["error"])

    def test_no_pip_is_its_own_sentence(self):
        error = routes.packages.PackageError("no_pip")
        with mock.patch.object(routes.packages, "install", side_effect=error):
            res = self.refuse("/api/packages/install", {"name": "toml"})
        self.assertEqual(res.get_json()["reason"], "no_pip")
        self.assertTrue(res.get_json()["error"].strip())

    def test_a_timeout_is_reported_rather_than_hanging(self):
        error = routes.packages.PackageError("timeout")
        with mock.patch.object(routes.packages, "install", side_effect=error):
            res = self.refuse("/api/packages/install", {"name": "huge"})
        self.assertEqual(res.get_json()["reason"], "timeout")

    def test_it_is_refused_without_the_access_code(self):
        # The same gate as running code, in the same shape, so the page's
        # existing code prompt handles it.
        routes.ACCESS_CODE = "letmein"
        with mock.patch.object(routes.packages, "install") as install:
            res = self.post("/api/packages/install", {"name": "toml"})
        self.assertEqual(res.status_code, 403)
        self.assertTrue(res.get_json()["code_required"])
        install.assert_not_called()

    def test_it_is_rate_limited_like_running_code(self):
        with mock.patch.object(routes, "rate_limited", return_value=True), \
             mock.patch.object(routes.packages, "install") as install:
            res = self.post("/api/packages/install", {"name": "toml"})
        self.assertEqual(res.status_code, 429)
        install.assert_not_called()

    def test_the_hosted_copy_refuses(self):
        with mock.patch.object(routes, "SANDBOX", True), \
             mock.patch.object(routes.packages, "install") as install:
            res = self.post("/api/packages/install", {"name": "toml"})
        self.assertEqual(res.status_code, 403)
        install.assert_not_called()

    def test_an_empty_request_installs_nothing(self):
        # The real validation runs here rather than a mock, because the claim is
        # that an absent name is rejected before pip is ever reached.
        with mock.patch.object(routes.packages, "_run_pip") as run_pip:
            res = self.refuse("/api/packages/install", {})
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.get_json()["reason"], "bad_name")
        run_pip.assert_not_called()

    def test_it_is_not_a_get(self):
        # Nothing that changes a machine answers to a link somebody can click.
        self.assertEqual(self.client.get("/api/packages/install").status_code, 405)


class ShellRestart(Base):
    """A shell holds every module it has imported for the life of the process.
    Installing or removing a package underneath it leaves the reader pressing
    Run and seeing the old answer, which reads as a broken install."""

    def test_an_install_restarts_the_shell_it_names(self):
        made = routes.packages.PackageInfo("toml", "0.10.2", "toml")
        session = mock.Mock()
        with mock.patch.object(routes.packages, "install", return_value=made), \
             mock.patch.object(routes.shell_registry, "get", return_value=session):
            res = self.refuse("/api/packages/install",
                              {"name": "toml", "session": "abc"})
        self.assertEqual(res.status_code, 200)
        session.reset.assert_called_once()

    def test_a_removal_restarts_it_too(self):
        # Otherwise a removed package keeps importing from the module cache and
        # the reader is told it is gone while their program still runs.
        session = mock.Mock()
        with mock.patch.object(routes.packages, "uninstall", return_value=True), \
             mock.patch.object(routes.packages, "installed", return_value=[]), \
             mock.patch.object(routes.shell_registry, "get", return_value=session):
            res = self.refuse("/api/packages/uninstall",
                              {"name": "toml", "session": "abc"})
        self.assertEqual(res.status_code, 200)
        session.reset.assert_called_once()

    def test_a_shell_that_will_not_restart_does_not_fail_the_install(self):
        # The package is on disk either way. Turning a successful install into
        # an error because the shell could not be reset would be worse than a
        # reader pressing Run once more.
        session = mock.Mock()
        session.reset.side_effect = routes.ShellError("gone")
        made = routes.packages.PackageInfo("toml", "0.10.2", "toml")
        with mock.patch.object(routes.packages, "install", return_value=made), \
             mock.patch.object(routes.shell_registry, "get", return_value=session):
            res = self.refuse("/api/packages/install",
                              {"name": "toml", "session": "abc"})
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.get_json()["success"])

    def test_an_unknown_session_is_not_an_error(self):
        # The panel works whether or not the shell is open.
        made = routes.packages.PackageInfo("toml", "0.10.2", "toml")
        with mock.patch.object(routes.packages, "install", return_value=made), \
             mock.patch.object(routes.shell_registry, "get", return_value=None):
            res = self.refuse("/api/packages/install",
                              {"name": "toml", "session": "gone"})
        self.assertEqual(res.status_code, 200)

    def test_no_session_is_fine(self):
        # The one-shot runner has no session at all, and installing from the
        # panel before opening a shell has to work the same way.
        made = routes.packages.PackageInfo("toml", "0.10.2", "toml")
        with mock.patch.object(routes.packages, "install", return_value=made), \
             mock.patch.object(routes.shell_registry, "get") as get:
            res = self.refuse("/api/packages/install", {"name": "toml"})
        self.assertEqual(res.status_code, 200)
        get.assert_not_called()


class Removing(Base):
    def test_a_removed_package_is_reported_and_the_list_returned(self):
        left = [routes.packages.PackageInfo("Pillow", "10.0.0", "PIL")]
        with mock.patch.object(routes.packages, "uninstall", return_value=True) as remove, \
             mock.patch.object(routes.packages, "installed", return_value=left):
            res = self.refuse("/api/packages/uninstall", {"name": "toml"})
        self.assertEqual(res.status_code, 200)
        body = res.get_json()
        self.assertTrue(body["success"])
        remove.assert_called_once_with("toml")
        # The refreshed list travels back so the page does not have to guess
        # what the list looks like now.
        self.assertEqual([p["name"] for p in body["installed"]], ["Pillow"])

    def test_a_package_that_was_not_there_is_not_an_error(self):
        # The reader asked for it to go; it had already gone. That is the
        # outcome they asked for, and a red message would suggest otherwise.
        with mock.patch.object(routes.packages, "uninstall", return_value=False), \
             mock.patch.object(routes.packages, "installed", return_value=[]):
            res = self.refuse("/api/packages/uninstall", {"name": "numpy"})
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.get_json()["success"])

    def test_a_bad_name_is_refused_before_anything_is_deleted(self):
        error = routes.packages.PackageError("bad_name")
        with mock.patch.object(routes.packages, "uninstall", side_effect=error):
            res = self.refuse("/api/packages/uninstall", {"name": "../.."})
        self.assertEqual(res.status_code, 400)

    def test_it_is_refused_without_the_access_code(self):
        routes.ACCESS_CODE = "letmein"
        with mock.patch.object(routes.packages, "uninstall") as remove:
            res = self.post("/api/packages/uninstall", {"name": "toml"})
        self.assertEqual(res.status_code, 403)
        remove.assert_not_called()

    def test_the_hosted_copy_refuses(self):
        with mock.patch.object(routes, "SANDBOX", True), \
             mock.patch.object(routes.packages, "uninstall") as remove:
            res = self.post("/api/packages/uninstall", {"name": "toml"})
        self.assertEqual(res.status_code, 403)
        remove.assert_not_called()

    def test_an_empty_request_removes_nothing(self):
        # Real validation runs, so this proves the name was refused before any
        # deletion was attempted rather than proving a mock was not called.
        res = self.refuse("/api/packages/uninstall", {})
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.get_json()["reason"], "bad_name")


class MissingImportOffers(Base):
    """What the runner and the shell say about a failed import."""

    def _shell_reply(self, error, error_type):
        session = mock.Mock()
        session.exec.return_value = {
            "output": "", "error": error, "error_type": error_type,
        }
        with mock.patch.object(routes.shell_registry, "get", return_value=session), \
             mock.patch.object(routes, "check_sandbox", return_value=(True, "")):
            return self.refuse("/api/shell/exec", {"code": "import PIL",
                                                   "session": "abc"})

    def test_the_shell_names_the_module_and_its_package(self):
        body = self._shell_reply(
            "ModuleNotFoundError: No module named 'PIL'",
            "ModuleNotFoundError").get_json()
        self.assertEqual(body["missing_module"], "PIL")
        self.assertEqual(body["missing_package"], "Pillow")
        # The error is still translated for the reader; the offer is extra.
        self.assertTrue(body["error"].strip())

    def test_an_ordinary_error_offers_nothing(self):
        # The case that matters most: a NameError must not produce a package
        # name, or the app offers to install something because of a typo.
        body = self._shell_reply(
            "NameError: name 'boom' is not defined",
            "NameError").get_json()
        self.assertEqual(body["missing_module"], "")
        self.assertEqual(body["missing_package"], "")

    def test_a_missing_submodule_offers_the_package(self):
        body = self._shell_reply(
            "ModuleNotFoundError: No module named 'PIL.Image'",
            "ModuleNotFoundError").get_json()
        # "PIL.Image" is not on PyPI. The package is what has to be installed.
        self.assertEqual(body["missing_module"], "PIL")
        self.assertEqual(body["missing_package"], "Pillow")

    def test_the_runner_reports_a_missing_import_too(self):
        # Not just the shell. Somebody who presses Run and gets a traceback
        # gets the same offer as somebody who typed into the shell.
        failure = mock.Mock(returncode=1, stdout="", stderr=(
            "Traceback (most recent call last):\n"
            "ModuleNotFoundError: No module named 'requests'\n"))
        with mock.patch.object(routes.subprocess, "run", return_value=failure), \
             mock.patch.object(routes, "check_sandbox", return_value=(True, "")):
            body = self.refuse("/api/run", {"code": "import requests"}).get_json()
        self.assertEqual(body["missing_module"], "requests")
        self.assertEqual(body["missing_package"], "requests")

    def test_a_successful_run_offers_nothing(self):
        ok = mock.Mock(returncode=0, stdout="hi\n", stderr="")
        with mock.patch.object(routes.subprocess, "run", return_value=ok), \
             mock.patch.object(routes, "check_sandbox", return_value=(True, "")):
            body = self.refuse("/api/run", {"code": "print(1)"}).get_json()
        self.assertEqual(body["missing_module"], "")
        self.assertEqual(body["missing_package"], "")


class ThePathIsPassedDown(Base):
    """A package that installs but cannot be imported is the failure this
    whole feature would otherwise have, so the path is checked at both ends."""

    def test_the_runner_child_gets_the_packages_folder_on_its_path(self):
        # A real directory, because the route only adds a path that exists.
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            pkgs = pathlib.Path(tmp) / "packages"
            pkgs.mkdir()
            ok = mock.Mock(returncode=0, stdout="", stderr="")
            with mock.patch.object(routes.packages, "python_path",
                                   return_value=str(pkgs)), \
                 mock.patch.object(routes.subprocess, "run", return_value=ok) as run, \
                 mock.patch.object(routes, "check_sandbox", return_value=(True, "")):
                self.refuse("/api/run", {"code": "print(1)"})
        env = run.call_args.kwargs["env"]
        self.assertIn(str(pkgs), env["PYTHONPATH"])

    def test_an_existing_python_path_is_kept_not_replaced(self):
        # Something else on the machine may rely on it. Adding to it costs
        # nothing; overwriting it breaks things nobody in this app knows about.
        existing = os.pathsep.join(["C:/already/here", "D:/also/here"])
        with mock.patch.dict(os.environ, {"PYTHONPATH": existing}):
            env = routes._runner_env()
        self.assertIn("C:/already/here", env["PYTHONPATH"])
        self.assertIn("D:/also/here", env["PYTHONPATH"])

    def test_a_folder_that_is_not_there_yet_is_not_added(self):
        # Before the first install there is no packages folder. Pointing at a
        # path that does not exist is harmless but wrong, and it hides the
        # difference between installed and not.
        with mock.patch.dict(os.environ, {}, clear=True), \
             mock.patch.object(routes.packages, "python_path",
                               return_value=str(REPO_ROOT / "no-such-folder")):
            env = routes._runner_env()
        self.assertNotIn("PYTHONPATH", env)

    def test_the_readers_package_wins_over_one_elsewhere(self):
        # Prepended, not appended: a package of the same name already on the
        # machine should not shadow the one the reader just asked for.
        existing = "C:/other/site-packages"
        with mock.patch.dict(os.environ, {"PYTHONPATH": existing}), \
             mock.patch.object(routes.packages, "python_path",
                               return_value=str(REPO_ROOT / "pkgs")), \
             mock.patch.object(routes.os.path, "isdir", return_value=True):
            env = routes._runner_env()
        self.assertTrue(env["PYTHONPATH"].startswith(str(REPO_ROOT / "pkgs")))

    def test_the_shell_child_is_told_which_folder_to_use(self):
        # Its own variable rather than PYTHONPATH, so it cannot collide with a
        # PYTHONPATH the reader already had.
        from accessible_ide import shell as shell_module
        session = shell_module.ShellSession()
        captured = {}

        class FakePopen:
            def __init__(self, cmd, **kwargs):
                captured["cmd"] = cmd
                captured.update(kwargs)
                raise OSError("stop here")

        with mock.patch.object(shell_module.subprocess, "Popen", FakePopen), \
             mock.patch.object(shell_module.packages, "python_path",
                               return_value="C:/data/packages"):
            with self.assertRaises(OSError):
                session._spawn()
        self.assertEqual(captured["env"]["ACCESSIBLE_IDE_PACKAGES"],
                         "C:/data/packages")

    def test_the_shell_keeps_the_readers_own_pythonpath(self):
        from accessible_ide import shell as shell_module
        session = shell_module.ShellSession()
        captured = {}

        class FakePopen:
            def __init__(self, cmd, **kwargs):
                captured.update(kwargs)
                raise OSError("stop here")

        with mock.patch.dict(os.environ, {"PYTHONPATH": "C:/mine"}), \
             mock.patch.object(shell_module.subprocess, "Popen", FakePopen), \
             mock.patch.object(shell_module.packages, "python_path",
                               return_value="C:/data/packages"):
            with self.assertRaises(OSError):
                session._spawn()
        self.assertEqual(captured["env"]["PYTHONPATH"], "C:/mine")


class TheModuleIndexIsGone(unittest.TestCase):
    """The module index was replaced, not left sitting beside the new thing."""

    def test_its_routes_are_not_served(self):
        client = create_app().test_client()
        self.assertEqual(client.get("/api/modules").status_code, 404)
        self.assertEqual(client.get("/api/modules/json").status_code, 404)

    def test_its_code_is_gone_from_the_package(self):
        root = REPO_ROOT / "src" / "accessible_ide"
        leftovers = [p.name for p in root.rglob("*.py")
                     if "module_index" in p.name or "modules_data" in p.name]
        self.assertEqual(leftovers, [])

    def test_no_route_still_points_at_it(self):
        source = (REPO_ROOT / "src" / "accessible_ide" / "routes.py").read_text(
            encoding="utf-8")
        self.assertNotIn("module_index", source)
        self.assertNotIn("/api/modules", source)


if __name__ == "__main__":
    unittest.main()