"""
Main routes for AccessibleIDE.
"""
from flask import Blueprint, render_template, request, jsonify, send_from_directory
import subprocess
import sys
import json
import os
import re
import time
import tempfile
import signal
import threading
from pathlib import Path

from . import i18n
from . import packages
from .utils import colour
from .shell import ShellError, ShellTimeout
from .shell import registry as shell_registry

main_bp = Blueprint('main', __name__)


def on_public_web():
    """True when this process is serving the public web, not one reader.

    This is asked in three places, and being wrong is either a security
    problem or a broken site, so the answer lives here alone rather than
    being worked out again at each call site. Two things go wrong when it
    is spread out: a check is missed and the hosted copy grows a quit
    button, or a company is named and the next host quietly inherits the
    desktop behaviour - which is how a hosted copy ended up refusing every
    request because it was not on the one hostname someone had in mind.

    So it trusts anything that says it is the web, and falls back to asking
    whether a real web server is in front of us rather than the desktop
    app's own.
    """
    if os.environ.get('WEB') == '1' or os.environ.get('SANDBOX') == '1':
        return True

    # Every platform-as-a-service sets a variable of its own name.
    if os.environ.get('RENDER') or os.environ.get('RAILWAY'):
        return True

    # gunicorn, uWSGI, waitress and uvicorn are web servers. Werkzeug, which
    # the desktop app runs on, is not - and that difference is the whole
    # reason this fallback is safe.
    server = (os.environ.get('SERVER_SOFTWARE') or '').lower()
    return any(name in server for name in ('gunicorn', 'uwsgi', 'waitress', 'uvicorn'))


# Access code for the web version. If set, /api/run and /api/config POST
# require it. If NOT set, the code runner is disabled (maintenance mode).
ACCESS_CODE = os.environ.get('ACCESS_CODE', '')

# Sandbox the code runner on the web. The desktop exe runs full Python.
SANDBOX = on_public_web()

# Simple in-memory rate limiting (per IP)
RATE_LIMIT = {}
RATE_MAX = 10          # requests per window
RATE_WINDOW = 60       # seconds

# The shell is metered separately, and more generously.
#
# RATE_MAX suits the runner, which is one request per deliberate click. A
# shell is one request per line the reader types, and the whole point of it is
# trying things: someone working out how a loop behaves will pass nine
# commands inside a minute and then be told to wait while their shell still
# looks perfectly open. Being throttled for using the thing you opened reads
# as the shell being broken, which is the opposite of what it is.
#
# Keyed on the session rather than the address, so one reader exploring cannot
# lock out everybody else behind the same IP - which on the hosted copy is
# every visitor behind one proxy. The session id is unguessable and there are
# at most MAX_SESSIONS of them, and the hosted sandbox still refuses os,
# subprocess and sockets, so a higher ceiling here is a smaller risk than the
# throttle causing is.
SHELL_RATE_MAX = 120

# Modules that are blocked in the sandboxed web runner
BLOCKED_IMPORTS = [
    'os', 'sys', 'subprocess', 'socket', 'requests', 'urllib', 'http',
    'ftplib', 'smtplib', 'telnetlib', 'poplib', 'imaplib', 'importlib',
    'ctypes', 'multiprocessing', 'threading', 'shutil', 'pathlib', 'glob',
    'tempfile', 'pickle', 'marshal', 'shelve', 'sqlite3', 'webbrowser',
    'platform', 'getpass', 'pwd', 'grp', 'resource', 'signal', 'asyncio',
    'concurrent', 'ssl', 'ftplib', 'nntplib', 'cgi', 'cgitb', 'wsgiref',
]

# Builtins that are blocked in the sandboxed web runner
BLOCKED_BUILTINS = [
    'open', 'eval', 'exec', 'compile', '__import__', 'input', 'breakpoint',
    'globals', 'locals', 'vars', 'getattr', 'setattr', 'delattr',
    'memoryview', 'help', 'exit', 'quit', 'copyright', 'credits', 'license',
]

# Patterns that are blocked in the sandboxed web runner
BLOCKED_PATTERNS = [
    r'__\w+__',          # dunder access (e.g. __import__, __builtins__)
    r'\bopen\s*\(', r'\beval\s*\(', r'\bexec\s*\(', r'\bcompile\s*\(',
    r'\binput\s*\(', r'\bbreakpoint\s*\(', r'\bglobals\s*\(', r'\blocals\s*\(',
    r'\bvars\s*\(', r'\bgetattr\s*\(', r'\bsetattr\s*\(', r'\bdelattr\s*\(',
]

IMPORT_RE = re.compile(r'^\s*(?:import|from)\s+([a-zA-Z_][a-zA-Z0-9_]*)', re.MULTILINE)

# Config file path
CONFIG_DIR = Path.home() / '.accessible-ide'
CONFIG_FILE = CONFIG_DIR / 'config.json'

# The first-run setup screen, one step at a time. Defined here rather than in
# the template so the validation below, the rendered progress text and the
# step each panel is tagged with all read the same number.
SETUP_STEPS = ('language', 'font', 'tour')
SETUP_TOTAL_STEPS = len(SETUP_STEPS)

DEFAULT_CONFIG = {
    'font': 'OpenDyslexic',
    'font_size': 16,
    'locale': i18n.DEFAULT_LOCALE,
    # The first-run setup screen shows until this is true. It is a flag
    # rather than "does the config file exist" because the config file is
    # written the first time any setting changes - including changes made
    # by somebody else sharing this machine, or by a version of the app
    # that predates the setup screen. Only the reader's own completion of
    # the screen should hide it.
    'setup_complete': False,
    # Which step of the setup screen to reopen at. Changing the language
    # inside the wizard reloads the page so every word on screen is in the
    # new language, and this is what stops that reload from throwing the
    # reader back to the first step.
    'setup_step': 1,
    # Empty means "use whatever the chosen theme says". Setting it to a
    # hex colour overrides the theme's foreground for code text only.
    'code_color': '',
    # Empty means "use whatever the chosen theme says". Setting it to a
    # hex colour overrides the theme's highlight for the line the reader
    # is working on.
    'highlight_color': '',
    'line_height': 1.6,
    'letter_spacing': 0.5,
    'theme': 'high-contrast',
    'focus_mode': 'gutter',
    'blur_intensity': 0.5,
    'contrast': 'normal',
    # None means "the reader has not chosen yet", so the app follows the
    # operating system's motion preference until they say otherwise. True
    # or False is a deliberate choice and is then the only thing honoured -
    # otherwise a reader who has asked for reduced motion at the OS level
    # could never turn movement back on here.
    'reduce_motion': None,
    # Which material the panels are made of. "off" is the default on
    # purpose: a see-through surface can cost contrast, and contrast is
    # the one thing this app is not allowed to trade away for a nicer
    # look. The names are ours, not Windows' - the panels imitate
    # acrylic and mica rather than using the real Windows materials,
    # which a WebView2 window cannot reach.
    'glass_material': 'off',
    # The tint for those panels. Empty means "whatever the chosen theme
    # uses", which is the safe answer and what the reset button sends.
    'glass_tint': '',
    'tts_enabled': False,
    'tts_engine': 'pyttsx3',
    'tts_voice': '',
    'tts_rate': 0.9,
    # How much of the screen a hover announces: nothing, only the things
    # that do something, or the words on the page as well. Default is the
    # middle one, because a screen reader's own choice matters more.
    'tts_hover_scope': 'controls',
    # Hovering pauses here before speaking, so that passing the pointer
    # across a row of buttons does not start a queue of voices.
    'tts_hover_delay': 600,
    'tts_click_to_speak': True,
    # The speech API does not say whether a voice is male or female, so
    # this is a preference applied to what is installed, not a promise.
    'tts_voice_gender': 'male',
    # Off by default. This is a program that runs on the reader's own
    # machine, and opening it should not send their IP address to a server
    # they never agreed to hear from. Being told about a fix matters, but it
    # is not worth the reader's privacy by default - so the check happens
    # when they press the button, and the switch is here to make it happen
    # on its own afterwards, for anyone who has decided that is a good
    # trade. Switching it off stops the automatic check only: a check the
    # reader asked for still happens, because refusing to answer a direct
    # question is the same as being broken.
    'auto_update': False,
    # Which set of releases this reader wants. Beta is the working channel
    # and gets every tagged release; stable is for a big finished change and
    # is left alone until one is tagged. Beta is the default because it is
    # the channel that is actually being worked on, and a reader who has
    # never chosen should not be parked on one waiting for a first release.
    'update_channel': 'beta',
}

# Editor palettes. These are the single source of truth: the settings
# screen reads them from /api/themes and app.js builds the CodeMirror
# theme from this response, so the code colours can never drift away
# from the surrounding chrome.
# Every value below is checked against its background for WCAG 2.1 AA
# (4.5:1) by tests/test_contrast.py.
THEMES = {
    'high-contrast': {
        'name': 'High Contrast',
        'bg': '#0b0b0b',
        'fg': '#ffffff',
        'selection': '#4d4300',
        # The line the reader is working on. It is a tint of the
        # background, not a strong colour: a strong colour behind the
        # text is how a highlight hides the text, which is the one thing
        # it must never do. Measured by test_contrast.py.
        'highlight': '#1e1e1e',
        'cursor': '#ffd93d',
        'gutter_bg': '#161616',
        'gutter_fg': '#a8a8a8',
        'keyword': '#ff9a9a',
        'string': '#93e6a8',
        'comment': '#b4b4b4',
        'number': '#ffd93d',
        'function': '#93d4ff',
        'variable': '#ffffff',
        'operator': '#ff9a9a',
        'punctuation': '#e8e8e8'
    },
    'dark': {
        'name': 'Dark',
        'bg': '#17181c',
        'fg': '#e6e6e6',
        'selection': '#234a6b',
        'highlight': '#23262c',
        'cursor': '#6bc1ff',
        'gutter_bg': '#1f2126',
        'gutter_fg': '#98a0a8',
        'keyword': '#8fc0f5',
        'string': '#b9d99f',
        'comment': '#93a18d',
        'number': '#e3c583',
        'function': '#8ad4e8',
        'variable': '#dde2e8',
        'operator': '#c2cad2',
        'punctuation': '#c8cfd6'
    },
    'pastel': {
        'name': 'Pastel',
        'bg': '#fbf6ec',
        'fg': '#453f3a',
        'selection': '#e3d2ab',
        'highlight': '#f1ead9',
        'cursor': '#b07d2c',
        'gutter_bg': '#f2ecdf',
        'gutter_fg': '#6b6258',
        'keyword': '#9a4a12',
        'string': '#427a20',
        'comment': '#6f675c',
        'number': '#8a6412',
        'function': '#1f6a94',
        'variable': '#3a4a52',
        'operator': '#584f47',
        'punctuation': '#584f47'
    },
    'light': {
        'name': 'Light',
        'bg': '#fcfcfc',
        'fg': '#2b2b2b',
        'selection': '#bcd6f2',
        'highlight': '#ececec',
        'cursor': '#0057b8',
        'gutter_bg': '#f2f2f2',
        'gutter_fg': '#565656',
        'keyword': '#7a1fa2',
        'string': '#1b6b2f',
        'comment': '#5c5c5c',
        'number': '#a03000',
        'function': '#0057b8',
        'variable': '#2b2b2b',
        'operator': '#3d3d3d',
        'punctuation': '#4a4a4a'
    }
}

def _panel_colour(theme):
    """The colour a theme's panels are painted in.

    Read from the theme table rather than from the stylesheet because the
    server has to agree with the CSS about this number, and a second copy of
    it in Python would eventually be a second copy that is wrong. The
    gutter colour is the same value the stylesheet uses for --panel-bg;
    tests/test_panel_materials.py checks that the two still agree.
    """
    return _palette(theme)['gutter_bg']


# The three token colours that sit on a panel: the words, the quieter
# secondary text, and the error text. These are what a custom panel tint has
# to stay readable behind, so a tint is checked against all three of them.
#
# Kept here, beside the theme table, rather than in utils/colour.py because
# they are the theme's identity and this is where the themes live. The
# stylesheet holds the same three values under --fg, --muted and --error-fg,
# and tests/test_panel_materials.py checks the two have not drifted apart -
# the same way it checks --panel-bg. A custom tint that silently ignored the
# error text would be worse than no tint at all.
PANEL_TEXT = {
    'high-contrast': ('#ffffff', '#c9c9c9', '#ffc1c1'),
    'dark': ('#e6e6e6', '#9aa3ad', '#ffb4a0'),
    'pastel': ('#453f3a', '#736a5f', '#8f2f1a'),
    'light': ('#2b2b2b', '#5f5f5f', '#8f1a1a'),
}


def _palette(theme):
    """A theme's table, falling back to the default for an unknown name."""
    return THEMES.get(theme) or THEMES[DEFAULT_CONFIG['theme']]


def panel_tint_for(theme, tint_hex):
    """The colour the panels actually get, for ``theme``.

    Checked against the theme's own three text colours, so a tint is pulled
    toward the panel only as far as it takes to keep the words readable.

    Shared with the browser through the same arithmetic in static/js/tint.js,
    so a theme change on the client lands where the server would have put it.
    """
    name = theme if theme in PANEL_TEXT else DEFAULT_CONFIG['theme']
    return colour.safe_panel_tint(
        tint_hex, _panel_colour(name), PANEL_TEXT[name]
    )


# Reading fonts. This table is the single source of truth: the settings
# screen and app.js both read it from /api/fonts, so a font can never be
# listed in one place and missing from the other. That duplication is
# what let OpenDyslexic ship as an HTML page under a .otf name while
# every other layer still believed the font existed.
#
# `family` is a CSS font stack. The browser uses the first family that
# actually has the characters on screen, so a missing font degrades to
# a plain sans-serif rather than to the generic `cursive`, which is
# close to unreadable for source code.
#
# `files` lists the font files this app bundles, and is empty for fonts
# taken from the computer. Calibri and Arial belong to Microsoft and
# cannot be redistributed in an open-source project, so they are
# referenced rather than shipped, with a free and metric-compatible
# stand-in behind them (Carlito for Calibri, Liberation Sans for Arial).
# Those stand-ins are not bundled either: they are named so that a user
# who has them installed, or who has installed them once, gets a
# sensible result instead of a broken font.
# Script fallbacks appended to every stack.
#
# None of the reading fonts carry Devanagari or Arabic, so without these a
# Hindi or Arabic reader gets empty boxes no matter which font they picked.
# The browser walks a font stack per character, which is what makes this
# work in the reader's favour: Latin still renders in the font they chose,
# Devanagari falls to Mukta and Arabic to Almarai, within the same line.
# Mukta comes first because it has no Arabic; Almarai comes first in
# Arabic only because nothing else in the stack has any.
SCRIPT_FALLBACKS = ('"Mukta"', '"Almarai"')


def _stack(*families, generic='sans-serif'):
    """Build a CSS font stack that can always render the shipped languages."""
    return ', '.join(list(families) + list(SCRIPT_FALLBACKS) + [generic])


FONTS = {
    'OpenDyslexic': {
        'name': 'OpenDyslexic',
        'family': _stack('"OpenDyslexic3"', '"OpenDyslexic"'),
        'files': ['OpenDyslexic3-Regular.ttf', 'OpenDyslexic3-Bold.ttf'],
        'bundled': True,
        'note': 'Designed for readers with dyslexia.'
    },
    'Atkinson Hyperlegible': {
        'name': 'Atkinson Hyperlegible',
        'family': _stack('"Atkinson Hyperlegible"'),
        'files': [
            'AtkinsonHyperlegible-Regular.ttf',
            'AtkinsonHyperlegible-Bold.ttf',
        ],
        'bundled': True,
        'note': 'Designed to be clear at small sizes and low contrast.'
    },
    'Lexend': {
        'name': 'Lexend',
        'family': _stack('"Lexend"'),
        'files': ['Lexend-Variable.ttf'],
        'bundled': True,
        'note': 'Designed for easy reading.'
    },
    'Nunito': {
        'name': 'Nunito',
        'family': _stack('"Nunito"'),
        'files': ['Nunito-Variable.ttf'],
        'bundled': True,
        'note': 'Rounded and open, which many readers find easier to track.'
    },
    'Calibri': {
        'name': 'Calibri',
        'family': _stack('"Calibri"', '"Carlito"', '"Segoe UI"'),
        'files': [],
        'bundled': False,
        'note': 'From your computer. Carlito is used instead if Calibri is missing.'
    },
    'Arial': {
        'name': 'Arial',
        'family': _stack('"Arial"', '"Liberation Sans"', '"Helvetica"'),
        'files': [],
        'bundled': False,
        'note': 'From your computer. Liberation Sans is used instead if Arial is missing.'
    },
    'Comic Sans MS': {
        'name': 'Comic Sans MS',
        'family': _stack('"Comic Sans MS"', '"Comic Sans"'),
        'files': [],
        'bundled': False,
        'note': 'From your computer.'
    },
    'Courier New': {
        'name': 'Courier New',
        'family': _stack('"Courier New"', 'Courier', generic='monospace'),
        'files': [],
        'bundled': False,
        'note': 'From your computer.'
    }
}


def load_config():
    """Load user configuration from JSON file."""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
            # The frosted panels were first shipped as a single on/off
            # switch before they became a choice of material. Somebody who
            # tried that build has a stored key the validator no longer
            # knows, and an unrecognised setting is an error worth showing
            # them. So the old switch is translated rather than left to
            # break: on becomes frosted, off becomes the default.
            if 'glass' in config:
                config['glass_material'] = (
                    'frosted' if config.pop('glass') else DEFAULT_CONFIG['glass_material']
                )
            # Merge with defaults for any missing keys
            for key, value in DEFAULT_CONFIG.items():
                if key not in config:
                    config[key] = value
            return config
        except Exception:
            pass
    return DEFAULT_CONFIG.copy()


def translator_for(locale):
    """A ``t()`` for a locale, falling back to English for anything unknown.

    Error text is built on the server, but the reader's language is chosen
    in the browser. The client sends its locale with each run so the message
    matches the language actually on screen right now, rather than whatever
    was last written to disk.
    """
    return i18n.make_translator(i18n.normalise(locale) or i18n.DEFAULT_LOCALE)


def request_locale(data):
    """Locale for a request: the one the client sent, else the saved one."""
    sent = i18n.normalise((data or {}).get('locale'))
    if sent:
        return sent
    return i18n.normalise(load_config().get('locale')) or i18n.DEFAULT_LOCALE


# Which sentence to show for each way an update can go wrong. The updater
# itself knows only the short code, so this is the single place a new kind of
# failure is given words in five languages.
UPDATE_ERROR_KEYS = {
    'network': 'update.error_network',
    # A channel nothing has been published to is not a fault and not a
    # network problem, so it is not given the words for one.
    'channel_empty': 'update.error_channel_empty',
    'too_large': 'update.error_too_large',
    'bad_manifest': 'update.error_bad_manifest',
    'no_checksum': 'update.error_no_checksum',
    'download_failed': 'update.error_download_failed',
    'checksum_failed': 'update.error_checksum',
    'not_applicable': 'update.error_not_applicable',
    'missing_build': 'update.error_missing_build',
    'prepare_failed': 'update.error_prepare',
    'start_failed': 'update.error_start',
    'bad_version': 'update.error_bad_version',
    'bad_url': 'update.error_bad_url',
    'checked_recently': 'update.error_checked_recently',
    'unknown': 'update.error_unknown',
}


def save_config(config):
    """Save user configuration to JSON file."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)


# The Python exception types we explain, in the order they are tried when
# reading a traceback. Each one needs a python.<Name> key in every
# catalogue; tests/test_error_translation.py checks that.
PYTHON_ERROR_KEYS = (
    'SyntaxError', 'IndentationError', 'NameError', 'TypeError', 'ValueError',
    'IndexError', 'KeyError', 'AttributeError', 'ImportError',
    'ModuleNotFoundError', 'ZeroDivisionError', 'FileNotFoundError',
    'PermissionError', 'RecursionError', 'MemoryError', 'KeyboardInterrupt',
    'EOFError',
)


def translate_error(error_output, t=None):
    """Turn a Python traceback into a sentence a learner can act on.

    Returns a tuple: (friendly_message, line_number_or_None).

    ``t`` is the reader's translator. It is optional so existing callers and
    tests still get the English wording.
    """
    say = t or i18n.make_translator(i18n.DEFAULT_LOCALE)

    # ''.split('\n') is [''], not [], so an empty traceback needs its own
    # check. Without it the reader saw a bare "Error: " and nothing else.
    lines = [line for line in error_output.strip().split('\n') if line.strip()]
    if not lines:
        return say('python.unknown'), None
    
    # Get the last line (actual error)
    last_line = lines[-1].strip()
    
    # Common error translations
    translations = {
        name: say(f'python.{name}') for name in PYTHON_ERROR_KEYS
    }
    
    # Extract error type
    error_type = None
    for et in translations:
        if et in last_line:
            error_type = et
            break
    
    if error_type:
        friendly = translations[error_type]
        # Add line number if available
        line_number = None
        for line in reversed(lines):
            if 'line' in line and '.py' in line:
                parts = line.split(',')
                for part in parts:
                    if 'line' in part:
                        # Extract the number (e.g. "line 12")
                        match = re.search(r'line\s+(\d+)', part)
                        if match:
                            line_number = int(match.group(1))
                        friendly += say('python.line_hint', part.strip())
                        break
                break
        return friendly, line_number
    
    # Fallback: return last line simplified
    return say('python.fallback', last_line), None


def access_code_ok(data):
    """Check the access code, if one is configured.

    - No ACCESS_CODE set: open (the sandbox is the protection).
    - ACCESS_CODE set: code required.
    """
    if not ACCESS_CODE:
        return True
    return data.get('access_code', '') == ACCESS_CODE


def rate_limited(ip, limit=None):
    """Return True if the IP has exceeded the request limit."""
    now = time.time()
    cap = RATE_MAX if limit is None else limit
    # Clean up old entries occasionally
    if len(RATE_LIMIT) > 1000:
        for key in list(RATE_LIMIT.keys()):
            RATE_LIMIT[key] = [t for t in RATE_LIMIT[key] if now - t < RATE_WINDOW]
            if not RATE_LIMIT[key]:
                del RATE_LIMIT[key]
    recent = [t for t in RATE_LIMIT.get(ip, []) if now - t < RATE_WINDOW]
    if len(recent) >= cap:
        return True
    recent.append(now)
    RATE_LIMIT[ip] = recent
    return False


def client_ip():
    """Best-effort client IP (handles Render's proxy)."""
    forwarded = request.headers.get('X-Forwarded-For', '')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.remote_addr or 'unknown'


def check_sandbox(code, t=None):
    """Return (ok, message) for the sandboxed web runner.

    ``t`` is the caller's translator. It is optional so existing tests and
    any other caller still get plain English.
    """
    say = t or i18n.make_translator(i18n.DEFAULT_LOCALE)

    if not SANDBOX:
        return True, None

    # Block dangerous imports
    for match in IMPORT_RE.finditer(code):
        module = match.group(1)
        top = module.split('.')[0]
        if top in BLOCKED_IMPORTS:
            return False, say('error.blocked_import', module)

    # Block dangerous builtins and patterns
    for pattern in BLOCKED_PATTERNS:
        if re.search(pattern, code):
            return False, say('error.blocked_general')

    return True, None


def _package_version():
    """The version of the build that is actually running.

    Imported inside the function on purpose. routes is imported by the
    package that defines __version__, so asking for it at the top of this
    module would be asking for a name that does not exist yet.
    """
    from . import __version__
    return __version__


@main_bp.route('/')
def index():
    config = load_config()
    locale = i18n.normalise(config.get('locale')) or i18n.DEFAULT_LOCALE
    # The setup step is clamped here, not in the template. A config file
    # written by a future version (or edited by hand) can hold a step this
    # version has no panel for, and the reader would open on a dialog with
    # nothing in it.
    step = config.get('setup_step', 1)
    if not isinstance(step, int) or isinstance(step, bool):
        step = 1
    step = max(1, min(step, SETUP_TOTAL_STEPS))
    return render_template('index.html',
                         config=config,
                         themes=THEMES,
                         # The colour the panels actually get. The stored
                         # tint is whatever the reader chose; this is that
                         # choice pulled toward the panel until the chosen
                         # theme's own panel text stays readable, so it cannot
                         # cost contrast. Computed here so the first paint is
                         # right, and again in the browser on a theme change.
                         glass_tint=panel_tint_for(
                             config.get('theme', DEFAULT_CONFIG['theme']),
                             config.get('glass_tint', ''),
                         ),
                         # The choice itself, separately from the colour above.
                         # The two are not the same value, and the page needs
                         # both: the hex field shows what the reader picked,
                         # the body carries what the panels are painted in.
                         # Reading the choice back out of the painted colour
                         # would mean saving a clamped colour over their
                         # original one the first time they changed anything
                         # else.
                         glass_choice=config.get('glass_tint', ''),
                         # Each theme's panel colour and the text colours that
                         # sit on it, so the browser can work out the same
                         # answer without waiting for /api/themes. Two reasons
                         # it is embedded rather than fetched: the first paint
                         # needs it before any script runs, and a tint computed
                         # against a fallback background is the unreadable
                         # panel this exists to prevent. A tint that ignored
                         # the text colours is the same failure.
                         panel_info={
                             name: {
                                 'panel': _panel_colour(name),
                                 'texts': list(PANEL_TEXT[name]),
                             }
                             for name in PANEL_TEXT
                         },
                         fonts=FONTS,
                         # The version on the badge comes from the build, not
                         # from a line somebody remembered to edit. It used to
                         # be written out in the template, which meant a
                         # reader could be three releases behind and be told
                         # they were current - and there is a whole update
                         # panel on this page insisting the number matters.
                         version=_package_version(),
                         locale=locale,
                         direction=i18n.direction(locale),
                         languages=i18n.available(),
                         catalogue=i18n.load_catalogue(locale),
                         setup_open=not config.get('setup_complete', False),
                         setup_step=step,
                         setup_total=SETUP_TOTAL_STEPS,
                         t=i18n.make_translator(locale))


def _runner_env():
    """The environment for a one-shot run, with the packages folder added.

    Prepended to PYTHONPATH so a package the reader installed wins over one of
    the same name that happens to be elsewhere on the path. The existing value
    is kept, not replaced: something else on the machine may be relying on it.
    """
    env = os.environ.copy()
    target = packages.python_path()
    if target and os.path.isdir(target):
        existing = env.get('PYTHONPATH', '')
        env['PYTHONPATH'] = (target + os.pathsep + existing
                             if existing else target)
    return env


@main_bp.route('/api/run', methods=['POST'])
def run_code():
    data = request.get_json(silent=True) or {}
    code = data.get('code', '')
    t = translator_for(request_locale(data))

    # Access code gate (web version)
    if not access_code_ok(data):
        return jsonify({
            'output': '',
            'error': t('error.access_code_run'),
            'error_line': None,
            'code_required': True
        }), 403

    # Rate limit
    if rate_limited(client_ip()):
        return jsonify({
            'output': '',
            'error': t('error.too_many_requests'),
            'error_line': None
        }), 429

    if not code.strip():
        return jsonify({'output': '', 'error': t('error.no_code'), 'error_line': None})

    # Sandbox check (web version)
    ok, sandbox_message = check_sandbox(code, t)
    if not ok:
        return jsonify({'output': '', 'error': sandbox_message, 'error_line': None})

    # Write code to temp file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(code)
        temp_file = f.name
    
    try:
        # Run with timeout.
        # In the packaged exe, sys.executable is the exe itself, so we
        # re-invoke it with --run-script to execute the temp file.
        if getattr(sys, 'frozen', False):
            cmd = [sys.executable, '--run-script', temp_file]
        else:
            cmd = [sys.executable, temp_file]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=10,
            cwd=tempfile.gettempdir(),
            # The reader's installed packages, so a program that imports
            # something they added works from the Run button as well as from
            # the shell. PYTHONPATH rather than the app's own variable here,
            # because this child runs a file through the interpreter directly
            # and never goes near shell_bootstrap.
            env=_runner_env(),
        )
        
        output = result.stdout
        error = result.stderr
        error_line = None
        
        if error:
            missing = ''
            if 'ModuleNotFoundError' in error:
                missing = packages.missing_module(error)
            error, error_line = translate_error(error, t)
            return jsonify({
                'output': output,
                'error': error,
                'error_line': error_line,
                'missing_module': missing,
                'missing_package': packages.package_for_module(missing) if missing else '',
            })

        return jsonify({'output': output, 'error': '', 'error_line': None,
                        'missing_module': '', 'missing_package': ''})
    
    except subprocess.TimeoutExpired:
        return jsonify({'output': '', 'error': t('error.timeout'), 'error_line': None})
    except Exception as e:
        return jsonify({'output': '', 'error': t('python.fallback', str(e)), 'error_line': None})
    finally:
        # Clean up
        try:
            os.unlink(temp_file)
        except Exception:
            pass


# The Python shell.
#
# A different shape from /api/run on purpose. The runner answers "run this
# file", writes it out and throws it away. A shell has to remember: what you
# imported is still imported, what you defined is still defined. So this
# keeps a child process per reader and talks to it over a pipe. That needs
# more than a route, which is why the machinery lives in shell.py and this is
# only the part the browser talks to.
#
# Every gate the runner has is here too, in the same order. The shell runs
# code, so anything that was true of /api/run is true of this, and a gate
# that was added to one and not the other would be a way around it.

@main_bp.route('/api/shell/start', methods=['POST'])
def shell_start():
    data = request.get_json(silent=True) or {}
    t = translator_for(request_locale(data))

    if not access_code_ok(data):
        return jsonify({
            'success': False,
            'error': t('error.access_code_run'),
            'code_required': True,
        }), 403

    if rate_limited(client_ip()):
        return jsonify({
            'success': False,
            'error': t('error.too_many_requests'),
        }), 429

    # The id is minted here, not accepted from the reader, so nobody can
    # arrive at somebody else's shell by guessing one.
    return jsonify({'success': True, 'session': shell_registry.start()})


@main_bp.route('/api/shell/exec', methods=['POST'])
def shell_exec():
    data = request.get_json(silent=True) or {}
    t = translator_for(request_locale(data))
    code = data.get('code', '')

    if not access_code_ok(data):
        return jsonify({
            'success': False,
            'output': '',
            'error': t('error.access_code_run'),
            'error_line': None,
            'code_required': True,
        }), 403

    if rate_limited('shell:' + str(data.get('session') or client_ip()),
                    SHELL_RATE_MAX):
        return jsonify({
            'success': False,
            'output': '',
            'error': t('error.too_many_requests'),
            'error_line': None,
        }), 429

    if not code.strip():
        return jsonify({
            'success': True,
            'output': '',
            'error': t('shell.no_code'),
            'error_line': None,
        })

    ok, sandbox_message = check_sandbox(code, t)
    if not ok:
        return jsonify({
            'success': True,
            'output': '',
            'error': sandbox_message,
            'error_line': None,
        })

    session = shell_registry.get(data.get('session'))
    if session is None:
        return jsonify({
            'success': False,
            'output': '',
            'error': t('shell.no_session'),
            'error_line': None,
        })

    try:
        result = session.exec(code)
    except ShellTimeout:
        # The child has already been killed. The next command starts a new
        # one, so this costs the reader their session and nothing else.
        return jsonify({
            'success': True,
            'output': '',
            'error': t('shell.timeout'),
            'error_line': None,
        })
    except ShellError as exc:
        # Either the child was gone already and has been replaced, or it
        # could not be read. Both are worth a sentence rather than a stack.
        key = 'shell.restarted' if 'restarted' in str(exc) else 'shell.closed'
        return jsonify({
            'success': True,
            'output': '',
            'error': t(key),
            'error_line': None,
        })

    error = result.get('error', '')
    error_line = None
    missing = ''
    if error:
        # A missing module is the one error with something the reader can do
        # about it, so the name travels back with the message. The page turns
        # it into an offer to install, and nothing is installed until they
        # press the button.
        if result.get('error_type') == 'ModuleNotFoundError':
            missing = packages.missing_module(error)
        error, error_line = translate_error(error, t)

    return jsonify({
        'success': True,
        'output': result.get('output', ''),
        'error': error,
        'error_line': error_line,
        # Empty when the error was not a missing module. package is the name to
        # install, which is not always the name imported (PIL is Pillow).
        'missing_module': missing,
        'missing_package': packages.package_for_module(missing) if missing else '',
    })


@main_bp.route('/api/shell/reset', methods=['POST'])
def shell_reset():
    data = request.get_json(silent=True) or {}
    t = translator_for(request_locale(data))

    if not access_code_ok(data):
        return jsonify({
            'success': False,
            'error': t('error.access_code_run'),
            'code_required': True,
        }), 403

    session = shell_registry.get(data.get('session'))
    if session is None:
        return jsonify({'success': False, 'error': t('shell.no_session')})

    try:
        session.reset()
    except ShellError as exc:
        key = 'shell.restarted' if 'restarted' in str(exc) else 'shell.closed'
        return jsonify({'success': False, 'error': t(key)})

    return jsonify({'success': True})


@main_bp.route('/api/shell/stop', methods=['POST'])
def shell_stop():
    data = request.get_json(silent=True) or {}
    t = translator_for(request_locale(data))

    if not access_code_ok(data):
        return jsonify({
            'success': False,
            'error': t('error.access_code_run'),
            'code_required': True,
        }), 403

    # Stopping a session that is already gone is the outcome the reader
    # asked for, not a failure, so it is reported as done either way.
    shell_registry.drop(data.get('session'))
    return jsonify({'success': True})


# Allowed config keys and their expected types
CONFIG_TYPES = {
    'font': str,
    'font_size': int,
    'code_color': str,
    'highlight_color': str,
    'locale': str,
    'setup_complete': bool,
    'setup_step': int,
    'line_height': (int, float),
    'letter_spacing': (int, float),
    'theme': str,
    'focus_mode': str,
    'blur_intensity': (int, float),
    'contrast': str,
    'reduce_motion': bool,
    'glass_material': str,
    'glass_tint': str,
    'tts_enabled': bool,
    'tts_engine': str,
    'tts_voice': str,
    'tts_rate': (int, float),
    'tts_hover_scope': str,
    'tts_hover_delay': (int, float),
    'tts_click_to_speak': bool,
    'tts_voice_gender': str,
    'auto_update': bool,
    'update_channel': str,
}

# The updater owns the list of channels, and it is imported inside the two
# routes that need it rather than at the top of this module. So the name is
# written out here and a test checks the two agree, rather than importing it
# early and changing that on purpose.
UPDATE_CHANNELS = {'beta', 'stable'}

CONFIG_VALUES = {
    'font': set(FONTS.keys()),
    'theme': set(THEMES.keys()),
    'focus_mode': {'off', 'gutter', 'lines'},
    'contrast': {'normal', 'high'},
    'glass_material': {'off', 'frosted', 'acrylic', 'mica'},
    'locale': set(i18n.LANGUAGES),
    # The wizard has three steps. The bound is not decoration: a corrupt or
    # hand-edited value would otherwise render a screen with no step shown
    # at all, which reads as a blank dialog with no way out.
    'setup_step': set(range(1, SETUP_TOTAL_STEPS + 1)),
    'tts_hover_scope': {'off', 'controls', 'all'},
    'tts_voice_gender': {'any', 'male', 'female'},
    'update_channel': UPDATE_CHANNELS,
}

# Numeric settings are bounded so a bad value can never produce an
# unreadable screen. (minimum, maximum)
CONFIG_RANGES = {
    'font_size': (12, 28),
    'line_height': (1.0, 2.4),
    'letter_spacing': (-0.5, 4.0),
    'blur_intensity': (0.0, 1.0),
    'tts_rate': (0.5, 2.0),
    # Milliseconds. Zero is allowed: someone who moves the pointer
    # deliberately and slowly should not have to wait at all. The top is
    # generous enough to be a deliberate request, low enough that nobody
    # can end up waiting half a minute for a word.
    'tts_hover_delay': (0, 3000),
}

# Voice names come from the operating system, so any string is allowed -
# but not an unbounded one, and never markup.
CONFIG_MAX_LENGTHS = {
    'tts_voice': 200,
    'tts_engine': 50,
}

# Settings that are colours. These are written straight into a style
# attribute, so anything other than a plain hex colour is rejected
# outright: that keeps out CSS injection (`red; background: url(...)`)
# as well as the empty, broken and "transparent" values that would
# quietly make the code unreadable. A hex colour is the one colour
# format that cannot carry a second declaration.
CONFIG_HEX_COLORS = {'code_color', 'glass_tint', 'highlight_color'}

# Only the 3- and 6-digit forms. The 4- and 8-digit forms (with alpha)
# are left out on purpose: alpha is how a colour silently becomes
# unreadable, so it is not offered.
HEX_COLOR_RE = re.compile(r'^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$')


def _describe(key, value, t):
    """Plain explanation of why a setting was rejected.

    The setting is named by its visible label ("Code text colour") rather
    than its config key, so a reader is pointed at the control they used.
    """
    label = t(i18n.CONFIG_LABELS.get(key, key))
    if key in CONFIG_HEX_COLORS:
        return t('config.error_colour', label)
    if key in CONFIG_RANGES:
        low, high = CONFIG_RANGES[key]
        return t('config.error_range', label, low, high)
    if key in CONFIG_MAX_LENGTHS:
        return t('config.error_too_long', label)
    if key in CONFIG_VALUES:
        # Sorted by text, and joined as text. The allowed values are not
        # all words: setup_step is a set of numbers, and building the
        # sentence out of them directly raised a TypeError - which turned
        # a plain 400 refusal into a server error page for every rejected
        # step. The one thing a reader gets when something is wrong must
        # not itself go wrong.
        allowed = ', '.join(sorted((str(v) for v in CONFIG_VALUES[key]), key=str))
        return t('config.error_one_of', label, allowed)
    # A setting we know, sent the wrong sort of value. Saying "not a setting
    # we recognise" here would send the reader looking for a missing control
    # that is sitting right in front of them.
    if CONFIG_TYPES.get(key) is bool:
        return t('config.error_on_off', label)
    if key in CONFIG_TYPES:
        return t('config.error_value', label)
    return t('config.error_unknown', label)


@main_bp.route('/api/config', methods=['GET', 'POST'])
def config_api():
    if request.method == 'GET':
        return jsonify(load_config())

    data = request.get_json(silent=True) or {}
    t = translator_for(request_locale(data))

    # Access code gate (web version)
    if not access_code_ok(data):
        return jsonify({'success': False, 'error': t('error.access_required'), 'code_required': True}), 403

    # The access code is a gate, not a setting. Drop it before validating
    # and before saving, otherwise it is rejected as an unknown key and
    # would be written into config.json in plain text.
    data = {key: value for key, value in data.items() if key != 'access_code'}

    # Validate keys and types
    invalid = []
    for key, value in data.items():
        if key not in CONFIG_TYPES:
            invalid.append(_describe(key, value, t))
            continue
        # bool is a subclass of int in Python, so True would otherwise
        # pass every numeric check (True == 1) and be written into a
        # numeric setting, where the browser then reads it as NaN. The
        # mirror problem is a real bool arriving for a numeric setting, so
        # this applies to every switch rather than one named key.
        if CONFIG_TYPES[key] is bool:
            if not isinstance(value, bool):
                invalid.append(_describe(key, value, t))
                continue
        elif isinstance(value, bool) or not isinstance(value, CONFIG_TYPES[key]):
            invalid.append(_describe(key, value, t))
            continue
        if key in CONFIG_VALUES and value not in CONFIG_VALUES[key]:
            invalid.append(_describe(key, value, t))
            continue
        if key in CONFIG_HEX_COLORS:
            # An empty value is meaningful rather than missing: it means
            # "use the theme's colour", which is exactly what the reset
            # button sends.
            if value and (not isinstance(value, str)
                          or not HEX_COLOR_RE.match(value)):
                invalid.append(_describe(key, value, t))
                continue
        if key in CONFIG_RANGES:
            low, high = CONFIG_RANGES[key]
            if not (low <= value <= high):
                invalid.append(_describe(key, value, t))
                continue
        if key in CONFIG_MAX_LENGTHS and isinstance(value, str) \
                and len(value) > CONFIG_MAX_LENGTHS[key]:
            invalid.append(_describe(key, value, t))
            continue

    if invalid:
        return jsonify({
            'success': False,
            'error': t('config.error_prefix') + ' ' + ' '.join(invalid)
        }), 400

    config = load_config()
    config.update(data)
    save_config(config)
    return jsonify({'success': True, 'config': config})


@main_bp.route('/api/config/reset', methods=['POST'])
def config_reset_api():
    """Put every setting back to the defaults.

    The first-run setup screen is not a setting: somebody who has already
    answered it does not want to be asked again just because they reset
    their font and theme, so setup_complete is carried over rather than
    reset with the rest. Everything else comes from DEFAULT_CONFIG, which
    is the same source a fresh install starts from.
    """
    data = request.get_json(silent=True) or {}
    t = translator_for(request_locale(data))

    # Access code gate (web version), same as the settings endpoint.
    if not access_code_ok(data):
        return jsonify({'success': False, 'error': t('error.access_required'), 'code_required': True}), 403

    current = load_config()
    config = DEFAULT_CONFIG.copy()
    config['setup_complete'] = current.get('setup_complete', False)
    save_config(config)
    return jsonify({'success': True, 'config': config})


@main_bp.route('/api/version')
def version_api():
    """What version is running, and whether it can update itself at all."""
    from . import __version__, updater
    return jsonify({
        'version': __version__,
        'applicable': updater.is_frozen(),
    })


@main_bp.route('/api/update/check', methods=['POST'])
def update_check_api():
    """Look for a newer build.

    The decision about whether to check at all is made here rather than in the
    browser, so the "check automatically" setting cannot be sidestepped by a
    page that simply asks anyway. An explicit request is always answered:
    turning the automatic check off is not a reason to say nothing when
    someone has asked a question.
    """
    from . import updater
    data = request.get_json(silent=True) or {}
    t = translator_for(request_locale(data))
    if not access_code_ok(data):
        return jsonify({
            'success': False,
            'error': t('error.access_required'),
            'code_required': True,
        }), 403

    asked = bool(data.get('force'))
    config = load_config()
    # The channel is read here rather than in the browser, for the same
    # reason the automatic switch is: a page that simply asked for a
    # different channel must not be able to talk the reader onto one.
    channel = updater.normalise_channel(config.get('update_channel'))
    # The fallback matches the default above on purpose. A config file
    # written by an older build can be missing this key, and treating that
    # as "on" would quietly reintroduce the phone-home the default is off
    # to avoid - silently, for readers who never had the switch at all.
    if not asked and not config.get('auto_update', False):
        return jsonify({
            'success': True,
            'applicable': updater.is_frozen(),
            'current': updater.current_version(),
            'update_available': False,
            'automatic': False,
            'channel': channel,
            'error': '',
        })

    result = updater.check(force=asked, channel=channel)
    result['success'] = True
    result['automatic'] = not asked
    # The updater raises English sentences; the reader is reading one of five
    # languages. The code is looked up in the catalogue so the sentence that
    # reaches the screen is in the reader's own words. The English text stays
    # in the field only when a code has no catalogue entry, which is a bug
    # worth seeing rather than a sentence worth showing.
    code = result.get('error_code') or ''
    if code:
        key = UPDATE_ERROR_KEYS.get(code, 'update.error_unknown')
        result['error_text'] = t(key)
    return jsonify(result)


@main_bp.route('/api/update/install', methods=['POST'])
def update_install_api():
    """Download the new build and check it, ready to be swapped in on close.

    This deliberately does not touch the running program. Windows will not
    allow a running exe to replace itself, and doing it any other way risks
    ending the reader's session mid-sentence. The download happens now; the
    swap happens when they close the app, which is a moment they chose.
    """
    from . import updater
    data = request.get_json(silent=True) or {}
    t = translator_for(request_locale(data))
    if not access_code_ok(data):
        return jsonify({
            'success': False,
            'error': t('error.access_required'),
            'code_required': True,
        }), 403

    if not updater.is_frozen():
        return jsonify({
            'success': False,
            'error_code': 'not_applicable',
            'error_text': t(UPDATE_ERROR_KEYS['not_applicable']),
        }), 400

    # The channel the reader is on, for the same reason the check reads it
    # from the config rather than from the request: the thing that gets
    # downloaded has to be the thing the settings screen says it is.
    result = updater.check(
        force=True,
        channel=updater.normalise_channel(
            load_config().get('update_channel')),
    )
    if not result.get('update_available'):
        # Nothing to install. Saying so plainly beats downloading whatever
        # the manifest happened to name.
        return jsonify({
            'success': False,
            'error_code': 'no_update',
            'error_text': t('update.error_no_update'),
        }), 400

    try:
        staged = updater.stage({
            'url': result['url'],
            'sha256': result['sha256'],
            'size': result['size'],
        })
    except updater.UpdateError as error:
        return jsonify({
            'success': False,
            'error_code': error.code,
            'error_text': t(UPDATE_ERROR_KEYS.get(error.code, 'update.error_unknown')),
        }), 400

    # Only recorded once the bytes have been checked, so nothing downstream
    # can act on a download that was never verified.
    updater.remember_staged(staged, result['latest'])
    return jsonify({
        'success': True,
        'version': result['latest'],
        'size': result['size'],
    })


@main_bp.route('/api/themes')
def themes_api():
    return jsonify(THEMES)


@main_bp.route('/api/fonts')
def fonts_api():
    return jsonify(FONTS)


# The package manager. Reading and changing what the reader has added to their
# own copy of Python.
#
# Three rules hold across all three routes.
#
# Installing is never automatic. The shell reports a missing module and this
# offers to install it; nothing is downloaded until the reader presses the
# button. See packages.py for why that limit is deliberate.
#
# The hosted copy cannot install. It runs for many readers at once on one
# machine, so a per-reader package folder is not meaningful and a server that
# installs whatever it is asked to is a much larger hole than one on somebody's
# own laptop. It says so rather than pretending.
#
# Failures come back as a reason code, not as pip's output. pip speaks in
# resolver jargon; the reader gets a sentence and the detail goes to the log.
@main_bp.route('/api/packages')
def packages_api():
    # Asked with GET because listing changes nothing. It carries no sentence
    # back, so there is no locale to honour here; the panel reads the failure
    # wording from the two routes that do fail.
    return jsonify({
        'installed': [p.as_dict() for p in packages.installed()],
        'can_install': packages.pip_available() and not SANDBOX,
        'directory': str(packages.packages_dir()),
    })


@main_bp.route('/api/packages/install', methods=['POST'])
def packages_install():
    data = request.get_json(silent=True) or {}
    t = translator_for(request_locale(data))

    # The same two gates as /api/run, in the same order. Installing is a bigger
    # thing to allow than running a file: it changes what is on the machine.
    # A route that skipped them would be a way round both.
    if not access_code_ok(data):
        return jsonify({
            'success': False,
            'error': t('error.access_code_run'),
            'code_required': True,
        }), 403

    if rate_limited(client_ip()):
        return jsonify({
            'success': False,
            'error': t('error.too_many_requests'),
        }), 429

    if SANDBOX:
        return jsonify({
            'success': False,
            'error': t('packages.not_here'),
        }), 403

    name = data.get('name', '')
    try:
        package = packages.install(name)
    except packages.PackageError as exc:
        # 400 for a name that was never going to work, 502 for one that might
        # have. The reader sees the same sentence either way.
        status = 400 if exc.reason == 'bad_name' else 502
        return jsonify({
            'success': False,
            'reason': exc.reason,
            'error': t(f'packages.{exc.reason}'),
        }), status

    # The shell holds its own copy of everything it has imported, so a newly
    # installed package is not visible to the running session until it is
    # restarted. The id is handed back so the page can do that rather than
    # leaving the reader to press a button and see nothing happen.
    session_id = data.get('session') or ''
    if session_id and shell_registry.get(session_id):
        try:
            shell_registry.get(session_id).reset()
        except ShellError:
            # The reset failing is not a failed install. The package is on disk;
            # the next command respawns the child anyway.
            pass

    return jsonify({'success': True, 'package': package.as_dict()})


@main_bp.route('/api/packages/uninstall', methods=['POST'])
def packages_uninstall():
    data = request.get_json(silent=True) or {}
    t = translator_for(request_locale(data))

    # The same gates as install, for the same reason: this one deletes things.
    if not access_code_ok(data):
        return jsonify({
            'success': False,
            'error': t('error.access_code_run'),
            'code_required': True,
        }), 403

    if rate_limited(client_ip()):
        return jsonify({
            'success': False,
            'error': t('error.too_many_requests'),
        }), 429

    if SANDBOX:
        return jsonify({
            'success': False,
            'error': t('packages.not_here'),
        }), 403

    name = data.get('name', '')
    try:
        removed = packages.uninstall(name)
    except packages.PackageError as exc:
        return jsonify({
            'success': False,
            'reason': exc.reason,
            'error': t(f'packages.{exc.reason}'),
        }), 400 if exc.reason == 'bad_name' else 502

    # Same reason as the install: a module already imported stays in memory
    # until the child is new. Restarting is what makes the removal real rather
    # than only reported.
    session_id = data.get('session') or ''
    if session_id and shell_registry.get(session_id):
        try:
            shell_registry.get(session_id).reset()
        except ShellError:
            pass

    return jsonify({
        'success': True,
        'removed': removed,
        'installed': [p.as_dict() for p in packages.installed()],
    })


# Python's mimetypes has no entry for .ttf on Windows, so fonts were
# being served as application/octet-stream. Browsers tolerate that, but
# a font served with a real font/* type is the correct answer and avoids
# surprises in stricter clients and in the packaged .exe.
FONT_MIME_TYPES = {
    '.ttf': 'font/ttf',
    '.otf': 'font/otf',
    '.woff': 'font/woff',
    '.woff2': 'font/woff2',
}


@main_bp.route('/assets/fonts/<path:filename>')
def serve_font(filename):
    mimetype = FONT_MIME_TYPES.get(Path(filename).suffix.lower())
    return send_from_directory('assets/fonts', filename, mimetype=mimetype)


@main_bp.route('/health')
def health():
    return jsonify({'status': 'ok'})


@main_bp.route('/api/shutdown', methods=['POST'])
def shutdown():
    """Stop the desktop app server. Local-only: never exposed on the web."""
    if on_public_web():
        t = translator_for(request_locale(request.get_json(silent=True) or {}))
        return jsonify({'success': False, 'error': t('error.not_on_web')}), 403

    def _stop():
        time.sleep(0.3)  # let the response flush first
        os._exit(0)

    threading.Thread(target=_stop, daemon=True).start()
    return jsonify({'success': True})