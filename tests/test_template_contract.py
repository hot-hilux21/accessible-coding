"""Checks the contract between index.html and app.js.

The front end wires everything up with getElementById and then uses the
result immediately. A control that is renamed in only one of the two
files produces a null reference that stops the rest of the script from
running - which in a single-file app means the whole editor stops
responding, with nothing in the console a user could act on.

So: every id the script looks up has to exist in the rendered template,
and the settings panel has to be complete.

Run with:  PYTHONPATH=src python -m unittest discover -s tests -t .
"""

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
from accessible_ide.utils.colour import parse_hex  # noqa: E402

APP_JS = REPO_ROOT / "src" / "accessible_ide" / "static" / "js" / "app.js"
STYLESHEET = (
    REPO_ROOT / "src" / "accessible_ide" / "static" / "css" / "style.css"
)
INDEX_TEMPLATE = REPO_ROOT / "src" / "accessible_ide" / "templates" / "index.html"

# Controls the settings panel is expected to provide. Listed separately
# from the automatic scan so a missing control produces a clear message
# rather than only showing up as a generic scan failure.
REQUIRED_SETTINGS_IDS = (
    "settings-dialog",
    "settings-title",
    "settings-status",
    "btn-settings",
    "btn-settings-close",
    "font-select",
    "font-size",
    "font-size-label",
    "line-height",
    "line-height-label",
    "letter-spacing",
    "letter-spacing-label",
    "blur-intensity",
    "blur-intensity-label",
    "blur-field",
    "theme-select",
    "contrast-select",
    "focus-mode",
    "tts-toggle",
    "tts-state",
    "tts-voice",
    "tts-rate",
    "tts-rate-label",
    "btn-test-voice",
    # The "Try it out" panel.
    "font-bundled-note",
    "sample-text",
    "font-preview",
    "font-preview-text",
    "preview-status",
    "swatches",
    "code-color-hex",
    "code-color-picker",
"colour-error",
    "btn-reset-colour",
    "btn-reset-config",
)


def render_index():
    """The page as a reader sees it, in English with default settings.

    routes.py reads the config file as module-level globals, so without the
    swap below this renders whatever the developer last chose on their own
    machine. That made the suite order-dependent: a saved locale of "ar"
    turned the English assertions here into failures that had nothing to do
    with the code under test.
    """
    tmp = tempfile.TemporaryDirectory()
    saved = (routes.CONFIG_DIR, routes.CONFIG_FILE, routes.ACCESS_CODE)
    try:
        routes.CONFIG_DIR = pathlib.Path(tmp.name)
        routes.CONFIG_FILE = routes.CONFIG_DIR / "config.json"
        routes.ACCESS_CODE = ""

        app = create_app()
        app.config["TESTING"] = True
        client = app.test_client()
        response = client.get("/")
        assert response.status_code == 200, response.status_code
        return response.get_data(as_text=True)
    finally:
        routes.CONFIG_DIR, routes.CONFIG_FILE, routes.ACCESS_CODE = saved
        tmp.cleanup()


def render_with(saved):
    """The page as a reader sees it, with `saved` already in the config file.

    Used for the screens that depend on what was answered last time - the
    setup wizard, mainly. Without it those pages can only be tested in the
    state a brand new install is in.
    """
    tmp = tempfile.TemporaryDirectory()
    was = (routes.CONFIG_DIR, routes.CONFIG_FILE, routes.ACCESS_CODE)
    try:
        routes.CONFIG_DIR = pathlib.Path(tmp.name)
        routes.CONFIG_FILE = routes.CONFIG_DIR / "config.json"
        routes.CONFIG_FILE.write_text(json.dumps(saved), encoding="utf-8")
        routes.ACCESS_CODE = ""

        app = create_app()
        app.config["TESTING"] = True
        client = app.test_client()
        response = client.get("/")
        assert response.status_code == 200, response.status_code
        return response.get_data(as_text=True)
    finally:
        routes.CONFIG_DIR, routes.CONFIG_FILE, routes.ACCESS_CODE = was
        tmp.cleanup()


class RenderedPageFixture(unittest.TestCase):
    """Shared setup only. Holding no tests keeps subclasses from
    re-running this whole file's suite."""

    @classmethod
    def setUpClass(cls):
        cls.html = render_index()
        cls.js = APP_JS.read_text(encoding="utf-8")
        cls.css = STYLESHEET.read_text(encoding="utf-8")
        cls.template = INDEX_TEMPLATE.read_text(encoding="utf-8")
        cls.html_ids = set(re.findall(r'id="([^"]+)"', cls.html))


class TemplateContractTests(RenderedPageFixture):
    def test_every_element_the_script_looks_up_exists(self):
        wanted = set(
            re.findall(r"getElementById\(\s*'([^']+)'\s*\)", self.js)
        )
        self.assertTrue(wanted, "failed to scan app.js for getElementById calls")
        missing = sorted(wanted - self.html_ids)
        self.assertEqual(
            missing,
            [],
            "app.js looks these up but index.html has no matching element: "
            + ", ".join(missing),
        )

    def test_settings_panel_is_complete(self):
        missing = [
            element for element in REQUIRED_SETTINGS_IDS if element not in self.html_ids
        ]
        self.assertEqual(
            missing, [], "settings panel is missing: " + ", ".join(missing)
        )

    def test_settings_dialog_is_a_real_modal(self):
        # A native <dialog> gives focus trapping, Escape handling and an
        # inert background without hand-rolled JavaScript.
        self.assertIn('<dialog id="settings-dialog"', self.html)
        self.assertIn("showModal", self.js)
        self.assertIn("aria-labelledby=\"settings-title\"", self.html)

    def test_settings_panel_is_not_a_form(self):
        # A form method="dialog" closes the panel whenever it is
        # submitted, and pressing Enter while a select has focus submits
        # it - so choosing a setting would slam the panel shut.
        dialog = self.html.split('<dialog id="settings-dialog"', 1)[1]
        dialog = dialog.split("</dialog>", 1)[0]
        self.assertNotIn("<form", dialog)

    def test_every_button_in_the_panel_declares_its_type(self):
        # Without an explicit type a button inside a form is a submit
        # button, and a bare button defaults to submit as well.
        dialog = self.html.split('<dialog id="settings-dialog"', 1)[1]
        dialog = dialog.split("</dialog>", 1)[0]
        for button in re.findall(r"<button[^>]*>", dialog):
            match = re.search(r'id="([^"]+)"', button)
            name = match.group(1) if match else button
            with self.subTest(button=name):
                self.assertIn(
                    'type="',
                    button,
                    f"button #{name} has no explicit type attribute: " + button,
                )

    def test_settings_controls_are_labelled(self):
        # Every range and select needs a label or aria-label, otherwise a
        # screen reader announces only "slider" with no name.
        for control in re.findall(r"<input[^>]*type=\"range\"[^>]*>", self.html):
            match = re.search(r'id="([^"]+)"', control)
            self.assertIsNotNone(match, f"range input has no id: {control}")
            assert match is not None  # for the type checker, not the test
            element_id = match.group(1)
            with self.subTest(control=element_id):
                self.assertTrue(
                    f'<label for="{element_id}"' in self.html
                    or "aria-label=" in control,
                    f"range input #{element_id} has no label",
                )

        for control in re.findall(r"<select[^>]*>", self.html):
            match = re.search(r'id="([^"]+)"', control)
            self.assertIsNotNone(match, f"select has no id: {control}")
            assert match is not None  # for the type checker, not the test
            element_id = match.group(1)
            with self.subTest(control=element_id):
                self.assertTrue(
                    f'<label for="{element_id}"' in self.html
                    or "aria-label=" in control,
                    f"select #{element_id} has no label",
                )

    def test_tts_toggle_is_a_switch_with_state(self):
        # role="switch" plus aria-checked is what makes the on/off state
        # announceable; the old markup used aria-pressed on a button that
        # had no visible state.
        self.assertIn('id="tts-toggle"', self.html)
        self.assertIn('role="switch"', self.html)
        self.assertIn("aria-checked=", self.html)
        self.assertIn("aria-checked", self.js)

    def test_removed_topbar_controls_are_not_duplicated(self):
        # The settings that moved into the panel must not still be in the
        # top bar, or there would be two controls fighting over one
        # setting with no obvious source of truth.
        header = self.html.split("<footer", 1)[0]
        for control in ("font-select", "font-size", "theme-select", "focus-mode"):
            with self.subTest(control=control):
                self.assertNotIn(
                    f'id="{control}"',
                    header,
                    f"#{control} is still in the top bar as well as the panel",
                )

    def test_body_carries_the_saved_settings(self):
        # The first paint reads these attributes, so a setting that is
        # saved but not rendered here would only take effect after a
        # reload.
        body_match = re.search(r"<body[^>]*>", self.html)
        self.assertIsNotNone(body_match, "index.html has no <body> tag")
        assert body_match is not None  # for the type checker, not the test
        body_tag = body_match.group(0)
        for attribute in (
            "data-theme",
            "data-font",
            "data-font-size",
            "data-line-height",
            "data-letter-spacing",
            "data-focus-mode",
            "data-blur-intensity",
            "data-contrast",
            "data-tts-voice",
            "data-tts-rate",
        ):
            with self.subTest(attribute=attribute):
                self.assertIn(f"{attribute}=", body_tag)

    def test_theme_palette_is_not_duplicated_in_javascript(self):
        # The palettes live on the server and are fetched at runtime. A
        # second hardcoded copy in app.js is what let the code colours
        # drift away from the rest of the theme.
        self.assertNotIn("THEME_COLORS", self.js)
        self.assertIn("/api/themes", self.js)

    def test_saved_values_apply_without_a_reload(self):
        # The three settings that used to be stored but never read.
        for token in (
            "--line-height",
            "--letter-spacing",
            "--blur-amount",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.js)

    def test_slider_bounds_match_the_server_ranges(self):
        # If a range is widened on the server but not on the slider, the
        # new value can never be reached from the panel, and the server
        # rejection is never the thing a reader sees.
        for key, (low, high) in routes.CONFIG_RANGES.items():
            # Config keys use underscores; the control ids are hyphenated.
            control_id = key.replace("_", "-")
            with self.subTest(key=key):
                tag = re.search(
                    r'<(?:input|select)[^>]*id="' + control_id + r'"[^>]*>',
                    self.html,
                )
                self.assertIsNotNone(
                    tag, f"no range control for the {key} setting"
                )
                if tag is None:
                    continue
                markup = tag.group(0)
                slider_low = re.search(r'min="([-\d.]+)"', markup)
                slider_high = re.search(r'max="([-\d.]+)"', markup)
                self.assertIsNotNone(slider_low, f"{key} has no min")
                self.assertIsNotNone(slider_high, f"{key} has no max")
                if slider_low is None or slider_high is None:
                    continue
                self.assertEqual(
                    float(slider_low.group(1)),
                    float(low),
                    f"slider min for {key} disagrees with CONFIG_RANGES",
                )
                self.assertEqual(
                    float(slider_high.group(1)),
                    float(high),
                    f"slider max for {key} disagrees with CONFIG_RANGES",
                )

    def test_every_spacing_slider_has_a_button_either_side_of_it(self):
        # Dragging a slider thumb is hard with a shaky hand and near
        # impossible behind a screen magnifier. The buttons are a second way
        # in, so each spacing slider needs one that lowers it and one that
        # raises it, and they have to name the slider they drive.
        for key in ("line_height", "letter_spacing"):
            control = key.replace("_", "-")
            for direction, sign in (("less", "-"), ("more", "")):
                button_id = f"{control}-{direction}"
                with self.subTest(button=button_id):
                    tag = re.search(
                        r"<button[^>]*id=\"" + button_id + r"\"[^>]*>",
                        self.html,
                    )
                    self.assertIsNotNone(
                        tag, f"no {direction} button for {key}"
                    )
                    if tag is None:
                        continue
                    markup = tag.group(0)
                    # An explicit type. A button inside a form defaults to
                    # submit, and the settings panel is deliberately not a
                    # form, so this is a habit worth keeping.
                    self.assertIn('type="button"', markup)
                    target = re.search(r'data-target="([^"]+)"', markup)
                    self.assertIsNotNone(
                        target, f"{button_id} does not say which slider it drives"
                    )
                    if target is not None:
                        self.assertEqual(
                            target.group(1),
                            control,
                            f"{button_id} points at the wrong slider",
                        )
                    step = re.search(r'data-step="([-\d.]+)"', markup)
                    self.assertIsNotNone(
                        step, f"{button_id} does not say which way it moves"
                    )
                    if step is not None and sign:
                        self.assertTrue(
                            step.group(1).startswith("-"),
                            f"{button_id} should lower the value",
                        )
                    elif step is not None:
                        self.assertFalse(
                            step.group(1).startswith("-"),
                            f"{button_id} should raise the value",
                        )
                    # The step must be one notch of the slider it drives, or
                    # the buttons move by more than the slider does and the
                    # two disagree about where a value sits.
                    slider_step = re.search(
                        r'<input[^>]*id="' + control + r'"[^>]*step="([\d.]+)"',
                        self.html,
                    )
                    if step is not None and slider_step is not None:
                        self.assertEqual(
                            abs(float(step.group(1))),
                            float(slider_step.group(1)),
                            f"{button_id} moves by a different amount than its slider",
                        )

    def test_the_stepper_buttons_are_labelled_and_their_glyphs_are_not_read_aloud(self):
        # The visible glyph is either a minus or a plus. A screen reader
        # announcing "plus" on its own tells a reader nothing about which
        # setting it belongs to, so the name comes from aria-label and the
        # glyph is hidden from it.
        #
        # The key is read from the template and the text from the rendered
        # page, so this checks both halves: that the button asks for a string
        # that exists, and that the string it gets is real prose rather than
        # an empty attribute.
        template = (
            REPO_ROOT / "src" / "accessible_ide" / "templates" / "index.html"
        ).read_text(encoding="utf-8")
        english = i18n.load_catalogue("en")

        for button_id, key in (
            ("line-height-less", "reading.line_height_less"),
            ("line-height-more", "reading.line_height_more"),
            ("letter-spacing-less", "reading.letter_spacing_less"),
            ("letter-spacing-more", "reading.letter_spacing_more"),
        ):
            with self.subTest(button=button_id):
                source = re.search(
                    r"<button[^>]*id=\"" + button_id + r"\"[^>]*>",
                    template,
                    re.DOTALL,
                )
                self.assertIsNotNone(source)
                if source is not None:
                    self.assertIn(
                        f"t('{key}')",
                        source.group(0),
                        f"{button_id} should be named by {key}",
                    )
                self.assertIn(key, english, f"no English string for {key}")

                rendered = re.search(
                    r"<button[^>]*id=\"" + button_id + r"\"[^>]*>.*?</button>",
                    self.html,
                    re.DOTALL,
                )
                self.assertIsNotNone(rendered)
                if rendered is None:
                    continue
                markup = rendered.group(0)
                label = re.search(r'aria-label="([^"]*)"', markup)
                self.assertIsNotNone(
                    label, f"{button_id} has no name for a screen reader"
                )
                if label is not None:
                    self.assertEqual(
                        label.group(1),
                        english[key],
                        f"{button_id} is not named by {key} in English",
                    )
                self.assertIn(
                    'aria-hidden="true"',
                    markup,
                    f"{button_id} lets the bare glyph be read aloud",
                )

    def test_the_stepper_buttons_are_big_enough_to_hit(self):
        # WCAG 2.1 AA asks for a target of at least 24 by 24 CSS pixels,
        # and 44 is the figure this project works to everywhere else, so a
        # button smaller than that is a miss even though it passes the letter
        # of the standard.
        block = re.search(
            r"\.stepper-btn\s*\{([^}]*)\}", self.css, re.DOTALL
        )
        self.assertIsNotNone(block, "no .stepper-btn rule in the stylesheet")
        if block is None:
            return
        rules = block.group(1)
        for dimension in ("min-width", "min-height"):
            with self.subTest(dimension=dimension):
                declared = re.search(dimension + r":\s*(\d+)px", rules)
                self.assertIsNotNone(
                    declared, f".stepper-btn sets no {dimension}"
                )
                if declared is not None:
                    self.assertGreaterEqual(
                        int(declared.group(1)),
                        44,
                        f".stepper-btn {dimension} is under 44px",
                    )

    def test_error_status_is_announced(self):
        # saveConfig reports failures now that the server can reject a
        # setting, and a silent failure is how broken settings survived so
        # long in the first place.
        self.assertIn("aria-live", self.html)
        self.assertIn("reportSaveError", self.js)
        self.assertIn("res.ok", self.js)


class UpdatePanelTests(RenderedPageFixture):
    """The Updates section of the settings panel."""

    def group_template(self):
        """The group as written, before the {{ t(...) }} calls are resolved.

        Assertions about which catalogue keys a word asks for have to look
        here. The rendered page is English by definition, so asking it
        whether a key was used would pass for the wrong reason.
        """
        return self._slice(INDEX_TEMPLATE.read_text(encoding="utf-8"))

    def group_markup(self):
        """The group as a reader sees it, in English with default settings."""
        return self._slice(self.html)

    @staticmethod
    def _slice(text):
        start = text.find('id="auto-update-toggle"')
        if start == -1:
            return ""
        open_tag = text.rfind("<fieldset", 0, start)
        close_tag = text.find("</fieldset>", start)
        return text[open_tag:close_tag] if close_tag != -1 else ""

    def update_js(self):
        """The Updates section of app.js, on its own.

        Bounded by the Quit button's own section, which legitimately closes
        the window. Without that bound the assertion below would be testing
        the Quit button and passing for the wrong reason.
        """
        start = self.js.find("// ---------- Updates ----------")
        end = self.js.find("// ---------- Quit")
        if start == -1 or end == -1 or end < start:
            return ""
        return self.js[start:end]

    def test_the_group_is_present(self):
        self.assertNotEqual(
            self.group_markup(), "", "no auto-update switch in the settings panel")

    def test_the_group_is_in_the_settings_dialog(self):
        dialog = re.search(
            r'<dialog id="settings-dialog".*?</dialog>', self.html, re.DOTALL
        )
        self.assertIsNotNone(dialog, "no settings dialog")
        if dialog is not None:
            inside = dialog.group(0)
            self.assertIn('id="auto-update-toggle"', inside)
            self.assertIn('id="btn-check-update"', inside)

    def test_the_switch_is_labelled_and_described(self):
        markup = self.group_markup()
        self.assertIn('id="auto-update-toggle"', markup)
        # A role=switch with no accessible name is a control a screen reader
        # announces as just "switch".
        self.assertRegex(markup, r'<label for="auto-update-toggle">')
        self.assertIn('aria-describedby="auto-update-help"', markup)
        self.assertIn('id="auto-update-help"', markup)
        self.assertIn('role="switch"', markup)
        self.assertIn("aria-checked=", markup)

    def test_the_switch_state_is_shown_in_words_not_only_drawn(self):
        # The track and thumb are aria-hidden, so a reader who cannot see the
        # switch has only the words beside it. Both states have to be
        # spelled out, or the switch is silent when it is off.
        markup = self.group_template()
        self.assertIn('id="auto-update-state"', markup)
        self.assertIn("speak.on", markup)
        self.assertIn("speak.off", markup)

    def test_the_check_button_is_labelled_and_described(self):
        markup = self.group_markup()
        self.assertIn('id="btn-check-update"', markup)
        # A button carrying only an icon would be unnamed. This one has words.
        self.assertIn("Check now", markup)
        self.assertIn('aria-describedby="update-check-label"', markup)
        self.assertIn('id="update-check-label"', markup)

    def test_the_answer_to_a_check_is_announced(self):
        # The reader has to be told the outcome without hunting for it, and
        # without focus being dragged away from what they were doing.
        markup = self.group_markup()
        self.assertIn('id="update-status"', markup)
        self.assertIn('aria-live="polite"', markup)
        self.assertIn('role="status"', markup)

    def test_the_download_button_is_offered_only_when_there_is_something_to_download(self):
        markup = self.group_markup()
        self.assertIn('id="update-install-row"', markup)
        # Hidden in the page, because an empty download button that quietly
        # does nothing is worse than no button at all.
        self.assertIn('id="update-install-row" hidden', markup)
        self.assertIn("showInstallRow(false)", self.js)

    def test_the_download_button_is_labelled_and_described(self):
        markup = self.group_markup()
        self.assertIn('id="btn-install-update"', markup)
        self.assertIn("Download the new version", markup)
        self.assertIn('aria-describedby="update-install-label"', markup)
        self.assertIn('id="update-install-label"', markup)

    def test_the_download_says_what_happens_to_the_work_in_hand(self):
        # The reader has to be able to decide without guessing: closing is
        # what installs it, and nothing is closed for them.
        markup = self.group_markup()
        self.assertIn('id="update-install-help"', markup)
        self.assertIn("when you close the app", markup)
        self.assertNotIn("window.close()", self.update_js())

    def test_the_running_version_is_shown(self):
        # The element is empty in the page because the version is not known
        # until the server answers; app.js fills it. So the test is split:
        # the place to put it, and the key used to word it.
        self.assertIn('id="update-version"', self.group_template())
        self.assertIn("update-version", self.js)
        self.assertIn("update.version_line", self.js)
        # /api/version, so the page is not guessing the number.
        self.assertIn("/api/version", self.js)

    def test_nothing_in_the_group_is_bare_english(self):
        # Checked against the template rather than the rendered page, because
        # the rendered page is English by definition and would fail for the
        # wrong reason. What matters is that every visible word is asked for
        # by name, so it can be given a translation.
        markup = self.group_template()
        self.assertNotEqual(markup, "", "no Updates group in the template")
        for text in re.findall(r">([^<>{}]+)<", markup):
            cleaned = text.strip()
            if not cleaned:
                continue
            with self.subTest(text=cleaned):
                self.fail(f"literal text in the Updates group: {cleaned!r}")

    def test_the_switch_and_the_button_are_told_apart_in_the_code(self):
        # They do different things. Collapsing them into one control would
        # make "off" mean "no updates ever" instead of "not by itself".
        self.assertIn("checkForUpdates", self.js)
        self.assertIn("force: !!manual", self.js)


class TryItOutPanelTests(RenderedPageFixture):
    """The font-and-colour test panel."""

    def test_the_panel_sits_inside_the_settings_dialog(self):
        # Outside the dialog it would be unreachable: the dialog is modal
        # and the rest of the page is inert while it is open.
        dialog = self.html.split('<dialog id="settings-dialog"', 1)[1]
        dialog = dialog.split("</dialog>", 1)[0]
        for element_id in ("swatches", "code-color-hex", "font-preview",
                           "btn-reset-colour", "sample-text"):
            with self.subTest(element=element_id):
                self.assertIn(f'id="{element_id}"', dialog)

    def test_font_options_carry_their_own_css_stack(self):
        # app.js reads data-family instead of keeping a second copy of the
        # font stacks. Without it, a font can be listed but not applied -
        # which is how OpenDyslexic shipped broken.
        options = re.findall(r"<option value=\"[^\"]+\"[^>]*>", self.html)
        font_options = [o for o in options if "data-family" in o]
        self.assertEqual(len(font_options), len(routes.FONTS))
        for option in font_options:
            with self.subTest(option=option[:60]):
                self.assertRegex(option, r'data-family="[^"]+"')
                self.assertRegex(option, r'data-bundled="(true|false)"')

    def test_the_swatches_are_a_labelled_radio_group(self):
        # Real radios, so arrow keys, Tab and a screen reader all work
        # without any extra scripting.
        self.assertIn('role="radiogroup"', self.html)
        self.assertIn('aria-labelledby="swatch-label"', self.html)
        self.assertIn('id="swatch-label"', self.html)

        radios = re.findall(r'<input type="radio" name="colour-swatch"[^>]*>', self.html)
        self.assertGreaterEqual(len(radios), 8)
        for radio in radios:
            self.assertRegex(radio, r'value="#[0-9a-fA-F]{6}"')
            # The chip carries the colour; the text below it names it, so
            # the swatch is not identified by colour alone.
            self.assertIn("swatch-chip", self.html)
            self.assertIn("swatch-name", self.html)

    def test_the_colour_field_explains_itself_and_reports_problems(self):
        self.assertIn('for="code-color-hex"', self.html)
        self.assertIn('aria-describedby="colour-help colour-error"', self.html)
        # role="alert" is what makes a screen reader say the problem out
        # loud rather than leaving it sitting there visually.
        self.assertRegex(self.html, r'id="colour-error"[^>]*role="alert"')
        # The error starts hidden; app.js reveals it.
        self.assertRegex(self.html, r'id="colour-error"[^>]*hidden')

    def test_the_preview_is_described_for_a_screen_reader(self):
        self.assertIn('aria-labelledby="preview-label"', self.html)
        self.assertIn('id="preview-label"', self.html)
        self.assertIn('id="preview-status"', self.html)
        # The default sample is the pangram, which exercises every letter.
        self.assertIn("The quick brown fox jumps over the lazy dog", self.html)

    def test_the_colour_picker_is_labelled(self):
        # A bare colour input is announced as just "colour" by most
        # screen readers, which is not enough to tell it apart from the
        # hex field beside it.
        self.assertRegex(
            self.html, r'<input type="color"[^>]*aria-label="[^"]+"')

    def test_the_colour_is_remembered_across_reloads(self):
        # The saved colour has to reach the page on load, or a reader who
        # picks a colour and closes the app loses it. Checked on the
        # rendered page, where Jinja has already substituted the value.
        body = re.search(r"<body[^>]*>", self.html)
        self.assertIsNotNone(body)
        assert body is not None  # narrow the type for checkers
        self.assertIn("data-code-color=", body.group(0))
        self.assertIn("code_color", routes.DEFAULT_CONFIG)
        self.assertIn("code_color", routes.CONFIG_TYPES)

    def test_app_js_restores_the_saved_colour_and_font(self):
        # Both have to be read back from the page on init, or the first
        # paint would show the theme colour and the wrong font for a frame.
        self.assertIn("data-code-color", self.js)
        self.assertIn("customCodeColor = body.getAttribute('data-code-color')", self.js)
        self.assertIn("data-family", self.js)


class SetupWizardTests(RenderedPageFixture):
    """The screen shown once, to a reader who has just installed the app.

    These are contracts the markup has to keep, not tests of the wording.
    Most of them exist because the failure is silent: a wizard that never
    opens, a step that does not announce itself, or a progress line written
    as "1/3" all look fine on screen and are unusable with a screen reader.
    """

    # The setup screen is the one piece of the app that is not in the
    # settings list, because it is a dialog in its own right.
    REQUIRED_SETUP_IDS = (
        "setup-dialog",
        "setup-title",
        "setup-progress",
        "setup-status",
        "setup-panel-language",
        "setup-panel-font",
        "setup-panel-tour",
        "setup-skip",
        "setup-back",
        "setup-next",
    )

    def dialog_markup(self):
        """The wizard as the template writes it, translations unexpanded.

        Read from the template rather than the rendered page, so that the
        "no bare English" check is not arguing with a page that is English
        on purpose, and so that the checks about which key a piece of
        wording is asked for by can see the key at all.
        """
        body = self.template.split("{% if setup_open %}", 1)[1]
        return body.split("{% endif %}", 1)[0]

    def wizard_css(self):
        """The stylesheet from the wizard's banner to the end of the file."""
        self.assertIn(
            "First-run setup", self.css, "the setup wizard has no block in the stylesheet"
        )
        return self.css.split("First-run setup", 1)[1]

    def test_the_wizard_is_offered_once_and_then_left_alone(self):
        # Default settings mean the reader has never answered it, so it has
        # to be in the page.
        self.assertIn('id="setup-dialog"', self.html)
        # Once answered, it has to stay out of the page entirely. Markup
        # that is merely hidden would still be tabbable and still be read
        # aloud, which is worse than not drawing it.
        answered = render_with({"setup_complete": True})
        self.assertNotIn('id="setup-dialog"', answered)
        self.assertNotIn("setup-panel-", answered)

    def test_the_wizard_is_a_real_modal(self):
        # A native <dialog> opened with showModal traps focus, makes the
        # page behind it inert, and cannot be half-open.
        self.assertIn('<dialog id="setup-dialog"', self.html)
        self.assertIn('aria-labelledby="setup-title"', self.html)
        self.assertIn("showModal", self.js)

    def test_everything_the_wizard_needs_is_present(self):
        missing = [i for i in self.REQUIRED_SETUP_IDS if f'id="{i}"' not in self.html]
        self.assertEqual(
            missing, [], "the setup screen is missing: " + ", ".join(missing)
        )

    def test_there_is_a_step_for_each_thing_the_reader_is_asked(self):
        # Three questions, three panels, and the panels are named after the
        # steps rather than numbered in the markup, so inserting a step
        # cannot leave two panels claiming to be number two.
        panels = re.findall(r'id="setup-panel-([a-z]+)"', self.html)
        self.assertEqual(panels, list(routes.SETUP_STEPS))
        self.assertEqual(len(panels), routes.SETUP_TOTAL_STEPS)

    def test_the_step_count_is_computed_not_written_out(self):
        # "Step 1 of 3" typed into the template is wrong the moment a step
        # is added. The count has to come from the same list that names the
        # steps, and has to be spoken rather than drawn as a fraction.
        self.assertIn("t('setup.step_of', setup_step, setup_total)", self.template)
        # app.js counts the panels it actually found rather than keeping its
        # own list, so a step added to the template cannot leave the buttons
        # offering to go on past the end.
        self.assertIn("setupPanels", self.js)
        self.assertIn("panels.length", self.js)
        progress = re.search(
            r'id="setup-progress"[^>]*>(.*?)</p>', self.html, re.S
        )
        self.assertIsNotNone(progress)
        assert progress is not None  # narrow the type for checkers
        self.assertIn("3", progress.group(1))
        self.assertNotIn("/", progress.group(1))
        self.assertRegex(self.html, r'id="setup-progress"[^>]*role="status"')

    def test_only_the_step_being_answered_is_shown(self):
        # Asked on the second step, a reader must not be shown the first
        # question above it, answered or not.
        resumed = render_with({"setup_step": 2})
        shown = [
            (name, "hidden" not in tag)
            for name, tag in re.findall(
                r'<section id="(setup-panel-[a-z]+)"(.*?)>', resumed, re.S
            )
        ]
        self.assertEqual(
            shown,
            [("setup-panel-language", False), ("setup-panel-font", True),
             ("setup-panel-tour", False)],
            "resuming on step 2 should show the font question and hide the rest",
        )
        self.assertIn("Step 2 of 3", resumed)
        # Back is hidden on the first step, because there is nowhere before
        # it to go, and offered from the second onwards.
        self.assertRegex(self.html, r'id="setup-back"[^>]*hidden')
        self.assertNotRegex(resumed, r'id="setup-back"[^>]*hidden')
        finished = render_with({"setup_step": routes.SETUP_TOTAL_STEPS})
        self.assertNotRegex(finished, r'id="setup-back"[^>]*hidden')
        self.assertIn(i18n.make_translator("en")("setup.start"), finished)

    def test_each_step_has_a_heading_that_can_take_focus(self):
        # Focus is moved to the question when the step changes. A heading
        # that is not focusable is the one place the browser will not do
        # this for us, and without it a screen reader announces "Next
        # button" again and the reader never learns the page changed.
        for step in routes.SETUP_STEPS:
            with self.subTest(step=step):
                self.assertIn(
                    f'id="setup-panel-{step}"', self.html
                )
        headings = re.findall(r'class="settings-legend setup-legend"[^>]*>', self.html)
        headings += re.findall(r'class="settings-legend setup-legend" tabindex="-1"', self.html)
        self.assertTrue(headings, "the steps have no focusable headings")
        for heading in headings:
            self.assertIn('tabindex="-1"', heading)
        self.assertIn("focus()", self.js)

    def test_the_language_choices_are_named_in_their_own_language(self):
        # A reader who cannot read the current language still has to be
        # able to find their own. The endonym is what the radio is named
        # by, and the English name is only there as a second line.
        radios = re.findall(r'<input type="radio" name="setup-locale"[^>]*>', self.html)
        self.assertEqual(len(radios), len(i18n.LANGUAGES))
        for radio in radios:
            with self.subTest(radio=radio):
                self.assertRegex(radio, r'value="[a-z]{2}"')
        endonyms = re.findall(r'class="setup-choice-name" lang="([a-z]{2})"', self.html)
        self.assertEqual(sorted(endonyms), sorted(i18n.LANGUAGES))
        # The choice already saved is the one that comes up ticked.
        self.assertRegex(self.html, r'name="setup-locale"[^>]*checked')

    def test_the_choices_are_real_radios_in_labelled_groups(self):
        # Arrow keys, Tab and the checked announcement all come from the
        # browser this way. A div with role="radiogroup" needs all three
        # reimplemented before it is as usable.
        self.assertIn('name="setup-locale"', self.html)
        self.assertIn('name="setup-font"', self.html)
        self.assertEqual(
            self.html.count("<fieldset"), self.html.count("</fieldset>"),
            "unbalanced fieldsets in the setup screen",
        )
        # Each group is named by a legend, so the question is read out with
        # the first option rather than the reader having to guess.
        for legend in ("setup.language_legend", "setup.font_legend"):
            with self.subTest(legend=legend):
                self.assertIn(f"t('{legend}')", self.template)

    def test_every_font_is_shown_in_its_own_font_before_it_is_chosen(self):
        # This is the whole point of the step. A list of names, all set in
        # the same typeface, asks the reader to trust a label.
        radios = re.findall(r'<input type="radio" name="setup-font"[^>]*>', self.html)
        self.assertEqual(len(radios), len(routes.FONTS))
        samples = re.findall(
            r'class="setup-sample"\s+style="font-family: ([^"]+)"', self.html
        )
        self.assertEqual(len(samples), len(routes.FONTS))
        for family, radio in zip(samples, radios):
            with self.subTest(font=family):
                self.assertIn(f'data-family="{family}"', radio)
        # And the choice carries the stack, so app.js does not keep a
        # second copy that can drift from this list.
        self.assertIn("data-family", self.js)

    def test_there_is_a_way_out_that_does_not_depend_on_escape(self):
        # Escape is blocked on purpose, because the screen exists to be
        # answered - so there has to be a visible way out instead. A reader
        # who cannot find the keyboard button must not be trapped.
        self.assertIn('id="setup-skip"', self.html)
        self.assertIn('type="button"', self.html.split('id="setup-skip"', 1)[1][:120])
        self.assertIn("setup-skip", self.js)
        self.assertIn("cancel", self.js)
        self.assertIn("preventDefault", self.js.split("cancel", 1)[1][:200])

    def test_a_problem_is_announced_rather_than_only_shown(self):
        # role="alert" makes a screen reader say a refused save out loud.
        # Left as plain text it would sit there, which for a screen reader
        # is the same as not having happened.
        self.assertRegex(self.html, r'id="setup-status"[^>]*role="alert"')
        self.assertRegex(self.html, r'id="setup-status"[^>]*hidden')
        self.assertIn("setup.error_saved", self.js)

    def test_the_wizard_can_be_run_again_from_settings(self):
        # A reader who skipped it, or who wants to change their mind, has
        # to be able to come back to it without a settings file edit.
        self.assertIn('id="btn-setup-again"', self.html)
        self.assertIn("settings.setup_again", self.html)
        self.assertIn("btn-setup-again", self.js)
        self.assertIn("setup_complete: false", self.js)

    def test_the_tour_points_at_buttons_by_their_translated_names(self):
        # The names are interpolated rather than typed in, so a line
        # cannot quietly point at a button that has been renamed.
        for key in ("setup.tour_run_text", "setup.tour_speak_text",
                    "setup.tour_settings_text"):
            with self.subTest(key=key):
                self.assertIn(f"t('{key}', t(", self.template)
        # And the four things it describes are the four the app has.
        self.assertEqual(self.html.count("setup-tour-name"), 4)

    def test_nothing_in_the_wizard_is_bare_english(self):
        # Every visible word is asked for by name so it can be given a
        # translation. The rendered page is English by definition, so this
        # is checked against the template.
        markup = self.dialog_markup()
        self.assertNotEqual(markup, "", "no setup screen in the template")
        for text in re.findall(r">([^<>{}]+)<", markup):
            cleaned = text.strip()
            if not cleaned:
                continue
            with self.subTest(text=cleaned):
                self.fail(f"literal text in the setup screen: {cleaned!r}")

    def test_the_setup_keys_exist_in_every_language(self):
        # The screen is asked for by key, so a key missing from one
        # catalogue shows the reader that language in English and nothing
        # else. The default English catalogue is the list of what exists.
        wanted = [
            key for key in i18n.load_catalogue("en") if key.startswith("setup.")
        ]
        self.assertGreaterEqual(len(wanted), 20)
        for code in i18n.LANGUAGES:
            with self.subTest(language=code):
                absent = [k for k in wanted if k not in i18n.load_catalogue(code)]
                self.assertEqual(
                    absent, [], f"{code} is missing setup wording"
                )

    def test_the_targets_are_big_enough_to_hit(self):
        # 44px is the smallest comfortable target. On the setup screen the
        # reader is often reaching for it without looking, because the
        # wizard covers the app they came to use - and the buttons that
        # carry them between questions are the ones most likely to be hit
        # by feel, at the bottom of the screen, in a hurry.
        #
        # The wizard used to carry its own ".setup-footer .btn { min-height:
        # 44px }" because .btn was 40px and the wizard had to push it back
        # up. .btn is 44px everywhere now, so the question is no longer
        # "does the wizard override it" but "does anything shrink a button".
        # A 44px answer row and a 32px button in the same dialog is still a
        # 32px button, which is what this test is really about.
        rules = self.wizard_css()

        base = re.search(r"\.btn\s*\{([^}]*)\}", self.css)
        self.assertIsNotNone(base, ".btn has no rule of its own")
        assert base is not None  # narrow the type for checkers
        self.assertIn(
            "min-height: 44px",
            base.group(1),
            "the shared .btn rule is the only thing keeping wizard buttons "
            "at 44px now, so it has to say so",
        )

        # Checked where it matters: on the rule itself, not merely somewhere
        # in the block.
        rule = re.search(re.escape(".setup-choice") + r"\s*\{([^}]*)\}", rules)
        self.assertIsNotNone(rule, ".setup-choice has no rule of its own")
        assert rule is not None
        self.assertIn("min-height: 44px", rule.group(1))

        # And nothing anywhere in the wizard may pull a button back under it.
        for selector, body in re.findall(
            r"(\.setup-footer[^{]*\.btn[^{]*)\{([^}]*)\}", rules
        ):
            with self.subTest(rule=selector.strip()):
                for height in re.findall(r"min-height:\s*([\d.]+)px", body):
                    self.assertGreaterEqual(
                        float(height),
                        44.0,
                        f"{selector.strip()} makes a wizard button "
                        f"{height}px tall, under the 44px floor",
                    )

    def test_the_wizard_does_not_move_by_itself(self):
        # Nothing in a three-question screen needs to animate. A reader
        # with a visual processing difference is asked to read and click
        # at the same time, and movement makes that harder rather than
        # easier. The buttons do inherit a hover transition from .btn, so
        # this is about the wizard's own rules adding none.
        rules = self.wizard_css()
        self.assertNotIn("animation", rules)
        self.assertNotIn("transition", rules)

    def test_hidden_panels_cannot_be_revealed_by_the_page_css(self):
        # The panels are shown and hidden by attribute from app.js. The
        # stylesheet has to honour that attribute, or a hidden step stays
        # on screen and the reader answers the wrong question.
        self.assertIn("[hidden]", self.css)
        self.assertRegex(self.css, r"\[hidden\]\s*\{[^}]*display:\s*none\s*!important")


class StaticAssetsTests(unittest.TestCase):
    def test_stylesheet_and_script_are_served(self):
        app = create_app()
        app.config["TESTING"] = True
        client = app.test_client()
        for path in ("/static/css/style.css", "/static/js/app.js"):
            with self.subTest(path=path):
                response = client.get(path)
                try:
                    self.assertEqual(response.status_code, 200)
                finally:
                    response.close()

    def test_stylesheet_defines_the_settings_panel(self):
        css = (
            REPO_ROOT / "src" / "accessible_ide" / "static" / "css" / "style.css"
        ).read_text(encoding="utf-8")
        self.assertEqual(css.count("{"), css.count("}"), "unbalanced CSS braces")
        for selector in (".settings", ".settings-group", ".switch-track"):
            with self.subTest(selector=selector):
                self.assertIn(selector, css)
        self.assertIn('body[data-contrast="high"]', css)


class ReducedMotionCssTests(unittest.TestCase):
    """The stylesheet has to answer the switch in Settings.

    If either rule below goes missing, the switch still looks right and the
    app still moves, which is the worst kind of broken: nothing looks wrong
    and nothing reports an error.
    """

    def setUp(self):
        self.css = (
            REPO_ROOT / "src" / "accessible_ide" / "static" / "css" / "style.css"
        ).read_text(encoding="utf-8")

    def test_the_body_attribute_stops_movement(self):
        self.assertIn("body[data-reduce-motion='true']", self.css)
        block = self.css.split("body[data-reduce-motion='true']", 1)[1]
        block = block[: block.index("}")]
        self.assertIn("transition: none", block)
        self.assertIn("animation: none", block)

    def test_the_operating_system_preference_is_still_honoured(self):
        # This one works with no JavaScript at all, so nothing moves before
        # the first paint. The "unset" qualifier is deliberate: once the
        # reader has answered in Settings, their answer outranks the system.
        self.assertIn("@media (prefers-reduced-motion: reduce)", self.css)
        block = self.css.split("@media (prefers-reduced-motion: reduce)", 1)[1]
        block = block[: block.index("}")]
        self.assertIn("transition: none", block)
        self.assertIn("body[data-reduce-motion='unset']", block)
        self.assertNotIn(
            "body[data-reduce-motion='unset']",
            self.css.split("@media (prefers-reduced-motion: reduce)", 1)[0],
            "the media query qualifier is not scoped to the media query",
        )

    def test_pseudo_elements_are_covered_too(self):
        # ::before and ::after are where a decorative rule usually hides,
        # and they animate even when their element does not.
        self.assertIn("body[data-reduce-motion='true'] *::before", self.css)
        self.assertIn("body[data-reduce-motion='true'] *::after", self.css)


class FrostedPanelAndMovementCssTests(RenderedPageFixture):
    """The frosted look and the new movement are both optional flourishes on
    an app whose readers depend on legibility. The rules worth defending are
    the negative ones: the editor never goes see-through, nothing animates
    forever, and a browser that cannot do the effect still gets solid panels
    rather than none."""

    GLASS_KEYS = (
        "glass.material_label",
        "glass.material_off",
        "glass.material_mica",
        "glass.material_frosted",
        "glass.material_acrylic",
        "glass.material_help",
        "glass.tint_label",
        "glass.tint_picker_label",
        "glass.tint_help",
        "glass.tint_reset",
        "glass.help",
    )

    # The body rule that opts a surface in. "off" is excluded here rather
    # than handled by a later override, so the solid state cannot be
    # reached by accident.
    SELECTOR = "body:not([data-glass-material='off']) :is("

    def test_the_page_carries_the_setting_before_any_script_runs(self):
        # Otherwise the page paints solid and then changes under the reader.
        self.assertIn("data-glass-material=", self.template)
        self.assertIn("data-glass-tint=", self.template)

    def test_the_material_is_a_radio_group_and_is_labelled(self):
        # Radios, not buttons: these are four names for one setting, so the
        # arrow keys have to move between them and only one can be chosen.
        self.assertIn('name="glass-material"', self.html)
        for value in ("off", "mica", "frosted", "acrylic"):
            with self.subTest(material=value):
                self.assertIn(f'value="{value}"', self.html)
        self.assertIn('role="radiogroup"', self.html)
        # A radiogroup needs a label and a description, or a screen reader
        # announces four bare buttons.
        self.assertIn('aria-labelledby="glass-material-label"', self.html)
        self.assertIn('aria-describedby="glass-material-help"', self.html)
        self.assertIn('id="glass-material-label"', self.html)

    def test_the_colour_picker_is_labelled_and_can_be_reset(self):
        self.assertIn('id="glass-tint-picker"', self.html)
        self.assertIn('id="glass-tint-hex"', self.html)
        self.assertIn('id="glass-tint-reset"', self.html)
        # The picker and the text box both change the one setting, so both
        # need names of their own rather than sharing a <label for>.
        self.assertIn('for="glass-tint-hex"', self.html)
        self.assertIn('aria-label="{{ t(\'glass.tint_picker_label\') }}"', self.template)
        self.assertIn('aria-describedby="glass-tint-help glass-tint-error"', self.html)
        # Reset is a real button, so it is in the tab order and can be
        # operated from the keyboard.
        self.assertRegex(
            self.html, r'<button id="glass-tint-reset"[^>]*type="button"'
        )

    def test_every_language_can_name_it(self):
        for language in i18n.LANGUAGES:
            catalogue = i18n.load_catalogue(language)
            for key in self.GLASS_KEYS:
                with self.subTest(language=language, key=key):
                    self.assertIn(key, catalogue)
                    self.assertTrue(catalogue[key].strip())

    def test_the_editor_is_never_translucent(self):
        # This is the rule that keeps the effect safe to offer at all. The
        # code is read against .editor-pane, so that surface stays solid.
        # Every material block is checked, not just the first: a new
        # material with its own selector could reintroduce the risk.
        for block in self._material_blocks():
            self.assertNotIn("editor-pane", block)
            self.assertNotIn("editor-wrap", block)

    def _material_blocks(self):
        """Every rule whose body sets a backdrop-filter, with its selector."""
        for match in re.finditer(
            r"([^{}]*backdrop-filter[^{}]*)\{([^}]*)\}", self.css
        ):
            yield match.group(1), match.group(2)

    def test_only_named_surfaces_go_translucent(self):
        # An open-ended descendant rule would catch the editor next time
        # somebody adds a panel, so the list is spelled out.
        block = self.css.split(self.SELECTOR, 1)[1]
        listed = block[: block.index(")")].replace("\n", " ")
        for surface in (
            ".topbar",
            ".output-pane",
            ".shell-pane",
            ".settings",
            ".pkg",
            ".setup-panel",
            ".error-panel",
        ):
            with self.subTest(surface=surface):
                self.assertIn(surface, listed)

    def test_a_browser_without_color_mix_still_gets_a_solid_panel(self):
        # The opaque declaration has to come first, or the panel loses its
        # background entirely and the words on it lose their contrast too.
        # Match the declaration, not the name, which also occurs in the
        # comment explaining why it is there.
        block = self.css.split(self.SELECTOR, 1)[1]
        block = block[: block.index("\n}")]
        self.assertLess(
            block.index("background: var(--panel-bg)"),
            block.index("background: color-mix"),
        )

    def test_every_material_is_a_real_one(self):
        # A material that is named in the UI but not in the CSS would
        # silently show solid panels, and the reader would have no way to
        # tell the app from a broken one.
        for value in ("mica", "frosted", "acrylic"):
            with self.subTest(material=value):
                self.assertIn(
                    f"body[data-glass-material='{value}']",
                    self.css,
                )

    def test_the_most_transparent_material_is_the_one_said_to_be(self):
        # The help text promises mica is nearly solid and acrylic the most
        # see-through. If the numbers drift the other way the description
        # becomes a lie, and a reader who chose mica for its quietness would
        # get the heaviest of the three.
        def alpha_of(material):
            match = re.search(
                rf"body\[data-glass-material='{material}'\][^{{]*\{{(.*?)\n\}}",
                self.css,
                re.S,
            )
            self.assertIsNotNone(match, f"no block for {material}")
            assert match is not None  # for the type checker, not the test
            found = re.search(r"--glass-alpha:\s*(\d+)%", match.group(1))
            self.assertIsNotNone(found, f"no alpha for {material}")
            assert found is not None
            return int(found.group(1))

        # Higher alpha is more solid, so mica must be the most opaque.
        self.assertGreater(alpha_of("mica"), alpha_of("frosted"))
        self.assertGreater(alpha_of("frosted"), alpha_of("acrylic"))

    def test_a_custom_tint_is_mixed_not_substituted(self):
        # The panels are already translucent. Letting a colour replace the
        # theme's panel colour outright would let a reader remove the very
        # thing that keeps the text legible, so the tint is a shift within
        # the theme's colour rather than a replacement for it.
        block = self.css.split(self.SELECTOR, 1)[1]
        block = block[: block.index("\n}")]
        self.assertIn("--glass-fill: color-mix", block)
        self.assertIn("var(--glass-tint, var(--panel-bg))", block)
        self.assertIn("var(--panel-bg)", block)

    def test_reduced_transparency_wins_over_the_materials(self):
        # Somebody who has asked their operating system for less
        # transparency gets none, whatever the app is set to. The
        # !important is deliberate and is what makes this override the
        # material rules in the one case that matters.
        self.assertIn("prefers-reduced-transparency: reduce", self.css)
        block = self.css.split("prefers-reduced-transparency: reduce", 1)[1]
        block = block[: block.index("\n}")]
        self.assertIn("backdrop-filter: none !important", block)
        self.assertIn("background: var(--panel-bg) !important", block)

    def test_the_grain_belongs_to_acrylic_only(self):
        # Grain is what tells acrylic from a merely blurry panel, so it has
        # to be reachable only under that material. Matched on the selector
        # that governs the declaration, not the declaration itself.
        rules = re.finditer(r"([^{}]*)\{([^}]*data:image/svg\+xml[^}]*)\}", self.css)
        selectors = [match.group(1) for match in rules]
        self.assertTrue(selectors, "the acrylic grain is missing")
        for selector in selectors:
            self.assertIn("data-glass-material='acrylic'", selector)

    def test_nothing_animates_forever(self):
        # A loop that never stops runs for as long as the window is open,
        # which is the classic way to set off vestibular symptoms. Every
        # animation here is allowed to run once.
        for found in re.finditer(r"animation:\s*([^;]+);", self.css):
            for declaration in found.group(1).split(","):
                if "infinite" in declaration:
                    self.fail(f"an animation loops forever: {declaration.strip()}")

    def _themes(self):
        """(name, variables) for the root defaults and each theme block."""
        root = self._vars(self.css.split(":root {", 1)[1].split("\n}", 1)[0])
        yield "(root defaults)", root
        for name, block in re.findall(
            r'body\[data-theme="([^"]+)"\]\s*\{(.*?)\n\}', self.css, re.S
        ):
            yield name, dict(root, **self._vars(block))

    @staticmethod
    def _vars(block):
        out = {}
        for name, raw in re.findall(r"(--[a-z0-9-]+)\s*:\s*(#[0-9a-fA-F]{3,8})\s*;", block):
            value = raw.lstrip("#")
            if len(value) == 3:
                value = "".join(c * 2 for c in value)
            out[name] = tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))
        return out

    @staticmethod
    def _luminance(rgb):
        channels = []
        for value in rgb:
            c = value / 255
            channels.append(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)
        r, g, b = channels
        return 0.2126 * r + 0.7152 * g + 0.0722 * b

    @classmethod
    def _contrast(cls, a, b):
        la, lb = cls._luminance(a), cls._luminance(b)
        return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)

    def _material_alpha(self, material):
        """The opacity the stylesheet gives a material, as a fraction.

        Read from the file rather than restated here, so the number the test
        measures is the number a reader actually gets. A material that sets
        none falls back to the defaults in the shared rule.
        """
        match = re.search(
            rf"body\[data-glass-material='{material}'\][^{{]*\{{(.*?)\n\}}", self.css, re.S
        )
        if match is not None:
            found = re.search(r"--glass-alpha:\s*(\d+)%", match.group(1))
            if found is not None:
                return int(found.group(1)) / 100
        shared = self.css.split(self.SELECTOR, 1)[1]
        shared = shared[: shared.index("\n}")]
        found = re.search(r"--glass-alpha:\s*(\d+)%", shared)
        self.assertIsNotNone(found, f"no opacity stated for {material}")
        assert found is not None
        return int(found.group(1)) / 100

    def test_no_material_costs_contrast(self):
        # The promise made in Settings is that choosing a material does not
        # change the contrast the reader reads by. So it is measured rather
        # than trusted: composite the fill the stylesheet actually uses over
        # the page background, and check every material in every theme, both
        # for a regression and for the 4.5:1 that AA asks of text.
        #
        # Acrylic is the one to watch. It is the most see-through of the
        # three, so it has the least colour left to sit behind the words.
        for material in ("mica", "frosted", "acrylic"):
            alpha = self._material_alpha(material)
            for name, variables in self._themes():
                bg, panel = variables.get("--bg"), variables.get("--panel-bg")
                if not bg or not panel:
                    continue
                fill = tuple(round(bg[i] * (1 - alpha) + panel[i] * alpha) for i in range(3))
                for token in ("--fg", "--muted", "--error-fg"):
                    fg = variables.get(token)
                    if not fg:
                        continue
                    solid = self._contrast(fg, panel)
                    softened = self._contrast(fg, fill)
                    with self.subTest(material=material, theme=name, token=token):
                        self.assertLessEqual(
                            solid, softened + 0.01,
                            f"{material} lowered {token} in the {name} theme",
                        )
                        self.assertGreaterEqual(
                            softened, 4.5,
                            f"{token} drops to {softened:.2f}:1 on a {material} "
                            f"panel in {name}",
                        )

    def test_a_custom_tint_cannot_remove_the_colour_behind_the_words(self):
        # A tint reaches CSS already pulled toward the panel by
        # routes.panel_tint_for, which checks it against the theme's own --fg,
        # --muted and --error-fg. So the hostile case here is not an arbitrary
        # colour any more: it is the worst colour the reader can get painted,
        # which is what that function returns for a tint that could not be
        # made readable as itself.
        #
        # CSS then blends that painted tint with the panel, and the material
        # blends the result with the page background. Both steps are measured
        # here against the real theme values, because two blends that each
        # look safe can add up to something that is not.
        found = re.search(
            r"--glass-fill:\s*color-mix\(in srgb,\s*var\(--glass-tint.*?\)\s*(\d+)%",
            self.css,
        )
        self.assertIsNotNone(found, "the tint blend no longer states its own share")
        assert found is not None
        tint_share = int(found.group(1)) / 100
        # The theme's colour always keeps the larger share, so a tint can
        # shift the hue without taking over.
        self.assertLess(tint_share, 0.5)

        for material in ("mica", "frosted", "acrylic"):
            alpha = self._material_alpha(material)
            for name, variables in self._themes():
                bg, panel = variables.get("--bg"), variables.get("--panel-bg")
                if not bg or not panel:
                    continue
                theme = (
                    routes.DEFAULT_CONFIG["theme"]
                    if name.startswith("(")
                    else name
                )
                # Hostile in the strongest sense available: the colour the
                # theme cannot rescue at all, which is the opposite of the
                # panel, and the most saturated thing a reader could pick.
                for raw in ("#000000", "#ffffff", "#ff0000", "#00ff00"):
                    painted = parse_hex(
                        routes.panel_tint_for(theme, raw)
                    ) if routes.panel_tint_for(theme, raw) else panel
                    blended = tuple(
                        round(panel[i] * (1 - tint_share) + painted[i] * tint_share)
                        for i in range(3)
                    )
                    fill = tuple(
                        round(bg[i] * (1 - alpha) + blended[i] * alpha)
                        for i in range(3)
                    )
                    for token in ("--fg", "--muted", "--error-fg"):
                        fg = variables.get(token)
                        if not fg:
                            continue
                        with self.subTest(
                            material=material, theme=name, tint=raw, token=token
                        ):
                            self.assertGreaterEqual(
                                self._contrast(fg, fill), 4.5,
                                f"{token} drops to "
                                f"{self._contrast(fg, fill):.2f}:1 on a "
                                f"{material} panel in {name} with {raw}",
                            )
                    # The control is only worth having if it moves the panel.
                    # Where the theme leaves no room to move it, the panel is
                    # the correct answer and there is nothing to assert - so
                    # that case is checked by asking whether a readable colour
                    # was reachable at all, rather than by listing themes,
                    # which would go stale the moment one is added.
                    if self._readable_reachable(raw, panel, variables):
                        self.assertGreater(
                            max(abs(blended[i] - panel[i]) for i in range(3)), 0,
                            f"{raw} was reachable but does nothing at all in "
                            f"the {name} theme",
                        )

    def _readable_reachable(self, tint, panel, variables):
        """Could this tint be made readable without becoming the panel?

        Walked along the same path the tint maths uses, fading toward the
        panel, and stopping short of it. The panel always passes, so including
        it would make every answer look reachable.
        """
        from accessible_ide.utils.colour import readable_on

        start = parse_hex(tint)
        texts = [
            variables[token]
            for token in ("--fg", "--muted", "--error-fg")
            if token in variables
        ]
        for step in range(256):
            fraction = step / 256
            candidate = tuple(
                round(start[i] * (1 - fraction) + panel[i] * fraction)
                for i in range(3)
            )
            if readable_on(texts, candidate) >= 4.5:
                return True
        return False


class ButtonStyleTests(unittest.TestCase):
    """The buttons, as a family.

    These rules exist because the buttons used to disagree with each other
    in ways no reader could name. The base .btn set no background, colour
    or border-colour at all, so the one bare .btn in the template rendered
    as invisible text inside an invisible border. The primary button
    hovered through a brightness filter, which no contrast test can
    measure, while every other control hovered through border-color.
    Buttons were 40px, 32px and 44px depending on where they sat, and a
    later rule replaced the press animation with a scale, contradicting
the comment above it that said a press was a settle and not a bounce.
    """

    def setUp(self):
        # Comments are stripped before anything is matched. These checks
        # read the stylesheet's rules, not its commentary, and a selector
        # named in a comment is not a rule that applies to anything.
        self.css = re.sub(
            r"/\*.*?\*/", "", STYLESHEET.read_text(encoding="utf-8"), flags=re.S
        )

    def rule(self, selector):
        match = re.search(re.escape(selector) + r"\s*\{([^}]*)\}", self.css)
        self.assertIsNotNone(match, f"{selector} has no rule of its own")
        assert match is not None  # narrow the type for checkers
        return match.group(1)

    def test_the_base_button_is_visible(self):
        # Without this, class="btn" on its own is a line of text.
        base = self.rule(".btn")
        for declaration in ("background:", "color:", "border:"):
            with self.subTest(declaration=declaration):
                self.assertIn(
                    declaration,
base,
                    f".btn does not set {declaration}, so a bare .btn in "
                    "the template has no visible box",
                )

    def test_no_button_hovers_through_a_filter(self):
        # filter: brightness() shifts a colour by an amount the contrast
        # arbiter cannot see, because it reads tokens rather than computed
        # pixels. A hover state should say which token it means.
        for selector, body in re.findall(
            r"(\.btn[\w-]*:hover[^{]*)\{([^}]*)\}", self.css
        ):
            with self.subTest(selector=selector.strip()):
                self.assertNotIn(
                    "filter:",
                    body,
                    f"{selector.strip()} hovers through a filter, which the "
                    "contrast test cannot measure",
                )

    def test_the_variants_differ_in_size_and_not_in_colour(self):
        # A small button and a normal one should be the same control at two
        # sizes. When each variant declared its own background and border,
        # adding a variant meant remembering to restate them.
        for variant in (".btn-small",):
            with self.subTest(variant=variant):
                body = self.rule(variant)
                for declaration in ("background:", "color:", "border-color:"):
                    self.assertNotIn(
                        declaration,
                        body,
                        f"{variant} restates {declaration}, which the base "
                        ".btn already sets",
                    )

    def test_buttons_share_one_elevation(self):
        # The primary used shadow-2 on top of a 2px border, which is the
        # thin-border-plus-wide-shadow pairing the design bar rules out,
        # and it left one button looking lifted off the panel.
        shadows = set()
        for selector, body in re.findall(r"(\.btn[\w-]*)\s*\{([^}]*)\}", self.css):
            found = re.findall(r"box-shadow:\s*([^;]+);", body)
            if found:
                with self.subTest(selector=selector.strip()):
                    shadows.update(value.strip() for value in found)
        self.assertLessEqual(
            len(shadows), 1, f"buttons use more than one elevation: {sorted(shadows)}"
        )

    def test_a_button_settles_rather_than_scaling(self):
        # .btn:active translates down by a pixel. A later rule used to
        # replace that with scale(0.97), so the two rules disagreed about
        # what a press does and the undocumented one won.
        self.assertIn("translateY", self.rule(".btn:active"))
        for selector, body in re.findall(
            r"(\.btn[\w-]*:active[^{]*)\{([^}]*)\}", self.css
        ):
            with self.subTest(selector=selector.strip()):
                self.assertNotIn(
                    "scale(",
                    body,
                    f"{selector.strip()} scales the button on press, which "
                    "is the bounce the .btn comment rules out",
                )
