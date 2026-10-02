"""Working out a panel colour that keeps the words on it readable.

The reader picks any colour they like for the panels. That is the point of
offering them a picker. It is also a problem: the panels are already
translucent, so the colour behind the text is a blend of whatever the reader
chose and whatever is on the far side of it. Choose badly and the text stops
being readable, which for this app is the one thing that must not happen.

The answer is not to refuse the colour. A tint that already reads is used
exactly as chosen. One that does not is faded toward the theme's panel colour
until every one of that theme's text colours clears 4.5:1 against it, and no
further. The panel is the anchor because it is safe by construction: the themes
were measured against their own text.

Measuring the real contrast of the real colours is the whole trick. An earlier
version computed a *band* of legal background lightnesses by walking a neutral
grey ramp, then scaled a tint to land inside it. That looks tidier and is
wrong: contrast depends on luminance alone, so the band is the right idea, but
a grey ramp overstates the room available when the panel and its text are both
warm, as they are in the pastel theme. Warm against warm reads worse than grey
against warm at the same lightness, and the panel ended up just outside the
band its own colours defined. Every tint then targeted an unreachable lightness
and came back as the panel. On pastel that was every colour the picker offered.

Fading toward the panel rather than aiming at a computed lightness also makes
the search well behaved: contrast is monotonic along that path, so bisection
lands on the exact boundary instead of hunting for a target it may not be able
to reach.

The same maths is done in the browser (static/js/tint.js) so a theme change
can be reflected without a round trip to the server. The two are pinned to
one another by tests/tint_vectors.json, which both test suites read. That
pinning has to include how values are rounded, because the two languages round
differently by default - see _round below.
"""

import math

# The three weights the WCAG contrast formula uses, in the order it names
# them: red, green, blue.
CHANNEL_WEIGHTS = (0.2126, 0.7152, 0.0722)

# The contrast ratio the app promises to hold everywhere, from WCAG 2.1 AA for
# normal-sized text. This is the number a custom panel colour has to clear.
AA_CONTRAST = 4.5

# Bisection needs a fixed number of passes because the search is bounded by the
# panel rather than by a tolerance that is guaranteed to be reached. Twenty-four
# passes narrows the mix to well under one 8-bit colour step, so the answer is
# the same colour either side of the rounding.
_BISECTION_STEPS = 24


def _round(value):
    """Round to the nearest whole channel, ties going up.

    Not Python's ``round``, which rounds a tie to the even number: it turns
    2.5 into 2 while JavaScript's ``Math.round`` turns it into 3. The two
    implementations of this maths have to give the same colour for the same
    input, or a reader who switches theme in the browser gets panels a step
    away from the ones the server painted.

    A sweep of several thousand tints found 12 where the difference showed, all
    of them landing exactly on a tie. Both answers passed the contrast check, so
    nothing looked broken - the panels just quietly disagreed. Those 12 are
    pinned in tests/tint_vectors.json, marked "tie", because every other case
    gives the same colour either way and cannot catch this.

    ``math.floor(value + 0.5)`` matches ``Math.round`` for every input,
    negatives included, because it rounds a tie toward positive infinity.

    Every conversion between a float and a whole channel goes through here, not
    through ``round``, so the two copies agree on all of them rather than only on
    the one in the bisection.
    """
    return int(math.floor(value + 0.5))


def _clamp(channel):
    """A channel inside the 0-255 range. Shared with parseHex in tint.js."""
    return min(255, max(0, _round(channel)))


def parse_hex(value):
    """"#abc" or "#aabbcc" to (r, g, b). Raises ValueError on anything else.

    An (r, g, b) tuple is passed straight through, so the test suite and any
    caller holding a parsed colour do not have to turn it back to a string
    first.

    The triple branch rounds and clamps rather than truncating, to match
    parseHex in tint.js. The two are documented as interchangeable, so they have
    to be: int() truncates and does not clamp, which made a float triple come out
    a channel apart and let the browser build a colour with a 256 in it.
    """
    if isinstance(value, (tuple, list)):
        if len(value) != 3:
            raise ValueError(f"not a colour: {value!r}")
        return tuple(_clamp(channel) for channel in value)
    text = (value or "").strip()
    if not text.startswith("#"):
        raise ValueError(f"not a hex colour: {value!r}")
    digits = text[1:]
    if len(digits) == 3:
        digits = "".join(char * 2 for char in digits)
    if len(digits) != 6 or any(char not in "0123456789abcdefABCDEF" for char in digits):
        raise ValueError(f"not a hex colour: {value!r}")
    return tuple(int(digits[i : i + 2], 16) for i in (0, 2, 4))


def to_hex(rgb):
    """(r, g, b) back to "#rrggbb".

    Rounds and clamps the same way parseHex does, for the same reason: this and
    toHex in tint.js are meant to be interchangeable, and the float case is
    where that stopped being true.
    """
    return "#" + "".join(f"{_clamp(c):02x}" for c in rgb)


def to_linear(channel):
    """One 0-255 channel to the linear form the luminance formula wants.

    This is the sRGB transfer function. It matters here because a panel's
    luminance is not its brightness: #808080 looks mid-grey but sits much
    closer to black than to white, and treating it as arithmetic would put
    every panel in the wrong place.
    """
    value = channel / 255
    if value <= 0.04045:
        return value / 12.92
    return ((value + 0.055) / 1.055) ** 2.4


def to_srgb(linear):
    """The same curve in reverse, returning a 0-255 channel.

    Clamped through _clamp, matching toSrgb in tint.js. Builtin's round() was
    here once, which rounds a tie to even while the browser's Math.round sends
    it up: the two copies of the sRGB curve disagreed on exactly the ties, the
    same way the tint maths did.
    """
    linear = min(1.0, max(0.0, linear))
    if linear <= 0.0031308:
        value = 12.92 * linear
    else:
        value = 1.055 * linear ** (1 / 2.4) - 0.055
    return _clamp(value * 255)


def luminance(rgb):
    """The relative luminance of a colour, 0.0 (black) to 1.0 (white)."""
    return sum(weight * to_linear(channel) for weight, channel in zip(CHANNEL_WEIGHTS, rgb))


def contrast_ratio(a, b):
    """The WCAG 2.1 contrast ratio between two colours, 1.0 to 21.0."""
    la, lb = luminance(a), luminance(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def readable_on(text_colours, background):
    """The worst contrast between ``background`` and any of ``text_colours``."""
    return min(contrast_ratio(text, background) for text in text_colours)


def tint_readable_on(tint, panel, text_colours):
    """``tint`` made readable on this panel, keeping as much colour as it can.

    A tint that already clears AA against every text colour is returned
    untouched, so the reader gets exactly the colour they asked for. That is the
    common case and it is the point: the app is a tool, and a reader who picks
    a colour they can read should see that colour.

    Failing that, the tint is faded toward the panel until every text colour
    clears AA, and no further. The panel is the anchor because it is safe by
    construction - the themes were measured against their own text - so it is
    always a colour we can reach.

    Fading, rather than moving to a computed target lightness, is deliberate.
    Contrast is a function of luminance alone, so the mix toward the panel is
    monotonic in contrast and bisection lands on the exact boundary. The
    earlier approach of computing a legal band of luminances and scaling to it
    looked tidier and failed on warm themes: it measured the band using neutral
    greys, but the pastel panel and its muted text are both warm, and warm
    against warm reads worse than grey against warm at the same lightness. That
    put the panel just outside the band its own colours defined, every tint
    targeted an unreachable lightness, and the whole picker collapsed back to
    the panel colour. Measuring the real contrast of the real colours is the
    only check that cannot drift from what the reader actually sees.
    """
    tint = parse_hex(tint)
    panel = parse_hex(panel)
    texts = [parse_hex(value) for value in text_colours]
    if not texts:
        return tuple(int(channel) for channel in tint)

    if readable_on(texts, tint) >= AA_CONTRAST:
        return tuple(int(channel) for channel in tint)

    # Mix is 0 for the tint itself and 1 for the panel. The panel always passes,
    # so the search is bounded on a known-good side.
    low_mix, high_mix = 0.0, 1.0
    best = None
    for _ in range(_BISECTION_STEPS):
        middle = (low_mix + high_mix) / 2
        candidate = tuple(
            _round(tint[i] * (1 - middle) + panel[i] * middle) for i in range(3)
        )
        if readable_on(texts, candidate) >= AA_CONTRAST:
            # Good enough to read. Remember it and try keeping more colour.
            best = candidate
            high_mix = middle
        else:
            low_mix = middle
    return best if best is not None else tuple(int(channel) for channel in panel)


def safe_panel_tint(tint_hex, panel_hex, text_colours=None):
    """The saved colour, or "" when the reader is following the theme.

    A blank answer means "use whatever the theme uses", which is the default
    and needs no arithmetic at all.

    ``text_colours`` is the theme's own ``--fg``, ``--muted`` and ``--error-fg``.
    Without it there is nothing to check against, so the panel colour is
    returned: the reader asked for something, but the app cannot show whether
    it is readable, and guessing risks text that cannot be read.
    """
    # Whitespace is "follow the theme" too. A hand-edited config or a reader
    # who typed a space into the colour box means the same thing as an empty
    # field, and treating it as a broken colour would fail the save.
    if not str(tint_hex or "").strip():
        return ""
    panel = parse_hex(panel_hex)
    if not text_colours:
        return to_hex(panel)
    return to_hex(tint_readable_on(tint_hex, panel, text_colours))