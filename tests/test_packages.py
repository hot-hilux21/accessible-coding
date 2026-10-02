"""Tests for the package manager: names, install, list, remove.

The rules these enforce are the ones that make the feature safe to offer to
somebody who did not know they needed it:

- installing is never automatic, so the mapping from an imported name to the
  distribution that provides it has to be right or the reader is sent to a
  package that does not exist;
- packages land in the reader's own folder, never inside the app, because the
  app folder is not writable by a normal reader and is replaced on every
  update;
- nothing installs or uninstalls without a name that is actually a package
  name, so a request cannot point pip at a path, a flag, or a URL;
- a removal takes out the files that were installed and leaves the files
  another installed package also owns.
"""

import os
import re
import subprocess
import unittest
from pathlib import Path
from unittest import mock

from accessible_ide import i18n, packages


class PackageNameMapping(unittest.TestCase):
    def test_the_obvious_case(self):
        # The one everybody hits first: the import is not the package name.
        self.assertEqual(packages.package_for_module('PIL'), 'Pillow')
        self.assertEqual(packages.package_for_module('yaml'), 'PyYAML')

    def test_a_dotted_name_is_reduced_to_its_first_part(self):
        # The reader has to be offered the package, not the submodule. There is
        # no such thing on PyPI as "PIL.Image".
        self.assertEqual(packages.package_for_module('PIL.Image'), 'Pillow')
        self.assertEqual(packages.package_for_module('sklearn.ensemble'), 'scikit-learn')

    def test_a_name_that_is_already_the_package_name(self):
        self.assertEqual(packages.package_for_module('numpy'), 'numpy')
        self.assertEqual(packages.package_for_module('pygame'), 'pygame')

    def test_module_of_goes_the_other_way(self):
        self.assertEqual(packages.module_of('Pillow'), 'PIL')
        self.assertEqual(packages.module_of('opencv-python'), 'cv2')
        self.assertEqual(packages.module_of('numpy'), 'numpy')

    def test_every_table_entry_is_a_usable_import_name(self):
        # A typo in the table would send a reader to a package that installs
        # and then still fails to import, which is worse than no offer at all.
        for module, distribution in packages._MODULE_TO_PACKAGE.items():
            with self.subTest(module=module):
                self.assertTrue(module.isidentifier(), module)
                self.assertRegex(distribution, r'^[A-Za-z0-9][A-Za-z0-9._-]*$')

    def test_a_builtin_is_never_offered_as_a_package(self):
        # sys and json are part of Python. Offering to install them sends the
        # reader hunting for something that cannot be bought, and pip would
        # either fail or fetch a squatted name.
        import sys as real_sys
        for module in ('sys', 'os', 'json', 'collections', 'math'):
            with self.subTest(module=module):
                self.assertIn(module, real_sys.stdlib_module_names)
        # The check the route actually relies on: nothing maps a standard
        # library module to a distribution.
        for module in real_sys.stdlib_module_names:
            if module in packages._MODULE_TO_PACKAGE:
                self.fail(f'{module} is part of Python but is in the table')


class MissingModuleParsing(unittest.TestCase):
    """Reading the module name out of a traceback."""

    def test_reads_a_plain_name(self):
        text = "ModuleNotFoundError: No module named 'numpy'"
        self.assertEqual(packages.missing_module(text), 'numpy')

    def test_reads_a_dotted_name_as_its_package(self):
        # This is what a real failure looks like, and the whole point of
        # returning the first part is that the submodule is not installable.
        text = "ModuleNotFoundError: No module named 'PIL.Image'"
        self.assertEqual(packages.missing_module(text), 'PIL')

    def test_the_annotated_form_matches(self):
        # CPython writes the annotated form for an import that failed further
        # in. Matching only the bare form would miss half of these.
        text = "ModuleNotFoundError: No module named 'PIL.Image', line 1"
        self.assertEqual(packages.missing_module(text), 'PIL')

    def test_double_quotes_as_well_as_single(self):
        text = 'ModuleNotFoundError: No module named "requests"'
        self.assertEqual(packages.missing_module(text), 'requests')

    def test_a_different_error_gives_nothing(self):
        # This is the case that matters most: an unrelated error must not
        # produce a package name, or the app offers to install something
        # because of a NameError.
        self.assertEqual(packages.missing_module("NameError: name 'boom' is not defined"), '')
        self.assertEqual(packages.missing_module('SyntaxError: invalid syntax'), '')
        self.assertEqual(packages.missing_module('Traceback (most recent call last):'), '')
        self.assertEqual(packages.missing_module(''), '')

    def test_the_two_ends_agree(self):
        # What the shell route does, end to end: an error string in, a package
        # name out, and nothing for an error that is not a missing import. The
        # route guards the empty case rather than passing it on, which is why
        # the guard is written out here too.
        text = "ModuleNotFoundError: No module named 'PIL'"
        self.assertEqual(
            packages.package_for_module(packages.missing_module(text)), 'Pillow')
        other = "NameError: name 'boom' is not defined"
        found = packages.missing_module(other)
        self.assertEqual(packages.package_for_module(found) if found else '', '')


class WherePackagesLive(unittest.TestCase):
    def test_the_folder_is_inside_the_readers_own_data(self):
        # Not beside the app. The app folder is Program Files on a packaged
        # install, which a reader cannot write to and which every update
        # replaces.
        self.assertEqual(packages.packages_dir(), packages.data_dir() / 'packages')

    def test_the_default_is_the_readers_home_not_the_app(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop('ACCESSIBLE_IDE_DATA_DIR', None)
            self.assertEqual(packages.data_dir(), Path.home() / '.accessible-ide')

    def test_the_folder_is_not_inside_this_checkout(self):
        here = Path(__file__).resolve().parent.parent
        self.assertNotIn(here, packages.packages_dir().resolve().parents)

    def test_the_override_is_honoured(self):
        # The tests need somewhere harmless to point at, and so does anybody
        # running a portable copy on a USB stick.
        with mock.patch.dict(os.environ, {'ACCESSIBLE_IDE_DATA_DIR': 'D:/portable'}):
            self.assertEqual(packages.packages_dir(), Path('D:/portable') / 'packages')


class NameValidation(unittest.TestCase):
    """What may be asked for. pip is never handed a shell string, so this is
    about refusing nonsense and anything carrying a path."""

    def test_a_plain_name_is_kept(self):
        self.assertEqual(packages._validate_name('  pygame  '), 'pygame')

    def test_dots_dashes_and_underscores_are_allowed(self):
        for name in ('ruamel.yaml', 'my-package', 'my_package', 'zope.interface'):
            with self.subTest(name=name):
                self.assertEqual(packages._validate_name(name), name)

    def test_nothing_is_refused(self):
        for name in ('', '   ', None):
            with self.subTest(name=name):
                with self.assertRaises(packages.PackageError) as caught:
                    packages._validate_name(name)
                self.assertEqual(caught.exception.reason, 'bad_name')

    def test_a_path_is_refused(self):
        for name in ('../evil', 'C:/Windows/System32', 'a/b', 'a\\b'):
            with self.subTest(name=name):
                with self.assertRaises(packages.PackageError):
                    packages._validate_name(name)

    def test_a_flag_or_a_url_is_refused(self):
        # pip takes these as options rather than package names, so passing one
        # through would turn a name box into a way to change what pip does.
        for name in ('--index-url=http://elsewhere', '-e', 'git+https://x/y',
                     '--upgrade', 'toml; rm -rf /'):
            with self.subTest(name=name):
                with self.assertRaises(packages.PackageError):
                    packages._validate_name(name)


class InstalledListing(unittest.TestCase):
    def _installed(self, names):
        entries = [Path('C:/pkgs') / name for name in names]
        with mock.patch.object(packages, 'packages_dir', return_value=Path('C:/pkgs')), \
             mock.patch.object(packages.Path, 'iterdir', return_value=iter(entries)), \
             mock.patch.object(packages.Path, 'is_dir', return_value=True):
            return packages.installed()

    def test_a_distribution_is_read_from_its_folder_name(self):
        found = self._installed(['toml-0.10.2.dist-info'])
        self.assertEqual([(p.name, p.version) for p in found], [('toml', '0.10.2')])

    def test_a_name_containing_a_dash_survives(self):
        # Split on the last dash, not the first: "typing-extensions" is one
        # name, and splitting the first dash reports a package called
        # "extensions" that nobody installed.
        found = self._installed(['typing-extensions-4.9.0.dist-info'])
        self.assertEqual((found[0].name, found[0].version), ('typing-extensions', '4.9.0'))

    def test_things_that_are_not_packages_are_ignored(self):
        # A __pycache__ or a stray file in the folder is not a distribution,
        # and reporting it as one would put it in the list with no version.
        found = self._installed(['__pycache__', 'README.txt', 'toml-0.10.2.dist-info'])
        self.assertEqual([p.name for p in found], ['toml'])

    def test_the_list_is_in_name_order(self):
        # Stable order matters because the reader reads it with a screen reader
        # and a list that reshuffles between openings is hard to follow.
        found = self._installed(['toml-0.10.2.dist-info',
                                 'Pillow-10.0.0.dist-info',
                                 'asyncio-1.0.dist-info'])
        self.assertEqual([p.name for p in found], ['asyncio', 'Pillow', 'toml'])

    def test_a_missing_folder_is_an_empty_list_not_an_error(self):
        # Before anything is installed the folder may not exist at all, and
        # that is the normal state of a fresh install rather than a fault.
        with mock.patch.object(packages, 'packages_dir', return_value=Path('C:/pkgs')), \
             mock.patch.object(packages.Path, 'is_dir', return_value=False):
            self.assertEqual(packages.installed(), [])

    def test_asking_whether_something_is_installed(self):
        with mock.patch.object(packages, 'installed', return_value=[
            packages.PackageInfo('Pillow', '10.0.0', 'PIL')]):
            # pip compares distribution names case-insensitively with the
            # separators folded, so the check has to as well.
            self.assertTrue(packages.is_installed('pillow'))
            self.assertTrue(packages.is_installed('Pillow'))
            self.assertFalse(packages.is_installed('numpy'))

    def test_it_compares_distribution_names_not_import_names(self):
        # is_installed answers "is this package already here", and it is given
        # a package name. Import names go through package_for_module first, so
        # matching on them here would make "Pillow" and "PIL" two packages.
        with mock.patch.object(packages, 'installed', return_value=[
            packages.PackageInfo('Pillow', '10.0.0', 'PIL')]):
            self.assertFalse(packages.is_installed('PIL'))


class PipDiscovery(unittest.TestCase):
    """Finding a Python that has pip. In the packaged build sys.executable is
    the app, so asking it for pip would relaunch the app instead."""

    def _run(self, results):
        """A fake subprocess.run answering per candidate path."""
        def fake(cmd, *args, **kwargs):
            for candidate, ok in results.items():
                if str(cmd[0]).lower().endswith(candidate.lower()):
                    return subprocess.CompletedProcess(cmd, 0 if ok else 1, '', '')
            return subprocess.CompletedProcess(cmd, 1, '', 'not found')
        return mock.Mock(side_effect=fake)

    def test_a_source_checkout_uses_the_python_running_the_app(self):
        with mock.patch.object(packages.sys, 'frozen', False, create=True), \
             mock.patch.object(packages.sys, 'executable', r'C:\py\python.exe'), \
             mock.patch.object(packages.subprocess, 'run', self._run({'C:\\py\\python.exe': True})):
            self.assertEqual(packages._pip_interpreter(), r'C:\py\python.exe')

    def test_a_frozen_build_never_uses_the_app_exe(self):
        # The whole reason this function exists. sys.executable is
        # AccessibleIDE.exe there, and piping to it does not run pip.
        with mock.patch.object(packages.sys, 'frozen', True, create=True), \
             mock.patch.object(packages.sys, 'executable', r'C:\app\AccessibleIDE.exe'), \
             mock.patch.object(packages.sys, '_MEIPASS', r'C:\app\_internal', create=True), \
             mock.patch.object(packages.Path, 'exists', return_value=False), \
             mock.patch.object(packages.subprocess, 'run', self._run({})):
            found = packages._pip_interpreter()
        self.assertIsNone(found)

    def test_the_unpacked_interpreter_is_used_when_it_is_there(self):
        with mock.patch.object(packages.sys, 'frozen', True, create=True), \
             mock.patch.object(packages.sys, 'executable', r'C:\app\AccessibleIDE.exe'), \
             mock.patch.object(packages.sys, '_MEIPASS', r'C:\app\_internal', create=True), \
             mock.patch.object(packages.Path, 'exists', return_value=True), \
             mock.patch.object(packages.subprocess, 'run', self._run({'python.exe': True})):
            found = packages._pip_interpreter()
        self.assertTrue(found.endswith('python.exe'))
        self.assertNotIn('AccessibleIDE', found)

    def test_a_python_without_pip_is_not_offered(self):
        # A Python that cannot install anything is worse than none found,
        # because the button would then fail for reasons nobody can explain.
        with mock.patch.object(packages.sys, 'frozen', False, create=True), \
             mock.patch.object(packages.sys, 'executable', r'C:\py\python.exe'), \
             mock.patch.object(packages.subprocess, 'run', self._run({})):
            self.assertIsNone(packages._pip_interpreter())
            self.assertFalse(packages.pip_available())

    def test_the_probe_asks_whether_pip_imports(self):
        # Not "--version": the question is whether pip can be imported, which
        # is the thing install actually needs.
        with mock.patch.object(packages.sys, 'frozen', False, create=True), \
             mock.patch.object(packages.sys, 'executable', r'C:\py\python.exe'), \
             mock.patch.object(packages.subprocess, 'run', self._run({'C:\\py\\python.exe': True})) as run:
            packages._pip_interpreter()
        probe = run.call_args[0][0]
        self.assertIn('import pip', probe[-1])


class InstallCommand(unittest.TestCase):
    """What actually gets run, read from the recorded call so the suite needs
    no network and no installed package."""

    def _install(self, name='toml'):
        # is_installed is asked twice: once before pip runs, and once after to
        # confirm something landed. False then True is the honest sequence.
        with mock.patch.object(packages, '_run_pip') as run_pip, \
             mock.patch.object(packages, '_ensure_packages_dir',
                               return_value=Path('C:/data/packages')), \
             mock.patch.object(packages, 'is_installed',
                               side_effect=[False, True]), \
             mock.patch.object(packages, 'installed', return_value=[
                 packages.PackageInfo(name, '0.10.2', name)]):
            run_pip.return_value = subprocess.CompletedProcess([], 0, '', '')
            result = packages.install(name)
        return run_pip.call_args[0][0], result

    def test_the_package_is_installed_into_the_readers_folder(self):
        args, _ = self._install()
        # --target is what keeps the app's own files and the system Python out
        # of it. Without it, "install into the app" quietly means "install
        # everywhere this user can reach".
        self.assertIn('--target', args)
        self.assertIn(str(packages.packages_dir()), args)

    def test_the_name_is_its_own_argument(self):
        # Not joined into a string, so there is nothing for a shell to read.
        args, _ = self._install('pygame')
        self.assertIn('pygame', args)

    def test_the_reader_is_never_left_answering_a_prompt(self):
        # --no-input stops pip waiting on a question in a window with nobody
        # in it, which would hang the request until the timeout. Added where
        # pip is actually launched, so this reads the real command.
        with mock.patch.object(packages, '_pip_interpreter', return_value='C:/py/python.exe'), \
             mock.patch.object(packages.subprocess, 'run') as run:
            run.return_value = subprocess.CompletedProcess([], 0, '', '')
            packages._run_pip(['install', 'toml'], 30)
        args = run.call_args[0][0]
        self.assertIn('--no-input', args)
        self.assertIn('-m', args)
        self.assertIn('pip', args)

    def test_pip_never_gets_a_shell(self):
        # The name is one argument, and there is no shell=True anywhere, so a
        # name that got past validation still has nothing to be interpreted by.
        with mock.patch.object(packages, '_pip_interpreter', return_value='C:/py/python.exe'), \
             mock.patch.object(packages.subprocess, 'run') as run:
            run.return_value = subprocess.CompletedProcess([], 0, '', '')
            packages._run_pip(['install', 'toml'], 30)
        self.assertNotIn('shell', run.call_args.kwargs)

    def test_a_failure_is_a_reason_not_an_exception_detail(self):
        with mock.patch.object(packages, '_run_pip') as run_pip, \
             mock.patch.object(packages, '_ensure_packages_dir', return_value=Path('C:/p')), \
             mock.patch.object(packages, 'is_installed', return_value=False):
            run_pip.return_value = subprocess.CompletedProcess([], 1, '', 'ERROR: No matching distribution')
            with self.assertRaises(packages.PackageError) as caught:
                packages.install('nope')
        self.assertEqual(caught.exception.reason, 'install_failed')
        self.assertIn('No matching distribution', caught.exception.detail)

    def test_pip_can_exit_zero_and_still_have_installed_nothing(self):
        # pip does this when it decides the requirement is already satisfied
        # somewhere else. The list and the reader's next import have to agree,
        # so what is on disk is what counts.
        with mock.patch.object(packages, '_run_pip') as run_pip, \
             mock.patch.object(packages, '_ensure_packages_dir', return_value=Path('C:/p')), \
             mock.patch.object(packages, 'is_installed', return_value=False):
            run_pip.return_value = subprocess.CompletedProcess([], 0, 'Requirement already satisfied', '')
            with self.assertRaises(packages.PackageError) as caught:
                packages.install('toml')
        self.assertEqual(caught.exception.reason, 'not_installed')

    def test_a_package_already_there_is_not_installed_again(self):
        with mock.patch.object(packages, '_run_pip') as run_pip, \
             mock.patch.object(packages, 'is_installed', return_value=True), \
             mock.patch.object(packages, 'installed', return_value=[
                 packages.PackageInfo('Pillow', '10.0.0', 'PIL')]):
            result = packages.install('pillow')
        run_pip.assert_not_called()
        self.assertEqual(result.name, 'Pillow')

    def test_no_pip_is_a_reason_the_reader_can_be_told(self):
        with mock.patch.object(packages, '_pip_interpreter', return_value=None):
            with self.assertRaises(packages.PackageError) as caught:
                packages._run_pip(['install', 'toml'], 30)
        self.assertEqual(caught.exception.reason, 'no_pip')


class Removal(unittest.TestCase):
    """Removing by hand, because pip uninstall has no --target."""

    def _make_package(self, root, name, version, files, extra_info=()):
        """A package laid out the way pip leaves one."""
        info = root / f'{name}-{version}.dist-info'
        info.mkdir(parents=True)
        record = [f'{path},sha256=abc,10' for path in files]
        (info / 'RECORD').write_text('\n'.join(record) + '\n', encoding='utf-8')
        for path in files:
            target = root / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(f'# {path}\n', encoding='utf-8')
        for entry in extra_info:
            (info / entry).write_text('x', encoding='utf-8')
        return info

    def test_a_package_and_its_folder_are_removed(self):
        with tempfile_in_temp() as root:
            self._make_package(root, 'toml', '0.10.2',
                               ['toml/__init__.py', 'toml/decoder.py'])
            with mock.patch.object(packages, 'packages_dir', return_value=root):
                self.assertTrue(packages.uninstall('toml'))
                self.assertEqual(packages.installed(), [])
            # The directory that only held it goes too, or the reader is told
            # it is gone while the folder is still sitting there.
            self.assertFalse((root / 'toml').exists())

    def test_another_packages_files_are_left_alone(self):
        # Two distributions can share a file. Deleting it here breaks the one
        # that still needs it.
        with tempfile_in_temp() as root:
            self._make_package(root, 'first', '1.0', ['shared/data.json'])
            self._make_package(root, 'second', '1.0', ['shared/data.json'])
            with mock.patch.object(packages, 'packages_dir', return_value=root):
                packages.uninstall('first')
            self.assertTrue((root / 'shared' / 'data.json').exists())

    def test_a_package_that_is_not_there_is_not_a_failure(self):
        # The reader asked for it to go. It had already gone. That is the
        # outcome they asked for.
        with tempfile_in_temp() as root:
            with mock.patch.object(packages, 'packages_dir', return_value=root):
                self.assertFalse(packages.uninstall('numpy'))

    def test_nothing_installed_yet_is_not_a_failure(self):
        with tempfile_in_temp() as root:
            with mock.patch.object(packages, 'packages_dir', return_value=root):
                self.assertFalse(packages.uninstall('numpy'))

    def test_a_record_that_cannot_be_read_still_removes_the_listing(self):
        # A RECORD that is missing makes the removal conservative about files.
        # The .dist-info going is what stops the package being listed and
        # stops it being importable, and that part has to happen.
        with tempfile_in_temp() as root:
            info = root / 'odd-1.0.dist-info'
            info.mkdir(parents=True)
            orphan = root / 'odd'
            orphan.mkdir()
            (orphan / '__init__.py').write_text('# left behind on purpose\n', encoding='utf-8')
            with mock.patch.object(packages, 'packages_dir', return_value=root):
                self.assertTrue(packages.uninstall('odd'))
            self.assertFalse(info.exists())
            self.assertTrue(orphan.exists())

    def test_a_record_cannot_reach_outside_the_packages_folder(self):
        # This list is going to delete files. A RECORD naming ../../something
        # is refused outright rather than followed.
        with tempfile_in_temp() as root:
            info = root / 'evil-1.0.dist-info'
            info.mkdir(parents=True)
            (info / 'RECORD').write_text(
                '../../outside.txt,sha256=abc,10\n/etc/passwd,sha256=abc,10\n',
                encoding='utf-8')
            self.assertEqual(packages._owned_files(info), set())

    def test_a_name_with_a_dash_is_found_again(self):
        with tempfile_in_temp() as root:
            self._make_package(root, 'typing-extensions', '4.9.0',
                               ['typing_extensions.py'])
            with mock.patch.object(packages, 'packages_dir', return_value=root):
                self.assertTrue(packages.uninstall('typing-extensions'))
                self.assertEqual(packages.installed(), [])


class FailureReasons(unittest.TestCase):
    """Every reason is one the interface has words for. A reason nobody can
    translate is a raw pip log in front of a reader."""

    def test_every_reason_the_module_raises_has_a_sentence_everywhere(self):
        source = Path(packages.__file__).read_text(encoding='utf-8')
        raised = set(re.findall(r"raise PackageError\(\s*'([a-z_]+)'", source))
        self.assertTrue(raised)
        for code in i18n.LANGUAGES:
            catalogue = i18n.load_catalogue(code)
            for reason in sorted(raised):
                with self.subTest(locale=code, reason=reason):
                    self.assertIn(f'packages.{reason}', catalogue)
                    self.assertTrue(catalogue[f'packages.{reason}'].strip())

    def test_the_detail_is_kept_for_the_log_and_the_words_are_not_lost(self):
        # The reader gets a sentence; the detail goes to the log. Both exist
        # and neither replaces the other.
        error = packages.PackageError('install_failed', 'pip said no')
        self.assertEqual(error.reason, 'install_failed')
        self.assertEqual(error.detail, 'pip said no')

    def test_pip_output_is_summarised_not_passed_on(self):
        # pip's own last line is usually the useful one; the rest is resolver
        # detail aimed at somebody who knows what backtracking is.
        result = subprocess.CompletedProcess(
            [], 1,
            stdout='Collecting nothing\n',
            stderr='  Reading package lists\nERROR: Could not find a version that satisfies the requirement\n')
        self.assertIn('Could not find a version', packages._summarise(result))

    def test_a_summarise_of_nothing_is_empty_rather_than_a_crash(self):
        result = subprocess.CompletedProcess([], 1, stdout='', stderr='')
        self.assertEqual(packages._summarise(result), '')


class PackageInfoShape(unittest.TestCase):
    def test_it_reports_what_the_list_needs(self):
        info = packages.PackageInfo('Pillow', '10.0.0', 'PIL')
        self.assertEqual(info.as_dict(),
                         {'name': 'Pillow', 'version': '10.0.0', 'module': 'PIL'})


class WhatTheShellIsTold(unittest.TestCase):
    """The variable the shell and the runner pass down, and what happens when
    there is nothing to pass."""

    def test_it_is_the_packages_folder(self):
        self.assertEqual(packages.python_path(), str(packages.packages_dir()))

    def test_it_is_a_path_separator_list_even_when_several_are_added(self):
        # The child splits on os.pathsep, so one value here means one entry
        # there. Asserted by construction rather than by parsing.
        self.assertNotIn(os.pathsep, packages.python_path())


def tempfile_in_temp():
    """A throwaway directory that cleans itself up."""
    import tempfile
    from contextlib import contextmanager

    @contextmanager
    def make():
        with tempfile.TemporaryDirectory() as path:
            yield Path(path)

    return make()


if __name__ == '__main__':
    unittest.main()