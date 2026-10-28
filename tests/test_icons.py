import pathlib
import sys
import unittest

SRC = str(pathlib.Path(__file__).resolve().parent.parent / "src")
if SRC not in sys.path:
    sys.path.append(SRC)

from accessible_ide import icons  # noqa: E402


class IconTests(unittest.TestCase):
    def test_every_icon_draws_with_current_colour(self):
        for name in icons.sprite_names():
            with self.subTest(name=name):
                markup = str(icons.icon(name))
                self.assertIn('class="icon icon-', markup)
                self.assertIn('stroke="currentColor"', markup)
                self.assertIn('aria-hidden="true"', markup)

    def test_a_typo_is_loud(self):
        with self.assertRaises(KeyError):
            icons.icon('not-an-icon')


if __name__ == '__main__':
    unittest.main()
