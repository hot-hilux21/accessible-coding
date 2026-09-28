"""Tests for what survives being frozen into a Windows exe.

A PyInstaller build copies the directories listed in the spec file and
nothing else. Python source is compiled in, so a missing import fails the
build loudly. A data file is simply not there, and the app only discovers
that when a reader opens the page that needed it.

That is how the five language files went missing from every published
build: the specs listed static, templates and assets, and i18n was never
added. Nothing failed. The main page came up as a RecursionError that
pointed at the fallback in the translation helper and said nothing about
the files that were absent.
"""
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'src'))

from accessible_ide import i18n  # noqa: E402

SPECS = ('AccessibleIDE.spec', 'AccessibleIDE-onedir.spec')

# Every directory the app reads from disk at run time. The desktop build and
# the hosted copy both need all of them; only the desktop one is frozen.
RUNTIME_DIRS = ('static', 'templates', 'assets', 'i18n')


class SpecContentsTests(unittest.TestCase):
    """Each spec has to list every directory the app reads at run time."""

    def spec_text(self, name):
        path = ROOT / name
        self.assertTrue(path.is_file(), f'{name} is missing')
        return path.read_text(encoding='utf-8')

    def test_every_runtime_directory_is_bundled(self):
        for name in SPECS:
            text = self.spec_text(name)
            for folder in RUNTIME_DIRS:
                with self.subTest(spec=name, folder=folder):
                    self.assertIn(
                        f"src/accessible_ide/{folder}', "
                        f"'accessible_ide/{folder}'",
                        text,
                        f'{name} does not bundle {folder}. A reader opening '
                        'that part of the app would get an error page.')

    def test_the_directories_we_bundle_actually_exist(self):
        # Guards the test above: if a directory is renamed, the spec entry
        # is stale rather than wrong, and the check would pass happily.
        for folder in RUNTIME_DIRS:
            with self.subTest(folder=folder):
                self.assertTrue(
                    (ROOT / 'src' / 'accessible_ide' / folder).is_dir(),
                    f'{folder} is listed for bundling but does not exist')

    def test_no_spec_silently_drops_a_directory(self):
        # Catches a data directory added to the package later. Python modules
        # are compiled into the exe, and a placeholder holding nothing but a
        # .gitkeep is never read, so neither has to be listed - only a
        # directory the app actually opens files from does.
        package = ROOT / 'src' / 'accessible_ide'
        for path in sorted(package.iterdir()):
            if not path.is_dir() or path.name.startswith('__'):
                continue
            shipped = [f for f in path.rglob('*')
                       if f.is_file() and f.name != '.gitkeep'
                       and '__pycache__' not in f.parts]
            if not shipped:
                continue
            for name in SPECS:
                text = self.spec_text(name)
                with self.subTest(spec=name, folder=path.name):
                    self.assertIn(
                        f"accessible_ide/{path.name}'", text,
                        f'{name} does not mention the {path.name} directory, '
                        'which holds files the app reads at run time')


class MissingCatalogueTests(unittest.TestCase):
    """A missing language file has to say so, not recurse."""

    def setUp(self):
        self.original_dir = i18n.I18N_DIR
        i18n.load_catalogue.cache_clear()
        self.addCleanup(self.restore)

    def restore(self):
        i18n.I18N_DIR = self.original_dir
        i18n.load_catalogue.cache_clear()

    def english_only(self):
        """Repoint the loader at a directory holding en.json and nothing else."""
        only = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, only, True)
        shutil.copy(self.original_dir / 'en.json', only / 'en.json')
        i18n.I18N_DIR = only
        i18n.load_catalogue.cache_clear()
        return only

    def test_english_missing_names_the_file_instead_of_recursing(self):
        empty = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, empty, True)
        i18n.I18N_DIR = empty
        with self.assertRaises(FileNotFoundError) as caught:
            i18n.load_catalogue(i18n.DEFAULT_LOCALE)
        self.assertIn('en.json', str(caught.exception))

    def test_another_language_missing_still_falls_back_to_english(self):
        # The fallback itself has to keep working - only the floor is
        # allowed to be missing, and only it is allowed to fail.
        self.english_only()
        self.assertEqual(i18n.load_catalogue('fr'),
                         i18n.load_catalogue('en'))
        self.assertEqual(i18n.load_catalogue('fr')['app.title'],
                         'AccessibleIDE - Code comfortably')

    def test_an_unknown_language_falls_back_rather_than_failing(self):
        # A language we never heard of is not an error, it is English.
        self.english_only()
        self.assertEqual(i18n.load_catalogue('zz'),
                         i18n.load_catalogue('en'))


class IsolatedConfigTests(unittest.TestCase):
    """Base class giving each test a private config file.

    routes.py reads its config path as a module-level global and the page
    takes its language out of that file, so both have to be repointed or a
    test would quietly render in whatever language the machine is set to.
    """

    def setUp(self):
        from accessible_ide import create_app, routes
        self._tmp = tempfile.TemporaryDirectory()
        tmp = Path(self._tmp.name)
        self._saved = (routes.CONFIG_DIR, routes.CONFIG_FILE, routes.ACCESS_CODE)
        self._i18n_dir = i18n.I18N_DIR
        routes.CONFIG_DIR = tmp
        routes.CONFIG_FILE = tmp / 'config.json'
        routes.ACCESS_CODE = ''
        app = create_app()
        app.config['TESTING'] = True
        self.client = app.test_client()
        self.addCleanup(self.restore)

    def restore(self):
        from accessible_ide import routes
        routes.CONFIG_DIR, routes.CONFIG_FILE, routes.ACCESS_CODE = self._saved
        i18n.I18N_DIR = self._i18n_dir
        i18n.load_catalogue.cache_clear()
        self._tmp.cleanup()

    def write_config(self, **values):
        from accessible_ide import routes
        routes.save_config(values)


class MainPageTests(IsolatedConfigTests):
    """The page a reader actually opens has to render."""

    def test_the_main_page_renders(self):
        reply = self.client.get('/')
        self.assertEqual(reply.status_code, 200)

    def test_the_main_page_renders_in_the_language_the_config_asks_for(self):
        # If a language file went missing the page would still come up, just
        # in English. So check the other way round: this request must not
        # have quietly fallen back. The expected text is read from the
        # catalogue rather than typed in, so a mistranscribed literal here
        # cannot pass or fail for the wrong reason.
        french = i18n.load_catalogue('fr')
        english = i18n.load_catalogue('en')
        self.assertNotEqual(french['app.title'], english['app.title'])

        self.write_config(locale='fr')
        reply = self.client.get('/')
        self.assertEqual(reply.status_code, 200)
        page = reply.get_data(as_text=True)
        self.assertIn(french['app.title'], page)
        self.assertNotIn(english['app.title'], page)

    def test_a_missing_language_file_says_which_file_is_missing(self):
        # Every published build shipped without the language files, and each
        # page came up as a RecursionError naming no file. With the files
        # gone the error has to name them.
        empty = Path(self._tmp.name) / 'no-languages'
        empty.mkdir()
        i18n.I18N_DIR = empty
        i18n.load_catalogue.cache_clear()
        with self.assertRaises(FileNotFoundError) as caught:
            self.client.get('/')
        self.assertIn('en.json', str(caught.exception))


if __name__ == '__main__':
    unittest.main()
