"""Installing extra Python packages, and taking them away again.

A reader types ``import requests``, it is not there, and this turns that into
one sentence and one button rather than a traceback. Installed packages go in
the reader's own data directory and are put on ``sys.path`` for the shell and
the runner, so the app's own files are never touched and nothing needs
administrator rights.

**Nothing is installed without being asked for.** The shell reports the name of
the module that was missing and the page offers to install it; it never installs
on sight. That is a deliberate limit. The alternative - try the import, and if
it fails download and install whatever was named - turns any line of code a
reader pastes into a download from PyPI, and on the hosted copy it would mean
anybody who can paste code can make the server install a package. Offering a
button keeps the useful part and drops the part that turns a typo into a fetch.

**Packages live beside the settings, not inside the app.** installer.iss puts
the app in Program Files with ``PrivilegesRequired=admin``, which is not
writable by a normal user, so installing "into the app" would mean asking for
elevation on every install. Living in the data directory also means an app
upgrade does not take the reader's packages with it.

**pip is run with a real Python, found by asking.** In the packaged build
``sys.executable`` is AccessibleIDE.exe, which has no pip in it, so
``sys.executable -m pip`` cannot work. The installer puts a per-user Python on
PATH, so the interpreter is looked up: the PyInstaller unpack directory first,
then PATH. If none is found, installing says so in words instead of failing
with a stack.

**The reader is never shown pip's output.** pip speaks in resolver jargon and
exit codes. It is captured, and what comes back is either a sentence saying it
worked or one saying why not, in the reader's language.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import sysconfig
from pathlib import Path

__all__ = [
    'PackageError', 'PackageInfo', 'data_dir', 'packages_dir', 'python_path',
    'pip_available', 'installed', 'install', 'uninstall', 'package_for_module',
    'module_of', 'normalise_name', 'MISSING_FROM_MESSAGE',
]


# Where the reader's packages go. Same place as config.json, so there is one
# directory to back up, move or delete, and it is next to the app in every
# sense that matters to somebody uninstalling it.
def data_dir() -> Path:
    """The reader's own directory for this app."""
    override = os.environ.get('ACCESSIBLE_IDE_DATA_DIR')
    if override:
        return Path(override)
    return Path.home() / '.accessible-ide'


def packages_dir() -> Path:
    """Where packages are installed.

    Created on demand rather than at import: importing this module should not
    make a folder appear on somebody's disk, and a read-only home directory
    should not stop the app starting.
    """
    return data_dir() / 'packages'


def _ensure_packages_dir() -> Path:
    target = packages_dir()
    target.mkdir(parents=True, exist_ok=True)
    return target


# pip's own naming rules. Two names that normalise to the same string are the
# same project, and comparing the normalised form is how pip decides whether a
# package is already installed. Reimplemented here because the check has to be
# consistent with what pip does with the name, not merely similar to it.
_NAME_SEPARATORS = re.compile(r'[-_.]+')


def normalise_name(name: str) -> str:
    """A package name the way pip compares them."""
    return _NAME_SEPARATORS.sub('-', (name or '').strip()).lower()


# The import name is not always the PyPI name, and this is where that catches
# people out most often. Importing "PIL" needs Pillow, importing "cv2" needs
# opencv-python, importing "sklearn" needs scikit-learn. Offering to install a
# package that does not exist is worse than not offering, so the ones a
# beginner is most likely to hit are named here.
#
# Only names where the import name differs from the package name. Everything
# else is assumed to be the same on both sides, which is the overwhelmingly
# common case and needs no table.
_MODULE_TO_PACKAGE = {
    'PIL': 'Pillow',
    'cv2': 'opencv-python',
    'sklearn': 'scikit-learn',
    'skimage': 'scikit-image',
    'bs4': 'beautifulsoup4',
    'yaml': 'PyYAML',
    'serial': 'pyserial',
    'dotenv': 'python-dotenv',
    'docx': 'python-docx',
    'pptx': 'python-pptx',
    'xlsxwriter': 'XlsxWriter',
    'Crypto': 'pycryptodome',
    'attr': 'attrs',
    'jwt': 'PyJWT',
    'dateutil': 'python-dateutil',
    'OpenGL': 'PyOpenGL',
    'win32api': 'pywin32',
    'discord': 'discord.py',
    'usb': 'pyusb',
    'fitz': 'PyMuPDF',
}


def package_for_module(module_name: str) -> str:
    """The package to install for a missing module name.

    Falls back to the module name itself, which is right for the large
    majority of packages and is the only sensible guess when there is no table
    entry.
    """
    top = (module_name or '').split('.')[0].strip()
    if not top:
        raise PackageError('bad_name')
    return _MODULE_TO_PACKAGE.get(top, top)


def module_of(distribution: str) -> str:
    """The import name a distribution provides.

    Best effort. Only needed for display: the package manager shows what was
    installed and lets it be removed, so a wrong guess costs a wrong label
    rather than a broken import.
    """
    top = (distribution or '').split('-')[0].split('_')[0].split('.')[0].strip()
    for module, package in _MODULE_TO_PACKAGE.items():
        if normalise_name(package) == normalise_name(distribution):
            return module
    return top


# Pulled out of the shell's ModuleNotFoundError. Kept here so the shell route
# and this module cannot disagree about what a missing module looks like.
#
# The trailing part matters. CPython writes the plain form for a bare import and
# the annotated form for one that failed further in, so both shapes have to
# match:
#   ModuleNotFoundError: No module named 'numpy'
#   ModuleNotFoundError: No module named 'package.sub', line 1
MISSING_FROM_MESSAGE = re.compile(
    r"No module named ['\"]([A-Za-z_][A-Za-z0-9_.]*)['\"]"
)


def missing_module(error_text: str) -> str:
    """The module named in a ModuleNotFoundError, or '' if there isn't one.

    Returns the top-level name. ``from package.sub import thing`` reports
    ``package.sub`` and the reader has to be offered ``package``: installing
    the submodule would fail, because it is not a separate thing on PyPI.
    """
    match = MISSING_FROM_MESSAGE.search(error_text or '')
    if not match:
        return ''
    return match.group(1).split('.')[0]


class PackageError(Exception):
    """Something went wrong, in a form worth showing a reader.

    ``reason`` is a short machine-readable tag the route turns into a sentence
    in the reader's language, so this never carries display text of its own.
    """

    def __init__(self, reason, detail=''):
        super().__init__(reason)
        self.reason = reason
        self.detail = detail or ''


class PackageInfo:
    """One installed package, for the list."""

    __slots__ = ('name', 'version', 'module')

    def __init__(self, name, version, module):
        self.name = name
        self.version = version
        self.module = module

    def as_dict(self):
        return {'name': self.name, 'version': self.version, 'module': self.module}


def _validate_name(name):
    """Reject anything that is not a plain package name.

    pip is invoked as a list, never through a shell, so there is no shell
    injection to guard against. This is about refusing nonsense and names that
    smuggle a path in, so a request cannot point the installer somewhere other
    than the packages directory.
    """
    cleaned = (name or '').strip()
    if not cleaned:
        raise PackageError('bad_name')
    # PEP 503 names: letters, digits, and the separators. Anything else is
    # either a path, a flag, or a URL.
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]*', cleaned):
        raise PackageError('bad_name')
    return cleaned


def _pip_interpreter():
    """A Python that has pip, or None.

    Three candidates, in order of preference:

    1. ``sys.executable``, when it is a real Python. This is the normal case in
       a source checkout and it is already running the app, so it is the
       interpreter whose version the packages will match.
    2. The PyInstaller unpack directory, when frozen. The app's own bundled
       interpreter, which is present and has pip unless the build stripped it.
    3. ``python`` on PATH, which is the per-user Python the installer puts
       there.

    Returns None rather than raising: not having pip is a normal state (the
    hosted copy, a build made without it) and the caller turns it into a
    sentence.
    """
    candidates = []

    if not getattr(sys, 'frozen', False):
        candidates.append(sys.executable)
    else:
        # sys.executable is the exe, not a Python. sys._MEIPASS is the
        # directory PyInstaller unpacked the bundle into, and it holds the
        # interpreter's own files, so it is tried first.
        meipass = getattr(sys, '_MEIPASS', None)
        if meipass:
            for sub in (Path(meipass) / 'base' / 'python.exe',
                        Path(meipass) / 'python.exe'):
                if sub.exists():
                    candidates.append(str(sub))

    # PATH last, and 'python' rather than 'python3': the Windows installer
    # installs 'python', and on the other platforms 'python' is what a normal
    # install provides.
    candidates.append('python')

    seen = set()
    for candidate in candidates:
        if not candidate:
            continue
        key = os.path.normcase(str(candidate))
        if key in seen:
            continue
        seen.add(key)
        try:
            probe = subprocess.run(
                [candidate, '-c', 'import pip, sys; sys.exit(0)'],
                capture_output=True, timeout=20,
                creationflags=_no_window(),
            )
        except (OSError, subprocess.SubprocessError):
            continue
        if probe.returncode == 0:
            return candidate
    return None


def _no_window():
    """Keep a console window from flashing up on Windows.

    A reader who clicks Install should not get a black box appearing and
    vanishing. Only defined on Windows, where the constant exists.
    """
    return getattr(subprocess, 'CREATE_NO_WINDOW', 0) if sys.platform == 'win32' else 0


def pip_available() -> bool:
    """Can packages be installed at all on this machine?"""
    return _pip_interpreter() is not None


def _site_dir():
    """The directory ``--target`` will write into.

    A stable path, not the versioned lib directory, so upgrading Python does
    not silently orphan everything a reader installed. Pure Python packages
    only: a package with a compiled extension has to be built against the
    interpreter doing the importing, which is why a failure here is reported in
    words rather than half-installed.
    """
    return str(packages_dir())


def _run_pip(args, timeout):
    python = _pip_interpreter()
    if python is None:
        raise PackageError('no_pip')
    cmd = [python, '-m', 'pip', '--disable-pip-version-check',
           '--no-input', '--no-color'] + list(args)
    try:
        return subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout,
            creationflags=_no_window(),
        )
    except subprocess.TimeoutExpired:
        raise PackageError('timeout')
    except OSError as exc:
        raise PackageError('pip_failed', str(exc))


def installed() -> list:
    """Every package installed into the packages directory, in name order.

    Read from the ``.dist-info`` directories pip leaves behind rather than by
    asking pip, so the list is fast, cannot fail on a pip problem, and still
    works when pip is missing - which is exactly when a reader most wants to
    see what is already there.
    """
    target = packages_dir()
    if not target.is_dir():
        return []

    found = {}
    for entry in target.iterdir():
        if not entry.name.endswith('.dist-info'):
            continue
        # numpy-1.26.4.dist-info -> numpy, 1.26.4
        stem = entry.name[:-len('.dist-info')]
        name, _, version = stem.rpartition('-')
        if not name:
            name, version = stem, ''
        found[normalise_name(name)] = PackageInfo(name, version,
                                                  module_of(name))

    return sorted(found.values(), key=lambda p: p.name.lower())


def is_installed(name) -> bool:
    """Is this distribution already in the packages directory?"""
    wanted = normalise_name(name)
    return any(normalise_name(p.name) == wanted for p in installed())


def install(name, timeout=300) -> PackageInfo:
    """Install one package into the reader's packages directory.

    Runs with ``--target``, so it cannot touch the system Python or another
    program's environment. A package that is already there is not reinstalled,
    which keeps a retry cheap and stops a second install from half-overwriting
    the first.
    """
    cleaned = _validate_name(name)
    if is_installed(cleaned):
        for package in installed():
            if normalise_name(package.name) == normalise_name(cleaned):
                return package

    target = _ensure_packages_dir()
    result = _run_pip(
        ['install', '--target', _site_dir(), '--upgrade', cleaned],
        timeout,
    )

    if result.returncode != 0:
        raise PackageError('install_failed', _summarise(result))

    # pip can exit 0 having only skipped the work. Trust what is on disk rather
    # than what was printed, so the list and the reader's next import agree.
    if not is_installed(cleaned):
        raise PackageError('not_installed', _summarise(result))

    for package in installed():
        if normalise_name(package.name) == normalise_name(cleaned):
            return package
    raise PackageError('not_installed')


def uninstall(name, timeout=120) -> bool:
    """Remove one package. True if it was there to begin with.

    ``pip uninstall --target`` does not exist, so this removes the distribution
    by hand: its ``.dist-info`` says which files it owns, and those are deleted.
    Files another installed package also claims are left alone, because a shared
    directory entry removed here breaks the package that still needs it.

    Returns False for a package that was not installed, which is the outcome
    the reader asked for rather than a failure.
    """
    cleaned = _validate_name(name)
    target = packages_dir()
    if not target.is_dir():
        return False

    wanted = normalise_name(cleaned)
    info_dir = None
    for entry in target.iterdir():
        if entry.name.endswith('.dist-info') and \
                normalise_name(entry.name[:-len('.dist-info')].rpartition('-')[0]) == wanted:
            info_dir = entry
            break
    if info_dir is None:
        return False

    # Everything this distribution owns, and what every other one owns, worked
    # out before a single file goes. Deleting first and hoping is how one
    # removal takes out the next package's files.
    mine = _owned_files(info_dir)
    others = set()
    for entry in target.iterdir():
        if entry.name.endswith('.dist-info') and entry != info_dir:
            others |= _owned_files(entry)

    import shutil

    removed = 0
    # Directories the distribution owned, deepest first, so they can be tidied
    # afterwards. RECORD lists files rather than folders, so without this a
    # package that is only a directory - toml, for one - leaves an empty folder
    # behind and the reader is told it is gone while the folder is still there.
    folders = set()
    for relative in mine:
        path = target / relative
        if path.is_dir():
            folders.add(path)
        parent = path.parent
        while parent != target:
            folders.add(parent)
            parent = parent.parent

    for relative in mine:
        if relative in others:
            continue
        try:
            path = target / relative
            if path.is_dir():
                shutil.rmtree(path, ignore_errors=True)
            elif path.exists():
                path.unlink()
            removed += 1
        except OSError:
            # A file held open, or locked by antivirus. The .dist-info going is
            # still the important part: it is what makes the package stop being
            # listed and stop being importable.
            continue

    for folder in sorted(folders, key=lambda p: len(p.parts), reverse=True):
        try:
            # rmdir only removes an empty directory, so this can never take out
            # something another package left behind.
            folder.rmdir()
        except OSError:
            continue

    try:
        shutil.rmtree(info_dir, ignore_errors=True)
    except OSError:
        pass
    return True


def _owned_files(info_dir):
    """The paths inside the packages directory that a distribution claims.

    Read from RECORD, the list pip writes of everything it placed. Its lines
    are "path,hash,size" and the path is relative to the install directory. A
    RECORD that cannot be read gives an empty set, which makes the removal
    conservative: the metadata goes and the files are left rather than risking
    the whole directory.
    """
    record = info_dir / 'RECORD'
    if not record.is_file():
        return set()
    try:
        text = record.read_text(encoding='utf-8', errors='replace')
    except OSError:
        return set()

    owned = set()
    for line in text.splitlines():
        if not line.strip():
            continue
        relative = line.split(',', 1)[0].strip().replace('\\', '/')
        if not relative or relative.startswith('/') or '..' in relative.split('/'):
            # An absolute or climbing path is refused: this list is going to
            # delete files, and it has no business reaching outside the
            # directory it was pointed at.
            continue
        owned.add(relative)
    return owned


def _summarise(result):
    """One readable line out of pip's output.

    pip's own last line is usually the useful one ("No matching distribution
    found", "Could not build wheels"), and the rest is resolver detail aimed at
    somebody who knows what a backtracking resolver is. Nothing here is shown
    raw; it goes to the log and the reader gets a sentence.
    """
    lines = [line.strip() for line in (result.stderr or result.stdout or '').splitlines()]
    lines = [line for line in lines if line and not line.startswith((' ', '\t', '-'))]
    for line in reversed(lines):
        if 'ERROR' in line:
            return line.replace('ERROR:', '').strip()[:300]
    return lines[-1][:300] if lines else ''


def python_path():
    """The packages directory as a ``sys.path`` entry, for a child process.

    Passed to the shell and the runner rather than left to inherit, because a
    frozen app's children do not get the parent's ``sys.path`` for free.
    """
    return str(packages_dir())


def sysconfig_check():
    """Whether the running Python can use a ``--target`` install.

    Not used to gate installing. It is here because a build that installed
    binary wheels into the wrong architecture is a confusing failure, and this
    is the cheapest way to catch it early and say something plain.
    """
    return {
        'purelib': sysconfig.get_paths().get('purelib', ''),
        'platform': sysconfig.get_platform(),
    }