"""Where the reader's own packages live.

The package manager itself was dropped, but the shell and the one-shot
runner still hand a child process a ``sys.path`` entry for the reader's
packages directory. The directory is created on demand by pip when the
desktop app installs something; on the hosted copy it simply never
exists, and a missing path in ``sys.path`` is harmless.
"""

from __future__ import annotations

import os
from pathlib import Path


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


def python_path():
    """The packages directory as a ``sys.path`` entry, for a child process.

    Passed to the shell and the runner rather than left to inherit, because a
    frozen app's children do not get the parent's ``sys.path`` for free.
    """
    return str(packages_dir())