"""Tests for deciding whether a port holds this app or a stranger.

The bug these guard against was quiet: on startup the window was attached
to whatever was listening on the preferred port, so a leftover process
that never answered produced a bare "127.0.0.1 could not connect" page
instead of the IDE. A port being bound only proves *something* is there -
these tests pin the difference between "something" and "us", because that
difference is the whole fix.

Everything here stays on this machine and on ephemeral ports, so the
suite cannot collide with a real running AccessibleCoding or with itself.
"""

import http.server
import pathlib
import socket
import sys
import threading
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import app  # noqa: E402  (the real app.py, so the shipped helpers are tested)


class _HealthHandler(http.server.BaseHTTPRequestHandler):
    """Answers /health with the status the test is named after.

    A class attribute rather than a constructor argument because
    http.server only takes the handler class; each server below is a
    subclass with its own answer, standing in for "our app" or "something
    else that happens to be listening".
    """

    health_status = 200

    def do_GET(self):
        if self.path == '/health':
            body = b'ok' if self.health_status == 200 else b'not here'
            self.send_response(self.health_status)
        else:
            body = b'not here'
            self.send_response(404)
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        # The default implementation writes to stderr on every request,
        # which is noise in a test run and nothing more.
        pass


class _Server(http.server.ThreadingHTTPServer):
    daemon_threads = True


def _serve(health_status):
    """Start a local server on an ephemeral port; return it cleaned up."""
    handler = type(f'_Handler{health_status}', (_HealthHandler,),
                   {'health_status': health_status})
    server = _Server(('127.0.0.1', 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def _ephemeral_port():
    """A port that was free a moment ago.

    Bind to 0, read the number, close: nothing else has used it yet in
    practice, and the alternative - hardcoding 5000 - would collide with
    a real AccessibleCoding running beside the tests.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


def _url(port):
    return f'http://127.0.0.1:{port}'


class IsOurServerTests(unittest.TestCase):
    """_is_our_server is what tells our own app apart from a leftover."""

    def test_our_own_health_answer_counts_as_us(self):
        # Without this the launcher would refuse its own running server
        # and start a second copy on another port.
        server = _serve(200)
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        port = server.server_address[1]
        self.assertTrue(app._is_our_server(_url(port), timeout=0.5))

    def test_a_dead_port_is_not_us(self):
        # The stale-process case in its simplest form: the port looks
        # taken by a bind check but nothing ever answers the question.
        port = _ephemeral_port()
        self.assertFalse(app._is_our_server(_url(port), timeout=0.5))

    def test_something_else_answering_is_not_us(self):
        # The regression this file exists for. A real server, healthy,
        # on the port - but not AccessibleCoding, so pointing the window at
        # it would show a stranger's page or a 404 instead of the IDE.
        server = _serve(404)
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        port = server.server_address[1]
        self.assertFalse(app._is_our_server(_url(port), timeout=0.5))


class FreePortTests(unittest.TestCase):
    """_free_port is what moves the launch past a port we cannot use."""

    def test_a_free_port_is_taken_as_is(self):
        # The ordinary case must not be disturbed: when the preferred
        # port is free, the reader's habitual port is where it starts.
        port = _ephemeral_port()
        self.assertEqual(app._free_port(port, tries=10), port)

    def test_a_port_held_by_a_stranger_is_skipped(self):
        # A bare listener that speaks no HTTP: the port is bound, so
        # _port_in_use says yes, and _is_our_server times out waiting for
        # /health - which is exactly when the launch has to move on
        # rather than attach a window to it.
        holder = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        holder.bind(('127.0.0.1', 0))
        holder.listen(1)
        self.addCleanup(holder.close)
        held = holder.getsockname()[1]

        chosen = app._free_port(held, tries=10)

        self.assertNotEqual(chosen, held,
                            'a port with no /health answer was kept')
        if chosen is not None:
            self.assertIn(chosen, range(held, held + 10))

    def test_no_usable_port_in_range_is_reported_not_invented(self):
        # Returning None is what makes the launcher show its plain-English
        # error page instead of guessing; a fallback to the preferred port
        # would silently recreate the original bug.
        self.assertIsNone(app._free_port(0, tries=0))


class PortInUseTests(unittest.TestCase):
    """_port_in_use is the cheap first question everything else builds on."""

    def test_a_listening_socket_reads_as_in_use(self):
        holder = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        holder.bind(('127.0.0.1', 0))
        holder.listen(1)
        self.addCleanup(holder.close)
        self.assertTrue(app._port_in_use(holder.getsockname()[1]))

    def test_a_closed_port_reads_as_free(self):
        port = _ephemeral_port()
        self.assertFalse(app._port_in_use(port))


if __name__ == '__main__':
    unittest.main()
