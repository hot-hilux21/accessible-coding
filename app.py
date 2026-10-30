#!/usr/bin/env python3
"""
AccessibleCoding - Main entry point.

Desktop app: runs a local Flask server in a background thread and shows
the IDE in a native window (PyWebView / WebView2) - no browser needed.

Web deployment (Oracle Cloud) uses `wsgi:app` via gunicorn and never reaches
the `__main__` block below.
"""
import os
import sys
import runpy
import socket
import threading
import time
import urllib.request

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from accessible_ide import create_app

app = create_app()


def _port_in_use(port):
    """Return True if something is already listening on the port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(('127.0.0.1', port))
            return False
        except OSError:
            return True


def _wait_for_server(url, timeout=15):
    """Block until the local server responds, or return False on timeout."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            urllib.request.urlopen(url + '/health', timeout=1)
            return True
        except Exception:
            time.sleep(0.2)
    return False


def _is_our_server(url, timeout=2):
    """Return True if a healthy AccessibleCoding is answering at this url.

    A port being bound only proves *something* is listening on it. After an
    update, a half-dead copy of this app can still hold the port without
    serving anything useful, and pointing a window at it produces a bare
    "cannot connect" page. Asking /health is what tells our own app apart
    from a leftover process.
    """
    try:
        with urllib.request.urlopen(url + '/health', timeout=timeout) as response:
            return response.status == 200
    except Exception:
        return False


def _free_port(preferred, tries=10):
    """Find a usable port, starting at the preferred one.

    If the preferred port is held by a stale process that never answers
    /health, we move to the next one rather than attaching a window to a
    server that cannot respond.
    """
    for port in range(preferred, preferred + tries):
        if not _port_in_use(port):
            return port
        if _is_our_server(f'http://127.0.0.1:{port}'):
            return port
    return None


def _show_error(message):
    """Tell the reader what went wrong, in a window they can read.

    Without this, a startup failure either vanishes into a console nobody is
    watching or surfaces as a raw browser-style connection error, which for a
    dyslexic reader is the least helpful way to be told something broke.
    """
    try:
        import webview
        webview.create_window(
            'AccessibleCoding',
            html=(
                '<!DOCTYPE html><html lang="en"><head>'
                '<meta charset="utf-8"><title>AccessibleCoding</title></head>'
                '<body style="font-family:sans-serif;padding:2em;'
                'font-size:18px;line-height:1.6">'
                f'<h1 style="font-size:1.4em">AccessibleCoding could not start</h1>'
                f'<p>{message}</p>'
                '<p>Close this window and open AccessibleCoding again.</p>'
                '</body></html>'
            ),
            width=700,
            height=420,
            min_size=(500, 300),
        )
        webview.start()
    except Exception:
        print(message)


def _start_server(port):
    """Run the Flask server (debug off, localhost only)."""
    debug = os.environ.get('FLASK_DEBUG', '0') == '1'
    app.run(host='127.0.0.1', port=port, debug=debug, use_reloader=False)


def _run_desktop(port):
    """Launch the native desktop window (PyWebView)."""
    import webview  # imported lazily so the web deployment needs no pywebview

    # An already-running copy only counts if it actually answers. A leftover
    # process can hold the port without serving, and pointing a window at it
    # is what produced the bare "cannot connect" page.
    existing = f'http://127.0.0.1:{port}'
    if _port_in_use(port) and _is_our_server(existing):
        webview.create_window(
            'AccessibleCoding',
            existing,
            width=1200,
            height=800,
            min_size=(800, 600),
        )
        webview.start()
        return

    # Nothing healthy on the preferred port: take the first one that is free
    # (or already serving our own app) rather than fighting a stale process.
    chosen = _free_port(port)
    if chosen is None:
        _show_error(
            'Another program is using the local address AccessibleCoding needs, '
            'and it is not responding.'
        )
        sys.exit(1)
    url = f'http://127.0.0.1:{chosen}'

    # Start the server, wait until it is ready, then open the window.
    threading.Thread(target=_start_server, args=(chosen,), daemon=True).start()
    if not _wait_for_server(url):
        _show_error(
            'The local part of AccessibleCoding did not start. This is a problem '
            'on this computer, not with your internet connection.'
        )
        sys.exit(1)

    _tidy_leftover_updates()

    webview.create_window(
        'AccessibleCoding',
        url,
        width=1200,
        height=800,
        min_size=(800, 600),
    )
    webview.start()

    # Window closed -> stop the server and exit.
    #
    # os._exit skips cleanup, so anything that has to happen on the way out
    # has to happen here. Starting the staged installer is one of those
    # things: it replaces this app, so it can only be started once the app is
    # on its way out, and this is the moment that is decided.
    _apply_staged_update_on_exit()
    os._exit(0)


def _tidy_leftover_updates():
    """Clear away copies left behind by the updater this replaced.

    That updater worked by copying the app aside and running the copy, and
    Windows refuses to delete a running program, so each update left its copy
    behind. Doing this at start rather than on the way out means the tidy-up
    runs with nothing of ours running, which is the only time the files are
    genuinely free.
    """
    try:
        from accessible_ide import updater
        if updater.is_frozen():
            updater.tidy_helpers()
    except Exception:
        pass


def _apply_staged_update_on_exit():
    """Hand a downloaded installer over, if one is waiting.

    A failure here must not stop the app closing, and must not be noisy: the
    reader has already shut the window, and a message on a console they have
    stopped looking at helps nobody. The installer stays on disk either way,
    and a record that was not handed over is offered again on the next close.
    """
    try:
        from accessible_ide import updater
        if not updater.is_frozen():
            return
        waiting = updater.pending_build()
        if waiting is None:
            return
        staged, _version = waiting
        if updater.install(staged):
            updater.clear_pending()
    except Exception:
        pass


if __name__ == '__main__':
    # Hidden mode used by the code runner inside the packaged exe.
    # The exe cannot call a separate python.exe, so it re-invokes itself
    # with --run-script to execute a temp file and exit.
    if len(sys.argv) >= 3 and sys.argv[1] == '--run-script':
        runpy.run_path(sys.argv[2], run_name='__main__')
        sys.exit(0)

    port = int(os.environ.get('PORT', 5000))
    _run_desktop(port)
