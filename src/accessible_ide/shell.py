"""One Python shell per reader, kept out of everybody else's way.

The one-shot runner in routes.py writes the editor's contents to a file and
runs it, which is the right shape for "run this" and the wrong one for a
shell. A shell has to remember: ``import os`` in one command is still true in
the next, and a variable set five lines ago is still set. So this keeps a
child process alive per session and talks to it over a pipe.

Sessions are keyed by an unguessable id, and that is not tidiness. The hosted
copy runs for many readers at once, and a single shared namespace would mean
one reader could read another's variables - or, worse, watch them get cleared.
On the reader's own machine there is only ever one session and this is
invisible, which is exactly why it is easy to get wrong and hard to notice.

Everything here kills its child. A shell that times out has to be killed
rather than left spinning, a session that goes idle has to be evicted, and
the whole registry is closed at exit. An orphaned python.exe holding a pipe
open is the kind of bug that only shows up weeks later on somebody else's
machine.
"""

import atexit
import collections
import json
import os
import secrets
import signal
import subprocess
import sys
import tempfile
import threading
import time

from .shell_bootstrap import SENTINEL

# How long one command may take before the child is killed and the session
# respawns. Matches the one-shot runner, so the shell is not more patient
# than the button above it.
DEFAULT_TIMEOUT = 10.0

# Live sessions allowed at once. Each one is a process, so this is a cap on
# the processes a reader - or a visitor to the hosted copy - can leave behind.
MAX_SESSIONS = 8

# A session nobody has touched in this long is closed, and its process with
# it. Long enough for a reader to look something up, short enough that the
# cap is not reached by people who opened the panel and walked away.
IDLE_SECONDS = 15 * 60

# How long to wait for a killed child's reader thread to notice its pipe
# closed. Only reached after a timeout, and the thread is a daemon, so this
# is a tidiness bound rather than a correctness one.
JOIN_GRACE = 1.0

# Lines of the child's own stderr kept for showing. Bounded on purpose: a
# runaway program can write forever, and this is not allowed to become the
# reason the app runs out of memory.
STDERR_TAIL_LINES = 40

# How long to let the stderr drainer catch up after a reply arrives. The
# child has already finished writing by then, so this is only ever waiting
# for the parent to read what is already sitting in the pipe.
STDERR_SETTLE = 0.25


class ShellError(Exception):
    """The shell could not do what was asked, in a form worth showing."""


class ShellTimeout(ShellError):
    """A command ran past its time, so the child was killed."""


def bootstrap_path():
    """Where shell_bootstrap.py is, in a source tree and in a frozen build.

    Flask's root_path puts the package beside its bundled folders, and the
    spec lists this file in datas, so the same expression finds it either
    way. Reading it from disk rather than keeping a copy of the text here
    means there is one bootstrap to look at, not two that can drift.
    """
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(here, 'shell_bootstrap.py')


class ShellSession:
    """A child process and the namespace it is holding."""

    def __init__(self, timeout=DEFAULT_TIMEOUT):
        self._proc = None
        self._stderr_tail = collections.deque(maxlen=STDERR_TAIL_LINES)
        self._stderr_thread = None
        self._reader_thread = None
        self._timeout = timeout
        # One command at a time. Two threads writing to the same pipe would
        # interleave, and each would then read the other's answer, so a
        # session asked two things at once would answer neither.
        self._lock = threading.Lock()
        self.last_used = time.time()

    @property
    def alive(self):
        return self._proc is not None and self._proc.poll() is None

    def start(self):
        with self._lock:
            if not self.alive:
                self._spawn()
            self.last_used = time.time()

    def _spawn(self):
        script = bootstrap_path()
        if getattr(sys, 'frozen', False):
            # The same trick the one-shot runner uses: in the packaged build
            # the exe is the interpreter, and --run-script is how it is told
            # to run a file and exit.
            cmd = [sys.executable, '--run-script', script]
        else:
            cmd = [sys.executable, '-u', script]
        # A new process group, so the whole tree can be taken down at once.
        # The reader's commands are allowed to start other programs - that is
        # what a shell is for - and a program started that way inherits this
        # process's pipe handles. Killing only the process we spawned
        # therefore leaves the pipes open in its children, and the reader
        # thread below never sees the end of the stream.
        if sys.platform == 'win32':
            creationflags = getattr(subprocess, 'CREATE_NEW_PROCESS_GROUP', 0)
        else:
            creationflags = 0
        self._proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8',
            errors='replace',
            cwd=tempfile.gettempdir(),
            creationflags=creationflags,
            **({} if sys.platform == 'win32' else {'start_new_session': True}),
        )
        self._drain_stderr()

    def _drain_stderr(self):
        """Read the child's stderr so it cannot fill up and wedge the child.

        Python-level stderr is already captured in the payload by the
        bootstrap's redirect, so this only ever sees what escapes that:
        output written straight to file descriptor 2 by a subprocess or a C
        extension. A reader experimenting with subprocesses hits this
        constantly, and without a reader here the pipe fills, the child
        blocks on its own write, and the command dies at the timeout having
        printed nothing at all - which is about the worst failure a shell
        can have, because it looks like the shell is broken rather than full.

        The tail is kept rather than thrown away. A learner whose subprocess
        failed deserves to see why, and it costs a bounded amount of memory
        to be able to say so.
        """
        proc = self._proc
        if proc is None:
            return
        stderr = proc.stderr
        if stderr is None:
            return
        tail = self._stderr_tail
        tail.clear()

        def drain():
            try:
                for line in stderr:
                    tail.append(line)
            except (ValueError, OSError):
                # The stream was closed under us, which _kill does once the
                # child is gone. Nothing to report: the child is dead.
                pass

        self._stderr_thread = threading.Thread(target=drain, daemon=True)
        self._stderr_thread.start()

    def _send(self, request):
        """Write one command, starting a new child if the old one is gone."""
        if not self.alive:
            self._spawn()
        proc = self._proc
        if proc is None or proc.stdin is None:
            self._spawn()
            raise ShellError('shell_restarted')
        # The tail belongs to one command. Carrying it over would answer the
        # next command with the previous command's noise, which reads as
        # though the reader's own code printed it.
        self._stderr_tail.clear()
        try:
            proc.stdin.write(json.dumps(request) + '\n')
            proc.stdin.flush()
        except (BrokenPipeError, OSError, ValueError, AttributeError):
            # The child died between commands, most often killed by an
            # earlier timeout. Start a new one and let this command be what
            # tells the reader, rather than failing every later one too.
            self._spawn()
            raise ShellError('shell_restarted')
        return proc

    def exec(self, code, timeout=None):
        """Run one command; return {'output', 'error', 'error_type'}."""
        with self._lock:
            self.last_used = time.time()
            proc = self._send({'code': code})
            return self._read_reply(proc, timeout or self._timeout)

    def reset(self):
        """Forget the namespace but keep the process.

        Cheaper than a respawn, and it means a reader who has filled the
        screen with experiments can clear it without losing the shell itself.
        """
        with self._lock:
            self.last_used = time.time()
            proc = self._send({'reset': True})
            self._read_reply(proc, self._timeout)

    def _read_reply(self, proc, timeout):
        # The read blocks and there is no portable way to put a deadline on a
        # pipe, so it happens on a thread that can be abandoned. Killing the
        # child is what unblocks it, which is why a timeout kills rather than
        # merely giving up: a thread left waiting on a live process leaks.
        box = {}

        def reader():
            try:
                while True:
                    line = proc.stdout.readline()
                    if not line:
                        box['eof'] = True
                        return
                    if line.strip() == SENTINEL:
                        break
                data = proc.stdout.readline()
                box['payload'] = json.loads(data) if data.strip() else None
            except Exception as exc:  # noqa: BLE001 - reported, not swallowed
                box['error'] = exc

        thread = threading.Thread(target=reader, daemon=True)
        self._reader_thread = thread
        thread.start()
        thread.join(timeout)

        if thread.is_alive():
            self._kill()
            raise ShellTimeout('shell_timeout')
        # The reply is in, so the child has finished the command. The stderr
        # drainer is a separate thread and may still be a line or two behind,
        # and a tail that loses the last line is the line the reader was
        # actually looking for.
        drain = self._stderr_thread
        if drain is not None and drain.is_alive():
            drain.join(STDERR_SETTLE)


        if 'eof' in box:
            self._kill()
            raise ShellError('shell_closed')
        if 'error' in box:
            self._kill()
            raise ShellError(str(box['error']))
        payload = box.get('payload')
        if not isinstance(payload, dict):
            self._kill()
            raise ShellError('shell_closed')
        # Whatever escaped the bootstrap's own capture is appended to the
        # output rather than to the error. It arrived on the child's real
        # stderr, so Python raised nothing and there is no traceback to
        # translate - but the reader still asked where it went, and an empty
        # answer would be a lie.
        leaked = ''.join(self._stderr_tail).strip()
        if leaked and not payload.get('error'):
            payload['output'] = (payload.get('output') or '') + leaked + '\n'
        return payload

    def _kill(self):
        proc, self._proc = self._proc, None
        if proc is None:
            return
        # Kill before closing, never the other way round. A reader thread is
        # very likely blocked in readline() on proc.stdout at this point,
        # and closing a stream another thread is reading waits for that
        # stream's lock - so closing first deadlocks instead of cleaning up.
        # Killing makes the child's end of the pipe close, the blocked read
        # returns EOF, and the streams are then free to close.
        if proc.poll() is None:
            self._kill_tree(proc)
            # Reaped on purpose. A killed process that is never waited on
            # stays a zombie, and this is the only place that would wait.
            try:
                proc.wait(timeout=JOIN_GRACE)
            except Exception:
                pass

        # Both helper threads can be blocked on a pipe at this point, and both
        # are in the same position: the process they are reading from is gone
        # but the stream is still locked. Keep the references, give them the
        # grace to notice, and then use them to decide what is safe to close.
        reader = getattr(self, '_reader_thread', None)
        drain = getattr(self, '_stderr_thread', None)
        self._reader_thread = None
        self._stderr_thread = None
        for thread in (reader, drain):
            if thread is not None and thread is not threading.current_thread():
                thread.join(JOIN_GRACE)

        # Close only what nobody is still reading. Closing a stream another
        # thread is blocked in blocks on that stream's lock, which is a hang,
        # not a cleanup. If a thread is still stuck the stream is left to the
        # garbage collector: the process is dead, so the handle goes away with
        # it either way, and leaking a descriptor beats freezing the app.
        def stuck(thread):
            return thread is not None and thread.is_alive()

        streams = [proc.stdin]
        if not stuck(reader):
            streams.append(proc.stdout)
        if not stuck(drain):
            streams.append(proc.stderr)
        for stream in streams:
            try:
                if stream is not None:
                    stream.close()
            except Exception:
                pass

    def _kill_tree(self, proc):
        """Take down the child and anything it started.

        On Windows proc.kill() ends only the process that was spawned, and
        anything the reader's code launched is left running - still holding
        the inherited pipe handles, so the reader thread never reaches the end
        of the stream and a later close deadlocks against it. taskkill with
        /T walks the tree, and it ships with Windows, so this needs no
        dependency added to a build that is meant to work offline.
        """
        try:
            if sys.platform == 'win32':
                subprocess.call(
                    ['taskkill', '/F', '/T', '/PID', str(proc.pid)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=JOIN_GRACE,
                )
            else:
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except Exception:
            # The group may already be gone, or the platform may not have
            # done what was asked. proc.kill() below is the floor.
            pass
        if proc.poll() is None:
            try:
                proc.kill()
            except Exception:
                pass

    def stop(self):
        with self._lock:
            proc = self._proc
            if proc is None:
                return
            stdin = proc.stdin
            if proc.poll() is None and stdin is not None:
                try:
                    stdin.write(json.dumps({'quit': True}) + '\n')
                    stdin.flush()
                except Exception:
                    pass
            self._kill()


class ShellRegistry:
    """The live sessions, and the rules about how many there may be."""

    def __init__(self, max_sessions: int = MAX_SESSIONS,
                 idle_seconds: float = IDLE_SECONDS):
        self._sessions = {}
        self._lock = threading.Lock()
        self._max = max_sessions
        # Compared against a difference of timestamps, so a float is fine and
        # tests can use fractions of a second rather than waiting a whole one.
        self._idle = float(idle_seconds)

    def start(self):
        """Open a session and return its id.

        The id is generated here rather than accepted from the reader, so a
        second visitor cannot walk into somebody else's shell by guessing.
        """
        session = ShellSession()
        sid = secrets.token_urlsafe(24)
        with self._lock:
            self._sessions[sid] = session
        # The cap is enforced after the insert, not before it. Evicting first
        # and then inserting would leave the registry permanently one over
        # the cap: with the dict already full, evict() has no overflow to
        # remove, and the new session then pushes it back past the limit.
        # Enforcing it here also means the overflow is measured against the
        # real size, and the session just created is the newest, so it is
        # never the one evicted.
        self.evict()
        session.start()
        return sid

    def get(self, sid):
        with self._lock:
            session = self._sessions.get(sid or '')
        if session is None:
            return None
        session.last_used = time.time()
        return session

    def drop(self, sid):
        with self._lock:
            session = self._sessions.pop(sid or '', None)
        if session is None:
            return False
        session.stop()
        return True

    def evict(self):
        """Close sessions nobody is using, then any over the cap.

        Returns how many were closed. The sessions are taken out of the dict
        under the lock and stopped outside it, so a slow kill cannot block
        another reader who happens to be starting a session.
        """
        now = time.time()
        doomed = []
        with self._lock:
            for sid, session in list(self._sessions.items()):
                if now - session.last_used > self._idle:
                    doomed.append(self._sessions.pop(sid))
            # Oldest first, so being over the cap costs the least-recently
            # used session rather than whichever happened to be made first.
            overflow = len(self._sessions) - self._max
            if overflow > 0:
                by_age = sorted(self._sessions.items(),
                                key=lambda item: item[1].last_used)
                for sid, _session in by_age[:overflow]:
                    doomed.append(self._sessions.pop(sid))
        for session in doomed:
            try:
                session.stop()
            except Exception:
                pass
        return len(doomed)

    def stop_all(self):
        with self._lock:
            sessions = list(self._sessions.values())
            self._sessions.clear()
        for session in sessions:
            try:
                session.stop()
            except Exception:
                pass

    def count(self):
        with self._lock:
            return len(self._sessions)


# One registry for the process, closed at exit so no child outlives the app.
registry = ShellRegistry()


@atexit.register
def _close_all():
    try:
        registry.stop_all()
    except Exception:
        pass
