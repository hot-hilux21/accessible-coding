"""Tests for the module index.

Three things could be wrong with an index of 190 modules, and each has its
own test below:

* a name that is not a real module, or that does not exist in the Python
  the index describes - the index would offer something that cannot be
  imported;
* a description or an example that is broken - the reader is told to trust
  these, so they are held to the same standard as the rest of the app;
* a search that answers everything - a search which returns every module
  for every query is not a search, and it looks like a bug to the reader
  before it looks like a feature.
"""
import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from accessible_ide import module_index  # noqa: E402
from accessible_ide.modules_data import (  # noqa: E402
    ADVANCED, EVERYDAY, GROUP_ORDER, START, ENTRIES,
)

PUBLIC = {n for n in sys.stdlib_module_names if not n.startswith('_')}

# The index describes the standard library of Python 3.13. These twenty
# modules were still in the library in 3.12 and were removed in 3.13 (PEP
# 594, "dead batteries"). They are not listed, and that is the right
# answer rather than a gap: telling a reader to import telnetlib when
# their Python no longer has it would be the opposite of help. They are
# named here so the tests below can tell "left out on purpose" apart from
# "missed", on 3.12 as well as on 3.13.
RETIRED_IN_3_13 = frozenset({
    'aifc', 'audioop', 'cgi', 'cgitb', 'chunk', 'crypt', 'imghdr',
    'lib2to3', 'mailcap', 'msilib', 'nis', 'nntplib', 'ossaudiodev',
    'pipes', 'sndhdr', 'spwd', 'sunau', 'telnetlib', 'uu', 'xdrlib',
})

# Three names in the documentation's index that are a demonstration
# package, a joke, and a whole application rather than something a reader
# would go and import. Listing them would be padding: a reader looking for
# the module that draws is not helped by a module that opens a web page.
DELIBERATELY_ABSENT = {'idlelib', 'turtledemo', 'antigravity'}

# os.path is in the documentation's index but is an attribute of os rather
# than a module of its own, so it is not in sys.stdlib_module_names.
EXPECTED_EXTRA = {'os.path'}

# A name the index mentions has to be a real module of this Python, or one
# of the two deliberate exceptions above, or a module that has since been
# removed - so that running these tests on a future Python, which will have
# retired more names, does not report the index as inventing modules.
KNOWN_NAMES = PUBLIC | EXPECTED_EXTRA | RETIRED_IN_3_13


class CatalogueShapeTests(unittest.TestCase):
    """Every entry is a complete, correctly labelled record."""

    def test_every_entry_is_a_full_record(self):
        for name, entry in ENTRIES.items():
            with self.subTest(module=name):
                level, group, summary, example = entry
                self.assertIn(level, (START, EVERYDAY, ADVANCED))
                self.assertIn(group, GROUP_ORDER)
                self.assertTrue(summary.strip())
                self.assertTrue(example.strip())

    def test_descriptions_are_a_sentence_in_plain_words(self):
        # A description is what a reader scans instead of the official
        # docs, so it has to say what the module is for, not what it is
        # called. Anything with a backtick or "module" in it is a
        # placeholder that was never written.
        for name, entry in ENTRIES.items():
            with self.subTest(module=name):
                summary = entry[2]
                self.assertNotIn('`', summary, 'code formatting in a description')
                self.assertGreaterEqual(len(summary.split()), 5)
                self.assertTrue(summary.endswith('.') or summary.endswith('!'),
                                'a description should read as a sentence')

    def test_examples_start_with_an_import(self):
        for name, entry in ENTRIES.items():
            with self.subTest(module=name):
                first = entry[3].splitlines()[0]
                self.assertTrue(
                    first.startswith('import ') or first.startswith('from '),
                    f'{name}: example should start by importing something')

    def test_group_order_has_no_duplicates(self):
        self.assertEqual(len(GROUP_ORDER), len(set(GROUP_ORDER)))


class CatalogueCoverageTests(unittest.TestCase):
    """The index covers the standard library, and nothing invented."""

    def test_no_invented_names(self):
        unknown = sorted(set(ENTRIES) - KNOWN_NAMES)
        self.assertEqual(unknown, [], 'not modules in this Python')

    def test_public_modules_are_all_listed(self):
        missing = sorted(PUBLIC - set(ENTRIES) - DELIBERATELY_ABSENT
                         - RETIRED_IN_3_13)
        self.assertEqual(missing, [], 'standard library modules missing from the index')

    def test_only_deliberate_names_are_absent(self):
        absent = PUBLIC - set(ENTRIES)
        self.assertTrue(
            absent <= DELIBERATELY_ABSENT | RETIRED_IN_3_13,
            f'absent but not deliberately so: '
            f'{sorted(absent - DELIBERATELY_ABSENT - RETIRED_IN_3_13)}')


class AvailabilityTests(unittest.TestCase):
    """Availability is measured, so it can be trusted on any machine."""

    def test_measurement_matches_the_interpreter(self):
        for name in list(ENTRIES)[:60]:
            with self.subTest(module=name):
                self.assertEqual(
                    module_index.available_here(name),
                    importlib.util.find_spec(name.split('.')[0]) is not None)

    def test_absent_module_is_reported_absent(self):
        self.assertFalse(module_index.available_here('definitely_not_a_module_xyz'))

    def test_dotted_name_resolves_to_its_package(self):
        self.assertEqual(module_index.available_here('os.path'),
                         module_index.available_here('os'))


class ExampleRunTests(unittest.TestCase):
    """Every example actually runs.

    Run in a scratch directory with a timeout, because an example that
    waits for input would otherwise hang the suite rather than fail it.
    """

    def test_every_example_runs(self):
        failures = []
        for name, entry in sorted(ENTRIES.items()):
            with self.subTest(module=name):
                ok, detail = self._run(entry[3])
                if not ok:
                    failures.append(f'{name}: {detail}')
        self.assertEqual(failures, [], '\n'.join(failures))

    def test_every_example_compiles(self):
        for name, entry in ENTRIES.items():
            with self.subTest(module=name):
                try:
                    compile(entry[3], name, 'exec')
                except SyntaxError as exc:
                    self.fail(f'{name}: {exc}')

    @staticmethod
    def _run(code):
        with tempfile.TemporaryDirectory() as work:
            env = dict(os.environ, PYTHONIOENCODING='utf-8', PYTHONDONTWRITEBYTECODE='1')
            try:
                done = subprocess.run(
                    [sys.executable, '-I', '-c', code],
                    cwd=work, env=env, capture_output=True, text=True,
                    timeout=20)
            except subprocess.TimeoutExpired:
                return False, 'took too long'
        if done.returncode != 0:
            return False, (done.stderr or '').strip()[-400:]
        return True, ''


class SearchTests(unittest.TestCase):
    """Search finds the module a reader means, and does not find noise."""

    def test_exact_name_wins(self):
        self.assertEqual(module_index.search('json')[0].name, 'json')

    def test_prefix_beats_substring(self):
        names = [e.name for e in module_index.search('so')][:2]
        self.assertEqual(names[0], 'socket')

    def test_finds_by_what_you_want_to_do(self):
        # The whole point: nobody searching for this knows "shutil".
        self.assertEqual(module_index.search('shuffle')[0].name, 'random')
        self.assertIn('shutil', [e.name for e in module_index.search('copy a folder')])
        self.assertIn('decimal', [e.name for e in module_index.search('money')])

    def test_a_short_query_only_ever_matches_names(self):
        # "a" is in nearly every description and is not a word anybody
        # searches a module index for. It may match a name beginning with
        # a; it may never match prose.
        for entry in module_index.search('a'):
            self.assertTrue(entry.name.startswith('a'), entry.name)
        for entry in module_index.search('so'):
            self.assertTrue(entry.name.startswith('so'), entry.name)

    def test_stopwords_do_not_match_prose(self):
        # "the" is in most descriptions. Searching for it should find
        # nothing, not a third of the catalogue.
        self.assertEqual(module_index.search('the'), [])
        self.assertEqual(module_index.search('and'), [])

    def test_a_sentence_does_not_match_by_a_stray_letter(self):
        # Regression: every module whose text contains the letter "a"
        # matched, so "save a file" returned the whole catalogue.
        names = [e.name for e in module_index.search('save a file')]
        self.assertIn('shutil', names)
        self.assertLess(len(names), len(ENTRIES) // 3)
    def test_ordinary_words_are_matched_in_full(self):
        # "math" must not offer hashlib because "mathematics" is in its
        # text somewhere.
        for entry in module_index.search('math'):
            self.assertIn(entry.name, {'math', 'cmath', 'statistics', 'decimal'})

    def test_empty_query_returns_everything(self):
        self.assertEqual(len(module_index.search('')), len(ENTRIES))
        self.assertEqual(len(module_index.search('   ')), len(ENTRIES))

    def test_a_query_with_nothing_to_find_returns_nothing(self):
        self.assertEqual(module_index.search('zzzqqqxyzzy'), [])

    def test_filters_narrow_the_pool(self):
        for level in (START, EVERYDAY, ADVANCED):
            got = module_index.search('math', level=level)
            self.assertTrue(all(e.level == level for e in got))
        got = module_index.search('', group='numbers')
        self.assertTrue(got)
        self.assertTrue(all(e.group == 'numbers' for e in got))

    def test_filters_combine(self):
        got = module_index.search('', level=ADVANCED, group='numbers')
        self.assertTrue(all(e.level == ADVANCED and e.group == 'numbers' for e in got))

    def test_counts_add_up(self):
        self.assertEqual(sum(module_index.counts().values()), len(ENTRIES))


class FindTests(unittest.TestCase):

    def test_known_name(self):
        self.assertIsNotNone(module_index.find('os'))
        padded = module_index.find('  json  ')
        if padded is None:
            self.fail('padded name should be found')
        self.assertEqual(padded.name, 'json')

    def test_unknown_name(self):
        self.assertIsNone(module_index.find('nope_nope'))
        self.assertIsNone(module_index.find(''))


class WebRunnabilityTests(unittest.TestCase):
    """The marker has to agree with the runner it is warning about."""

    def test_desktop_says_everything_runs(self):
        # With no sandbox, the question does not arise and every example
        # is offered without a warning it would never honour.
        self.assertTrue(module_index.runs_in_web('print(1)'))

    def test_marker_uses_the_routes_blocklist(self):
        from accessible_ide import routes
        code = 'import socket'
        expected, _ = routes.check_sandbox(code)
        if routes.SANDBOX:
            self.assertEqual(module_index.runs_in_web(code), expected)
        else:
            self.assertTrue(module_index.runs_in_web(code))


if __name__ == '__main__':
    unittest.main()
