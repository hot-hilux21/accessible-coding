"""Generate the two pictures the Inno Setup wizard shows.

Both are drawn from the app's own palette (static/css/style.css, the :root
block) so the installer and the program look like one product rather than two
that happen to share a name. Nothing here is decorative for its own sake: the
panel carries the name and the mark, and the mark is the same tile as the app
icon, which is already the thing a reader learns to recognise.

  installer/assets/wizard-image.png   the tall panel beside the Welcome and
                                      Finished pages (aspect 164:314)
  installer/assets/wizard-small.png   the square mark in the wizard header

Run from anywhere:  python scripts/make_wizard_images.py
Needs Pillow, the same as scripts/make_icon.py. Pillow is a tool for whoever
edits these files, not something the app or the installer ships.
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
from make_icon import draw_icon  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
ASSETS = REPO / "installer" / "assets"
FONTS = REPO / "src" / "accessible_ide" / "assets" / "fonts"

# The app's own tokens, so the installer cannot drift from the product.
BG = (13, 13, 13, 255)         # --bg      #0D0D0D
FG = (255, 255, 255, 255)      # --fg      #FFFFFF
MUTED = (170, 170, 170, 255)   # --muted   #AAAAAA

# 164:314 is the shape Inno stretches the panel to, drawn at 200% of Inno's
# own default area so it stays sharp on a high-DPI display and simply scales
# down on a normal one. 147x147 is Inno's own size for the header mark.
PANEL = (430, 824)
SMALL = 147

WORDMARK = "AccessibleCoding"
TAGLINE = "Python editor"

BOLD = "AtkinsonHyperlegible-Bold.ttf"
REGULAR = "AtkinsonHyperlegible-Regular.ttf"


def _font(name, size):
    return ImageFont.truetype(str(FONTS / name), size)


def _fit(draw, text, name, max_width, start):
    """The largest size at or below start whose text fits in max_width.

    The wordmark is one long word with no natural break, so it has to be
    measured rather than guessed: a size that fits at one DPI setting is not
    the size that fits the picture.
    """
    for size in range(start, 8, -1):
        font = _font(name, size)
        if draw.textlength(text, font=font) <= max_width:
            return font
    return _font(name, 8)


def build_panel():
    """The tall panel: mark over the name over one plain line."""
    width, height = PANEL
    img = Image.new("RGBA", PANEL, BG)
    draw = ImageDraw.Draw(img)

    icon_size = 200
    mark = _fit(draw, WORDMARK, BOLD, width - 80, 46)
    tag = _font(REGULAR, 26)

    mark_height = mark.getbbox(WORDMARK)[3]
    tag_height = tag.getbbox(TAGLINE)[3]
    gap_icon_mark = 64
    gap_mark_tag = 14

    block = icon_size + gap_icon_mark + mark_height + gap_mark_tag + tag_height
    y = (height - block) // 2

    img.alpha_composite(draw_icon(icon_size), ((width - icon_size) // 2, y))
    y += icon_size + gap_icon_mark

    draw.text(
        ((width - draw.textlength(WORDMARK, font=mark)) / 2, y),
        WORDMARK, font=mark, fill=FG,
    )
    y += mark_height + gap_mark_tag

    draw.text(
        ((width - draw.textlength(TAGLINE, font=tag)) / 2, y),
        TAGLINE, font=tag, fill=MUTED,
    )
    return img


def build_small():
    """The header mark: the app icon, unchanged, on a transparent square."""
    return draw_icon(SMALL)


if __name__ == "__main__":
    ASSETS.mkdir(parents=True, exist_ok=True)
    build_panel().save(ASSETS / "wizard-image.png")
    build_small().save(ASSETS / "wizard-small.png")
    print(f"wizard images written to {ASSETS}")
