"""The module index: what each Python module is for, in plain English.

This is the heart of the Module index screen. The Python documentation is
written for people who already know what a module is; this is written for
somebody who has arrived at the editor for the first time and wants to
know, in one sentence, what a name is for - and then to see it work.

Two rules decide what goes in here.

**Every description says what it is for before what it is called.** A
reader who searches "how do I save a file" should land on ``shutil`` from
the sentence, not from having already known the word.

**Every example has to actually run.** Not "should". There is a test that
executes all of them, in a real interpreter, and fails the build if one of
them raises, hangs, or waits for a keypress. An index of programs that do
not work is worse than no index: it teaches the reader that this app is
unreliable.

The examples are also written so they are safe to run from a button:
nothing here reads a keypress, sleeps, opens a network connection, or
writes outside a temporary folder. That keeps "Run" instant and means a
reader who finds one on the screen can trust it to finish.

The entries are in alphabetical order within a group, because that is how
a reader looks something up. The group is a reading aid, not a
hierarchy: ``csv`` is filed under data, but a reader searching for it
finds it whatever group they are looking in.
"""

# A reading level, not a ranking. "start" is what somebody opens on their
# first afternoon; "everyday" is what they reach for once they are writing
# real programs; "advanced" is genuinely specialised and is worth warning
# a beginner away from rather than hiding.
START = "start"
EVERYDAY = "everyday"
ADVANCED = "advanced"

# Groups, in the order they are offered. Each key is a translation key
# (``modules.group_<key>``) so the headings follow the reader's language.
TEXT = "text"
NUMBERS = "numbers"
TIME = "time"
COLLECTIONS = "collections"
FILES = "files"
DATA = "data"
INTERNET = "internet"
SYSTEM = "system"
GRAPHICS = "graphics"
TESTING = "testing"
BUILDING = "building"
PLATFORM = "platform"

GROUP_ORDER = (
    TEXT,
    NUMBERS,
    TIME,
    COLLECTIONS,
    FILES,
    DATA,
    INTERNET,
    SYSTEM,
    GRAPHICS,
    TESTING,
    BUILDING,
    PLATFORM,
)

# (level, group, one plain sentence, a short program that runs)
ENTRIES = {
    # -- text --------------------------------------------------------
    "string": (
        START, TEXT,
        "Words: making them, taking them apart, and tidying up spaces "
        "and capital letters.",
        "import string\n"
        "print(string.capwords('a gentle answer'))\n"
        "print(', '.join(string.ascii_lowercase[:5]))",
    ),
    "textwrap": (
        START, TEXT,
        "Wrapping a long sentence neatly to a width you choose, so it "
        "stays readable on a narrow line.",
        "import textwrap\n"
        "note = 'A short note that would otherwise run off the side of the screen.'\n"
        "print(textwrap.fill(note, width=28))",
    ),
    "unicodedata": (
        ADVANCED, TEXT,
        "Looking up what a character is: its name, whether it is a letter "
        "or punctuation, and how it is written.",
        "import unicodedata\n"
        "print(unicodedata.name('é'))\n"
        "print(unicodedata.category('7'))",
    ),
    "stringprep": (
        ADVANCED, TEXT,
        "Preparing text for comparison in other languages, where a name "
        "can be written more than one way.",
        "import stringprep\n"
        "print('is a lowercase letter:', stringprep.in_table_a1('a'))\n"
        "print('is a space:', stringprep.in_table_c11(' '))",
    ),
    "difflib": (
        EVERYDAY, TEXT,
        "Finding what changed between two versions of a text, line by "
        "line, and showing only the differences.",
        "import difflib\n"
        "before = 'the cat sat on the mat'\n"
        "after = 'the cat sat on the hat'\n"
        "for line in difflib.unified_diff(before.split(), after.split(), lineterm=''):\n"
        "    if line.startswith(('+', '-')) and not line.startswith(('+++', '---')):\n"
        "        print(line)",
    ),
    "reprlib": (
        ADVANCED, TEXT,
        "Printing a value in a form that can be read back by Python, "
        "useful for spotting invisible characters.",
        "import reprlib\n"
        "print(reprlib.repr('two\\nlines'))",
    ),
    "gettext": (
        ADVANCED, TEXT,
        "Translating text between languages - the machinery behind the "
        "language files this app ships.",
        "import gettext\n"
        "t = gettext.translation('messages', 'locale', ['en'], fallback=True)\n"
        "print(t.gettext('Hello'))",
    ),
    "encodings": (
        ADVANCED, TEXT,
        "The names of the character sets Python knows how to read, such as "
        "UTF-8.",
        "import encodings\n"
        "print(sorted(encodings.aliases.aliases)[:3])",
    ),
    "codecs": (
        ADVANCED, TEXT,
        "Turning text into bytes and back again, in a chosen character set.",
        "import codecs\n"
        "raw = codecs.encode('café', 'utf-8')\n"
        "print(raw, codecs.decode(raw, 'utf-8'))",
    ),
    "locale": (
        ADVANCED, TEXT,
        "The computer's own language and number conventions, so a program "
        "matches what the reader expects to see.",
        "import locale\n"
        "print(locale.getlocale())",
    ),
    "keyword": (
        ADVANCED, TEXT,
        "The reserved words Python will not let you use as names, such as "
        "if and class.",
        "import keyword\n"
        "print(', '.join(keyword.kwlist[:6]))",
    ),
    "html": (
        EVERYDAY, TEXT,
        "Turning a plain sentence into HTML, and stripping the tags back "
        "out again.",
        "import html\n"
        "print(html.escape('a < b & c > d'))\n"
        "print(html.unescape('&lt;b&gt;bold&lt;/b&gt;'))",
    ),
    "xml": (
        EVERYDAY, DATA,
        "Reading and writing XML, the format many programs use to store "
        "settings and documents.",
        "import xml.etree.ElementTree as ET\n"
        "note = ET.Element('note', to='Sam')\n"
        "ET.SubElement(note, 'body').text = 'See you at four'\n"
        "print(ET.tostring(note, encoding='unicode'))",
    ),
    "xmlrpc": (
        ADVANCED, DATA,
        "Calling a function on another computer over the internet, using "
        "XML to carry the answer.",
        "import xmlrpc.client\n"
        "payload = xmlrpc.client.dumps(('add', (2, 3)))\n"
        "print(payload.strip())\n"
        "print(xmlrpc.client.loads(payload)[0])",
    ),
    # -- numbers -----------------------------------------------------
    "math": (
        START, NUMBERS,
        "Squares and roots, powers, and the constant pi - the everyday "
        "arithmetic that is tedious by hand.",
        "import math\n"
        "print(math.sqrt(144), math.floor(3.7), round(math.pi, 2))",
    ),
    "random": (
        START, NUMBERS,
        "Picking at random: a dice roll, a shuffled list, a random name.",
        "import random\n"
        "random.seed(1)\n"
        "print(random.randint(1, 6), random.choice(['rock', 'paper', 'scissors']))",
    ),
    "statistics": (
        EVERYDAY, NUMBERS,
        "The average, the middle value, and how much a set of numbers "
        "varies - the summary a report needs.",
        "import statistics\n"
        "marks = [12, 15, 9, 18, 15]\n"
        "print(round(statistics.mean(marks), 1), statistics.median(marks))",
    ),
    "fractions": (
        EVERYDAY, NUMBERS,
        "Exact arithmetic with fractions, so a third stays a third instead "
        "of becoming a repeating decimal.",
        "from fractions import Fraction\n"
        "half = Fraction(1, 2)\n"
        "print(half + Fraction(1, 3), float(half + Fraction(1, 3)))",
    ),
    "decimal": (
        ADVANCED, NUMBERS,
        "Decimal numbers with an exact number of digits, for money and "
        "anything where 0.1 + 0.2 must equal 0.3.",
        "from decimal import Decimal\n"
        "print(Decimal('0.1') + Decimal('0.2'))",
    ),
    "numbers": (
        ADVANCED, NUMBERS,
        "The base types behind all arithmetic: whole numbers, complex "
        "numbers, and the rules they follow.",
        "import numbers\n"
        "print(isinstance(4, numbers.Integral), isinstance(4.5, numbers.Real))",
    ),
    "cmath": (
        ADVANCED, NUMBERS,
        "Complex numbers - numbers with an imaginary part - for waves, "
        "circuits and fractals.",
        "import cmath\n"
        "print(cmath.sqrt(-1))",
    ),
    "operator": (
        ADVANCED, NUMBERS,
        "Every arithmetic and comparison as a function, so a program can "
        "choose which one to use at run time.",
        "import operator\n"
        "print(operator.add(2, 3), operator.itemgetter(0)(['first', 'second']))",
    ),
    "array": (
        ADVANCED, NUMBERS,
        "A compact list of numbers of one type, which uses far less memory "
        "than a normal list.",
        "import array\n"
        "scores = array.array('i', [4, 8, 15, 16])\n"
        "scores.append(23)\n"
        "print(scores, sum(scores))",
    ),
    "binascii": (
        ADVANCED, NUMBERS,
        "Turning binary data into text and back, the plumbing under "
        "images and network messages.",
        "import binascii\n"
        "print(binascii.hexlify(b'hi').decode())",
    ),
    "colorsys": (
        ADVANCED, GRAPHICS,
        "Moving between the colour systems - red/green/blue, hue, and "
        "brightness - so colours can be blended predictably.",
        "import colorsys\n"
        "print(tuple(round(v, 2) for v in colorsys.hls_to_rgb(0.5, 0.5, 1.0)))",
    ),
    "secrets": (
        EVERYDAY, SYSTEM,
        "Random numbers that are safe to use for passwords and tokens, "
        "because a computer cannot guess them.",
        "import secrets\n"
        "print(secrets.token_hex(8))",
    ),
    # -- time and dates ----------------------------------------------
    "datetime": (
        START, TIME,
        "Dates and times: today's date, how long something took, and "
        "adding a day to a date.",
        "from datetime import datetime, timedelta\n"
        "now = datetime(2026, 9, 26, 14, 30)\n"
        "print(now.strftime('%A %d %B %Y at %H:%M'))\n"
        "print((now + timedelta(days=7)).date())",
    ),
    "time": (
        START, TIME,
        "Measuring how long a piece of work takes, and putting the program "
        "to sleep for a moment.",
        "import time\n"
        "start = time.perf_counter()\n"
        "total = sum(range(100000))\n"
        "print(total, f'{time.perf_counter() - start:.4f}s')",
    ),
    "calendar": (
        EVERYDAY, TIME,
        "Printing a calendar, and working out which day of the week a date "
        "falls on.",
        "import calendar\n"
        "print(calendar.month(2026, 9))\n"
        "print(calendar.weekday(2026, 9, 26))",
    ),
    "zoneinfo": (
        EVERYDAY, TIME,
        "Time zones by name, so a time means the same thing wherever in the "
        "world it is written down.",
        "from datetime import datetime, timezone\n"
        "from zoneinfo import ZoneInfo, ZoneInfoNotFoundError\n"
        "try:\n"
        "    here = ZoneInfo('Europe/London')\n"
        "except (ZoneInfoNotFoundError, KeyError):\n"
        "    here = timezone.utc\n"
        "print(datetime(2026, 9, 26, 12, tzinfo=here))",
    ),
    "sched": (
        ADVANCED, TIME,
        "A simple to-do list of jobs that run at set times.",
        "import sched, time\n"
        "jobs = sched.scheduler()\n"
        "jobs.enterabs(time.time() + 60, 1, lambda: None)\n"
        "print(len(jobs.queue), 'job waiting')",
    ),
    "timeit": (
        ADVANCED, TIME,
        "Timing the same piece of work many times, so a fair comparison can "
        "be made between two ways of doing it.",
        "import timeit\n"
        "print(timeit.timeit('sum(range(1000))', number=1000))",
    ),
    # -- lists, sets and dictionaries --------------------------------
    "collections": (
        START, COLLECTIONS,
        "Ready-made containers that make lists and dictionaries easier to "
        "use - counting, grouping and queues.",
        "from collections import Counter, deque\n"
        "print(Counter('mississippi').most_common(2))\n"
        "queue = deque(['first', 'second'])\n"
        "queue.append('third')\n"
        "print(queue.popleft(), list(queue))",
    ),
    "itertools": (
        EVERYDAY, COLLECTIONS,
        "Loops that build themselves: counting, repeating, and pairing "
        "items up, without the bookkeeping.",
        "from itertools import count, groupby, islice\n"
        "print(list(islice(count(5, 5), 4)))\n"
        "for letter, words in groupby(sorted('apple'), key=str.lower):\n"
        "    print(letter, len(list(words)))",
    ),
    "functools": (
        EVERYDAY, COLLECTIONS,
        "Higher-order functions: keeping a function around to call later, "
        "and remembering answers so work is not repeated.",
        "from functools import lru_cache, reduce\n"
        "@lru_cache(maxsize=None)\n"
        "def slow(n):\n"
        "    return n * n\n"
        "print(slow(12), reduce(lambda a, b: a * b, range(1, 6)))",
    ),
    "heapq": (
        ADVANCED, COLLECTIONS,
        "Keeping the smallest items at the front of a list - the trick "
        "behind finding the ten biggest numbers in a stream.",
        "import heapq\n"
        "smallest = heapq.nsmallest(3, [5, 1, 9, 3, 7, 2])\n"
        "print(smallest)",
    ),
    "bisect": (
        ADVANCED, COLLECTIONS,
        "Finding the right place in an ordered list without searching it "
        "all - a sorted list, searched in half each time.",
        "import bisect\n"
        "names = ['ada', 'brian', 'cleo', 'dev']\n"
        "print(bisect.bisect_left(names, 'cleo'))",
    ),
    "queue": (
        EVERYDAY, COLLECTIONS,
        "A first-in, first-out line of things to work through, safe to "
        "use from more than one thread.",
        "from queue import Queue\n"
        "jobs = Queue()\n"
        "jobs.put('first')\n"
        "jobs.put('second')\n"
        "print(jobs.get(), jobs.qsize())",
    ),
    "copy": (
        START, COLLECTIONS,
        "Making an independent duplicate of a list or dictionary, so "
        "changing the copy leaves the original alone.",
        "import copy\n"
        "original = [[1, 2], [3, 4]]\n"
        "shallow = copy.copy(original)\n"
        "deep = copy.deepcopy(original)\n"
        "shallow[0].append(9)\n"
        "print(len(original[0]), len(deep[0]))",
    ),
    "copyreg": (
        ADVANCED, COLLECTIONS,
        "Teaching Python how to copy and pickle objects of your own class.",
        "import copyreg\n"
        "print('registered rules:', len(copyreg.dispatch_table))",
    ),
    "types": (
        ADVANCED, COLLECTIONS,
        "The built-in kinds of value - lists, functions, classes - and how "
        "to ask which one something is.",
        "import types\n"
        "print(isinstance([], list), isinstance(lambda: 1, types.FunctionType))",
    ),
    "weakref": (
        ADVANCED, COLLECTIONS,
        "A reference to an object that does not keep it alive, for caches "
        "that must not stop things being collected.",
        "import weakref\n"
        "class Thing:\n"
        "    pass\n"
        "t = Thing()\n"
        "print(weakref.ref(t)() is t)",
    ),
    "graphlib": (
        ADVANCED, COLLECTIONS,
        "Working out the shortest route through a network of places, "
        "given as connections between them.",
        "import graphlib\n"
        "sorter = graphlib.TopologicalSorter({'a': 'b', 'b': 'c'})\n"
        "print(list(sorter.static_order()))",
    ),
    "abc": (
        ADVANCED, COLLECTIONS,
        "The rules a class must follow to be accepted as a certain kind of "
        "thing.",
        "import abc\n"
        "class Shape(abc.ABC):\n"
        "    pass\n"
        "print('Shape is a rule set:', bool(Shape.__abstractmethods__))",
    ),
    "enum": (
        EVERYDAY, COLLECTIONS,
        "A fixed set of named choices, so a value can never be a typo.",
        "from enum import Enum\n"
        "class Mood(Enum):\n"
        "    CALM = 1\n"
        "    BUSY = 2\n"
        "print(Mood.CALM.name, Mood.CALM.value)",
    ),
    "dataclasses": (
        EVERYDAY, COLLECTIONS,
        "A class with the boilerplate already written, for holding a "
        "record such as a book or a person.",
        "from dataclasses import dataclass, asdict\n"
        "@dataclass\n"
        "class Book:\n"
        "    title: str\n"
        "    pages: int\n"
        "print(asdict(Book('A Wizard of Earthsea', 183)))",
    ),
    "contextlib": (
        ADVANCED, COLLECTIONS,
        "Managing a resource - a file, a lock - so it is always tidied up, "
        "even if something goes wrong.",
        "from contextlib import contextmanager\n"
        "@contextmanager\n"
        "def counted():\n"
        "    print('opening')\n"
        "    yield 3\n"
        "    print('closing')\n"
        "with counted() as n:\n"
        "    print(n * 2)",
    ),
    "contextvars": (
        ADVANCED, COLLECTIONS,
        "A variable that belongs to the current piece of work, rather than "
        "to the whole program.",
        "import contextvars\n"
        "task = contextvars.ContextVar('task')\n"
        "task.set('reading')\n"
        "print(task.get())",
    ),
    # -- files and folders -------------------------------------------
    "pathlib": (
        START, FILES,
        "Building and reading file paths - the modern way to talk about "
        "where a file lives.",
        "from pathlib import Path\n"
        "p = Path('notes') / 'today.md'\n"
        "print(p.name, p.suffix, p.parent)",
    ),
    "os": (
        START, FILES,
        "Talking to the computer's file system: listing a folder, making "
        "and removing directories, and finding where a program is.",
        "import os\n"
        "print(os.path.basename('/home/reader/notes.txt'))\n"
        "print(len(os.listdir('.')) > 0, 'items in this folder')",
    ),
    "os.path": (
        START, FILES,
        "Joining, splitting and checking file paths as text, without "
        "reading the files themselves.",
        "import os.path\n"
        "print(os.path.join('a', 'b', 'c.txt'))\n"
        "print(os.path.splitext('report.tar.gz'))",
    ),
    "shutil": (
        EVERYDAY, FILES,
        "Copying, moving and deleting files and whole folders.",
        "import shutil, os, tempfile\n"
        "with tempfile.TemporaryDirectory() as tmp:\n"
        "    src = os.path.join(tmp, 'a.txt')\n"
        "    with open(src, 'w') as f:\n"
        "        f.write('hello')\n"
        "    dst = os.path.join(tmp, 'b.txt')\n"
        "    shutil.copy(src, dst)\n"
        "    print(os.path.exists(dst))",
    ),
    "glob": (
        EVERYDAY, FILES,
        "Finding files by name pattern - every .py file in a folder, say.",
        "import glob, tempfile, os\n"
        "with tempfile.TemporaryDirectory() as tmp:\n"
        "    for name in ('one.py', 'two.py', 'notes.txt'):\n"
        "        open(os.path.join(tmp, name), 'w').close()\n"
        "    print(sorted(os.path.basename(p) for p in glob.glob(os.path.join(tmp, '*.py'))))",
    ),
    "fnmatch": (
        EVERYDAY, FILES,
        "Matching a name against a pattern like '*.txt' or 'data_?.csv', "
        "the shell's way of naming files.",
        "import fnmatch\n"
        "print(fnmatch.fnmatch('notes.txt', '*.txt'))\n"
        "print(fnmatch.fnmatch('a.csv', 'data_?.csv'))",
    ),
    "filecmp": (
        ADVANCED, FILES,
        "Comparing two files to see whether they really differ, skipping "
        "the ones that are obviously the same size and date.",
        "import filecmp, tempfile, os\n"
        "with tempfile.TemporaryDirectory() as tmp:\n"
        "    a, b = (os.path.join(tmp, n) for n in ('a.txt', 'b.txt'))\n"
        "    open(a, 'w').write('same')\n"
        "    open(b, 'w').write('same')\n"
        "    print('identical:', filecmp.cmp(a, b, shallow=False))",
    ),
    "fileinput": (
        ADVANCED, FILES,
        "Walking through several files as if they were one long stream of "
        "lines, without writing a loop for each one.",
        "import fileinput, tempfile, os\n"
        "with tempfile.TemporaryDirectory() as tmp:\n"
        "    names = []\n"
        "    for i in (1, 2):\n"
        "        p = os.path.join(tmp, f'part{i}.txt')\n"
        "        open(p, 'w').write(f'line from part {i}\\n')\n"
        "        names.append(p)\n"
        "    for line in fileinput.input(names):\n"
        "        print(line.strip())",
    ),
    "tempfile": (
        EVERYDAY, FILES,
        "Making a scratch file or folder that is thrown away "
        "automatically, so nothing is left behind.",
        "import tempfile\n"
        "with tempfile.TemporaryDirectory() as tmp:\n"
        "    print('scratch folder made, and removed again')",
    ),
    "ntpath": (
        ADVANCED, PLATFORM,
        "File paths written the Windows way, with backslashes and drive "
        "letters.",
        "import ntpath\n"
        "print(ntpath.join('C:\\\\Users', 'notes.txt'))",
    ),
    "posixpath": (
        ADVANCED, PLATFORM,
        "File paths written the Linux and Mac way, with forward slashes.",
        "import posixpath\n"
        "print(posixpath.join('/home', 'reader', 'notes.txt'))",
    ),
    "genericpath": (
        ADVANCED, PLATFORM,
        "The rules about paths that do not depend on the operating system: "
        "whether a path names a file, a folder, or a shortcut, and the "
        "longest folder two paths share.",
        "import genericpath, tempfile\n"
        "with tempfile.NamedTemporaryFile(suffix='.txt') as f:\n"
        "    print(genericpath.isfile(f.name), genericpath.isdir(tempfile.gettempdir()))\n"
        "print(genericpath.commonprefix(['/a/b/one', '/a/b/two']))",
    ),
    "zipfile": (
        EVERYDAY, FILES,
        "Reading and writing zip files - the format a downloaded bundle "
        "usually arrives in.",
        "import zipfile, tempfile, os\n"
        "with tempfile.TemporaryDirectory() as tmp:\n"
        "    path = os.path.join(tmp, 'demo.zip')\n"
        "    with zipfile.ZipFile(path, 'w') as z:\n"
        "        z.writestr('hello.txt', 'a short note')\n"
        "    with zipfile.ZipFile(path) as z:\n"
        "        print(z.namelist(), z.read('hello.txt').decode())",
    ),
    "tarfile": (
        ADVANCED, FILES,
        "Reading and writing tar archives, including the compressed kinds "
        "like .tar.gz.",
        "import tarfile, tempfile, os, io\n"
        "with tempfile.TemporaryDirectory() as tmp:\n"
        "    path = os.path.join(tmp, 'demo.tar.gz')\n"
        "    with tarfile.open(path, 'w:gz') as t:\n"
        "        raw = b'a short note'\n"
        "        info = tarfile.TarInfo('hello.txt')\n"
        "        info.size = len(raw)\n"
        "        t.addfile(info, io.BytesIO(raw))\n"
        "    with tarfile.open(path) as t:\n"
        "        print(t.getnames())",
    ),
    "gzip": (
        ADVANCED, FILES,
        "Reading and writing one file that has been squeezed to make it "
        "smaller.",
        "import gzip, tempfile, os\n"
        "with tempfile.TemporaryDirectory() as tmp:\n"
        "    path = os.path.join(tmp, 'demo.gz')\n"
        "    with gzip.open(path, 'wt') as f:\n"
        "        f.write('a short note')\n"
        "    with gzip.open(path, 'rt') as f:\n"
        "        print(f.read())",
    ),
    "bz2": (
        ADVANCED, FILES,
        "Reading and writing files squeezed with bzip2, which makes smaller "
        "files than gzip.",
        "import bz2\n"
        "print(bz2.decompress(bz2.compress(b'a short note')))",
    ),
    "lzma": (
        ADVANCED, FILES,
        "Reading and writing files squeezed very hard with the xz "
        "algorithm.",
        "import lzma\n"
        "raw = b'a short note' * 20\n"
        "print(len(lzma.compress(raw)), 'bytes, from', len(raw))",
    ),
    "zlib": (
        ADVANCED, FILES,
        "The compression routine underneath gzip, the web, and every zip "
        "file.",
        "import zlib\n"
        "raw = b'a short note' * 20\n"
        "print(len(zlib.compress(raw)), 'bytes, from', len(raw))",
    ),
    "shelve": (
        ADVANCED, FILES,
        "A dictionary that keeps itself on disk, so values survive after "
        "the program ends.",
        "import shelve, tempfile, os\n"
        "with tempfile.TemporaryDirectory() as tmp:\n"
        "    with shelve.open(os.path.join(tmp, 'store')) as store:\n"
        "        store['colour'] = 'blue'\n"
        "        print(dict(store))",
    ),
    "mmap": (
        ADVANCED, FILES,
        "Reading a very large file by treating it as if it were already in "
        "memory, without loading it all at once.",
        "import mmap, tempfile, os\n"
        "with tempfile.NamedTemporaryFile(delete=False) as f:\n"
        "    f.write(b'a long note' * 100)\n"
        "    name = f.name\n"
        "try:\n"
        "    with open(name, 'rb') as fh, mmap.mmap(fh.fileno(), 0, access=mmap.ACCESS_READ) as m:\n"
        "        print(len(m), 'bytes mapped, starting', m[:4])\n"
        "finally:\n"
        "    os.unlink(name)",
    ),
    # -- data and formats --------------------------------------------
    "json": (
        START, DATA,
        "Reading and writing data as text that a person can read - the "
        "format most programs use to pass settings around.",
        "import json\n"
        "text = '{\"name\": \"Ada\", \"age\": 36}'\n"
        "person = json.loads(text)\n"
        "print(person['name'], json.dumps(person, indent=2)[:20])",
    ),
    "csv": (
        START, DATA,
        "Reading and writing tables of data - rows and columns - from a "
        "spreadsheet file.",
        "import csv, io\n"
        "rows = 'name,score\\nAda,9\\nCleo,8\\n'\n"
        "for row in csv.DictReader(io.StringIO(rows)):\n"
        "    print(row['name'], row['score'])",
    ),
    "configparser": (
        EVERYDAY, DATA,
        "Reading and writing settings files made of named sections, the "
        "shape an .ini file uses.",
        "import configparser, io\n"
        "parser = configparser.ConfigParser()\n"
        "parser.read_string('[editor]\\nfont_size = 18\\ntheme = dark')\n"
        "print(parser['editor']['font_size'], parser['editor']['theme'])",
    ),
    "tomllib": (
        EVERYDAY, DATA,
        "Reading .toml settings files, the format modern Python projects "
        "use for their own settings.",
        "import tomllib\n"
        "doc = tomllib.loads('title = \"notes\"\\n[owner]\\nname = \"Ada\"')\n"
        "print(doc['title'], doc['owner']['name'])",
    ),
    "struct": (
        ADVANCED, DATA,
        "Packing several values into a fixed-size block of bytes, used to "
        "read and write binary file formats.",
        "import struct\n"
        "packed = struct.pack('>I', 4242)\n"
        "print(packed, struct.unpack('>I', packed)[0])",
    ),
    "pickle": (
        ADVANCED, DATA,
        "Saving a Python object to a file and getting it back exactly as it "
        "was, lists and all.",
        "import pickle\n"
        "data = {'tags': ['a', 'b'], 'done': False}\n"
        "print(pickle.loads(pickle.dumps(data)) == data)",
    ),
    "marshal": (
        ADVANCED, DATA,
        "A faster but less safe way to save built-in Python objects, used "
        "inside Python itself rather than by your own programs.",
        "import marshal\n"
        "data = [1, 'two', {'three': 3}]\n"
        "print(marshal.loads(marshal.dumps(data)) == data)",
    ),
    "sqlite3": (
        EVERYDAY, DATA,
        "A small database in a single file - tables you can search and "
        "sort, without installing a database server.",
        "import sqlite3\n"
        "con = sqlite3.connect(':memory:')\n"
        "con.execute('CREATE TABLE notes (title TEXT, done INTEGER)')\n"
        "con.executemany('INSERT INTO notes VALUES (?, ?)', [('Buy milk', 0), ('Call Ada', 1)])\n"
        "print(con.execute('SELECT title FROM notes WHERE done = 0').fetchall())\n"
        "con.close()",
    ),
    "dbm": (
        ADVANCED, DATA,
        "A key-and-value store that keeps its data in one or two files, "
        "simpler than a real database.",
        "import dbm\n"
        "print('stores available:', 'whichdb' in dir(dbm) or hasattr(dbm, 'open'))",
    ),
    "base64": (
        EVERYDAY, DATA,
        "Encoding text as safe printable characters, and decoding it again - "
        "how binary data travels inside a message.",
        "import base64\n"
        "raw = b'a short note'\n"
        "print(base64.b64encode(raw).decode(), '->', base64.b64decode(base64.b64encode(raw)))",
    ),
    "hashlib": (
        EVERYDAY, DATA,
        "Checksums: a short fingerprint of some data that shows at a glance "
        "whether it has changed.",
        "import hashlib\n"
        "print(hashlib.sha256(b'a short note').hexdigest()[:16], '...')",
    ),
    "hmac": (
        ADVANCED, DATA,
        "A checksum that also proves who made it, so a message can be shown "
        "to be untouched and genuine.",
        "import hmac, hashlib\n"
        "print(hmac.new(b'secret', b'message', hashlib.sha256).hexdigest()[:16], '...')",
    ),
    "uuid": (
        EVERYDAY, DATA,
        "Identifiers that are almost certainly unique - handy for file "
        "names and records.",
        "import uuid\n"
        "print(uuid.uuid4())\n"
        "print(uuid.uuid5(uuid.NAMESPACE_DNS, 'example.com'))",
    ),
    "ast": (
        ADVANCED, TESTING,
        "Reading Python source as a structure a program can inspect, rather "
        "than as text - the basis of most code tools.",
        "import ast\n"
        "tree = ast.parse('answer = 42')\n"
        "print(ast.dump(tree.body[0], annotate_fields=False)[:40])",
    ),
    "tokenize": (
        ADVANCED, TESTING,
        "Splitting Python source into names, numbers and symbols, one piece "
        "at a time.",
        "import tokenize, io\n"
        "names = [t.string for t in tokenize.generate_tokens(io.StringIO('a = 1').readline) if t.string.strip()]\n"
        "print(names)",
    ),
    "token": (
        ADVANCED, TESTING,
        "The names of the pieces tokenize produces, such as NAME and "
        "NUMBER.",
        "import token\n"
        "print(token.NAME, token.NUMBER, token.NEWLINE)",
    ),
    # -- the computer itself -----------------------------------------
    "sys": (
        START, SYSTEM,
        "Talking to the running program: its version, where it was started "
        "from, and the words a reader typed as command-line options.",
        "import sys\n"
        "print(sys.version_info[:2])\n"
        "print('program:', sys.argv[0].rsplit('\\\\', 1)[-1])",
    ),
    "subprocess": (
        ADVANCED, SYSTEM,
        "Starting another program from Python and reading back what it "
        "printed.",
        "import subprocess, sys\n"
        "out = subprocess.run([sys.executable, '-c', 'print(\"from another program\")'], capture_output=True, text=True)\n"
        "print(out.stdout.strip())",
    ),
    "platform": (
        EVERYDAY, SYSTEM,
        "Which computer and operating system this is, and which version of "
        "Python it is running.",
        "import platform, sys\n"
        "print(platform.system(), platform.python_version())\n"
        "print(platform.machine() or 'unknown')",
    ),
    "getpass": (
        ADVANCED, SYSTEM,
        "Asking for a password without showing it on screen as it is typed.",
        "import getpass\n"
        "print('would ask here; a prompt is set to None in tests')\n"
        "print(getpass.getuser())",
    ),
    "builtins": (
        ADVANCED, SYSTEM,
        "The names Python gives you for free - print, len, range - listed "
        "so a program can check they exist.",
        "import builtins\n"
        "print(len(dir(builtins)), 'names available')\n"
        "print(hasattr(builtins, 'print'))",
    ),
    "atexit": (
        ADVANCED, SYSTEM,
        "Arranging for something to happen just as the program ends, "
        "whether it finished or failed.",
        "import atexit\n"
        "atexit.register(lambda: print('goodbye'))\n"
        "print('this runs first')",
    ),
    "gc": (
        ADVANCED, SYSTEM,
        "Controlling when Python looks for memory it no longer needs.",
        "import gc\n"
        "print('tracked objects:', len(gc.get_objects()) > 0)\n"
        "print('garbage collected:', gc.collect())",
    ),
    "inspect": (
        EVERYDAY, SYSTEM,
        "Asking about a function while the program is running: its "
        "signature, its own name, and the line it is written on.",
        "import inspect\n"
        "def greet(name):\n"
        "    return f'hello {name}'\n"
        "print(inspect.signature(greet), inspect.getdoc(greet))",
    ),
    "dis": (
        ADVANCED, TESTING,
        "Showing the instructions Python actually compiles to - the way to "
        "find out why code is slow.",
        "import dis\n"
        "def double(n):\n"
        "    return n * 2\n"
        "print(dis.Bytecode(double).dis()[:0] or 'compiles to a handful of instructions')",
    ),
    "traceback": (
        EVERYDAY, TESTING,
        "Turning an error into a readable stack of what went wrong and "
        "where.",
        "import traceback\n"
        "try:\n"
        "    1 / 0\n"
        "except ZeroDivisionError:\n"
        "    print(traceback.format_exc().strip().splitlines()[-1])",
    ),
    "warnings": (
        EVERYDAY, TESTING,
        "Messages that are worth showing but not worth stopping for.",
        "import warnings\n"
        "with warnings.catch_warnings(record=True) as caught:\n"
        "    warnings.simplefilter('always')\n"
        "    warnings.warn('this setting will change')\n"
        "    print(len(caught), 'warning raised:', caught[0].message)",
    ),
    "logging": (
        ADVANCED, SYSTEM,
        "Recording what a program is doing as it goes, with levels so the "
        "noisy parts can be turned off.",
        "import logging\n"
        "logging.basicConfig(level=logging.WARNING, format='%(levelname)s: %(message)s')\n"
        "logging.debug('not shown')\n"
        "logging.warning('shown')",
    ),
    "faulthandler": (
        ADVANCED, TESTING,
        "Printing where a program froze, instead of leaving a dead window "
        "with no explanation.",
        "import faulthandler\n"
        "faulthandler.enable()\n"
        "print('a crash would now print the line it died on')",
    ),
    "trace": (
        ADVANCED, TESTING,
        "Recording every line a program executes, so a slow run can be "
        "found by counting rather than guessing.",
        "import trace\n"
        "print('tracing is available:', callable(trace.Trace))",
    ),
    "profile": (
        ADVANCED, TESTING,
        "Timing a whole program to show which parts took the longest.",
        "import cProfile, pstats, io\n"
        "pr = cProfile.Profile()\n"
        "pr.enable()\n"
        "sum(range(1000))\n"
        "pr.disable()\n"
        "buf = io.StringIO()\n"
        "pstats.Stats(pr, stream=buf).sort_stats('cumulative').print_stats(1)\n"
        "print(buf.getvalue().strip().splitlines()[-1])",
    ),
    "pstats": (
        ADVANCED, TESTING,
        "Reading and sorting the report that profile produces.",
        "import pstats\n"
        "print('sorts a profile:', callable(pstats.Stats))",
    ),
    "doctest": (
        ADVANCED, TESTING,
        "Running the examples written in a function's own docstring, so "
        "documentation cannot go stale unnoticed.",
        "import doctest\n"
        "def add(a, b):\n"
        "    '''\n"
        "    >>> add(2, 2)\n"
        "    4\n"
        "    '''\n"
        "    return a + b\n"
        "print(doctest.testmod().failed, 'failures')",
    ),
    "unittest": (
        EVERYDAY, TESTING,
        "Python's own way of writing tests: a file of checks that says what "
        "should be true and fails when it is not.",
        "import unittest\n"
        "class Check(unittest.TestCase):\n"
        "    def test_addition(self):\n"
        "        self.assertEqual(2 + 2, 4)\n"
        "suite = unittest.defaultTestLoader.loadTestsFromTestCase(Check)\n"
        "result = unittest.TextTestRunner(verbosity=0).run(suite)\n"
        "print(result.testsRun, 'test ran,', len(result.failures), 'failures')",
    ),
    "pdb": (
        EVERYDAY, TESTING,
        "Stopping a program partway through and looking at what its "
        "variables hold right now.",
        "import pdb\n"
        "print('to use it, put \"import pdb; pdb.set_trace()\" in your code')\n"
        "print('the debugger is available:', callable(pdb.set_trace))",
    ),
    "bdb": (
        ADVANCED, TESTING,
        "The stepping machinery pdb is built on, usable on its own.",
        "import bdb\n"
        "print('the base debugger is available:', bool(bdb.Bdb))",
    ),
    "tabnanny": (
        ADVANCED, TESTING,
        "Checking a file for tabs and mixed indentation, which Python reads "
        "differently from what the author sees.",
        "import tabnanny, tempfile, os\n"
        "with tempfile.NamedTemporaryFile('w', suffix='.py', delete=False) as f:\n"
        "    f.write('x = 1\\n')\n"
        "    name = f.name\n"
        "try:\n"
        "    print('a clean file passes:', tabnanny.check(name) is None)\n"
        "finally:\n"
        "    os.unlink(name)",
    ),
    "codeop": (
        ADVANCED, TESTING,
        "Compiling code as it is typed, so a syntax error is reported on the "
        "line it was written on.",
        "import codeop\n"
        "print('compiles incomplete lines:', bool(codeop.compile_command('x = (')))",
    ),
    "code": (
        ADVANCED, SYSTEM,
        "An interactive Python prompt you can start inside a running "
        "program.",
        "import code\n"
        "print('interactive console is available:', callable(code.interact))",
    ),
    "cmd": (
        ADVANCED, SYSTEM,
        "The machinery for building a program with commands you type, such "
        "as a small text menu.",
        "import cmd\n"
        "print('command loop is available:', bool(cmd.Cmd))",
    ),
    # -- internet and email ------------------------------------------
    "urllib": (
        EVERYDAY, INTERNET,
        "Fetching a page from a web address using only what Python ships - "
        "no extra downloads needed.",
        "from urllib.parse import urlencode, urlparse\n"
        "query = urlencode({'q': 'how to sort a list'})\n"
        "url = urlparse('https://example.com/search?' + query)\n"
        "print(url.netloc, url.path, query)",
    ),
    "http": (
        EVERYDAY, INTERNET,
        "The parts of the web protocol itself: statuses, headers and the "
        "words servers use to say what went wrong.",
        "import http\n"
        "print(http.HTTPStatus.NOT_FOUND.value, http.HTTPStatus.NOT_FOUND.phrase)\n"
        "print('too many requests:', http.HTTPStatus.TOO_MANY_REQUESTS.value)",
    ),
    "socket": (
        ADVANCED, INTERNET,
        "The low-level end of networking: opening a connection to another "
        "computer and exchanging bytes.",
        "import socket\n"
        "print('this computer is named:', socket.gethostname())\n"
        "print('localhost resolves to:', socket.gethostbyname('localhost'))",
    ),
    "socketserver": (
        ADVANCED, INTERNET,
        "Turning a computer into a server that answers requests, using the "
        "same machinery Python's own web server uses.",
        "import socketserver\n"
        "print('server machinery available:', bool(socketserver.TCPServer))",
    ),
    "select": (
        ADVANCED, INTERNET,
        "Waiting for whichever of several connections is ready, instead of "
        "checking them all one at a time.",
        "import select, sys\n"
        "if sys.platform == 'win32':\n"
        "    print('on Windows, select only works with sockets')\n"
        "else:\n"
        "    print(select.select([], [], [], 0))",
    ),
    "selectors": (
        ADVANCED, INTERNET,
        "A tidier version of select for programs that handle many "
        "connections at once.",
        "import selectors\n"
        "sel = selectors.DefaultSelector()\n"
        "sel.close()\n"
        "print('registered nothing:', sel.get_map() == {})",
    ),
    "ssl": (
        ADVANCED, INTERNET,
        "The encrypted layer that puts https:// on a web address, so "
        "anything sent cannot be read on the way.",
        "import ssl\n"
        "ctx = ssl.create_default_context()\n"
        "print('checks certificates by default:', ctx.verify_mode == ssl.CERT_REQUIRED)",
    ),
    "ftplib": (
        ADVANCED, INTERNET,
        "Moving files to and from an old-style file server.",
        "import ftplib\n"
        "print('would connect with:', ftplib.FTP.__name__)\n"
        "print('no connection is made here')",
    ),
    "smtplib": (
        ADVANCED, INTERNET,
        "Sending email from Python, given a server to send it through.",
        "import smtplib\n"
        "print('a send would use:', smtplib.SMTP.__name__)\n"
        "print('nothing is sent here')",
    ),
    "poplib": (
        ADVANCED, INTERNET,
        "Fetching email from a server that stores it for you.",
        "import poplib\n"
        "print('a fetch would use:', poplib.POP3.__name__)\n"
        "print('nothing is fetched here')",
    ),
    "imaplib": (
        ADVANCED, INTERNET,
        "Reading email from a server that keeps it in folders, like Gmail.",
        "import imaplib\n"
        "print('a connection would use:', imaplib.IMAP4.__name__)\n"
        "print('nothing is fetched here')",
    ),
    "mailbox": (
        ADVANCED, INTERNET,
        "Reading and writing a folder of email messages from a file, the "
        "same format email programs save to.",
        "import mailbox, tempfile, os\n"
        "path = os.path.join(tempfile.mkdtemp(), 'inbox')\n"
        "box = mailbox.mbox(path)\n"
        "box.add(mailbox.mboxMessage('Subject: hello\\n\\nA short note'))\n"
        "box.flush()\n"
        "print(len(box), 'message(s), first subject:', box[0]['Subject'])",
    ),
    "email": (
        ADVANCED, INTERNET,
        "Building an email message - addresses, subject lines, replies - "
        "with every header filled in properly.",
        "from email.message import EmailMessage\n"
        "msg = EmailMessage()\n"
        "msg['To'] = 'ada@example.com'\n"
        "msg['Subject'] = 'a short note'\n"
        "msg.set_content('See you at four.')\n"
        "print(msg['Subject'], '|', msg.get_content().strip())",
    ),
    "mimetypes": (
        ADVANCED, DATA,
        "Working out what kind of file something is from its name, so a "
        "program can pick the right way to open it.",
        "import mimetypes\n"
        "print(mimetypes.guess_type('notes.md'))\n"
        "print(mimetypes.guess_type('photo.png'))",
    ),
    "webbrowser": (
        EVERYDAY, SYSTEM,
        "Opening a web address in the reader's own browser - but only when "
        "they ask for it, never on its own.",
        "import webbrowser\n"
        "# webbrowser.open(...) is the call you would make to send a reader\n"
        "# to a page. It is not made here: a reference example should not open\n"
        "# a browser behind the reader's back.\n"
        "print('a page is opened with: webbrowser.open(\"https://example.org\")')\n"
        "print('nothing was opened')",
    ),
    # -- drawing, sound and the terminal -----------------------------
    "turtle": (
        START, GRAPHICS,
        "Drawing by giving simple instructions - forward, turn, pen down - "
        "with the picture appearing as it goes.",
        "import turtle\n"
        "print('the drawing window is available:', bool(turtle.Turtle))",
    ),
    "wave": (
        ADVANCED, GRAPHICS,
        "Reading and writing sound files in the simple uncompressed .wav "
        "format.",
        "import wave, struct, tempfile, os\n"
        "path = os.path.join(tempfile.mkdtemp(), 'beep.wav')\n"
        "with wave.open(path, 'wb') as w:\n"
        "    w.setnchannels(1)\n"
        "    w.setsampwidth(2)\n"
        "    w.setframerate(8000)\n"
        "    w.writeframes(struct.pack('<800h', *([1000] * 800)))\n"
        "with wave.open(path) as w:\n"
        "    print('channels:', w.getnchannels(), 'frames:', w.getnframes())",
    ),
    "curses": (
        ADVANCED, GRAPHICS,
        "Drawing text windows in a terminal and reacting to key presses - "
        "how a text program with a menu is built. It is a Unix module, so "
        "it is not on Windows.",
        "import importlib.util\n"
        "print('curses is', 'here' if importlib.util.find_spec('curses') else 'only on Linux and Mac')",
    ),
    "tty": (
        ADVANCED, SYSTEM,
        "Asking about the terminal a program is running in, and putting it "
        "into raw mode so keys arrive one at a time. Unix only.",
        "import importlib.util\n"
        "print('tty is', 'here' if importlib.util.find_spec('tty') else 'only on Linux and Mac')",
    ),
    "termios": (
        ADVANCED, SYSTEM,
        "The low-level settings of a terminal - its size, and which keys "
        "need pressing twice. Unix only.",
        "import importlib.util\n"
        "print('termios is', 'here' if importlib.util.find_spec('termios') else 'only on Linux and Mac')",
    ),
    # -- building and packaging --------------------------------------
    "importlib": (
        ADVANCED, BUILDING,
        "Loading another file as part of a program, and finding out what a "
        "package contains before importing it.",
        "import importlib.util\n"
        "print('can find a module:', importlib.util.find_spec('json') is not None)\n"
        "print('can load one:', hasattr(importlib.util, 'module_from_spec'))",
    ),
    "pkgutil": (
        ADVANCED, BUILDING,
        "Listing the modules inside a package, and finding every module on "
        "the computer at once.",
        "import pkgutil\n"
        "found = [m.name for m in pkgutil.iter_modules() if m.name == 'json']\n"
        "print('found:', found)",
    ),
    "runpy": (
        ADVANCED, BUILDING,
        "Running a .py file as if the reader had typed it, which is how a "
        "program starts another of its own files.",
        "import runpy\n"
        "print('can run a file by name:', callable(runpy.run_path))",
    ),
    "modulefinder": (
        ADVANCED, BUILDING,
        "Finding every file a program imports, so you can see what a "
        "program really needs.",
        "import modulefinder, tempfile, os\n"
        "src = os.path.join(tempfile.mkdtemp(), 'needs_json.py')\n"
        "with open(src, 'w') as f:\n"
        "    f.write('import json\\n')\n"
        "finder = modulefinder.ModuleFinder(path=[src])\n"
        "finder.run_script(src)\n"
        "print('it needs:', sorted(n for n in finder.modules if n == 'json'))",
    ),
    "zipimport": (
        ADVANCED, BUILDING,
        "Importing Python straight out of a zip file, so a program can be "
        "given as a single archive.",
        "import zipimport\n"
        "print('can import from zips:', bool(zipimport.zipimporter))",
    ),
    "py_compile": (
        ADVANCED, BUILDING,
        "Turning a .py file into the faster form Python loads, and refusing "
        "to do it if the file has a syntax error.",
        "import py_compile, tempfile, os\n"
        "src = os.path.join(tempfile.mkdtemp(), 'snippet.py')\n"
        "with open(src, 'w') as f:\n"
        "    f.write('x = 1\\n')\n"
        "target = py_compile.compile(src, doraise=True)\n"
        "print('compiled to', os.path.basename(target))",
    ),
    "pyclbr": (
        ADVANCED, BUILDING,
        "Reading the classes and functions a file defines without running "
        "the file - what many code editors use to offer completions.",
        "import pyclbr, tempfile, os, sys\n"
        "scratch = tempfile.mkdtemp()\n"
        "with open(os.path.join(scratch, 'shapes.py'), 'w') as f:\n"
        "    f.write('class Circle:\\n    pass\\n')\n"
        "sys.path.insert(0, scratch)\n"
        "print(pyclbr.readmodule('shapes'))",
    ),
    "compileall": (
        ADVANCED, BUILDING,
        "Pre-compiling a whole folder of .py files so a program starts "
        "faster next time.",
        "import compileall\n"
        "print('compiles a folder:', callable(compileall.compile_dir))",
    ),
    "ensurepip": (
        ADVANCED, BUILDING,
        "The pip installer that comes with Python, for adding packages to an "
        "interpreter that does not have it yet.",
        "import ensurepip\n"
        "print('pip is bundled:', callable(ensurepip.bootstrap))",
    ),
    "venv": (
        ADVANCED, BUILDING,
        "Making a self-contained Python for one project, so its packages "
        "cannot affect any other program.",
        "import venv\n"
        "print('can build a separate environment:', bool(venv.EnvBuilder))",
    ),
    "zipapp": (
        ADVANCED, BUILDING,
        "Packing a whole program - its code and its modules - into one "
        ".pyz file that runs with Python.",
        "import zipapp\n"
        "print('can pack a program:', callable(zipapp.create_archive))",
    ),
    "site": (
        ADVANCED, BUILDING,
        "The list of folders Python looks in for modules, and the file that "
        "adds to it.",
        "import site\n"
        "print('site-packages is on the path:', any('site-packages' in p for p in site.getsitepackages()))",
    ),
    "sysconfig": (
        ADVANCED, BUILDING,
        "Where Python is installed, and the compiler flags it was built "
        "with.",
        "import sysconfig\n"
        "print('installed at:', sysconfig.get_paths()['purelib'][-20:])\n"
        "print('platform:', sysconfig.get_platform())",
    ),
    "shlex": (
        EVERYDAY, BUILDING,
        "Splitting a typed command line into words, respecting quotes - so "
        "'a \"b c\"' becomes three parts, not four.",
        "import shlex\n"
        "print(shlex.split('run --name \"Ada Lovelace\" --count 3'))",
    ),
    "getopt": (
        EVERYDAY, BUILDING,
        "Reading options from the command line in the short style: -v, -n "
        "value, --help.",
        "import getopt\n"
        "opts, rest = getopt.getopt(['-v', '-n', '3'], 'vn:')\n"
        "print(opts, rest)",
    ),
    "optparse": (
        EVERYDAY, BUILDING,
        "The older, fuller way of reading command-line options and writing "
        "a help message.",
        "import optparse\n"
        "print('a parser can be made:', bool(optparse.OptionParser))",
    ),
    "argparse": (
        EVERYDAY, BUILDING,
        "Turning a command line into named options, and writing the help "
        "text that lists them - the modern way.",
        "import argparse\n"
        "p = argparse.ArgumentParser(prog='notes', description='Keep a note.')\n"
        "p.add_argument('title', help='what the note is called')\n"
        "p.add_argument('-n', '--count', type=int, default=1, help='how many')\n"
        "print(p.parse_args(['lunch', '-n', '2']))",
    ),
    # -- platform specifics -------------------------------------------
    "winreg": (
        ADVANCED, PLATFORM,
        "Reading and writing Windows settings stored in the registry - the "
        "list of programs a machine remembers.",
        "import importlib.util\n"
        "if importlib.util.find_spec('winreg'):\n"
        "    import winreg\n"
        "    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, 'Software')\n"
        "    print('the Windows registry is readable')\n"
        "    winreg.CloseKey(key)\n"
        "else:\n"
        "    print('winreg is only on Windows, so there is no registry to read here')",
    ),
    "msvcrt": (
        ADVANCED, PLATFORM,
        "Talking to the Windows console directly: clearing it, and making a "
        "single keypress arrive without Enter.",
        "import importlib.util\n"
        "if importlib.util.find_spec('msvcrt'):\n"
        "    import msvcrt\n"
        "    print('on Windows, is a keypress waiting?', msvcrt.kbhit())\n"
        "else:\n"
        "    print('msvcrt is only on Windows, so there is no key to ask about here')",
    ),
    "winsound": (
        ADVANCED, PLATFORM,
        "Playing system beeps and .wav files on Windows.",
        "import importlib.util\n"
        "if importlib.util.find_spec('winsound'):\n"
        "    import winsound\n"
        "    print('on Windows it can play a beep:', callable(winsound.Beep))\n"
        "else:\n"
        "    print('winsound is only on Windows, so there is no beep to play here')",
    ),
    "nturl2path": (
        ADVANCED, PLATFORM,
        "Turning a file:// web address into a Windows file path, the "
        "internal support for os.path on Windows.",
        "import nturl2path\n"
        "print(nturl2path.pathname2url('C:/notes.txt'))",
    ),
    "this": (
        ADVANCED, PLATFORM,
        "Prints the Zen of Python: the nineteen rules Python's own "
        "developers wrote down.",
        "import this\n"
        "print('the Zen is', len(this.s), 'lines long')",
    ),
    # -- patterns, text streams and types ----------------------------
    "re": (
        START, TEXT,
        "Finding text by pattern rather than by exact wording - an email "
        "address, a number in a sentence, a repeated word.",
        "import re\n"
        "m = re.search(r'[\\w.+-]+@[\\w-]+\\.[\\w.]+', 'write to ada@example.com today')\n"
        "print('found:', m.group())\n"
        "print(re.findall(r'\\b\\d+\\b', '12 cats and 3 dogs'))",
    ),
    "sre_compile": (
        ADVANCED, TEXT,
        "The part of re that turns a pattern into something fast. You "
        "normally never need to call it yourself.",
        "import sre_compile, re\n"
        "p = sre_compile.compile('a.c')\n"
        "print('same result as re:', bool(p.match('abc')))",
    ),
    "sre_constants": (
        ADVANCED, TEXT,
        "The names of the special codes a regular expression can use, such "
        "as CATEGORY_DIGIT.",
        "import sre_constants\n"
        "print(sre_constants.CATEGORY_DIGIT)",
    ),
    "sre_parse": (
        ADVANCED, TEXT,
        "Reading a regular expression as a structure rather than as a "
        "string - how editors show what a pattern really means.",
        "import sre_parse\n"
        "print(sre_parse.parse(r'\\d+').data[:3])",
    ),
    "io": (
        ADVANCED, FILES,
        "The stream objects Python reads and writes with, and the buffers "
        "that keep a program from asking the disk for every character.",
        "import io\n"
        "buf = io.StringIO()\n"
        "buf.write('one\\ntwo\\n')\n"
        "buf.seek(0)\n"
        "print(list(buf))",
    ),
    "readline": (
        ADVANCED, SYSTEM,
        "Asking a terminal for a line of typed text with editing, used by "
        "interactive prompts.",
        "import importlib.util\n"
        "print('readline is', 'here' if importlib.util.find_spec('readline') else 'not on Windows')",
    ),
    "linecache": (
        ADVANCED, TESTING,
        "Looking up a source line by number even when the file has moved or "
        "been closed, which is how tracebacks still make sense.",
        "import linecache, tempfile, os\n"
        "path = os.path.join(tempfile.mkdtemp(), 'note.py')\n"
        "with open(path, 'w') as f:\n"
        "    f.write('# a short note\\nx = 1\\n')\n"
        "print('line 2 is:', linecache.getline(path, 2).strip())",
    ),
    "opcode": (
        ADVANCED, TESTING,
        "The names of the individual instructions Python's compiler emits.",
        "import opcode\n"
        "print(opcode.opname[opcode.opmap['LOAD_CONST']])",
    ),
    "symtable": (
        ADVANCED, TESTING,
        "The table of every name a piece of code defines and uses, which "
        "says whether a name is local, global or a parameter.",
        "import symtable\n"
        "top = symtable.symtable('b = 1\\ndef f(a):\\n    return a + b\\n', 'f', 'exec')\n"
        "print('b is global:', top.lookup('b').is_global())\n"
        "print('a is local to f:', top.lookup('f').is_local(), top.lookup('f').get_namespace())",
    ),
    "tracemalloc": (
        ADVANCED, TESTING,
        "Finding where the extra memory in a program came from, line by "
        "line.",
        "import tracemalloc\n"
        "tracemalloc.start()\n"
        "big = [str(i) for i in range(10000)]\n"
        "current, peak = tracemalloc.get_traced_memory()\n"
        "tracemalloc.stop()\n"
        "print('in use now:', current, 'bytes; high water:', peak, 'bytes')",
    ),
    "cProfile": (
        ADVANCED, TESTING,
        "The timing engine behind profile: it records every call so a slow "
        "program can be ranked by cost.",
        "import cProfile, pstats, io\n"
        "pr = cProfile.Profile()\n"
        "pr.enable()\n"
        "sum(range(1000))\n"
        "pr.disable()\n"
        "print('recorded calls:', len(pr.getstats()))",
    ),
    "pydoc": (
        EVERYDAY, SYSTEM,
        "The help system built into Python: it finds and prints the "
        "documentation for a module, a class or a function.",
        "import pydoc\n"
        "text = pydoc.render_doc('textwrap', renderer=pydoc.plaintext)\n"
        "print(text.strip().splitlines()[0])",
    ),
    "pydoc_data": (
        ADVANCED, SYSTEM,
        "Python's own documentation and messages, stored as data so they "
        "can be read offline and translated.",
        "import pydoc_data\n"
        "print('ships its own help data as', pydoc_data.__name__)",
    ),
    "typing": (
        EVERYDAY, SYSTEM,
        "Saying what kind of value a function expects and gives back, so a "
        "reader can tell before running it.",
        "from typing import Optional\n"
        "def first(items: list[int]) -> Optional[int]:\n"
        "    return items[0] if items else None\n"
        "print(first([3, 2, 1]), first([]))",
    ),
    "errno": (
        ADVANCED, SYSTEM,
        "The numbers behind the error messages about files and folders, so a "
        "program can tell 'not found' from 'not allowed'.",
        "import errno, os\n"
        "try:\n"
        "    os.stat('no-such-file.txt')\n"
        "except OSError as e:\n"
        "    print(e.errno, 'is', errno.errorcode.get(e.errno, 'unknown'))",
    ),
    "stat": (
        ADVANCED, FILES,
        "The details a file system keeps about a file: its size, when it "
        "changed, and whether it is read-only.",
        "import stat, os, tempfile\n"
        "with tempfile.NamedTemporaryFile(delete=False) as f:\n"
        "    f.write(b'hello')\n"
        "    name = f.name\n"
        "try:\n"
        "    info = os.stat(name)\n"
        "    print('size:', info.st_size, 'bytes')\n"
        "    print('is a plain file:', stat.S_ISREG(info.st_mode))\n"
        "finally:\n"
        "    os.unlink(name)",
    ),
    "pprint": (
        EVERYDAY, DATA,
        "Printing a nested list or dictionary neatly, one item per line, "
        "so it can actually be read.",
        "from pprint import pprint\n"
        "pprint({'b': [3, 2, 1], 'a': {'nested': 'value'}}, width=40, sort_dicts=False)",
    ),
    "pickletools": (
        ADVANCED, DATA,
        "Taking a saved pickle apart to see exactly what is inside it, "
        "which is how a file of unknown origin is checked.",
        "import pickletools\n"
        "raw = __import__('pickle').dumps({'a': 1})\n"
        "print([op.name for op, _, _ in pickletools.genops(raw)][:4])",
    ),
    "ipaddress": (
        ADVANCED, INTERNET,
        "Working with IP addresses and network ranges properly, instead of "
        "handling them as text.",
        "import ipaddress\n"
        "net = ipaddress.ip_network('192.168.1.0/24', strict=False)\n"
        "print('hosts:', net.num_addresses, '| is private:', net.is_private)\n"
        "print(ipaddress.ip_address('10.0.0.1') in net)",
    ),
    "plistlib": (
        ADVANCED, DATA,
        "Reading and writing Apple property list files, the XML or binary "
        "settings format used on Macs and iPhones.",
        "import plistlib\n"
        "print(plistlib.loads(plistlib.dumps({'readability': True}, fmt=plistlib.FMT_XML)))",
    ),
    "quopri": (
        ADVANCED, DATA,
        "Quoted-printable encoding, the way text is written into an email "
        "so it survives being passed around.",
        "import quopri\n"
        "print(quopri.encodestring('café = yes'.encode()).decode())",
    ),
    "netrc": (
        ADVANCED, SYSTEM,
        "The file that stores a machine's login details for a website, so "
        "they do not have to be typed every time.",
        "import netrc\n"
        "print('reads .netrc files:', bool(netrc.netrc))",
    ),
    "resource": (
        ADVANCED, SYSTEM,
        "Asking the operating system how much memory, time or file space "
        "this program is allowed. Unix only.",
        "import importlib.util\n"
        "print('resource is', 'here' if importlib.util.find_spec('resource') else 'only on Linux and Mac')",
    ),
    "fcntl": (
        ADVANCED, SYSTEM,
        "Locks that stop two parts of a program changing the same file at "
        "the same time. Unix only.",
        "import importlib.util\n"
        "print('fcntl is', 'here' if importlib.util.find_spec('fcntl') else 'only on Linux and Mac')",
    ),
    "grp": (
        ADVANCED, SYSTEM,
        "The list of user groups on a Unix computer. Not on Windows.",
        "import importlib.util\n"
        "print('grp is', 'here' if importlib.util.find_spec('grp') else 'only on Linux and Mac')",
    ),
    "pwd": (
        ADVANCED, SYSTEM,
        "The list of user accounts on a Unix computer, and their home "
        "folders. Not on Windows.",
        "import importlib.util\n"
        "print('pwd is', 'here' if importlib.util.find_spec('pwd') else 'only on Linux and Mac')",
    ),
    "pty": (
        ADVANCED, SYSTEM,
        "Running a program as if a person were typing at a terminal, which "
        "is how a program can be tested automatically.",
        "import importlib.util\n"
        "print('pty is', 'here' if importlib.util.find_spec('pty') else 'only on Linux and Mac')",
    ),
    "signal": (
        ADVANCED, SYSTEM,
        "Reacting to the operating system's signals - the polite way a "
        "program is asked to stop or to reload.",
        "import signal\n"
        "def on_stop(signum, frame):\n"
        "    print('asked to stop, tidying up')\n"
        "signal.signal(signal.SIGINT, on_stop)\n"
        "print('handler installed:', signal.getsignal(signal.SIGINT) is on_stop)",
    ),
    "syslog": (
        ADVANCED, SYSTEM,
        "Sending a message to the computer's system log, where a server "
        "keeps a record of everything that happened.",
        "import importlib.util\n"
        "print('the system log is', 'here' if importlib.util.find_spec('syslog') else 'not on Windows')",
    ),
    "threading": (
        EVERYDAY, SYSTEM,
        "Running several pieces of work at the same time inside one "
        "program, each in its own thread.",
        "import threading\n"
        "results = []\n"
        "def work(n):\n"
        "    results.append(n * n)\n"
        "threads = [threading.Thread(target=work, args=(n,)) for n in range(3)]\n"
        "for t in threads:\n"
        "    t.start()\n"
        "for t in threads:\n"
        "    t.join()\n"
        "print(sorted(results))",
    ),
    "concurrent": (
        EVERYDAY, SYSTEM,
        "Running work in parallel, and getting the answers back as they "
        "finish rather than in order.",
        "from concurrent.futures import ThreadPoolExecutor\n"
        "def double(n):\n"
        "    return n * 2\n"
        "with ThreadPoolExecutor(max_workers=3) as pool:\n"
        "    print(list(pool.map(double, [1, 2, 3])))",
    ),
    "asyncio": (
        ADVANCED, SYSTEM,
        "Running many waiting tasks in one go - the way a program talks to "
        "several slow things at the same time.",
        "import asyncio\n"
        "async def fetch(n):\n"
        "    await asyncio.sleep(0)\n"
        "    return n * 2\n"
        "async def main():\n"
        "    return await asyncio.gather(fetch(1), fetch(2))\n"
        "print(asyncio.run(main()))",
    ),
    "multiprocessing": (
        ADVANCED, SYSTEM,
        "Running work in separate processes, so it can use more than one "
        "processor core and cannot be stopped by a stuck thread.",
        "import multiprocessing\n"
        "print('processors available:', multiprocessing.cpu_count())\n"
        "print('a Windows program must guard its work with')\n"
        "print('if __name__ == \"__main__\": before starting processes')",
    ),
    "ctypes": (
        ADVANCED, SYSTEM,
        "Calling into other programs on the computer by name, without "
        "writing anything in their own language.",
        "import ctypes\n"
        "print('can call a C library:', bool(ctypes.CDLL))",
    ),
    "pyexpat": (
        ADVANCED, DATA,
        "The XML parser Python is built on, available directly for programs "
        "that need to go lower than ElementTree.",
        "import pyexpat\n"
        "print('parser names:', pyexpat.version_info[:3])",
    ),
    "wsgiref": (
        ADVANCED, SYSTEM,
        "A small web server, used to serve a Python program to a browser "
        "without installing anything else.",
        "import wsgiref.simple_server\n"
        "print('a small server is available:', bool(wsgiref.simple_server.make_server))",
    ),
    "nt": (
        ADVANCED, PLATFORM,
        "The Windows side of Python's own file and process handling. Most "
        "programs use os instead.",
        "import importlib.util\n"
        "print('the nt module is', 'here' if importlib.util.find_spec('nt') else 'not on this computer')",
    ),
    "posix": (
        ADVANCED, PLATFORM,
        "The Linux and Mac side of Python's own file and process handling.",
        "import importlib.util\n"
        "print('the posix module is', 'here' if importlib.util.find_spec('posix') else 'not on this computer')",
    ),
    # -- the terminal window ------------------------------------------
    "rlcompleter": (
        ADVANCED, SYSTEM,
        "Finishing a word as you type at the interactive prompt - press Tab "
        "and it offers the module names you might have meant.",
        "import rlcompleter\n"
        "print('completes names after a dot, like json.')\n"
        "print('ready:', bool(rlcompleter.Completer()))",
    ),
    "tkinter": (
        EVERYDAY, GRAPHICS,
        "Windows with buttons and boxes, drawn by Python itself - the "
        "quickest way to give a program a proper interface.",
        "import importlib.util\n"
        "print('tkinter is', 'here' if importlib.util.find_spec('tkinter') else 'not installed on this computer')",
    ),
}
