# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller onedir spec for Jojo Code Windows installer build.

Produces dist/Jojo Code/ (folder with exe + _internal/).
A folder install is more reliable than onefile: no temp extraction,
faster startup, and fewer antivirus false positives.
"""

import os

block_cipher = None

# Collect static assets, templates, fonts and the language files.
# Every directory the app reads at runtime has to be listed here, or the
# build is missing it and the page that needs it fails.
datas = [
    ('src/jojo_code/static', 'jojo_code/static'),
    ('src/jojo_code/templates', 'jojo_code/templates'),
    ('src/jojo_code/assets', 'jojo_code/assets'),
    ('src/jojo_code/i18n', 'jojo_code/i18n'),
    # The traced child the app launches by path rather than importing. It is
    # read from disk and handed to a child interpreter, so it has to sit beside
    # the package in the bundle and not only inside it as compiled bytecode.
    # Bundled as a module alone it is not on disk, --run-script is pointed at a
    # file that is not there, and every run fails in the exe.
    ('src/jojo_code/trace_runner.py', 'jojo_code'),
    # The shell's bootstrap is launched by path the same way, and its own
    # docstring says the spec lists it in datas. No spec did, so the packaged
    # shell had nothing on disk to start from.
    ('src/jojo_code/shell_bootstrap.py', 'jojo_code'),
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
    name='JojoCode',
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
    icon='src/jojo_code/assets/icon.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='JojoCode',
)