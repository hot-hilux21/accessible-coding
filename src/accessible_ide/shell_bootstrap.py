"""The other end of the Python shell.

This file runs as a child process. It reads one JSON command per line on
stdin, runs it against a namespace it keeps between commands, and writes the
answer back on one line.

Two things about that are deliberate.

The namespace is kept. That is the whole difference between this and the
existing one-shot runner, which writes the editor's contents to a file and
throws it away. Here ``import os`` in one command is still true in the next,
which is what a reader means by a shell.

The answer comes back behind a sentinel, on its own line. The sentinel is not
decoration. Anything the reader's own code prints is captured and handed back
as data, and a program that prints the sentinel itself must not be able to
make the parent think a second reply had arrived. The parent reads whole
lines until it sees one that is exactly the sentinel, so whatever the program
printed stays inside the payload where it belongs.

Runs under ``exec`` mode by default and falls back from ``single``, so a bare
expression answers with its value the way a real shell does while a loop or a
function definition still works. ``single`` refuses compound statements
outright, which would have broken ``for`` on the first try.
"""

import ast
import contextlib
import io
import json
import sys
import traceback

# Written on its own line to the real stdout, after the reader's own output
# has been captured, so it can never be confused with the payload.
SENTINEL = '__AIDE_SHELL_END__'

# The reader is a learner, so errors are reported the way Python would report
# them and translated later by the parent, which has the reader's language.
_FILENAME = '<shell>'


def _compile(code):
    """Work out how to run this, and return the code objects in order.

    ``single`` echoes a bare expression's value, which is most of what makes
    a shell feel like a shell. It also refuses anything with more than one
    line of statements, so a two-line paste falls through to ``exec`` - which
    runs the code but prints no value for it. Someone who pastes

        import math
        math.factorial(5)

    and gets nothing back has every reason to think the second line never
    ran. A terminal shell answers 120, because it treats the paste as two
    submissions. This does the same thing: the statements before the last one
    run under ``exec``, and the trailing expression is run on its own under
    ``single`` so its value is displayed.

    Each statement is compiled and run exactly once, so a line with side
    effects is not repeated to get the echo. The trailing expression keeps its
    real line number, so an error in it still points at the line the reader
    actually typed.
    """
    try:
        tree = ast.parse(code, _FILENAME, 'exec')
    except SyntaxError:
        # Not parseable at all. Let the ordinary path report it properly.
        return None

    if len(tree.body) > 1 and isinstance(tree.body[-1], ast.Expr):
        last = tree.body[-1]
        prefix = ast.Module(body=tree.body[:-1], type_ignores=[])
        # Compiled with the original source, so the prefix's line numbers are
        # already right and need no adjusting.
        return [
            compile(prefix, _FILENAME, 'exec'),
            _interactive(last),
        ]
    return None


def _interactive(node):
    """Compile one trailing expression so its value is displayed.

    Built as an Interactive block, which is what puts the display hook in.
    The node is moved to line 1 first and the block then shifted up to the
    line the reader typed it on, so a failure inside it reports that line
    rather than line 1.
    """
    expr = ast.Expression(body=node.value)
    ast.copy_location(expr, node.value)
    block = ast.Interactive(body=[ast.Expr(value=expr.body)])
    ast.fix_missing_locations(block)
    if getattr(node, 'lineno', 1) > 1:
        ast.increment_lineno(block, node.lineno - 1)
    return compile(block, _FILENAME, 'single')


def main():
    # Whatever the reader imports or defines lives here, for the life of the
    # process. __builtins__ is put back by exec/exec, so no need to seed it.
    namespace = {'__name__': '__main__', '__doc__': None}

    stdin = sys.stdin
    # sys.__stdout__ rather than sys.stdout: the redirect below swaps
    # sys.stdout for a buffer, and the sentinel has to go out to the real
    # pipe or it would be captured along with the program's own prints.
    out = sys.__stdout__ if sys.__stdout__ is not None else sys.stdout
    # Line buffered, or a reply can sit in a buffer while the parent waits
    # for a line that has already been "written". reconfigure is 3.7+ on
    # text streams; guarded because a pipe in some environments is not one.
    for stream in (stdin, out):
        reconfigure = getattr(stream, 'reconfigure', None)
        if reconfigure is not None:
            try:
                reconfigure(line_buffering=True)
            except Exception:
                pass

    while True:
        line = stdin.readline()
        if not line:
            break
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
        except ValueError:
            continue
        if request.get('quit'):
            break

        code = request.get('code', '')
        if request.get('reset'):
            namespace = {'__name__': '__main__', '__doc__': None}
            out.write(SENTINEL + '\n')
            out.write(json.dumps({'output': '', 'error': '', 'error_type': ''}) + '\n')
            out.flush()
            continue

        stdout_buf = io.StringIO()
        stderr_buf = io.StringIO()
        error_type = ''
        try:
            with contextlib.redirect_stdout(stdout_buf), \
                    contextlib.redirect_stderr(stderr_buf):
                prepared = _compile(code)
                if prepared is None:
                    # A single statement, or something that does not parse.
                    # 'single' answers a bare expression; anything more falls
                    # back to 'exec' so a loop or a def is not a SyntaxError.
                    try:
                        prepared = compile(code, _FILENAME, 'single')
                    except SyntaxError:
                        prepared = compile(code, _FILENAME, 'exec')
                if isinstance(prepared, list):
                    for chunk in prepared:
                        exec(chunk, namespace)
                else:
                    exec(prepared, namespace)
        except BaseException:
            # BaseException, not Exception, because a reader who types
            # exit() or raises SystemExit should get a sentence back, not
            # lose the session and everything they had defined in it.
            error_type = type(sys.exc_info()[1]).__name__
            traceback.print_exc(file=stderr_buf)

        out.write(SENTINEL + '\n')
        out.write(json.dumps({
            'output': stdout_buf.getvalue(),
            'error': stderr_buf.getvalue(),
            'error_type': error_type,
        }) + '\n')
        out.flush()


if __name__ == '__main__':
    main()
