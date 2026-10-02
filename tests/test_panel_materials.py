"""The panel materials: three translucent looks and one custom colour.

Two separate promises are tested here, and they are kept apart on purpose.

The first is that the three materials cost no contrast. That is checked by
compositing the fill the stylesheet actually uses over the page background and
measuring, rather than by trusting the comment next to it.

The second is that the colour picker cannot be used to break contrast. That
one is checked against the arithmetic in utils/colour.py, because that is
where the guarantee actually lives: a chosen colour is faded toward the theme's
panel colour, and only as far as it takes for that theme's own --fg, --muted
and --error-fg to stay readable on it.

The vectors in tests/tint_vectors.json are shared with the browser's copy of
the maths (static/js/tint.js), so the two cannot drift apart unnoticed.
"""

import json
import math
import re
import unittest
from pathlib import Path

from accessible_ide import create_app, routes
from accessible_ide.utils import colour

HERE = Path(__file__).resolve().parent
CSS = (HERE.parent / "src/accessible_ide/static/css/style.css").read_text(
    encoding="utf-8"
)
VECTORS = json.loads((HERE / "tint_vectors.json").read_text(encoding="utf-8"))

MATERIALS = ("mica", "frosted", "acrylic")
SELECTOR = "body:not([data-glass-material='off']) :is("


def variables(block):
    """The hex colours declared in a CSS block, by custom property name."""
    return {
        match.group(1): tuple(int(match.group(i), 16) for i in (2, 3, 4))
        for match in re.finditer(
            r"(--[\w-]+):\s*#([0-9a-f]{2})([0-9a-f]{2})([0-9a-f]{2})", block
        )
    }


def themes():
    """(name, variables) for the root defaults and each theme block."""
    root = variables(CSS.split(":root {", 1)[1].split("\n}", 1)[0])
    yield "(root defaults)", root
    for name, block in re.findall(
        r'body\[data-theme="([^"]+)"\]\s*\{(.*?)\n\}', CSS, re.S
    ):
        yield name, dict(root, **variables(block))


def alpha_of(material):
    """The opacity the stylesheet gives a material, as a fraction.

    Read from the file rather than restated here, so the number measured is
    the number a reader gets. A material naming no opacity falls back to the
    shared rule's default.
    """
    match = re.search(
        rf"body\[data-glass-material='{material}'\][^{{]*\{{(.*?)\n\}}", CSS, re.S
    )
    if match is not None:
        found = re.search(r"--glass-alpha:\s*(\d+)%", match.group(1))
        if found is not None:
            return int(found.group(1)) / 100
    shared = CSS.split(SELECTOR, 1)[1]
    shared = shared[: shared.index("\n}")]
    found = re.search(r"--glass-alpha:\s*(\d+)%", shared)
    if found is None:
        raise AssertionError(f"no opacity stated for {material}")
    return int(found.group(1)) / 100


def composite(foreground, background, alpha):
    """The colour a fill of ``alpha`` shows, painted over ``background``."""
    return tuple(
        round(background[i] * (1 - alpha) + foreground[i] * alpha)
        for i in range(3)
    )


def panel_text(palette):
    """The three text colours that sit on this palette's panel, as triples.

    Read from the stylesheet the same way the panel colour is, so a check here
    is a check against what a reader actually looks at. Taken from the same
    palette rather than from the theme table, because pairing one theme's panel
    with another theme's text is exactly the mismatch that let the pastel
    picker collapse: the search was checking a set the reader never sees.
    """
    found = tuple(
        palette[token]
        for token in ("--fg", "--muted", "--error-fg")
        if token in palette
    )
    if len(found) != 3:
        raise AssertionError(
            "no panel text colours found for "
            f"{sorted(t for t in palette if t in ('--fg', '--muted', '--error-fg'))}"
        )
    return found


def themes_by_name():
    """The named theme blocks, keyed by name, with the root defaults applied."""
    root = variables(CSS.split(":root {", 1)[1].split("\n}", 1)[0])
    return {
        name: dict(root, **variables(block))
        for name, block in re.findall(
            r'body\[data-theme="([^"]+)"\]\s*\{(.*?)\n\}', CSS, re.S
        )
    }


def tinted(palette, tint_hex):
    """What the panels are painted in for this palette and this choice."""
    return colour.parse_hex(
        colour.safe_panel_tint(tint_hex, palette["--panel-bg"], panel_text(palette))
    )


class MaterialContrastTests(unittest.TestCase):
    """A material is a look. It must not cost the contrast the reader reads
    by, in any theme, for any of the text that sits on a panel."""

    def test_no_material_costs_contrast(self):
        # Measured rather than trusted: composite the fill the stylesheet
        # actually uses over the page background, then compare each token
        # against the solid panel it replaces.
        for material in MATERIALS:
            alpha = alpha_of(material)
            for name, palette in themes():
                background = palette.get("--bg")
                panel = palette.get("--panel-bg")
                if not background or not panel:
                    continue
                fill = composite(panel, background, alpha)
                for token in ("--fg", "--muted", "--error-fg"):
                    foreground = palette.get(token)
                    if not foreground:
                        continue
                    solid = colour.contrast_ratio(foreground, panel)
                    softened = colour.contrast_ratio(foreground, fill)
                    with self.subTest(material=material, theme=name, token=token):
                        self.assertLessEqual(
                            solid,
                            softened + 0.01,
                            f"{material} lowered {token} in the {name} theme",
                        )
                        self.assertGreaterEqual(
                            softened,
                            4.5,
                            f"{token} drops to {softened:.2f}:1 on a {material} "
                            f"panel in {name}",
                        )

    def test_the_most_transparent_material_is_the_one_said_to_be(self):
        # The help text promises mica is nearly solid and acrylic the most
        # see-through. If the numbers drift the other way the description
        # becomes a lie, and a reader who chose mica for its quietness would
        # get the heaviest of the three.
        self.assertGreater(alpha_of("mica"), alpha_of("frosted"))
        self.assertGreater(alpha_of("frosted"), alpha_of("acrylic"))


class TintClampTests(unittest.TestCase):
    """A chosen colour is faded toward the theme's panel colour, and only as far
    as it takes for that theme's own text to stay readable on it.

    Faded rather than pinned to a computed lightness on purpose: contrast
    depends on luminance alone, so fading toward the panel is monotonic in
    contrast and the answer lands on the boundary. The earlier approach looked
    tidier and collapsed the pastel picker, because it measured legal
    lightnesses on neutral greys while pastel's panel and muted text are both
    warm.
    """

    # Colours a reader is likely to reach for, including the ones no tint can
    # rescue on every theme.
    TINTS = ("#000000", "#ffffff", "#ff0000", "#0000ff", "#00ff00",
             "#7a1fa2", "#0057b8", "#ffd93d", "#336699", "#4a7fb5")

    def test_it_matches_the_shared_vectors(self):
        for case in VECTORS["cases"]:
            with self.subTest(theme=case["theme"], tint=case["tint"]):
                self.assertEqual(
                    colour.safe_panel_tint(
                        case["tint"], case["panel"], case["texts"]
                    ),
                    case["expected"],
                )

    def test_no_tint_means_follow_the_theme(self):
        for case in VECTORS["empty_tint"]:
            with self.subTest(tint=case["tint"]):
                self.assertEqual(
                    colour.safe_panel_tint(case["tint"], "#f2f2f2", case["texts"]),
                    case["expected"],
                )

    def test_the_themes_own_text_stays_readable_on_the_result(self):
        # The whole guarantee in one line. Measured, not inferred: whatever
        # the reader picks, the answer is a colour this theme's own three text
        # colours can be read against.
        for tint in self.TINTS:
            for name, palette in themes():
                if "--panel-bg" not in palette:
                    continue
                got = tinted(palette, tint)
                for token in ("--fg", "--muted", "--error-fg"):
                    with self.subTest(tint=tint, theme=name, token=token):
                        self.assertGreaterEqual(
                            colour.contrast_ratio(palette[token], got),
                            colour.AA_CONTRAST,
                            f"{token} on a {tint} panel in {name}",
                        )

    def test_a_colour_that_already_reads_is_left_alone(self):
        # The app is a tool. A reader who picks a colour they can read has to
        # be given that colour, not something adjacent to it.
        for name, palette in themes():
            if "--panel-bg" not in palette:
                continue
            for tint in self.TINTS:
                rgb = colour.parse_hex(tint)
                if colour.readable_on(panel_text(palette), rgb) >= colour.AA_CONTRAST:
                    with self.subTest(tint=tint, theme=name):
                        self.assertEqual(
                            tinted(palette, tint), rgb,
                            f"{tint} already reads in {name} and was altered",
                        )

    def test_the_tint_is_still_visible(self):
        # A clamp that collapsed every colour onto the panel would satisfy
        # every contrast check and be useless, so most tints have to move the
        # panel by a visible amount.
        #
        # Not all of them, and the exceptions are real. A saturated dark
        # colour cannot be made readable on a light theme whose panel already
        # sits close to its own limit: pastel's --muted clears AA by 0.01, so
        # lightening pure red toward the panel runs out of room before it
        # clears the bar, and the panel itself is the correct answer. Keeping
        # the reader inside the theme beats jumping to a near-white that no
        # longer belongs to it.
        collapsed = []
        moved = 0
        for tint in ("#ff0000", "#0000ff", "#00ff00", "#7a1fa2",
                     "#0057b8", "#ffd93d"):
            for name, palette in themes():
                panel = palette["--panel-bg"]
                got = tinted(palette, tint)
                shift = max(abs(got[i] - panel[i]) for i in range(3))
                if shift == 0:
                    collapsed.append((tint, name, palette))
                elif shift >= 8:
                    moved += 1
        # Most combinations move the panel visibly.
        self.assertGreater(moved, len(MATERIALS) * 3)
        # And every collapse has to be one the theme leaves no room for. The
        # scan stops short of the panel, because the panel is always readable
        # and counting it would make every collapse look like a missed answer.
        for tint, name, palette in collapsed:
            with self.subTest(tint=tint, theme=name):
                rgb = colour.parse_hex(tint)
                texts = panel_text(palette)
                surface = palette["--panel-bg"]
                reachable = any(
                    colour.readable_on(
                        texts,
                        tuple(
                            round(rgb[i] * (1 - step / 256)
                                  + surface[i] * (step / 256))
                            for i in range(3)
                        ),
                    ) >= colour.AA_CONTRAST
                    for step in range(256)
                )
                self.assertFalse(
                    reachable,
                    f"{tint} collapsed to the panel in {name}, but a readable "
                    f"colour was reachable and the search missed it",
                )

    def test_no_theme_ever_needs_a_colour_the_server_cannot_make(self):
        # Every theme, every material, the colour the reader asked for and
        # the two most hostile ones, all still above 4.5:1.
        for name, palette in themes():
            background = palette.get("--bg")
            if not background or "--panel-bg" not in palette:
                continue
            for material in MATERIALS:
                alpha = alpha_of(material)
                for tint in ("#000000", "#ffffff", "#ff0000", "#0000ff", "#00ff00"):
                    fill = composite(tinted(palette, tint), background, alpha)
                    for token in ("--fg", "--muted", "--error-fg"):
                        foreground = palette.get(token)
                        if not foreground:
                            continue
                        with self.subTest(
                            material=material, theme=name, tint=tint, token=token
                        ):
                            self.assertGreaterEqual(
                                colour.contrast_ratio(foreground, fill),
                                4.5,
                                f"{token} on a tinted {material} panel in {name}",
                            )

    def test_a_rubbish_colour_is_refused_rather_than_guessed_at(self):
        for value in ("red", "#12345", "#gggggg", "rgb(1,2,3)", "#1234567"):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    colour.parse_hex(value)


class ServerAndBrowserAgreeTests(unittest.TestCase):
    """The server computes the first paint; the browser computes a theme
    change. If they disagreed, the panels would change colour the moment the
    reader switched theme, which looks like a fault even when it is only
    arithmetic."""

    def test_the_browser_copy_is_served(self):
        page = create_app().test_client().get("/").data.decode("utf-8")
        self.assertIn("js/tint.js", page)
        # Loaded before app.js, which uses it on the first pass.
        self.assertLess(page.index("js/tint.js"), page.index("js/app.js"))

    def test_the_browser_copy_defines_the_same_functions(self):
        script = (
            HERE.parent / "src/accessible_ide/static/js/tint.js"
        ).read_text(encoding="utf-8")
        for name in (
            "parseHex", "toHex", "toLinear", "toSrgb", "luminance",
            "contrastRatio", "readableOn", "tintReadableOn", "safePanelTint",
        ):
            with self.subTest(name=name):
                self.assertIn(name, script)

    def test_the_two_copies_use_the_same_numbers(self):
        # The weights, the threshold and the bisection length. These are the
        # values that decide what colour a reader ends up looking at, and a
        # change to one copy has to be a change to both.
        script = (
            HERE.parent / "src/accessible_ide/static/js/tint.js"
        ).read_text(encoding="utf-8")
        weights = ", ".join(str(w) for w in colour.CHANNEL_WEIGHTS)
        self.assertIn(f"CHANNEL_WEIGHTS = [{weights}]", script)
        self.assertIn(f"AA_CONTRAST = {colour.AA_CONTRAST}", script)
        self.assertIn(f"BISECTION_STEPS = {colour._BISECTION_STEPS}", script)

    def test_a_channel_conversion_is_always_inside_the_byte_range(self):
        # The one thing a colour helper must never return. The browser's
        # parseHex and toHex already clamped; Python's did not, so a float
        # triple came back with a 256 in it and the two copies disagreed about
        # a colour that cannot exist. Checked here on the Python side because
        # this suite runs without node.
        for triple in (
            [2.5, 3.5, 4.5], [2.6, 3.4, 4.9], [-2.6, 0.5, 255.4],
            [254.6, 254.9, 255.5], [0.0, 0.4, 0.5], [1000.0, -1000.0, 128.5],
            [255.5, 256.0, 300.0],
        ):
            with self.subTest(triple=triple):
                for channel in colour.parse_hex(triple):
                    self.assertTrue(
                        0 <= channel <= 255,
                        f"parse_hex({triple}) gave {channel}, which is not a "
                        "colour",
                    )
                for channel in colour.parse_hex(colour.to_hex(triple)):
                    self.assertTrue(0 <= channel <= 255)

        # The inverse sRGB curve, where the same builtin round() was hiding in
        # Python's to_srgb while the browser used Math.round.
        for linear in (-0.5, 0.0, 0.0031308, 0.5, 1.0, 1.5):
            with self.subTest(linear=linear):
                channel = colour.to_srgb(linear)
                self.assertTrue(
                    0 <= channel <= 255,
                    f"to_srgb({linear}) gave {channel}, which is not a channel",
                )
                self.assertIsInstance(channel, int)

    def test_a_conversion_rounds_up_on_a_tie(self):
        # Python's int() truncates, which is the other half of the bug above:
        # 2.5 became 2 where the browser's Math.round made it 3. to_hex is
        # where a float reaches a channel in the tint path, so that is what is
        # pinned.
        for triple, expected in (
            ([2.5, 3.5, 4.5], "#030405"),
            ([0.5, 1.5, 2.5], "#010203"),
            ([254.5, 0.5, 127.5], "#ff0180"),
        ):
            with self.subTest(triple=triple):
                self.assertEqual(colour.to_hex(triple), expected)

    def test_the_browser_copy_clamps_too(self):
        # The JS half of the two tests above. Read out of the source rather than
        # run through node, because the harness already covers the bisection
        # against a live tint.js and duplicating the whole colour module in this
        # file would be a second implementation to keep in step rather than a
        # check. This asserts the rule is stated once and used twice.
        script = (
            HERE.parent / "src/accessible_ide/static/js/tint.js"
        ).read_text(encoding="utf-8")
        self.assertIn(
            "Math.min(255, Math.max(0, round(value)))", script,
            "tint.js has no single clamping rule; parseHex and toHex each "
            "rolling their own is how they came to disagree",
        )
        # Every float-to-channel conversion goes through one of the two helpers.
        # Comments are stripped first, so prose that mentions clamp() does not
        # count as a call site.
        code = re.sub(r"//[^\n]*", "", script)
        self.assertIn("function round(value)", code)
        self.assertIn("function clamp(value)", code)
        # round() declared once and called once from clamp(). Counted with the
        # declaration excluded, because "round(" also matches "Math.round(".
        self.assertEqual(
            code.count("round(") - code.count("Math.round("), 2,
            "round declared once and called once from clamp",
        )
        # clamp() declared once, then six call sites: three in parseHex (one per
        # channel), toHex, toSrgb, and the bisection.
        self.assertEqual(
            code.count("clamp("), 7,
            "expected clamp declared once and called six times (parseHex "
            f"three, toHex, toSrgb, bisection), found {code.count('clamp(')}",
        )
        # And nothing may round a channel on its own any more. round()'s own
        # body is the one place Math.round belongs.
        body = code.split("function round", 1)[1].split("}", 1)[0]
        for line in code.replace(body, "").splitlines():
            if "Math.round" in line:
                self.fail(
                    "a Math.round outside round(), which is how parseHex and "
                    f"toHex came to disagree: {line.strip()}"
                )

    def test_the_two_copies_round_the_same_way(self):
        # The two implementations have to agree on ties, and their languages
        # default to different answers: Python's round() goes to even, JS's
        # Math.round goes up. A sweep of several thousand tints found 12 that
        # landed exactly on a tie and came out a channel apart. Every one of them
        # still passed the contrast check, so nothing looked broken - the panels
        # just quietly disagreed, which is the failure the whole mirrored-copy
        # arrangement exists to prevent.
        for value in (-2.5, -1.5, -0.5, 0.5, 1.5, 2.5, 3.5, 4.5, 5.5,
                      99.5, 100.5, 101.5, 254.5):
            with self.subTest(value=value):
                # Math.round, spelled out the way JS spells it, for the values
                # this search produces. Everything here is a whole number or
                # ends in .5, which is the only place the two can differ.
                expected = int(math.floor(value + 0.5))
                self.assertEqual(colour._round(value), expected)

    def test_the_vectors_include_a_rounding_tie(self):
        # The shared vectors are what would have caught the tie problem, so
        # they have to actually contain one. Marking a case is only worth
        # anything if the marker is true of it, so a case that is marked as a
        # tie but is not one fails here rather than sitting in the file as a
        # comment that has drifted away from the code.
        for case in VECTORS["cases"]:
            if not case.get("tie"):
                continue
            with self.subTest(theme=case["theme"], tint=case["tint"]):
                self.assertTrue(
                    self._tie_changes_the_answer(case),
                    f"{case['tint']} on {case['theme']} is marked as a rounding "
                    "tie but round() and _round() give the same colour for it, "
                    "so it cannot catch one copy using the other's rounding",
                )

        self.assertTrue(
            any(case.get("tie") for case in VECTORS["cases"]),
            "the shared vectors hold no rounding tie, so the two copies could "
            "disagree on one without any test noticing",
        )

    def test_every_tinted_colour_keeps_the_theme_text_readable(self):
        # The guarantee, measured on every vector rather than inferred from the
        # bisection. Each expected value should sit just above the threshold:
        # the search stops as soon as the text reads, so a vector well clear of
        # 4.5 means the search gave up early and left the reader's colour
        # further from their choice than it needed to be.
        for case in VECTORS["cases"]:
            texts = [colour.parse_hex(c) for c in case["texts"]]
            got = colour.parse_hex(case["expected"])
            with self.subTest(theme=case["theme"], tint=case["tint"]):
                worst = colour.readable_on(texts, got)
                self.assertGreaterEqual(
                    worst, colour.AA_CONTRAST,
                    f"{case['tint']} came out as {case['expected']}, which "
                    f"{case['theme']}'s own text cannot be read against",
                )

    @staticmethod
    def _tie_changes_the_answer(case):
        """Whether the tie convention decides this case's expected value.

        Runs the search both ways. The two conventions agree on almost every
        input, which is why a sweep found 12 divergent cases out of thousands
        and why the ones that matter have to be pinned by hand.
        """
        def search(rounder):
            tint = colour.parse_hex(case["tint"])
            panel = colour.parse_hex(case["panel"])
            texts = [colour.parse_hex(c) for c in case["texts"]]
            low, high = 0.0, 1.0
            best = None
            for _ in range(colour._BISECTION_STEPS):
                middle = (low + high) / 2
                candidate = tuple(
                    rounder(tint[i] * (1 - middle) + panel[i] * middle)
                    for i in range(3)
                )
                if colour.readable_on(texts, candidate) >= colour.AA_CONTRAST:
                    best = candidate
                    high = middle
                else:
                    low = middle
            return best

        return search(colour._round) != search(lambda v: int(round(v)))


class PanelColourLookupTests(unittest.TestCase):
    """The server has to agree with the stylesheet about what colour a theme's
    panels are, because it is the server's number that clamps the tint."""

    def test_the_server_and_the_stylesheet_agree(self):
        css = {
            name: palette.get("--panel-bg")
            for name, palette in themes()
            if not name.startswith("(")
        }
        for theme, panel in css.items():
            with self.subTest(theme=theme):
                self.assertEqual(
                    colour.parse_hex(routes._panel_colour(theme)), panel
                )

    def test_an_unknown_theme_falls_back_rather_than_failing(self):
        # A hand-edited config should show a usable page, not a traceback.
        self.assertEqual(
            routes._panel_colour("no-such-theme"),
            routes.THEMES[routes.DEFAULT_CONFIG["theme"]]["gutter_bg"],
        )


if __name__ == "__main__":
    unittest.main()