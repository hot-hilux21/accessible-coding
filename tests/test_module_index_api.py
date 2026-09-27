"""Tests for the module index endpoints and the markup that drives them.

Split from test_module_index.py on purpose: that file checks the data and
the search, this one checks that the HTTP layer and the page agree, which
is a different thing to break.
"""
import json
import os
import re
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from accessible_ide import create_app, i18n  # noqa: E402
from accessible_ide.modules_data import ENTRIES  # noqa: E402

LOCALES = ('en', 'hi', 'fr', 'es', 'ar')


class ModulesApiTestCase(unittest.TestCase):

    def setUp(self):
        os.environ['SECRET_KEY'] = 'test-key'
        self.app = create_app()
        self.client = self.app.test_client()

    def get(self, url):
        res = self.client.get(url)
        return res, res.get_json()


class ListEndpointTests(ModulesApiTestCase):

    def test_returns_every_module(self):
        res, data = self.get('/api/modules')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(data['total'], len(ENTRIES))
        self.assertEqual(data['total_all'], len(ENTRIES))
        self.assertEqual(len(data['modules']), len(ENTRIES))

    def test_search_narrows_the_list(self):
        _, data = self.get('/api/modules?q=shuffle')
        self.assertEqual(data['modules'][0]['name'], 'random')
        self.assertLess(data['total'], len(ENTRIES))
        # The count of everything is still reported, so the reader can
        # see there is more to find by clearing the search.
        self.assertEqual(data['total_all'], len(ENTRIES))

    def test_availability_is_reported_per_module(self):
        _, data = self.get('/api/modules')
        for entry in data['modules']:
            self.assertIn('available', entry)
            self.assertIsInstance(entry['available'], bool)

    def test_examples_are_not_in_the_list(self):
        # A few hundred lines of code nobody asked for. They are fetched
        # one at a time when a module is opened.
        _, data = self.get('/api/modules')
        self.assertNotIn('example', data['modules'][0])

    def test_level_filter(self):
        _, data = self.get('/api/modules?level=start')
        self.assertTrue(data['modules'])
        self.assertTrue(all(m['level'] == 'start' for m in data['modules']))
        self.assertEqual(sum(data['counts'].values()), len(ENTRIES))

    def test_group_filter(self):
        _, data = self.get('/api/modules?group=numbers')
        self.assertTrue(data['modules'])
        self.assertTrue(all(m['group'] == 'numbers' for m in data['modules']))

    def test_filters_combine(self):
        _, data = self.get('/api/modules?level=advanced&group=numbers')
        self.assertTrue(all(m['level'] == 'advanced' and m['group'] == 'numbers'
                            for m in data['modules']))

    def test_unknown_filter_is_rejected_with_the_allowed_values(self):
        # The message has to say what was allowed, or the reader is left
        # guessing what to type instead.
        res, data = self.get('/api/modules?level=nope')
        self.assertEqual(res.status_code, 400)
        self.assertIn('start', data['error'])
        res, data = self.get('/api/modules?group=nope')
        self.assertEqual(res.status_code, 400)
        self.assertIn('numbers', data['error'])
        self.assertNotIn('start', data['error'])

    def test_surrounding_whitespace_is_ignored(self):
        _, data = self.get('/api/modules?q=%20%20')
        self.assertEqual(data['total'], len(ENTRIES))

    def test_a_query_that_matches_nothing_is_an_empty_list_not_an_error(self):
        res, data = self.get('/api/modules?q=zzzqqqxyzzy')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(data['total'], 0)
        self.assertEqual(data['modules'], [])


class DetailEndpointTests(ModulesApiTestCase):

    def test_returns_the_example(self):
        res, data = self.get('/api/modules/json')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(data['name'], 'json')
        self.assertIn('import json', data['example'])
        self.assertTrue(data['summary'])
        self.assertIn('runs_in_web', data)

    def test_summary_is_never_embedded_markup(self):
        # The detail is inserted as text, but a description that came to
        # contain markup would be worth catching at the source.
        for name in ('keyword', 'json', 'os.path'):
            _, data = self.get(f'/api/modules/{name}')
            self.assertNotIn('<', data['summary'])

    def test_unknown_module_is_404(self):
        res, data = self.get('/api/modules/definitely_not_a_module')
        self.assertEqual(res.status_code, 404)
        self.assertIn('error', data)


class I18nTests(unittest.TestCase):
    """The index's own strings exist in every language the app ships."""

    KEYS = (
        'modules.title', 'modules.intro', 'modules.search_label',
        'modules.search_help', 'modules.clear', 'modules.filter',
        'modules.level_all', 'modules.level_start', 'modules.level_everyday',
        'modules.level_advanced', 'modules.results', 'modules.results_aria',
        'modules.no_results', 'modules.no_results_hint',
        'modules.available_here', 'modules.not_available',
        'modules.web_blocked', 'modules.example', 'modules.insert',
        'modules.inserted', 'modules.run', 'modules.loading',
        'modules.english_note', 'modules.detail_label', 'modules.choose',
        'modules.close', 'modules.results_label', 'modules.show_more',
    )

    def test_every_locale_has_every_key(self):
        for loc in LOCALES:
            table = i18n.load_catalogue(loc)
            for key in self.KEYS:
                with self.subTest(locale=loc, key=key):
                    self.assertIn(key, table)
                    self.assertTrue(table[key].strip())

    def test_group_names_exist(self):
        from accessible_ide.modules_data import GROUP_ORDER
        for loc in LOCALES:
            table = i18n.load_catalogue(loc)
            for group in GROUP_ORDER:
                key = f'modules.group_{group}'
                with self.subTest(locale=loc, key=key):
                    self.assertIn(key, table)

    def test_placeholder_count_matches(self):
        # A string with {0} and one with {0} {1} are fine; a translation
        # that lost a placeholder would print the raw brace at a reader.
        for loc in LOCALES:
            table = i18n.load_catalogue(loc)
            for key in ('modules.results', 'modules.results_aria',
                        'modules.show_more'):
                with self.subTest(locale=loc, key=key):
                    self.assertEqual(set(re.findall(r'\{(\d+)\}', table[key])),
                                     set(re.findall(r'\{(\d+)\}', i18n.load_catalogue('en')[key])))


class TemplateTests(ModulesApiTestCase):
    """The markup carries what the script and the reader both need."""

    def setUp(self):
        super().setUp()
        self.html = self.client.get('/').get_data(as_text=True)

    def test_the_dialog_exists_with_the_expected_ids(self):
        for wanted in ('modules-dialog', 'btn-modules', 'modules-search-input',
                       'modules-results', 'modules-detail', 'modules-status',
                       'modules-close', 'modules-empty'):
            with self.subTest(id=wanted):
                self.assertIn(f'id="{wanted}"', self.html)

    def test_the_dialog_is_a_native_dialog_labelled_by_its_heading(self):
        self.assertIn('<dialog id="modules-dialog"', self.html)
        self.assertIn('aria-labelledby="modules-title"', self.html)
        self.assertIn('id="modules-title"', self.html)

    def test_the_search_box_has_a_visible_label_and_help(self):
        self.assertIn('<label for="modules-search-input"', self.html)
        self.assertIn('aria-describedby="modules-search-help"', self.html)
        self.assertIn('id="modules-search-help"', self.html)

    def test_the_result_count_is_a_polite_status_region(self):
        # Polite, not assertive: an assertive region would interrupt on
        # every keystroke, which makes a search box unusable.
        self.assertRegex(self.html, r'id="modules-status"[^>]*role="status"')
        self.assertRegex(self.html, r'id="modules-status"[^>]*aria-live="polite"')

    def test_the_level_buttons_report_their_pressed_state(self):
        for level in ('', 'start', 'everyday', 'advanced'):
            with self.subTest(level=level):
                self.assertRegex(
                    self.html,
                    rf'data-level="{re.escape(level)}"\s+aria-pressed="(true|false)"')

    def test_the_filter_buttons_are_grouped_and_labelled(self):
        self.assertIn('role="group"', self.html)
        self.assertIn('aria-labelledby="modules-filter-label"', self.html)

    def test_the_button_that_opens_it_declares_a_dialog(self):
        self.assertRegex(self.html, r'id="btn-modules"[^>]*aria-haspopup="dialog"')


if __name__ == '__main__':
    unittest.main()
