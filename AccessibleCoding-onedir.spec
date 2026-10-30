# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller onedir spec for AccessibleCoding Windows installer build.

Produces dist/AccessibleCoding/ (folder with exe + _internal/).
A folder install is more reliable than onefile: no temp extraction,
faster startup, and fewer antivirus false positives.
"""

import os

block_cipher = None

# Collect static assets, templates, fonts and the language files.
# Every directory the app reads at runtime has to be listed here, or the
# build is missing it and the page that needs it fails.
datas = [
    ('src/accessible_ide/static', 'accessible_ide/static'),
    ('src/accessible_ide/templates', 'accessible_ide/templates'),
    ('src/accessible_ide/assets', 'accessible_ide/assets'),
    ('src/accessible_ide/i18n', 'accessible_ide/i18n'),
    # The traced child the app launches by path rather than importing. It is
    # read from disk and handed to a child interpreter, so it has to sit beside
    # the package in the bundle and not only inside it as compiled bytecode.
    # Bundled as a module alone it is not on disk, --run-script is pointed at a
    # file that is not there, and every run fails in the exe.
    ('src/accessible_ide/trace_runner.py', 'accessible_ide'),
    # The shell's bootstrap is launched by path the same way, and its own
    # docstring says the spec lists it in datas. No spec did, so the packaged
    # shell had nothing on disk to start from.
    ('src/accessible_ide/shell_bootstrap.py', 'accessible_ide'),
]

a = Analysis(
    ['app.py'],
    pathex=['src'],
    binaries=[],
    datas=datas,
    hiddenimports=['flask', 'jinja2', 'werkzeug', 'webview', 'clr', 'pythonnet'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'unittest', 'pydoc'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='AccessibleCoding',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,          # Windowed app (no console)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='src/accessible_ide/assets/icon.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='AccessibleCoding',
)