"""Tests for the trace table.

Two halves, and they need testing two ways.

The child in trace_runner.py is run for real. What matters about it is what
sys.settrace actually reports, in the order it reports it, and no double of a
trace function reproduces that. So the fixtures here run the child and read the
sidecar it leaves behind.

The server half is tested through the route, because the promise it makes is
about the shape of every answer. A run the server refused to perform, or one
that came back with nothing to show, still has to carry a trace key: the page
decides whether to offer the table from that key, and a missing one would make
it guess.

Isolation: routes.py reads RATE_LIMIT, CONFIG_DIR, CONFIG_FILE and ACCESS_CODE
as module-level globals, so each of those is repointed or cleared per test.
Clearing RATE_LIMIT matters most here: the route allows ten runs a minute per
address and the test client is always the same address, so without it these
tests would be the ones that trip the limit.
"""

import io
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = str(REPO_ROOT / "src")
if SRC not in sys.path:
    sys.path.append(SRC)

from accessible_ide import create_app, routes, trace_runner  # noqa: E402

CHILD = REPO_ROOT / "src" / "accessible_ide" / "trace_runner.py"

# A loop, one statement per line, small enough to reason about in full.
#
# The rows it should produce are the point of the whole feature, so they are
# written out rather than counted: a loop variable is credited to the ``for``
# line that advances it and not to the line below that reads it, and the last
# assignment is reported from the frame's return because no later line event
# will ever observe it.
LOOP = "total = 0\nfor i in range(3):\n    total = total + i\n"
LOOP_ROWS = [
    [1, "total", "0"],
    [2, "i", "0"],
    [2, "i", "1"],
    [3, "total", "1"],
    [2, "i", "2"],
    [3, "total", "3"],
]


class BrokenRepr:
    """A value whose repr raises, which a reader can write by accident."""

    def __repr__(self):
        raise ValueError("no repr for you")


class NotAStringRepr:
    """A repr that does not answer with a string."""

    def __repr__(self):
        return 42  # type: ignore[return-value]


def some_function():
    """Something whose repr carries an address that must be stripped."""


class TraceChildTestCase(unittest.TestCase):
    """Runs trace_runner.py the way routes.py runs it."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = pathlib.Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)

    def run_child(self, source, env=None):
        """Run one program through the child and return (result, sidecar)."""
        script = self.dir / "program.py"
        script.write_text(source, encoding="utf-8")
        out = self.dir / "trace.json"

        child_env = dict(os.environ)
        if env is None:
            child_env[trace_runner.ENV_TARGET] = str(script)
            child_env[trace_runner.ENV_OUT] = str(out)
        else:
            child_env.update(env)

        result = subprocess.run(
            [sys.executable, "-u", str(CHILD)],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=str(self.dir),
            env=child_env,
        )
        payload = None
        if out.is_file():
            payload = json.loads(out.read_text(encoding="utf-8"))
        return result, payload


class TraceRowsTests(TraceChildTestCase):
    """What the child records, and which line it credits it to."""

    def test_a_change_is_credited_to_the_line_that_caused_it(self):
        result, payload = self.run_child(LOOP)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(payload["rows"], LOOP_ROWS)
        self.assertFalse(payload["truncated"])

    def test_the_program_output_is_untouched(self):
        # The trace goes to its own file. A program that prints must print
        # exactly what it printed before there was a trace table.
        result, payload = self.run_child(LOOP + "print(total)\n")
        self.assertEqual(result.stdout, "3\n")
        self.assertEqual(result.stderr, "")
        self.assertEqual(payload["rows"], LOOP_ROWS)

    def test_a_value_that_never_moves_is_written_once(self):
        # The table answers "where did this change". A repeated value is not
        # news, and writing it every line would bury the one row that is.
        _, payload = self.run_child("x = 1\nx = 1\nx = 2\n")
        self.assertEqual(payload["rows"], [[1, "x", "1"], [3, "x", "2"]])

    def test_a_function_argument_is_reported_at_its_own_first_line(self):
        source = (
            "def double(n):\n"
            "    return n * 2\n"
            "\n"
            "x = double(5)\n"
        )
        _, payload = self.run_child(source)
        rows = payload["rows"]
        self.assertIn([2, "n", "5"], rows)
        # The assignment is on the last line of the file, so it is reported
        # from the frame's return rather than from a line event below it.
        self.assertIn([4, "x", "10"], rows)

    def test_a_value_longer_than_a_cell_is_cut_down(self):
        _, payload = self.run_child("text = 'x' * 200\n")
        value = payload["rows"][0][2]
        self.assertEqual(len(value), trace_runner.MAX_VALUE_LEN)
        self.assertTrue(value.endswith("..."))

    def test_a_failing_program_still_leaves_a_trace(self):
        # The failing run is the one a reader most wants to look at, so the
        # sidecar is written from a finally block and not only on success.
        result, payload = self.run_child("a = 1\nb = a / 0\n")
        self.assertNotEqual(result.returncode, 0)
        self.assertIsNotNone(payload, "a failing run left no trace at all")
        self.assertIn([1, "a", "1"], payload["rows"])
        self.assertIn("ZeroDivisionError", result.stderr)

    def test_the_row_cap_labels_the_table_incomplete(self):
        # Piling up distinct values (a growing list, a counting loop) fills the
        # table long before the step cap, and a table that filled up must say
        # so. Reporting "incomplete" only for the step cap would show a reader
        # four hundred rows as though they were all of them.
        _, payload = self.run_child(
            "values = []\nfor i in range(600):\n    values.append(i)\n")
        self.assertEqual(len(payload["rows"]), trace_runner.MAX_ROWS)
        self.assertTrue(payload["truncated"])

    def test_the_step_cap_labels_the_table_incomplete_and_finishes(self):
        # Six thousand statements with nothing changing in them: the steps run
        # out while the table stays nearly empty. The trace has to uninstall
        # itself here, or a run that used to finish would instead spend the ten
        # second budget being traced and come back as a timeout.
        source = "x = 0\n" + "y = x + 1\n" * 6000
        result, payload = self.run_child(source)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(payload["truncated"])
        self.assertLess(len(payload["rows"]), 10)
        self.assertGreater(payload["steps"], trace_runner.MAX_STEPS)

    def test_the_child_refuses_when_it_is_told_nothing_to_run(self):
        result, payload = self.run_child(LOOP, env={
            trace_runner.ENV_TARGET: "",
            trace_runner.ENV_OUT: "",
        })
        self.assertEqual(result.returncode, 2)
        self.assertIsNone(payload)


class SafeReprTests(unittest.TestCase):
    """Reporting on a program must never be what breaks it."""

    def test_a_repr_that_raises_becomes_a_row_not_a_crash(self):
        self.assertEqual(
            trace_runner.safe_repr(BrokenRepr()),
            "<BrokenRepr that cannot be shown>",
        )

    def test_a_repr_that_is_not_a_string_becomes_a_row_not_a_crash(self):
        self.assertEqual(
            trace_runner.safe_repr(NotAStringRepr()),
            "<NotAStringRepr that cannot be shown>",
        )

    def test_a_memory_address_is_stripped(self):
        # An address changes on every run. Left in, the same variable would
        # look like a brand new value every time the program started.
        text = trace_runner.safe_repr(some_function)
        self.assertNotIn(" at 0x", text)
        self.assertTrue(text.startswith("<function some_function"))

    def test_a_short_value_is_left_alone(self):
        self.assertEqual(trace_runner.safe_repr("hi"), "'hi'")


class HiddenNameTests(unittest.TestCase):
    """The dunder names the interpreter puts in every namespace."""

    def test_the_interpreters_own_names_are_hidden(self):
        for name in ("__builtins__", "__name__", "__init__"):
            with self.subTest(name=name):
                self.assertTrue(trace_runner.is_hidden_name(name))

    def test_a_readers_own_names_are_not_hidden(self):
        for name in ("x", "total", "_", "__", "dunder_like"):
            with self.subTest(name=name):
                self.assertFalse(trace_runner.is_hidden_name(name))


class ReadTraceTests(unittest.TestCase):
    """Reading the sidecar, where every failure has to end as "nothing"."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = pathlib.Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)

    def write(self, text, name="trace.json"):
        path = self.dir / name
        path.write_text(text, encoding="utf-8")
        return path

    def test_a_missing_file_is_nothing_to_show(self):
        trace = routes.read_trace(str(self.dir / "not-there.json"))
        self.assertFalse(trace["available"])

    def test_junk_is_nothing_to_show(self):
        # Half a file is what a run killed mid-write leaves behind.
        trace = routes.read_trace(str(self.write("{not json")))
        self.assertFalse(trace["available"])

    def test_rows_that_are_not_a_list_are_nothing_to_show(self):
        trace = routes.read_trace(str(self.write('{"rows": "nope", "steps": 3}')))
        self.assertFalse(trace["available"])

    def test_a_trace_with_no_rows_and_no_steps_is_nothing_to_show(self):
        trace = routes.read_trace(str(self.write('{"rows": [], "steps": 0}')))
        self.assertFalse(trace["available"])

    def test_a_real_trace_reads_back_with_its_counts(self):
        path = self.write(json.dumps({
            "rows": [[1, "x", "1"], [2, "x", "2"]],
            "steps": 7,
            "truncated": True,
        }))
        trace = routes.read_trace(str(path))
        self.assertTrue(trace["available"])
        self.assertEqual(trace["rows"], [[1, "x", "1"], [2, "x", "2"]])
        self.assertEqual(trace["steps"], 7)
        self.assertEqual(trace["shown"], 2)
        self.assertTrue(trace["truncated"])

    def test_nothing_to_show_has_the_same_shape_as_a_real_trace(self):
        # The page reads these fields without asking whether they exist, so
        # "nothing to show" is a state and not a missing value.
        self.assertEqual(
            set(routes.no_trace()),
            {"available", "rows", "steps", "shown", "truncated"},
        )

    def test_the_child_path_points_at_a_file_that_is_there(self):
        self.assertTrue(os.path.isfile(routes.trace_child_path()))


class RunRouteTestCase(unittest.TestCase):
    """The isolation and the request every test that runs a program needs.

    Subclassed rather than copied, so that a change to what the runner needs
    from a test client reaches every test that talks to it. Why each of the
    globals below is here is in the module docstring.
    """

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        tmp_path = pathlib.Path(self._tmp.name)

        self._saved = {
            "CONFIG_DIR": routes.CONFIG_DIR,
            "CONFIG_FILE": routes.CONFIG_FILE,
            "ACCESS_CODE": routes.ACCESS_CODE,
            "RATE_LIMIT": routes.RATE_LIMIT,
            "SANDBOX": routes.SANDBOX,
        }
        routes.CONFIG_DIR = tmp_path
        routes.CONFIG_FILE = tmp_path / "config.json"
        routes.ACCESS_CODE = ""
        routes.RATE_LIMIT = {}
        # The sandbox is off everywhere except the public web build, and the
        # test client is not that. Left alone, the refusal path in a test below
        # would never be reached and the test would pass for the wrong reason.
        routes.SANDBOX = False

        app = create_app()
        app.config["TESTING"] = True
        self.client = app.test_client()
        self.addCleanup(self._restore)

    def _restore(self):
        for key, value in self._saved.items():
            setattr(routes, key, value)
        self._tmp.cleanup()

    def run_code(self, source, answers=None):
        response = self.client.post("/api/run", json={"code": source,
                                                      "answers": answers or []})
        return response, response.get_json()


class TraceRouteTests(RunRouteTestCase):
    """Every answer from /api/run carries a trace key."""

    def test_a_run_reports_its_trace(self):
        _, data = self.run_code(LOOP)
        self.assertEqual(data["output"], "")
        trace = data["trace"]
        self.assertTrue(trace["available"])
        self.assertEqual(trace["rows"], LOOP_ROWS)
        self.assertEqual(trace["shown"], len(LOOP_ROWS))

    def test_an_empty_program_says_nothing_to_show(self):
        # Empty code is answered before anything is run, and it still has to
        # carry the key rather than leaving the page to guess.
        _, data = self.run_code("   \n")
        self.assertIn("trace", data)
        self.assertFalse(data["trace"]["available"])

    def test_a_refused_program_says_nothing_to_show(self):
        # Refused by the sandbox, so it never ran and there is nothing to show.
        routes.SANDBOX = True
        _, data = self.run_code("import os\n")
        self.assertIn("trace", data)
        self.assertFalse(data["trace"]["available"])
        self.assertTrue(data["error"])

    def test_a_failing_program_reports_its_own_line_and_still_has_a_trace(self):
        # The line number has to be the reader's line in their own file, not a
        # line in the runner or in the trace child.
        _, data = self.run_code("a = 1\nb = a / 0\n")
        self.assertTrue(data["error"])
        self.assertEqual(data["error_line"], 2)
        self.assertTrue(data["trace"]["available"])
        self.assertIn([1, "a", "1"], data["trace"]["rows"])

    def test_a_program_that_prints_still_prints(self):
        _, data = self.run_code("print('hello')\n")
        self.assertEqual(data["output"], "hello\n")
        self.assertEqual(data["error"], "")


class InteractiveRunTests(RunRouteTestCase):
    """A program that asks a question gets an answer, not an error.

    The runner stays one-shot: nothing is left alive between one request and
    the next. What makes it interactive is that the answers already given are
    sent along with each run, so the program reaches the question nobody has
    answered yet and stops there. These tests are about that handshake, which
    is the whole difference between a program using input() and an error the
    reader did not cause.
    """

    ASKS = 'name = input("What is your name? ")\nprint("hello", name)\n'

    def test_a_program_that_asks_is_held_on_its_question(self):
        _, data = self.run_code(self.ASKS)
        self.assertTrue(data["awaiting_answer"])
        self.assertEqual(data["error"], "")
        # The question is what the program printed, so the page can show it
        # without the route having to work out where the question started.
        self.assertEqual(data["output"], "What is your name? ")
        # A failing run is not the only one worth a trace table.
        self.assertTrue(data["trace"]["available"])

    def test_an_answer_finishes_the_program_and_is_shown_back(self):
        self.run_code(self.ASKS)
        _, data = self.run_code(self.ASKS, ["alice"])
        self.assertFalse(data["awaiting_answer"])
        self.assertEqual(data["error"], "")
        # The typed answer appears because input() writes it back out. A
        # terminal echoes what is typed at it and a pipe does not, so without
        # that this would read "What is your name? hello alice" and leave the
        # reader's own typing out of the transcript.
        self.assertEqual(data["output"],
                         "What is your name? alice\nhello alice\n")

    def test_every_answer_is_sent_again_with_every_run(self):
        source = ('first = input("First? ")\n'
                  'second = input("Second? ")\n'
                  'print(first, second)\n')
        _, first = self.run_code(source)
        self.assertTrue(first["awaiting_answer"])
        _, second = self.run_code(source, ["one"])
        self.assertTrue(second["awaiting_answer"])
        self.assertEqual(second["output"], "First? one\nSecond? ")
        _, third = self.run_code(source, ["one", "two"])
        self.assertFalse(third["awaiting_answer"])
        self.assertEqual(third["output"], "First? one\nSecond? two\none two\n")

    def test_a_program_that_does_not_ask_is_unaffected(self):
        # The common case, which has to stay exactly as it was.
        _, data = self.run_code("print('hello')\n")
        self.assertFalse(data["awaiting_answer"])
        self.assertEqual(data["output"], "hello\n")

    def test_an_answer_may_be_empty(self):
        # Pressing Enter without typing is an answer, and a program that is
        # told apart by it must not be told apart wrongly.
        _, data = self.run_code('x = input()\nprint("got", x)\n', [""])
        self.assertFalse(data["awaiting_answer"])
        self.assertEqual(data["output"], "\ngot \n")

    def test_a_readers_own_eoferror_is_still_their_mistake(self):
        # A question is recognised by the exact message the runner raises, not
        # by the exception name. One they wrote themselves is their error to
        # see, not something to ask them to answer.
        _, data = self.run_code('raise EOFError("their own reason")\n')
        self.assertFalse(data["awaiting_answer"])
        self.assertTrue(data["error"])

    def test_answers_that_are_not_a_list_are_treated_as_none(self):
        # Anything other than the list the page sends becomes a fresh run
        # rather than a half-read one, which is the state the reader can fix
        # by answering again.
        response = self.client.post("/api/run", json={"code": self.ASKS,
                                                      "answers": "alice"})
        self.assertTrue(response.get_json()["awaiting_answer"])

    def test_past_the_cap_a_program_is_reported_as_ended(self):
        # The cap is about what one request may carry rather than about the
        # reader, and reaching it takes one run: fed fifty answers, this
        # program stops on its fifty-first question and is then reported the
        # way any other program that ran out of input is reported.
        source = "for i in range(51):\n    input()\n"
        _, data = self.run_code(source, ["a"] * routes.MAX_ANSWERS)
        self.assertFalse(data["awaiting_answer"])
        self.assertTrue(data["error"])


class AnswerLimitsTests(unittest.TestCase):
    """What one request may be asked to carry.

    These are the limits that keep the route's body small no matter what a
    client sends, so they are about the shape of the request rather than about
    the reader and belong to a plain unit test rather than to a run.
    """

    def test_answers_are_trimmed_to_the_two_limits(self):
        answers = routes.answers_from({"answers": ["x" * 5000] * 200})
        self.assertEqual(len(answers), routes.MAX_ANSWERS)
        self.assertTrue(all(len(answer) == routes.MAX_ANSWER_LEN
                            for answer in answers))

    def test_an_answer_of_the_wrong_shape_clears_the_whole_list(self):
        # Not dropping the odd entry: a request that did not come from the
        # page should not have part of its answers treated as if it had.
        self.assertEqual(routes.answers_from({"answers": ["a", 3]}), [])
        self.assertEqual(routes.answers_from({"answers": {"a": 1}}), [])
        self.assertEqual(routes.answers_from({"answers": "alice"}), [])
        self.assertEqual(routes.answers_from({"answers": None}), [])
        self.assertEqual(routes.answers_from({}), [])


class ReaderInputTests(unittest.TestCase):
    """input() as the reader's own program sees it.

    The route tests cover the round trip through a running program; this is
    about the one function that stands in for the builtin, which decides what
    the transcript says and what the route is able to recognise afterwards.
    """

    def ask(self, supplied, prompt=""):
        """Run the reader's input() against some text already on stdin, and
        say what it answered along with what the program's own output saw."""
        original = sys.stdin
        sys.stdin = io.StringIO(supplied)
        written = io.StringIO()
        try:
            with redirect_stdout(written):
                answer = trace_runner._reader_input(prompt)
        finally:
            sys.stdin = original
        return answer, written.getvalue()

    def test_the_question_and_the_answer_both_reach_the_transcript(self):
        answer, seen = self.ask("alice\n", "What is your name? ")
        self.assertEqual(answer, "alice")
        self.assertEqual(seen, "What is your name? alice\n")

    def test_an_answer_with_no_prompt_is_only_the_answer(self):
        answer, seen = self.ask("41\n")
        self.assertEqual(answer, "41")
        self.assertEqual(seen, "41\n")

    def test_an_empty_line_is_an_answer_of_nothing(self):
        answer, seen = self.ask("\n", "> ")
        self.assertEqual(answer, "")
        self.assertEqual(seen, "> \n")

    def test_a_line_of_spaces_keeps_its_spaces(self):
        # The builtin strips the terminator and nothing else, so an answer
        # that is spaces stays spaces instead of becoming an empty answer.
        answer, seen = self.ask("   \n")
        self.assertEqual(answer, "   ")
        self.assertEqual(seen, "   \n")

    def test_running_out_of_answers_says_exactly_what_the_route_listens_for(self):
        # The contract between the child and the server. The server matches
        # this wording to tell a question from a failure, so a change to it
        # would quietly turn every question the reader is asked into an error.
        with self.assertRaises(EOFError) as caught:
            self.ask("")
        self.assertEqual(str(caught.exception), trace_runner.EOF_MESSAGE)
        self.assertEqual(trace_runner.EOF_MESSAGE, "EOF when reading a line")


class PackagingTests(unittest.TestCase):
    """Both builds have to ship the child programs on disk."""

    SPECS = ("AccessibleIDE.spec", "AccessibleIDE-onedir.spec")

    def test_both_specs_bundle_the_traced_child(self):
        # It is launched by path, not imported, so PyInstaller has to be told
        # to copy it out as a file. Bundled only as compiled bytecode it is not
        # on disk, --run-script is pointed at nothing, and every run would fail
        # in the packaged exe.
        for name in self.SPECS:
            spec = (REPO_ROOT / name).read_text(encoding="utf-8")
            with self.subTest(spec=name):
                self.assertIn("trace_runner.py", spec)

    def test_both_specs_bundle_the_shell_bootstrap(self):
        # The shell reads its bootstrap from disk too, through shell.py's
        # bootstrap_path, and that function's own docstring says the spec lists
        # this file in datas. Until now no spec did, so the packaged shell had
        # nothing to start from.
        for name in self.SPECS:
            spec = (REPO_ROOT / name).read_text(encoding="utf-8")
            with self.subTest(spec=name):
                self.assertIn("shell_bootstrap.py", spec)


class TraceWindowStylesheetTests(unittest.TestCase):
    """A closed dialog has to stay hidden.

    The user agent hides a closed <dialog> with `dialog:not([open]) { display:
    none }`. An author rule on the bare class outranks that, because author
    styles beat user-agent styles whatever the selectors compare like. So a
    `display` written on `.trace-window` instead of `.trace-window[open]` leaves
    the empty table on the page before any run, still hit-testable and still
    draggable by whatever the pointer finds. That shipped once.
    """

    CSS = REPO_ROOT / "src" / "accessible_ide" / "static" / "css" / "style.css"

    # Comments are stripped before anything is read, so a comment that names a
    # property cannot pass for the property itself.
    COMMENTS = re.compile(r"/\*.*?\*/", re.DOTALL)

    @classmethod
    def _top_level_rule(cls, selector):
        """The declaration block of a top-level rule, without comments."""
        css = cls.COMMENTS.sub("", cls.CSS.read_text(encoding="utf-8"))
        search = 0
        while True:
            index = css.find(selector, search)
            if index == -1:
                return None
            search = index + len(selector)
            # Exactly this selector, so `.trace-window` does not answer for
            # `.trace-window[open]`.
            if not css[search:].lstrip().startswith("{"):
                continue
            # And at the top level, so a rule inside an @media is not taken for
            # the one the page applies everywhere.
            if css.count("{", 0, index) != css.count("}", 0, index):
                continue
            start = css.index("{", index) + 1
            depth = 1
            end = start
            while depth:
                if css[end] == "{":
                    depth += 1
                elif css[end] == "}":
                    depth -= 1
                end += 1
            return css[start:end - 1]

    def test_the_closed_window_carries_no_author_display(self):
        block = self._top_level_rule(".trace-window")
        self.assertIsNotNone(block, ".trace-window has no rule in style.css")
        self.assertNotIn(
            "display",
            block,
            "a display on .trace-window outranks dialog:not([open]) and shows "
            "the closed window; it belongs on .trace-window[open]",
        )

    def test_the_open_window_is_still_a_flex_column(self):
        block = self._top_level_rule(".trace-window[open]")
        self.assertIsNotNone(block, ".trace-window[open] has no rule")
        self.assertIn("display: flex", block)
        self.assertIn("flex-direction: column", block)


if __name__ == "__main__":
    unittest.main()
