"""Tests for telling the reader's own machine apart from the public web.

The desktop app and the hosted site are the same code, and they must not
behave the same way: the desktop app needs to answer only to localhost and
needs a working quit button, while a hosted copy needs neither and must
sandbox anything it runs.

Getting that wrong is not a small mistake, so it is pinned here for every
platform we can think of, including the ones we have not met yet.
"""
import os
import sys
import time
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from accessible_ide import create_app  # noqa: E402
from accessible_ide import routes  # noqa: E402


WEB_SERVERS = ('gunicorn/21.2.0', 'uwsgi', 'waitress/2.1.0', 'uvicorn')


class WebDetectionTests(unittest.TestCase):
    """on_public_web must answer for every host, not just the first one."""

    def call(self, **env):
        clean = {k: v for k, v in os.environ.items()
                 if k not in ('WEB', 'SANDBOX', 'RENDER', 'RAILWAY',
                              'SERVER_SOFTWARE')}
        clean.update(env)
        with mock.patch.dict(os.environ, clean, clear=True):
            return routes.on_public_web()

    def test_a_plain_desktop_run_is_not_the_web(self):
        self.assertFalse(self.call())

    def test_the_desktop_development_server_is_not_the_web(self):
        # Werkzeug is what the desktop app serves on. Treating it as a web
        # server would turn the host check off on the machine that needs it.
        self.assertFalse(self.call(SERVER_SOFTWARE='Werkzeug/3.0.0'))

    def test_web_one_turns_it_on(self):
        self.assertTrue(self.call(WEB='1'))

    def test_sandbox_one_turns_it_on(self):
        self.assertTrue(self.call(SANDBOX='1'))

    def test_web_zero_does_not_turn_it_on(self):
        # Only the exact value counts, so a stray WEB=0 cannot be read as
        # "definitely not the web" by accident in either direction.
        self.assertFalse(self.call(WEB='0'))

    def test_render_is_the_web(self):
        self.assertTrue(self.call(RENDER='true'))

    def test_railway_is_the_web(self):
        self.assertTrue(self.call(RAILWAY='1'))

    def test_every_real_web_server_is_the_web(self):
        for server in WEB_SERVERS:
            with self.subTest(server=server):
                self.assertTrue(self.call(SERVER_SOFTWARE=server))

    def test_an_unknown_host_is_not_assumed_to_be_the_web(self):
        # A host we do not recognise is treated as the reader's own machine,
        # which is the safe direction for the host check to fail: a public
        # copy behind a server we did not anticipate keeps the check, and a
        # desktop copy never has it lifted by accident.
        self.assertFalse(self.call(SOMETHING_ELSE='1'))


class HostHeaderTests(unittest.TestCase):
    """A hosted copy must not refuse requests just for having a real host."""

    def get(self, host, **env):
        clean = {k: v for k, v in os.environ.items()
                 if k not in ('WEB', 'SANDBOX', 'RENDER', 'RAILWAY',
                              'SERVER_SOFTWARE')}
        clean.update(env)
        with mock.patch.dict(os.environ, clean, clear=True):
            app = create_app()
            app.config['TESTING'] = True
            with app.test_client() as client:
                return client.get('/health',
                                  headers={'Host': host})

    def test_the_desktop_refuses_a_foreign_host(self):
        # This is the DNS-rebinding guard. It must keep working.
        self.assertEqual(self.get('evil.example').status_code, 403)

    def test_railway_is_answered_normally(self):
        self.assertEqual(
            self.get('accessible-ide.up.railway.app', RAILWAY='1').status_code,
            200)

    def test_render_is_answered_normally(self):
        self.assertEqual(
            self.get('accessible-coding.onrender.com', RENDER='1').status_code,
            200)

    def test_a_web_server_answers_normally(self):
        self.assertEqual(
            self.get('anything.example',
                     SERVER_SOFTWARE='gunicorn/21.2.0').status_code,
            200)


class ShutdownTests(unittest.TestCase):
    """The quit button must not survive being put on the web."""

    def post(self, **env):
        clean = {k: v for k, v in os.environ.items()
                 if k not in ('WEB', 'SANDBOX', 'RENDER', 'RAILWAY',
                              'SERVER_SOFTWARE')}
        clean.update(env)
        with mock.patch.dict(os.environ, clean, clear=True):
            app = create_app()
            app.config['TESTING'] = True
            with app.test_client() as client:
                return client.post('/api/shutdown',
                                   headers={'Host': 'localhost'})

    def test_the_desktop_may_quit(self):
        with mock.patch.object(routes.os, '_exit') as exit_:
            self.assertEqual(self.post().status_code, 200)
            # The exit is deliberately deferred by a moment so the reply
            # reaches the window first, so it happens on another thread.
            for _ in range(50):
                if exit_.called:
                    break
                time.sleep(0.05)
        exit_.assert_called_once_with(0)

    def test_a_web_server_may_not_quit(self):
        with mock.patch.object(routes.os, '_exit') as exit_:
            reply = self.post(SERVER_SOFTWARE='gunicorn/21.2.0')
        self.assertEqual(reply.status_code, 403)
        exit_.assert_not_called()

    def test_railway_may_not_quit(self):
        with mock.patch.object(routes.os, '_exit') as exit_:
            reply = self.post(RAILWAY='1')
        self.assertEqual(reply.status_code, 403)
        exit_.assert_not_called()


if __name__ == '__main__':
    unittest.main()
