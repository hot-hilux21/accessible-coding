"""Tests for the settings API (POST /api/config).

The app is offline-first, so a setting that fails to save is a setting
the reader silently loses on the next restart. These tests cover the
new settings and the validation that keeps bad values out of the file.

Isolation: routes.py reads CONFIG_DIR and CONFIG_FILE as module-level
globals, so both are repointed at a fresh temporary directory for every
test. ACCESS_CODE is cleared because it is read once at import time and
a developer machine may have one set.

Run with:  PYTHONPATH=src python -m unittest discover -s tests -t .
"""

import html
import json
import pathlib
import re
import sys
import tempfile
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = str(REPO_ROOT / "src")
if SRC not in sys.path:
    sys.path.append(SRC)

from accessible_ide import create_app, i18n, routes  # noqa: E402


class ConfigApiTestCase(unittest.TestCase):
    """Base class giving each test a private config file."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        tmp_path = pathlib.Path(self._tmp.name)

        self._saved = {
            "CONFIG_DIR": routes.CONFIG_DIR,
            "CONFIG_FILE": routes.CONFIG_FILE,
            "ACCESS_CODE": routes.ACCESS_CODE,
        }
        routes.CONFIG_DIR = tmp_path
        routes.CONFIG_FILE = tmp_path / "config.json"
        routes.ACCESS_CODE = ""

        app = create_app()
        app.config["TESTING"] = True
        self.client = app.test_client()
        self.addCleanup(self._restore)

    def _restore(self):
        for key, value in self._saved.items():
            setattr(routes, key, value)
        self._tmp.cleanup()

    # -- helpers -------------------------------------------------------
    def post_settings(self, **payload):
        return self.client.post("/api/config", json=payload)

    def get_settings(self):
        response = self.client.get("/api/config")
        self.assertEqual(response.status_code, 200)
        return response.get_json()


class NewSettingsTests(ConfigApiTestCase):
    def test_defaults_contain_every_applied_setting(self):
        # line_height, letter_spacing and blur_intensity were stored and
        # rendered for a long time but never read by anything. The panel
        # now applies all of them, so they must all be present.
        for key in (
            "font",
            "font_size",
            "line_height",
            "letter_spacing",
            "blur_intensity",
            "theme",
            "focus_mode",
            "contrast",
            "tts_enabled",
            "tts_voice",
            "tts_rate",
            "locale",
        ):
            with self.subTest(key=key):
                self.assertIn(key, routes.DEFAULT_CONFIG)

    def test_contrast_round_trips(self):
        for value in sorted(routes.CONFIG_VALUES["contrast"]):
            with self.subTest(contrast=value):
                response = self.post_settings(contrast=value)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(self.get_settings()["contrast"], value)

    def test_tts_voice_round_trips_with_realistic_voice_name(self):
        # Voice names come from the OS and routinely contain spaces,
        # punctuation and parentheses.
        name = "Microsoft David Desktop - English (United States)"
        response = self.post_settings(tts_voice=name)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.get_settings()["tts_voice"], name)

    def test_tts_rate_round_trips(self):
        for value in (0.5, 0.9, 1.25, 2.0):
            with self.subTest(tts_rate=value):
                response = self.post_settings(tts_rate=value)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(self.get_settings()["tts_rate"], value)

    def test_reading_settings_round_trip(self):
        response = self.post_settings(
            line_height=2.0,
            letter_spacing=1.5,
            blur_intensity=0.75,
        )
        self.assertEqual(response.status_code, 200)
        stored = self.get_settings()
        self.assertEqual(stored["line_height"], 2.0)
        self.assertEqual(stored["letter_spacing"], 1.5)
        self.assertEqual(stored["blur_intensity"], 0.75)


class SetupWizardSettingsTests(ConfigApiTestCase):
    """The two values the setup screen stores.

    The wizard asks once, and both answers are all that is remembered: that
    it has been answered, and which question was being answered when the
    page was last drawn. The second one is the easy one to get wrong - a
    language change reloads the page, and a step that is not stored with it
    drops the reader back at question one, in a language they just picked,
    with no sign that anything has been lost.
    """

    def test_the_wizard_asks_unless_it_has_been_answered(self):
        # A brand new install has to be asked, and has to be asked in a
        # shape the page can act on.
        stored = self.get_settings()
        self.assertIs(stored["setup_complete"], False)
        self.assertEqual(stored["setup_step"], 1)
        page = self.client.get("/").get_data(as_text=True)
        self.assertIn('id="setup-dialog"', page)

    def test_answering_the_wizard_is_remembered(self):
        response = self.post_settings(setup_complete=True)
        self.assertEqual(response.status_code, 200)
        self.assertIs(self.get_settings()["setup_complete"], True)
        # And then it stays out of the way.
        page = self.client.get("/").get_data(as_text=True)
        self.assertNotIn('id="setup-dialog"', page)

    def test_asking_for_the_setup_screen_again_works(self):
        # A reader who skipped it, or who wants to change their mind, has to
        # be able to get it back without editing a file.
        self.post_settings(setup_complete=True, setup_step=3)
        response = self.post_settings(setup_complete=False, setup_step=1)
        self.assertEqual(response.status_code, 200)
        stored = self.get_settings()
        self.assertIs(stored["setup_complete"], False)
        self.assertEqual(stored["setup_step"], 1)
        self.assertIn('id="setup-dialog"', self.client.get("/").get_data(as_text=True))

    def test_every_step_round_trips(self):
        for step in range(1, routes.SETUP_TOTAL_STEPS + 1):
            with self.subTest(step=step):
                response = self.post_settings(setup_step=step)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(self.get_settings()["setup_step"], step)

    def test_a_step_outside_the_wizard_is_rejected(self):
        # Step 99 would ask the page to show a step that is not in it, and
        # the reader would be shown a blank question with no way to move.
        for step in (0, -1, routes.SETUP_TOTAL_STEPS + 1, 99):
            with self.subTest(step=step):
                response = self.post_settings(setup_step=step)
                self.assertEqual(response.status_code, 400)
        # The good answer is still there: a refused save must not take the
        # reader's place in the wizard with it.
        self.assertEqual(self.get_settings()["setup_step"], 1)

    def test_setup_complete_wants_a_yes_or_a_no(self):
        # Anything else - "true" as text, 1, null - would be stored as-is
        # and then read as "not finished", so the wizard would come back
        # after every restart with no explanation.
        for value in ("true", 1, None, "yes", []):
            with self.subTest(value=value):
                response = self.post_settings(setup_complete=value)
                self.assertEqual(response.status_code, 400)
        self.assertIs(self.get_settings()["setup_complete"], False)

    def test_setup_step_wants_a_whole_number(self):
        # "2" would compare as greater than 1 and behave like 1 in some
        # places and like 2 in others.
        for value in ("2", 1.5, True, None):
            with self.subTest(value=value):
                response = self.post_settings(setup_step=value)
                self.assertEqual(response.status_code, 400)

    def test_the_refusal_is_in_plain_english(self):
        response = self.post_settings(setup_step=99)
        self.assertEqual(response.status_code, 400)
        answer = response.get_json()
        self.assertFalse(answer["success"])
        # A sentence a reader can act on. The step is named by its visible
        # label, and no Python type or config key is shown to anyone.
        self.assertNotIn("ValueError", answer["error"])
        self.assertNotIn("setup_step", answer["error"])
        self.assertNotIn("Traceback", answer["error"])
        self.assertIn(
            i18n.make_translator("en")("config.error_prefix"), answer["error"]
        )

    def test_the_step_is_named_in_the_chosen_language(self):
        # The wizard is, by definition, on screen in the language being
        # chosen - so a refusal has to come back in that language too.
        spanish = self.client.post(
            "/api/config", json={"setup_step": 99, "locale": "es"}
        )
        self.assertEqual(spanish.status_code, 400)
        english = self.post_settings(setup_step=99, locale="en")
        self.assertEqual(english.status_code, 400)
        self.assertNotEqual(
            spanish.get_json()["error"],
            english.get_json()["error"],
            "the refusal came back in the wrong language",
        )

    def test_a_corrupt_step_in_the_file_does_not_break_the_page(self):
        # Someone editing config.json by hand should get the first question
        # rather than a server error, and a step they can answer.
        routes.CONFIG_FILE.write_text(
            '{"setup_complete": false, "setup_step": "second"}', encoding="utf-8"
        )
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        page = response.get_data(as_text=True)
        self.assertIn('id="setup-panel-language"', page)
        self.assertIn("Step 1 of", page)
        # The unreadable value is not carried on screen, and a fresh answer
        # is still accepted, so the wizard is not stuck.
        self.assertEqual(self.post_settings(setup_step=2).status_code, 200)
        self.assertEqual(self.get_settings()["setup_step"], 2)

    def test_a_step_past_the_end_is_pulled_back_into_range(self):
        # Same reasoning for a number that is too big rather than not a
        # number: the wizard would render a question that is not there.
        routes.CONFIG_FILE.write_text(
            '{"setup_complete": false, "setup_step": 99}', encoding="utf-8"
        )
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(
            f"Step {routes.SETUP_TOTAL_STEPS} of {routes.SETUP_TOTAL_STEPS}",
            response.get_data(as_text=True),
        )
        # Only the last real question is on show, not a blank one after it.
        page = response.get_data(as_text=True)
        for name, shown in (
            ("language", False),
            ("font", False),
            ("tour", True),
        ):
            with self.subTest(step=name):
                tag = re.search(
                    r'<section id="setup-panel-%s"(.*?)>' % name, page, re.S
                )
                self.assertIsNotNone(tag, "the panel is missing from the page")
                assert tag is not None
                self.assertEqual("hidden" not in tag.group(1), shown)

    def test_answering_the_wizard_asks_nothing(self):
        # Only the wizard posts these, and it posts them one at a time. A
        # rejection would mean a reader who answered a question is told
        # nothing, or told the wrong thing.
        response = self.post_settings(
            setup_complete=True, setup_step=routes.SETUP_TOTAL_STEPS
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()["success"])


class AccessCodeIsNotASettingTests(ConfigApiTestCase):
    """The browser always sends access_code, including when it is empty.

    It used to be validated as a setting and rejected, so every settings
    change failed with a 400 while appearing to work. It would also have
    been written into config.json in plain text.
    """

    def test_empty_access_code_does_not_block_saving(self):
        response = self.post_settings(font_size=20, access_code="")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.get_settings()["font_size"], 20)

    def test_access_code_is_never_written_to_the_config_file(self):
        routes.ACCESS_CODE = "letmein"
        response = self.post_settings(font_size=21, access_code="letmein")
        self.assertEqual(response.status_code, 200)

        self.assertIn("font_size", routes.CONFIG_FILE.read_text())
        raw = routes.CONFIG_FILE.read_text()
        self.assertNotIn("access_code", raw)
        self.assertNotIn("letmein", raw)

    def test_wrong_access_code_is_still_rejected(self):
        routes.ACCESS_CODE = "letmein"
        response = self.post_settings(font_size=21, access_code="wrong")
        self.assertEqual(response.status_code, 403)
        self.assertFalse(routes.CONFIG_FILE.exists())


class ConfigResetTests(ConfigApiTestCase):
    """POST /api/config/reset puts every setting back to the defaults."""

    def test_reset_returns_the_defaults(self):
        self.post_settings(font="Nunito", font_size=20, theme="dark")
        response = self.client.post("/api/config/reset", json={})
        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertTrue(body["success"])
        for key, value in routes.DEFAULT_CONFIG.items():
            with self.subTest(key=key):
                self.assertEqual(body["config"][key], value)

    def test_reset_writes_the_defaults_to_disk(self):
        self.post_settings(font="Nunito", font_size=20)
        response = self.client.post("/api/config/reset", json={})
        self.assertEqual(response.status_code, 200)
        stored = json.loads(routes.CONFIG_FILE.read_text(encoding="utf-8"))
        self.assertEqual(stored["font"], routes.DEFAULT_CONFIG["font"])
        self.assertEqual(stored["font_size"], routes.DEFAULT_CONFIG["font_size"])

    def test_reset_keeps_the_setup_screen_answered(self):
        # The first-run screen is onboarding, not a setting. Somebody who
        # has answered it does not want to be asked again just because they
        # reset their font and theme.
        self.post_settings(setup_complete=True)
        response = self.client.post("/api/config/reset", json={})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()["config"]["setup_complete"])

    def test_reset_requires_the_access_code_when_one_is_set(self):
        routes.ACCESS_CODE = "letmein"
        response = self.client.post("/api/config/reset", json={})
        self.assertEqual(response.status_code, 403)
        self.assertFalse(routes.CONFIG_FILE.exists())

    def test_reset_accepts_the_access_code(self):
        routes.ACCESS_CODE = "letmein"
        response = self.client.post(
            "/api/config/reset", json={"access_code": "letmein"}
        )
        self.assertEqual(response.status_code, 200)

    def test_reset_is_post_only(self):
        response = self.client.get("/api/config/reset")
        self.assertEqual(response.status_code, 405)


class ValidationTests(ConfigApiTestCase):
    def test_out_of_range_values_are_rejected(self):
        for key, (low, high) in routes.CONFIG_RANGES.items():
            for label, value in (("below", low - 1), ("above", high + 1)):
                with self.subTest(key=key, side=label):
                    # Seed a known good value first so we can prove the
                    # bad one did not overwrite it.
                    good = low if isinstance(low, int) else low
                    self.post_settings(**{key: good})
                    response = self.post_settings(**{key: value})
                    self.assertEqual(
                        response.status_code,
                        400,
                        f"{key}={value} should be rejected",
                    )
                    self.assertIn("error", response.get_json())
                    self.assertEqual(self.get_settings()[key], good)

    def test_unknown_setting_is_rejected_with_plain_english(self):
        response = self.post_settings(colour="purple")
        self.assertEqual(response.status_code, 400)
        error = response.get_json()["error"]
        self.assertIn("colour", error)
        # Plain English, not a Python exception or a key dump.
        self.assertNotIn("Traceback", error)

    def test_invalid_contrast_value_is_rejected(self):
        response = self.post_settings(contrast="extra")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.get_settings()["contrast"], "normal")

    def test_overlong_tts_voice_is_rejected(self):
        limit = routes.CONFIG_MAX_LENGTHS["tts_voice"]
        self.assertEqual(self.post_settings(tts_voice="a" * limit).status_code, 200)
        response = self.post_settings(tts_voice="a" * (limit + 1))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.get_settings()["tts_voice"], "a" * limit)

    def test_wrong_type_is_rejected(self):
        cases = [
            {"font_size": "large"},
            {"tts_enabled": "yes"},
            {"tts_rate": "fast"},
        ]
        for payload in cases:
            with self.subTest(payload=payload):
                self.assertEqual(self.post_settings(**payload).status_code, 400)

    def test_bool_is_not_accepted_where_a_number_is_wanted(self):
        # bool is a subclass of int in Python, so True would otherwise
        # sneak through a numeric check and render as font_size: 1.
        self.assertEqual(self.post_settings(font_size=True).status_code, 400)
        self.assertEqual(self.post_settings(tts_rate=True).status_code, 400)

    def test_a_bad_key_does_not_corrupt_the_good_ones(self):
        # Rejection happens before the save, so a payload mixing a good
        # and a bad setting must leave the previous file untouched.
        self.post_settings(font_size=18, contrast="high")
        response = self.post_settings(theme="dark", font_size=99)
        self.assertEqual(response.status_code, 400)

        stored = self.get_settings()
        self.assertEqual(stored["font_size"], 18)
        self.assertEqual(stored["contrast"], "high")
        self.assertEqual(stored["theme"], routes.DEFAULT_CONFIG["theme"])


class LocaleTests(ConfigApiTestCase):
    """The chosen interface language."""

    def test_every_shipped_language_round_trips(self):
        for code in ("en", "hi", "fr", "es", "ar"):
            with self.subTest(locale=code):
                self.assertEqual(self.post_settings(locale=code).status_code, 200)
                self.assertEqual(self.get_settings()["locale"], code)

    def test_a_language_the_app_does_not_ship_is_rejected(self):
        # Saving "de" would leave the reader with a language picker showing
        # German and an English interface, with no way back.
        response = self.post_settings(locale="de")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.get_settings()["locale"], "en")

    def test_a_non_string_language_is_rejected(self):
        for value in (5, True, ["fr"], None, ""):
            with self.subTest(value=value):
                self.assertEqual(self.post_settings(locale=value).status_code, 400)

    def test_the_rejection_names_the_setting_in_the_chosen_language(self):
        # A reader who has chosen Hindi should not be handed an English
        # sentence, and the sentence should quote the label they actually
        # clicked rather than the key stored in the file. The saved
        # language is the fallback, because the browser sends its own
        # locale and this request is deliberately not carrying one.
        from accessible_ide import i18n

        label_key = i18n.CONFIG_LABELS["contrast"]
        for code in ("en", "hi", "fr", "es", "ar"):
            with self.subTest(locale=code):
                self.assertEqual(self.post_settings(locale=code).status_code, 200)
                error = self.post_settings(contrast="extra").get_json()["error"]
                self.assertIn(i18n.load_catalogue(code)[label_key], error)
                # The label, not the key someone would grep for in the file.
                self.assertNotIn("'contrast'", error)
                self.assertNotIn('"contrast"', error)

    def test_a_sent_locale_beats_the_saved_one(self):
        # The picker saves and reloads, so this is belt and braces, but it
        # is what keeps an error in the language on screen if the save has
        # not landed yet.
        from accessible_ide import i18n

        self.assertEqual(self.post_settings(locale="es").status_code, 200)
        error = self.client.post(
            "/api/config", json={"locale": "ar", "contrast": "extra"}
        ).get_json()["error"]
        self.assertIn(
            i18n.load_catalogue("ar")[i18n.CONFIG_LABELS["contrast"]], error
        )

    def test_the_page_renders_in_the_saved_language(self):
        self.assertEqual(self.post_settings(locale="es").status_code, 200)
        page = self.client.get("/")
        try:
            body = page.data.decode("utf-8")
        finally:
            page.close()
        self.assertIn('<html lang="es">', body)
        self.assertIn("Ajustes", body)

    def test_a_corrupt_locale_in_the_file_falls_back_to_english(self):
        routes.CONFIG_FILE.write_text('{"locale": "klingon"}', encoding="utf-8")
        page = self.client.get("/")
        try:
            body = page.data.decode("utf-8")
        finally:
            page.close()
        self.assertIn('<html lang="en">', body)

    def test_every_theme_name_is_translated(self):
        # The theme picker is built from /api/themes, whose names are English.
        # app.js looks each one up as theme.<key>, so every theme the server
        # offers needs a catalogue entry in every language.
        from accessible_ide import i18n

        for code, theme in routes.THEMES.items():
            for locale in i18n.LANGUAGES:
                key = f"theme.{code}"
                with self.subTest(theme=code, locale=locale):
                    self.assertIn(key, i18n.load_catalogue(locale))


class CodeColorTests(ConfigApiTestCase):
    """The chosen code text colour."""

    def test_a_colour_round_trips(self):
        self.assertEqual(self.post_settings(code_color="#ffd93d").status_code, 200)
        self.assertEqual(self.get_settings()["code_color"], "#ffd93d")

    def test_empty_means_use_the_theme_colour(self):
        self.post_settings(code_color="#ffd93d")
        self.assertEqual(self.post_settings(code_color="").status_code, 200)
        self.assertEqual(self.get_settings()["code_color"], "")

    def test_short_hex_form_is_accepted(self):
        self.assertEqual(self.post_settings(code_color="#f0a").status_code, 200)
        self.assertEqual(self.get_settings()["code_color"], "#f0a")

    def test_capital_letters_are_accepted(self):
        self.assertEqual(self.post_settings(code_color="#FFD93D").status_code, 200)

    def test_anything_that_is_not_a_hex_colour_is_rejected(self):
        # This setting is written into a style attribute, so anything
        # carrying a second CSS declaration has to be refused outright.
        cases = [
            "red",              # a named colour, not a hex code
            "#ff",              # too short
            "#ffff",            # 4 digits: alpha, which hides text
            "#ffffffff",        # 8 digits: the same, with more opacity
            "#gggggg",          # not hex digits
            "ffd93d",           # missing the #
            "#ffd93d; background: url(evil)",   # style injection
            "rgb(255,0,0)",     # another format
            " ",                # whitespace is not a colour
        ]
        for value in cases:
            with self.subTest(code_color=value):
                response = self.post_settings(code_color=value)
                self.assertEqual(response.status_code, 400, f"{value!r} was accepted")
                self.assertEqual(self.get_settings()["code_color"], "")

    def test_a_non_string_colour_is_rejected(self):
        for value in [123, None, ["#ffffff"], {"hex": "#ffffff"}, True]:
            with self.subTest(code_color=value):
                self.assertEqual(self.post_settings(code_color=value).status_code, 400)

    def test_the_error_explains_itself_in_plain_english(self):
        response = self.post_settings(code_color="purple")
        message = response.get_json().get("error", "")
        self.assertIn("#", message)
        self.assertIn("colour", message.lower())
        # Jargon the reader would not know is exactly what this avoids.
        for jargon in ("hex", "regex", "null", "NaN", "invalid"):
            self.assertNotIn(jargon, message)


class ReduceMotionTests(ConfigApiTestCase):
    """The reduce-motion switch.

    Movement is the one setting with three states rather than two, because
    "not chosen yet" has to be distinguishable from "off": until the reader
    decides, the operating system preference decides for them.
    """

    def test_it_keeps_both_directions(self):
        # An OS-level reduced-motion setting must not be the only way to turn
        # movement off, and turning it off in the app must not be impossible
        # for a reader whose computer asks for reduction everywhere else.
        for value in (True, False):
            with self.subTest(reduce_motion=value):
                self.assertEqual(
                    self.post_settings(reduce_motion=value).status_code, 200
                )
                self.assertIs(self.get_settings()["reduce_motion"], value)

    def test_nothing_chosen_reports_unset_rather_than_off(self):
        # None is what the page reads to decide whether to defer to the
        # system, so it must survive as a real null, not collapse to False.
        self.assertIsNone(self.get_settings()["reduce_motion"])
        self.assertIsNone(routes.DEFAULT_CONFIG["reduce_motion"])

    def test_the_page_marks_the_body_before_any_script_runs(self):
        # app.js can adjust the switch, but the stylesheet has to be right
        # from the first paint or things move before the correction lands.
        page = self.client.get("/").data.decode("utf-8")
        self.assertIn('data-reduce-motion="unset"', page)

        self.post_settings(reduce_motion=True)
        page = self.client.get("/").data.decode("utf-8")
        self.assertIn('data-reduce-motion="true"', page)
        self.assertNotIn('data-reduce-motion="unset"', page)

        self.post_settings(reduce_motion=False)
        page = self.client.get("/").data.decode("utf-8")
        self.assertIn('data-reduce-motion="false"', page)

    def test_a_text_value_is_refused_with_a_message_about_the_switch(self):
        response = self.post_settings(reduce_motion="yes")
        self.assertEqual(response.status_code, 400)
        message = response.get_json()["error"]
        # The old wording would have said this is not a setting we
        # recognise, sending the reader hunting for a control that exists.
        self.assertIn("Reduce motion", message)
        self.assertIn("on or off", message)


class PanelMaterialSettingTests(ConfigApiTestCase):
    """The material and its colour are preferences, so they have to survive
    a save, refuse nonsense with a sentence about the control the reader
    actually used, and start solid - a see-through surface costs contrast,
    and contrast is not something this app trades for a look."""

    MATERIALS = ("off", "mica", "frosted", "acrylic")

    def test_it_is_solid_until_it_is_asked_for(self):
        self.assertEqual(routes.DEFAULT_CONFIG["glass_material"], "off")
        self.assertEqual(self.get_settings()["glass_material"], "off")
        self.assertEqual(routes.DEFAULT_CONFIG["glass_tint"], "")
        self.assertEqual(self.get_settings()["glass_tint"], "")

    def test_the_material_round_trips(self):
        for value in self.MATERIALS:
            with self.subTest(glass_material=value):
                self.assertEqual(
                    self.post_settings(glass_material=value).status_code, 200
                )
                self.assertEqual(self.get_settings()["glass_material"], value)

    def test_a_colour_round_trips_in_both_accepted_lengths(self):
        # The 3-digit form is accepted on the same rule as the code-colour
        # field: "#abc" and "#aabbcc" mean the same colour, and refusing the
        # short one would be a rule nobody could guess.
        for value in ("#223344", "#fff", "#223344"):
            with self.subTest(glass_tint=value):
                self.assertEqual(self.post_settings(glass_tint=value).status_code, 200)
                self.assertEqual(self.get_settings()["glass_tint"], value)

    def test_the_page_marks_the_body_before_any_script_runs(self):
        # Same reasoning as motion: the first paint has to be right, or the
        # page appears one way and then corrects itself in front of the reader.
        page = self.client.get("/").data.decode("utf-8")
        self.assertIn('data-glass-material="off"', page)

        self.post_settings(glass_material="acrylic", glass_tint="#336699")
        page = self.client.get("/").data.decode("utf-8")
        self.assertIn('data-glass-material="acrylic"', page)
        self.assertNotIn('data-glass-material="off"', page)

        # The stored colour is the reader's own, unchanged, so that it can be
        # shown back to them and re-clamped for a different theme.
        self.assertEqual(self.get_settings()["glass_tint"], "#336699")

        # What the page paints is that colour pulled toward the chosen theme's
        # panel until that theme's own text stays readable on it. It has to
        # reach CSS before the first paint too, or the panels would flash the
        # theme colour and change.
        from accessible_ide.utils import colour as tint_utils

        theme = routes.DEFAULT_CONFIG["theme"]
        expected = tint_utils.safe_panel_tint(
            "#336699",
            routes._panel_colour(theme),
            routes.PANEL_TEXT[theme],
        )
        self.assertNotEqual(expected, "#336699")
        self.assertIn(f'data-glass-tint="{expected}"', page)
        self.assertIn(f"--glass-tint: {expected};", page)
        # And it has to still be the same colour the browser works out, or the
        # panels would change the moment the first script runs.
        self.assertEqual(expected, routes.panel_tint_for(theme, "#336699"))

    def test_an_unknown_material_is_refused_by_name(self):
        response = self.post_settings(glass_material="obsidian")
        self.assertEqual(response.status_code, 400)
        message = response.get_json()["error"]
        # Naming the choice that exists beats saying the setting is unknown.
        self.assertIn("Panel material", message)
        for value in self.MATERIALS:
            self.assertIn(value, message)

    def test_a_colour_with_alpha_is_refused(self):
        # Alpha is how a colour silently becomes unreadable, and the panels
        # are already translucent. Letting a reader set both at once would
        # remove the floor that keeps the text legible.
        response = self.post_settings(glass_tint="#33669980")
        self.assertEqual(response.status_code, 400)
        message = response.get_json()["error"]
        self.assertIn("Panel colour", message)

    def test_the_old_on_off_switch_is_translated_rather_than_rejected(self):
        # Somebody who tried the earlier build has a stored key the validator
        # no longer knows. An unrecognised setting is an error worth showing,
        # so the old value is migrated instead of left to break.
        import json
        from pathlib import Path

        # Written from scratch rather than read, so the test does not depend
        # on whether an earlier test happened to save anything.
        routes.CONFIG_FILE.write_text(
            json.dumps(dict(routes.DEFAULT_CONFIG, glass=True)), encoding="utf-8"
        )
        migrated = routes.load_config()
        self.assertEqual(migrated["glass_material"], "frosted")
        self.assertNotIn("glass", migrated)

        routes.CONFIG_FILE.write_text(
            json.dumps(dict(routes.DEFAULT_CONFIG, glass=False)), encoding="utf-8"
        )
        self.assertEqual(routes.load_config()["glass_material"], "off")

    def test_the_switch_is_announced_as_a_switch(self):
        page = self.client.get("/").data.decode("utf-8")
        self.assertIn('id="reduce-motion"', page)
        self.assertRegex(page, r'id="reduce-motion"[^>]*role="switch"')
        self.assertIn('aria-describedby="motion-hint"', page)


class WrongTypeTests(ConfigApiTestCase):
    """A known setting sent the wrong sort of value."""

    def test_a_non_bool_for_a_switch_is_rejected(self):
        for value in ("yes", 1, 0, None, [], {}):
            with self.subTest(value=value):
                self.assertEqual(
                    self.post_settings(tts_enabled=value).status_code, 400,
                    f"tts_enabled={value!r} was accepted",
                )
                self.assertEqual(
                    self.post_settings(reduce_motion=value).status_code, 400,
                    f"reduce_motion={value!r} was accepted",
                )

    def test_the_message_names_the_setting_rather_than_dismissing_it(self):
        for key in ("tts_enabled", "reduce_motion"):
            with self.subTest(key=key):
                message = self.post_settings(**{key: "maybe"}).get_json()["error"]
                self.assertNotIn("not a setting we recognise", message)
                self.assertIn("on or off", message)


class HoverAndClickSpeechTests(ConfigApiTestCase):
    """What gets read out, and on what terms.

    The hover scope is the reader's answer to a question the app cannot
    decide for them: how much of a screen is worth hearing. It has to
    round-trip, it has to reject nonsense, and the delay has to stay
    within bounds because a long enough delay is a broken feature.
    """

    def test_the_hover_scope_round_trips(self):
        for value in ("off", "controls", "all"):
            with self.subTest(scope=value):
                self.assertEqual(
                    self.post_settings(tts_hover_scope=value).status_code, 200
                )
                self.assertEqual(self.get_settings()["tts_hover_scope"], value)

    def test_it_starts_on_the_middle_setting(self):
        # Reading only the things that do something is the useful default.
        # "all" would talk over a screen of code, and "off" would make the
        # feature look broken.
        self.assertEqual(self.get_settings()["tts_hover_scope"], "controls")

    def test_a_scope_that_does_not_exist_is_refused(self):
        for value in ("everything", "buttons", "", "ALL"):
            with self.subTest(scope=value):
                response = self.post_settings(tts_hover_scope=value)
                self.assertEqual(response.status_code, 400, f"{value!r} was accepted")
                self.assertEqual(self.get_settings()["tts_hover_scope"], "controls")

    def test_the_delay_round_trips_and_is_bounded(self):
        self.assertEqual(self.post_settings(tts_hover_delay=1500).status_code, 200)
        self.assertEqual(self.get_settings()["tts_hover_delay"], 1500)
        # Zero is legitimate: someone who rests the pointer on a control
        # should not have to wait at all.
        self.assertEqual(self.post_settings(tts_hover_delay=0).status_code, 200)
        self.assertEqual(self.get_settings()["tts_hover_delay"], 0)
        for value in (-1, 3001, 60000):
            with self.subTest(delay=value):
                self.assertEqual(
                    self.post_settings(tts_hover_delay=value).status_code, 400
                )

    def test_click_to_speak_is_a_switch_with_a_real_default(self):
        # On by default, because a click that says what was clicked is the
        # behaviour a screen reader would give anyway.
        self.assertIs(self.get_settings()["tts_click_to_speak"], True)
        self.assertEqual(
            self.post_settings(tts_click_to_speak=False).status_code, 200
        )
        self.assertIs(self.get_settings()["tts_click_to_speak"], False)

    def test_the_preferred_voice_round_trips(self):
        for value in ("male", "female", "any"):
            with self.subTest(gender=value):
                self.assertEqual(
                    self.post_settings(tts_voice_gender=value).status_code, 200
                )
                self.assertEqual(self.get_settings()["tts_voice_gender"], value)

    def test_a_male_voice_is_the_default(self):
        self.assertEqual(self.get_settings()["tts_voice_gender"], "male")

    def test_an_unknown_gender_is_refused(self):
        for value in ("neutral", "MALE", "robot", ""):
            with self.subTest(gender=value):
                response = self.post_settings(tts_voice_gender=value)
                self.assertEqual(response.status_code, 400, f"{value!r} was accepted")
                self.assertEqual(self.get_settings()["tts_voice_gender"], "male")

    def test_the_settings_reach_the_page_so_hover_works_before_settings_opens(self):
        # The whole point is that hovering starts working from the saved
        # answer, without the reader having to open the panel first.
        self.post_settings(
            tts_hover_scope="all", tts_hover_delay=1200, tts_voice_gender="female"
        )
        page = self.client.get("/").data.decode("utf-8")
        self.assertIn('data-tts-hover-scope="all"', page)
        self.assertIn('data-tts-hover-delay="1200"', page)
        self.assertIn('data-tts-voice-gender="female"', page)

    def test_the_delay_is_shown_in_a_unit_a_reader_can_picture(self):
        # 1200ms is a number nobody can feel; 1.2s is.
        self.post_settings(tts_hover_delay=1200)
        page = self.client.get("/").data.decode("utf-8")
        self.assertIn("1.2s", page)
        self.post_settings(tts_hover_delay=600)
        page = self.client.get("/").data.decode("utf-8")
        self.assertIn("600ms", page)

    def test_hover_and_click_controls_are_present_and_labelled(self):
        page = self.client.get("/").data.decode("utf-8")
        self.assertIn('id="tts-hover-scope"', page)
        self.assertIn('id="tts-hover-delay"', page)
        self.assertRegex(page, r'id="tts-click"[^>]*role="switch"')
        self.assertIn('aria-describedby="tts-hover-scope-help"', page)
        self.assertIn('aria-describedby="tts-click-help"', page)

    def test_every_control_is_reachable_and_fits_on_a_phone(self):
        # Four new controls in the reading group. The panel is the part of
        # the app most likely to be used on a small screen, and a control
        # that needs horizontal scrolling is a control nobody finds.
        page = self.client.get("/").data.decode("utf-8")
        for control in ("tts-hover-scope", "tts-hover-delay", "tts-click",
                        "tts-voice-gender"):
            with self.subTest(control=control):
                self.assertIn(f'id="{control}"', page)

    def test_the_hover_delay_slider_cannot_be_set_to_an_absurd_wait(self):
        # The markup and the server have to agree on the bounds, or the
        # slider will happily offer a value the server then refuses.
        page = self.client.get("/").data.decode("utf-8")
        self.assertIn('id="tts-hover-delay" min="0" max="3000" step="100"', page)
        low, high = routes.CONFIG_RANGES["tts_hover_delay"]
        self.assertEqual((low, high), (0, 3000))

    def test_the_controls_say_they_do_not_touch_the_code(self):
        # A reader who has been interrupted mid-edit by a voice talking over
        # their code needs to be told it will not happen again. The promise
        # has to survive translation, so this checks the rendered page in
        # every language rather than the English source.
        from accessible_ide import i18n

        seen = {}
        for code in i18n.LANGUAGES:
            with self.subTest(locale=code):
                self.post_settings(locale=code)
                page = self.client.get("/").data.decode("utf-8")
                expected = i18n.make_translator(code)("speak.click_help")
                # Jinja escapes an apostrophe as &#39; where Python's html
                # module writes &#x27;, so the two are reconciled here.
                escaped = html.escape(expected, quote=False).replace("'", "&#39;")
                self.assertTrue(
                    escaped in page,
                    f"the translated click help is missing from the {code} page",
                )
                seen[code] = expected
        # If every language rendered the same words, the check above would
        # pass for the wrong reason.
        self.assertGreater(len(set(seen.values())), 1, seen)


class ThemeApiTests(ConfigApiTestCase):
    def test_themes_endpoint_serves_the_editor_palettes(self):
        # app.js builds the CodeMirror theme from this response, so the
        # key set here is the contract with the front end.
        response = self.client.get("/api/themes")
        self.assertEqual(response.status_code, 200)
        themes = response.get_json()
        self.assertEqual(sorted(themes), sorted(routes.THEMES))
        for name, palette in themes.items():
            with self.subTest(theme=name):
                for key in ("name", "bg", "fg", "keyword", "string", "comment"):
                    self.assertIn(key, palette)


if __name__ == "__main__":
    unittest.main()
