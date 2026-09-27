"""The module index: every standard library module, in plain English.

The Python documentation has a module index. It is complete and accurate
and almost unusable for the person this app is for: the entries are
grouped by the name of the module that implements them, and there is no
way to search it by what you want to do. Somebody who wants to save a
file does not know that the answer is called ``shutil``.

So this is a second index over the same set of names, organised the other
way round. Each entry says in one sentence what the module is *for*, and
carries a short program that actually runs.

Three things this module is careful about.

**Availability is measured, not declared.** ``curses`` and ``termios``
are real modules that do not exist on Windows; ``tkinter`` may simply not
be installed. Rather than keep a hand-written list of what is missing -
which would be wrong on the first machine somebody ran it on - the index
asks the interpreter, and says so.

**The web runner is not the desktop app.** The hosted version refuses
some imports and most file access, so an example that cannot run there is
marked instead of being offered and then refused with a message about
sandboxes. The marker is derived from the same list the runner uses, so
it cannot drift.

**Search matches how people ask.** Someone types "save a file", not
"shutil". Every entry also carries a set of the words a reader is likely
to reach for, so the search finds it by the job rather than by the name.
"""
from __future__ import annotations

import functools
import importlib.util
import re

from .modules_data import ADVANCED, EVERYDAY, GROUP_ORDER, START, ENTRIES

__all__ = [
    'GROUPS', 'LEVELS', 'ModuleEntry', 'all_entries', 'search', 'find',
    'available_here', 'runs_in_web',
]


# Words a reader is likely to type, per module, that are not in the name.
# This is the difference between an index and a lookup table. These are
# the everyday words: "save", "shuffle", "money", "password".
#
# Deliberately small. A long list of keywords makes the results noisier,
# not clearer - a reader who types "sort" should be offered the module
# that sorts, not every module whose source happens to contain the word.
_WORDS = {
    'shutil': 'copy move delete folder backup save file files',
    'pathlib': 'path folder name address',
    'os': 'folder computer environment current working directory',
    'tempfile': 'temporary scratch throw away clean up',
    'zipfile': 'zip compress archive bundle extract',
    'glob': 'find search wildcards list files pattern',
    'csv': 'table spreadsheet row column excel comma read write',
    'json': 'settings data object nested read write',
    'configparser': 'settings ini section preferences',
    'sqlite3': 'database table search records store',
    'shelve': 'save keep store remember between runs',
    'pickle': 'save keep store between runs',
    're': 'pattern search text find match email validate',
    'difflib': 'compare difference changed similar',
    'textwrap': 'wrap long line width paragraph',
    'string': 'words text capital letters spaces',
    'unicodedata': 'characters accents symbols letters',
    'math': 'square root power round pi trigonometry',
    'random': 'dice shuffle choose chance lottery password',
    'secrets': 'password token secure random private key',
    'statistics': 'average mean median average spread',
    'decimal': 'money exact rounding decimals',
    'fractions': 'fractions thirds halves exact',
    'datetime': 'date today time now days weeks',
    'time': 'measure seconds speed clock how long',
    'calendar': 'calendar month weekdays dates',
    'zoneinfo': 'time zones utc international clocks',
    'collections': 'count group queue ordered dictionary',
    'itertools': 'loops repeat chain zip combinations',
    'functools': 'cache remember function repeat work',
    'bisect': 'search find ordered sorted middle',
    'heapq': 'smallest largest top ten priority',
    'copy': 'duplicate clone independent',
    'enum': 'choices named constants options fixed',
    'dataclasses': 'record class object blueprint',
    'threading': 'parallel simultaneous background tasks',
    'multiprocessing': 'parallel separate processes cores',
    'concurrent': 'parallel at the same time pool',
    'asyncio': 'await async waiting slow network',
    'subprocess': 'run program command external call',
    'platform': 'windows mac linux operating system computer',
    'sys': 'version arguments command line running program',
    'argparse': 'arguments options command line flags',
    'getopt': 'arguments options command line flags',
    'logging': 'messages record debug warnings output',
    'unittest': 'tests testing checks assertions',
    'doctest': 'tests examples documentation checks',
    'pdb': 'debug stop break step inspect',
    'traceback': 'errors stack trace what went wrong',
    'pprint': 'print readable nicely format',
    'inspect': 'signature documentation what is this',
    'typing': 'types hints annotations what it expects',
    'io': 'read write stream buffers text',
    'ssl': 'secure https certificates encryption',
    'urllib': 'web address url fetch download links',
    'http': 'web requests responses status codes',
    'socket': 'connections network ports',
    'smtplib': 'email send messages',
    'email': 'email messages headers address',
    'ipaddress': 'ip addresses networks subnets',
    'tomllib': 'settings toml configuration',
    'struct': 'binary packed bytes format',
    'base64': 'encode decode safe text binary',
    'hashlib': 'checksum fingerprint hash sha',
    'hmac': 'signature authenticate verify secret',
    'uuid': 'unique identifiers ids names',
    'wave': 'sound audio wav',
    'turtle': 'drawing graphics pictures canvas',
    'tkinter': 'windows buttons boxes interface forms gui',
    'curses': 'terminal menu text interface',
    'ctypes': 'call other programs libraries dll',
    'gettext': 'translation languages strings',
    'locale': 'language country formats regional',
    'tokenize': 'split source code words symbols',
    'ast': 'read code structure parse',
    'dis': 'slow performance instructions assembly',
    'profile': 'slow performance timing where time goes',
    'tracemalloc': 'memory leaking usage',
    'gc': 'memory freeing cleaning up',
    'weakref': 'memory references not keeping alive',
    'atexit': 'when program ends closing down goodbye',
    'stat': 'file size permissions details',
    'filecmp': 'compare files same different',
    'fileinput': 'several files at once read in turn',
    'gzip': 'compress smaller squeeze',
    'bz2': 'compress smaller squeeze',
    'lzma': 'compress smaller squeeze',
    'zlib': 'compress smaller squeeze',
    'tarfile': 'archive backup bundle tar',
    'mmap': 'large files memory big',
    'binascii': 'binary bytes encode',
    'cmath': 'complex imaginary numbers waves',
    'array': 'compact lists of numbers memory',
    'operator': 'functions for operators',
    'colorsys': 'colours blending rgb hue',
    'graphlib': 'shortest route network order dependencies',
    'contextlib': 'tidying up reliably resources',
    'contextvars': 'per task variables context',
    'abc': 'rules interfaces base classes',
    'types': 'what kind of thing is this',
    'numbers': 'number types whole real complex',
    'copyreg': 'copying objects of your own class',
    'linecache': 'source lines error messages',
    'symtable': 'names local global scope',
    'opcode': 'instructions machine code',
    'sre_compile': 'regular expressions patterns',
    'sre_parse': 'regular expressions patterns',
    'sre_constants': 'regular expressions patterns',
    'pydoc': 'help documentation built in',
    'pydoc_data': 'help documentation data',
    'rlcompleter': 'tab completion suggestions',
    'readline': 'editing typed lines at the prompt',
    'cmd': 'commands menu interactive',
    'code': 'interactive console prompt',
    'codeop': 'compile as you type',
    'termios': 'terminal settings keyboard',
    'tty': 'terminal raw keyboard keys',
    'pty': 'pretend a terminal testing',
    'resource': 'limits memory time allowed',
    'fcntl': 'locks files two programs at once',
    'grp': 'groups of users',
    'pwd': 'user accounts home folders',
    'signal': 'stop reload interrupt handling',
    'syslog': 'system log record',
    'errno': 'error numbers files missing refused',
    'faulthandler': 'crash frozen stuck where it died',
    'trace': 'record every line executed',
    'pstats': 'sorting a timing report',
    'bdb': 'stepping through code',
    'tabnanny': 'indentation tabs mistakes',
    'trace': 'record every line executed',
    'py_compile': 'compile ahead of time syntax check',
    'pyclbr': 'what a file defines without running it',
    'compileall': 'compile a whole folder',
    'importlib': 'loading modules dynamically plugins',
    'pkgutil': 'list what is inside a package',
    'runpy': 'run a file as a program',
    'modulefinder': 'what does this program need',
    'zipimport': 'import from a zip',
    'zipapp': 'pack a program into one file',
    'ensurepip': 'install pip itself',
    'venv': 'separate environment for one project',
    'sysconfig': 'where python is installed build flags',
    'site': 'where python looks for modules',
    'shlex': 'split a command line quotes',
    'quopri': 'email text encoding',
    'netrc': 'saved logins passwords for a site',
    'mimetypes': 'file types by extension',
    'plistlib': 'apple property lists mac settings',
    'marshal': 'fast saving python objects',
    'pickletools': 'inspect a saved file safely',
    'webbrowser': 'open a web page in the reader browser',
    'selectors': 'many connections at once',
    'select': 'waiting for several connections',
    'socketserver': 'make a computer into a server',
    'ftplib': 'file transfer ftp',
    'poplib': 'fetch email',
    'imaplib': 'fetch email folders gmail',
    'mailbox': 'read a folder of saved email',
    'wsgiref': 'a small web server',
    'pyexpat': 'xml parser lower level',
}


class ModuleEntry:
    """One row of the index.

    Plain attributes rather than a dataclass: this is read on every
    request, and there is no behaviour here that a dataclass would make
    shorter.
    """

    __slots__ = ('name', 'level', 'group', 'summary', 'example', 'words')

    def __init__(self, name, level, group, summary, example, words):
        self.name = name
        self.level = level
        self.group = group
        self.summary = summary
        self.example = example
        # Pre-split once: the search runs on every keystroke, and splitting
        # 190 strings each time is the sort of thing that makes a search
        # box feel slow on an old machine.
        self.words = words.split() if words else ()

    def as_dict(self, here=None, web=None):
        return {
            'name': self.name,
            'level': self.level,
            'group': self.group,
            'summary': self.summary,
            'words': list(self.words),
            'available': available_here(self.name) if here is None else here,
            'runs_in_web': runs_in_web(self.example) if web is None else web,
        }


LEVELS = (START, EVERYDAY, ADVANCED)
LEVEL_ORDER = {START: 0, EVERYDAY: 1, ADVANCED: 2}
GROUPS = GROUP_ORDER

# Only one name is in the standard-library list but not in
# ``sys.stdlib_module_names``; it is an attribute of a module rather than
# a module in its own right, and the documentation's index lists it.
_DOTTED = frozenset({'os.path'})

# Names deliberately left out: three are demonstration packages that
# print a menu rather than do anything a reader would call, and the rest
# are private implementation details.
_SKIPPED = frozenset({'idlelib', 'turtledemo'})

_by_name = {
    name: ModuleEntry(name, level, group, summary, example, _WORDS.get(name, ''))
    for name, (level, group, summary, example) in ENTRIES.items()
}


@functools.lru_cache(maxsize=None)
def available_here(name):
    """Is this module present in the Python running this app?

    Measured, not declared. ``curses`` is a real module that is not on
    Windows; ``tkinter`` is real and may simply not be installed; a
    package built with ``--without-something`` can be missing a member
    the documentation promises. Asking the interpreter is the only answer
    that is right on the machine in front of the reader.

    Cached, because the answer cannot change while the app is running and
    the index asks about all 190 modules on every search. Caching is safe
    here and only here: a plain availability question about the machine
    the app is already on.
    """
    top = name.split('.')[0]
    if top in _SKIPPED:
        return False
    if top in _DOTTED:
        # os.path always exists if os does.
        top = top.split('.')[0]
    try:
        return importlib.util.find_spec(top) is not None
    except (ImportError, ValueError):
        # A parent package that is not installed, or a name that is not a
        # module at all.
        return False


def runs_in_web(example):
    """Will this example be accepted by the hosted runner?

    The answer decides whether the Run button is offered, so it has to be
    right: a reader who is told to press Run and then refused with a
    message about blocked features has been misled. The blocklist is
    imported from the routes rather than repeated, so a change to the
    runner changes this too.
    """
    from .routes import SANDBOX, check_sandbox

    if not SANDBOX:
        # On the desktop there is no sandbox, so everything can run and
        # this question does not arise.
        return True
    ok, _ = check_sandbox(example)
    return ok


def all_entries(level=None, group=None):
    """Every entry, in the order a reader would look them up.

    Grouped in reading order first, then alphabetical inside each group,
    because that is how somebody scans a reference. When a level or group
    is given the list is alphabetical only - a filtered list is a search
    result, and a search result is read in name order.
    """
    items = list(_by_name.values())
    if level:
        items = [e for e in items if e.level == level]
    if group:
        items = [e for e in items if e.group == group]
        return sorted(items, key=lambda e: e.name)
    if not level:
        return sorted(items, key=lambda e: (GROUPS.index(e.group), e.name))
    return sorted(items, key=lambda e: e.name)


def find(name):
    """One entry by name, or None. The name may be a dotted path."""
    return _by_name.get(name.strip())


def _tokens(text):
    return {t for t in re.split(r'[^a-z0-9]+', text.lower()) if t}


# Words shorter than this carry no signal of their own. "save a file"
# would otherwise match every module whose text contains the letter "a",
# which is most of them - and a search that answers everything answers
# nothing. The words are dropped for matching, not for display.
_MIN_WORD = 3

# Words that are long enough to pass the length test and still mean
# nothing, because almost every description contains them. Without this,
# searching for "the" matched a third of the catalogue. Kept to words
# that really are common in prose; an exhaustive list would start
# dropping words a reader might genuinely mean.
_STOPWORDS = frozenset("""
a an and are as at be been by can could did do does for from had has have
how i if in into is it its may might more most must no not of on one only
or other our should so some such than that the their them then there these
they this those to too up us use used using very was we were what when
where which while who why will with would you your
""".split())


def _substantive(tokens):
    """The words worth matching on.

    Two things are dropped: any word too short to mean much on its own,
    and the function words that appear in nearly every description.

    Note the absence of a fallback. If that is all the query has, there
    is nothing to match on, and the description search returns nothing -
    the name passes above still get their say, so "sys" finds sys.
    """
    return {t for t in tokens if len(t) >= _MIN_WORD and t not in _STOPWORDS}


def search(query, level=None, group=None):
    """Entries matching what the reader typed.

    Ranked so the obvious answer is at the top:

    1. the module name is exactly what was typed;
    2. the module name starts with it;
    3. the module name contains it;
    4. every word of the query is in the description or the everyday
       words - "save a file" finding the module that copies and deletes
       files;
    5. one substantial word of the query is in there.

    There is deliberately no "does any word begin with these letters"
    pass. It was tried and it made the results worse: searching "sort a
    list" offered ``abc`` and ``antigravity`` because both contain the
    letter "a". Returning fewer, better answers is the whole point of a
    reference a reader is expected to trust.
    """
    query = (query or '').strip().lower()
    pool = all_entries(level=level, group=group)
    if not query:
        return pool

    wanted = _tokens(query)
    if not wanted:
        return pool
    needed = _substantive(wanted)
    if not needed:
        # Nothing but short words. Let the name passes above have their
        # say - "sys" should still find sys - but do not search prose.
        needed = None

    exact, prefix, inside, all_of, any_of = [], [], [], [], []
    for entry in pool:
        name = entry.name.lower()
        if name == query:
            exact.append(entry)
            continue
        if name.startswith(query):
            prefix.append(entry)
            continue
        # Word matching, not substring matching. "and" is inside
        # "random" and "so" is inside "json"; offering those for a
        # three-letter query is how a search becomes noise. Splitting on
        # dots is what keeps "path" finding "os.path".
        if query in _tokens(name) or (len(wanted) == 1 and query in name
                                       and len(query) > 3):
            inside.append(entry)
            continue

        haystack = _tokens(entry.summary) | set(entry.words) | _tokens(name)
        if needed is None:
            continue
        hits = needed & haystack
        if not hits:
            continue
        # Count the hits, so the entry that matched most of what was
        # typed comes first. "read a csv" should offer csv before the
        # modules that happen to mention reading.
        row = (-len(hits), entry.name, entry)
        (all_of if needed <= haystack else any_of).append(row)

    for bucket in (all_of, any_of):
        bucket.sort(key=lambda item: (item[0], item[1]))
    for bucket in (exact, prefix, inside):
        bucket.sort(key=lambda e: e.name)
    return (exact + prefix + inside
            + [e for _, _, e in all_of] + [e for _, _, e in any_of])


def counts():
    """How many entries there are per level, for the filter buttons."""
    tally = {START: 0, EVERYDAY: 0, ADVANCED: 0}
    for entry in _by_name.values():
        tally[entry.level] += 1
    return tally
