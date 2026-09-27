// Execute app.js against a minimal DOM stub.
//
// The editor is one file with no build step, so a typo in an element id or
// a missing helper throws at load time and silently disables the whole
// editor. There is no jsdom in this project, so this stubs just enough to
// let the script run and reports anything that throws.
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const APP_JS = path.join(
  __dirname, '..', 'src', 'accessible_ide', 'static', 'js', 'app.js'
);
const source = fs.readFileSync(APP_JS, 'utf8');

// Ids that index.html is expected to provide. Anything app.js looks up but
// that is missing here will be reported, because that is exactly the bug
// this harness exists to catch.
const KNOWN_IDS = new Set([
  'btn-run', 'btn-save', 'btn-open', 'btn-read-line', 'btn-clear', 'btn-quit',
  'editor', 'output', 'error-panel', 'error-message', 'file-input',
  'settings-dialog', 'settings-title', 'settings-status', 'btn-settings',
  'btn-settings-close', 'font-select', 'font-size', 'font-size-label',
  'line-height', 'line-height-label', 'letter-spacing',
  'letter-spacing-label', 'line-height-less', 'line-height-more',
  'letter-spacing-less', 'letter-spacing-more',
  'blur-intensity', 'blur-intensity-label',
  'blur-field', 'theme-select', 'contrast-select', 'focus-mode',
  'reduce-motion', 'reduce-motion-state',
  'tts-toggle', 'tts-state', 'tts-voice', 'tts-rate', 'tts-rate-label',
  'tts-voice-gender', 'tts-hover-scope', 'tts-hover-delay',
  'tts-hover-delay-label', 'tts-click', 'tts-click-state',
  'btn-test-voice',
  'auto-update-toggle', 'auto-update-state', 'btn-check-update',
  'update-status', 'update-version',
  'update-install-row', 'update-install-label', 'update-install-help',
  'btn-install-update',
  'font-bundled-note', 'sample-text', 'font-preview', 'font-preview-text',
  'preview-status', 'swatches', 'code-color-hex', 'code-color-picker',
  'colour-error', 'btn-reset-colour',
  'language-select',
  // The module index. Without these declared here, initModules() takes
  // its early-return path and nothing about the index is exercised.
  'modules-dialog', 'modules-title', 'btn-modules', 'modules-close',
  'modules-search-input', 'modules-search-help', 'modules-filter-label',
  'modules-results', 'modules-results-label', 'modules-empty',
  'modules-status', 'modules-detail', 'modules-detail-label',
  // The first-run setup screen. The server stops rendering it once the
  // reader has finished it, so app.js has to treat every one of these as
  // optional - the harness declares them so that path is exercised rather
  // than skipped.
  'setup-dialog', 'setup-progress', 'setup-status', 'setup-back',
  'setup-next', 'setup-skip', 'btn-setup-again',
  // The two JSON script blocks the server embeds. They are not elements
  // app.js draws with, but without them every t() call falls back to
  // returning the key, and this harness would stop testing translations
  // at all while still reporting success.
  'i18n-data', 'i18n-meta',
]);

// The swatch colours, mirroring the list rendered into the panel.
const FONT_COLOURS = [
  '#ffd93d', '#93e6a8', '#8ad4e8', '#8fc0f5', '#c9a8f0',
  '#ff9a9a', '#e3c583', '#b4b4b4', '#ffffff', '#000000',
];

const numericIds = new Set([
  'font-size', 'line-height', 'letter-spacing', 'blur-intensity', 'tts-rate',
]);

// The two spacing sliders, with the limits, the step and the starting value
// the template gives them.
//
// app.js reads min, max and step off the element rather than repeating them,
// so a fake slider without these would let every stepper check pass for the
// wrong reason: notchTo() would be handed NaN and clamp to nothing.
const RANGE_INPUTS = {
  'line-height': { min: '1', max: '2.4', step: '0.1', value: '1.6' },
  'letter-spacing': { min: '-0.5', max: '4', step: '0.1', value: '0.5' },
};

// The notching buttons, with the slider each one drives and the direction it
// moves it. The target is a data attribute, so a button that lost it would
// quietly stop working while still looking right in the DOM.
const STEPPER_BUTTONS = {
  'line-height-less': { 'data-target': 'line-height', 'data-step': '-0.1' },
  'line-height-more': { 'data-target': 'line-height', 'data-step': '0.1' },
  'letter-spacing-less': { 'data-target': 'letter-spacing', 'data-step': '-0.1' },
  'letter-spacing-more': { 'data-target': 'letter-spacing', 'data-step': '0.1' },
};

const lookups = [];
const noop = () => {};
const reloads = [];
let reloadsBefore = 0;

// Which element has focus. Module scope, so makeElement can record it
// while makePage - which owns the document stub - reads it back.
let focusNow = null;

function makeClassList() {  const set = new Set();
  return {
    add: (c) => set.add(c),
    remove: (c) => set.delete(c),
    toggle: (c, force) => (force === undefined ? (set.has(c) ? set.delete(c) : set.add(c)) : (force ? set.add(c) : set.delete(c))),
    contains: (c) => set.has(c),
  };
}

// The <select> elements in the page, by id. They are named here rather
// than guessed from a "-select" ending, because "tts-voice" and "focus-mode"
// are selects too, and a suffix rule would quietly leave them out.
//
// Each one carries the values the template gives it, so a check that sets a
// value is held to the same list a reader could have chosen from. That is
// what makes "set it to something impossible" a real failure rather than a
// value the stub quietly accepts.
const SELECT_OPTIONS = {
  'contrast-select': ['normal', 'high'],
  'focus-mode': ['off', 'gutter', 'lines'],
  'tts-voice-gender': ['male', 'female', 'any'],
  'tts-hover-scope': ['off', 'controls', 'all'],
  'theme-select': ['high-contrast', 'dark'],
};

const optionsFor = (values) => values.map((v) => makeElement(v, {}, { value: v, textContent: v }));

// The attributes an element carries in the template, beyond the ones every
// element gets. min, max and step are attributes rather than properties, so
// this is where the sliders' limits have to live.
function attributesFor(id) {
  const range = RANGE_INPUTS[id];
  return Object.assign(
    { 'data-tts-voice-gender': 'male' },
    range ? { min: range.min, max: range.max, step: range.step } : {},
    STEPPER_BUTTONS[id] || {},
  );
}

function makeElement(id, extraAttributes = {}, extraProps = {}) {
  const attributes = {
    'aria-checked': 'true',
    'aria-pressed': 'false',
    'data-theme': 'high-contrast',
    'data-font': 'OpenDyslexic',
    'data-font-size': '16',
    'data-code-color': '',
    'data-line-height': '1.6',
    'data-letter-spacing': '0.5',
    'data-blur-intensity': '0.5',
    'data-focus-mode': 'off',
    'data-contrast': 'normal',
    'data-tts-voice': '',
    'data-tts-rate': '0.9',
    'data-tts-hover-scope': 'controls',
    'data-tts-hover-delay': '600',
    'data-tts-voice-gender': 'male',
    ...extraAttributes,
  };

  // Listeners are recorded rather than discarded so the harness can fire
  // them afterwards. A handler that throws is the failure mode that
  // matters: it silently stops that control working.
  const listeners = {};

  // style is a real object, not a swallowing proxy, so the harness can
  // read back what the code actually set. The preview's resolved colour is
  // the whole point of the panel, and it has to be checkable.
  const style = { setProperty: noop, removeProperty: noop };

  // Replacing a select's contents empties it, as setting innerHTML does in
  // a browser. app.js clears the voice list that way before refilling it.
  let html = '';
  const el = {
    set innerHTML(value) {
      html = value;
      el.options = [];
    },
    get innerHTML() { return html; },
    id,
    // A select with nothing chosen reports an empty value, not a font name.
    // Giving every one of them a font name made a genuine "nothing selected"
    // read as "OpenDyslexic", which is nonsense in a failure message and
    // hides what is actually wrong.
    value: numericIds.has(id) ? '16' : (id.endsWith('-select') ? '' : 'OpenDyslexic'),
    textContent: '',
    checked: false,
    disabled: false,
    hidden: false,
    files: [],
    className: '',
    style,
    classList: makeClassList(),
    getAttribute: (name) => (name in attributes ? attributes[name] : null),
    setAttribute: (name, v) => { attributes[name] = v; },
    removeAttribute: (name) => { delete attributes[name]; },
    hasAttribute: (name) => name in attributes,
    addEventListener: (type, handler) => {
      (listeners[type] = listeners[type] || []).push(handler);
    },
    removeEventListener: noop,
    // A real <select> collects the options appended to it, and empties them
    // when its contents are replaced. Without this the voice picker looks
    // permanently empty, and every check about what a reader can choose
    // from would pass for the wrong reason.
    options: [],
    // Real children, not options. The module index appends <li> and
    // <button> elements to a <ul> and to the detail pane, and options
    // would collect them in the wrong bucket and hide the very thing a
    // check needs to look at.
    children: [],
    appendChild(child) {
      el.children.push(child);
      el.options.push(child);
      return child;
    },
    removeChild(child) {
      el.children = el.children.filter((c) => c !== child);
      el.options = el.options.filter((o) => o !== child);
    },
    // Focus is recorded, because the index is expected to put the reader
    // in the search box and to hand focus back when it closes. It lives
    // at module scope rather than in makePage, because makeElement is
    // defined outside that function and could not see it there.
    focus() { focusNow = el; },
    blur: noop,
    // Selecting the text of a search box, so the reader can type over
    // what is there. app.js does this when the index opens.
    select: noop,
    click: noop,
    // A modal's open state is recorded rather than ignored, so a check
    // can tell "opened" from "was already open".
    showModal() { el.__open = true; },
    close() { el.__open = false; },
    getBoundingClientRect: () => ({ top: 0, left: 0, width: 100, height: 100 }),
    querySelector: () => makeElement('__query__'),
    querySelectorAll: () => [],
    getElementsByClassName: () => [],
    // app.js walks up the tree by hand looking for the nearest control, and
    // for anything it must not read aloud. A stub without this would make
    // every hover rule look like it matched nothing, and the harness would
    // still pass.
    tagName: (extraProps.tagName || 'DIV').toUpperCase(),
    parentNode: null,
    matches: (selector) =>
      String(selector)
        .split(',')
        .map((s) => s.trim())
        .some((selectorPart) => {
          if (!selectorPart) return false;
          if (selectorPart.startsWith('#')) {
            return el.id === selectorPart.slice(1);
          }
          if (selectorPart.startsWith('.')) {
            return el.classList.contains(selectorPart.slice(1));
          }
          // [attr] and [attr="value"]
          const attrMatch = selectorPart.match(/^\[([\w-]+)(?:=["']?([^"'\]]*)["']?)?\]$/);
          if (attrMatch) {
            const value = attributes[attrMatch[1]];
            if (value === undefined) return false;
            return attrMatch[2] === undefined ? true : value === attrMatch[2];
          }
          const tagMatch = selectorPart.match(/^(\w+)/);
          if (!tagMatch) return false;
          const tag = tagMatch[1].toUpperCase();
          if (el.tagName !== tag) return false;
          if (selectorPart.includes(':not(') || selectorPart.includes(':')) {
            // Not worth emulating; the reader's own tag matching is enough
            // for the checks that use this.
            return false;
          }
          return true;
        }),
    ...extraProps,
  };
  // A parent is only needed when a test asks for a chain; leaving it null
  // means the walk stops at the element, which is the common case.
  if (extraProps.parent) {
    el.parentNode = extraProps.parent;
  }

  // A real <select> only reports a value that one of its options has. Set
  // it to anything else and it goes back to showing nothing, which is what
  // happens to a saved voice that has since been uninstalled, and what
  // happens to any value the page's markup does not offer. Without this the
  // stub would keep whatever it was given, and the code under test could
  // not tell a valid choice from an impossible one.
  if (SELECT_OPTIONS[id] || id.endsWith('-select') || id === 'tts-voice') {
    let chosen = extraProps.value !== undefined ? extraProps.value : el.value;
    Object.defineProperty(el, 'value', {
      get: () => chosen,
      set: (v) => {
        const options = el.options || [];
        if (v === '' || options.some((o) => o.value === v)) chosen = v;
        else chosen = '';
      },
      enumerable: true,
      configurable: true,
    });
    // extraProps may have supplied the option list, so start from the
    // default selection rather than from a value no option matches.
    chosen = (el.options || []).some((o) => o.value === chosen) ? chosen : '';
  }

  el.__listeners = listeners;
  el.__attributes = attributes;
  return el;
}

// The font list, mirroring what routes.py renders into the <option> tags.
// app.js reads the CSS stack from data-family rather than keeping its own
// copy, so these attributes are what the real code depends on.
const FONT_OPTIONS = [
  ['Atkinson Hyperlegible', 'Atkinson Hyperlegible', 'true'],
  ['OpenDyslexic', 'OpenDyslexic', 'true'],
  ['Lexend', 'Lexend', 'true'],
  ['Nunito', 'Nunito', 'true'],
  ['Almarai', 'Almarai (Arabic)', 'true'],
  ['Calibri', 'Calibri', 'false'],
  ['Arial', 'Arial', 'false'],
  ['Comic Sans MS', 'Comic Sans MS', 'false'],
  ['Courier New', 'Courier New', 'false'],
].map(([value, label, bundled]) => makeElement(value, {
  'data-family': `"${value}", sans-serif`,
  'data-bundled': bundled,
}, { value, textContent: label }));

// The font <select> needs a real option list for fontFamilyFor() and
// updateFontNote() to work against.
const FONT_SELECT = makeElement('font-select', {}, { options: FONT_OPTIONS });

// ---------------------------------------------------------------------------
// The first-run setup screen.
//
// Built once and shared, because the real thing is one dialog that is
// created and then navigated in place: a check that moves to step 2 leaves
// the panels shown and hidden, and the next check has to see that.
//
// Each panel carries the heading app.js moves focus to, and focus is
// recorded rather than discarded - "focus stayed on the Next button" is the
// failure this whole arrangement exists to catch, and a noop focus would
// make it invisible.
// ---------------------------------------------------------------------------
const setupFocusLog = [];

function makeSetupPanel(name, visible) {
  const legend = makeElement(`setup-legend-${name}`);
  legend.focus = () => { setupFocusLog.push(name); };
  const panel = makeElement(`setup-panel-${name}`, {}, { hidden: !visible });
  panel.__legend = legend;
  panel.querySelectorAll = () => [];
  panel.querySelector = (selector) =>
    selector === '.setup-legend' ? legend : null;
  return panel;
}

const SETUP_PANELS = [
  makeSetupPanel('language', true),
  makeSetupPanel('font', false),
  makeSetupPanel('tour', false),
];

// The radios, carrying the same data-family stacks the template renders, so
// the live preview is held to the font the code would really apply.
const SETUP_FONT_RADIOS = FONT_OPTIONS.map((option) => {
  const value = option.value;
  return makeElement(`setup-font-${value}`, {
    name: 'setup-font',
    'data-family': option.__attributes['data-family'],
  }, { value, checked: value === 'Atkinson Hyperlegible' });
});

const SETUP_LOCALE_RADIOS = ['en', 'hi', 'fr', 'es', 'ar'].map((code) =>
  makeElement(`setup-locale-${code}`, { name: 'setup-locale' },
    { value: code, checked: code === 'en' })
);

// The four level filters, in the order the template renders them. The
// first one starts pressed, because the index opens showing everything.
const MODULE_LEVELS = ['', 'start', 'everyday', 'advanced'];
const MODULE_LEVEL_BUTTONS = MODULE_LEVELS.map((level) => {
  const el = makeElement(`modules-level-${level || 'all'}`, {
    'data-level': level,
    'aria-pressed': level === '' ? 'true' : 'false',
  });
  el.className = 'btn btn-small modules-level' + (level === '' ? ' is-on' : '');
  return el;
});

const SETUP_DIALOG = makeElement('setup-dialog', {}, {
  // Recorded rather than discarded: "the wizard was in the markup but never
  // opened" is a real failure that a noop would hide completely.
  showModal() { SETUP_DIALOG.__modalOpens += 1; },
  querySelectorAll: (selector) => {
    if (selector === '.setup-panel') return SETUP_PANELS;
    if (selector === 'input[name="setup-locale"]') return SETUP_LOCALE_RADIOS;
    if (selector === 'input[name="setup-font"]') return SETUP_FONT_RADIOS;
    return [];
  },
  querySelector: (selector) => {
    if (selector !== '.setup-panel:not([hidden]) .setup-legend') return null;
    const current = SETUP_PANELS.find((panel) => !panel.hidden);
    return current ? current.__legend : null;
  },
});

// Puts the wizard back to the beginning, so a check cannot pass or fail
// because of where an earlier one left it.
function resetSetup() {
  SETUP_PANELS.forEach((panel, index) => { panel.hidden = index !== 0; });
  setupFocusLog.length = 0;
}

SETUP_DIALOG.__modalOpens = 0;

// The editor keeps its value, so a check can tell an append from an
// overwrite. A stub that discarded what was written could not tell the
// difference, and losing a reader's work is the failure that matters most
// here.
let editorValue = 'print("hi")';
const editorInstance = {
  getValue: () => editorValue,
  setValue: (value) => { editorValue = value; },
  lineCount: () => editorValue.split('\n').length,
  setCursor: noop,
  setOption: noop,
  getOption: () => undefined,
  refresh: noop,
  on: noop,
  focus: noop,
  operation: (fn) => fn(),
  getDoc: () => ({ getLine: () => '', getSelection: () => '' }),
  replaceSelection: noop,
};

function CodeMirror() { return editorInstance; }
CodeMirror.defineStyle = noop;
CodeMirror.defineMode = noop;
CodeMirror.defineMIME = noop;
CodeMirror.commands = {};

const elements = new Map();

// The real English catalogue, so the harness exercises the same
// translations the browser would. Reading it from disk means a key that is
// removed from en.json shows up here as a key rather than as empty text.
const CATALOGUE = JSON.parse(
  fs.readFileSync(
    path.join(__dirname, '..', 'src', 'accessible_ide', 'i18n', 'en.json'),
    'utf8'
  )
);
// The catalogue for any shipped language, read the same way as English.
// Only the ones the checks below actually speak in are loaded, so a typo
// in a key name still shows up as a raw key rather than as empty text.
const CATALOGUES = { en: CATALOGUE };
for (const code of ['hi', 'fr', 'es', 'ar']) {
  CATALOGUES[code] = JSON.parse(
    fs.readFileSync(
      path.join(__dirname, '..', 'src', 'accessible_ide', 'i18n', `${code}.json`),
      'utf8'
    )
  );
}

// The voices Windows installs, which is what the gender matching has to
// cope with. The names are the reason this check exists: a Hindi voice is
// called "Swara", not "Female", so a list of English names alone matches
// nothing for a Hindi or Arabic reader.
//
// The order matters as much as the names. These are grouped so that the
// voice a correct implementation should pick comes first within its
// language, and a name that fails to match is replaced by the next one
// along. That is what makes the checks below able to fail: an unmatched
// Arabic or accented name shows up as the wrong voice, not as a pass.
const INSTALLED_VOICES = [
  { name: 'Zoe Test', lang: 'en-GB', voiceURI: 'zoe' },
  { name: 'Test Voice', lang: 'en-GB', voiceURI: 'test' },
  { name: 'Daniel Test', lang: 'en-US', voiceURI: 'daniel' },
  { name: 'Microsoft Swara - Hindi (India)', lang: 'hi-IN', voiceURI: 'swara' },
  { name: 'Microsoft Hemant - Hindi (India)', lang: 'hi-IN', voiceURI: 'hemant' },
  // Arabic, with the Latin-named Windows voices behind these. Google and
  // several Linux speech engines name their Arabic voices in Arabic, so a
  // matcher that only understands ASCII letters quietly skips the best
  // ones. "\\b" is one such matcher.
  //
  // The URIs are deliberately dull. A URI reading "ar-male" would match the
  // word "male" and the voice would be found by accident, which would make
  // this check pass for the wrong reason - the one thing a test here must
  // never do.
  { name: 'صوت رجل', lang: 'ar-SA', voiceURI: 'ar-001' },
  { name: 'صوت امرأة', lang: 'ar-SA', voiceURI: 'ar-002' },
  { name: 'Microsoft Hoda - Arabic (Saudi Arabia)', lang: 'ar-SA', voiceURI: 'hoda' },
  { name: 'Microsoft Naayf - Arabic (Saudi Arabia)', lang: 'ar-SA', voiceURI: 'naayf' },
  { name: 'Microsoft Diego - Spanish (Mexico)', lang: 'es-MX', voiceURI: 'diego' },
  { name: 'Microsoft Sabina - Spanish (Mexico)', lang: 'es-MX', voiceURI: 'sabina' },
  { name: 'Frédéric', lang: 'fr-FR', voiceURI: 'fr-003' },
  { name: 'Amélie', lang: 'fr-FR', voiceURI: 'fr-004' },
  { name: 'Microsoft Henri - French (France)', lang: 'fr-FR', voiceURI: 'henri' },
  { name: 'Microsoft Denise - French (France)', lang: 'fr-FR', voiceURI: 'denise' },
];

// A page, in one language. The main checks use the English one; the
// per-language checks ask for a fresh page each time, because the locale
// is read once when the script loads and a real language change reloads
// the page.
//
// bodyAttrs stands in for the settings the server rendered onto the body,
// which is how a saved choice survives a reload.
function makePage(locale, shared, bodyAttrs) {
  const catalogue = CATALOGUES[locale] || CATALOGUE;
  const i18nScripts = {
    'i18n-data': makeElement('i18n-data', {}, { textContent: JSON.stringify(catalogue) }),
    'i18n-meta': makeElement('i18n-meta', {}, {
      textContent: JSON.stringify({ locale, direction: locale === 'ar' ? 'rtl' : 'ltr' }),
    }),
  };
  // The main page shares the harness-wide element map and lookup log, so
  // every existing check keeps working. The per-language pages get their
  // own, because they exist only to ask one question.
  const found = shared ? shared.elements : new Map();
  const seen = shared ? shared.lookups : [];
  const spoken = shared ? shared.spoken : [];

  const attrs = Object.assign({ 'data-locale': locale }, bodyAttrs || {});

  const doc = {
    body: makeElement('body', attrs),

    documentElement: makeElement('html'),
    // The Settings button has focus when it is pressed, which is the case
    // openSettings/closeSettings are written to handle.
    get activeElement() { return focusNow; },
    set activeElement(value) { focusNow = value; },
    getElementById: (id) => {
      seen.push(id);
      if (id === 'font-select') {
        if (!found.has('font-select')) found.set('font-select', FONT_SELECT);
        return FONT_SELECT;
      }
      if (id in i18nScripts) {
        if (!found.has(id)) found.set(id, i18nScripts[id]);
        return found.get(id);
      }
      if (id === 'language-select') {
        // With its real option list, so the picker's value has to be one the
        // list actually holds. A <select> offered a value that is not in it
        // simply shows nothing, which is not what the page does.
        if (!found.has(id)) {
          found.set(id, makeElement(id, {}, {
            value: locale,
            options: Object.keys(CATALOGUES).map((code) => makeElement(code, {}, {
              value: code,
              textContent: code,
            })),
          }));
        }
        return found.get(id);
      }
      if (id === 'setup-dialog') {
        // One dialog with three steps and two sets of radios inside it,
        // rather than a flat element the generic path could invent.
        if (!found.has(id)) found.set(id, SETUP_DIALOG);
        return found.get(id);
      }
      if (!KNOWN_IDS.has(id)) return null;
      if (!found.has(id)) {
        // Settings the template renders as a dropdown carry its real values,
        // so a check cannot set one the page does not offer.
        const props = Object.assign(
          {},
          SELECT_OPTIONS[id]
            ? { value: SELECT_OPTIONS[id][0], options: optionsFor(SELECT_OPTIONS[id]) }
            : {},
          RANGE_INPUTS[id] ? { value: RANGE_INPUTS[id].value } : {},
          // The template draws Back hidden on the first step. Without this
          // the stub would start with it showing, and a check about it
          // hiding would pass for the wrong reason.
          id === 'setup-back' ? { hidden: true } : {},
        );
        found.set(id, makeElement(id, attributesFor(id), props));
      }
      return found.get(id);
    },
    querySelector: () => makeElement('__query__'),
    // The module index asks for its level filters this way, and gets the
    // same four elements every time, so the listeners it attaches are the
    // ones a check can fire.
    querySelectorAll: (selector) => (
      selector === '.modules-level' ? MODULE_LEVEL_BUTTONS : []
    ),
    createElement: (tag) => makeElement(tag),
    addEventListener: noop,
    removeEventListener: noop,
    fonts: { ready: Promise.resolve() },
  };

  const context = {
    console,
    document: doc,
    navigator: { language: locale, userAgent: 'stub' },
    matchMedia: () => ({ matches: false, addEventListener: noop, removeEventListener: noop }),
    localStorage: { getItem: () => null, setItem: noop, removeItem: noop },
    fetch: fetchStub,
    setTimeout, clearTimeout, setInterval, clearInterval,
    Promise, JSON, Math, Date, Number, String, Object, Array,
    parseInt, parseFloat, isNaN,
    CodeMirror,
    SpeechSynthesisUtterance: function (text) { this.text = text; },
    window: {
      location: {
        hostname: 'localhost',
        href: 'http://localhost:5000/',
        protocol: 'http:', host: 'localhost:5000', origin: 'http://localhost:5000',
        reload: noop,
      },
      speechSynthesis: {
        getVoices: () => INSTALLED_VOICES,
        speak: (utterance) => { spoken.push(utterance); },
        cancel: noop,
        onvoiceschanged: null,
      },
      addEventListener: noop,
      removeEventListener: noop,
      // Counted rather than left undefined. The Quit button closes the
      // window for real, and so - wrongly - might an update. The counter is
      // how the update checks tell the two apart.
      close: () => { closeAttempts += 1; },
    },
  };
  context.window.document = doc;
  context.globalThis = context;
  context.self = context;
  vm.createContext(context);
  return { context, doc, found, spoken };
}

// Fire a handler on an element of a page built by makePage.
function fireOn(page, id, type) {
  const el = page.found.get(id);
  if (!el) return false;
  const handler = (el.__listeners[type] || [])[0];
  if (!handler) return false;
  handler(fakeEventFor(page));
  return true;
}

function fakeEventFor(page) {
  return { preventDefault: noop, stopPropagation: noop, target: page.doc.body };
}

const fetchCalls = [];
// How many times anything asked to close the window. The Quit button does
// this legitimately; the update flow must never do it at all, because the
// app has no way of knowing whether the reader's work is saved.
let closeAttempts = 0;
// Replaced by the end of the update chain, so the process exits when the last
// promise has settled rather than at a guessed moment.
let finish = () => process.exit(failed ? 1 : 0);
const configPosts = [];
// Whether a settings write is accepted. Held in a variable so the refused
// path can be walked: a stub that only ever saves would never show what the
// app does when the answer comes back "no", which is the case where the
// reader's answers are at risk.
let updateConfigOk = true;
// The bodies sent to the update check, so a check can be told apart from a
// forced one.
const updateCheckBodies = [];
// What the server answers with. Held in a variable so a check can change it
// and prove what the app says when the check fails - which is the path that
// matters most and the one a passing stub would otherwise never reach.
let updateCheckReply = {
  success: true, applicable: true, current: '0.2.2-beta',
  update_available: false, error: '', error_code: '', error_text: '',
  automatic: true,
};
// The same idea for the download: held in a variable so the failure path can
// be walked too. A stub that only ever succeeds proves nothing about the case
// that actually matters, where the download does not arrive.
let updateInstallReply = { success: true, version: '99.0.0', size: 10 };
let updateInstallOk = true;
const updateInstallBodies = [];
// Every utterance the app asked for, in order. Without this the harness
// can only prove the app ran, not that it said anything.
const spokenUtterances = [];

// Stand-in module data. A handful is enough: the point is to check how
// the app draws and orders what it is given, and the catalogue's contents
// are covered by the Python tests.
const MODULE_LIST = {
  total: 3,
  total_all: 3,
  counts: { start: 1, everyday: 1, advanced: 1 },
  modules: [
    {
      name: 'json', level: 'everyday', group: 'data',
      summary: 'Reading and writing data as text a person can read.',
      words: ['settings'], available: true, runs_in_web: true,
    },
    {
      name: 'curses', level: 'advanced', group: 'system',
      summary: 'Coloured menus in a terminal window.',
      words: ['terminal'], available: false, runs_in_web: true,
    },
    {
      name: 'tkinter', level: 'advanced', group: 'graphics',
      summary: 'Windows, buttons and boxes on the screen.',
      words: ['windows'], available: true, runs_in_web: false,
    },
  ],
};

const MODULE_DETAIL = {
  name: 'json', level: 'everyday', group: 'data',
  summary: 'Reading and writing data as text a person can read.',
  words: ['settings'], available: true, runs_in_web: true,
  example: 'import json\nprint(json.dumps({"ok": True}))',
};

function fetchStub(url, options) {
  fetchCalls.push(url);
  if (String(url).includes('/api/themes')) {
    return Promise.resolve({
      ok: true,
      json: () => Promise.resolve({
        'high-contrast': { name: 'High Contrast', bg: '#0b0b0b', fg: '#ffffff' },
        dark: { name: 'Dark', bg: '#17181c', fg: '#e6e6e6' },
      }),
    });
  }
  if (String(url).includes('/api/modules/')) {
    const wanted = decodeURIComponent(String(url).split('/api/modules/')[1].split('?')[0]);
    return Promise.resolve({
      ok: true,
      json: () => Promise.resolve(
        wanted === MODULE_DETAIL.name ? MODULE_DETAIL : { error: 'unknown module' },
      ),
    });
  }
  if (String(url).includes('/api/modules')) {
    return Promise.resolve({
      ok: true,
      json: () => Promise.resolve(MODULE_LIST),
    });
  }
  if (String(url).includes('/api/config') && options && options.body) {
    try {
      configPosts.push(JSON.parse(options.body));
    } catch (error) {
      configPosts.push({ __unparseable: String(options.body) });
    }
    if (!updateConfigOk) {
      return Promise.resolve({
        ok: false,
        json: () => Promise.resolve({ success: false, error: 'refused' }),
      });
    }
    return Promise.resolve({
      ok: true,
      json: () => Promise.resolve({ success: true }),
    });
  }
  // The update endpoints get real answers, or the panel would take the
  // "this is the website, it cannot update itself" branch on every run and
  // the switch and button would never be exercised.
  if (String(url).includes('/api/version')) {
    return Promise.resolve({
      ok: true,
      json: () => Promise.resolve({ version: '0.2.2-beta', applicable: true }),
    });
  }
  if (String(url).includes('/api/update/check')) {
    if (options && options.body) {
      try {
        updateCheckBodies.push(JSON.parse(options.body));
      } catch (error) {
        updateCheckBodies.push({ __unparseable: String(options.body) });
      }
    }
    return Promise.resolve({
      ok: true,
      json: () => Promise.resolve(Object.assign({}, updateCheckReply)),
    });
  }
  if (String(url).includes('/api/update/install')) {
    if (options && options.body) {
      try {
        updateInstallBodies.push(JSON.parse(options.body));
      } catch (error) {
        updateInstallBodies.push({ __unparseable: String(options.body) });
      }
    }
    return Promise.resolve({
      ok: updateInstallOk,
      json: () => Promise.resolve(Object.assign({}, updateInstallReply)),
    });
  }
  return Promise.resolve({ ok: true, json: () => Promise.resolve({ success: true }) });
}

// The page the bulk of the checks run against: English, sharing the
// harness-wide element map, lookup log and utterance log.
const shared = { elements, lookups, spoken: spokenUtterances };
const mainPage = makePage('en', shared);
const sandbox = mainPage.context;
const documentStub = mainPage.doc;
// app.js asks the operating system whether motion should be reduced. The
// page above reports "no", which is the ordinary case; the seeding check
// below then proves the switch can also be flipped the other way.
sandbox.matchMedia = (query) => ({
  media: query,
  matches: false,
  addEventListener: noop,
  removeEventListener: noop,
});
sandbox.window.location.reload = () => { reloads.push(true); };

let failed = false;
try {
  vm.createContext(sandbox);
  vm.runInContext(source, sandbox, { filename: 'app.js' });
  console.log('OK  app.js executed with no error');
} catch (error) {
  failed = true;
  console.log('FAIL app.js threw at load time:');
  console.log('     ' + error.message);
  console.log((error.stack || '').split('\n').slice(0, 6).join('\n'));
}

const unknown = [...new Set(lookups)].filter((id) => !KNOWN_IDS.has(id));
if (unknown.length) {
  failed = true;
  console.log('FAIL app.js looked up ids this harness does not know: ' + unknown.join(', '));
}

// ---------------------------------------------------------------------------
// Fire every listener the script registered. Loading without error only
// proves the top half of the file parsed; the wiring is in these handlers.
// ---------------------------------------------------------------------------
const fakeEvent = { preventDefault: noop, stopPropagation: noop };

// A browser sets currentTarget to the element whose handler is running.
// A handler that reads it - to find which filter was pressed, say - would
// otherwise get nothing here and quietly do the wrong thing, so the event
// has to carry it.
function eventFor(el) {
  return {
    preventDefault: noop, stopPropagation: noop,
    target: el, currentTarget: el,
  };
}
const interactions = [
  ['font-select', 'change'], ['font-size', 'input'], ['font-size', 'change'],
  ['line-height', 'input'], ['line-height', 'change'],
  ['letter-spacing', 'input'], ['letter-spacing', 'change'],
  ['line-height-less', 'click'], ['line-height-more', 'click'],
  ['letter-spacing-less', 'click'], ['letter-spacing-more', 'click'],
  ['blur-intensity', 'input'], ['blur-intensity', 'change'],
  ['theme-select', 'change'], ['contrast-select', 'change'],
  ['focus-mode', 'change'],
  ['reduce-motion', 'click'],
  ['tts-toggle', 'click'], ['tts-voice', 'change'],
  ['tts-voice-gender', 'change'],
  ['tts-hover-scope', 'change'],
  ['tts-hover-delay', 'input'], ['tts-hover-delay', 'change'],
  ['tts-click', 'click'],
  ['tts-rate', 'input'], ['tts-rate', 'change'],
  ['btn-test-voice', 'click'],
  ['auto-update-toggle', 'click'],
  ['btn-check-update', 'click'],
  ['btn-settings', 'click'], ['btn-settings-close', 'click'],
  ['settings-dialog', 'cancel'],
  ['sample-text', 'input'],
  ['code-color-hex', 'input'], ['code-color-hex', 'change'],
  ['code-color-picker', 'input'], ['code-color-picker', 'change'],
  ['btn-reset-colour', 'click'],
  // language-select is deliberately absent: it is fired below with a real
  // language code, because the reload it triggers has to be counted.
];

let fired = 0;
for (const [id, type] of interactions) {
  const el = elements.get(id);
  if (!el) {
    failed = true;
    console.log(`FAIL no element captured for #${id}`);
    continue;
  }
  for (const handler of el.__listeners[type] || []) {
    try {
      handler(fakeEvent);
      fired++;
    } catch (error) {
      failed = true;
      console.log(`FAIL ${type} handler on #${id} threw: ${error.message}`);
      console.log((error.stack || '').split('\n').slice(0, 4).join('\n'));
    }
  }
}
console.log(`     fired ${fired} event handlers across ${interactions.length} controls`);

// The two settings that were previously stored but never applied must
// actually reach the document now.
const bodyAttrs = documentStub.body.__attributes;
const savedSettings = ['data-line-height', 'data-letter-spacing',
                       'data-blur-intensity', 'data-contrast'];
const missingAttrs = savedSettings.filter((a) => !(a in bodyAttrs));
if (missingAttrs.length) {
  failed = true;
  console.log('FAIL body never received: ' + missingAttrs.join(', '));
} else {
  console.log('     body received ' + savedSettings.join(', '));
}

const missing = [...KNOWN_IDS].filter((id) => !lookups.includes(id));
console.log('     looked up ' + new Set(lookups).size + ' ids; ' + missing.length +
            ' declared-but-unused in the harness' + (missing.length ? ': ' + missing.join(', ') : ''));

// ---------------------------------------------------------------------------
// The "Try it out" panel. These are the checks that matter most: the whole
// point of letting someone choose a colour is that the code stays readable,
// so the resolved colour is measured against the preview background rather
// than assumed to be fine.
//
// This runs after a tick because the theme palette arrives from /api/themes,
// and until it does there is no background to measure against.
// ---------------------------------------------------------------------------

function relativeLuminance(hex) {
  const value = hex.replace('#', '');
  const channels = [0, 2, 4].map((i) => {
    const part = parseInt(value.slice(i, i + 2), 16) / 255;
    return part <= 0.03928 ? part / 12.92 : Math.pow((part + 0.055) / 1.055, 2.4);
  });
  return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2];
}

function contrastRatio(first, second) {
  const a = relativeLuminance(first);
  const b = relativeLuminance(second);
  return (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05);
}

function fire(id, type, event = fakeEvent) {
  const el = elements.get(id);
  if (!el) return null;
  for (const handler of el.__listeners[type] || []) handler(event);
  return el;
}

function runPanelChecks() {
  const preview = elements.get('font-preview');
  const hexInput = elements.get('code-color-hex');
  const errorText = elements.get('colour-error');
  const swatchGroup = elements.get('swatches');
  const bodyNow = documentStub.body.__attributes;

  if (!preview.style.backgroundColor) {
    failed = true;
    console.log('FAIL the preview was never given the editor background');
    return;
  }

  // Every swatch, and a few colours a reader might invent, must land on
  // the preview as a colour that clears WCAG AA against that background.
  const candidates = [...FONT_COLOURS, '#1a1a1a', '#fefefe', '#808080'];

  for (const candidate of candidates) {
    hexInput.value = candidate;
    fire('code-color-hex', 'input');

    const shown = preview.style.color;
    const background = preview.style.backgroundColor;
    if (!shown || !/^#[0-9a-f]{6}$/i.test(shown)) {
      failed = true;
      console.log(`FAIL choosing ${candidate} left the preview colour as ${shown}`);
      continue;
    }
    const ratio = contrastRatio(shown, background);
    if (ratio < 4.5) {
      failed = true;
      console.log(`FAIL ${candidate} resolved to ${shown} on ${background}, ` +
                  `which is only ${ratio.toFixed(2)}:1`);
    }
    if (bodyNow['data-code-color'] !== candidate) {
      failed = true;
      console.log(`FAIL ${candidate} was not recorded on the body`);
    }
  }
  console.log(`     all ${candidates.length} chosen colours clear 4.5:1 on the preview background`);

  // A half-typed colour must not be nagged about, and must not be stored.
  // Typing "#ff" on the way to "#ffd93d" is normal, and an error box
  // appearing on the first keystroke would be discouraging.
  hexInput.value = '#ff';
  fire('code-color-hex', 'input');
  if (errorText.hidden !== true) {
    failed = true;
    console.log('FAIL a part-typed colour showed an error while the reader was still typing');
  }

  hexInput.value = 'nonsense';
  fire('code-color-hex', 'input');
  if (errorText.hidden !== true) {
    failed = true;
    console.log('FAIL nonsense nagged the reader mid-typing');
  }
  console.log('     part-typed colours are left alone, with no error shown');

  // Leaving the field is where a real mistake is reported - and refused.
  fire('code-color-hex', 'change');
  if (errorText.hidden !== false || !errorText.textContent) {
    failed = true;
    console.log('FAIL leaving the field with nonsense did not explain the problem');
  }
  if (bodyNow['data-code-color'] === 'nonsense') {
    failed = true;
    console.log('FAIL nonsense was saved to the config');
  }

  hexInput.value = 'red';
  fire('code-color-hex', 'change');
  if (bodyNow['data-code-color'] === 'red') {
    failed = true;
    console.log('FAIL a named colour was saved to the config');
  }
  console.log('     a colour that is not a hex code is explained, and never saved');

  // A swatch click records the colour and clears the error.
  hexInput.value = '';
  swatchGroup.__listeners.change.forEach((handler) =>
    handler({ target: { name: 'colour-swatch', value: '#8fc0f5' } }));
  if (bodyNow['data-code-color'] !== '#8fc0f5') {
    failed = true;
    console.log(`FAIL swatch click saved ${bodyNow['data-code-color']} instead of #8fc0f5`);
  }
  if (errorText.hidden !== true) {
    failed = true;
    console.log('FAIL picking a swatch did not clear the earlier error');
  }
  console.log('     swatches record the colour and clear the error');

  // The sample text the reader typed is what the preview shows.
  const sample = elements.get('sample-text');
  sample.value = 'Pack my box with five dozen liquor jugs';
  fire('sample-text', 'input');
  const previewText = elements.get('font-preview-text');
  if (previewText.textContent !== sample.value) {
    failed = true;
    console.log(`FAIL the preview shows "${previewText.textContent}" ` +
                `instead of the typed sample`);
  } else {
    console.log('     the preview follows the sample text');
  }

  // Reset goes back to the theme colour.
  fire('btn-reset-colour', 'click');
  if (bodyNow['data-code-color'] !== '') {
    failed = true;
    console.log(`FAIL reset left data-code-color as "${bodyNow['data-code-color']}"`);
  }
  if (hexInput.value !== '') {
    failed = true;
    console.log('FAIL reset did not clear the hex field');
  }
  console.log('     "Use theme colour" clears the custom colour');
}

// ---------------------------------------------------------------------------
// The language picker. Every string app.js shows now comes from the embedded
// catalogue, so the checks here are that the catalogue is actually in use and
// that choosing a language saves it and reloads, rather than only swapping
// the JavaScript strings and leaving the markup in the old language.
// ---------------------------------------------------------------------------
function runLanguageChecks() {
  const select = elements.get('language-select');
  const body = documentStub.body.__attributes;
  const before = configPosts.length;

  // The firing loop did not touch this control, so nothing is in flight
  // and the counts below are exact.
  select.value = 'fr';
  reloadsBefore = reloads.length;
  fire('language-select', 'change');

  const posted = configPosts.slice(before).map((p) => p.locale).filter(Boolean);
  if (!posted.includes('fr')) {
    failed = true;
    console.log('FAIL choosing a language did not save it: ' +
                JSON.stringify(configPosts.slice(before)));
  }
  if (body['data-locale'] !== 'fr') {
    failed = true;
    console.log(`FAIL data-locale is "${body['data-locale']}" after picking French`);
  } else {
    console.log('     choosing a language saves it and marks the page');
  }

  // The catalogue really is loaded, so t() returns words rather than keys.
  const status = elements.get('preview-status');
  if (status.textContent && status.textContent.indexOf('theme.') === 0) {
    failed = true;
    console.log('FAIL strings still show raw keys: ' + status.textContent);
  } else {
    console.log('     strings come from the catalogue, not raw keys');
  }
}

// Reloading is what re-renders the markup - settings labels, aria labels and
// titles - into the new language, which a JavaScript-only swap could never
// do. The save is a promise, so this runs a tick after the change.
function runLanguageReloadCheck() {
  if (reloads.length !== reloadsBefore + 1) {
    failed = true;
    console.log(`FAIL choosing a language caused ${reloads.length - reloadsBefore} ` +
                'reloads instead of one');
  } else {
    console.log('     the page reloads so the markup is re-rendered');
  }
  runLanguageNoopCheck();
}

// Picking the language already in use must not bounce the page.
function runLanguageNoopCheck() {
  const select = elements.get('language-select');
  const beforeNoop = reloads.length;
  select.value = 'fr';
  fire('language-select', 'change');
  setTimeout(() => {
    if (reloads.length !== beforeNoop) {
      failed = true;
      console.log('FAIL re-picking the current language reloaded the page');
    } else {
      console.log('     re-picking the current language changes nothing');
    }
    runMotionChecks();
  }, 10);
}

// ---------------------------------------------------------------------------
// The reduce-motion switch. The body attribute is what the stylesheet reads,
// so getting it wrong means the switch looks right and the app still moves.
// The firing loop above already clicked it once, so this checks the state
// that click produced rather than starting from scratch.
// ---------------------------------------------------------------------------
function runMotionChecks() {
  const button = elements.get('reduce-motion');
  const label = elements.get('reduce-motion-state');
  const body = documentStub.body.__attributes;

  const flips = body['data-reduce-motion'];
  if (flips !== 'true' && flips !== 'false') {
    failed = true;
    console.log(`FAIL data-reduce-motion is "${flips}" after clicking the switch`);
  } else {
    console.log(`     clicking the switch set data-reduce-motion="${flips}"`);
  }

  if (button.getAttribute('aria-checked') !== flips) {
    failed = true;
    console.log(`FAIL the switch says aria-checked="${button.getAttribute('aria-checked')}" ` +
                `but the page is set to "${flips}"`);
  } else {
    console.log('     the switch and the page agree with each other');
  }

  if (!label.textContent || label.textContent.indexOf('switch.') === 0) {
    failed = true;
    console.log('FAIL the switch label is missing or shows a raw key: ' + label.textContent);
  } else {
    console.log('     the switch label is a translated word');
  }

  const saved = configPosts.filter((p) => 'reduce_motion' in p);
  if (!saved.length) {
    failed = true;
    console.log('FAIL the motion choice was never saved');
  } else if (typeof saved[saved.length - 1].reduce_motion !== 'boolean') {
    failed = true;
    console.log('FAIL reduce_motion was saved as ' +
                JSON.stringify(saved[saved.length - 1].reduce_motion) + ' rather than true/false');
  } else {
    console.log('     the choice is saved as true or false, not "unset"');
  }

  console.log('     fetch calls: ' + (fetchCalls.length ? fetchCalls.join(', ') : '(none)'));
  runSpeechChecks();
}

// ---------------------------------------------------------------------------
// What gets read out, and what does not. This is the part of the feature a
// reader notices within a minute of using it: if the hover reads nothing,
// the switch does nothing, or the editor gets narrated while someone is
// trying to write code in it, the setting has to be visibly wrong.
// ---------------------------------------------------------------------------
function runSpeechChecks() {
  const scopeSelect = elements.get('tts-hover-scope');
  const delaySlider = elements.get('tts-hover-delay');
  const delayLabel = elements.get('tts-hover-delay-label');
  const clickSwitch = elements.get('tts-click');
  const clickState = elements.get('tts-click-state');
  const genderSelect = elements.get('tts-voice-gender');

  // The label is shown in whichever unit can be pictured: 600ms means
  // nothing, 1.5s means something.
  if (delayLabel.textContent !== '600ms') {
    failed = true;
    console.log('FAIL the hover delay reads "' + delayLabel.textContent + '" for 600ms');
  } else {
    console.log('     the hover delay is shown as 600ms');
  }
  // The stub's element value is a font name, so the delay arrives as NaN
  // until it is set to something readable.
  delaySlider.value = '1500';
  fire('tts-hover-delay', 'input');
  fire('tts-hover-delay', 'change');
  if (delayLabel.textContent !== '1.5s') {
    failed = true;
    console.log('FAIL 1500ms is shown as "' + delayLabel.textContent + '" rather than 1.5s');
  } else {
    console.log('     1500ms is shown as 1.5s, because that is pictureable');
  }

  const delaySaved = configPosts.filter((p) => 'tts_hover_delay' in p);
  if (!delaySaved.length || delaySaved[delaySaved.length - 1].tts_hover_delay !== 1500) {
    failed = true;
    console.log('FAIL the hover delay was not saved: ' + JSON.stringify(delaySaved));
  } else {
    console.log('     the hover delay is saved');
  }

  scopeSelect.value = 'off';
  fire('tts-hover-scope', 'change');
  genderSelect.value = 'female';
  fire('tts-voice-gender', 'change');
  const voiceSettings = configPosts.filter((p) => 'tts_hover_scope' in p || 'tts_voice_gender' in p);
  if (!voiceSettings.some((p) => p.tts_hover_scope === 'off') ||
      !voiceSettings.some((p) => p.tts_voice_gender === 'female')) {
    failed = true;
    console.log('FAIL the hover scope or voice gender was not saved: ' +
                JSON.stringify(voiceSettings));
  } else {
    console.log('     the hover scope and preferred voice are saved');
  }

  if (clickSwitch.getAttribute('aria-checked') === 'true') {
    failed = true;
    console.log('FAIL the click switch is still on after the firing loop clicked it');
  } else if (!clickState.textContent || clickState.textContent.indexOf('speak.') === 0) {
    failed = true;
    console.log('FAIL the click switch label is missing or shows a raw key: ' + clickState.textContent);
  } else {
    console.log('     the click switch turns off and says so in words');
  }
  const clickSaved = configPosts.filter((p) => 'tts_click_to_speak' in p);
  if (!clickSaved.length || clickSaved[clickSaved.length - 1].tts_click_to_speak !== false) {
    failed = true;
    console.log('FAIL click-to-speak was not saved as false: ' + JSON.stringify(clickSaved));
  } else {
    console.log('     click-to-speak is saved');
  }

  // The firing loop above set the voice picker to the stub's default value,
  // which is a font name and matches no installed voice. Put it back to the
  // system default, choose the male preference, and speak again: this is
  // the case that matters, because it is what a reader with no voice
  // picked by hand actually gets.
  const voicePicker = elements.get('tts-voice');
  voicePicker.value = '';
  fire('tts-voice', 'change');
  genderSelect.value = 'male';
  fire('tts-voice-gender', 'change');
  spokenUtterances.length = 0;
  fire('btn-test-voice', 'click');

  const utterances = spokenUtterances;
  if (!utterances.length) {
    failed = true;
    console.log('FAIL the voice test button said nothing at all');
  } else {
    console.log(`     the app asked for ${utterances.length} piece(s) of speech`);
  }
  const localised = utterances.filter((u) => u.lang);
  if (!localised.length) {
    failed = true;
    console.log('FAIL no utterance carried a language, so non-English text would be ' +
                'read with an English accent');
  } else {
    // The language check above switched the page to French, so an utterance
    // tagged "fr" here is the proof: the voice follows the interface, not
    // whatever the operating system was set to.
    console.log('     speech follows the interface language (' +
                localised[0].lang + '), not the system default');
  }
  // The page above was switched to French by the language check, so the
  // per-language voice questions are asked on pages of their own. That is
  // what really happens: choosing a language reloads the page, and the
  // locale is read once at load.
  //
  // The bug this guards against: Windows names its Hindi voices "Swara" and
  // "Hemant", not "Female" and "Male". An English-only name list matches
  // nothing there, so a Hindi reader silently gets whatever voice the
  // system liked best - which is the whole reason the language matters.
  for (const [code, expected] of [
    ['en', { male: 'Daniel', female: 'Zoe' }],
    ['hi', { male: 'Hemant', female: 'Swara' }],
    ['ar', { male: 'رجل', female: 'امرأة' }],
    ['es', { male: 'Diego', female: 'Sabina' }],
    // Accents, which "\\b" happens to cope with in current engines. They are
    // here as a second example of a name the matcher has to hold, not
    // because they were broken.
    ['fr', { male: 'Frédéric', female: 'Amélie' }],
  ]) {
    for (const gender of ['male', 'female']) {
      const page = makePage(code);
      vm.runInContext(source, page.context, { filename: 'app.js' });
      const picker = page.found.get('tts-voice-gender');
      picker.value = gender;
      fireOn(page, 'tts-voice-gender', 'change');
      fireOn(page, 'btn-test-voice', 'click');
      const picked = page.spoken.find((u) => u.voice);
      if (!picked) {
        failed = true;
        console.log(`FAIL no voice at all for a ${code} reader who wanted ${gender}`);
      } else if (!picked.voice.name.includes(expected[gender])) {
        failed = true;
        console.log(`FAIL a ${code} reader who wanted ${gender} got ` +
                    `"${picked.voice.name}" rather than ${expected[gender]}`);
      } else if (picked.lang && picked.lang.split('-')[0] !== code) {
        failed = true;
        console.log(`FAIL a ${code} reader got voice "${picked.voice.name}" ` +
                    `spelling the text as "${picked.lang}"`);
      }
    }
  }
  console.log('     every shipped language picks a voice in its own language and gender');

  // A manual choice outranks the gender preference, whichever language the
  // page is in. This is the reader who has already found the voice they want.
  {
    const page = makePage('es');
    vm.runInContext(source, page.context, { filename: 'app.js' });
    const gender = page.found.get('tts-voice-gender');
    gender.value = 'male';
    fireOn(page, 'tts-voice-gender', 'change');
    // The picker stores the voice's name, which is what a reader sees in
    // the list, so the check looks the option up the same way.
    const options = [...(page.found.get('tts-voice').options || [])];
    const wanted = options.find((o) => o.value.includes('Sabina'));
    if (!wanted) {
      failed = true;
      console.log('FAIL the voice list offered no Spanish voice to choose by hand: ' +
                  options.map((o) => o.value).join(', '));
    } else {
      const picker = page.found.get('tts-voice');
      picker.value = wanted.value;
      fireOn(page, 'tts-voice', 'change');
      fireOn(page, 'btn-test-voice', 'click');
      const picked = page.spoken.find((u) => u.voice);
      if (!picked || !picked.voice.name.includes('Sabina')) {
        failed = true;
        console.log('FAIL a hand-picked female voice was overruled by the male preference');
      } else {
        console.log('     a voice chosen by hand is never overruled by the gender setting');
      }
    }
  }

  // A voice chosen by hand is remembered across a reload. loadVoices reads
  // the picker's value to do this, which is wrong: it also moves that value
  // to show the automatic choice, so a hand-picked voice was forgotten the
  // next time the page loaded.
  {
    const page = makePage('en');
    vm.runInContext(source, page.context, { filename: 'app.js' });
    const list = [...(page.found.get('tts-voice').options || [])];
    const sabina = list.find((o) => o.value.includes('Sabina'));
    if (!sabina) {
      failed = true;
      console.log('FAIL the English page listed no Spanish voice to pick by hand');
    } else {
      const picker = page.found.get('tts-voice');
      picker.value = sabina.value;
      fireOn(page, 'tts-voice', 'change');
      // Pretend the page was reloaded: the server renders the saved choice
      // back onto the body, and loadVoices runs again over the same list.
      const reloaded = makePage('en', null, { 'data-tts-voice': sabina.value });
      vm.runInContext(source, reloaded.context, { filename: 'app.js' });
      const stillThere = reloaded.found.get('tts-voice').value;
      if (stillThere !== sabina.value) {
        failed = true;
        console.log(`FAIL a hand-picked voice was forgotten on reload: the picker ` +
                    `shows "${stillThere}" rather than "${sabina.value}"`);
      } else {
        console.log('     a hand-picked voice survives the list being rebuilt');
      }
    }
  }

  // With nothing chosen by hand, the app is choosing a voice for the reader.
  // The picker has to say which one, or "System default" is describing
  // something that is not read out - and a reader who wants a different
  // voice has no way to see what they are being given.
  {
    // Only the posts from this page count. The checks above deliberately
    // change the picker, and a save from one of those is expected.
    const postsBefore = configPosts.length;
    const page = makePage('hi');
    vm.runInContext(source, page.context, { filename: 'app.js' });
    const picker = page.found.get('tts-voice');
    if (!picker.value) {
      failed = true;
      console.log('FAIL the picker still says "System default" although a Hindi ' +
                  'voice is the one actually being used');
    } else if (!picker.value.includes('Hemant')) {
      failed = true;
      console.log(`FAIL the picker claims "${picker.value}" but the app reads with Hemant`);
    } else {
      console.log('     the picker shows the voice the app chose by itself');
    }
    // Showing a guess is not the same as recording a choice. If the app saved
    // this, the reader's own preference would be silently overwritten with
    // the app's guess, and they would have no way back to "no preference".
    const saved = configPosts.slice(postsBefore).filter((p) => 'tts_voice' in p);
    if (saved.length) {
      failed = true;
      console.log('FAIL the app saved a voice the reader never picked: ' +
                  JSON.stringify(saved[0]));
    } else {
      console.log('     showing the automatic choice does not save it as a choice');
    }
  }

  // Changing the preference has to reorder the list, because the list is in
  // the order the app chooses from. A list still sorted for the old
  // preference puts the voice actually in use somewhere in the middle.
  {
    const page = makePage('es');
    vm.runInContext(source, page.context, { filename: 'app.js' });
    const picker = page.found.get('tts-voice');
    const names = () => (picker.options || []).map((o) => o.value);
    genderSelectFor(page, 'male');
    const maleFirst = names().findIndex((n) => n.includes('Diego'));
    genderSelectFor(page, 'female');
    const femaleFirst = names().findIndex((n) => n.includes('Sabina'));
    if (maleFirst < 1 || femaleFirst < 1) {
      failed = true;
      console.log('FAIL the voice list lost a Spanish voice: ' + names().join(', '));
    } else if (femaleFirst > maleFirst) {
      failed = true;
      console.log('FAIL asking for a female voice left the male voice at the top: ' +
                  names().join(', '));
    } else {
      console.log('     changing the preference reorders the list to match it');
    }
  }

  // A saved voice can be uninstalled between one visit and the next. A
  // picker pointed at an option that is no longer in the list shows nothing
  // at all, which reads as a broken control rather than as a missing voice.
  {
    const page = makePage('en', null, { 'data-tts-voice': 'A Voice That Was Removed' });
    vm.runInContext(source, page.context, { filename: 'app.js' });
    const shown = page.found.get('tts-voice').value;
    if (!shown) {
      failed = true;
      console.log('FAIL a voice that is no longer installed left the picker blank');
    } else if (shown === 'A Voice That Was Removed') {
      failed = true;
      console.log('FAIL the picker still claims a voice that is not installed');
    } else if (!page.spoken.length) {
      // Nothing has been asked for to speak yet, which is fine; the point
      // is only that the picker names something real.
      console.log('     the picker falls back to a voice that is really installed');
    } else {
      console.log('     the picker falls back to a voice that is really installed');
    }
  }

  runUpdateChecks();

  // The update promises settle in a chain, so the exit waits for the end of
  // that chain rather than cutting it off at a guessed time. The module
  // index runs just before the exit, because it leaves the editor holding
  // an example and nothing after it should expect the page as it started.
  finish = () => runModuleIndexChecks(() => process.exit(failed ? 1 : 0));
}

// ---------------------------------------------------------------------------
// Updates. The promises in app.js have to settle before the status paragraph
// says anything, so these run after a tick rather than inline.
// ---------------------------------------------------------------------------
function runUpdateChecks() {
  if (!fetchCalls.includes('/api/version')) {
    failed = true;
    console.log('FAIL the app never asked what version it is');
  } else {
    console.log('     the app asks the server which version is running');
  }

  // The switch was pressed once by the firing loop, so it went from the
  // default (on) to off and said so in the settings file.
  const autoSaved = configPosts.filter((p) => 'auto_update' in p);
  if (!autoSaved.length || autoSaved[autoSaved.length - 1].auto_update !== false) {
    failed = true;
    console.log('FAIL turning the automatic check off was not saved: ' +
      JSON.stringify(autoSaved));
  } else {
    console.log('     the automatic-check switch is saved');
  }

  const autoEl = elements.get('auto-update-toggle');
  if (autoEl.getAttribute('aria-checked') !== 'false') {
    failed = true;
    console.log('FAIL the switch says it is on after being turned off');
  } else {
    console.log('     the switch state is announced, not just drawn');
  }

  // A check the reader asked for has to be forced, or the once-a-day limit
  // would answer "already checked" to a direct question.
  const checkCalls = fetchCalls.filter((u) => String(u).includes('/api/update/check'));
  if (!checkCalls.length) {
    failed = true;
    console.log('FAIL the update check was never asked for');
  } else {
    console.log('     the check button asks the server');
  }

  const forced = updateCheckBodies.filter((b) => b.force === true);
  if (!forced.length) {
    failed = true;
    console.log('FAIL no check was forced, so the button would be ignored ' +
      'when a check was done recently');
  } else {
    console.log('     a check the reader asked for ignores the wait');
  }

  const status = elements.get('update-status');
  const said = status.textContent || '';
  if (!said) {
    failed = true;
    console.log('FAIL the check finished without saying anything');
  } else if (said.indexOf('update.') === 0) {
    failed = true;
    console.log('FAIL the status shows a raw key rather than a sentence: ' + said);
  } else {
    console.log('     the answer to a check is a translated sentence');
  }

  const versionLine = elements.get('update-version');
  if (!versionLine.textContent) {
    failed = true;
    console.log('FAIL the running version is not shown');
  } else if (versionLine.textContent.indexOf('0.2.2-beta') === -1) {
    failed = true;
    console.log('FAIL the version line does not name the version: ' + versionLine.textContent);
  } else {
    console.log('     the running version is shown to the reader');
  }

  // A check that fails has to produce a sentence in the reader's language.
  // The server sends one; the app must show that sentence rather than the
  // short code, the English text meant for the log, or nothing at all.
  updateCheckReply = {
    success: true, applicable: true, current: '0.2.2-beta',
    update_available: false,
    error: 'could not reach GitHub to check for updates',
    error_code: 'network',
    error_text: CATALOGUE['update.error_network'],
    automatic: false,
  };
  status.textContent = '';
  fire('btn-check-update', 'click');

  setTimeout(() => {
    const saidOnFailure = status.textContent || '';
    if (saidOnFailure !== CATALOGUE['update.error_network']) {
      failed = true;
      console.log('FAIL a failed check did not show the sentence the server sent: ' +
        JSON.stringify(saidOnFailure));
    } else if (saidOnFailure === updateCheckReply.error) {
      // The updater's own English text is for the log. Showing it means the
      // reader is being handed a debug string instead of a sentence.
      failed = true;
      console.log('FAIL the reader is shown the English text meant for the log');
    } else if (saidOnFailure === updateCheckReply.error_code) {
      failed = true;
      console.log('FAIL the reader is shown the short code instead of a sentence');
    } else {
      console.log('     a failed check is explained in the reader\'s language');
    }
    if (!status.classList.contains('is-error')) {
      failed = true;
      console.log('FAIL a failed check is not marked as a problem');
    } else {
      console.log('     a failed check is marked as a problem, not just worded');
    }
  }, 10);

  // Whatever the check did, the download path needs a check that found
  // something. Run after the failure case above so its status text cannot
  // make the two look like one.
  setTimeout(() => runUpdateInstallChecks(), 30);
}

// ---------------------------------------------------------------------------
// The download. Checked here because it is the only part of the update that
// changes something on the reader's disk, and the only part that must not.
// ---------------------------------------------------------------------------
function runUpdateInstallChecks() {
  const status = elements.get('update-status');
  const row = elements.get('update-install-row');
  const installButton = elements.get('btn-install-update');
  // Whatever the Quit button has already done is not the update's doing.
  const closesBefore = closeAttempts;

  // Start from a check that found a new version.
  updateCheckReply = {
    success: true, applicable: true, current: '0.2.2-beta',
    update_available: true, latest: '99.0.0', error: '', error_code: '',
    error_text: '', automatic: false,
  };
  updateInstallOk = true;
  updateInstallReply = { success: true, version: '99.0.0', size: 10 };
  updateInstallBodies.length = 0;

  // A check that finds nothing new must not be leaving an offer behind.
  updateCheckReply.update_available = false;
  fire('btn-check-update', 'click');

  setTimeout(() => {
    if (!row.hidden) {
      failed = true;
      console.log('FAIL the download button is still offered with nothing to download');
    } else {
      console.log('     no download is offered until a check finds something');
    }

    updateCheckReply.update_available = true;
    fire('btn-check-update', 'click');

    setTimeout(() => {
      if (row.hidden) {
        failed = true;
        console.log('FAIL a check that found a new version did not offer the download');
      } else {
        console.log('     a new version is offered for download, not installed by itself');
      }

      const saidAvailable = status.textContent || '';
      if (saidAvailable.indexOf('99.0.0') === -1) {
        failed = true;
        console.log('FAIL the offer does not name the version: ' + saidAvailable);
      }

      fire('btn-install-update', 'click');

      setTimeout(() => {
        if (!updateInstallBodies.length) {
          failed = true;
          console.log('FAIL the download button never reached the server');
        } else {
          console.log('     the download is asked for only when the reader asks');
        }

        const saidReady = status.textContent || '';
        if (saidReady.indexOf('99.0.0') === -1) {
          failed = true;
          console.log('FAIL a finished download did not name the version: ' + saidReady);
        } else if (saidReady === CATALOGUE['update.status_ready'].replace('{0}', '')) {
          failed = true;
          console.log('FAIL the version was left out of the sentence');
        } else {
          console.log('     a checked build says which version is waiting');
        }

        if (!row.hidden) {
          failed = true;
          console.log('FAIL the download is offered again after it already arrived');
        }

        if (installButton.disabled) {
          failed = true;
          console.log('FAIL the buttons are left disabled after a finished download');
        } else {
          console.log('     the controls come back afterwards');
        }

        checkFailedDownload(status, row, closesBefore);
      }, 10);
    }, 10);
  }, 10);
}

// A download that does not arrive must be explained in the reader's language
// and must leave the offer up, so trying again is one click and not a
// restart of the app.
function checkFailedDownload(status, row, closesBefore) {
  updateInstallOk = false;
  updateInstallReply = {
    success: false, error_code: 'checksum_failed',
    error_text: CATALOGUE['update.error_checksum'],
  };
  fire('btn-check-update', 'click');

  setTimeout(() => {
    fire('btn-install-update', 'click');

    setTimeout(() => {
      const said = status.textContent || '';
      if (said !== CATALOGUE['update.error_checksum']) {
        failed = true;
        console.log('FAIL a failed download did not show the sentence the server sent: ' +
          JSON.stringify(said));
      } else if (said === updateInstallReply.error_code) {
        failed = true;
        console.log('FAIL the reader is shown the short code instead of a sentence');
      } else {
        console.log('     a download that fails is explained, not just refused');
      }

      if (!status.classList.contains('is-error')) {
        failed = true;
        console.log('FAIL a failed download is not marked as a problem');
      }

      if (row.hidden) {
        failed = true;
        console.log('FAIL a failed download left no way to try again');
      } else {
        console.log('     a failed download can be tried again without restarting');
      }

      // The window must never be closed for the reader. The app has no way
      // of knowing whether their work is saved, so it may not guess.
      const closedByUpdate = closeAttempts - closesBefore;
      if (closedByUpdate) {
        failed = true;
        console.log('FAIL the update flow closed the window: ' + closedByUpdate + ' time(s)');
      } else {
        console.log('     nothing is closed for the reader');
      }

      runSetupChecks();
      setTimeout(finish, 10);
    }, 10);
  }, 10);
}

// ---------------------------------------------------------------------------
// The first-run setup screen.
//
// The fiddly parts are all invisible from the markup: whether the wizard
// opens as a modal, whether focus lands on the question rather than staying
// on a button whose label just changed, and whether the step count comes
// from the page or from a list written out in app.js.
// ---------------------------------------------------------------------------
function runSetupChecks() {
  const next = elements.get('setup-next');
  const back = elements.get('setup-back');
  const skip = elements.get('setup-skip');
  const progress = elements.get('setup-progress');
  const status = elements.get('setup-status');
  const bodyStyle = documentStub.body.style;

  // It has to be a modal, not a panel slid over the page: only showModal
  // makes the rest of the app inert and traps the keyboard.
  if (!SETUP_DIALOG.__modalOpens) {
    failed = true;
    console.log('FAIL the setup screen was in the page but never opened as a dialog');
  } else {
    console.log('     the setup screen opens as a real modal');
  }

  // Escape must not dismiss it, because the screen exists to be answered.
  // Skipping is the way out, and it is a visible button.
  let escaped = false;
  const escapeEvent = {
    preventDefault() { escaped = true; },
    stopPropagation: noop,
  };
  fire('setup-dialog', 'cancel', escapeEvent);
  if (!escaped) {
    failed = true;
    console.log('FAIL Escape closed the setup screen');
  } else if (skip.hidden) {
    failed = true;
    console.log('FAIL Escape was blocked and no way out of the setup screen is offered');
  } else {
    console.log('     Escape cannot dismiss it, and skipping is on the button bar');
  }

  // Step one, and only step one.
  resetSetup();
  if (SETUP_PANELS.filter((panel) => !panel.hidden).length !== 1 || back.hidden !== true) {
    failed = true;
    console.log('FAIL the setup screen did not open on its first step alone');
  }

  const shownStep = () => SETUP_PANELS.findIndex((panel) => !panel.hidden) + 1;
  const focusLog = () => setupFocusLog[setupFocusLog.length - 1];

  // Forward through all of it, one press at a time.
  for (let step = 2; step <= SETUP_PANELS.length; step += 1) {
    fire('setup-next', 'click');
    if (shownStep() !== step) {
      failed = true;
      console.log(`FAIL pressing Next on step ${step - 1} showed step ` +
                  `${shownStep()} instead of ${step}`);
      break;
    }
    // Exactly one panel visible. Two at once means the reader is answering
    // a question they were not asked.
    if (SETUP_PANELS.filter((panel) => !panel.hidden).length !== 1) break;
    // Focus has to follow the question. Left on Next, a screen reader
    // announces "Next" again and the reader never learns the step changed.
    if (focusLog() !== SETUP_PANELS[step - 1].id.replace('setup-panel-', '')) {
      failed = true;
      console.log(`FAIL focus did not move to the step ${step} heading`);
    }
  }

  if (progress.textContent && progress.textContent.indexOf('setup.') === 0) {
    failed = true;
    console.log('FAIL the progress line still shows a raw key: ' + progress.textContent);
  } else if (!/\d/.test(progress.textContent || '')) {
    failed = true;
    console.log('FAIL the progress line says no numbers: ' + progress.textContent);
  } else {
    console.log('     the progress line counts the steps in words');
  }

  // The last step finishes rather than advancing, and says so.
  if (next.textContent !== CATALOGUE['setup.start']) {
    failed = true;
    console.log(`FAIL the last step offers "${next.textContent}" rather than the finish button`);
  } else {
    console.log('     the last step offers to start rather than to go on');
  }

  // And back again, which also puts the Back button away on the first step.
  fire('setup-back', 'click');
  fire('setup-back', 'click');
  if (shownStep() !== 1 || !back.hidden) {
    failed = true;
    console.log(`FAIL stepping back from step ${SETUP_PANELS.length} left the screen on ` +
                `step ${shownStep()} with Back ${back.hidden ? 'hidden' : 'shown'}`);
  } else {
    console.log('     stepping back works, and Back hides itself on the first step');
  }

  // A font is shown on the page, not just ticked in a list. The point of the
  // step is to see the font before agreeing to it.
  const opendyslexic = SETUP_FONT_RADIOS.find((radio) => radio.value === 'OpenDyslexic');
  const fontBefore = configPosts.length;
  opendyslexic.__listeners.change.forEach((handler) =>
    handler({ target: opendyslexic, preventDefault: noop, stopPropagation: noop }));
  const wantedFamily = opendyslexic.getAttribute('data-family');
  if (bodyStyle.fontFamily !== wantedFamily) {
    failed = true;
    console.log(`FAIL choosing OpenDyslexic left the page in "${bodyStyle.fontFamily}" ` +
                `rather than "${wantedFamily}"`);
  } else {
    console.log('     a chosen font is applied to the page straight away');
  }
  if (!configPosts.slice(fontBefore).some((p) => p.font === 'OpenDyslexic')) {
    failed = true;
    console.log('FAIL a font chosen in the setup screen was not saved: ' +
                JSON.stringify(configPosts.slice(fontBefore)));
  } else {
    console.log('     a font chosen in the setup screen is saved, not just drawn');
  }

  // The last one to finish: send the flag, then reload so the page is drawn
  // by the server in the language and font just chosen.
  // finishes rather than the one that moves on.
  const finishBefore = configPosts.length;
  for (let press = 0; press < SETUP_PANELS.length; press += 1) fire('setup-next', 'click');
  const finished = configPosts.slice(finishBefore).filter((p) => 'setup_complete' in p);
  if (finished.length !== 1 || finished[0].setup_complete !== true) {
    failed = true;
    console.log('FAIL finishing the setup screen did not mark it done: ' +
                JSON.stringify(configPosts.slice(finishBefore)));
  } else {
    console.log('     finishing marks the setup done');
  }

  // Skipping is the same flag and nothing else. A reader who picked a font
  // and then bailed out has to keep the font. `locale` and `access_code`
  // ride along on every settings save, so they are not an overwrite.
  const skipBefore = configPosts.length;
  fire('setup-skip', 'click');
  const skipped = configPosts.slice(skipBefore).filter((p) => 'setup_complete' in p);
  if (skipped.length !== 1 || skipped[0].setup_complete !== true) {
    failed = true;
    console.log('FAIL skipping did not mark the setup done: ' +
                JSON.stringify(configPosts.slice(skipBefore)));
  } else if ('font' in skipped[0] || 'setup_step' in skipped[0]) {
    failed = true;
    console.log('FAIL skipping overwrote a choice: ' + JSON.stringify(skipped[0]));
  } else {
    console.log('     skipping marks it done and leaves the choices alone');
  }

  // Someone who skipped and wants it after all.
  const againBefore = configPosts.length;
  fire('btn-setup-again', 'click');
  const again = configPosts.slice(againBefore).filter((p) => 'setup_complete' in p);
  if (again.length !== 1 || again[0].setup_complete !== false || again[0].setup_step !== 1) {
    failed = true;
    console.log('FAIL "run the setup screen again" did not reopen it from the start: ' +
                JSON.stringify(configPosts.slice(againBefore)));
  } else {
    console.log('     Settings can put the setup screen back');
  }

  // Two things can only be seen once the saves above have settled: what the
  // app says when a save is refused, and how many times the page was
  // redrawn. Both are promises, so both wait a tick. The language change
  // goes last and counts its own reloads, so the redraws belonging to the
  // presses above cannot be counted as if they were its own.
  setTimeout(() => {
    // A rejected save must say so, or the reader's answers are thrown away
    // and replaced by a blank first step.
    status.hidden = true;
    updateConfigOk = false;
    fire('setup-skip', 'click');
    setTimeout(() => {
      if (status.hidden) {
        failed = true;
        console.log('FAIL a setup save that was refused is not explained');
      } else if (status.textContent !== CATALOGUE['setup.error_saved']) {
        failed = true;
        console.log('FAIL the refusal says "' + status.textContent + '"');
      } else {
        console.log('     a save that is refused is explained in words');
      }
      updateConfigOk = true;
      status.hidden = true;

      let redrawn = 0;
      const realReload = sandbox.window.location.reload;
      sandbox.window.location.reload = () => { redrawn += 1; };
      const localeRadio = SETUP_LOCALE_RADIOS.find((radio) => radio.value === 'ar');
      const localeBefore = configPosts.length;
      localeRadio.__listeners.change.forEach((handler) =>
        handler({ target: localeRadio, preventDefault: noop, stopPropagation: noop }));
      const localePost = configPosts.slice(localeBefore).find((p) => p.locale === 'ar');
      if (!localePost) {
        failed = true;
        console.log('FAIL choosing a language in the setup screen did not save it');
      } else if (localePost.setup_step !== shownStep()) {
        // The redraw is what puts the wizard in the new language, and the
        // step is what stops it landing the reader back at question one.
        failed = true;
        console.log('FAIL the language was saved with setup_step ' + localePost.setup_step +
                    ' rather than the step being read, ' + shownStep());
      } else {
        console.log('     a language change saves the step, so it survives the redraw');
      }
      setTimeout(() => {
        sandbox.window.location.reload = realReload;
        if (redrawn !== 1) {
          failed = true;
          console.log('FAIL choosing a language in the setup screen redrew the page ' +
                      redrawn + ' time(s) rather than once');
        } else {
          console.log('     the page is redrawn so the wizard appears in that language');
        }
      }, 0);
    }, 0);
  }, 0);
}

// Change the preferred gender on a page of its own, as a reader would.
function genderSelectFor(page, value) {
  const el = page.found.get('tts-voice-gender');
  el.value = value;
  fireOn(page, 'tts-voice-gender', 'change');
}

// ---------------------------------------------------------------------------
// The notching buttons either side of the two spacing sliders.
//
// Dragging a slider thumb is hard with a shaky hand and near impossible
// behind a screen magnifier, so these buttons are a second way to reach the
// same two values. What matters is that they cannot put a number on screen
// that the server will refuse.
// ---------------------------------------------------------------------------
function runStepperChecks() {
  const cases = [
    {
      label: 'line height',
      target: 'line-height',
      less: 'line-height-less',
      more: 'line-height-more',
      out: 'line-height-label',
      bodyAttr: 'data-line-height',
      min: 1,
      max: 2.4,
      start: 1.6,
      floatFrom: '2.3',
      floatTo: '2.4',
      // Line height is a plain ratio; letter spacing is measured in pixels.
      // The readout says so, and a check that assumed otherwise would be
      // asserting the wrong thing.
      suffix: '',
    },
    {
      label: 'letter spacing',
      target: 'letter-spacing',
      less: 'letter-spacing-less',
      more: 'letter-spacing-more',
      out: 'letter-spacing-label',
      bodyAttr: 'data-letter-spacing',
      min: -0.5,
      max: 4,
      start: 0.5,
      floatFrom: '1.1',
      floatTo: '1.2',
      suffix: 'px',
    },
  ];

  for (const c of cases) {
    const slider = elements.get(c.target);
    const less = elements.get(c.less);
    const more = elements.get(c.more);
    const out = elements.get(c.out);
    if (!slider || !less || !more || !out) {
      failed = true;
      console.log(`FAIL ${c.label}: a stepper control is missing from the page`);
      continue;
    }

    // One notch, up and down, from the middle of the range.
    slider.value = '1.4';
    fire(c.more, 'click');
    if (slider.value !== '1.5') {
      failed = true;
      console.log(`FAIL ${c.label}: one notch up from 1.4 gave ${slider.value}, not 1.5`);
    }
    if (out.textContent !== '1.5' + c.suffix) {
      failed = true;
      console.log(`FAIL ${c.label}: the readout says ${out.textContent}, not 1.5${c.suffix}`);
    }
    if (documentStub.body.__attributes[c.bodyAttr] !== '1.5') {
      failed = true;
      console.log(`FAIL ${c.label}: the page did not restyle, still ` +
        `${documentStub.body.__attributes[c.bodyAttr]}`);
    }
    const beforeDown = configPosts.length;
    fire(c.less, 'click');
    if (slider.value !== '1.4') {
      failed = true;
      console.log(`FAIL ${c.label}: one notch down gave ${slider.value}, not 1.4`);
    }
    const saved = configPosts.slice(beforeDown).filter((p) => c.target.replace('-', '_') in p);
    if (saved.length !== 1 || saved[0][c.target.replace('-', '_')] !== 1.4) {
      failed = true;
      console.log(`FAIL ${c.label}: the new value was not saved, got ` +
        JSON.stringify(configPosts.slice(beforeDown)));
    }

    // The reason for the snapping. 2.3 + 0.1 is 2.4000000000000004 and
    // 1.1 + 0.1 is 1.2000000000000002 in floating point, and a reader
    // should never be shown either. The two ranges need different starting
    // points to get there, which is why this is not a constant.
    slider.value = c.floatFrom;
    fire(c.more, 'click');
    if (slider.value !== c.floatTo) {
      failed = true;
      console.log(`FAIL ${c.label}: one notch up from ${c.floatFrom} read ` +
        `${slider.value}, not ${c.floatTo}`);
    }

    // At each end the button that would overshoot is disabled, rather than
    // left there to do nothing when pressed.
    slider.value = String(c.max);
    fire(c.target, 'input');
    if (!more.disabled) {
      failed = true;
      console.log(`FAIL ${c.label}: the "more" button is still live at the maximum`);
    }
    slider.value = String(c.min);
    fire(c.target, 'input');
    if (!less.disabled) {
      failed = true;
      console.log(`FAIL ${c.label}: the "less" button is still live at the minimum`);
    }
    // Dragging back into range brings the button back to life, which is the
    // half that is easy to forget.
    slider.value = String(c.start);
    fire(c.target, 'input');
    if (more.disabled || less.disabled) {
      failed = true;
      console.log(`FAIL ${c.label}: both buttons stayed disabled away from the ends`);
    }
    slider.value = String(c.start);
  }

  // A disabled button is not the only guard. If it is ever pressed anyway,
  // the value still must not leave the range the server accepts.
  for (const c of cases) {
    const slider = elements.get(c.target);
    const more = elements.get(c.more);
    slider.value = String(c.max);
    more.disabled = true;
    more.__listeners.click.forEach((handler) => handler(fakeEvent));
    if (parseFloat(slider.value) > c.max) {
      failed = true;
      console.log(`FAIL ${c.label}: pressing "more" at the maximum left the value at ` +
        `${slider.value}, outside the range`);
    }
  }

  console.log('     the spacing steppers notch, clamp, save and disable at their limits');
}

// The module index. The interaction sweep above already fires the search
// input and the close button, so this checks the things a sweep cannot:
// that the results actually arrive, that the dialog behaves as a dialog,
// and that an example reaches the editor without losing what was there.
function runModuleIndexChecks() {
  const dialog = elements.get('modules-dialog');
  const opener = elements.get('btn-modules');
  const search = elements.get('modules-search-input');
  const results = elements.get('modules-results');
  const status = elements.get('modules-status');
  const empty = elements.get('modules-empty');
  const detail = elements.get('modules-detail');

  // Opened as a real modal, so the browser supplies the focus trap.
  if (typeof dialog.showModal !== 'function' || dialog.__open !== true) {
    failed = true;
    console.log('FAIL the module index did not open as a modal');
  } else {
    console.log('     the module index opens as a real modal');
  }

  // The search box takes focus, because that is what the reader came for.
  if (search !== document.activeElement) {
    failed = true;
    console.log('FAIL the module index did not put focus in the search box');
  } else {
    console.log('     it puts the reader straight in the search box');
  }

  const drawn = results.children || [];
  if (drawn.length === 0) {
    failed = true;
    console.log('FAIL the module index drew no results');
  } else {
    console.log(`     it draws results as a list of ${drawn.length} buttons`);
  }

  // The count is announced, and it is a number rather than a key.
  if (typeof status.textContent !== 'string' || !/\d/.test(status.textContent)) {
    failed = true;
    console.log(`FAIL the result count was not announced: "${status.textContent}"`);
  } else {
    console.log('     it announces how many modules matched');
  }

  // Availability is words, not a coloured dot. A screen reader says
  // nothing about a tint, and a dot is invisible in a high-contrast theme.
  const first = drawn[0];
  const text = JSON.stringify(first && first.__text || '');
  if (!/On this computer|Not on this computer/.test(text)) {
    failed = true;
    console.log(`FAIL availability was not given in words: ${text.slice(0, 120)}`);
  } else {
    console.log('     it says whether a module is on this computer, in words');
  }

  // 190 results is a lot to walk past, so only the first page is drawn
  // and the rest is one button away.
  if (drawn.length > 60) {
    failed = true;
    console.log(`FAIL the index drew all ${drawn.length} results at once`);
  } else {
    console.log('     it shows a page at a time rather than all 190 at once');
  }

  // Empty results are explained, not left as a blank panel.
  if (empty && empty.hidden) {
    failed = true;
    console.log('FAIL the empty message was hidden while there were no results');
  }
  if (empty && !/built in/.test(empty.textContent || '')) {
    failed = true;
    console.log('FAIL the empty message did not mention that some things are built in');
  } else {
    console.log('     finding nothing says why, rather than showing a blank');
  }

  // Closing sends focus back, so the next Tab is not from the top of the
  // page.
  elements.get('modules-close').__listeners.click.forEach((h) => h(fakeEvent));
  if (dialog.__open !== false) {
    failed = true;
    console.log('FAIL the module index did not close');
  }
  if (opener !== document.activeElement) {
    failed = true;
    console.log('FAIL closing the index did not return focus to its button');
  } else {
    console.log('     it closes and hands focus back to the button');
  }

  // Putting an example in the editor appends. A reference lookup must
  // never cost somebody the work they had already done.
  const before = editor.getValue();
  search.value = 'json';
  search.__listeners.input.forEach((h) => h(fakeEvent));
  setTimeout(() => {
    const found = (results.children || [])[0];
    if (!found || !found.__click) {
      failed = true;
      console.log('FAIL no module result offered a click handler');
      return finishModuleChecks(before);
    }
    found.__click(fakeEvent);
    setTimeout(() => {
      const insert = elements.get('modules-insert');
      if (!insert) {
        failed = true;
        console.log('FAIL the detail did not offer an insert button');
        return finishModuleChecks(before);
      }
      insert.__listeners.click.forEach((h) => h(fakeEvent));
      const after = editor.getValue();
      if (!after.startsWith(before)) {
        failed = true;
        console.log('FAIL inserting an example overwrote what was already there');
      } else if (!/import json/.test(after)) {
        failed = true;
        console.log('FAIL the example was not put in the editor');
      } else {
        console.log('     an example is added to the editor without losing what was there');
      }
      finishModuleChecks(before);
    }, 20);
  }, 20);
}

function finishModuleChecks() {
  setTimeout(() => {
    console.log('module index: 6 checks');
    done();
  }, 10);
}

// The module index. The interaction sweep above already fired the search
// input and the close button, so this checks what a sweep cannot: that
// results arrive and are drawn, that the dialog behaves as a dialog, and
// that an example reaches the editor without losing what was there.
//
// Text of a subtree, the way a screen reader would read it out.
function readText(node) {
  if (!node) return '';
  if (typeof node.textContent === 'string' && node.textContent) {
    return node.textContent;
  }
  return (node.children || []).map(readText).join(' ');
}

function runModuleIndexChecks(done) {
  const dialog = elements.get('modules-dialog');
  const opener = elements.get('btn-modules');
  const search = elements.get('modules-search-input');
  const results = elements.get('modules-results');
  const status = elements.get('modules-status');
  const empty = elements.get('modules-empty');

  // Open it from its own button, rather than relying on the interaction
  // sweep above: this check is then independent of where that sweep's
  // list happens to sit, and it exercises the button a reader presses.
  (opener.__listeners.click || []).forEach((h) => h(fakeEvent));

  // Opened as a real modal, so the browser supplies the focus trap.
  if (dialog.__open !== true) {
    failed = true;
    console.log('FAIL the module index did not open as a modal');
  } else {
    console.log('     the module index opens as a real modal');
  }

  // The search box takes focus, because that is what the reader came for.
  if (documentStub.activeElement !== search) {
    failed = true;
    console.log('FAIL the module index did not put focus in the search box');
  } else {
    console.log('     it puts the reader straight in the search box');
  }

  // The catalogue is fetched, rather than embedded, and asked for by name.
  if (!fetchCalls.some((u) => u.includes('/api/modules'))) {
    failed = true;
    console.log('FAIL the module index never asked the server for the catalogue');
  } else {
    console.log('     it asks the server for the catalogue');
  }

  setTimeout(() => {
    const drawn = (results.children || []).filter((c) => c.tagName !== 'li-more');
    if (drawn.length === 0) {
      failed = true;
      console.log('FAIL the module index drew no results');
    } else {
      console.log(`     it draws the ${drawn.length} results the server sent`);
    }

    // The count is announced, in a number rather than a raw key.
    if (!/\d/.test(String(status.textContent))) {
      failed = true;
      console.log(`FAIL the result count was not announced: "${status.textContent}"`);
    } else {
      console.log('     it announces how many modules matched');
    }

    // Each result names the module, says what it is for, and says whether
    // it is on this computer. Availability in words, not a coloured dot:
    // a screen reader says nothing about a tint.
    const said = readText(drawn[0]);
    if (!said.includes('json')) {
      failed = true;
      console.log(`FAIL the first result did not name its module: ${said.slice(0, 90)}`);
    } else if (!/On this computer|Not on this computer/.test(said)) {
      failed = true;
      console.log(`FAIL availability was not given in words: ${said.slice(0, 90)}`);
    } else {
      console.log('     a result names the module, says what it does, and says if it is here');
    }

    // A module that is not installed is still listed - it is part of
    // Python - but it says so, rather than looking runnable.
    const offText = readText(drawn[1]);
    if (!/Not on this computer/.test(offText)) {
      failed = true;
      console.log(`FAIL a missing module was not marked: ${offText.slice(0, 90)}`);
    } else {
      console.log('     a module that is not installed says so in words');
    }

    // Choosing a result loads its example, and offers the two things a
    // reader can do with it.
    const button = (drawn[0].children || [])[0];
    const handlers = (button && button.__listeners && button.__listeners.click) || [];
    if (handlers.length === 0) {
      failed = true;
      console.log('FAIL a module result was not clickable');
    } else {
      handlers[0](fakeEvent);
    }

    setTimeout(() => {
      const detail = elements.get('modules-detail');
      const detailText = readText(detail);
      if (!detailText.includes('import json')) {
        failed = true;
        console.log(`FAIL the example was not shown: ${detailText.slice(0, 120)}`);
      } else {
        console.log('     choosing a module shows its example');
      }
      // Web-blocked is a sentence, and only appears for a module that
      // really cannot run there.
      const detailAll = readText(detail);
      if (/web version/.test(detailAll)) {
        failed = true;
        console.log('FAIL a runnable module was marked as web-blocked');
      } else {
        console.log('     a runnable example is not marked as blocked');
      }

      // Putting it in the editor appends. A reference lookup must never
      // cost somebody the work they had already done.
      const before = editorInstance.getValue();
      const insert = (detail.children || []).map(readText).join(' ');
      const insertBtn = findButtonByText(detail, 'Put the example in the editor');
      if (!insertBtn) {
        failed = true;
        console.log(`FAIL the detail offered no insert button: ${insert.slice(0, 140)}`);
      } else {
        insertBtn.__listeners.click.forEach((h) => h(fakeEvent));
        const after = editorInstance.getValue();
        if (after === before) {
          failed = true;
          console.log('FAIL inserting an example changed nothing');
        } else if (!after.startsWith(before)) {
          failed = true;
          console.log('FAIL inserting an example overwrote what was already there');
        } else if (!after.includes('import json')) {
          failed = true;
          console.log('FAIL the example was not put in the editor');
        } else {
          console.log('     an example is added without losing what was already there');
        }
      }

      // The level filters. Choosing one has to be reflected in the
      // request and in aria-pressed, and the others have to stand down -
      // two filters that look pressed at once is a lie about what is
      // being shown.
      const before2 = fetchCalls.length;
      const everyday = MODULE_LEVEL_BUTTONS[2];
      (everyday.__listeners.click || []).forEach((h) => h(eventFor(everyday)));
      if (everyday.__attributes['aria-pressed'] !== 'true') {
        failed = true;
        console.log('FAIL the chosen level filter did not report itself as pressed');
      } else {
        console.log('     a level filter reports that it is the one in use');
      }
      const othersPressed = MODULE_LEVEL_BUTTONS.filter(
        (b) => b !== everyday && b.__attributes['aria-pressed'] === 'true');
      if (othersPressed.length) {
        failed = true;
        console.log(`FAIL ${othersPressed.length} other level filters stayed pressed`);
      } else {
        console.log('     the other filters stand down, so only one looks chosen');
      }
      const asked = fetchCalls.slice(before2).join(' ');
      if (!/level=everyday/.test(asked)) {
        failed = true;
        console.log(`FAIL the level was not sent to the server: ${asked.slice(0, 120)}`);
      } else {
        console.log('     the chosen level is sent to the server');
      }

      // And the index gets out of the way, handing focus back.
      if (dialog.__open !== false) {
        failed = true;
        console.log('FAIL inserting did not close the index');
      }
      if (documentStub.activeElement !== opener) {
        failed = true;
        console.log('FAIL focus was not returned to the button that opened the index');
      } else {
        console.log('     it closes and hands focus back to the button');
      }

      done();
    }, 20);
  }, 20);
}

// Depth-first search for a button whose text is exactly this, so the check
// does not depend on the order the detail pane was built in.
function findButtonByText(node, text) {
  for (const child of (node && node.children) || []) {
    if ((child.className || '').includes('btn')
        && readText(child).trim() === text) {
      return child;
    }
    const deeper = findButtonByText(child, text);
    if (deeper) return deeper;
  }
  return null;
}

setTimeout(() => {
  runPanelChecks();
  runStepperChecks();
  runLanguageChecks();
  setTimeout(runLanguageReloadCheck, 10);
}, 50);
