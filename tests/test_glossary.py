"""Tests for the in-app Python dictionary.

The entries are copied from the README, so the thing worth testing is that the
copy is still true. These read the Markdown table back out of the README and
compare it against the module, heading by heading and row by row, in order.
A word edited in one place and not the other fails here, rather than being
found by a reader who has been told two different things.

The rest is the rendering. The entries carry backticks, inline_code turns the
pairs into <code>, and nothing else in an entry may become markup.
"""

import unittest
from pathlib import Path

from markupsafe import Markup

from accessible_ide import glossary

ROOT = Path(__file__).resolve().parent.parent
README = ROOT / "README.md"

START = "## Python dictionary"
# The columns the two tables in this section use for their headings. Both
# tables are two wide, so the heading text is the only thing that says a row
# is a heading and not an entry.
HEADINGS = ("Command", "What you typed")


def readme_dictionary():
    """The dictionary section alone, up to the next top-level heading.

    Bounded rather than scanning the whole README, because other sections have
    tables too and a row from one of those is not a dictionary entry.
    """
    text = README.read_text(encoding="utf-8")
    start = text.index(START)
    rest = text[start:]
    return rest[:rest.index("\n## ", 1)]


def readme_headings(section):
    return [line[4:].strip() for line in section.splitlines()
            if line.startswith("### ")]


def readme_rows(section):
    """Every (what you type, what it means) pair in the section's tables."""
    rows = []
    for line in section.splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) != 2:
            continue
        if cells[0] in HEADINGS:
            continue
        # The --- divider under each heading.
        if cells[0] and set(cells[0]) <= set("- "):
            continue
        rows.append((cells[0], cells[1]))
    return rows


def module_rows():
    return [(command, meaning)
            for section in glossary.SECTIONS
            for command, meaning in section["rows"]]


class ReadmeStaysInStep(unittest.TestCase):
    """The README and the module hold the same words, in the same order."""

    @classmethod
    def setUpClass(cls):
        cls.section = readme_dictionary()

    def test_the_tables_were_actually_found(self):
        # A parse that quietly stopped matching would leave the comparisons
        # below passing on two empty lists, which is the one way these tests
        # could fall silent without being right.
        self.assertGreaterEqual(len(readme_rows(self.section)), 30)
        self.assertGreaterEqual(len(readme_headings(self.section)), 8)

    def test_section_headings_match_in_order(self):
        self.assertEqual(
            [section["title"] for section in glossary.SECTIONS],
            readme_headings(self.section),
        )

    def test_every_row_matches_in_order(self):
        self.assertEqual(module_rows(), readme_rows(self.section))

    def test_no_section_is_empty(self):
        for section in glossary.SECTIONS:
            with self.subTest(section=section["title"]):
                self.assertTrue(section["rows"])


class EntryData(unittest.TestCase):
    def test_backticks_are_paired(self):
        # inline_code works in pairs. An odd count is a mistake in the data,
        # and this is where it is caught rather than on the page.
        for command, meaning in module_rows():
            with self.subTest(command=command):
                self.assertEqual(command.count("`") % 2, 0)
                self.assertEqual(meaning.count("`") % 2, 0)

    def test_nothing_is_blank(self):
        for section in glossary.SECTIONS:
            with self.subTest(section=section["title"]):
                self.assertTrue(section["title"].strip())
                for command, meaning in section["rows"]:
                    self.assertTrue(command.strip())
                    self.assertTrue(meaning.strip())

    def test_no_em_dash(self):
        # This project writes the sentence a colleague would write. An em dash
        # in a glossary entry is the tell that it was not.
        for command, meaning in module_rows():
            with self.subTest(command=command):
                self.assertNotIn("\u2014", command)
                self.assertNotIn("\u2014", meaning)

    def test_the_count_is_the_number_of_rows(self):
        self.assertEqual(glossary.entry_count(), len(module_rows()))


class InlineCode(unittest.TestCase):
    def test_a_pair_becomes_a_code_element(self):
        self.assertEqual(
            str(glossary.inline_code("use `print` here")),
            "use <code>print</code> here",
        )

    def test_several_pairs_all_become_code(self):
        self.assertEqual(
            str(glossary.inline_code("`a` and `b`")),
            "<code>a</code> and <code>b</code>",
        )

    def test_text_without_backticks_is_left_alone(self):
        self.assertEqual(str(glossary.inline_code("plain words")), "plain words")

    def test_markup_in_the_text_is_escaped(self):
        # Escaping happens before the tag is inserted, so an entry cannot
        # introduce markup of its own.
        self.assertEqual(
            str(glossary.inline_code("<b>&</b>")),
            "&lt;b&gt;&amp;&lt;/b&gt;",
        )
        self.assertEqual(
            str(glossary.inline_code("<b>`x`</b>")),
            "&lt;b&gt;<code>x</code>&lt;/b&gt;",
        )

    def test_the_result_is_markup(self):
        # Not a plain string: Jinja escapes a string, which would print the
        # tags into the page as words.
        self.assertIsInstance(glossary.inline_code("`x`"), Markup)
