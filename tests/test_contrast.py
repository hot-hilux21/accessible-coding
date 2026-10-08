"""WCAG 2.1 AA checks for the syntax colour palettes.

The base palettes live in routes.THEMES. The optional "extra high
contrast" remaps live in the contrastPalette object in app.js, because
they are applied by the editor at runtime.

The tests below cover both directions of drift:
  - a colour changed on the server without updating app.js, and
  - a remap left behind in app.js after the server colour was renamed.
Either one would otherwise only show up as "the code looks a bit off"
for a user, so it is worth a failing test.

Run with:  PYTHONPATH=src python -m unittest discover -s tests -t .
"""

import pathlib
import re
import sys
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
APP_JS = REPO_ROOT / "src" / "accessible_ide" / "static" / "js" / "app.js"

# The colours that are rendered as text and must clear 4.5:1 against the
# theme background. `selection` and `cursor` are excluded: neither is text.
TEXT_KEYS = (
    "fg",
    "gutter_fg",
    "keyword",
    "string",
    "comment",
    "number",
    "function",
    "variable",
    "operator",
    "punctuation",
)

AA_NORMAL_TEXT = 4.5
# Guards against a value that is exactly 4.5 failing on float noise.
EPSILON = 1e-9


def _load_routes():
    """Import accessible_ide.routes from src/ without needing it installed."""
    src = str(REPO_ROOT / "src")
    if src not in sys.path:
        sys.path.append(src)

    # Imported as a package member rather than by file path: routes.py is
    # part of accessible_ide and uses package-relative imports, so loading
    # it standalone would execute it with no parent package and blow up on
    # the first "from . import".
    from accessible_ide import routes

    return routes


def load_contrast_palette():
    """Pull the contrastPalette literal out of app.js.

    It is plain data - string keys to string hex values, grouped by theme
    - so a regex is enough and keeps the test free of a JS runtime.
    """
    text = APP_JS.read_text(encoding="utf-8")
    start = text.index("var contrastPalette")
    brace = text.index("{", start)

    depth = 0
    for index in range(brace, len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                block = text[brace : index + 1]
                break
    else:
        raise AssertionError("could not find the end of the contrastPalette object")

    palette = {}
    for theme, body in re.findall(r"'?([\w-]+)'?\s*:\s*\{([^}]*)\}", block):
        pairs = re.findall(
            r"'(#[0-9a-fA-F]{6})'\s*:\s*'(#[0-9a-fA-F]{6})'", body
        )
        palette[theme] = dict(pairs)
    return palette


def _srgb_channel(value):
    channel = value / 255.0
    if channel <= 0.04045:
        return channel / 12.92
    return ((channel + 0.055) / 1.055) ** 2.4


def relative_luminance(hex_color):
    raw = hex_color.lstrip("#")
    red, green, blue = (int(raw[i : i + 2], 16) for i in (0, 2, 4))
    return (
        0.2126 * _srgb_channel(red)
        + 0.7152 * _srgb_channel(green)
        + 0.0722 * _srgb_channel(blue)
    )


def contrast_ratio(foreground, background):
    first = relative_luminance(foreground)
    second = relative_luminance(background)
    lighter = max(first, second)
    darker = min(first, second)
    return (lighter + 0.05) / (darker + 0.05)


class SyntaxContrastTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.routes = _load_routes()
        cls.themes = cls.routes.THEMES
        cls.contrast_palette = load_contrast_palette()

    def test_every_theme_background_is_a_hex_colour(self):
        # A typo in a hex value would make the ratio maths below lie.
        for theme, palette in self.themes.items():
            for key, value in palette.items():
                with self.subTest(theme=theme, key=key):
                    if key == "name":
                        continue
                    self.assertRegex(value, r"^#[0-9a-fA-F]{6}$")

    def test_syntax_colours_meet_aa(self):
        for theme, palette in self.themes.items():
            background = palette["bg"]
            for key in TEXT_KEYS:
                with self.subTest(theme=theme, key=key):
                    ratio = contrast_ratio(palette[key], background)
                    self.assertGreaterEqual(
                        ratio + EPSILON,
                        AA_NORMAL_TEXT,
                        f"{theme}.{key} ({palette[key]}) on "
                        f"{background} is only {ratio:.2f}:1",
                    )

    def test_every_theme_has_a_remap_table(self):
        self.assertEqual(
            sorted(self.contrast_palette),
            sorted(self.themes),
            "app.js contrastPalette and routes.THEMES have drifted apart",
        )

    def test_high_contrast_remaps_meet_aa(self):
        for theme, palette in self.themes.items():
            background = palette["bg"]
            remaps = self.contrast_palette[theme]
            for key in TEXT_KEYS:
                base = palette[key]
                with self.subTest(theme=theme, key=key):
                    self.assertIn(
                        base,
                        remaps,
                        f"{theme}.{key} ({base}) has no extra-high-contrast remap "
                        f"in app.js",
                    )
                    ratio = contrast_ratio(remaps[base], background)
                    self.assertGreaterEqual(
                        ratio + EPSILON,
                        AA_NORMAL_TEXT,
                        f"boosted {theme}.{key} ({remaps[base]}) on "
                        f"{background} is only {ratio:.2f}:1",
                    )

    def test_high_contrast_remaps_have_no_stray_keys(self):
        # The reverse of the drift above: a remap whose base colour is no
        # longer used by the theme is dead code that will mislead the next
        # person to change a palette.
        for theme, palette in self.themes.items():
            in_use = set(palette.values())
            for base in self.contrast_palette[theme]:
                with self.subTest(theme=theme, base=base):
                    self.assertIn(
                        base,
                        in_use,
                        f"{theme}: contrastPalette remaps {base}, which is not "
                        f"a colour in routes.THEMES",
                    )

    def test_extra_high_contrast_never_reduces_contrast(self):
        # A boost that made text harder to read would be worse than no
        # boost at all, so every remap must move away from the background.
        for theme, palette in self.themes.items():
            background = palette["bg"]
            for key in TEXT_KEYS:
                base = palette[key]
                boosted = self.contrast_palette[theme].get(base)
                if boosted is None:
                    continue
                with self.subTest(theme=theme, key=key):
                    self.assertGreater(
                        contrast_ratio(boosted, background) + EPSILON,
                        contrast_ratio(base, background),
                        f"{theme}.{key}: extra high contrast made it worse",
                    )

    def test_highlight_keeps_text_readable(self):
        # The highlight sits behind the code, so the theme's own text must
        # still clear AA on it. A highlight that hides the text is the bug
        # this test exists to catch: the old active-line colour was the
        # selection colour at 20% opacity, which on the dark themes was
        # effectively black.
        for theme, palette in self.themes.items():
            with self.subTest(theme=theme):
                self.assertIn(
                    "highlight",
                    palette,
                    f"{theme} has no highlight colour",
                )
                ratio = contrast_ratio(palette["fg"], palette["highlight"])
                self.assertGreaterEqual(
                    ratio + EPSILON,
                    AA_NORMAL_TEXT,
                    f"{theme}: text ({palette['fg']}) on the highlight "
                    f"({palette['highlight']}) is only {ratio:.2f}:1",
                )


class CustomThemeContrastTests(unittest.TestCase):
    """The reader's own theme is derived, so it has to be checked with the
    derivation, not with a fixed table. The fixtures are the cases the
    derivation exists for: a dark pick, a light pick, and a mid-grey
    background where the raw picks fail and the clamp has to save them.
    """

    @classmethod
    def setUpClass(cls):
        cls.routes = _load_routes()

    def _palette(self, picks):
        config = {"theme_custom_" + key: value for key, value in picks.items()}
        return self.routes.custom_palette(config)

    def _chrome(self, picks):
        return self.routes.custom_chrome(self._palette(picks))

    def test_dark_picks_meet_aa(self):
        palette = self._palette({
            "bg": "#0b0b0b", "fg": "#ffffff", "keyword": "#ff9a9a",
            "string": "#93e6a8", "comment": "#b4b4b4", "number": "#ffd93d",
            "function": "#93d4ff",
        })
        for key in TEXT_KEYS:
            with self.subTest(key=key):
                ratio = contrast_ratio(palette[key], palette["bg"])
                self.assertGreaterEqual(
                    ratio + EPSILON, AA_NORMAL_TEXT,
                    f"custom.{key} ({palette[key]}) on {palette['bg']} "
                    f"is only {ratio:.2f}:1",
                )

    def test_light_picks_meet_aa(self):
        palette = self._palette({
            "bg": "#fcfcfc", "fg": "#2b2b2b", "keyword": "#7a1f1f",
            "string": "#1f5c33", "comment": "#5c5c5c", "number": "#7a5c00",
            "function": "#1f4d7a",
        })
        for key in TEXT_KEYS:
            with self.subTest(key=key):
                ratio = contrast_ratio(palette[key], palette["bg"])
                self.assertGreaterEqual(
                    ratio + EPSILON, AA_NORMAL_TEXT,
                    f"custom.{key} ({palette[key]}) on {palette['bg']} "
                    f"is only {ratio:.2f}:1",
                )

    def test_mid_grey_background_clamps_the_picks(self):
        # White on mid grey is 3.9:1, under AA. The derivation has to move
        # the text toward black until it clears, and the result has to be
        # readable on the background it was clamped for.
        palette = self._palette({
            "bg": "#777777", "fg": "#ffffff", "keyword": "#ffffff",
            "string": "#ffffff", "comment": "#ffffff", "number": "#ffffff",
            "function": "#ffffff",
        })
        for key in TEXT_KEYS:
            with self.subTest(key=key):
                ratio = contrast_ratio(palette[key], palette["bg"])
                self.assertGreaterEqual(
                    ratio + EPSILON, AA_NORMAL_TEXT,
                    f"custom.{key} ({palette[key]}) on {palette['bg']} "
                    f"is only {ratio:.2f}:1",
                )

    def test_chrome_text_meets_aa(self):
        # The page chrome is derived too: the accent's own text, the muted
        # panel text, and the error colours all have to clear AA on the
        # surfaces they sit on.
        for picks in (
            {"bg": "#0b0b0b", "fg": "#ffffff", "keyword": "#ff9a9a",
             "string": "#93e6a8", "comment": "#b4b4b4", "number": "#ffd93d",
             "function": "#93d4ff"},
            {"bg": "#fcfcfc", "fg": "#2b2b2b", "keyword": "#7a1f1f",
             "string": "#1f5c33", "comment": "#5c5c5c", "number": "#7a5c00",
             "function": "#1f4d7a"},
            {"bg": "#777777", "fg": "#ffffff", "keyword": "#ffffff",
             "string": "#ffffff", "comment": "#ffffff", "number": "#ffffff",
             "function": "#ffffff"},
        ):
            chrome = self._chrome(picks)
            with self.subTest(bg=picks["bg"]):
                self.assertGreaterEqual(
                    contrast_ratio(chrome["accent-fg"], chrome["accent"]) + EPSILON,
                    AA_NORMAL_TEXT,
                    f"accent text {chrome['accent-fg']} on "
                    f"{chrome['accent']} is under AA",
                )
                self.assertGreaterEqual(
                    contrast_ratio(chrome["muted"], chrome["panel-bg"]) + EPSILON,
                    AA_NORMAL_TEXT,
                    f"muted {chrome['muted']} on {chrome['panel-bg']} is under AA",
                )
                self.assertGreaterEqual(
                    contrast_ratio(chrome["error-fg"], chrome["error-bg"]) + EPSILON,
                    AA_NORMAL_TEXT,
                    f"error text {chrome['error-fg']} on "
                    f"{chrome['error-bg']} is under AA",
                )
                self.assertGreaterEqual(
                    contrast_ratio(chrome["error-border"], chrome["error-bg"]) + EPSILON,
                    AA_NORMAL_TEXT,
                    f"error border {chrome['error-border']} on "
                    f"{chrome['error-bg']} is under AA",
                )


if __name__ == "__main__":
    unittest.main()
