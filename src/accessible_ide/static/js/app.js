/* ============================================================
   AccessibleIDE - Frontend logic
   CodeMirror editor, code runner, config persistence, TTS
   ============================================================ */

(function () {
  'use strict';

  // ---------- Translations ----------
  // The server renders the page in the chosen language and embeds the same
  // catalogue here, so every string below comes from one JSON file rather
  // than being written out twice. A missing key shows the key itself, which
  // is deliberate: tests/test_i18n.py fails on that, and a reader would
  // rather see a gap than silently get English in the middle of Hindi.
  var CATALOGUE = {};
  var META = { locale: 'en', direction: 'ltr' };
  // Each theme's panel colour and the text colours on it, as
  // { theme: { panel: '#rrggbb', texts: [fg, muted, error-fg] } }.
  //
  // Embedded in the page rather than fetched, because the tint has to be right
  // the first time it is painted. /api/themes may not have answered yet, and a
  // tint mixed against a placeholder background is unreadable.
  var PANEL_INFO = {};
  try {
    CATALOGUE = JSON.parse(document.getElementById('i18n-data').textContent) || {};
    META = JSON.parse(document.getElementById('i18n-meta').textContent) || META;
  } catch (err) {
    // No embedded catalogue: fall back to whatever the server already put
    // in the page. The page still works, just without JS-side strings.
  }

  try {
    PANEL_INFO = JSON.parse(
      document.getElementById('panel-info').textContent
    ) || {};
  } catch (err) {
    PANEL_INFO = {};
  }

  function t(key) {
    var text = CATALOGUE[key];
    if (typeof text !== 'string') return key;
    var args = Array.prototype.slice.call(arguments, 1);
    for (var i = 0; i < args.length; i++) {
      text = text.split('{' + i + '}').join(args[i]);
    }
    return text;
  }

  // ---------- Elements ----------
  var editorEl = document.getElementById('editor');
  var outputEl = document.getElementById('output');
  var errorPanel = document.getElementById('error-panel');
  var errorMessage = document.getElementById('error-message');
  var btnRun = document.getElementById('btn-run');
  var btnClear = document.getElementById('btn-clear');
  var btnTts = document.getElementById('tts-toggle');
  var btnSave = document.getElementById('btn-save');
  var btnOpen = document.getElementById('btn-open');
  var btnReadLine = document.getElementById('btn-read-line');
  var fileInput = document.getElementById('file-input');
  var fontSelect = document.getElementById('font-select');
  var fontSize = document.getElementById('font-size');
  var fontSizeLabel = document.getElementById('font-size-label');
  var lineHeight = document.getElementById('line-height');
  var lineHeightLabel = document.getElementById('line-height-label');
  var letterSpacing = document.getElementById('letter-spacing');
  var letterSpacingLabel = document.getElementById('letter-spacing-label');
  var blurIntensity = document.getElementById('blur-intensity');
  var blurIntensityLabel = document.getElementById('blur-intensity-label');
  var blurField = document.getElementById('blur-field');
  var themeSelect = document.getElementById('theme-select');
  var contrastSelect = document.getElementById('contrast-select');
  var focusMode = document.getElementById('focus-mode');
  var ttsVoice = document.getElementById('tts-voice');
  var ttsRate = document.getElementById('tts-rate');
  var ttsRateLabel = document.getElementById('tts-rate-label');
  var ttsVoiceGenderEl = document.getElementById('tts-voice-gender');
  var ttsHoverScopeEl = document.getElementById('tts-hover-scope');
  var ttsHoverDelay = document.getElementById('tts-hover-delay');
  var ttsHoverDelayLabel = document.getElementById('tts-hover-delay-label');
  var ttsClickEl = document.getElementById('tts-click');
  var ttsClickState = document.getElementById('tts-click-state');
  var ttsState = document.getElementById('tts-state');
  var btnReduceMotion = document.getElementById('reduce-motion');
  var reduceMotionState = document.getElementById('reduce-motion-state');
  var btnTestVoice = document.getElementById('btn-test-voice');
  var autoUpdateEl = document.getElementById('auto-update-toggle');
  var autoUpdateState = document.getElementById('auto-update-state');
  var btnCheckUpdate = document.getElementById('btn-check-update');
  var updateStatus = document.getElementById('update-status');
  var updateVersion = document.getElementById('update-version');
  var updateInstallRow = document.getElementById('update-install-row');
  var btnInstallUpdate = document.getElementById('btn-install-update');
  var updateChannelEl = document.getElementById('update-channel');
  var settingsDialog = document.getElementById('settings-dialog');
  var btnSettings = document.getElementById('btn-settings');
  var btnSettingsClose = document.getElementById('btn-settings-close');
  var settingsStatus = document.getElementById('settings-status');
  var btnQuit = document.getElementById('btn-quit');
  var fontBundledNote = document.getElementById('font-bundled-note');
  var sampleText = document.getElementById('sample-text');
  var fontPreview = document.getElementById('font-preview');
  var fontPreviewText = document.getElementById('font-preview-text');
  var previewStatus = document.getElementById('preview-status');
  var highlightColorHex = document.getElementById('highlight-color-hex');
  var highlightColorPicker = document.getElementById('highlight-color-picker');
  var highlightError = document.getElementById('highlight-error');
  var highlightStatus = document.getElementById('highlight-status');
  var btnResetHighlight = document.getElementById('btn-reset-highlight');
  var languageSelect = document.getElementById('language-select');
  // The first-run setup screen. These are null once the reader has
  // finished it, because the server stops rendering it - so every use
  // below has to cope with that, and none of it may run at all.
  var setupDialog = document.getElementById('setup-dialog');
  var setupProgress = document.getElementById('setup-progress');
  var setupStatus = document.getElementById('setup-status');
  var setupBack = document.getElementById('setup-back');
  var setupNext = document.getElementById('setup-next');
  var setupSkip = document.getElementById('setup-skip');
  var btnSetupAgain = document.getElementById('btn-setup-again');
  var btnResetConfig = document.getElementById('btn-reset-config');

  var body = document.body;
  var ttsEnabled = btnTts.getAttribute('aria-checked') === 'true';
  // True, false, or null while the reader has not chosen and the system
  // preference is standing in.
  var reduceMotion = null;
  var accessCode = localStorage.getItem('accessible_ide_code') || '';
  var settingsOpener = null;
  var speechRate = 0.9;
  var speechVoiceName = '';
  var ttsHoverScopeValue = 'controls';
  var ttsHoverDelayMs = 600;
  var ttsClickToSpeak = true;
  var ttsVoiceGenderValue = 'male';

  // The blur slider only means something while the "fade the other
  // lines" focus mode is on, so it is disabled rather than hidden -
  // hidden would make the panel jump around as you switch modes.
  function syncBlurField() {
    blurField.classList.toggle('is-disabled', focusMode.value !== 'lines');
    blurIntensity.disabled = focusMode.value !== 'lines';
  }

  function promptForAccessCode() {
    var code = window.prompt(t('error.access_code_prompt'));
    if (code) {
      accessCode = code;
      localStorage.setItem('accessible_ide_code', code);
      return true;
    }
    return false;
  }

  // ---------- CodeMirror setup ----------
  var editor = CodeMirror(editorEl, {
    mode: 'python',
    lineNumbers: true,
    matchBrackets: true,
    styleActiveLine: true,
    indentUnit: 4,
    tabSize: 4,
    indentWithTabs: false,
    lineWrapping: true,
    autofocus: true,
    value: '# Welcome to AccessibleIDE!\n# Write Python code and press Run (or Ctrl+Enter).\n\nprint("Hello, world!")\n\nfor i in range(3):\n    print("Counting:", i)\n'
  });

  // ---------- Theme colours ----------
  // The palettes live on the server (routes.THEMES) and arrive from
  // /api/themes. Keeping one copy means the code colours can never drift
  // away from the colours in style.css. Until the fetch lands we fall
  // back to the current theme's background so the editor never flashes
  // white.
  var themePalette = { bg: '#0b0b0b', fg: '#ffffff' };
  var contrastMode = 'normal';

  function fetchThemes() {
    return fetch('/api/themes')
      .then(function (res) { return res.json(); })
      .then(function (data) {
        Object.keys(data).forEach(function (key) {
          themePalette[key] = data[key];
        });
        populateThemeSelect(data);
        applyTheme(themeSelect.value);
      })
      .catch(function () {
        // Offline: the editor keeps its neutral fallback colours.
      });
  }

  function populateThemeSelect(themes) {
    var current = themeSelect.value || body.getAttribute('data-theme');
    themeSelect.innerHTML = '';
    Object.keys(themes).forEach(function (key) {
      var option = document.createElement('option');
      option.value = key;
      // Theme names are proper-noun-ish labels the reader has to scan, so
      // they come from the catalogue like every other visible word. The
      // server name is the fallback for a theme added without a translation.
      var translated = CATALOGUE['theme.' + key];
      option.textContent = typeof translated === 'string' ? translated : themes[key].name;
      if (key === current) option.selected = true;
      themeSelect.appendChild(option);
    });
  }

  // Extra-high contrast pushes the token colours apart without changing
  // the hue, so a reader who needs more separation gets it without
  // having to learn a new colour scheme.
  function contrastAdjust(hex) {
    if (contrastMode !== 'high') return hex;
    var c = contrastPalette[themeSelect.value] || contrastPalette.high;
    return c[hex] || hex;
  }

  // High-contrast remaps, keyed by the exact base hex so a palette change
  // on the server can never silently skip a colour here. Each target is
  // pushed further from its background, not re-hued, so the theme still
  // looks like itself. Verified by tests/test_contrast.py.
  // Keys cover fg, gutter_fg and every syntax colour.
  var contrastPalette = {
    'high-contrast': {
      '#ffffff': '#ffffff', '#a8a8a8': '#d0d0d0', '#e8e8e8': '#ffffff',
      '#93e6a8': '#c9f5d6', '#ff9a9a': '#ffc9c9', '#93d4ff': '#c9e9ff',
      '#b4b4b4': '#e0e0e0', '#ffd93d': '#ffe98a'
    },
    dark: {
      '#e6e6e6': '#ffffff', '#98a0a8': '#c0c8d0',
      '#b9d99f': '#d6efc4', '#8fc0f5': '#c2ddff', '#93a18d': '#bccbb5',
      '#e3c583': '#f5e3bd', '#8ad4e8': '#c4eef7', '#c8cfd6': '#e4e9ee',
      '#c2cad2': '#dee4ea', '#dde2e8': '#f2f5f8'
    },
    pastel: {
      '#453f3a': '#000000', '#6b6258': '#4a443c',
      '#9a4a12': '#6d300a', '#427a20': '#2c5414', '#6f675c': '#4e4840',
      '#8a6412': '#5e440b', '#1f6a94': '#144a67', '#3a4a52': '#26333a',
      '#584f47': '#3a342e'
    },
    light: {
      '#2b2b2b': '#000000', '#565656': '#3a3a3a',
      '#7a1fa2': '#5c1478', '#1b6b2f': '#114a1f', '#5c5c5c': '#3d3d3d',
      '#a03000': '#702100', '#0057b8': '#003d80', '#3d3d3d': '#262626',
      '#4a4a4a': '#333333'
    },
    ocean: {
      '#e8eef7': '#f4f8fc', '#9fb0c4': '#b8c6d6',
      '#8fc7ff': '#a8d4ff', '#a8e6c1': '#c2f0d4', '#8fa3b8': '#a8b8c8',
      '#ffd98a': '#ffe6ab', '#7fd4ff': '#9adfff', '#dbe6f2': '#eaf1f8',
      '#b8c8da': '#ccd8e6', '#c2d0e0': '#d4deea'
    },
    forest: {
      '#e6efe6': '#f2f8f2', '#9cb3a0': '#b4c8b8',
      '#a8e6a8': '#c2f0c2', '#e6d9a8': '#f0e6c2', '#8fa893': '#a8bcaa',
      '#e6c88a': '#f0d8ab', '#8fd4c1': '#aae0d0', '#d8e6d8': '#e8f2e8',
      '#b0c4b4': '#c4d4c8', '#bcccb8': '#ccd8c8'
    }
  };

  // The user's own colour for the line they are working on. Empty means
  // "use the theme". The highlight sits behind the code, so the rule is
  // the opposite of a text colour: instead of pushing the colour away
  // from the background until it is readable, a highlight that would
  // swallow the text is faded toward the background until the theme's
  // text clears AA on it. Either way the reader's hue is kept.
  var customHighlightColor = '';

  function highlightColour(palette) {
    if (customHighlightColor) {
      return ensureHighlightReadable(
        customHighlightColor, palette.bg, palette.fg);
    }
    return palette.highlight || palette.selection + '33';
  }

  // The <style> element the theme is written into. Created once and
  // reused, so a theme or colour change rewrites the rules rather than
  // stacking new ones.
  var themeStyleEl = null;

  function applyTheme(themeKey) {
    var c = themePalette[themeKey] || themePalette;
    if (!c.bg) return;
    // The bundled CodeMirror build applies the theme class (cm-s-*) but
    // ships without the defineTheme/defineStyle API, so the theme is
    // written as CSS rules instead of being registered with CodeMirror.
    // The rules target the class CodeMirror puts on the wrapper when the
    // theme option is set, which is exactly what defineTheme would have
    // generated. The style element is reused, so a theme or colour change
    // rewrites the rules rather than stacking new ones.
    var rules = [
      '.cm-s-accessible-theme { background: ' + c.bg + '; color: ' + contrastAdjust(c.fg) + ' }',
      '.cm-s-accessible-theme .CodeMirror-gutters { background-color: ' + c.gutter_bg + '; color: ' + c.gutter_fg + '; }',
      '.cm-s-accessible-theme .CodeMirror-linenumber { color: ' + c.gutter_fg + '; }',
      '.cm-s-accessible-theme .CodeMirror-cursor { border-left: 2px solid ' + c.cursor + '; }',
      '.cm-s-accessible-theme .CodeMirror-selected { background-color: ' + c.selection + '; }',
      '.cm-s-accessible-theme .CodeMirror-activeline-background { background-color: ' + highlightColour(c) + '; }',
      '.cm-s-accessible-theme .cm-keyword { color: ' + contrastAdjust(c.keyword) + '; font-weight: bold; }',
      '.cm-s-accessible-theme .cm-string { color: ' + contrastAdjust(c.string) + '; }',
      '.cm-s-accessible-theme .cm-comment { color: ' + contrastAdjust(c.comment) + '; font-style: italic; }',
      '.cm-s-accessible-theme .cm-number { color: ' + contrastAdjust(c.number) + '; }',
      '.cm-s-accessible-theme .cm-def { color: ' + contrastAdjust(c.function) + '; }',
      '.cm-s-accessible-theme .cm-variable-2 { color: ' + contrastAdjust(c.variable) + '; }',
      '.cm-s-accessible-theme .cm-variable-3 { color: ' + contrastAdjust(c.function) + '; }',
      '.cm-s-accessible-theme .cm-operator { color: ' + contrastAdjust(c.operator) + '; }',
      '.cm-s-accessible-theme .cm-punctuation { color: ' + contrastAdjust(c.punctuation) + '; }',
      '.cm-s-accessible-theme .cm-bracket { color: ' + contrastAdjust(c.punctuation) + '; }',
      '.cm-s-accessible-theme .cm-builtin { color: ' + contrastAdjust(c.function) + '; }',
      '.cm-s-accessible-theme .cm-atom { color: ' + contrastAdjust(c.number) + '; }',
      '.cm-s-accessible-theme .cm-meta { color: ' + contrastAdjust(c.comment) + '; }'
    ].join('\n');
    if (!themeStyleEl) {
      themeStyleEl = document.createElement('style');
      themeStyleEl.id = 'cm-theme-style';
      document.head.appendChild(themeStyleEl);
    }
    themeStyleEl.textContent = rules;
    editor.setOption('theme', 'accessible-theme');
    applyCustomChrome(themeKey);
    updatePreview();
  }

  // ---------- The custom theme ----------
  // The reader's own theme. Seven colours are picked in Settings; the rest
  // of the palette is derived from them so the derived colours can never
  // cost contrast. The server is the authority (custom_palette and
  // custom_chrome in routes.py); these two functions are the browser's
  // copies, so a pick previews live and a theme change lands without a
  // reload. tests/test_contrast.py checks the server's derivation, and the
  // dom harness checks these against the same rules.
  var CUSTOM_CHROME_KEYS = [
    '--bg', '--fg', '--accent', '--accent-fg', '--panel-bg',
    '--panel-border', '--muted', '--error-bg', '--error-border',
    '--error-fg', '--error-line', '--focus-ring'
  ];

  function customPalette(picks) {
    var T = AccessibleTint;
    var bg = T.parseHex(picks.bg);
    var fg = T.readableTextOn(bg, picks.fg);
    var keyword = T.readableTextOn(bg, picks.keyword);
    var string = T.readableTextOn(bg, picks.string);
    var comment = T.readableTextOn(bg, picks.comment);
    var number = T.readableTextOn(bg, picks.number);
    var fn = T.readableTextOn(bg, picks.function);
    var selection = T.toHex(T.tintReadableOn(
      T.mixHex(bg, fg, 0.25), bg, [fg]));
    var gutterBg = T.mixHex(bg, fg, 0.04);
    return {
      name: 'Custom',
      bg: T.toHex(bg),
      fg: fg,
      selection: selection,
      highlight: T.mixHex(bg, fg, 0.06),
      cursor: fg,
      gutter_bg: gutterBg,
      // Clamped against the background like every other text colour; the
      // gutter is only 4% away from it, so this clears on the gutter too.
      gutter_fg: T.readableTextOn(bg, T.mixHex(fg, bg, 0.35)),
      keyword: keyword,
      string: string,
      comment: comment,
      number: number,
      function: fn,
      variable: fg,
      operator: keyword,
      punctuation: fg
    };
  }

  function customChrome(palette) {
    var T = AccessibleTint;
    var bg = T.parseHex(palette.bg);
    var fg = T.parseHex(palette.fg);
    var panel = T.parseHex(palette.gutter_bg);
    var accent = fg;
    var black = [0, 0, 0], white = [255, 255, 255];
    var accentFg;
    if (T.contrastRatio(black, accent) >= 4.5) {
      accentFg = '#000000';
    } else if (T.contrastRatio(white, accent) >= 4.5) {
      accentFg = '#ffffff';
    } else {
      // A mid-grey accent clears neither extreme. Fade it toward the
      // background until the extreme that clears on the background clears
      // on it - the fade always has a known-good side.
      accentFg = T.contrastRatio(white, bg) >= T.contrastRatio(black, bg)
        ? '#ffffff' : '#000000';
      accent = T.tintReadableOn(T.toHex(accent), bg, [accentFg]);
    }
    var errorBg = T.mixHex(bg, '#ff6b6b', 0.12);
    var errorFgBase, errorBorderBase;
    if (T.luminance(bg) < 0.5) {
      errorFgBase = '#ffb3b3'; errorBorderBase = '#ff6b6b';
    } else {
      errorFgBase = '#8f2f1a'; errorBorderBase = '#c0523f';
    }
    return {
      '--bg': palette.bg,
      '--fg': palette.fg,
      '--accent': T.toHex(accent),
      '--accent-fg': accentFg,
      '--panel-bg': palette.gutter_bg,
      '--panel-border': T.mixHex(bg, fg, 0.2),
      '--muted': T.readableTextOn(panel, T.mixHex(fg, bg, 0.25)),
      '--error-bg': errorBg,
      '--error-border': T.readableTextOn(errorBg, errorBorderBase),
      '--error-fg': T.readableTextOn(errorBg, errorFgBase),
      '--error-line': 'color-mix(in srgb, var(--error-border) 16%, transparent)',
      '--focus-ring': palette.fg
    };
  }

  function applyCustomChrome(themeKey) {
    var palette = themePalette[themeKey];
    if (themeKey !== 'custom' || !palette || !palette.bg) {
      // A preset theme's chrome comes from the stylesheet. The inline
      // variables are removed so they cannot win the cascade over it.
      CUSTOM_CHROME_KEYS.forEach(function (key) {
        body.style.removeProperty(key);
      });
      return;
    }
    var chrome = customChrome(palette);
    Object.keys(chrome).forEach(function (key) {
      body.style.setProperty(key, chrome[key]);
    });
  }

  // ---------- Fonts ----------
  // The font stacks live in routes.py and arrive here on each <option>
  // as data-family, so there is only ever one copy of them. An earlier
  // version kept a second list in this file, which is how OpenDyslexic
  // could be listed but not actually load.
  var DEFAULT_FONT_FAMILY = '"OpenDyslexic3", "OpenDyslexic", "Atkinson Hyperlegible", "Nunito", "Mukta", "Almarai", sans-serif';

  function fontFamilyFor(fontKey) {
    var option = fontSelect && fontSelect.querySelector(
      'option[value="' + (fontKey || '').replace(/"/g, '') + '"]');
    var family = option && option.getAttribute('data-family');
    return family || DEFAULT_FONT_FAMILY;
  }

  // ---------- Colour ----------
  // The user can pick any colour for their code. That is a genuine
  // accessibility risk: a pale yellow on a light theme, or near-black on
  // a dark one, is unreadable. Rather than block the choice, the colour
  // is moved - along the lightness axis only, so the hue the user chose
  // is preserved - until it clears WCAG AA (4.5:1) against the theme it
  // is being used on. Contrast-mode remapping still applies on top.
  function hexToRgb(hex) {
    var value = String(hex || '').replace('#', '').trim();
    if (value.length === 3) {
      value = value[0] + value[0] + value[1] + value[1] + value[2] + value[2];
    }
    if (!/^[0-9a-fA-F]{6}$/.test(value)) return null;
    return {
      r: parseInt(value.slice(0, 2), 16),
      g: parseInt(value.slice(2, 4), 16),
      b: parseInt(value.slice(4, 6), 16)
    };
  }

  function relativeLuminance(rgb) {
    var channels = [rgb.r, rgb.g, rgb.b].map(function (channel) {
      var part = channel / 255;
      return part <= 0.03928 ? part / 12.92
        : Math.pow((part + 0.055) / 1.055, 2.4);
    });
    return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2];
  }

  function contrastRatio(first, second) {
    var a = relativeLuminance(first);
    var b = relativeLuminance(second);
    var lighter = Math.max(a, b);
    var darker = Math.min(a, b);
    return (lighter + 0.05) / (darker + 0.05);
  }

  function rgbToHex(rgb) {
    return '#' + [rgb.r, rgb.g, rgb.b].map(function (channel) {
      return ('0' + Math.max(0, Math.min(255, Math.round(channel)))
        .toString(16)).slice(-2);
    }).join('');
  }

  function ensureReadable(hex, backgroundHex, minimum) {
    var target = minimum || 4.5;
    var rgb = hexToRgb(hex);
    var bg = hexToRgb(backgroundHex);
    if (!rgb || !bg) return hex;
    if (contrastRatio(rgb, bg) >= target) return rgbToHex(rgb);

    // Move away from the background, whichever end is closer, so the
    // user's hue is kept and only the brightness changes.
    var backgroundIsDark = relativeLuminance(bg) < 0.5;
    var step = backgroundIsDark ? 12 : -12;
    var moved = { r: rgb.r, g: rgb.g, b: rgb.b };
    for (var i = 0; i < 40; i++) {
      moved = {
        r: moved.r + step,
        g: moved.g + step,
        b: moved.b + step
      };
      if (moved.r < 0 || moved.r > 255 || moved.g < 0 || moved.g > 255
          || moved.b < 0 || moved.b > 255) {
        break;
      }
      if (contrastRatio(moved, bg) >= target) return rgbToHex(moved);
    }
    return backgroundIsDark ? '#ffffff' : '#000000';
  }

  // A highlight sits behind the text, so the direction is the reverse of
  // ensureReadable: a colour that would swallow the theme's text is faded
  // toward the background until the text clears AA on it. The background
  // is the safe anchor because the theme's own text already clears 4.5:1
  // against it, and contrast is monotonic along the fade, so the first
  // stop that passes is the lightest touch that works.
  function ensureHighlightReadable(hex, backgroundHex, textHex) {
    var rgb = hexToRgb(hex);
    var bg = hexToRgb(backgroundHex);
    var text = hexToRgb(textHex);
    if (!rgb || !bg || !text) return hex;
    if (contrastRatio(text, rgb) >= 4.5) return rgbToHex(rgb);
    for (var i = 0; i < 20; i++) {
      rgb = {
        r: Math.round(rgb.r + (bg.r - rgb.r) * 0.1),
        g: Math.round(rgb.g + (bg.g - rgb.g) * 0.1),
        b: Math.round(rgb.b + (bg.b - rgb.b) * 0.1)
      };
      if (contrastRatio(text, rgb) >= 4.5) return rgbToHex(rgb);
    }
    return rgbToHex(bg);
  }

  function applyFont(fontKey, familyOverride) {
    // The wizard offers the same fonts as radios rather than as the
    // settings <select>, so it passes the stack it was rendered with.
    // Reading it from the select would quietly fall back to the default
    // family and the preview would show the wrong font.
    var family = familyOverride || fontFamilyFor(fontKey);
    body.style.fontFamily = family;
    editorEl.style.fontFamily = family;
    // CodeMirror needs the font applied to its content
    var cm = editorEl.querySelector('.CodeMirror');
    if (cm) cm.style.fontFamily = family;
    // Font metrics changed - recalculate the gutter width so line
    // numbers never overlap the code.
    editor.refresh();
    updatePreview();
  }

  function applyFontSize(size) {
    body.style.fontSize = size + 'px';
    editorEl.style.fontSize = size + 'px';
    var cm = editorEl.querySelector('.CodeMirror');
    if (cm) cm.style.fontSize = size + 'px';
    fontSizeLabel.textContent = size + 'px';
    editor.refresh();
    updatePreview();
  }

  // These three were stored in the config and rendered onto <body>, but
  // nothing ever read them, so the settings did nothing. The tokens
  // already exist in style.css and body already consumes them, so all
  // that is needed is to write the new value.
  function applyLineHeight(value) {
    body.style.setProperty('--line-height', value);
    body.setAttribute('data-line-height', value);
    lineHeightLabel.textContent = value;
    editor.refresh();
  }

  function applyLetterSpacing(value) {
    body.style.setProperty('--letter-spacing', value + 'px');
    body.setAttribute('data-letter-spacing', value);
    letterSpacingLabel.textContent = value + 'px';
    editor.refresh();
  }

  // The notching buttons either side of the two spacing sliders.
  //
  // Dragging a slider thumb is a poor target for a shaky hand and a worse
  // one behind a screen magnifier, and the arrow keys only work once the
  // slider has focus. The buttons are a second way in, not a replacement.
  //
  // Everything is read from the slider being driven rather than written out
  // again here. A button that disagrees with its own slider is a control
  // that lies: the value stops short or overshoots, and the reader is shown
  // a number the server then rejects.
  var stepperButtons = [
    'line-height-less', 'line-height-more',
    'letter-spacing-less', 'letter-spacing-more',
  ].map(function (id) {
    return document.getElementById(id);
  }).filter(function (button) {
    return !!button;
  });

  function stepperTarget(button) {
    var id = button.getAttribute('data-target');
    // A button with no target is a mistake in the markup, not something a
    // reader can press, so it is skipped rather than looked up as "null".
    return id ? document.getElementById(id) : null;
  }

  // The nearest value the slider can actually take. Snapping to the step
  // grid first, then rounding, is what keeps 1.4 + 0.1 from arriving as
  // 1.5000000000000002 and being shown in the field.
  function notchTo(target, value) {
    var min = parseFloat(target.getAttribute('min'));
    var max = parseFloat(target.getAttribute('max'));
    var increment = parseFloat(target.getAttribute('step')) || 0.1;
    var snapped = min + (Math.round((value - min) / increment) * increment);
    return Math.min(max, Math.max(min, Number(snapped.toFixed(2))));
  }

  // At the end of its travel a button is disabled rather than doing nothing,
  // so a reader is told the value cannot go further this way instead of
  // pressing it and watching nothing happen.
  function paintStepperLimits() {
    stepperButtons.forEach(function (button) {
      var target = stepperTarget(button);
      if (!target) return;
      var value = parseFloat(target.value);
      var step = parseFloat(button.getAttribute('data-step'));
      if (isNaN(value) || isNaN(step)) return;
      if (step < 0) {
        button.disabled = value <= parseFloat(target.getAttribute('min'));
      } else {
        button.disabled = value >= parseFloat(target.getAttribute('max'));
      }
    });
  }

  stepperButtons.forEach(function (button) {
    button.addEventListener('click', function () {
      var target = stepperTarget(button);
      if (!target) return;
      var step = parseFloat(button.getAttribute('data-step'));
      var next = notchTo(target, parseFloat(target.value) + step);
      if (isNaN(next)) return;
      target.value = String(next);
      // The slider's own listeners are not told, because no event happened
      // on it. Applying and saving here keeps one place where each value
      // becomes a setting, rather than two that can drift apart.
      if (target === lineHeight) {
        applyLineHeight(target.value);
        saveConfig({ line_height: next });
      } else if (target === letterSpacing) {
        applyLetterSpacing(target.value);
        saveConfig({ letter_spacing: next });
      }
      paintStepperLimits();
    });
  });

  // 0 = barely faded, 1 = strongly faded. A 0 value would hide the other
  // lines completely, so we keep a floor of 0.15.
  function applyBlurIntensity(value) {
    var amount = 0.85 - (value * 0.7);
    body.style.setProperty('--blur-amount', amount.toFixed(2));
    blurIntensityLabel.textContent = value;
  }

  function applyContrast(value) {
    contrastMode = value;
    body.setAttribute('data-contrast', value);
    applyTheme(themeSelect.value);
  }

  function applyFocusMode(mode) {
    body.setAttribute('data-focus-mode', mode);
    // Hide the gutter through CodeMirror's native option rather than CSS
    // display:none. Toggling lineNumbers makes CodeMirror re-measure and
    // drop the gutter column, so the numbers never ghost over the code.
    if (mode === 'gutter') {
      if (editor.getOption('lineNumbers')) editor.setOption('lineNumbers', false);
    } else {
      if (!editor.getOption('lineNumbers')) editor.setOption('lineNumbers', true);
    }
    editor.refresh();
    setTimeout(editor.refresh.bind(editor), 40);
  }

  // ---------- Config persistence ----------
  function saveConfig(partial) {
    var payload = {};
    Object.keys(partial).forEach(function (key) { payload[key] = partial[key]; });
    payload.access_code = accessCode;
    // The server needs a locale so the sentences it sends back match what
    // is on screen. A caller that is changing the language passes its own,
    // and that has to win - overwriting it here made the picker save
    // nothing at all and reload straight back into the old language.
    if (payload.locale) {
      META.locale = payload.locale;
    } else {
      payload.locale = META.locale;
    }
    return fetch('/api/config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    })
      .then(function (res) { return res.json().then(function (data) { return { ok: res.ok, data: data }; }); })
      .then(function (result) {
        if (result.ok) {
          if (settingsStatus) {
            settingsStatus.textContent = t('settings.saved');
            settingsStatus.classList.remove('is-error');
          }
        } else {
          reportSaveError(result.data);
        }
        return result;
      })
      .catch(function () {
        // Offline or server error - the setting still applies for this
        // session, so say so rather than pretending it failed.
        if (settingsStatus) {
          settingsStatus.textContent = t('settings.not_saved');
          settingsStatus.classList.add('is-error');
        }
      });
  }

  function reportSaveError(data) {
    if (!settingsStatus) return;
    settingsStatus.textContent = (data && data.error) || t('settings.save_failed');
    settingsStatus.classList.add('is-error');
  }

  // ---------- Settings dialog ----------
  function openSettings() {
    settingsOpener = document.activeElement;
    syncBlurField();
    if (typeof settingsDialog.showModal === 'function') {
      settingsDialog.showModal();
    } else {
      settingsDialog.setAttribute('open', '');
    }
    // Land focus on the first real control, not the close button.
    var first = settingsDialog.querySelector('select, input, button');
    if (first) first.focus();
  }

  function closeSettings() {
    if (typeof settingsDialog.close === 'function') {
      settingsDialog.close();
    } else {
      settingsDialog.removeAttribute('open');
    }
    // Send focus back where it came from, so keyboard and screen reader
    // users are not dropped at the top of the page.
    if (settingsOpener && typeof settingsOpener.focus === 'function') {
      settingsOpener.focus();
    }
  }

  // ---------- First-run setup ----------
  // Three steps: language, reading font, and a very short tour. It is shown
  // only until the reader has finished it, which is why the server decides
  // whether it exists at all.
  //
  // The step is derived from the panels in the page rather than from a list
  // written out here, so adding a step to index.html cannot leave this
  // file stepping past the end of its own navigation.
  function setupPanels() {
    if (!setupDialog) return [];
    return setupDialog.querySelectorAll('.setup-panel');
  }

  function setupCurrentStep() {
    var panels = setupPanels();
    for (var i = 0; i < panels.length; i++) {
      if (!panels[i].hidden) return i + 1;
    }
    return 1;
  }

  function showSetupStep(step) {
    var panels = setupPanels();
    var total = panels.length;
    if (!total) return;
    step = Math.max(1, Math.min(step, total));

    for (var i = 0; i < total; i++) {
      panels[i].hidden = (i + 1) !== step;
    }
    if (setupProgress) setupProgress.textContent = t('setup.step_of', step, total);
    if (setupBack) setupBack.hidden = step === 1;
    // The last step finishes rather than advancing, so the button says so.
    if (setupNext) {
      setupNext.textContent = step === total ? t('setup.start') : t('setup.next');
    }
    // Move focus to the new question. Staying on the Next button would
    // leave a screen reader announcing the same button after it changes.
    var heading = panels[step - 1].querySelector('.setup-legend');
    if (heading && heading.focus) heading.focus();
  }

  function setupError() {
    if (!setupStatus) return;
    setupStatus.hidden = false;
    setupStatus.textContent = t('setup.error_saved');
  }

  // Reached at the end. Reloading is the point: the whole page, wizard
  // included, is drawn by the server in the chosen language and font, so
  // this is the only way the reader ever sees the app as they set it up.
  function finishSetup(extra) {
    var payload = extra || {};
    payload.setup_complete = true;
    saveConfig(payload).then(function (result) {
      if (result && result.ok) {
        window.location.reload();
        return;
      }
      setupError();
    });
  }

  function openSetup() {
    if (!setupDialog) return;
    if (typeof setupDialog.showModal === 'function') {
      setupDialog.showModal();
    } else {
      setupDialog.setAttribute('open', '');
    }
    var heading = setupDialog.querySelector('.setup-panel:not([hidden]) .setup-legend');
    if (heading && heading.focus) heading.focus();
  }

  if (setupDialog) {
    // Escape does not close this one. The screen exists to be answered,
    // and dismissing it by reflex would leave the reader on the default
    // font with no idea there was a choice to make. Skipping is a visible
    // button instead, so there is still a way out.
    setupDialog.addEventListener('cancel', function (event) {
      event.preventDefault();
    });

    if (setupNext) {
      setupNext.addEventListener('click', function () {
        var panels = setupPanels();
        var step = setupCurrentStep();
        if (step >= panels.length) {
          finishSetup();
          return;
        }
        showSetupStep(step + 1);
      });
    }

    if (setupBack) {
      setupBack.addEventListener('click', function () {
        showSetupStep(setupCurrentStep() - 1);
      });
    }

    if (setupSkip) {
      // Only marks the setup done. Anything already chosen stays chosen,
      // so a reader who picked a font and then bailed out keeps it.
      setupSkip.addEventListener('click', function () {
        finishSetup();
      });
    }

    var localeRadios = setupDialog.querySelectorAll('input[name="setup-locale"]');
    Array.prototype.forEach.call(localeRadios, function (radio) {
      radio.addEventListener('change', function () {
        var chosen = radio.value;
        if (!chosen || chosen === META.locale) return;
        body.setAttribute('data-locale', chosen);
        // Saving the step first is what stops the reload from throwing
        // the reader back to the first question they already answered.
        saveConfig({ locale: chosen, setup_step: setupCurrentStep() })
          .then(function (result) {
            if (result && result.ok) {
              window.location.reload();
              return;
            }
            setupError();
          });
      });
    });

    var fontRadios = setupDialog.querySelectorAll('input[name="setup-font"]');
    Array.prototype.forEach.call(fontRadios, function (radio) {
      radio.addEventListener('change', function () {
        var family = radio.getAttribute('data-family');
        // Applied to the whole page, wizard included, rather than to a
        // snippet in isolation: the point is to see the font against the
        // real interface before agreeing to it.
        applyFont(radio.value, family);
        body.setAttribute('data-font', radio.value);
        // Saved straight away, so a reader who chooses a font and then
        // skips does not lose the choice.
        saveConfig({ font: radio.value }).then(function (result) {
          if (!result || !result.ok) setupError();
        });
      });
    });

    var themeRadios = setupDialog.querySelectorAll('input[name="setup-theme"]');
    Array.prototype.forEach.call(themeRadios, function (radio) {
      radio.addEventListener('change', function () {
        var chosen = radio.value;
        if (!chosen) return;
        // The editor behind the wizard repaints so the reader sees the
        // theme against real code, not just the swatches.
        applyTheme(chosen);
        body.setAttribute('data-theme', chosen);
        // Saved straight away, so a reader who chooses a theme and then
        // skips does not lose the choice.
        saveConfig({ theme: chosen }).then(function (result) {
          if (!result || !result.ok) setupError();
        });
      });
    });
  }

  // For anyone who skipped the first-run screen and wants it after all.
  if (btnSetupAgain) {
    btnSetupAgain.addEventListener('click', function () {
      saveConfig({ setup_complete: false, setup_step: 1 }).then(function (result) {
        if (result && result.ok) {
          window.location.reload();
          return;
        }
        if (settingsStatus) {
          settingsStatus.textContent = t('setup.error_saved');
          settingsStatus.classList.add('is-error');
        }
      });
    });
  }

  // Reset every setting to the defaults. Two clicks on purpose: the first
  // arms the button, the second does it, so a reader who pressed it by
  // accident has a visible way out. The button disarms itself after a few
  // seconds so it cannot stay dangerous. Reloading is the point, exactly
  // as it is for the language picker and the setup screen: the whole page
  // is drawn by the server from the saved config, so a reload is the only
  // way every control and every panel agrees with what was just reset.
  if (btnResetConfig) {
    var resetArmed = false;
    var resetTimer = null;
    btnResetConfig.addEventListener('click', function () {
      if (!resetArmed) {
        resetArmed = true;
        btnResetConfig.textContent = t('settings.reset_confirm');
        btnResetConfig.classList.add('is-armed');
        resetTimer = setTimeout(function () {
          resetArmed = false;
          btnResetConfig.textContent = t('settings.reset_config');
          btnResetConfig.classList.remove('is-armed');
        }, 6000);
        return;
      }
      clearTimeout(resetTimer);
      btnResetConfig.disabled = true;
      fetch('/api/config/reset', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ access_code: accessCode, locale: META.locale })
      })
        .then(function (res) {
          return res.json().then(function (data) { return { ok: res.ok, data: data }; });
        })
        .then(function (result) {
          if (result.ok) {
            window.location.reload();
            return;
          }
          resetFailed();
        })
        .catch(resetFailed);
    });

    function resetFailed() {
      btnResetConfig.disabled = false;
      btnResetConfig.textContent = t('settings.reset_config');
      btnResetConfig.classList.remove('is-armed');
      resetArmed = false;
      if (settingsStatus) {
        settingsStatus.textContent = t('settings.not_saved');
        settingsStatus.classList.add('is-error');
      }
    }
  }

  // ---------- TTS ----------
  // The browser already knows how to read a line out loud; what it does not
  // know is that this app is meant for people who would rather not have to
  // work out what a button does before pressing it. So four separate
  // decisions decide whether something is spoken: what its name is, whether
  // it is worth saying, which voice says it, and whether to wait first.
  //
  // Nothing here touches the editor or the output. Those are the places
  // where speaking on hover turns into noise - a reader moving the pointer
  // across a screen of code would set off a queue of voices, and worse,
  // cancel the error they were trying to hear.
  var MAX_SPEECH_CHARS = 400;

  // Never read aloud, at any scope: the places a hover would be a nuisance
  // rather than a help.
  var NEVER_SPOKEN = '#editor, #output, .CodeMirror, [contenteditable=""], '
    + '[contenteditable="true"]';

  // What "the things that do something" means for the hover scope. Inputs
  // and selects are in here because their label is exactly the thing a
  // reader wants before touching them, and the name of a text field is
  // usually the one thing the page does not show in the same place.
  var HOVER_CONTROLS = 'button, a[href], input, select, textarea, [role="switch"], '
    + '[role="button"], [role="tab"], summary, label, legend, h1, h2, h3, h4, h5, h6, th';

  // Only read when the scope is "all". This is the difference between a
  // helpful app and an unusable one, which is why it is the reader's call.
  var HOVER_TEXT = 'p, li, td, dt, dd, blockquote, figcaption, caption, '
    + '.field-help, .settings-legend, .switch-text, .notice, .tagline';

  function cleanText(text) {
    return String(text == null ? '' : text).replace(/\s+/g, ' ').trim();
  }

  // Element.closest is avoided deliberately: walking the chain by hand is
  // the same answer, and the DOM test harness has no layout engine to
  // implement it with.
  function closestOf(el, selectors) {
    var node = el;
    while (node && node !== document.body) {
      if (node.matches && node.matches(selectors)) return node;
      node = node.parentNode;
    }
    return null;
  }

  function isHidden(el) {
    return !!(closestOf(el, '[hidden], [aria-hidden="true"]'));
  }

  // The name of a thing, in the order a screen reader would go looking for
  // it. Returns an empty string when there is genuinely nothing to say,
  // which is the signal not to speak rather than to read out a stray
  // punctuation mark.
  function labelFor(el) {
    if (!el) return '';
    var tag = (el.tagName || '').toLowerCase();
    var name = cleanText(el.getAttribute && el.getAttribute('aria-label'));

    if (!name && el.labels && el.labels.length) {
      name = cleanText(el.labels[0].textContent);
    }
    if (!name) {
      var wrapping = closestOf(el, 'label');
      if (wrapping) name = cleanText(wrapping.textContent);
    }

    // A control's own text: what a button says, or which option a
    // dropdown is currently showing. Reading only the label of a dropdown
    // would leave the reader knowing the field name and none of its
    // contents.
    var own = '';
    if (tag === 'select') {
      var option = el.options && el.selectedIndex >= 0
        ? el.options[el.selectedIndex]
        : null;
      own = cleanText(option && (option.textContent || option.text));
    } else if (tag === 'input') {
      if (el.type === 'checkbox' || el.type === 'radio') {
        own = el.checked ? t('speak.on') : t('speak.off');
      } else if (el.type === 'range' || el.type === 'number') {
        own = cleanText(el.value);
      } else {
        own = cleanText(el.getAttribute && el.getAttribute('placeholder'));
      }
    } else if (tag === 'img') {
      own = '';
    } else {
      own = cleanText(el.textContent);
    }

    if (own === name) own = '';
    if (name && own) return name + ', ' + own;
    if (own) return own;
    if (name) return name;

    return cleanText(el.getAttribute && el.getAttribute('title'));
  }

  // A switch is read with its state, the way VoiceOver and NVDA read it.
  // Without the state, "Reduce motion" sounds identical whether the app is
  // about to obey the request or ignore it.
  function withState(text, el) {
    if (!el || !el.getAttribute) return text;
    if (el.getAttribute('role') !== 'switch') return text;
    return text + ', ' + t(el.getAttribute('aria-checked') === 'true'
      ? 'speak.on' : 'speak.off');
  }

  function shorten(text) {
    if (text.length <= MAX_SPEECH_CHARS) return text;
    return text.slice(0, MAX_SPEECH_CHARS).replace(/\s+\S*$/, '') + t('speak.cut_off');
  }

  function whatToSay(el) {
    if (!el || isHidden(el) || closestOf(el, NEVER_SPOKEN)) return '';
    return shorten(withState(labelFor(el), el));
  }

  function loadVoices() {
    if (!('speechSynthesis' in window) || !ttsVoice) return;
    var voices = window.speechSynthesis.getVoices() || [];
    if (!voices.length) return;

    // A choice the reader made themselves is remembered in speechVoiceName,
    // not in the picker's value, because loadVoices moves that value around
    // to show the automatic choice below. Reading it from the wrong one is
    // how a hand-picked voice gets quietly forgotten on the next reload.
    var current = speechVoiceName;
    ttsVoice.innerHTML = '';
    var def = document.createElement('option');
    def.value = '';
    def.textContent = t('speak.system_default');
    ttsVoice.appendChild(def);

    // The picker is in the same order pickVoice would choose from: the
    // reader's own language first, and within it the voices matching the
    // preferred gender. Operating systems list voices alphabetically by
    // English name, which for a Hindi or Arabic reader puts a page of
    // English options above the one voice that reads their language.
    var ordered = voicesForLocale(voices);
    ordered.forEach(function (voice) {
      var option = document.createElement('option');
      // value holds the voice name; the language is shown so a reader
      // can tell two similarly named voices apart.
      option.value = voice.name;
      option.textContent = voice.name + ' (' + voice.lang + ')';
      ttsVoice.appendChild(option);
    });

    if (current) {
      ttsVoice.value = current;
      // A voice can be removed from the machine between one visit and the
      // next, and a picker pointed at an option that is no longer there shows
      // nothing at all. Treat that as no choice, so the fallback below
      // applies and the reader is shown what will actually be read out.
      if (ttsVoice.value !== current) current = '';
    }

    if (!current) {
      // No voice of their own, so the app is choosing one for them. Leaving
      // the picker on "System default" would then be a small lie: the
      // system default is not what is read out, and a reader who wanted to
      // see which voice that is had no way to find out. Showing the actual
      // choice makes the guess visible and lets them correct it in one
      // click, without saving anything they did not pick themselves.
      var chosen = pickVoice();
      if (chosen) ttsVoice.value = chosen.name;
    }
  }

  // The speech API does not report whether a voice is male or female, so
  // this is a guess from the name, and it is only ever a guess: it is used
  // to order the choices, never to hide a voice the reader picked.
  //
  // The names are grouped by the languages the app ships in, because they
  // are not one list that grows. Windows names its voices after people,
  // and names them differently for each language - "Zira" is the English
  // one, "Swara" is the Hindi one, "Hoda" is the Arabic one - so a list
  // with only English names in it silently matched nothing for a Hindi or
  // Arabic reader, who would have been handed whatever voice happened to
  // be first. Adding a language means adding its names here.
  //
  // What is left over is 'unknown', which is the honest answer for a voice
  // nobody has heard of, and it falls back to the browser's own choice.
  var VOICE_NAMES = {
    en: {
      female: 'female|woman|girl|samantha|karen|serena|moira|tessa|fiona|'
        + 'victoria|zira|allison|ava|amelie|katja|lucia|marlene|nicky|petra|'
        + 'helena|susan|agnes|carla|catherine|alice|joana|nora|sonia|paulina|'
        + 'aria|jenny|michelle|natural|hazel|zoe',
      male: 'male|man|boy|david|daniel|alex|fred|thomas|oliver|james|george|'
        + 'paul|mark|rishi|diego|mateo|riccardo|yannick|albert|aaron|ryan|'
        + 'markus|brandon|christopher|eric|guy|jake|roger|steffan',
    },
    hi: {
      // Windows: Swara and Hemant. Google: several Hindi voices, and the
      // ones that name their gender say so outright.
      female: 'female|woman|girl|swara|lakshmi|sangeeta|kalpana|lekha|asha',
      male: 'male|man|boy|hemant|madhur|rishi|raj|aarav|ravi',
    },
    fr: {
      // Windows: Denise and Henri. macOS adds a few more.
      female: 'female|femme|woman|girl|denise|amélie|amelie|audrey|marie|'
        + 'chantal|virginie|lucie',
      male: 'male|homme|man|boy|henri|thomas|bernard|nicolas|olivier|'
        + 'georges|antoine|mathieu|frédéric|frederic',
    },
    es: {
      // Windows Mexico: Sabina and Diego. Windows Spain: Helena and Pablo.
      female: 'female|mujer|woman|girl|sabina|helena|monica|lucia|paula|'
        + 'carmen|rosa|valentina',
      male: 'male|hombre|man|boy|diego|pablo|javier|raul|carlos|miguel|'
        + 'sergio|antonio',
    },
    ar: {
      // Windows Arabic: Hoda and Naayf. Google Arabic voices are named
      // after the dialect, and say their gender where they know it.
      female: 'female|امرأة|woman|girl|hoda|huuda|leila|maja|female-arabic',
      male: 'male|رجل|man|boy|naayf|خليل|male-arabic',
    },
  };

  // The names are matched on word boundaries, and "\\b" is the wrong tool
  // for that here. It only treats a letter as a word character where the
  // engine says so, which for "Amélie" it does but for "رجل" it does not:
  // both boundaries land in the wrong place and the Arabic name is never
  // found, leaving an Arabic reader with the system's arbitrary choice.
  // Asking for "not a letter and not a digit" instead is the rule that was
  // meant, and it behaves the same in every language on the list.
  function namePattern(names) {
    return new RegExp('(^|[^\\p{L}\\p{N}])(' + names + ')($|[^\\p{L}\\p{N}])', 'iu');
  }

  function voiceGender(voice) {

    var name = ((voice && voice.name) || '') + ' ' + ((voice && voice.voiceURI) || '');
    var locale = String(META.locale || 'en').toLowerCase().split(/[-_]/)[0];
    // The reader's own language is tried first, then English, because a
    // Windows install lists its Hindi voices in English on some versions.
    var order = [locale, 'en'];
    for (var i = 0; i < order.length; i++) {
      var set = VOICE_NAMES[order[i]];
      if (!set) continue;
      if (namePattern(set.female).test(name)) return 'female';
      if (namePattern(set.male).test(name)) return 'male';
    }
    return 'unknown';
  }

  // Voices that sound the right language first, so a Hindi interface is
  // not read by an English voice simply because it was listed earlier.
  // Within each language group, the voices matching the preferred gender
  // come first, so the automatic choice and the top of the picker agree
  // with each other.
  function voicesForLocale(voices) {
    var wanted = String(META.locale || 'en').toLowerCase();
    var exact = [];
    var sameLanguage = [];
    var rest = [];
    voices.forEach(function (voice) {
      var lang = String(voice.lang || '').toLowerCase();
      if (lang === wanted) exact.push(voice);
      else if (lang.split(/[-_]/)[0] === wanted.split(/[-_]/)[0]) sameLanguage.push(voice);
      else rest.push(voice);
    });

    var preferred = ttsVoiceGenderValue;
    var sort = function (list) {
      if (preferred === 'any') return list;
      var match = [];
      var other = [];
      list.forEach(function (voice) {
        if (voiceGender(voice) === preferred) match.push(voice);
        else other.push(voice);
      });
      return match.concat(other);
    };

    return sort(exact).concat(sort(sameLanguage), sort(rest));
  }

  function pickVoice() {
    if (!('speechSynthesis' in window)) return null;
    var voices = window.speechSynthesis.getVoices() || [];
    if (!voices.length) return null;

    // A voice the reader chose themselves always wins, whatever the
    // gender preference says. They can see the name; the app cannot.
    for (var i = 0; i < voices.length; i++) {
      if (speechVoiceName && voices[i].name === speechVoiceName) return voices[i];
    }
    if (ttsVoiceGenderValue === 'any') return null;
    // A saved voice that is not installed any more is deliberately still
    // saved, so it comes back if the reader puts it back. It cannot be used
    // today, though, and the alternative is leaving speech to whatever the
    // operating system picks - which for a non-English reader is usually an
    // English voice. So the preference below is used instead, and the picker
    // shows the voice that is really being read out.

    var ordered = voicesForLocale(voices);
    for (var j = 0; j < ordered.length; j++) {
      if (voiceGender(ordered[j]) === ttsVoiceGenderValue) return ordered[j];
    }
    // Nothing installed matches the preference. Saying nothing would be
    // worse than a wrong guess, so the browser picks its own default.
    return null;
  }

  function speak(text) {
    if (!('speechSynthesis' in window)) return;
    var words = cleanText(text);
    if (!words) return;
    window.speechSynthesis.cancel();
    var utterance = new SpeechSynthesisUtterance(words);
    utterance.rate = speechRate;
    utterance.pitch = 1.0;
    // Without this the voice reads Hindi and French words in an English
    // accent, which is the one thing that makes a foreign interface
    // genuinely hard to follow.
    if (META.locale) utterance.lang = META.locale;
    var voice = pickVoice();
    if (voice) utterance.voice = voice;
    window.speechSynthesis.speak(utterance);
  }

  // ---------- Hover and click ----------
  // Both are delegated from the document, so the page does not grow a
  // listener every time the editor is redrawn.
  var hoverTimer = null;
  var hoverTarget = null;

  function hoverTargetFor(el) {
    if (ttsHoverScope === 'off' || !ttsEnabled) return null;
    var control = closestOf(el, HOVER_CONTROLS);
    if (control) return control;
    if (ttsHoverScope !== 'all') return null;
    return closestOf(el, HOVER_TEXT);
  }

  function clearHover() {
    if (hoverTimer !== null) {
      clearTimeout(hoverTimer);
      hoverTimer = null;
    }
    hoverTarget = null;
  }

  function onMouseOver(event) {
    var target = hoverTargetFor(event && event.target);
    if (!target) {
      clearHover();
      return;
    }
    // Moving between a button and the words inside it is still one thing
    // under the pointer, and a screen reader would not repeat itself here.
    if (target === hoverTarget) return;
    clearHover();
    hoverTarget = target;
    hoverTimer = setTimeout(function () {
      hoverTimer = null;
      var words = whatToSay(hoverTarget);
      if (words) speak(words);
    }, Math.max(0, ttsHoverDelay || 0));
  }

  function onMouseOut(event) {
    var from = hoverTargetFor(event && event.target);
    if (!from) return;
    var to = hoverTargetFor(event && event.relatedTarget);
    if (to === from) return;
    clearHover();
  }

  // Capture phase, and this is the whole reason for it. A click on Run
  // starts the program, whose output then speaks and replaces whatever was
  // said here. Speaking the button name afterwards would cancel the output
  // the reader actually asked for.
  function onClick(event) {
    if (!ttsClickToSpeak || !ttsEnabled) return;
    var el = event && event.target;
    if (!el || closestOf(el, NEVER_SPOKEN)) return;
    if (el.disabled) return;
    var words = whatToSay(el);
    if (words) speak(words);
  }

  document.addEventListener('mouseover', onMouseOver);
  document.addEventListener('mouseout', onMouseOut);
  document.addEventListener('click', onClick, true);

  // ---------- Run code ----------
  var errorMarkers = [];

  function clearErrorMarkers() {
    errorMarkers.forEach(function (m) { m.clear(); });
    errorMarkers = [];
  }

  function highlightErrorLine(lineNumber) {
    clearErrorMarkers();
    if (!lineNumber) return;
    var line = lineNumber - 1; // CodeMirror lines are 0-based
    if (line < 0 || line >= editor.lineCount()) return;
    var marker = editor.markText(
      { line: line, ch: 0 },
      { line: line, ch: editor.getLine(line).length },
      { className: 'cm-error-line' }
    );
    errorMarkers.push(marker);
    editor.scrollIntoView({ line: line, ch: 0 }, 100);
    editor.setCursor({ line: line, ch: 0 });
  }

  function runCode() {
    var code = editor.getValue();
    outputEl.textContent = t('output.running');
    errorPanel.hidden = true;
    clearErrorMarkers();

    fetch('/api/run', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ code: code, access_code: accessCode, locale: META.locale })
    })
      .then(function (res) { return res.json(); })
      .then(function (data) {
        if (data.code_required) {
          if (promptForAccessCode()) {
            runCode();
          } else {
            outputEl.textContent = t('output.locked');
            errorMessage.textContent = data.error;
            errorPanel.hidden = false;
          }
          return;
        }
        outputEl.textContent = data.output || t('output.no_output');
        if (data.error) {
          errorMessage.textContent = data.error;
          errorPanel.hidden = false;
          highlightErrorLine(data.error_line);
          if (ttsEnabled) speak(data.error);
        } else {
          errorPanel.hidden = true;
          if (ttsEnabled) speak(data.output || t('speak.finished'));
        }
      })
      .catch(function () {
        outputEl.textContent = t('output.runner_unreachable');
        errorMessage.textContent = t('output.server_down');
        errorPanel.hidden = false;
      });
  }

  // ---------- Save / Open files ----------
  function saveFile() {
    var content = editor.getValue();
    var suggestedName = 'my_code.py';

    if (window.showSaveFilePicker) {
      window.showSaveFilePicker({
        suggestedName: suggestedName,
        types: [{ description: t('file.python_type'), accept: { 'text/x-python': ['.py'] } }]
      })
        .then(function (handle) { return handle.createWritable(); })
        .then(function (writable) {
          return writable.write(content).then(function () { return writable.close(); });
        })
        .then(function () {
          outputEl.textContent = t('output.saved');
          errorPanel.hidden = true;
        })
        .catch(function (err) {
          if (err.name !== 'AbortError') {
            outputEl.textContent = t('output.save_failed');
          }
        });
    } else {
      // Fallback: download the file
      var blob = new Blob([content], { type: 'text/x-python' });
      var url = URL.createObjectURL(blob);
      var a = document.createElement('a');
      a.href = url;
      a.download = suggestedName;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      outputEl.textContent = t('output.downloaded');
      errorPanel.hidden = true;
    }
  }

  function openFile() {
    if (window.showOpenFilePicker) {
      window.showOpenFilePicker({
        types: [{ description: t('file.python_type'), accept: { 'text/x-python': ['.py'] } }]
      })
        .then(function (handles) { return handles[0].getFile(); })
        .then(function (file) { return file.text(); })
        .then(function (text) {
          editor.setValue(text);
          clearErrorMarkers();
          outputEl.textContent = t('output.opened');
          errorPanel.hidden = true;
        })
        .catch(function (err) {
          if (err.name !== 'AbortError') {
            outputEl.textContent = t('output.open_failed');
          }
        });
    } else {
      fileInput.click();
    }
  }

  // ---------- Read line aloud ----------
  function readLine() {
    var selection = editor.getSelection();
    var text = selection || editor.getLine(editor.getCursor().line);
    if (text && text.trim()) {
      speak(text);
    }
  }

  // ---------- Event wiring ----------
  btnRun.addEventListener('click', runCode);

  btnClear.addEventListener('click', function () {
    outputEl.textContent = '';
    errorPanel.hidden = true;
  });

  btnSave.addEventListener('click', saveFile);

  btnOpen.addEventListener('click', openFile);

  fileInput.addEventListener('change', function () {
    var file = fileInput.files[0];
    if (!file) return;
    var reader = new FileReader();
    reader.onload = function () {
      editor.setValue(reader.result);
      clearErrorMarkers();
      outputEl.textContent = t('output.opened');
      errorPanel.hidden = true;
    };
    reader.readAsText(file);
    fileInput.value = '';
  });

  btnReadLine.addEventListener('click', readLine);

  btnTts.addEventListener('click', function () {
    ttsEnabled = !ttsEnabled;
    btnTts.setAttribute('aria-checked', ttsEnabled ? 'true' : 'false');
    btnTts.classList.toggle('active', ttsEnabled);
    if (ttsState) ttsState.textContent = ttsEnabled ? t('speak.on') : t('speak.off');
    saveConfig({ tts_enabled: ttsEnabled });
    if (ttsEnabled) {
      speak(t('speak.enabled'));
    }
  });

  // ---------- Motion ----------
  // The CSS stops transitions and animations when the body says so. What
  // this switch has to get right is the difference between "off" and "not
  // chosen yet": until the reader picks, the operating system preference
  // decides, and the switch shows whatever the system is asking for rather
  // than sitting at a default the reader never agreed to.
  var prefersReducedMotion = window.matchMedia
    ? window.matchMedia('(prefers-reduced-motion: reduce)')
    : { matches: false, addEventListener: null };

  function systemPrefersReducedMotion() {
    return !!(prefersReducedMotion && prefersReducedMotion.matches);
  }

  function paintMotionSwitch() {
    if (!btnReduceMotion) return;
    var on = reduceMotion;
    btnReduceMotion.setAttribute('aria-checked', on ? 'true' : 'false');
    btnReduceMotion.classList.toggle('active', on);
    if (reduceMotionState) {
      reduceMotionState.textContent = on ? t('switch.on') : t('switch.off');
    }
  }

  function applyMotion(on) {
    // 'unset' is never sent back: by this point the system preference has
    // been folded in, and the attribute is always a real answer.
    body.setAttribute('data-reduce-motion', on ? 'true' : 'false');
    reduceMotion = on;
    paintMotionSwitch();
  }

  reduceMotion = body.getAttribute('data-reduce-motion') === 'true';
  if (body.getAttribute('data-reduce-motion') === 'unset') {
    // First run, or nobody has chosen yet: follow the system without
    // writing anything to disk, so a later change to the system setting
    // still takes effect.
    reduceMotion = systemPrefersReducedMotion();
    body.setAttribute('data-reduce-motion', reduceMotion ? 'true' : 'false');
  }
  paintMotionSwitch();

  // While nothing has been chosen, a change in the system setting should
  // take effect without a reload. Once the reader has chosen, their choice
  // stands and the system no longer gets a say here.
  var motionChosenByReader = body.getAttribute('data-reduce-motion') !== 'unset';
  if (prefersReducedMotion && prefersReducedMotion.addEventListener) {
    prefersReducedMotion.addEventListener('change', function () {
      if (!motionChosenByReader) applyMotion(systemPrefersReducedMotion());
    });
  }

  if (btnReduceMotion) {
    btnReduceMotion.addEventListener('click', function () {
      applyMotion(!reduceMotion);
      motionChosenByReader = true;
      saveConfig({ reduce_motion: reduceMotion });
    });
  }

  // ---------- Frosted panels ----------
  // A look, not a legibility aid. The switch is off until asked for, and it
  // only ever changes panels and bars - the editor and the text behind it
  // keep their solid background, so turning it on cannot cost contrast on
  // the words the reader is actually trying to read.
  // A material name is only ever one of these four, because the server
  // will not save anything else. The fallback is 'off' rather than the
  // attribute's raw value: a bad value in the DOM should leave the panels
  // solid, never leave them in some half-understood material.
  var MATERIALS = ['off', 'mica', 'frosted', 'acrylic'];
  // Same shape the server accepts (HEX_COLOR_RE in routes.py): 3- or
  // 6-digit only. Alpha forms are refused on both sides, because alpha is
  // how a colour silently becomes unreadable.
  var GLASS_HEX_RE = /^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$/;
  var glassMaterial = body.getAttribute('data-glass-material');
  if (MATERIALS.indexOf(glassMaterial) === -1) glassMaterial = 'off';
  // The reader's own choice, not the colour the panels ended up painted in.
  // The two differ whenever the choice had to be faded toward the theme's
  // panel to keep the text on it readable, and only the choice is ever saved
  // back: saving the painted colour instead would quietly rewrite their red
  // into a darker red the first time they touched anything else.
  var glassTint = (body.getAttribute('data-glass-choice') || '').trim();

  function applyGlassMaterial(name) {
    body.setAttribute('data-glass-material', name);
  }

  // The panel colour and the text colours that sit on it, both from the table
  // the server embedded, for the theme that is showing now.
  //
  // Read from the page rather than from /api/themes on purpose. That fetch may
  // still be in flight when the reader picks a colour, and falling back to the
  // placeholder background mixes the tint against a panel no reader ever sees.
  function panelInfo() {
    return PANEL_INFO[themeSelect.value] || null;
  }

  // The colour the panels are actually painted in. This is the reader's choice
  // pulled toward the theme's panel colour until that theme's own text stays
  // readable on it, so it cannot cost contrast however vivid the choice was.
  // tint.js does the arithmetic and its Python twin does the same for the first
  // paint.
  function panelColour() {
    var info = panelInfo();
    if (info && info.panel) return info.panel;
    var palette = themePalette[themeSelect.value] || themePalette;
    return palette.gutter_bg || palette.bg || '';
  }

  // The three text colours the current theme puts on a panel, which is what
  // the tint is checked against. A theme missing from the embedded table falls
  // back to no check, and tint.js then hands back the panel colour itself: the
  // reader asked for something the app cannot show is readable, so it errs
  // toward the theme rather than toward a guess. That only happens if the
  // table and the theme list have drifted apart, which
  // tests/test_panel_materials.py fails on.
  function panelTexts() {
    var info = panelInfo();
    return info && info.texts ? info.texts : null;
  }

  function applyGlassTint(hex) {
    glassTint = hex || '';
    var safe = '';
    if (glassTint && panelColour()) {
      try {
        safe = AccessibleTint.safePanelTint(
          glassTint, panelColour(), panelTexts());
      } catch (error) {
        // An unusable colour is caught by the field's own error message.
        // Here it just means the panels keep the theme colour, which is
        // the safe answer and never a blank one.
        safe = '';
      }
    }
    body.setAttribute('data-glass-tint', safe);
    // The property is removed rather than set to an empty string: the CSS
    // reads it with a fallback, and an empty --glass-tint would win the
    // cascade and leave nothing to blend with.
    if (safe) body.style.setProperty('--glass-tint', safe);
    else body.style.removeProperty('--glass-tint');
  }

  applyGlassMaterial(glassMaterial);
  applyGlassTint(glassTint);

  Array.prototype.forEach.call(
    document.querySelectorAll('input[name="glass-material"]'),
    function (radio) {
      radio.checked = radio.value === glassMaterial;
      radio.addEventListener('change', function () {
        if (!radio.checked) return;
        glassMaterial = radio.value;
        applyGlassMaterial(glassMaterial);
        saveConfig({ glass_material: glassMaterial });
      });
    }
  );

  var tintPicker = document.getElementById('glass-tint-picker');
  var tintHex = document.getElementById('glass-tint-hex');
  var tintError = document.getElementById('glass-tint-error');
  var tintReset = document.getElementById('glass-tint-reset');

  function setTintError(message) {
    if (!tintError) return;
    tintError.textContent = message || '';
    tintError.hidden = !message;
    if (tintHex) tintHex.setAttribute('aria-invalid', message ? 'true' : 'false');
  }

  function commitTint(hex, save) {
    applyGlassTint(hex);
    setTintError('');
    if (save) saveConfig({ glass_tint: glassTint });
  }

  if (tintPicker) {
    tintPicker.addEventListener('input', function () {
      commitTint(tintPicker.value, false);
      if (tintHex) tintHex.value = tintPicker.value;
    });
    tintPicker.addEventListener('change', function () {
      saveConfig({ glass_tint: glassTint });
    });
  }

  // Same rule as the highlight-colour field, and for the same reason: an
  // unfinished colour is not applied and not complained about until the
  // reader leaves the field. A red box appearing after the first keystroke
  // of "#223344" would be discouraging, and they cannot have made a
  // mistake they have not finished expressing.
  function onTintInput() {
    var value = (tintHex.value || '').trim();
    if (value === '') {
      commitTint('', false);
      return;
    }
    if (!GLASS_HEX_RE.test(value)) return;
    setTintError('');
    if (tintPicker) tintPicker.value = expandHex(value);
    applyGlassTint(value);
  }

  if (tintHex) {
    tintHex.addEventListener('input', onTintInput);
    tintHex.addEventListener('change', function () {
      var value = (tintHex.value || '').trim();
      if (GLASS_HEX_RE.test(value)) {
        setTintError('');
        commitTint(value, true);
      } else if (value === '') {
        // Empty means "follow the theme", which is a real answer rather
        // than an unfinished one, so it is saved as it stands.
        setTintError('');
        commitTint('', true);
      } else {
        setTintError(t('try.error_not_hex'));
      }
    });
  }

  if (tintReset) {
    tintReset.addEventListener('click', function () {
      setTintError('');
      commitTint('', true);
      if (tintHex) tintHex.value = '';
      // The picker always needs a real colour to show, so it returns to the
      // theme's own rather than to blank. Read from the DOM, so switching
      // theme while a tint is set still lands on the right colour.
      var themeColour = tintPicker && tintPicker.getAttribute('data-theme-colour');
      if (tintPicker && themeColour) tintPicker.value = themeColour;
    });
  }

  // ---------- Language ----------
  // Changing the language re-renders the whole page rather than swapping
  // text in place. Every string in the app comes from one catalogue, so the
  // server can produce a page that is entirely in the new language --
  // including the parts that live in HTML attributes, which a client-side
  // pass would leave behind in the old language. The setting is saved
  // first so a reload in the new language cannot bounce back.
  if (languageSelect) {
    languageSelect.addEventListener('change', function () {
      var chosen = languageSelect.value;
      if (!chosen || chosen === META.locale) return;
      body.setAttribute('data-locale', chosen);
      saveConfig({ locale: chosen }).then(function () {
        window.location.reload();
      });
    });
  }

  fontSelect.addEventListener('change', function () {
    applyFont(fontSelect.value);
    body.setAttribute('data-font', fontSelect.value);
    updateFontNote();
    updatePreview();
    saveConfig({ font: fontSelect.value });
  });

  // A theme change moves the panel colour under the tint, so the tint has to
  // be worked out again. Saved first so a theme change made while the
  // Settings panel is closed is not silently lost.
  themeSelect.addEventListener('change', function () {
    applyGlassTint(glassTint);
    if (tintPicker) {
      var panel = panelColour();
      if (panel) {
        tintPicker.value = panel;
        tintPicker.setAttribute('data-theme-colour', panel);
      }
    }
  });

  // ---------- Try it out panel ----------
  // Fonts taken from the computer are not guaranteed to exist on every
  // machine, so the panel says which one is in use rather than leaving
  // the reader to wonder why Arial looks like Liberation Sans.
  function updateFontNote() {
    if (!fontBundledNote || !fontSelect) return;
    var option = fontSelect.options[fontSelect.selectedIndex];
    var bundled = option && option.getAttribute('data-bundled') === 'true';
    var note = option ? option.textContent : '';
    fontBundledNote.textContent = bundled
      ? t('try.bundled', note)
      : t('try.system_font', note);
    fontBundledNote.hidden = false;
  }

  function updatePreview() {
    if (!fontPreview) return;
    var palette = themePalette[themeSelect.value] || themePalette;
    var shown = contrastAdjust(palette.fg);
    var option = fontSelect.options[fontSelect.selectedIndex];
    var name = option ? option.textContent : t('try.your_font');
    var sample = sampleText && sampleText.value ? sampleText.value : ' ';

    fontPreview.style.fontFamily = fontFamilyFor(fontSelect.value);
    fontPreview.style.fontSize = fontSize.value + 'px';
    // The preview uses the editor's own background and the same resolved
    // text colour, so it cannot drift from what the editor will show.
    if (palette.bg) fontPreview.style.backgroundColor = palette.bg;
    fontPreview.style.color = shown;

    if (fontPreviewText) fontPreviewText.textContent = sample;

    if (previewStatus) {
      previewStatus.textContent = t('try.status_theme', name);
    }
  }

  function expandHex(value) {
    return value.length === 7
      ? value
      : '#' + value[1] + value[1] + value[2] + value[2] + value[3] + value[3];
  }

  // ---------- Highlight colour ----------
  // The highlight is a background, so the nudge fades it toward the
  // theme's background until the theme's text clears AA on it, instead
  // of moving a text colour away from the background. The reader's hue
  // is kept either way, and the status line says when the app has
  // adjusted their choice.

  function setHighlightColor(hex, persist) {
    customHighlightColor = hex || '';
    body.setAttribute('data-highlight-color', customHighlightColor);
    applyTheme(themeSelect.value);
    updateHighlightStatus();
    if (persist) saveConfig({ highlight_color: customHighlightColor });
  }

  function showHighlightError(message) {
    if (!highlightError) return;
    highlightError.textContent = message || '';
    highlightError.hidden = !message;
    if (highlightColorHex) {
      highlightColorHex.setAttribute('aria-invalid', message ? 'true' : 'false');
    }
  }

  function updateHighlightStatus() {
    if (!highlightStatus) return;
    if (!customHighlightColor) {
      highlightStatus.hidden = true;
      highlightStatus.textContent = '';
      return;
    }
    var palette = themePalette[themeSelect.value] || themePalette;
    var shown = ensureHighlightReadable(
      customHighlightColor, palette.bg, palette.fg);
    var nudged = shown.toLowerCase() !== customHighlightColor.toLowerCase();
    highlightStatus.textContent = nudged
      ? t('try.status_nudged', shown)
      : '';
    highlightStatus.hidden = !nudged;
  }

  function onHighlightHexInput() {
    var value = (highlightColorHex.value || '').trim();
    if (value === '') {
      showHighlightError('');
      setHighlightColor('', false);
      return;
    }
    if (!/^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$/.test(value)) return;
    showHighlightError('');
    if (highlightColorPicker) highlightColorPicker.value = expandHex(value);
    setHighlightColor(value, false);
  }

  if (highlightColorHex) {
    highlightColorHex.addEventListener('input', onHighlightHexInput);
    highlightColorHex.addEventListener('change', function () {
      var value = (highlightColorHex.value || '').trim();
      if (/^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$/.test(value)) {
        showHighlightError('');
        setHighlightColor(value, true);
      } else if (value === '') {
        showHighlightError('');
        setHighlightColor('', true);
      } else {
        showHighlightError(t('try.error_not_hex'));
      }
    });
  }

  if (highlightColorPicker) {
    highlightColorPicker.addEventListener('input', function () {
      if (highlightColorHex) highlightColorHex.value = highlightColorPicker.value;
      showHighlightError('');
      setHighlightColor(highlightColorPicker.value, false);
    });
    highlightColorPicker.addEventListener('change', function () {
      if (highlightColorHex) highlightColorHex.value = highlightColorPicker.value;
      showHighlightError('');
      setHighlightColor(highlightColorPicker.value, true);
    });
  }

  if (btnResetHighlight) {
    btnResetHighlight.addEventListener('click', function () {
      if (highlightColorHex) highlightColorHex.value = '';
      showHighlightError('');
      setHighlightColor('', true);
      if (highlightColorHex) highlightColorHex.focus();
    });
  }

  if (sampleText) {
    sampleText.addEventListener('input', updatePreview);
  }

  fontSize.addEventListener('input', function () {
    applyFontSize(parseInt(fontSize.value, 10));
  });

  fontSize.addEventListener('change', function () {
    saveConfig({ font_size: parseInt(fontSize.value, 10) });
  });

  lineHeight.addEventListener('input', function () {
    applyLineHeight(lineHeight.value);
    paintStepperLimits();
  });

  lineHeight.addEventListener('change', function () {
    saveConfig({ line_height: parseFloat(lineHeight.value) });
  });

  letterSpacing.addEventListener('input', function () {
    applyLetterSpacing(letterSpacing.value);
    paintStepperLimits();
  });

  letterSpacing.addEventListener('change', function () {
    saveConfig({ letter_spacing: parseFloat(letterSpacing.value) });
  });

  blurIntensity.addEventListener('input', function () {
    applyBlurIntensity(blurIntensity.value);
  });

  blurIntensity.addEventListener('change', function () {
    saveConfig({ blur_intensity: parseFloat(blurIntensity.value) });
  });

  themeSelect.addEventListener('change', function () {
    applyTheme(themeSelect.value);
    body.setAttribute('data-theme', themeSelect.value);
    syncThemeBuilder();
    saveConfig({ theme: themeSelect.value });
  });

  // ---------- Theme builder ----------
  // The reader's own theme. Seven colours are picked; the rest of the
  // palette is derived from them (customPalette above, mirrored from
  // custom_palette in routes.py). The server is the authority on what gets
  // saved; the browser copy exists so a pick previews live.
  var themeBuilder = document.getElementById('theme-builder');
  var themeBuilderFields = ['bg', 'fg', 'keyword', 'string', 'comment', 'number', 'function'];
  var themeCustomReset = document.getElementById('theme-custom-reset');
  var themeCustomSaved = document.getElementById('theme-custom-saved');

  function syncThemeBuilder() {
    if (!themeBuilder) return;
    themeBuilder.hidden = themeSelect.value !== 'custom';
  }

  function customFieldHex(key) {
    return document.getElementById('theme-custom-' + key);
  }

  function customFieldPicker(key) {
    return document.getElementById('theme-custom-' + key + '-picker');
  }

  function customFieldStatus(key) {
    return document.getElementById('theme-custom-' + key + '-status');
  }

  function buildCustomPalette() {
    var picks = {};
    themeBuilderFields.forEach(function (key) {
      picks[key] = customFieldHex(key).value;
    });
    return customPalette(picks);
  }

  // The contrast of a raw pick against the picked background, shown under
  // the field. The server clamps a pick that fails, so this is a preview
  // of what will happen to the colour, not a rejection of it.
  function paintCustomStatus(key) {
    var status = customFieldStatus(key);
    if (!status) return;
    var bg = customFieldHex('bg').value;
    var colour = customFieldHex(key).value;
    var ratio = 0;
    try {
      ratio = AccessibleTint.contrastRatio(
        AccessibleTint.parseHex(colour), AccessibleTint.parseHex(bg));
    } catch (error) {
      status.hidden = true;
      return;
    }
    status.hidden = false;
    status.textContent = ratio >= 4.5
      ? t('theme.custom_contrast_ok')
      : t('theme.custom_contrast_fail');
  }

  function repaintCustomTheme() {
    var palette;
    try {
      palette = buildCustomPalette();
    } catch (error) {
      return; // a field is mid-typing; the save validates it
    }
    themePalette.custom = palette;
    if (themeSelect.value === 'custom') {
      applyTheme('custom');
      applyGlassTint(glassTint);
    }
    themeBuilderFields.forEach(paintCustomStatus);
  }

  function saveCustomTheme() {
    var payload = {};
    themeBuilderFields.forEach(function (key) {
      payload['theme_custom_' + key] = customFieldHex(key).value;
    });
    return saveConfig(payload).then(function () {
      if (themeCustomSaved) {
        themeCustomSaved.hidden = false;
        themeCustomSaved.textContent = t('theme.custom_saved');
      }
    });
  }

  if (themeBuilder) {
    themeBuilderFields.forEach(function (key) {
      var hex = customFieldHex(key);
      var picker = customFieldPicker(key);
      if (hex) {
        hex.addEventListener('input', function () {
          if (picker && /^#[0-9a-fA-F]{6}$/.test(hex.value)) picker.value = hex.value;
          repaintCustomTheme();
        });
        hex.addEventListener('change', function () {
          saveCustomTheme();
        });
      }
      if (picker) {
        picker.addEventListener('input', function () {
          hex.value = picker.value;
          repaintCustomTheme();
        });
        picker.addEventListener('change', function () {
          saveCustomTheme();
        });
      }
    });
    if (themeCustomReset) {
      themeCustomReset.addEventListener('click', function () {
        // The defaults are the high-contrast theme's colours, the same
        // values DEFAULT_CONFIG starts with in routes.py.
        var defaults = {
          bg: '#0b0b0b', fg: '#ffffff', keyword: '#ff9a9a',
          string: '#93e6a8', comment: '#b4b4b4', number: '#ffd93d',
          function: '#93d4ff'
        };
        themeBuilderFields.forEach(function (key) {
          customFieldHex(key).value = defaults[key];
          customFieldPicker(key).value = defaults[key];
        });
        repaintCustomTheme();
        saveCustomTheme();
      });
    }
  }

  // ---------- Background gradient ----------
  // A very subtle pull of the background toward the foreground colour, so
  // the page is not a flat slab. It is off by default for readers who find
  // any movement of tone distracting, and it never touches text.
  var themeGradient = document.getElementById('theme-gradient');
  var themeGradientState = document.getElementById('theme-gradient-state');

  function applyThemeGradient(on) {
    body.setAttribute('data-gradient', on ? 'on' : 'off');
    if (themeGradientState) themeGradientState.textContent = on
      ? t('switch.on') : t('switch.off');
  }

  if (themeGradient) {
    themeGradient.addEventListener('click', function () {
      var on = themeGradient.getAttribute('aria-checked') !== 'true';
      themeGradient.setAttribute('aria-checked', on ? 'true' : 'false');
      themeGradient.classList.toggle('active', on);
      applyThemeGradient(on);
      saveConfig({ theme_gradient: on });
    });
  }

  contrastSelect.addEventListener('change', function () {
    applyContrast(contrastSelect.value);
    saveConfig({ contrast: contrastSelect.value });
  });

  focusMode.addEventListener('change', function () {
    applyFocusMode(focusMode.value);
    syncBlurField();
    saveConfig({ focus_mode: focusMode.value });
  });

  ttsVoice.addEventListener('change', function () {
    speechVoiceName = ttsVoice.value;
    saveConfig({ tts_voice: speechVoiceName });
  });

  ttsRate.addEventListener('input', function () {
    speechRate = parseFloat(ttsRate.value);
    ttsRateLabel.textContent = speechRate.toFixed(1) + 'x';
  });
  ttsRate.addEventListener('change', function () {
    saveConfig({ tts_rate: speechRate });
  });

  // ---------- Hover and click settings ----------
  // The delay is shown in whichever unit the reader can picture: 600 means
  // nothing, 1500 means something. Asking someone to translate 1200 into
  // "is that a long pause" is the kind of small arithmetic that gets in
  // the way of the thing being read.
  function paintHoverDelay(ms) {
    if (!ttsHoverDelayLabel) return;
    if (ms >= 1000) {
      ttsHoverDelayLabel.textContent = (ms / 1000).toFixed(1) + 's';
    } else {
      ttsHoverDelayLabel.textContent = ms + 'ms';
    }
  }

  function paintClickSwitch() {
    if (!ttsClickEl) return;
    ttsClickEl.setAttribute('aria-checked', ttsClickToSpeak ? 'true' : 'false');
    ttsClickEl.classList.toggle('active', ttsClickToSpeak);
    if (ttsClickState) {
      ttsClickState.textContent = ttsClickToSpeak ? t('speak.on') : t('speak.off');
    }
  }

  if (ttsHoverScopeEl) {
    ttsHoverScopeEl.addEventListener('change', function () {
      ttsHoverScopeValue = ttsHoverScopeEl.value;
      // Anything already waiting would now be speaking the wrong amount of
      // the page, so it is dropped rather than left to arrive late.
      clearHover();
      saveConfig({ tts_hover_scope: ttsHoverScopeValue });
    });
  }

  if (ttsHoverDelay) {
    ttsHoverDelay.addEventListener('input', function () {
      ttsHoverDelayMs = parseFloat(ttsHoverDelay.value);
      paintHoverDelay(ttsHoverDelayMs);
    });
    ttsHoverDelay.addEventListener('change', function () {
      saveConfig({ tts_hover_delay: ttsHoverDelayMs });
    });
  }

  if (ttsVoiceGenderEl) {
    ttsVoiceGenderEl.addEventListener('change', function () {
      ttsVoiceGenderValue = ttsVoiceGenderEl.value;
      // The list is in the order the app would choose from, so it has to be
      // rebuilt here too. Otherwise the picker still shows the old
      // preference's order, and the voice actually being used is nowhere
      // near the top of it.
      loadVoices();
      saveConfig({ tts_voice_gender: ttsVoiceGenderValue });
    });
  }

  if (ttsClickEl) {
    ttsClickEl.addEventListener('click', function () {
      ttsClickToSpeak = !ttsClickToSpeak;
      paintClickSwitch();
      saveConfig({ tts_click_to_speak: ttsClickToSpeak });
    });
  }


  // ---------- Updates ----------
  // Two things live here and they are deliberately not the same thing: the
  // switch turns the once-a-day background check off, and the button asks
  // right now. A reader who has switched the check off can still ask, and a
  // reader who asks always gets an answer.
  var autoUpdateOn = false;
  var updateApplicable = false;
  var updateBusy = false;

  function say(text, isError) {
    if (!updateStatus) return;
    updateStatus.textContent = text || '';
    updateStatus.classList.toggle('is-error', !!isError);
  }

  // The download row is only offered when there is something to download.
  // Showing an empty button that quietly does nothing is worse than showing
  // nothing at all.
  function showInstallRow(show) {
    if (updateInstallRow) updateInstallRow.hidden = !show;
  }

  function setUpdateControlsDisabled(disabled) {
    if (btnCheckUpdate) btnCheckUpdate.disabled = disabled;
    if (btnInstallUpdate) btnInstallUpdate.disabled = disabled;
  }

  function paintAutoUpdateSwitch() {
    if (!autoUpdateEl) return;
    autoUpdateEl.setAttribute('aria-checked', autoUpdateOn ? 'true' : 'false');
    autoUpdateEl.classList.toggle('active', autoUpdateOn);
    if (autoUpdateState) {
      autoUpdateState.textContent = autoUpdateOn ? t('speak.on') : t('speak.off');
    }
  }

  // A check the reader did not ask for is quiet unless it found something.
  // The one exception is the website, which cannot update itself at all, and
  // that is said once so the switch is not a control that does nothing.
  function reportCheck(result) {
    if (!result || result.success === false) return;
    if (!result.applicable) {
      showInstallRow(false);
      say(t('update.status_not_applicable'));
      return;
    }
    if (result.update_available) {
      showInstallRow(true);
      say(t('update.status_available', result.latest || ''), false);
      return;
    }
    showInstallRow(false);
    if (result.error === 'checked_recently') return;
    if (result.error) {
      // The server sends a sentence already in the reader's language.
      say(result.error_text || t('update.error_unknown'), true);
      return;
    }
    say(result.manual === false && !autoUpdateOn
      ? t('update.status_off')
      : t('update.status_current', result.current || ''));
  }

  function checkForUpdates(manual) {
    if (updateBusy) return Promise.resolve(null);
    updateBusy = true;
    if (btnCheckUpdate) btnCheckUpdate.disabled = true;
    if (manual) say(t('update.status_checking'));
    return fetch('/api/update/check', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ force: !!manual, access_code: accessCode, locale: META.locale })
    })
      .then(function (res) {
        return res.json().then(function (data) {
          data.manual = !!manual;
          return data;
        });
      })
      .then(function (data) {
        reportCheck(data);
        return data;
      })
      .catch(function () {
        say(t('update.error_network'), true);
        return null;
      })
      .then(function (data) {
        updateBusy = false;
        setUpdateControlsDisabled(false);
        return data;
      });
  }

  // Downloads the new build and checks it. Nothing is replaced here, and
  // nothing is closed: the download is checked, the app carries on, and the
  // swap happens the next time the reader closes the app themselves.
  //
  // The request is not sent until they ask, so nothing changes on their disk
  // without them choosing to. The one thing that does change without asking
  // is the check, which is the part the switch in Settings controls.
  function installUpdate() {
    if (updateBusy) return Promise.resolve(null);
    updateBusy = true;
    setUpdateControlsDisabled(true);
    say(t('update.status_downloading'));
    return fetch('/api/update/install', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ access_code: accessCode, locale: META.locale })
    })
      .then(function (res) {
        return res.json().then(function (data) { return { ok: res.ok, data: data }; });
      })
      .then(function (answer) {
        if (!answer.ok || answer.data.success === false) {
          // The server sends a sentence already in the reader's language.
          // The access-code refusal arrives under a different name, because
          // it is not an updater error at all.
          say(answer.data.error_text || answer.data.error || t('update.error_unknown'), true);
          return null;
        }
        // The row has done its job. Leaving it up would ask again for a
        // build that is already downloaded and waiting.
        showInstallRow(false);
        say(t('update.status_ready', answer.data.version || ''));
        return answer.data;
      })
      .catch(function () {
        say(t('update.error_network'), true);
        return null;
      })
      .then(function (data) {
        updateBusy = false;
        setUpdateControlsDisabled(false);
        return data;
      });
  }

  function startUpdateSection() {
    if (!autoUpdateEl) return;
    autoUpdateOn = autoUpdateEl.getAttribute('aria-checked') === 'true';
    paintAutoUpdateSwitch();
    showInstallRow(false);

    fetch('/api/version')
      .then(function (res) { return res.json(); })
      .then(function (info) {
        updateApplicable = !!info.applicable;
        if (updateVersion) {
          updateVersion.textContent = t('update.version_line', info.version || '');
        }
        if (!updateApplicable) {
          // Nothing here can change a file on the reader's computer, so the
          // switch and buttons would be controls that do nothing. Say so
          // instead of leaving them looking live.
          if (autoUpdateEl) autoUpdateEl.disabled = true;
          if (btnCheckUpdate) btnCheckUpdate.disabled = true;
          showInstallRow(false);
          say(t('update.status_not_applicable'));
          return;
        }
        if (autoUpdateOn) checkForUpdates(false);
      })
      .catch(function () {
        if (updateVersion) updateVersion.textContent = '';
      });
  }

  if (autoUpdateEl) {
    autoUpdateEl.addEventListener('click', function () {
      autoUpdateOn = !autoUpdateOn;
      paintAutoUpdateSwitch();
      say('');
      saveConfig({ auto_update: autoUpdateOn });
      // Turning it on is a request to start looking, not just to remember a
      // preference for tomorrow. Turning it off stops asking, and says so.
      if (autoUpdateOn) {
        checkForUpdates(false);
      } else {
        say(t('update.status_off'));
      }
    });
  }

  if (updateChannelEl) {
    updateChannelEl.addEventListener('change', function () {
      // The server reads the channel out of the saved config, so the check
      // has to wait for the save or it asks about the channel the reader
      // just left. Forcing it also matters: without force, the once-a-day
      // guard answers "checked recently" and the change looks like it did
      // nothing.
      saveConfig({ update_channel: updateChannelEl.value }).then(function (result) {
        // If the save did not land, the server is still on the old channel.
        // Asking anyway would replace the answer on screen with one about a
        // channel the reader has just left, which is the one mistake here
        // that gives no sign of being wrong. saveConfig has already said the
        // setting was not kept, so leave the old answer standing.
        if (!result || !result.ok) return;
        if (autoUpdateOn) {
          checkForUpdates(true);
        } else {
          // No automatic checking, so no request to make. The status is
          // cleared because whatever it says is about the old channel.
          say('');
        }
      });
    });
  }

  // ---------- Developer mode ----------
  // Hidden on purpose: it is for the people building the app, not for the
  // readers. Right-clicking the Settings button (or pressing Shift+F10 on
  // it) adds the "dev" update channel to the channel list. The choice is
  // remembered in localStorage, so it survives a reload but stays on this
  // machine. Turning it off removes the channel again.
  var devMode = false;

  function ensureDevOption() {
    if (!updateChannelEl) return;
    var devOption = updateChannelEl.querySelector('option[value="dev"]');
    if (devMode && !devOption) {
      var option = document.createElement('option');
      option.value = 'dev';
      option.textContent = t('update.channel_dev');
      updateChannelEl.appendChild(option);
    } else if (!devMode && devOption) {
      // Leaving dev mode while the dev channel is chosen would strand the
      // reader on a channel they can no longer see. Fall back to beta, the
      // default, and save it so the server agrees.
      if (updateChannelEl.value === 'dev') {
        updateChannelEl.value = 'beta';
        saveConfig({ update_channel: 'beta' });
      }
      devOption.remove();
    }
  }

  function setDevMode(on) {
    devMode = on;
    try {
      localStorage.setItem('accessible_ide_dev_mode', on ? '1' : '0');
    } catch (error) {
      // Storage can be unavailable (private mode, some embedded browsers).
      // The mode still works for this page load.
    }
    ensureDevOption();
    say(on ? t('update.dev_mode_on') : t('update.dev_mode_off'));
  }

  function toggleDevMode() {
    setDevMode(!devMode);
  }

  if (btnSettings) {
    btnSettings.addEventListener('contextmenu', function (event) {
      event.preventDefault();
      toggleDevMode();
    });
    btnSettings.addEventListener('keydown', function (event) {
      if (event.key === 'F10' && event.shiftKey) {
        event.preventDefault();
        toggleDevMode();
      }
    });
  }

  try {
    devMode = localStorage.getItem('accessible_ide_dev_mode') === '1';
  } catch (error) {
    devMode = false;
  }
  ensureDevOption();

  if (btnCheckUpdate) {
    btnCheckUpdate.addEventListener('click', function () {
      checkForUpdates(true);
    });
  }

  if (btnInstallUpdate) {
    btnInstallUpdate.addEventListener('click', function () {
      installUpdate();
    });
  }

  startUpdateSection();



  btnTestVoice.addEventListener('click', function () {
    speak(t('speak.demo'));
  });

  btnSettings.addEventListener('click', openSettings);

  settingsDialog.addEventListener('cancel', function (event) {
    // Escape was pressed. Let the dialog close itself, then put focus
    // back on the button that opened it.
    event.preventDefault();
    closeSettings();
  });

  if (btnSettingsClose) {
    btnSettingsClose.addEventListener('click', function (event) {
      event.preventDefault();
      closeSettings();
    });
  }

  // ---------- Resizable panes ----------
  // The workspace is a split view: the editor on the left, the output on
  // the right, and the shell below the output when it is open. The dividers
  // are separators, so a reader who cannot use a mouse can still resize
  // with the arrow keys, and a screen reader hears the current size as a
  // percentage.
  //
  // The sizes live in CSS variables on the two containers, and a drag only
  // rewrites the numbers. The layout itself stays in the stylesheet, where
  // a narrow screen can fall back to stacked panes without this script
  // having to know about it.
  var workspaceEl = document.getElementById('workspace');
  var rightColumn = document.getElementById('right-column');
  var dividerMain = document.getElementById('divider-main');
  var dividerShell = document.getElementById('divider-shell');
  var LAYOUT_KEY = 'accessible_ide_layout';
  var MIN_PCT = 20;
  var MAX_PCT = 80;
  var editorWidthPct = 50;
  var shellHeightPct = 40;

  function clampPct(value) {
    return Math.min(MAX_PCT, Math.max(MIN_PCT, value));
  }

  function applyLayout() {
    if (workspaceEl) workspaceEl.style.setProperty('--editor-width', editorWidthPct + '%');
    if (rightColumn) rightColumn.style.setProperty('--shell-height', shellHeightPct + '%');
    if (dividerMain) dividerMain.setAttribute('aria-valuenow', String(editorWidthPct));
    if (dividerShell) dividerShell.setAttribute('aria-valuenow', String(shellHeightPct));
  }

  // The layout is the reader's own: where they put a divider is where it
  // stays, on this browser. A corrupt value is ignored and the defaults
  // stand, the same way a hand-edited config file is.
  try {
    var savedLayout = JSON.parse(localStorage.getItem(LAYOUT_KEY) || '{}');
    if (typeof savedLayout.editorWidth === 'number') editorWidthPct = clampPct(savedLayout.editorWidth);
    if (typeof savedLayout.shellHeight === 'number') shellHeightPct = clampPct(savedLayout.shellHeight);
  } catch (e) { /* defaults stand */ }
  applyLayout();

  function saveLayout() {
    try {
      localStorage.setItem(LAYOUT_KEY, JSON.stringify({
        editorWidth: editorWidthPct,
        shellHeight: shellHeightPct
      }));
    } catch (e) { /* a full or blocked store is not worth a dialog */ }
  }

  function startPaneDrag(e, axis) {
    // Only the primary button drags. A right-click must not start a resize.
    if (e.button && e.button !== 0) return;
    e.preventDefault();
    var divider = axis === 'vertical' ? dividerMain : dividerShell;
    if (!divider) return;
    if (divider.setPointerCapture) {
      try { divider.setPointerCapture(e.pointerId); } catch (err) { /* already released */ }
    }
    var startX = e.clientX;
    var startY = e.clientY;
    var startWidth = editorWidthPct;
    var startHeight = shellHeightPct;
    var moved = false;

    function onMove(ev) {
      if (axis === 'vertical') {
        var width = workspaceEl && workspaceEl.getBoundingClientRect ?
          workspaceEl.getBoundingClientRect().width : 0;
        if (width > 0) {
          editorWidthPct = clampPct(startWidth + ((ev.clientX - startX) / width) * 100);
          moved = true;
        }
      } else {
        var height = rightColumn && rightColumn.getBoundingClientRect ?
          rightColumn.getBoundingClientRect().height : 0;
        if (height > 0) {
          // The divider is the shell's top edge, so dragging it down makes
          // the shell shorter. The delta is subtracted for that reason.
          shellHeightPct = clampPct(startHeight - ((ev.clientY - startY) / height) * 100);
          moved = true;
        }
      }
      applyLayout();
    }

    function onUp() {
      divider.removeEventListener('pointermove', onMove);
      divider.removeEventListener('pointerup', onUp);
      divider.removeEventListener('pointercancel', onUp);
      if (moved) {
        saveLayout();
        // CodeMirror lays out to the size it was given. After a drag it has
        // to be told the editor pane changed, or the text keeps the old
        // width until the next window resize.
        if (typeof editor.refresh === 'function') editor.refresh();
      }
    }

    divider.addEventListener('pointermove', onMove);
    divider.addEventListener('pointerup', onUp);
    divider.addEventListener('pointercancel', onUp);
  }

  function nudgePane(axis, delta) {
    if (axis === 'vertical') {
      editorWidthPct = clampPct(editorWidthPct + delta);
    } else {
      shellHeightPct = clampPct(shellHeightPct + delta);
    }
    applyLayout();
    saveLayout();
    if (typeof editor.refresh === 'function') editor.refresh();
  }

  if (dividerMain) {
    dividerMain.addEventListener('pointerdown', function (e) { startPaneDrag(e, 'vertical'); });
    dividerMain.addEventListener('keydown', function (e) {
      var step = e.shiftKey ? 10 : 5;
      if (e.key === 'ArrowLeft') { e.preventDefault(); nudgePane('vertical', -step); }
      else if (e.key === 'ArrowRight') { e.preventDefault(); nudgePane('vertical', step); }
      else if (e.key === 'Home') { e.preventDefault(); nudgePane('vertical', -100); }
      else if (e.key === 'End') { e.preventDefault(); nudgePane('vertical', 100); }
    });
  }
  if (dividerShell) {
    dividerShell.addEventListener('pointerdown', function (e) { startPaneDrag(e, 'horizontal'); });
    dividerShell.addEventListener('keydown', function (e) {
      var step = e.shiftKey ? 10 : 5;
      // The divider is the shell's top edge: ArrowUp moves it up and makes
      // the shell taller, ArrowDown moves it down and makes it shorter.
      if (e.key === 'ArrowUp') { e.preventDefault(); nudgePane('horizontal', step); }
      else if (e.key === 'ArrowDown') { e.preventDefault(); nudgePane('horizontal', -step); }
      else if (e.key === 'Home') { e.preventDefault(); nudgePane('horizontal', -100); }
      else if (e.key === 'End') { e.preventDefault(); nudgePane('horizontal', 100); }
    });
  }

  // The Python shell.
  //
  // Deliberately not the runner above. The runner is for handing in a file
  // and getting its output; this is for trying things and keeping what you
  // tried. Everything you define here is still here in your next command,
  // which is the whole difference.
  //
  // The session id comes back from the server and rides along with every
  // command. That is not ceremony: on the hosted copy it is the only thing
  // keeping one reader's variables out of another reader's shell.
  var shellPane = document.getElementById('shell-pane');
  var btnShell = document.getElementById('btn-shell');
  var shellInput = document.getElementById('shell-input');
  var shellOutput = document.getElementById('shell-output');
  var shellStatus = document.getElementById('shell-status');
  var btnShellRun = document.getElementById('shell-run');
  var btnShellClear = document.getElementById('shell-clear');
  var btnShellClose = document.getElementById('shell-close');
  var shellSession = null;
  var shellBusy = false;

  function shellPost(url, code) {
    return fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session: shellSession,
        access_code: accessCode,
        locale: META.locale,
        code: code || ''
      })
    }).then(function (res) { return res.json(); });
  }

  // Appended, never replaced. The point of a shell is being able to look
  // back at what you did three lines ago.
  function shellSay(text, isError) {
    if (text) {
      shellOutput.textContent += text + '\n';
      shellOutput.scrollTop = shellOutput.scrollHeight;
      if (ttsEnabled) speak(text, isError);
    }
  }

  function shellFail(data) {
    if (data.code_required) {
      // The same gate as the runner, so a hosted reader is asked once and
      // then answers the same way for both.
      promptForAccessCode();
      return true;
    }
    return false;
  }

  function shellOpen() {
    if (!shellPane || !shellPane.hidden) return;
    shellPane.hidden = false;
    // The divider between the output and the shell comes with it. A line
    // with nothing on the other side of it would just be a line.
    if (dividerShell) dividerShell.hidden = false;
    if (btnShell) btnShell.setAttribute('aria-expanded', 'true');
    if (shellInput) shellInput.focus();
    if (shellSession) return;
    shellPost('/api/shell/start')
      .then(function (data) {
        if (shellFail(data)) return;
        if (data.error || !data.session) {
          if (shellStatus) shellStatus.textContent = data.error || '';
          return;
        }
        shellSession = data.session;
        if (shellStatus) shellStatus.textContent = t('shell.status_waiting');
      })
      .catch(function () {
        if (shellStatus) shellStatus.textContent = t('shell.closed');
      });
  }

  function shellClose() {
    if (!shellPane || shellPane.hidden) return;
    shellPane.hidden = true;
    if (dividerShell) dividerShell.hidden = true;
    if (btnShell) btnShell.setAttribute('aria-expanded', 'false');
    // Closing hands the process back rather than leaving it running for
    // nobody. The id is forgotten, so reopening starts a clean shell.
    if (shellSession) {
      var closing = shellSession;
      shellSession = null;
      shellPost('/api/shell/stop', '').catch(function () {});
    }
    if (btnShell) btnShell.focus();
  }

  function shellRun() {
    if (shellBusy || !shellSession || !shellInput) return;
    var code = shellInput.value;
    if (!code.trim()) return;
    shellBusy = true;
    if (btnShellRun) btnShellRun.disabled = true;
    shellPost('/api/shell/exec', code)
      .then(function (data) {
        if (shellFail(data)) return;
        shellSay(data.output);
        if (data.error) {
          shellSay(data.error, true);
        }
      })
      .catch(function () {
        shellSay(t('shell.closed'), true);
      })
      .then(function () {
        shellBusy = false;
        if (btnShellRun) btnShellRun.disabled = false;
        if (shellInput) shellInput.focus();
      });
  }

  function shellClear() {
    if (!shellSession) return;
    shellPost('/api/shell/reset', '')
      .then(function (data) {
        if (shellFail(data)) return;
        // The transcript is cleared with the namespace. A reader who wipes
        // their definitions expects the screen to match.
        shellOutput.textContent = '';
        if (shellStatus) shellStatus.textContent = t('shell.status_waiting');
      })
      .catch(function () {});
  }

  if (btnShell) btnShell.addEventListener('click', function () {
    if (shellPane && shellPane.hidden) shellOpen(); else shellClose();
  });
  if (btnShellClose) btnShellClose.addEventListener('click', shellClose);
  if (btnShellRun) btnShellRun.addEventListener('click', shellRun);
  if (btnShellClear) btnShellClear.addEventListener('click', shellClear);
  if (shellInput) {
    // The same gesture as the editor, because muscle memory should not
    // have to be relearned for a different box.
    shellInput.addEventListener('keydown', function (e) {
      if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
        e.preventDefault();
        shellRun();
      }
    });
  }

  // Keyboard shortcut: Ctrl+Enter to run
  editor.setOption('extraKeys', {
    'Ctrl-Enter': runCode,
    'Cmd-Enter': runCode
  });

  // ---------- Quit (desktop app only) ----------
  // The Quit button only appears when running on the local desktop app,
  // where it stops the background server cleanly.
  if (btnQuit && (window.location.hostname === '127.0.0.1' || window.location.hostname === 'localhost')) {
    btnQuit.hidden = false;
    btnQuit.addEventListener('click', function () {
      fetch('/api/shutdown', { method: 'POST' })
        .then(function () {
          window.close();
        })
        .catch(function () {
          window.close();
        });
    });
  }

  // ---------- Init ----------
  contrastMode = contrastSelect.value || 'normal';
  applyContrast(contrastMode);
  // A saved colour has to be in place before the theme is built, or the
  // editor would paint in the old colour for a frame.
  customHighlightColor = body.getAttribute('data-highlight-color') || '';
  applyTheme(body.getAttribute('data-theme') || 'high-contrast');
  applyFont(body.getAttribute('data-font') || 'OpenDyslexic');
  applyFontSize(parseInt(body.getAttribute('data-font-size') || '16', 10));
  applyLineHeight(body.getAttribute('data-line-height') || '1.6');
  applyLetterSpacing(body.getAttribute('data-letter-spacing') || '0.5');
  paintStepperLimits();
  applyBlurIntensity(body.getAttribute('data-blur-intensity') || '0.5');
  applyFocusMode(body.getAttribute('data-focus-mode') || 'off');
  syncBlurField();
  updateFontNote();
  updatePreview();

  speechRate = parseFloat(body.getAttribute('data-tts-rate') || ttsRate.value || '0.9');
  speechVoiceName = body.getAttribute('data-tts-voice') || '';
  ttsRateLabel.textContent = speechRate.toFixed(1) + 'x';

  // The hover and click settings are read from the body rather than from
  // the controls, so the saved answer is what governs from the first
  // pointer movement - a reader should not have to open Settings for
  // hovering to start working.
  ttsHoverScopeValue = body.getAttribute('data-tts-hover-scope') || 'controls';
  ttsHoverDelayMs = parseFloat(body.getAttribute('data-tts-hover-delay') || '600');
  if (isNaN(ttsHoverDelayMs)) ttsHoverDelayMs = 600;
  ttsVoiceGenderValue = body.getAttribute('data-tts-voice-gender') || 'male';
  ttsClickToSpeak = true;
  if (ttsClickEl) {
    ttsClickToSpeak = ttsClickEl.getAttribute('aria-checked') === 'true';
  }
  if (ttsHoverScopeEl) ttsHoverScopeEl.value = ttsHoverScopeValue;
  if (ttsHoverDelay) ttsHoverDelay.value = String(ttsHoverDelayMs);
  if (ttsVoiceGenderEl) ttsVoiceGenderEl.value = ttsVoiceGenderValue;
  paintHoverDelay(ttsHoverDelayMs);
  paintClickSwitch();

  // Theme names and the voice list both come from the server, so the
  // first paint uses the saved values and these fill in behind them.
  fetchThemes();

  if ('speechSynthesis' in window) {
    loadVoices();
    // Chrome and Edge populate the voice list asynchronously.
    window.speechSynthesis.onvoiceschanged = loadVoices;
  }

  // Custom fonts load asynchronously. Once they are ready, recalculate
  // the editor layout so the gutter width matches the real font metrics.
  if (document.fonts && document.fonts.ready) {
    document.fonts.ready.then(function () {
      editor.refresh();
    });
  }

  // Last, so the app has already painted itself in the saved font and
  // size. The setup screen draws over all of it, and a wizard appearing
  // on top of a half-styled page looks like the app failed to load.
  openSetup();

})();
