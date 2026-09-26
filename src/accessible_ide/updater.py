"""Checking for a newer build of AccessibleIDE, and installing it.

Why this is hand-written rather than a library
---------------------------------------------
Every packaged updater for Python desktop apps is abandoned. The one usually
recommended, ``pyinstaller-updater``, is gone entirely: its PyPI page and its
GitHub repository both return 404. The alternatives are three to five years
stale (``PyUpdater`` 2022, ``PyiUpdater`` 2022, ``pysparkle`` 2023). This
project's stated priority is reliable uptime over features, and an update
mechanism that breaks when its author stops maintaining it is the opposite of
reliable. So the whole thing is a few hundred lines of the standard library
and no new dependencies.

How a version is decided
------------------------
There is no comparison against the GitHub release list. The ``latest`` release
is republished on every push, so a new build of the same version would look
like an upgrade and readers would be nagged for no reason.

Instead each build writes its own version number into the executable *and*
publishes the same number as ``version.json`` next to it. The app fetches
that file and compares it with the version inside the running copy. The build
stamps itself, so the two can never disagree.

Trusting the download
---------------------
A checksum protects the download against corruption and interception, and
this module refuses any URL that is not a release asset of this repository,
so a tampered manifest cannot redirect the download elsewhere. It does not
protect against someone who can publish releases on this repository: that
person can change both the program and its checksum. Closing that gap needs
code signing, which is a separate piece of work.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

# Fixed in the source rather than taken from config or an environment
# variable. The whole point of checking a checksum is that the answer does
# not depend on anything the machine running the app can be made to say.
OWNER = 'hothilux-21'
REPO = 'accessible-coding'
ASSET_NAME = 'AccessibleIDE.exe'
MANIFEST_NAME = 'version.json'

RELEASES_BASE = f'https://github.com/{OWNER}/{REPO}/releases'
MANIFEST_URL = f'{RELEASES_BASE}/latest/download/{MANIFEST_NAME}'

# A desktop IDE is tens of megabytes. Anything far past that is not this
# program, and a runaway download is a way to fill someone's disk.
MAX_DOWNLOAD_BYTES = 200 * 1024 * 1024
MAX_MANIFEST_BYTES = 64 * 1024

# How long to wait before giving up. This runs while someone is trying to
# open their editor, so it must not become a reason for the app to feel slow.
DEFAULT_TIMEOUT = 6

# Checked at most this often, so launching the app fifty times does not ask
# GitHub fifty times. An explicit "check now" ignores this.
CHECK_INTERVAL_SECONDS = 6 * 60 * 60

# How long the replacement helper waits for the app to close before giving up.
# It is long enough that closing the app tomorrow still installs the update,
# and short enough that an abandoned helper does not outlive the machine.
WAIT_LIMIT_SECONDS = 24 * 60 * 60

# Windows will not delete a running program, so a helper copy is left behind
# each time. They are named apart from the downloaded builds, and cleaned up
# on the next start, so a reader never accumulates them.
HELPER_PREFIX = 'updater-'

# Records a verified build that is waiting for the app to close.
STATE_NAME = 'pending.json'

_VERSION_RE = re.compile(
    r'^\s*v?(\d+)(?:\.(\d+))?(?:\.(\d+))?'      # 1, 1.2, 1.2.3
    r'(?:[-.]?([0-9A-Za-z.]+))?\s*$'             # optional suffix
)


class UpdateError(Exception):
    """Something went wrong that the reader can be told about in plain words.

    Every error carries a short ``code`` as well as an English message. The
    code is what the interface shows, because the interface is translated and
    an English sentence handed to a reader who reads Hindi is a bug. The
    message stays for the log and for anyone debugging.
    """

    def __init__(self, message: str, code: str = 'unknown'):
        super().__init__(message)
        self.code = code


def is_frozen() -> bool:
    """True when running as the packaged exe.

    The hosted web version is updated by redeploying the server, so it has no
    exe to replace and must not offer one. The environment variable lets the
    desktop build be exercised from a source checkout during development.
    """
    if os.environ.get('ACCESSIBLE_IDE_UPDATE_TEST') == '1':
        return True
    return bool(getattr(sys, 'frozen', False))


def current_version() -> str:
    """The version inside the running build."""
    from . import __version__
    return __version__


def parse_version(text: str) -> tuple:
    """Turn a version string into something that sorts correctly.

    Plain numbers compare as you would expect. A suffixed build sorts *below*
    the same number without a suffix, so 0.3.0 is newer than 0.3.0-dev.8.
    Among two suffixed builds of the same number, the one with the larger
    suffix number is newer, which is what makes the ever-increasing CI run
    number a usable ordering for development builds.

    Anything unparseable raises rather than guessing, because guessing here
    means offering someone a downgrade.
    """
    if not isinstance(text, str):
        raise UpdateError('version is not text', code='bad_version')
    match = _VERSION_RE.match(text)
    if match is None:
        raise UpdateError(f'cannot read the version {text!r}', code='bad_version')
    major = int(match.group(1))
    minor = int(match.group(2) or 0)
    patch = int(match.group(3) or 0)
    suffix = match.group(4)
    if not suffix:
        # Stable builds sort above every pre-release of the same number.
        return (major, minor, patch, 1, 0)
    # The number inside the suffix is the CI run number for a development
    # build, which is what orders them. Taken from the end of the suffix
    # because the useful number is the last one: "dev.121".
    digits = re.findall(r'(\d+)', suffix)
    if digits:
        return (major, minor, patch, 0, int(digits[-1]))
    # A named pre-release with no number, such as "-beta". All of these sit
    # together at the bottom of their number.
    return (major, minor, patch, 0, 0)


def is_newer(candidate: str, current: str) -> bool:
    """True only when candidate is strictly newer than current."""
    try:
        return parse_version(candidate) > parse_version(current)
    except UpdateError:
        return False


def _allowed_asset_url(url: str) -> str:
    """Return url if it is a release asset of this repository, else raise.

    The manifest is data fetched from the internet, and it names the file to
    download. Without this check, anything that could change the manifest
    could also point the app at a program of their choosing.
    """
    if not isinstance(url, str):
        raise UpdateError('the download address is not text', code='bad_url')
    if not url.startswith(f'{RELEASES_BASE}/download/'):
        raise UpdateError('the download address is not from this project', code='bad_url')
    if not url.startswith('https://'):
        raise UpdateError('the download address is not secure', code='bad_url')
    if '..' in url:
        raise UpdateError('the download address is not valid', code='bad_url')
    return url


def _open_url(url: str, timeout: int, accept: str):
    """Start a download, refusing an obviously oversized one up front."""
    request = urllib.request.Request(url, headers={
        # Without this GitHub serves the API's JSON error bodies, which are
        # small and would be mistaken for a manifest.
        'User-Agent': f'AccessibleIDE/{current_version()}',
        'Accept': accept,
    })
    try:
        response = urllib.request.urlopen(request, timeout=timeout)
    except urllib.error.HTTPError as error:
        raise UpdateError(
            f'could not download from GitHub ({error.code})', code='network'
        ) from error
    except (urllib.error.URLError, OSError) as error:
        # No network, DNS failure, timed out. Not a problem worth shouting
        # about: the app is offline-first and the reader did not ask.
        raise UpdateError('could not reach GitHub to check for updates', code='network') from error
    return response


def _read_url(url: str, timeout: int, limit: int) -> bytes:
    """Read a small URL into memory, refusing anything over limit bytes.

    The length is checked before reading and again while reading, because a
    server can claim a small file and then send an endless one.
    """
    with _open_url(url, timeout, 'application/json' if url.endswith('.json') else '*/*') as response:
        declared = response.headers.get('Content-Length')
        if declared and declared.isdigit() and int(declared) > limit:
            raise UpdateError('the file is larger than expected', code='too_large')
        data = response.read(limit + 1)
    if len(data) > limit:
        raise UpdateError('the file is larger than expected', code='too_large')
    return data


def fetch_manifest(timeout: int = DEFAULT_TIMEOUT) -> dict:
    """Download and check the manifest published alongside the exe."""
    raw = _read_url(
        MANIFEST_URL + f'?t={int(time.time())}',
        timeout,
        MAX_MANIFEST_BYTES,
    )
    try:
        manifest = json.loads(raw.decode('utf-8'))
    except (ValueError, UnicodeDecodeError) as error:
        raise UpdateError('the update information could not be read', code='bad_manifest') from error
    if not isinstance(manifest, dict):
        raise UpdateError('the update information was not in the expected form', code='bad_manifest')
    for field in ('version', 'url', 'sha256', 'size'):
        if field not in manifest:
            raise UpdateError(f'the update information is missing {field}',
                       code='bad_manifest')
    # Checked before anything else uses it.
    _allowed_asset_url(manifest['url'])
    if not isinstance(manifest['version'], str) or not manifest['version']:
        raise UpdateError('the update information has no version number', code='bad_manifest')
    return manifest


def cache_path() -> Path:
    """Where the last check is remembered between launches."""
    base = os.environ.get('LOCALAPPDATA') or str(Path.home())
    return Path(base) / 'AccessibleIDE' / 'update-check.json'


def should_check(force: bool = False, now: float = None) -> bool:
    """False when a check was already made recently, unless force is set."""
    if force:
        return True
    if now is None:
        now = time.time()
    try:
        with open(cache_path(), encoding='utf-8') as handle:
            last = float(json.load(handle).get('checked_at', 0))
    except (OSError, ValueError, TypeError):
        return True
    return (now - last) >= CHECK_INTERVAL_SECONDS


def remember_check(now: float = None) -> None:
    """Note that a check just happened, so the next launch does not repeat it."""
    if now is None:
        now = time.time()
    target = cache_path()
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(target, 'w', encoding='utf-8') as handle:
            json.dump({'checked_at': now}, handle)
    except OSError:
        # Failing to write a cache file only means checking again next time.
        pass


def check(force: bool = False) -> dict:
    """Report whether a newer build exists.

    Never raises: an update check is a background nicety, and a failure here
    must not become a failure to open the editor.
    """
    result = {
        'applicable': is_frozen(),
        'current': current_version(),
        'update_available': False,
        'error': '',
        'error_code': '',
    }
    if not result['applicable']:
        return result
    if not should_check(force):
        result['error'] = 'checked_recently'
        result['error_code'] = 'checked_recently'
        return result
    try:
        manifest = fetch_manifest()
    except UpdateError as error:
        result['error'] = str(error)
        result['error_code'] = error.code
        return result
    remember_check()
    result['latest'] = manifest['version']
    result['url'] = manifest['url']
    result['size'] = manifest['size']
    result['sha256'] = manifest['sha256']
    result['notes'] = str(manifest.get('notes', ''))[:2000]
    result['prerelease'] = bool(manifest.get('prerelease', False))
    # The whole comparison in one place, so "newer" cannot mean two things.
    result['update_available'] = is_newer(manifest['version'], result['current'])
    return result


def update_dir() -> Path:
    """Where a downloaded build waits until the app closes."""
    base = os.environ.get('LOCALAPPDATA') or str(Path.home())
    return Path(base) / 'AccessibleIDE' / 'updates'


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, 'rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def stage(manifest: dict) -> Path:
    """Download the new build and prove it is the one that was offered.

    Streamed to a ``.part`` file and hashed as it arrives, so a build of any
    size never has to fit in memory, and the finished name only ever appears
    once the bytes have been checked. An interrupted or altered download
    therefore cannot be mistaken for a good one.
    """
    url = _allowed_asset_url(manifest['url'])
    wanted_sha = str(manifest['sha256']).strip().lower()
    if not re.fullmatch(r'[0-9a-f]{64}', wanted_sha):
        raise UpdateError('the update information has no usable checksum', code='no_checksum')

    target = update_dir() / manifest['url'].rsplit('/', 1)[-1]
    temporary = target.with_suffix('.part')
    target.parent.mkdir(parents=True, exist_ok=True)

    digest = hashlib.sha256()
    written = 0
    try:
        with _open_url(url, DEFAULT_TIMEOUT * 10, '*/*') as response:
            with open(temporary, 'wb') as handle:
                while True:
                    chunk = response.read(256 * 1024)
                    if not chunk:
                        break
                    written += len(chunk)
                    if written > MAX_DOWNLOAD_BYTES:
                        raise UpdateError('the downloaded file is larger than expected', code='too_large')
                    digest.update(chunk)
                    handle.write(chunk)

        if written == 0:
            raise UpdateError('nothing was downloaded', code='download_failed')
        expected_size = manifest.get('size')
        if isinstance(expected_size, int) and expected_size and written != expected_size:
            raise UpdateError('the downloaded file is the wrong size', code='download_failed')
        if digest.hexdigest() != wanted_sha:
            raise UpdateError('the downloaded file did not match its checksum', code='checksum_failed')

        os.replace(temporary, target)
    except BaseException:
        # A half-downloaded file left under the real name is the one thing
        # that could make a later run install something unchecked, so the
        # attempt is removed whether it failed or was interrupted.
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass
        raise
    return target


def install(staged: Path, relaunch: bool = False) -> bool:
    """Replace the running exe with the staged one.

    Windows will not let a running program overwrite its own file, so this
    does not try. It copies the app to a throwaway name, runs that copy as a
    helper which waits for this process to finish, and only then swaps the
    file. The original is left alone until the replacement is ready, so a
    failure at any point leaves a working app behind.

    Returns False when the helper could not be started, which leaves the
    downloaded build in place for the reader to run themselves.

    ``relaunch`` starts the new build once the swap is done. It is off by
    default and the app leaves it off, because the app has no way of knowing
    whether the reader's work is saved, and closing the app for them is not a
    decision this is entitled to make on their behalf.
    """
    if not is_frozen():
        raise UpdateError('updates only apply to the packaged app', code='not_applicable')
    if not staged.is_file():
        raise UpdateError('the downloaded build is missing', code='missing_build')
    target = Path(sys.executable)
    helper = update_dir() / f'{HELPER_PREFIX}{os.getpid()}.exe'
    try:
        helper.parent.mkdir(parents=True, exist_ok=True)
        # The copy is the point of the whole exercise: a program cannot
        # replace itself on Windows, so the helper runs from a throwaway
        # name and the real file is free by the time it swaps.
        _copy(target, helper)
    except OSError as error:
        raise UpdateError('the update could not be prepared', code='prepare_failed') from error

    command = [
        str(helper), '--apply-update',
        '--wait-for', str(os.getpid()),
        '--staged', str(staged),
        '--target', str(target),
        '--relaunch' if relaunch else '--no-relaunch',
    ]
    try:
        subprocess.Popen(
            command,
            close_fds=True,
            creationflags=getattr(subprocess, 'DETACHED_PROCESS', 0)
            | getattr(subprocess, 'CREATE_NO_WINDOW', 0),
        )
    except OSError as error:
        helper.unlink(missing_ok=True)
        raise UpdateError('the update could not be started', code='start_failed') from error
    return True


def _copy(source: Path, destination: Path) -> None:
    with open(source, 'rb') as reader, open(destination, 'wb') as writer:
        for chunk in iter(lambda: reader.read(1024 * 1024), b''):
            writer.write(chunk)


def tidy_helpers() -> None:
    """Remove helper copies left by earlier updates.

    Only ever called while the app itself is running, at which point any
    helper still on disk is one that has already given up or already
    finished. Nothing here can touch the downloaded build the reader may be
    about to install, because those are named after the release file.
    """
    directory = update_dir()
    if not directory.is_dir():
        return
    for leftover in directory.glob(HELPER_PREFIX + '*'):
        if leftover.is_file() and leftover != Path(sys.executable):
            try:
                leftover.unlink()
            except OSError:
                pass


def _state_file() -> Path:
    return update_dir() / STATE_NAME


def remember_staged(path: Path, version: str) -> None:
    """Record that a verified build is on disk, waiting for the app to close.

    Written after the download has been checked, so a file that exists here
    has already been proved to be the build that was offered. The name of the
    staged file is checked against the one expected when reading it back, so
    a tampered or stale record cannot point the installer at something else.
    """
    state = {'staged': str(path), 'version': version}
    target = _state_file()
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix('.part')
    temporary.write_text(json.dumps(state), encoding='utf-8')
    os.replace(temporary, target)


def pending_build() -> tuple[Path, str] | None:
    """The build waiting to be installed, as (path, version).

    None when there is nothing to do, when the record cannot be read, or when
    the file it names is not there. Returning None in each of those cases is
    deliberate: the caller is on the way out of the app, and the only
    acceptable answer to a record it cannot trust is to do nothing.
    """
    try:
        state = json.loads(_state_file().read_text(encoding='utf-8'))
        staged = Path(state['staged'])
        version = str(state['version'])
    except (OSError, ValueError, KeyError, TypeError):
        return None
    if staged.name != ASSET_NAME or not staged.is_file():
        return None
    return staged, version


def clear_pending() -> None:
    """Forget the staged build, whether or not it was installed."""
    try:
        _state_file().unlink(missing_ok=True)
    except OSError:
        pass


def process_has_exited(pid: int, timeout: float | None = None) -> bool:
    """Has that process finished? True once it is safe to touch its files.

    On Windows this waits on a real handle to the process. It does not poll
    with ``os.kill(pid, 0)``, which was the obvious thing to reach for and is
    wrong here twice over: a process that has finished but whose handle is
    still open somewhere reports as alive, so a loop built on it would never
    end and the update would silently never be installed; and the call is a
    liveness test, not a wait, so it would spin a core for as long as the
    reader had the app open.
    """
    if os.name != 'nt':
        import time
        deadline = None if timeout is None else time.monotonic() + timeout
        while True:
            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                return True
            except OSError:
                # Permission problems mean it exists but is not ours to ask.
                # Treating that as gone would replace a program still running.
                return False
            if deadline is not None and time.monotonic() >= deadline:
                return False
            time.sleep(0.3)

    import ctypes

    SYNCHRONIZE = 0x00100000
    WAIT_OBJECT_0 = 0x00000000
    INFINITE = 0xFFFFFFFF

    kernel32 = ctypes.windll.kernel32
    # A HANDLE is pointer-sized. Left as the default c_int, a real handle
    # above 4 billion is truncated on the way out and every later call is
    # made on a handle that never existed, so the wait would report a
    # finished process the moment it opened one.
    kernel32.OpenProcess.argtypes = [ctypes.c_ulong, ctypes.c_int, ctypes.c_ulong]
    kernel32.OpenProcess.restype = ctypes.c_void_p
    kernel32.WaitForSingleObject.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
    kernel32.WaitForSingleObject.restype = ctypes.c_ulong
    kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
    kernel32.CloseHandle.restype = ctypes.c_int

    handle = kernel32.OpenProcess(SYNCHRONIZE, False, int(pid))
    if not handle:
        # Nothing to wait for: either it never existed or it is already gone.
        return True
    try:
        milliseconds = INFINITE if timeout is None else int(max(timeout, 0) * 1000)
        return kernel32.WaitForSingleObject(handle, milliseconds) == WAIT_OBJECT_0
    finally:
        kernel32.CloseHandle(handle)


def run_helper(arguments: list) -> int:
    """The helper's side of the swap, run by the copied exe.

    Waits for the app to close, puts the new build in its place, and starts
    it again if the reader asked for that. Returns an exit code so the
    workflow can report what happened.
    """
    wanted = {}
    relaunch = False
    index = 0
    while index < len(arguments):
        name = arguments[index]
        if name in ('--wait-for', '--staged', '--target'):
            wanted[name[2:]] = arguments[index + 1]
            index += 2
            continue
        if name == '--relaunch':
            relaunch = True
        index += 1

    try:
        pid = int(wanted['wait-for'])
    except (KeyError, ValueError):
        return 1

    # A cap, so a reader who leaves the app open overnight does not leave a
    # helper sitting there forever. The cap only decides when to give up; it
    # never decides that a running app may be replaced.
    if not process_has_exited(pid, timeout=WAIT_LIMIT_SECONDS):
        return 1

    staged = Path(wanted['staged'])
    target = Path(wanted['target'])
    if not staged.is_file():
        return 1

    # The replacement is written beside the target and moved into place in one
    # step. Moving inside the same folder is what makes it atomic: a reader
    # who starts the app at the wrong moment gets either the whole old build
    # or the whole new one, never half of each.
    incoming = target.with_name(target.name + '.new')
    try:
        _copy(staged, incoming)
        os.replace(incoming, target)
    except OSError:
        # The original was never touched, so the app still starts.
        try:
            incoming.unlink(missing_ok=True)
        except OSError:
            pass
        return 1
    finally:
        # The helper is running from its own copy, which Windows will not let
        # it delete while it is running. A later start tidies it away.
        #
        # Never the target itself. The two are different places in normal
        # use, but if they were ever the same file this would delete the very
        # program that was just put in place.
        try:
            if staged != target:
                staged.unlink(missing_ok=True)
        except OSError:
            pass

    if relaunch:
        try:
            subprocess.Popen([str(target)], close_fds=True)
        except OSError:
            return 1

    # The build is installed, so the record that said one was waiting must go
    # too. Left behind, it would put the same build in again on the next close.
    clear_pending()
    return 0
