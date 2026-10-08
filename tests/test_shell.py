"""Tests for the Python shell.

The rule these protect is the one that separates a shell from a runner: what
was typed five commands ago is still true now. Every test here is really asking
one of four things.

  remembering   - state survives between commands, and a mistake does not cost
                  the reader the session
  staying apart  - two readers on the hosted copy cannot see each other, and a
                  guessed id does not get you in
  letting go     - a command that hangs, or a reader who closes the panel, does
                  not leave a python.exe behind
  staying quiet  - the shell costs nothing until it is asked for, and the
                  limits that protect the hosted copy still apply to it

The process-lifetime tests are the slow ones, because they are the ones that
have actually gone wrong: an unread stderr pipe wedges the child, and on
Windows a grandchild outlives a kill that only reaches its parent. Both were
found by hand and are pinned here so they stay found.

Isolation: as in test_config_api, routes.py reads its config paths as
module-level globals, so they are repointed at a temporary directory here.
"""

import os
import pathlib
import subprocess
import sys
import tempfile
import time
import unittest
from typing import cast

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = str(REPO_ROOT / "src")
if SRC not in sys.path:
    sys.path.append(SRC)

from accessible_ide import create_app, routes, shell  # noqa: E402


def child_count():
    """How many shell children are alive, by looking for the bootstrap itself.

    Asked the OS rather than tracked in a variable, because the whole point
    of these tests is processes this process has forgotten about.
    """
    if sys.platform == "win32":
        try:
            listing = subprocess.run(
                ["wmic", "process", "get", "processid,parentprocessid,commandline"],
                capture_output=True, text=True, timeout=20, errors="replace",
            ).stdout
        except Exception:
            return -1  # wmic is gone on newer Windows; skip rather than fail
        # A venv python.exe is a redirector that spawns the real interpreter,
        # so one session can show up twice with the same command line. Count
        # only the top of each tree: a bootstrap whose parent is not itself a
        # bootstrap.
        rows = []
        for line in listing.splitlines():
            if "shell_bootstrap" not in line:
                continue
            parts = line.split()
            if len(parts) >= 2:
                rows.append((parts[-2], parts[-1]))
        parents = {pid for parent, pid in rows}
        return sum(1 for parent, pid in rows if parent not in parents)
    try:
        listing = subprocess.run(
            ["ps", "-eo", "args"], capture_output=True, text=True, timeout=20,
            errors="replace",
        ).stdout
    except Exception:
        return -1
    return sum(1 for line in listing.splitlines() if "shell_bootstrap" in line)


class ShellSessionTests(unittest.TestCase):
    """One session, and whether it behaves like a shell."""

    def setUp(self):
        self.session = shell.ShellSession(timeout=10.0)
        self.session.start()
        self.addCleanup(self.session.stop)

    def run_code(self, code):
        return self.session.exec(code)

    def test_a_bare_expression_answers_with_its_value(self):
        # The thing that makes a shell feel like a shell rather than a
        # run button: you type a thing, you get the answer back.
        self.assertEqual(self.run_code("6 * 7").get("output", "").strip(), "42")

    def test_a_variable_is_still_there_in_the_next_command(self):
        # This is the whole difference from the one-shot runner, and the one
        # thing that must never regress into it.
        self.run_code("colour = 'blue'")
        reply = self.run_code("colour")
        self.assertEqual(reply.get("output", "").strip(), "'blue'")

    def test_an_import_is_still_there_in_the_next_command(self):
        self.run_code("import math")
        self.assertEqual(self.run_code("math.sqrt(144)").get("output", "").strip(), "12.0")

    def test_a_loop_and_a_function_still_work(self):
        # The bootstrap falls back from 'single' to 'exec' for exactly this.
        # Without the fallback the first 'for' a reader types is a
        # SyntaxError and the shell looks broken.
        reply = self.run_code("for i in range(3):\n    print(i)")
        self.assertEqual(reply.get("output", "").split(), ["0", "1", "2"])
        self.assertEqual(reply.get("error"), "")

        reply = self.run_code("def double(n):\n    return n * 2")
        self.assertEqual(reply.get("error"), "")

        self.assertEqual(self.run_code("double(21)").get("output", "").strip(), "42")

    def test_a_mistake_is_explained_and_the_session_survives(self):
        reply = self.run_code("print(undefined_name)")
        self.assertIn("NameError", reply.get("error", ""))
        self.assertEqual(reply.get("error_type"), "NameError")
        # The reader has not lost the session over a typo.
        self.assertEqual(self.run_code("1 + 1").get("output", "").strip(), "2")

    def test_a_syntax_error_is_explained_and_the_session_survives(self):
        reply = self.run_code("for")
        self.assertIn("SyntaxError", reply.get("error", ""))
        self.assertEqual(self.run_code("1 + 1").get("output", "").strip(), "2")

    def test_quitting_does_not_cost_the_reader_their_session(self):
        # exit() raises SystemExit, which is not an Exception. Treating it as
        # fatal would close the shell and take every definition with it.
        reply = self.run_code("raise SystemExit")
        self.assertTrue(reply.get("error") or reply.get("error_type"))
        self.assertEqual(self.run_code("1 + 1").get("output", "").strip(), "2")

    def test_a_command_that_overruns_is_stopped_and_the_next_one_works(self):
        # No deadlock, and no half-state the reader has to reason about.
        before = child_count()
        if before < 0:
            self.skipTest("cannot count processes on this platform")
        self.assertEqual(before, 1, "the session should have exactly one child")

        with self.assertRaises(shell.ShellTimeout):
            self.run_code("while True:\n    pass")

        # The killed child is gone rather than left spinning, and the reader
        # gets a working shell back.
        time.sleep(0.5)
        self.assertLessEqual(child_count(), 1)
        self.assertEqual(self.run_code("1 + 1").get("output", "").strip(), "2")

    def test_two_lines_typed_together_answer_like_two_lines_typed_apart(self):
        # A terminal shell treats a pasted pair as two submissions and
        # answers the second. Falling back to 'exec' for anything multi-line
        # runs the code but shows no value, which reads as though the second
        # line never ran.
        reply = self.run_code("import math\nmath.factorial(5)")
        self.assertEqual(reply.get("error"), "")
        self.assertEqual(reply.get("output", "").strip(), "120")

        reply = self.run_code("total = 2\ntotal + 3")
        self.assertEqual(reply.get("output", "").strip(), "5")

        # A definition followed by a call, which is the shape a reader
        # actually pastes when they are trying something out.
        reply = self.run_code("def twice(n):\n    return n * 2\ntwice(21)")
        self.assertEqual(reply.get("output", "").strip(), "42")

    def test_showing_the_value_of_the_last_line_does_not_run_anything_twice(self):
        # The echo is not worth a line of somebody's code running twice. A
        # counter is the honest way to ask.
        self.run_code("calls = 0")
        self.run_code("def bump():\n    global calls\n    calls += 1\n    return calls")
        self.assertEqual(self.run_code("bump()").get("output", "").strip(), "1")
        self.assertEqual(self.run_code("bump()").get("output", "").strip(), "2")
        self.assertEqual(self.run_code("calls").get("output", "").strip(), "2")

    def test_a_loop_is_still_not_mistaken_for_something_to_echo(self):
        # The trailing line of a loop belongs to the loop, not to the shell,
        # so the loop's own output is the whole answer.
        reply = self.run_code("for i in range(3):\n    print(i)")
        self.assertEqual(reply.get("output", "").split(), ["0", "1", "2"])
        self.assertEqual(reply.get("error"), "")

    def test_a_reader_closing_the_panel_leaves_nothing_behind(self):
        if child_count() < 0:
            self.skipTest("cannot count processes on this platform")
        # setUp already holds one session, so the count to compare against is
        # what is there now, not zero.
        before = child_count()
        session = shell.ShellSession(timeout=10.0)
        session.start()
        session.exec("kept = 1")
        self.assertEqual(child_count(), before + 1)

        session.stop()
        time.sleep(0.5)
        self.assertEqual(
            child_count(), before,
            "closing the shell must close its process",
        )

    def test_stopping_twice_is_not_an_error(self):
        # The page stops the session on close, and the registry may have
        # evicted it first. Neither is worth showing a reader.
        self.session.stop()
        self.session.stop()

    def test_stderr_from_a_program_the_reader_started_is_shown(self):
        # The regression test for the wedge. A reader running a command that
        # starts another program is the ordinary way to fill a pipe, and
        # without a reader on the other end the child blocks on its own write
        # and the command dies at the timeout having printed nothing.
        script = pathlib.Path(tempfile.gettempdir()) / "accessible_ide_noisy_child.py"
        script.write_text(
            "import sys\n"
            "sys.stderr.write('the child said no\\n')\n"
            "sys.stderr.flush()\n",
            encoding="utf-8",
        )
        self.addCleanup(script.unlink, missing_ok=True)

        started = time.time()
        reply = self.run_code(
            "import subprocess, sys\n"
            "subprocess.run([sys.executable, %r])\n" % str(script)
        )
        # Well inside the timeout, which is what "did not wedge" means.
        self.assertLess(time.time() - started, 5.0)
        self.assertIn("the child said no", reply.get("output", ""))
        # Shown as output, not dressed up as a Python error: the child wrote
        # to its own stderr, so nothing was raised and there is no traceback
        # to translate.
        self.assertEqual(reply.get("error"), "")

    def test_a_program_that_writes_far_more_than_a_pipe_holds_still_answers(self):
        # The same wedge, past the point where the buffer is certainly full.
        # A few lines would have been swallowed; this is the size that used to
        # hang until the timeout.
        script = pathlib.Path(tempfile.gettempdir()) / "accessible_ide_loud_child.py"
        script.write_text(
            "import sys\n"
            "for _ in range(20000):\n"
            "    sys.stderr.write('a line of noise\\n')\n"
            "sys.stderr.flush()\n",
            encoding="utf-8",
        )
        self.addCleanup(script.unlink, missing_ok=True)

        started = time.time()
        reply = self.run_code(
            "import subprocess, sys\n"
            "subprocess.run([sys.executable, %r])\n" % str(script)
        )
        self.assertLess(time.time() - started, 8.0)
        self.assertIn("a line of noise", reply.get("output", ""))
        self.assertEqual(self.run_code("1 + 1").get("output", "").strip(), "2")

    def test_a_program_the_reader_started_does_not_outlive_a_timeout(self):
        # On Windows, killing the process that was spawned does not reach the
        # programs it started. Those keep the inherited pipe handles open, so
        # the reply never arrives and a later close waits on a stream another
        # thread still holds - which hangs the app rather than failing the
        # command.
        if child_count() < 0:
            self.skipTest("cannot count processes on this platform")
        with self.assertRaises(shell.ShellTimeout):
            self.run_code(
                "import subprocess, sys, time\n"
                "subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'])\n"
                "time.sleep(60)\n"
            )
        time.sleep(1.0)
        self.assertLessEqual(child_count(), 1)
        self.assertEqual(self.run_code("1 + 1").get("output", "").strip(), "2")


class ShellRegistryTests(unittest.TestCase):
    """The rules about how many sessions there may be, and who may use them."""

    def setUp(self):
        self.registry = shell.ShellRegistry(max_sessions=3, idle_seconds=300)
        self.addCleanup(self.registry.stop_all)

    def opened(self):
        """A started session, insisting it really is one.

        get() returning None is the "you are not holding a valid id" answer,
        and a test that used it without saying so would be testing nothing.
        """
        session = self.registry.get(self.registry.start())
        self.assertIsNotNone(session)
        # assertIsNotNone does not narrow the type for a reader of this file,
        # and an Optional here would push the checking onto every call below.
        return cast(shell.ShellSession, session)

    def id_of(self, session):
        for sid, candidate in self.registry._sessions.items():
            if candidate is session:
                return sid
        self.fail("that session is not in the registry")

    def test_two_readers_cannot_see_each_other(self):
        # The reason the id is a secret rather than a counter. On the hosted
        # copy a shared namespace would mean one reader can print another's
        # variables, or watch them get cleared.
        mine = self.opened()
        theirs = self.opened()

        mine.exec("secret = 'mine'")
        theirs.exec("secret = 'theirs'")

        self.assertEqual(mine.exec("secret").get("output", "").strip(), "'mine'")
        self.assertEqual(theirs.exec("secret").get("output", "").strip(), "'theirs'")

    def test_a_name_in_one_session_is_not_defined_in_the_next(self):
        first = self.opened()
        first.exec("only_here = 1")
        reply = self.opened().exec("only_here")
        self.assertIn("NameError", reply.get("error", ""))

    def test_session_ids_are_not_guessable(self):
        ids = {self.registry.start() for _ in range(5)}
        self.assertEqual(len(ids), 5, "every session needs its own id")
        for sid in ids:
            self.assertGreaterEqual(len(sid), 24)

    def test_an_unknown_or_missing_id_gets_nothing(self):
        self.assertIsNone(self.registry.get("made-up"))
        self.assertIsNone(self.registry.get(""))
        self.assertIsNone(self.registry.get(None))

    def test_the_cap_is_the_cap_and_not_the_cap_plus_one(self):
        # Evicting before inserting leaves the registry permanently one over
        # the limit: with the dict already full there is no overflow to
        # remove, and the new session then pushes it back past the cap. This
        # is a cap on processes, so being one over is the whole point of
        # having one.
        for _ in range(3):
            self.registry.start()
        self.assertEqual(self.registry.count(), 3)
        for _ in range(4):
            self.registry.start()
            self.assertLessEqual(
                self.registry.count(), 3,
                "the cap was exceeded by starting another session",
            )
        self.assertEqual(self.registry.count(), 3)

    def test_going_over_the_cap_costs_the_least_recently_used_session(self):
        first = self.registry.get(self.registry.start())
        second = self.registry.get(self.registry.start())
        third = self.registry.get(self.registry.start())
        first_id = [s for s in self.registry._sessions if self.registry._sessions[s] is first][0]

        time.sleep(0.05)
        # Touch the other two so the first is the least recently used.
        self.registry.get(second)
        self.registry.get(third)

        self.registry.start()
        self.assertIsNone(self.registry.get(first_id))
        self.assertIsNotNone(self.registry.get(
            [s for s in self.registry._sessions if self.registry._sessions[s] is second][0]
        ))

    def test_a_session_nobody_touched_is_closed(self):
        stale = shell.ShellRegistry(max_sessions=4, idle_seconds=0.2)
        self.addCleanup(stale.stop_all)
        sid = stale.start()
        self.assertIsNotNone(stale.get(sid))
        time.sleep(0.4)
        self.assertEqual(stale.evict(), 1)
        self.assertIsNone(stale.get(sid))

    def test_dropping_a_session_closes_it(self):
        sid = self.registry.start()
        self.assertTrue(self.registry.drop(sid))
        self.assertIsNone(self.registry.get(sid))
        # Dropping one that is already gone is the outcome asked for.
        self.assertFalse(self.registry.drop(sid))

    def test_stopping_everything_closes_everything(self):
        for _ in range(3):
            self.registry.start()
        self.registry.stop_all()
        self.assertEqual(self.registry.count(), 0)


class ShellRouteTests(unittest.TestCase):
    """The endpoints, and the gates the hosted copy needs around them."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self._orig_dir = routes.CONFIG_DIR
        self._orig_config = routes.CONFIG_FILE
        self._orig_access = routes.ACCESS_CODE
        self._orig_sandbox = routes.SANDBOX
        routes.CONFIG_DIR = pathlib.Path(self.tmp)
        routes.CONFIG_FILE = pathlib.Path(self.tmp) / "config.json"
        routes.ACCESS_CODE = ""
        # Matches a desktop run: the reader's own machine, no web in front.
        routes.SANDBOX = False
        # The limiter remembers by module-level dict, so it carries between
        # tests unless it is emptied. Left alone, the first few tests spend
        # the whole window's allowance and the rest are told to slow down.
        routes.RATE_LIMIT.clear()

        app = create_app()
        app.config["TESTING"] = True
        self.client = app.test_client()
        self.registry = shell.ShellRegistry(max_sessions=4, idle_seconds=300)
        self._orig_registry = routes.shell_registry
        routes.shell_registry = self.registry
        self.addCleanup(self.registry.stop_all)
        self.addCleanup(self._restore)

    def _restore(self):
        routes.CONFIG_DIR = self._orig_dir
        routes.CONFIG_FILE = self._orig_config
        routes.ACCESS_CODE = self._orig_access
        routes.SANDBOX = self._orig_sandbox
        routes.RATE_LIMIT.clear()
        routes.shell_registry = self._orig_registry

    def _sandbox(self, on):
        """Whether this run is standing in for the hosted copy."""
        routes.SANDBOX = on

    def start(self):
        response = self.client.post("/api/shell/start", json={})
        self.assertEqual(response.status_code, 200)
        return response.get_json()["session"]

    def test_the_whole_journey_works_over_http(self):
        sid = self.start()
        self.client.post("/api/shell/exec", json={"session": sid, "code": "kept = 5"})
        reply = self.client.post(
            "/api/shell/exec", json={"session": sid, "code": "kept * 2"}
        ).get_json()
        self.assertEqual(reply["output"].strip(), "10")

        self.assertTrue(
            self.client.post("/api/shell/reset", json={"session": sid}).get_json()["success"]
        )
        reply = self.client.post(
            "/api/shell/exec", json={"session": sid, "code": "kept"}
        ).get_json()
        # Plain words, not "NameError". The shell speaks the reader's language
        # the same way the runner does, so what is checked here is the
        # sentence, not the exception name behind it.
        self.assertIn("hasn't been defined", reply["error"])
        self.assertNotIn("Traceback", reply["error"])

        self.assertTrue(
            self.client.post("/api/shell/stop", json={"session": sid}).get_json()["success"]
        )

    def test_a_command_in_a_session_that_is_gone_says_so(self):
        # The reader's own process may have been evicted, or the page may have
        # been closed for a while. This is a sentence, not a stack trace.
        reply = self.client.post(
            "/api/shell/exec", json={"session": "not-a-real-session", "code": "1"}
        ).get_json()
        self.assertFalse(reply["success"])
        self.assertTrue(reply["error"])

    def test_empty_input_is_refused_in_plain_words(self):
        sid = self.start()
        reply = self.client.post(
            "/api/shell/exec", json={"session": sid, "code": "   \n  "}
        ).get_json()
        self.assertTrue(reply["error"])
        self.assertNotIn("Traceback", reply["error"])

    def test_blocked_code_is_refused_before_it_runs(self):
        # The same gate the runner has. A shell that could import anything the
        # runner refuses would make the runner's protection theatre.
        #
        # The sandbox is on for the hosted copy and off on the reader's own
        # machine, so it has to be switched on here or this check would pass
        # without anything being blocked at all.
        self._sandbox(True)
        sid = self.start()
        reply = self.client.post(
            "/api/shell/exec",
            json={"session": sid, "code": "import subprocess\nsubprocess.run(['whoami'])"},
        ).get_json()
        self.assertTrue(reply["error"])
        # Nothing was defined by the refused command, so the session is
        # untouched and still usable.
        self.assertEqual(
            self.client.post(
                "/api/shell/exec", json={"session": sid, "code": "2 + 2"}
            ).get_json()["output"].strip(),
            "4",
        )

    def test_on_the_readers_own_machine_the_shell_is_just_python(self):
        # The reason the shell exists. With no web server in front, nothing is
        # blocked, so a reader can install a package and use the module -
        # which is the whole point of asking for a shell rather than a list of
        # modules.
        self._sandbox(False)
        sid = self.start()
        reply = self.client.post(
            "/api/shell/exec",
            json={"session": sid, "code": "import math\nmath.factorial(5)"},
        ).get_json()
        self.assertEqual(reply.get("error"), "")
        self.assertEqual(reply["output"].strip(), "120")

    def test_a_package_the_reader_installs_can_then_be_used(self):
        # What "install requests" has to mean, end to end, without actually
        # reaching the network in a test: a module found on the path is
        # importable in the shell, and the shell keeps it.
        self._sandbox(False)
        sid = self.start()
        self.client.post(
            "/api/shell/exec",
            json={"session": sid, "code": "import json, base64"},
        )
        reply = self.client.post(
            "/api/shell/exec",
            json={"session": sid, "code": "base64.b64encode(b'ok').decode()"},
        ).get_json()
        self.assertEqual(reply.get("error"), "")
        self.assertEqual(reply["output"].strip(), "'b2s='")

    def test_the_access_code_gate_matches_the_runner(self):
        # Set the code the same way the runner's own tests do, so a shell that
        # forgot the gate would be caught here rather than in production.
        routes.ACCESS_CODE = "letmein"
        self.addCleanup(setattr, routes, "ACCESS_CODE", "")
        if not routes.ACCESS_CODE:
            self.skipTest("ACCESS_CODE is not a module global here")

        reply = self.client.post("/api/shell/start", json={}).get_json()
        self.assertTrue(reply.get("code_required"))
        self.assertEqual(
            self.client.post("/api/shell/start", json={}).status_code, 403
        )

        ok = self.client.post(
            "/api/shell/start", json={"access_code": "letmein"}
        ).get_json()
        self.assertTrue(ok.get("session"))

    def test_a_reader_is_not_locked_out_of_their_own_shell_for_typing(self):
        # The reason the shell has its own allowance. RATE_MAX suits the
        # runner, which is one request per deliberate click, but a shell is
        # one request per line typed, and being told to slow down while your
        # shell still looks open reads as the shell being broken.
        sid = self.start()
        for n in range(routes.RATE_MAX + 5):
            reply = self.client.post(
                "/api/shell/exec", json={"session": sid, "code": "1"}
            )
            self.assertNotEqual(
                reply.status_code, 429,
                f"throttled after {n + 1} commands, which is ordinary use",
            )

    def test_the_shell_allowance_is_still_a_ceiling(self):
        # Generous is not the same as unlimited. Someone hammering the hosted
        # copy with a real session id still gets stopped.
        sid = self.start()
        last = self.client.post("/api/shell/exec", json={"session": sid, "code": "1"})
        for _ in range(routes.SHELL_RATE_MAX + 5):
            last = self.client.post(
                "/api/shell/exec", json={"session": sid, "code": "1"}
            )
        self.assertEqual(last.status_code, 429)
        self.assertTrue(last.get_json()["error"])

    def test_stopping_a_session_that_is_already_gone_is_reported_as_done(self):
        # The outcome the reader asked for. Saying "failed" here would be a
        # lie, and would make the page show an error for closing a panel.
        reply = self.client.post(
            "/api/shell/stop", json={"session": "never-existed"}
        ).get_json()
        self.assertTrue(reply["success"])


if __name__ == "__main__":
    unittest.main()
