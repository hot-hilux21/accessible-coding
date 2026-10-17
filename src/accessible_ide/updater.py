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
There is no comparison against the GitHub release list. Instead each build
writes its own version number into the executable *and* publishes the same
number as ``version.json`` next to it. The app fetches that file and
compares it with the version inside the running copy. The build stamps
itself, so the two can never disagree.

That file is published twice, under two moving release tags, so the reader
picks a channel rather than a version. ``beta`` moves on every tagged
release and ``stable`` moves only for a big finished change. The app reads
one small file at a fixed address per channel, which means it needs no
release-list API and no GitHub token.

This replaced a single moving release tagged ``latest``, which was wrong in
a way that only ever showed up as silence. Every push to the main branch
republished that release, and every push is a build, so ``latest`` held a
development version for most of its life. The app read it, decided the
development build was older than the release the reader was already on, and
reported that there was no update - while the release it was comparing
against sat on the same page, unseen. A channel the reader chooses is
also a channel CI cannot quietly refill with something unreleased.

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
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

# Fixed in the source rather than taken from config or an environment
# variable. The whole point of checking a checksum is that the answer does
# not depend on anything the machine running the app can be made to say.
OWNER = 'hot-hilux21'
REPO = 'accessible-coding'
# The file the app downloads when an update is offered is the Setup
# installer, not the portable exe that sits beside it in the release.
#
# An installed AccessibleIDE is a folder, not a file: the program lives next
# to an _internal folder holding the interpreter and every library it uses.
# Replacing the program on its own leaves an older _internal folder beside a
# newer exe, which is a mismatch at best. Replacing both means replacing
# files that are open, in a folder a normal user cannot write to, while the
# reader may still have unsaved work. The installer already does all of that
# correctly, and is already published, so the app hands the job to it.
ASSET_NAME = 'AccessibleIDE-Setup.exe'
MANIFEST_NAME = 'version.json'

RELEASES_BASE = f'https://github.com/{OWNER}/{REPO}/releases'

# Two channels, and which one a reader is on.
#
# "beta" is the working channel and the default: every tagged release lands
# there from build-release.yml, and every push to main lands there from
# build-exe.yml, so a reader on it gets the newest build as soon as it is
# made rather than waiting for the next tag. "stable" is for a big, finished
# change, and only moves when one is tagged. Beta is the default because this
# project has not shipped a stable release yet, and a reader who has never
# chosen should be on the channel that is actually being worked on rather
# than one waiting for a first release.
#
# A main-branch build is stamped from the newest tag plus a run number, so it
# sorts above the tag it was built from and below the next tag. That is what
# lets beta move forward on every push without ever asking a reader to
# install something older than what they have.
#
# The channel name is also the moving release tag the manifest is published
# under, so the app needs no release-list API and no GitHub token: it reads
# one small file at a fixed address.
CHANNELS = ('beta', 'stable')
DEFAULT_CHANNEL = 'beta'


def normalise_channel(channel) -> str:
    """Return a known channel name, falling back to the default.

    A config file can be hand-edited and an older copy has no channel at
    all, so anything unrecognised becomes the default rather than raising
    and turning the check into an error the reader has to read about.
    """
    if isinstance(channel, str) and channel.strip().lower() in CHANNELS:
        return channel.strip().lower()
    return DEFAULT_CHANNEL


def manifest_url(channel: str = DEFAULT_CHANNEL) -> str:
    """The fixed address the given channel publishes its manifest at.

    The asset sits under /releases/download/<tag>/ like any other release
    asset. Only the literal word "latest" has the shorter
    /releases/latest/download/ form, so a channel name must not be put
    where that word used to go.
    """
    return f'{RELEASES_BASE}/download/{normalise_channel(channel)}/{MANIFEST_NAME}'


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

# Copies left behind by an older updater, from before the installer took the
# job over. That one worked by copying the running app to a throwaway name
# and running the copy; Windows will not let a running program delete itself,
# so each of those copies outlived the update that made it. They are named
# apart from the downloaded builds and cleared on the next start, so a reader
# never accumulates them.
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


class _NotFound(Exception):
    """The server answered 404 for a URL we asked for.

    Deliberately not an ``UpdateError``, because a 404 is not one kind of
    thing: a missing manifest means a channel has nothing published on it,
    while a missing build means a release was taken away. Each caller knows
    which it is looking at and gives the reader their own words. Letting it
    escape as a code would put one vague sentence on two unrelated problems,
    and 404 on the manifest is not a fault worth shouting about.
    """


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
    """The version inside the running build.

    Read from the package rather than kept here, so the number reported is
    the one the build was made with. There is one case where the package
    cannot be read: ``tools/check_publish.py`` loads this module straight
    from its file, because the job that publishes a release installs no
    dependencies and importing the package there needs Flask. That job has
    no running build to name, and the request header below is the only thing
    it uses the name for, so an unknown name is honest there.

    In the app the package is always present. If it ever were not, the name
    would reach ``parse_version`` and be refused as unreadable, which is a
    loud failure rather than a wrong comparison.
    """
    try:
        from . import __version__
    except ImportError:
        return 'unknown'
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
        if error.code == 404:
            raise _NotFound(url) from error
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


def fetch_manifest(timeout: int = DEFAULT_TIMEOUT, channel: str = DEFAULT_CHANNEL) -> dict:
    """Download and check the manifest published on ``channel``."""
    try:
        raw = _read_url(
            f'{manifest_url(channel)}?t={int(time.time())}',
            timeout,
            MAX_MANIFEST_BYTES,
        )
    except _NotFound as error:
        # Said in terms of the channel, because that is what the reader
        # chose and the only useful thing to tell them about it.
        raise UpdateError(
            f'nothing has been published on the {normalise_channel(channel)} channel yet',
            code='channel_empty',
        ) from error
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


def should_check(force: bool = False, now: float | None = None) -> bool:
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


def remember_check(now: float | None = None) -> None:
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


def check(force: bool = False, channel: str = DEFAULT_CHANNEL) -> dict:
    """Report whether a newer build exists on ``channel``.

    Never raises: an update check is a background nicety, and a failure here
    must not become a failure to open the editor.
    """
    channel = normalise_channel(channel)
    result = {
        'applicable': is_frozen(),
        'current': current_version(),
        'update_available': False,
        'error': '',
        'error_code': '',
        # Echoed back so the page can say which channel answered, rather
        # than leaving the reader to wonder whether the answer was about
        # the version they are on.
        'channel': channel,
    }
    if not result['applicable']:
        return result
    if not should_check(force):
        result['error'] = 'checked_recently'
        result['error_code'] = 'checked_recently'
        return result
    try:
        manifest = fetch_manifest(channel=channel)
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
        try:
            response = _open_url(url, DEFAULT_TIMEOUT * 10, '*/*')
        except _NotFound as error:
            # The manifest named a build that is not there. Different from an
            # empty channel: something was promised and is now gone, so the
            # reader is told a build is missing rather than that there is
            # nothing new.
            raise UpdateError(
                'the build that was offered is no longer there',
                code='missing_build',
            ) from error
        with response:
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


# The flags the installer is started with. Silent rather than very silent, so
# a progress window is on screen while it works: the reader has just been told
# an update is being applied, and a window saying so is the honest thing to
# show. The rest close this app if it is somehow still holding the files, keep
# the installer from asking questions that have nobody to answer them, and
# stop an update ever turning into a reboot prompt.
INSTALLER_FLAGS = (
    '/SILENT',
    '/CLOSEAPPLICATIONS',
    '/NORESTART',
    '/SUPPRESSMSGBOXES',
    '/NOCANCEL',
)

# ShellExecuteW returns an HINSTANCE-sized value that is really an error code:
# anything at or below 32 means the program was not run. Two documented
# failures sit above that line and have to be named separately, or a refusal
# would be read as an install:
#
#   1223  ERROR_CANCELLED      the reader said no to the permission prompt
#   1155  ERROR_DLL_NOT_FOUND  the shell itself is damaged
#
# Getting this wrong is not loud. The app would record the update as applied,
# delete the record, and leave the reader on the old version with nothing on
# screen to say why.
SHELL_EXECUTE_REFUSALS = frozenset({1155, 1223})


def install(staged: Path) -> bool:
    """Start the staged installer, which replaces this app and closes it.

    The app does not replace itself. It used to, and the way it did was
    broken: it copied its own exe to a throwaway name and ran the copy, with
    no _internal folder beside it, so the copy died on the way up with
    "failed to load the Python DLL". It also only ever replaced one file, and
    an installed copy is a folder.

    The installer is the right tool, and it is already published. It asks
    Windows for the rights it needs, closes the running app through the same
    mechanism the Task Manager uses, and replaces the folder as one operation
    it can roll back. Handing the job over is a few lines rather than a
    second, worse updater.

    Started with ``runas`` rather than ``subprocess``: the installer asks for
    administrator rights, and a process that is not elevated cannot start one
    that is. CreateProcess refuses outright with "the requested operation
    requires elevation" instead of raising the question, so the call that does
    raise it is the one used here. Windows asks the reader, in their own
    language; if they decline, nothing happens and their app is untouched.

    The new build is never started again afterwards. The reader closed the
    app, and opening it back up for them would hide the fact that anything
    had happened at all.

    Returns True once Windows has accepted the request. Raises UpdateError
    when it has not, which leaves the downloaded installer on disk for the
    reader to run themselves.
    """
    if not is_frozen():
        raise UpdateError('updates only apply to the packaged app', code='not_applicable')
    if os.name != 'nt':
        raise UpdateError('updates only apply to the Windows build', code='not_applicable')
    if not staged.is_file():
        raise UpdateError('the downloaded installer is missing', code='missing_build')

    result = _shell_execute(staged, ' '.join(INSTALLER_FLAGS), 'runas')
    # No handle at all, anything at or below 32, or one of the two documented
    # failures that sit above it, all mean the installer never started.
    if not result or result <= 32 or result in SHELL_EXECUTE_REFUSALS:
        raise UpdateError('the update could not be started', code='start_failed')
    return True


def _shell_execute(program: Path, parameters: str, verb: str = 'runas') -> int:
    """Ask the shell to run a program, raising the permission question.

    ``runas`` is the whole reason this is not ``subprocess``: the installer
    carries an administrator manifest, and CreateProcess refuses to start one
    from a process that is not elevated rather than asking. This is the call
    that asks. It is a parameter rather than a literal so the caller states
    which request it is making, and a test can read it back.

    Kept apart from ``install`` so the decision can be tested on its own,
    without a real prompt and without Windows.
    """
    import ctypes

    shell32 = ctypes.windll.shell32
    shell32.ShellExecuteW.restype = ctypes.c_void_p
    shell32.ShellExecuteW.argtypes = [
        ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_wchar_p,
        ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_int,
    ]
    return shell32.ShellExecuteW(None, verb, str(program), parameters, None, 1)


def tidy_helpers() -> None:
    """Remove copies left behind by the updater this replaced.

    Only ever called while the app itself is running, at which point any such
    copy still on disk is one that has already finished or already given up.
    Nothing here can touch the installer the reader may be about to run, or a
    downloaded build waiting beside it, because those are named differently.
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
    """The installer waiting to be run, as (path, version).

    None when there is nothing to do, when the record cannot be read, when
    the file it names is not there, or when that version is not newer than
    the one already running. Returning None in each of those cases is
    deliberate: the caller is on the way out of the app, and the only
    acceptable answer to a record it cannot trust is to do nothing.

    The version check is what stops a loop. A record that outlived the update
    it asked for would otherwise run the same installer on every close, for a
    build the reader already has, each time with its permission prompt.
    """
    try:
        state = json.loads(_state_file().read_text(encoding='utf-8'))
        staged = Path(state['staged'])
        version = str(state['version'])
    except (OSError, ValueError, KeyError, TypeError):
        return None
    if staged.name != ASSET_NAME or not staged.is_file():
        return None
    if not is_newer(version, current_version()):
        return None
    return staged, version


def clear_pending() -> None:
    """Forget the staged build, whether or not it was installed."""
    try:
        _state_file().unlink(missing_ok=True)
    except OSError:
        pass
