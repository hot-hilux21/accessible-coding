/* The browser's copy of utils/colour.py.
 *
 * The server pulls a chosen panel colour toward the theme's panel colour until
 * the theme's own text stays readable on it, and that has to happen here too.
 * The reader can change theme without the page reloading, and a colour that is
 * readable on a near-black panel is not readable on a cream one.
 *
 * The two implementations are pinned together by tests/tint_vectors.json,
 * which both test suites read. If they ever disagree, one of them fails
 * rather than the reader seeing a colour that is subtly wrong.
 *
 * Kept as a plain script rather than a module because app.js is served as a
 * plain script, and the harness loads the same files the browser does.
 */

(function (global) {
  'use strict';

  var CHANNEL_WEIGHTS = [0.2126, 0.7152, 0.0722];
  var AA_CONTRAST = 4.5;
  var BISECTION_STEPS = 24;
  // Every float-to-channel conversion goes through round() or clamp(), and
  // neither is spelled out at the call site. That is the whole point: parseHex
  // and toHex used to round and clamp in JavaScript while Python's parse_hex
  // truncated with int() and left the value unclamped, so a float triple came
  // out a channel apart between the two copies and the browser built a colour
  // containing 256. Round has to match colour.py's _round, which sends a tie
  // toward positive infinity. Math.round already does that, so the helper only
  // exists to give the rule a name the two files can be checked against.
  function round(value) {
    return Math.round(value);
  }

  function clamp(value) {
    // A channel inside 0-255. Mirrors Python's _clamp.
    return Math.min(255, Math.max(0, round(value)));
  }

  function parseHex(value) {
    // An [r, g, b] triple is passed straight through, so a caller already
    // holding a parsed colour does not have to turn it back into a string.
    // Python's parse_hex does the same with a tuple, and the two are meant to
    // be interchangeable.
    //
    // Rounded and clamped, not truncated. Python used int() here, which
    // truncated and let an unclamped 255.5 through as a 256 in the browser:
    // two of the four channels agreed and the other two came out a step apart.
    if (Array.isArray(value)) {
      if (value.length !== 3) throw new Error('not a colour: ' + value);
      return [clamp(value[0]), clamp(value[1]), clamp(value[2])];
    }
    var text = String(value == null ? '' : value).trim();
    if (text.charAt(0) !== '#') throw new Error('not a hex colour: ' + value);
    var digits = text.slice(1);
    if (digits.length === 3) {
      digits = digits.charAt(0) + digits.charAt(0)
             + digits.charAt(1) + digits.charAt(1)
             + digits.charAt(2) + digits.charAt(2);
    }
    if (digits.length !== 6 || !/^[0-9a-fA-F]{6}$/.test(digits)) {
      throw new Error('not a hex colour: ' + value);
    }
    return [
      parseInt(digits.slice(0, 2), 16),
      parseInt(digits.slice(2, 4), 16),
      parseInt(digits.slice(4, 6), 16),
    ];
  }

  function toHex(rgb) {
    // Same rounding and clamping as parseHex, and the same rule as Python's
    // to_hex, which is why all three go through clamp() rather than each
    // spelling it out.
    var out = '#';
    for (var i = 0; i < 3; i += 1) {
      var value = clamp(rgb[i]);
      out += (value < 16 ? '0' : '') + value.toString(16);
    }
    return out;
  }

  function toLinear(channel) {
    var value = channel / 255;
    if (value <= 0.04045) return value / 12.92;
    return Math.pow((value + 0.055) / 1.055, 2.4);
  }

  function toSrgb(linear) {
    var clamped = Math.min(1, Math.max(0, linear));
    var value = clamped <= 0.0031308
      ? 12.92 * clamped
      : 1.055 * Math.pow(clamped, 1 / 2.4) - 0.055;
    return clamp(value * 255);
  }

  function luminance(rgb) {
    var total = 0;
    for (var i = 0; i < 3; i += 1) {
      total += CHANNEL_WEIGHTS[i] * toLinear(rgb[i]);
    }
    return total;
  }

  function contrastRatio(a, b) {
    var la = luminance(a);
    var lb = luminance(b);
    return (Math.max(la, lb) + 0.05) / (Math.min(la, lb) + 0.05);
  }

  /* The worst contrast between a background and any of the text colours.
   * The worst, not the average: one unreadable token colour is enough to make
   * the panel unusable, and it is usually the quieter --muted that fails.
   */
  function readableOn(textColours, background) {
    var worst = Infinity;
    for (var i = 0; i < textColours.length; i += 1) {
      worst = Math.min(worst, contrastRatio(textColours[i], background));
    }
    return worst;
  }

  /* The tint made readable on this panel, keeping as much colour as it can.
   *
   * A tint that already clears AA is returned untouched, so a reader who picks
   * a colour they can read sees that colour.
   *
   * Failing that it is faded toward the panel until every text colour clears
   * AA, and no further. The panel is the anchor because it is safe by
   * construction - the themes were measured against their own text - so there
   * is always a colour to reach.
   *
   * Fading rather than moving to a computed target lightness is deliberate.
   * Contrast is a function of luminance alone, so the mix toward the panel is
   * monotonic in contrast and bisection lands on the exact boundary. The
   * earlier version computed a band of legal luminances from neutral greys,
   * which quietly broke the pastel theme: its panel and its muted text are
   * both warm, so warm against warm reads worse than grey against warm at the
   * same lightness, and the panel ended up outside the band its own colours
   * defined. Measuring the real contrast of the real colours is the only check
   * that cannot drift from what the reader actually sees.
   */
  function tintReadableOn(tint, panel, textColours) {
    var t = parseHex(tint);
    var p = parseHex(panel);
    if (!textColours || !textColours.length) return t;

    if (readableOn(textColours, t) >= AA_CONTRAST) return t;

    // The candidate channel goes through clamp, so it is rounded the same way
    // Python's _round rounds it and held inside 0-255. Python's own round()
    // rounds ties to even and would not agree here, which is why colour.py
    // defines _round rather than using the builtin. A sweep of several thousand
    // tints found 12 that landed exactly on a tie and came out a channel apart
    // between the two copies: both passed the contrast check, so nothing looked
    // broken, but a reader who switched theme in the browser got panels a step
    // from the server's. Those 12 are the vectors marked "tie" in
    // tint_vectors.json.
    //
    // Mix is 0 for the tint itself and 1 for the panel. The panel always
    // passes, so the search is bounded on a known-good side.
    var lowMix = 0;
    var highMix = 1;
    var best = null;
    for (var pass = 0; pass < BISECTION_STEPS; pass += 1) {
      var middle = (lowMix + highMix) / 2;
      var candidate = [];
      for (var i = 0; i < 3; i += 1) {
        candidate.push(clamp(t[i] * (1 - middle) + p[i] * middle));
      }
      if (readableOn(textColours, candidate) >= AA_CONTRAST) {
        // Good enough to read. Remember it and try keeping more colour.
        best = candidate;
        highMix = middle;
      } else {
        lowMix = middle;
      }
    }
    return best === null ? p : best;
  }

  function safePanelTint(tintHex, panelHex, textColours) {
    // Blank, or only whitespace, means "follow the theme", which needs no
    // arithmetic. Python's safe_panel_tint treats a blank the same way, so a
    // hand-edited config or a space in the colour box is not a broken colour
    // in either copy.
    if (!String(tintHex == null ? '' : tintHex).trim()) return '';
    var panel = parseHex(panelHex);
    // Without the theme's text colours there is nothing to check against, so
    // the panel is used rather than a guess that could be unreadable.
    if (!textColours || !textColours.length) return toHex(panel);
    return toHex(tintReadableOn(parseHex(tintHex), panel, textColours.map(parseHex)));
  }

  /* Two colours mixed by t (0 is all a, 1 is all b). A straight channel mix
   * in sRGB space, the same arithmetic the tint search uses, so a derived
   * colour and the search that checks it agree about what "toward" means.
   * Mirrors mix_hex in utils/colour.py.
   */
  function mixHex(a, b, t) {
    a = parseHex(a);
    b = parseHex(b);
    return toHex([
      round(a[0] * (1 - t) + b[0] * t),
      round(a[1] * (1 - t) + b[1] * t),
      round(a[2] * (1 - t) + b[2] * t)
    ]);
  }

  /* A text colour made readable on a background, keeping its hue.
   *
   * A colour that already clears AA is returned untouched. One that does not
   * is mixed toward the far extreme (white on a dark background, black on a
   * light one) until it does, and no further. Mixing toward the background
   * would be wrong: a colour picked on the same side as the background only
   * gets closer to it, and the search has no way out. The far extreme is the
   * anchor because it always clears, and contrast is monotonic along the mix
   * once the colour passes the background, so bisection lands on the exact
   * boundary. Mirrors readable_text_on in utils/colour.py.
   */
  function readableTextOn(background, colour) {
    var bg = parseHex(background);
    colour = parseHex(colour);
    if (contrastRatio(colour, bg) >= AA_CONTRAST) return toHex(colour);
    var far = contrastRatio([255, 255, 255], bg) >= contrastRatio([0, 0, 0], bg)
      ? [255, 255, 255] : [0, 0, 0];
    var lowMix = 0.0, highMix = 1.0, best = null;
    for (var pass = 0; pass < BISECTION_STEPS; pass += 1) {
      var middle = (lowMix + highMix) / 2;
      var candidate = [
        round(colour[0] * (1 - middle) + far[0] * middle),
        round(colour[1] * (1 - middle) + far[1] * middle),
        round(colour[2] * (1 - middle) + far[2] * middle)
      ];
      if (contrastRatio(candidate, bg) >= AA_CONTRAST) {
        best = candidate;
        highMix = middle;
      } else {
        lowMix = middle;
      }
    }
    return toHex(best || far);
  }

  global.AccessibleTint = {
    parseHex: parseHex,
    toHex: toHex,
    toLinear: toLinear,
    toSrgb: toSrgb,
    luminance: luminance,
    contrastRatio: contrastRatio,
    readableOn: readableOn,
    tintReadableOn: tintReadableOn,
    safePanelTint: safePanelTint,
    mixHex: mixHex,
    readableTextOn: readableTextOn,
  };
}(typeof globalThis !== 'undefined' ? globalThis : this));
