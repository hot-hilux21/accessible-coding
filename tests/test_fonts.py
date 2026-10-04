"""Checks that every bundled font is a real font.

OpenDyslexic shipped for several releases as two saved HTML web pages
named ".otf". The browser refused them, the @font-face silently failed,
the stack fell through to the generic `cursive` family, and the server
answered 200 the whole time - so the flagship accessibility font was
simply absent and nothing failed loudly.

These tests check the bytes, not the filename or the HTTP status.
"""

import pathlib
import re
import struct
import sys
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = str(REPO_ROOT / "src")
if SRC not in sys.path:
    sys.path.append(SRC)

from accessible_ide import create_app, routes  # noqa: E402

FONT_DIR = REPO_ROOT / "src" / "accessible_ide" / "assets" / "fonts"
TEMPLATE = REPO_ROOT / "src" / "accessible_ide" / "templates" / "index.html"

# Leading bytes of each real font container format.
FONT_MAGIC = {
    b"\x00\x01\x00\x00": "TrueType",
    b"OTTO": "CFF/OpenType",
    b"ttcf": "TrueType Collection",
    b"wOFF": "WOFF",
    b"wOF2": "WOFF2",
}


def embedded_family_name(path):
    """Read the family name out of a TrueType/OpenType name table."""
    data = path.read_bytes()
    if data[:4] not in (b"\x00\x01\x00\x00", b"OTTO", b"ttcf"):
        return None

    start = struct.unpack(">I", data[12:16])[0] if data[:4] == b"ttcf" else 0
    num_tables = struct.unpack(">H", data[start + 4 : start + 6])[0]

    name_offset = 0
    for index in range(num_tables):
        entry = start + 12 + index * 16
        if data[entry : entry + 4] == b"name":
            name_offset = struct.unpack(">I", data[entry + 8 : entry + 12])[0]
            break
    if not name_offset:
        return None

    count, string_offset = struct.unpack(
        ">HH", data[name_offset + 2 : name_offset + 6]
    )
    found = {}
    for index in range(count):
        record = name_offset + 6 + index * 12
        platform, _enc, _lang, name_id, length, offset = struct.unpack(
            ">HHHHHH", data[record : record + 12]
        )
        if name_id not in (1, 16):
            continue
        raw = data[name_offset + string_offset + offset :][:length]
        try:
            value = raw.decode("utf-16-be") if platform == 3 else raw.decode("latin-1")
        except UnicodeDecodeError:
            continue
        value = value.strip("\x00").strip()
        if value and (name_id not in found or platform == 3):
            found[name_id] = value
    return found.get(16) or found.get(1)


def _group(pattern, text, what):
    """The first capture group of a match that has to be there.

    Written as a function so the tests do not repeat the None check, and
    so a missing match fails as itself rather than as an AttributeError
    three lines later.
    """
    match = re.search(pattern, text)
    if match is None:
        raise AssertionError(what)
    return match.group(1)


def _group_or_none(pattern, text):
    """The first capture group, or None when the pattern simply is not there.

    Some patterns are expected to miss. A font that does not declare a
    weight at all is not an error here, it is just a font this check says
    nothing about.
    """
    match = re.search(pattern, text)
    return None if match is None else match.group(1)


class BundledFontTests(unittest.TestCase):
    def test_every_font_file_is_really_a_font(self):
        fonts = [
            path
            for path in sorted(FONT_DIR.iterdir())
            if path.suffix.lower() in (".ttf", ".otf", ".woff", ".woff2")
        ]
        self.assertTrue(fonts, "no font files found at all")

        for path in fonts:
            with self.subTest(font=path.name):
                head = path.read_bytes()[:4]
                self.assertIn(
                    head,
                    FONT_MAGIC,
                    f"{path.name} is not a font: it starts with {head!r}. "
                    f"It is {path.stat().st_size} bytes and begins "
                    f"{path.read_bytes()[:60]!r}",
                )

    def test_fonts_are_not_trivially_small(self):
        # A real font is tens of kilobytes. A stub or an error page that
        # somehow passed the magic-byte check is still wrong.
        for path in sorted(FONT_DIR.iterdir()):
            if path.suffix.lower() not in (".ttf", ".otf", ".woff", ".woff2"):
                continue
            with self.subTest(font=path.name):
                self.assertGreater(path.stat().st_size, 2000)

    def test_font_family_names_match_the_css(self):
        # The @font-face family name has to match the family inside the
        # file, or the browser downloads the font and then refuses to use
        # it. This is the second half of the OpenDyslexic failure.
        css = TEMPLATE.read_text(encoding="utf-8")
        declared = set(re.findall(r"font-family:\s*'([^']+)'\s*;", css))
        declared |= set(re.findall(r"font-family:\s*'([^']+)',", css))
        self.assertTrue(declared, "no @font-face families found in the template")

        for path in sorted(FONT_DIR.iterdir()):
            if path.suffix.lower() not in (".ttf", ".otf"):
                continue
            with self.subTest(font=path.name):
                family = embedded_family_name(path)
                self.assertIsNotNone(family, f"could not read a family name")
                self.assertIn(
                    family,
                    declared,
                    f"{path.name} contains family {family!r}, which no "
                    f"@font-face declares. Declared: {sorted(declared)}",
                )

    def test_every_listed_font_file_exists(self):
        for key, font in routes.FONTS.items():
            for filename in font["files"]:
                with self.subTest(font=key, file=filename):
                    self.assertTrue(
                        (FONT_DIR / filename).exists(),
                        f"{key} lists {filename}, which is not in {FONT_DIR}",
                    )

    def test_font_families_never_fall_back_to_cursive(self):
        # `cursive` is the browser's handwriting-ish generic. As the last
        # item in a code editor's stack it makes the code very hard to
        # read, and it is what OpenDyslexic silently degraded to.
        for key, font in routes.FONTS.items():
            with self.subTest(font=key):
                last = [part.strip() for part in font["family"].split(",")][-1]
                self.assertNotEqual(last, "cursive")

    def _stack_parts(self, key):
        """The families in a stack, with the CSS quoting removed."""
        return [
            part.strip().strip("'\"")
            for part in routes.FONTS[key]["family"].split(",")
        ]

    def test_every_stack_carries_both_script_fallbacks(self):
        # Mukta carries the Devanagari for Hindi, Almarai the Arabic. They
        # sit in every stack rather than being separate choices, so a reader
        # who picked OpenDyslexic for its Latin still gets readable Hindi
        # instead of boxes.
        for key in routes.FONTS:
            with self.subTest(font=key):
                parts = self._stack_parts(key)
                self.assertIn("Mukta", parts, f"{key} cannot render Devanagari")
                self.assertIn("Almarai", parts, f"{key} cannot render Arabic")

    def test_script_fallbacks_come_after_the_chosen_font(self):
        # The reader's pick has to win for the script it covers. Mukta and
        # Almarai are fallbacks, not overrides.
        for key in routes.FONTS:
            with self.subTest(font=key):
                parts = self._stack_parts(key)
                first_fallback = min(parts.index("Mukta"), parts.index("Almarai"))
                for chosen in parts[:first_fallback]:
                    self.assertNotIn(chosen, ("Mukta", "Almarai"))
                self.assertIn(
                    parts[-1],
                    ("sans-serif", "monospace"),
                    "the stack must still end in a generic family",
                )

    def test_every_bundled_font_is_referenced_by_the_template(self):
        # A font file nobody loads is dead weight in an offline app: it
        # still has to be shipped, downloaded on install, and licence-
        # audited forever. Mukta-ExtraLight sat in the folder for exactly
        # this reason - nothing asks the stack for weight 200.
        css = TEMPLATE.read_text(encoding="utf-8")
        referenced = set(re.findall(r"filename='([^']+)'", css))
        for path in sorted(FONT_DIR.iterdir()):
            if path.suffix.lower() not in (".ttf", ".otf"):
                continue
            with self.subTest(font=path.name):
                self.assertIn(
                    path.name,
                    referenced,
                    f"{path.name} is bundled but no @font-face loads it",
                )

    def test_fonts_endpoint_matches_the_served_files(self):
        app = create_app()
        app.config["TESTING"] = True
        client = app.test_client()

        response = client.get("/api/fonts")
        try:
            self.assertEqual(response.status_code, 200)
            self.assertEqual(sorted(response.get_json()), sorted(routes.FONTS))
        finally:
            response.close()

        # Every font the app claims to bundle must actually be served, and
        # must arrive as font bytes rather than an error page.
        for key, font in routes.FONTS.items():
            for filename in font["files"]:
                with self.subTest(font=key, file=filename):
                    served = client.get(f"/assets/fonts/{filename}")
                    try:
                        self.assertEqual(served.status_code, 200)
                        self.assertIn(
                            served.data[:4],
                            FONT_MAGIC,
                            f"/assets/fonts/{filename} did not return a font",
                        )
                        # Python has no .ttf entry in mimetypes on Windows,
                        # so this has to be asked for explicitly or the font
                        # arrives as application/octet-stream.
                        self.assertEqual(
                            served.mimetype,
                            routes.FONT_MIME_TYPES[pathlib.Path(filename).suffix.lower()],
                        )
                    finally:
                        served.close()


class FontLicensingTests(unittest.TestCase):
    """What the repository is allowed to ship, and what it must not."""

    # Calibri and Arial belong to Microsoft. Bundling them in an
    # open-source project would be a licence breach and would put the
    # public repository at risk, so they are referenced, never shipped.
    PROPRIETARY = {"calibri", "arial", "comic sans ms", "courier new"}

    def test_no_proprietary_font_is_bundled(self):
        for key, font in routes.FONTS.items():
            if key.lower() in self.PROPRIETARY:
                with self.subTest(font=key):
                    self.assertEqual(
                        font["files"],
                        [],
                        f"{key} is a Microsoft font and must not be bundled",
                    )
                    self.assertFalse(font["bundled"])

    def test_system_fonts_are_labelled_as_not_bundled(self):
        for key, font in routes.FONTS.items():
            with self.subTest(font=key):
                # files and bundled have to agree, or the settings panel
                # will tell the reader a font is included when it is not.
                self.assertEqual(bool(font["files"]), font["bundled"])

    def test_every_bundled_font_ships_its_licence(self):
        licences = FONT_DIR / "licenses"
        self.assertTrue(licences.is_dir(), "no licences folder")

        # Matched on the font's own name, not the file name: the file is
        # OpenDyslexic3-Bold.ttf but its licence file is
        # opendyslexic-ofl.txt, and the version suffix is the kind of
        # detail that should not decide a licensing check.
        present = [
            "".join(char for char in path.name.lower() if char.isalnum())
            for path in licences.iterdir()
        ]
        for key, font in routes.FONTS.items():
            if not font["bundled"]:
                continue
            expected = "".join(char for char in key.lower() if char.isalnum())
            with self.subTest(font=key):
                self.assertTrue(
                    any(name.startswith(expected) for name in present),
                    f"{key} is bundled but has no licence file in {licences}. "
                    f"Found: {sorted(present)}",
                )

    def test_a_licence_file_is_not_empty(self):
        licences = FONT_DIR / "licenses"
        for path in sorted(licences.iterdir()):
            with self.subTest(licence=path.name):
                self.assertGreater(path.stat().st_size, 500)
                self.assertIn("Copyright", path.read_text(encoding="utf-8", errors="ignore"))


class DefaultFontTests(unittest.TestCase):
    """What the app shows a reader who has not chosen anything.

    The default has to be a bundled font, or the hosted site and a Linux
    build quietly render in something else while the Windows build looks
    right. It also has to be the same family in the stylesheet, in
    app.js and here, because those three are read independently and a
    mismatch shows as one font on the panel and another on the editor.
    """

    STYLESHEET = REPO_ROOT / "src" / "accessible_ide" / "static" / "css" / "style.css"
    APP_JS = REPO_ROOT / "src" / "accessible_ide" / "static" / "js" / "app.js"

    def _css(self):
        # Comments are stripped first. The token definitions explain what they
        # used to be, and a test should read the rules, not the prose.
        return re.sub(r"/\*.*?\*/", "", self.STYLESHEET.read_text(encoding="utf-8"), flags=re.S)

    def test_the_default_font_is_bundled(self):
        # A default that is not bundled is a default that renders as
        # something else on the hosted site.
        default = routes.DEFAULT_CONFIG["font"]
        self.assertIn(
            default,
            routes.FONTS,
            f"the default font {default!r} is not in the FONTS table",
        )
        self.assertTrue(
            routes.FONTS[default]["bundled"],
            f"the default font {default!r} is not bundled, so it cannot be "
            "relied on to render on the hosted site",
        )

    def test_the_stylesheet_and_app_js_agree_on_the_default(self):
        default = routes.DEFAULT_CONFIG["font"]
        token = _group(
            r"--font-family:\s*([^;]+);",
            self._css(),
            "no --font-family token in style.css",
        )
        self.assertIn(
            f'"{default}"',
            token,
            f"--font-family starts with {token.strip()!r}, so the first "
            f"paint does not use the default font {default!r}",
        )

        app_js = self.APP_JS.read_text(encoding="utf-8")
        families = _group(
            r"DEFAULT_FONT_FAMILY\s*=\s*'([^']+)'",
            app_js,
            "no DEFAULT_FONT_FAMILY in app.js",
        )
        self.assertIn(f'"{default}"', families)

    def _faces(self):
        """Every @font-face in the template, as (family, font-weight).

        Each weight is paired with the family declared above it rather than
        by slicing the block out with a non-greedy brace match. That approach
        stops at the first closing brace, which here is the one inside
        Jinja's url('{{ ... }}'), so every block came back truncated just
        after its src line and reported no weight at all.
        """
        template = TEMPLATE.read_text(encoding="utf-8")
        pattern = re.compile(
            r"font-family:\s*'([^']+)'|font-weight:\s*([^;]+);", flags=re.S
        )
        faces = []
        family = None
        for match in pattern.finditer(template):
            declared, weight = match.group(1), match.group(2)
            if declared is not None:
                family = declared
            elif family is not None:
                faces.append((family, weight.strip()))
        return faces

    def test_a_single_weight_font_is_not_the_default(self):
        # Atkinson Hyperlegible and OpenDyslexic ship Regular and Bold only,
        # declared as font-weight: normal and font-weight: bold. style.css
        # asks for weight 600 in several places, so as the default face the
        # browser has to synthesise that weight and the whole UI renders at
        # a smeared in-between one. A variable font declares a range like
        # "100 900", which is a real axis and is safe to lead with.
        faces = self._faces()
        self.assertTrue(faces, "no @font-face blocks found in the template")

        fixed = set()
        for family, weight in faces:
            is_range = bool(re.fullmatch(r"\d+\s+\d+", weight))
            if not is_range and weight not in ("normal", "bold"):
                continue  # a keyword this test does not reason about
            if not is_range:
                fixed.add(family)

        self.assertNotIn(
            routes.DEFAULT_CONFIG["font"],
            fixed,
            f"the default font {routes.DEFAULT_CONFIG['font']!r} is one of "
            f"{sorted(fixed)}, which declare fixed weights rather than a "
            "variable axis, so the weight 600 the stylesheets ask for has "
            "to be faked by the browser",
        )

    def test_the_check_above_can_actually_see_a_fixed_weight_font(self):
        # A guard that cannot fail is not a guard. Atkinson Hyperlegible
        # and OpenDyslexic are fixed; Lexend and Nunito are variable. If
        # this fails then test_a_single_weight_font_is_not_the_default is
        # comparing against an empty set and passing for the wrong reason.
        faces = self._faces()
        families = {family for family, _ in faces}
        self.assertIn("Atkinson Hyperlegible", families)
        self.assertIn("Nunito", families)

        def is_variable(family):
            return any(
                family == declared and bool(re.fullmatch(r"\d+\s+\d+", weight))
                for declared, weight in faces
            )

        self.assertFalse(
            is_variable("Atkinson Hyperlegible"),
            "Atkinson Hyperlegible should declare fixed weights",
        )
        self.assertTrue(
            is_variable("Nunito"),
            "Nunito should declare a variable weight range",
        )


class MonospaceTests(unittest.TestCase):
    """The code areas that are not the editor.

    These were "Courier New", hardcoded in seven separate rules. Courier
    New is a screen face from the 1980s, thin and widely spaced, and it
    was the first thing on the page that read as unfinished. They now go
    through one token.
    """

    STYLESHEET = REPO_ROOT / "src" / "accessible_ide" / "static" / "css" / "style.css"

    def _rules(self):
        css = re.sub(
            r"/\*.*?\*/", "", self.STYLESHEET.read_text(encoding="utf-8"), flags=re.S
        )
        return re.findall(r"font-family:\s*([^;]+);", css)

    def test_there_is_a_monospace_token(self):
        css = self._css_token_text()
        self.assertIn("--font-mono:", css, "no --font-mono token in style.css")
        value = _group(
            r"--font-mono:\s*([^;]+);",
            css,
            "the --font-mono token is declared but has no value",
        )
        self.assertTrue(
            value.strip().endswith("monospace"),
            "the monospace stack must end in the generic, or a missing "
            f"font gives the reader no monospace at all: {value!r}",
        )

    def _css_token_text(self):
        return re.sub(
            r"/\*.*?\*/", "", self.STYLESHEET.read_text(encoding="utf-8"), flags=re.S
        )

    def test_no_rule_hardcodes_a_specific_monospace(self):
        # Every monospace rule should read the token. A hardcoded name here
        # is how the seven Courier New rules happened in the first place.
        for value in self._rules():
            value = value.strip()
            if value == "var(--font-mono)":
                continue
            if "monospace" not in value:
                continue  # a proportional stack, fine
            self.assertIn(
                "var(--font-mono)",
                value,
                f"monospace rule {value!r} bypasses the --font-mono token",
            )

    def test_courier_new_is_no_longer_used_in_the_stylesheets(self):
        css = self._css_token_text()
        self.assertNotIn(
            "Courier New",
            css,
            "Courier New is back in a rule. It is a Microsoft font and a "
            "1980s screen face; the monospace token should be used instead.",
        )


if __name__ == "__main__":
    unittest.main()
