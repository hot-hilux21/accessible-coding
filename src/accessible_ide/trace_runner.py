"""Run one script with a trace, and write down what each line did to a variable.

This file is a child process, not something the server calls in-process. The
one-shot runner in routes.py writes the reader's code to a temp file and runs
it, which answers "what did this print" and says nothing at all about how it
got there. This runs the same file with ``sys.settrace`` installed and leaves a
sidecar JSON beneath it describing the lines the program executed and the
variables visible at each one, so the app can offer a trace table after a run
the reader has already done.

Four things about that are deliberate.

The trace never touches the program's own output. The reader's ``print`` calls
go to the real stdout exactly as before and the trace goes to a separate file,
so opening a table can never change what a program printed. That is also what
keeps the plain English error translation working untouched, since it reads the
child's stderr and nothing here writes to it.

The trace stops itself. A trace function is called on every line the program
executes, which slows it down a great deal, and the runner gives a script ten
seconds and no more. Once the caps below are reached the trace function is
uninstalled and the rest of the program runs at full speed. This matters more
than it looks: the reader only opens the table *after* the run, so every run
pays for tracing whether or not anybody looks, and a trace that could not stop
would turn a working script into a timeout.

Only the reader's own file is traced. ``sys.settrace`` fires for the standard
library too, and four hundred rows about what ``range`` did would bury the
reader's own three variables. Frames are matched on the filename of the file
being run, so the table is about their code and nothing else.

A row is only written when a value actually changes. A loop body re-reading
``i`` on every pass would otherwise write the same row dozens of times and
drown the one line the reader is looking for. The table is meant to answer
"where did this change", so a repeated value is not news.
"""

import json
import os
import re
import runpy
import sys

# How the parent tells this process what to run and where to leave the answer.
#
# Passed through the environment rather than as command line arguments because
# the packaged exe re-invokes itself with ``--run-script`` and does not forward
# extra arguments to the file it runs. Reading them from the environment means
# one launch path that works in a source tree and inside the exe, instead of
# two that can disagree.
ENV_TARGET = 'ACCESSIBLE_IDE_TRACE_TARGET'
ENV_OUT = 'ACCESSIBLE_IDE_TRACE_OUT'

# Lines executed in the reader's own file before the trace gives up and lets
# the program finish at full speed. Well above anything a learner writes by
# hand, and low enough that the ten second budget is not spent tracing.
MAX_STEPS = 5000

# Rows handed to the app. One line in a loop can contribute several rows, so
# this is reached long before MAX_STEPS and the two are not the same limit.
MAX_ROWS = 400

# Characters kept of one value. A list of a thousand numbers is a legitimate
# thing for a learner to print and a terrible thing to put in a table cell.
MAX_VALUE_LEN = 80

# An unset variable and a variable worth less than nothing are different
# answers, so "never seen" needs a value of its own. None cannot be it: the
# reader's own ``x = None`` has to record a row.
_MISSING = object()

# A function or an object reprs with the address it happens to live at, which
# changes on every run. Left in, the same variable would look like a new value
# every time the program started and the table would be full of noise.
_ADDRESS = re.compile(r' at 0x[0-9a-fA-F]+')


def _trim(text):
    """Cut a value down to something one table cell can hold."""
    if len(text) <= MAX_VALUE_LEN:
        return text
    return text[:MAX_VALUE_LEN - 3] + '...'


def safe_repr(value):
    """``repr()`` that always answers with a string.

    A reader writing their own class can easily give it a ``__repr__`` that
    raises, or one that never stops recursing. Reporting on a program is not
    allowed to be the thing that breaks it, so every failure here becomes a
    row saying what it was instead of an exception.
    """
    try:
        text = repr(value)
    except BaseException:
        return '<' + type(value).__name__ + ' that cannot be shown>'
    if not isinstance(text, str):
        # repr is documented to return a str, but this only has to not crash.
        return '<' + type(value).__name__ + ' that cannot be shown>'
    return _trim(_ADDRESS.sub('', text))


def is_hidden_name(name):
    """True for the dunder names the interpreter puts in every namespace.

    ``__builtins__`` alone reprs to thousands of characters and none of it is
    the reader's code. Their own variables are never spelled this way.
    """
    return len(name) > 4 and name.startswith('__') and name.endswith('__')


def main(argv=None):
    """Trace the file named in the environment and write the sidecar."""
    target = os.environ.get(ENV_TARGET, '')
    out_path = os.environ.get(ENV_OUT, '')
    if not target or not os.path.isfile(target):
        return 2

    # Compared through normcase and abspath because the same file reaches this
    # process by more than one spelling - a short path, a forward slashed path -
    # and a trace that matched on the spelling would silently record nothing.
    wanted = os.path.normcase(os.path.abspath(target))

    rows = []
    steps = 0
    truncated = False
    # The last value written for each variable, per function. Keyed by function
    # as well as name so that two functions with a local ``i`` do not look like
    # one variable jumping between them.
    last = {}
    # The line each frame ran last, so a change can be credited to the line that
    # caused it rather than the line that noticed it.
    previous_line = {}

    def record(frame, origin):
        """Write one row per variable whose value changed.

        Answers True when a change had to be dropped because the table is full.
        Both caps end the same way, so the caller treats them the same: the
        table is incomplete, and it is labelled incomplete.
        """
        for name, value in list(frame.f_locals.items()):
            if is_hidden_name(name):
                continue
            text = safe_repr(value)
            key = (frame.f_code.co_name, name)
            if last.get(key, _MISSING) == text:
                continue
            last[key] = text
            if len(rows) >= MAX_ROWS:
                return True
            rows.append([origin, name, text])
        return False

    def stop():
        """Label the table incomplete and let the rest of the program run free.

        Both caps end here. Returning None stops this frame and sys.settrace
        stops the next one, so a run that filled the table finishes at full
        speed instead of spending its ten second budget being traced.
        """
        nonlocal truncated
        truncated = True
        sys.settrace(None)

    def local_trace(frame, event, arg):
        nonlocal steps, truncated
        if event == 'return':
            # The last line of a frame still has its own assignment to report:
            # there is no later line event to observe it, and a script ending in
            # ``x = 5`` would otherwise never show x at all. Credited to the line
            # that ran, and the dedupe above drops everything that did not move.
            if steps <= MAX_STEPS and record(
                    frame, previous_line.get(id(frame), frame.f_lineno)):
                stop()
                return None
            # The frame is going away and its id can be handed to the next one,
            # so its entry goes with it or an unrelated function inherits a line
            # number from a frame that finished long ago.
            previous_line.pop(id(frame), None)
            return local_trace
        if event != 'line':
            return local_trace
        steps += 1
        if steps > MAX_STEPS:
            stop()
            return None
        # A line event fires *before* its line runs, so the variables on show are
        # the ones the line above left behind. Crediting them to this line would
        # say a loop variable changed on the line below the one that changed it,
        # which is exactly the question the table exists to answer. The first
        # event of a frame has nothing before it, so a function's arguments are
        # credited to its own first line.
        origin = previous_line.get(id(frame), frame.f_lineno)
        previous_line[id(frame)] = frame.f_lineno
        if record(frame, origin):
            stop()
            return None
        return local_trace

    def global_trace(frame, event, arg):
        if event == 'call' and os.path.normcase(
                os.path.abspath(frame.f_code.co_filename)) == wanted:
            return local_trace
        return None

    sys.settrace(global_trace)
    try:
        # run_path rather than exec so the reader's file is run the way the
        # interpreter runs it: __name__ is __main__ (so a guarded main runs),
        # __file__ is set, and a traceback still names their file and line.
        runpy.run_path(target, run_name='__main__')
    except BaseException:
        # Deliberately re-raised. The runner shows the program's own error, and
        # a trace is not a reason to swallow it.
        raise
    finally:
        sys.settrace(None)
        _write(out_path, rows, steps, truncated)
    return 0


def _write(out_path, rows, steps, truncated):
    """Leave the answer where the parent will look, and never raise.

    Written in a finally block so a program that failed still gets a trace. A
    failing run is the run a reader most wants to look at, and a table that
    only appeared for programs that worked would be missing the point.

    A failure to write is not worth reporting: the parent treats a missing file
    as "no trace", which is a state it has to handle anyway.
    """
    if not out_path:
        return
    try:
        with open(out_path, 'w', encoding='utf-8') as handle:
            json.dump({
                'rows': rows,
                'steps': steps,
                'truncated': truncated,
            }, handle)
    except Exception:
        pass


if __name__ == '__main__':
    sys.exit(main())
