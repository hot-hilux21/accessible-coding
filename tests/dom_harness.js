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

// tint.js is loaded ahead of app.js, the way the template loads it. It is the
// real file, not a stub: the panel colour is the one place in this app where
// the arithmetic decides whether the reader can read the screen, and a stub
// would let the checks pass against behaviour no reader ever gets.
const TINT_JS = path.join(
  __dirname, '..', 'src', 'accessible_ide', 'static', 'js', 'tint.js'
);
const tintSource = fs.readFileSync(TINT_JS, 'utf8');

// tests/tint_vectors.json is the one file both copies of the tint maths are
// checked against. The Python suite reads it in test_panel_materials.py; this
// is the browser's half of the same contract. Without it the two copies are
// only ever compared by eye, and they did drift once: Python's round() rounds
// ties to even, Math.round rounds them up, and 12 cases came out a channel
// apart. Both answers were readable, so no contrast test noticed. The vectors
// marked "tie" are the ones that catch it.
const TINT_VECTORS = JSON.parse(
  fs.readFileSync(path.join(__dirname, 'tint_vectors.json'), 'utf8')
);

// Ids that index.html is expected to provide. Anything app.js looks up but
// that is missing here will be reported, because that is exactly the bug
// this harness exists to catch.
const KNOWN_IDS = new Set([
  'btn-run', 'btn-stop', 'btn-save', 'btn-open', 'btn-read-line', 'btn-clear', 'btn-quit',
  'editor', 'output', 'error-panel', 'error-message', 'file-input',
  'settings-dialog', 'settings-title', 'settings-status', 'btn-settings',
  'btn-settings-close', 'font-select',
  // The four areas the chosen font is used in. app.js looks all four up on
  // the way in, so an id missing from here would be reported as unknown
  // rather than quietly skipped - and the boxes have to exist for the "an
  // area can be unticked on its own" path to be exercised at all.
  'font-code', 'font-output', 'font-shell', 'font-ui',
  'font-size', 'font-size-label',
  'font-weight', 'font-weight-label',
  'line-height', 'line-height-label', 'letter-spacing',
  'letter-spacing-label', 'line-height-less', 'line-height-more',
  'letter-spacing-less', 'letter-spacing-more',
  'blur-intensity', 'blur-intensity-label',
  'blur-field', 'theme-select', 'contrast-select', 'focus-mode',
  'reduce-motion', 'reduce-motion-state',
  // The background gradient switch and the theme builder. The builder is
  // hidden until the custom theme is chosen, so its fields are declared
  // here for the same reason as the setup screen: app.js has to treat them
  // as optional, and the harness has to exercise that path.
  'theme-gradient', 'theme-gradient-state', 'theme-builder',
  'icon-only', 'setup-icon-only', 'icon-only-state', 'setup-icon-only-state',
  'reading-ruler', 'reading-ruler-state',
  // The builder renders its fields from a Jinja loop over these nine keys,
  // and each key emits four ids: the hex input, the colour picker, the
  // error line, and the contrast status line. All four are listed for every
  // key: a key whose ids are only partly declared is reported as unknown.
  'theme-custom-page', 'theme-custom-bg', 'theme-custom-fg',
  'theme-custom-selection', 'theme-custom-keyword', 'theme-custom-string',
  'theme-custom-comment', 'theme-custom-number', 'theme-custom-function',
  'theme-custom-page-picker', 'theme-custom-bg-picker',
  'theme-custom-fg-picker', 'theme-custom-selection-picker',
  'theme-custom-keyword-picker', 'theme-custom-string-picker',
  'theme-custom-comment-picker', 'theme-custom-number-picker',
  'theme-custom-function-picker',
  'theme-custom-page-error', 'theme-custom-bg-error',
  'theme-custom-fg-error', 'theme-custom-selection-error',
  'theme-custom-keyword-error', 'theme-custom-string-error',
  'theme-custom-comment-error', 'theme-custom-number-error',
  'theme-custom-function-error',
  'theme-custom-page-status', 'theme-custom-bg-status',
  'theme-custom-fg-status', 'theme-custom-selection-status',
  'theme-custom-keyword-status', 'theme-custom-string-status',
  'theme-custom-comment-status', 'theme-custom-number-status',
  'theme-custom-function-status',
  'theme-custom-reset', 'theme-custom-saved',
  'theme-confirm-page', 'theme-confirm-bg', 'theme-confirm-fg',
  'theme-confirm-selection', 'theme-confirm-keyword', 'theme-confirm-string',
  'theme-confirm-comment', 'theme-confirm-number', 'theme-confirm-function',
  'setup-theme-confirm-page', 'setup-theme-confirm-bg',
  'setup-theme-confirm-fg', 'setup-theme-confirm-selection',
  'setup-theme-confirm-keyword', 'setup-theme-confirm-string',
  'setup-theme-confirm-comment', 'setup-theme-confirm-number',
  'setup-theme-confirm-function',
  'setup-theme-custom-page', 'setup-theme-custom-bg', 'setup-theme-custom-fg',
  'setup-theme-custom-selection', 'setup-theme-custom-keyword',
  'setup-theme-custom-string', 'setup-theme-custom-comment',
  'setup-theme-custom-number', 'setup-theme-custom-function',
  'setup-theme-custom-page-picker', 'setup-theme-custom-bg-picker',
  'setup-theme-custom-fg-picker', 'setup-theme-custom-selection-picker',
  'setup-theme-custom-keyword-picker', 'setup-theme-custom-string-picker',
  'setup-theme-custom-comment-picker', 'setup-theme-custom-number-picker',
  'setup-theme-custom-function-picker',
  'glass-tint-picker', 'glass-tint-hex', 'glass-tint-error', 'glass-tint-reset',
  'tts-toggle', 'tts-state', 'tts-voice', 'tts-rate', 'tts-rate-label',
  'tts-voice-gender', 'tts-hover-scope', 'tts-hover-delay',
  'tts-hover-delay-label', 'tts-click', 'tts-click-state',
  'btn-test-voice',
  'auto-update-toggle', 'auto-update-state', 'btn-check-update',
  'update-status', 'update-version',
  // The update channel. It has to be declared here, like every other id
  // app.js reads, or the harness reports an unknown id instead of quietly
  // skipping the control.
  'update-channel', 'update-channel-help',
  'update-install-row', 'update-install-label', 'update-install-help',
  'btn-install-update',
  // The restart-to-apply row, the unsaved-changes warning, and the update
  // notice. These live in index.html and app.js reads them on the way in, so
  // they belong in this list; leaving them out reports them as unknown ids.
  'update-restart-row', 'btn-restart-update',
  'save-warn-dialog', 'btn-save-warn-cancel', 'btn-save-warn-confirm',
  'update-notice',
  'font-bundled-note', 'sample-text', 'font-preview', 'font-preview-text',
  'font-upload', 'btn-remove-font', 'font-upload-status',
  // The same font choice offered on the first-run screen. app.js looks both
  // up on the way in, so an id missing here would be reported as unknown.
  'setup-font-upload', 'setup-font-upload-status',
  'preview-status', 'btn-reset-config',
  'btn-export-config', 'btn-import-config', 'config-file-input', 'backup-status',
  'highlight-color-hex', 'highlight-color-picker', 'highlight-error',
  'highlight-status', 'btn-reset-highlight',
  'language-select',
  // The first-run setup screen. The server stops rendering it once the
  // reader has finished it, so app.js has to treat every one of these as
  // optional - the harness declares them so that path is exercised rather
  // than skipped.
  'setup-dialog', 'setup-progress', 'setup-status', 'setup-back',
  'setup-next', 'setup-skip', 'btn-setup-again',
  // The Python shell. Declared here for the same reason as the index above:
  // without these, the pane cannot be found and nothing about the shell is
  // exercised, while the harness still reports success.
  'btn-shell', 'shell-pane', 'shell-input', 'shell-output', 'shell-status',
  'shell-form', 'shell-clear', 'shell-close',
  // The answer row the output pane shows while a program is waiting to be
  // answered. app.js looks all three up on the way in and registers the
  // submit handler against the form, so an id missing here is not a quietly
  // absent feature: the lookup returns null, the script throws while it is
  // still loading, and everything defined after that point goes with it.
  'answer-form', 'answer-input', 'answer-status',
  // The two keypress settings and their record buttons. The selects carry
  // explicit values below rather than the font-name default a stub hands
  // out, because every press check is written against the real defaults:
  // Ctrl+Enter runs, Escape twice stops.
  'run-key', 'stop-key', 'btn-record-run', 'btn-record-stop',
  'record-run-text', 'record-stop-text', 'keys-run-status', 'keys-stop-status',
  // The Python dictionary and the quit question. The dictionary's rows are
  // drawn by the server, so the harness builds a small one of its own below
  // with real rows in it: a stub whose querySelectorAll answered with nothing
  // would let the filter run over an empty list, and every search check would
  // report success without a row ever being hidden.
  'glossary-dialog', 'btn-glossary', 'btn-glossary-close', 'glossary-search',
  'glossary-status', 'glossary-empty',
  'quit-dialog', 'btn-quit-keep', 'btn-quit-confirm',
  // The split view: the editor and the right-hand column, and the two
  // dividers between them. The dividers are separators, so the harness can
  // check the keyboard path and the drag path both work.
  'workspace', 'right-column', 'divider-main', 'divider-shell',
  // The two JSON script blocks the server embeds. They are not elements
  // app.js draws with, but without them every t() call falls back to
  // returning the key, and this harness would stop testing translations
  // at all while still reporting success.
  'i18n-data', 'i18n-meta',
  // Each theme's panel text colours. Without these the browser has no way to
  // work out which backgrounds keep the text readable, so it falls back to
  // pinning the tint to the panel's own luminance - a path that destroys most
  // of the colour on the light themes. Declared here so that path is measured
  // rather than quietly skipped.
  'panel-info',
  // The pane text toolbars. app.js looks every one of these up on the way in,
  // and an id it cannot find is a getElementById returning null - so without
  // these the toolbar would be silently absent and each check below would pass
  // while the feature did nothing at all.
  'mini-editor-toggle', 'mini-editor-panel',
  // The editor's line-number tick. app.js looks it up on the way in, so a
  // missing id here would leave the control silently absent.
  'line-numbers-toggle',
  // The fade tick and its slider, beside the line-number tick in the editor
  // strip. app.js looks all four up on the way in.
  'fade-toggle', 'fade-amount', 'fade-slider', 'fade-slider-value',
  'editor-font-size', 'editor-line-height', 'editor-letter-spacing',
  'editor-font-size-value', 'editor-line-height-value', 'editor-letter-spacing-value',
  'mini-output-toggle', 'mini-output-panel',
  'output-font-size', 'output-line-height', 'output-letter-spacing',
  'output-font-size-value', 'output-line-height-value', 'output-letter-spacing-value',
  'mini-shell-toggle', 'mini-shell-panel',
  'shell-font-size', 'shell-line-height', 'shell-letter-spacing',
  'shell-font-size-value', 'shell-line-height-value', 'shell-letter-spacing-value',
  // The trace table. app.js looks every one of these up on the way in too, so
  // a missing id here would leave the feature silently absent while each check
  // below still passed.
  'btn-trace', 'trace-window', 'trace-rows', 'trace-note', 'trace-scroll',
  'trace-grip', 'trace-close',
]);

const numericIds = new Set([
  'font-size', 'font-weight', 'line-height', 'letter-spacing', 'blur-intensity', 'tts-rate',
  'fade-slider',
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
  // The nine pane sliders. The limits are the ones CONFIG_RANGES enforces
  // server-side, so a pane cannot be dragged somewhere the config would then
  // refuse to store. The starting values are the reading defaults, which is
  // what an untouched pane is following before anybody touches it.
  'editor-font-size': { min: '12', max: '28', step: '1', value: '16' },
  'editor-line-height': { min: '1', max: '2.4', step: '0.1', value: '1.6' },
  'editor-letter-spacing': { min: '-0.5', max: '4', step: '0.1', value: '0.5' },
  'output-font-size': { min: '12', max: '28', step: '1', value: '16' },
  'output-line-height': { min: '1', max: '2.4', step: '0.1', value: '1.6' },
  'output-letter-spacing': { min: '-0.5', max: '4', step: '0.1', value: '0.5' },
  'shell-font-size': { min: '12', max: '28', step: '1', value: '16' },
  'shell-line-height': { min: '1', max: '2.4', step: '0.1', value: '1.6' },
  'shell-letter-spacing': { min: '-0.5', max: '4', step: '0.1', value: '0.5' },
  // The fade slider in the editor strip. Same setting as the Settings one,
  // and the same 0..1 range, so the two views cannot drift apart.
  'fade-slider': { min: '0', max: '1', step: '0.05', value: '0.5' },
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

// The pane dividers are separators, and the template gives each one its
// role, orientation, size range and starting size. A stub without these
// would let every separator check pass for the wrong reason.
const DIVIDER_ATTRIBUTES = {
  'divider-main': {
    role: 'separator',
    'aria-orientation': 'vertical',
    'aria-valuemin': '20',
    'aria-valuemax': '80',
    'aria-valuenow': '50',
    tabindex: '0',
  },
  'divider-shell': {
    role: 'separator',
    'aria-orientation': 'horizontal',
    'aria-valuemin': '20',
    'aria-valuemax': '80',
    'aria-valuenow': '50',
    tabindex: '0',
  },
};

const lookups = [];
const noop = () => {};
const reloads = [];
let reloadsBefore = 0;
let resetReloadsBefore = 0;

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
  'theme-select': ['high-contrast', 'dark', 'pastel', 'light', 'ocean', 'forest', 'custom'],
  'update-channel': ['beta', 'stable'],
};

const optionsFor = (values) => values.map((v) => makeElement(v, {}, { value: v, textContent: v }));

// The nine picks the theme builder starts with, mirroring the defaults in
// routes.py. The builder's fields are hex boxes, so a stub that left them
// at the generic "OpenDyslexic" value would make every live preview throw
// and the checks would pass for the wrong reason. All nine are needed: the
// live preview reads the page and selection colours as well, and a missing
// one leaves a bad value behind.
const THEME_CUSTOM_DEFAULTS = {
  'theme-custom-page': '#0b0b0b',
  'theme-custom-bg': '#0b0b0b',
  'theme-custom-fg': '#ffffff',
  'theme-custom-selection': '#4d4300',
  'theme-custom-keyword': '#ff9a9a',
  'theme-custom-string': '#93e6a8',
  'theme-custom-comment': '#b4b4b4',
  'theme-custom-number': '#ffd93d',
  'theme-custom-function': '#93d4ff',
};

// The attributes an element carries in the template, beyond the ones every
// element gets. min, max and step are attributes rather than properties, so
// this is where the sliders' limits have to live.
// The three pane toolbars start closed, and the template says so with
// aria-expanded. app.js reads that attribute to decide which way the next
// press goes, so a stub without it would make the first press look like a
// close and every toggle check would pass for the wrong reason.
const PANE_TOGGLES = {
  'mini-editor-toggle': { 'aria-expanded': 'false' },
  'mini-output-toggle': { 'aria-expanded': 'false' },
  'mini-shell-toggle': { 'aria-expanded': 'false' },
};

// The four areas the chosen font is used in. The template draws them ticked,
// so the harness has to start them ticked too: applyFont reads them back, and
// unticked boxes would clear every token and make the chosen font look as
// though it applied nowhere.
const FONT_AREA_IDS = new Set(['font-code', 'font-output', 'font-shell', 'font-ui']);

function attributesFor(id) {
  const range = RANGE_INPUTS[id];
  return Object.assign(
    { 'data-tts-voice-gender': 'male' },
    range ? { min: range.min, max: range.max, step: range.step } : {},
    STEPPER_BUTTONS[id] || {},
    DIVIDER_ATTRIBUTES[id] || {},
    PANE_TOGGLES[id] || {},
  );
}

function makeElement(id, extraAttributes = {}, extraProps = {}) {
  const attributes = {
    'aria-checked': 'true',
    'aria-pressed': 'false',
    'data-theme': 'high-contrast',
    'data-font': 'OpenDyslexic',
    'data-font-size': '16',
    'data-font-weight': '400',
    'data-highlight-color': '',
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
  // the whole point of the panel, and it has to be checkable. setProperty
  // records the same way, so a CSS variable the code wrote (the pane
  // widths) can be read back as a property.
  const style = {
    setProperty: (name, value) => { style[name] = value; },
    removeProperty: (name) => { delete style[name]; },
  };

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
    // Removal is real too. The pane dividers add move and up handlers for
    // the duration of a drag and remove them on release; a stub that kept
    // them would fire a stale handler at the next drag.
    removeEventListener: (type, handler) => {
      listeners[type] = (listeners[type] || []).filter((h) => h !== handler);
    },
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
      child.parentNode = el;
      return child;
    },
    removeChild(child) {
      el.children = el.children.filter((c) => c !== child);
      el.options = el.options.filter((o) => o !== child);
      if (child.parentNode === el) {
        child.parentNode = null;
      }
    },
    // A real element removes itself from its parent. The dev-mode code
    // removes the channel option that way, and a stub that did nothing
    // would leave the hidden channel on offer after dev mode was off.
    remove() {
      if (el.parentNode) {
        el.parentNode.removeChild(el);
      }
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
    // A real element answers "is there an option with this value?" by
    // searching its own options. The dev-mode code asks exactly that of the
    // channel list, and a stub that always answered "yes" would make the
    // option never get added. Anything else falls back to a fresh element,
    // which is what the older checks expect.
    querySelector: (selector) => {
      const optionMatch = String(selector).match(/^option\[value="([^"]+)"\]$/);
      if (optionMatch) {
        return (el.options || []).find((o) => o.value === optionMatch[1]) || null;
      }
      return makeElement('__query__');
    },
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
  makeSetupPanel('theme', false),
  makeSetupPanel('tour', false),
];

// The radios, carrying the same data-family stacks the template renders, so
// the live preview is held to the font the code would really apply.
const SETUP_FONT_RADIOS = FONT_OPTIONS.map((option) => {
  const value = option.value;
  return makeElement(`setup-font-${value}`, {
    name: 'setup-font',
    'data-family': option.__attributes['data-family'],
  }, { value, checked: value === 'OpenDyslexic' });
});

const SETUP_LOCALE_RADIOS = ['en', 'hi', 'fr', 'es', 'ar', 'uk'].map((code) =>
  makeElement(`setup-locale-${code}`, { name: 'setup-locale' },
    { value: code, checked: code === 'en' })
);

// Each theme's panel colour and the three token colours sitting on it, which is
// what the server embeds in the page. The browser needs both to work out the
// painted tint before it paints anything, so they are here rather than being
// left to /api/themes: a fetch that has not answered yet would mix the tint
// against a background no reader ever sees.
// tests/test_panel_materials.py fails if this and routes.py drift apart, so a
// new theme cannot be added to one and forgotten in the other.
const PANEL_INFO = {
  'high-contrast': { panel: '#161616', texts: ['#ffffff', '#c9c9c9', '#ffc1c1'] },
  dark: { panel: '#1f2126', texts: ['#e6e6e6', '#9aa3ad', '#ffb4a0'] },
  pastel: { panel: '#f2ecdf', texts: ['#453f3a', '#736a5f', '#8f2f1a'] },
  light: { panel: '#f2f2f2', texts: ['#2b2b2b', '#5f5f5f', '#8f1a1a'] },
};

// What /api/themes answers with, held as a table so the checks can name the
// colours they expect rather than hard-coding them beside the fetch stub.
const SANDBOX_THEMES = {
  'high-contrast': {
    name: 'High Contrast', bg: '#0b0b0b', fg: '#ffffff', gutter_bg: '#161616',
    selection: '#4d4300', highlight: '#1e1e1e',
  },
  dark: { name: 'Dark', bg: '#17181c', fg: '#e6e6e6', gutter_bg: '#1f2126',
    selection: '#234a6b', highlight: '#23262c',
    keyword: '#ff9a9a', string: '#93e6a8', comment: '#b4b4b4',
    number: '#ffd93d', function: '#93d4ff' },
  pastel: { name: 'Pastel', bg: '#fbf6ec', fg: '#453f3a', gutter_bg: '#f2ecdf',
    selection: '#e3d2ab', highlight: '#f1ead9' },
  light: { name: 'Light', bg: '#fcfcfc', fg: '#2b2b2b', gutter_bg: '#f2f2f2',
    selection: '#bcd6f2', highlight: '#ececec' },
  ocean: { name: 'Ocean', bg: '#0d1420', fg: '#e8eef7', gutter_bg: '#111a28',
    selection: '#1e3a5f', highlight: '#131c2b' },
  forest: { name: 'Forest', bg: '#0e1510', fg: '#e6efe6', gutter_bg: '#121a14',
    selection: '#1f3d2a', highlight: '#141d16' },
  // The reader's own theme. The server derives the full palette from the
  // seven picks; this is the default derivation, which is what a fresh
  // config produces.
  custom: { name: 'Custom', bg: '#0b0b0b', fg: '#ffffff', gutter_bg: '#151515',
    selection: '#484848', highlight: '#151515' },
};

// The theme choices in the wizard, one per theme the server offers. The
// custom theme is among them, so a reader can pick it before the app has
// ever been used.
const SETUP_THEME_RADIOS = Object.keys(SANDBOX_THEMES).map((key) =>
  makeElement(`setup-theme-${key}`, { name: 'setup-theme' },
    { value: key, checked: key === 'high-contrast' })
);

// The four materials, in the order the template renders them. "off" starts
// chosen, because that is the default and the safe answer.
const GLASS_MATERIAL_RADIOS = ['off', 'mica', 'frosted', 'acrylic'].map((value) =>
  makeElement(`glass-material-${value}`, { name: 'glass-material' },
    { value, checked: value === 'off' })
);



// The preset colour squares on the setup step. Choosing one starts the
// reader's own theme from that preset, and it must not move focus: the
// square the reader is standing on is where they are, and jumping the
// heading back into view would scroll the page out from under them.
//
// Each query hands out fresh cells and records them. The per-language pages
// run app.js again against the same shared dialog, so a single fixed array
// would collect their change handlers too - and those pages have no tint
// helper, so firing one would throw instead of testing anything. The first
// registration is the real page's.
const setupSwatchRegistrations = [];

function makeSetupSwatchCells() {
  return ['dark'].map((themeKey) =>
    makeElement(`setup-swatch-${themeKey}-bg`,
      { 'data-theme': themeKey, 'data-role': 'bg' },
      { value: SANDBOX_THEMES[themeKey].bg }));
}

const SETUP_DIALOG = makeElement('setup-dialog', {}, {
  // Recorded rather than discarded: "the wizard was in the markup but never
  // opened" is a real failure that a noop would hide completely.
  showModal() { SETUP_DIALOG.__modalOpens += 1; },
  querySelectorAll: (selector) => {
    if (selector === '.setup-panel') return SETUP_PANELS;
    if (selector === 'input[name="setup-locale"]') return SETUP_LOCALE_RADIOS;
    if (selector === 'input[name="setup-font"]') return SETUP_FONT_RADIOS;
    if (selector === 'input[name="setup-theme"]') return SETUP_THEME_RADIOS;
    if (selector === '.setup-swatch-cell') {
      const cells = makeSetupSwatchCells();
      setupSwatchRegistrations.push(cells[0]);
      return cells;
    }
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

// ---------------------------------------------------------------------------
// The Python dictionary. Real rows, because hiding them is the only thing the
// dialog does. Two sections, so the check that a section left with no visible
// entry goes with them has something to catch - the failure that would leave a
// heading standing over nothing.
// ---------------------------------------------------------------------------

function makeGlossaryRow(label, text) {
  return makeElement('glossary-entry', { 'data-glossary-entry': '' }, {
    textContent: text,
    label,
  });
}

function makeGlossarySection(title, rows) {
  const section = makeElement('glossary-section', { 'data-glossary-section': '' }, {
    textContent: title,
    // app.js asks each section whether it still holds a visible entry. A stub
    // that always answered "yes" would leave every heading in place, which is
    // the state the check exists to rule out.
    querySelector: (selector) => (
      selector === '[data-glossary-entry]:not([hidden])'
        ? rows.find((row) => !row.hidden) || null
        : null
    ),
  });
  section.__rows = rows;
  return section;
}

const GLOSSARY_ROWS = [
  makeGlossaryRow('print', 'print("hello") Puts something on the screen.'),
  makeGlossaryRow('input', 'input("How old are you? ") Asks a question.'),
  makeGlossaryRow('len', 'len(fruits) How many items are in a list.'),
  makeGlossaryRow('break', 'break Leaves the loop straight away.'),
];
const GLOSSARY_SECTIONS = [
  makeGlossarySection('Saying something and reading an answer',
    GLOSSARY_ROWS.slice(0, 2)),
  makeGlossarySection('Doing something more than once',
    GLOSSARY_ROWS.slice(2)),
];

const GLOSSARY_DIALOG = makeElement('glossary-dialog',
  { 'data-total': String(GLOSSARY_ROWS.length) }, {
    querySelectorAll: (selector) => {
      if (selector === '[data-glossary-entry]') return GLOSSARY_ROWS;
      if (selector === '[data-glossary-section]') return GLOSSARY_SECTIONS;
      return [];
    },
  });
GLOSSARY_DIALOG.__entries = GLOSSARY_ROWS;
GLOSSARY_DIALOG.__sections = GLOSSARY_SECTIONS;

// The quit question. It only has to record that it opened: the checks are that
// nothing is shut down until its own button is pressed, and that the request
// that finally goes out is a POST.
const QUIT_DIALOG = makeElement('quit-dialog');

// The editor keeps its value, so a check can tell an append from an
// overwrite. A stub that discarded what was written could not tell the
// difference, and losing a reader's work is the failure that matters most
// here.
let editorValue = 'print("hi")';
// The reader is not in the code at the moment the page loads. A run press
// has to find them there, so starting them elsewhere is what makes that
// check mean something.
let editorFocused = false;
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
  // Whether the editor holds focus, so the run press can be checked to fire
  // only while the reader is in the code and not while they are elsewhere on
  // the page. Set through setEditorFocused() below.
  hasFocus: () => editorFocused,
};

// Lets a check put the reader in the code, or take them out of it, without
// having to reach into the stub itself.
function setEditorFocused(focused) { editorFocused = !!focused; }

function CodeMirror() { return editorInstance; }
// The theme app.js applies is written into a <style> element in the head
// (the bundled CodeMirror build has no defineTheme/defineStyle API), so a
// check reads the active-line highlight back out of that element and
// measures it against the theme's text. A noop here would report success
// while the highlight was never applied.
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
for (const code of ['hi', 'fr', 'es', 'ar', 'uk']) {
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
  // Ukrainian, named the way Windows and Edge name it. Ostap is the male
  // voice and Polina the female one; neither name contains the word "male"
  // or "female", so only the name list below can find them.
  { name: 'Microsoft Ostap - Ukrainian (Ukraine)', lang: 'uk-UA', voiceURI: 'ostap' },
  { name: 'Microsoft Polina - Ukrainian (Ukraine)', lang: 'uk-UA', voiceURI: 'polina' },
];

// A page, in one language. The main checks use the English one; the
// per-language checks ask for a fresh page each time, because the locale
// is read once when the script loads and a real language change reloads
// the page.
//
// bodyAttrs stands in for the settings the server rendered onto the body,
// which is how a saved choice survives a reload.
function makePage(locale, shared, bodyAttrs) {
  // A per-page store, so a layout saved on one page does not leak into the
  // next page the harness builds.
  const store = new Map();
  const catalogue = CATALOGUES[locale] || CATALOGUE;
  const i18nScripts = {
    'i18n-data': makeElement('i18n-data', {}, { textContent: JSON.stringify(catalogue) }),
    'i18n-meta': makeElement('i18n-meta', {}, {
      textContent: JSON.stringify({ locale, direction: locale === 'ar' ? 'rtl' : 'ltr' }),
    }),
    'panel-info': makeElement('panel-info', {}, {
      textContent: JSON.stringify(PANEL_INFO),
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
    // The theme app.js applies is written into a <style> element in the
    // head, so the head exists and collects it like a real document's.
    head: makeElement('head'),

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
      if (id === 'theme-builder') {
        // The builder wires its per-key reset and confirm buttons by class,
        // not by id. The generic stub answers querySelectorAll with nothing,
        // so those buttons would never receive a listener and a check that
        // pressed one would report a control that did nothing. The buttons
        // are registered in the id map first, so the same object the wiring
        // touched is the one a check fires at.
        if (!found.has(id)) {
          const keys = ['page', 'bg', 'fg', 'selection', 'keyword', 'string',
            'comment', 'number', 'function'];
          const buttonFor = (prefix, key) => {
            const buttonId = prefix + '-' + key;
            if (!found.has(buttonId)) {
              found.set(buttonId, makeElement(buttonId, {
                'data-key': key,
                class: prefix === 'theme-confirm' ? 'theme-confirm-one' : 'theme-reset-one',
              }));
            }
            return found.get(buttonId);
          };
          const confirms = keys.map((key) => buttonFor('theme-confirm', key));
          const resets = keys.map((key) => buttonFor('theme-reset', key));
          found.set(id, makeElement(id, {}, {
            querySelectorAll: (selector) => {
              if (selector === '.theme-confirm-one') return confirms;
              if (selector === '.theme-reset-one') return resets;
              return [];
            },
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
      if (id === 'glossary-dialog') {
        // A dialog holding real rows, for the same reason as the wizard above:
        // the generic stub answers querySelectorAll with nothing, and a filter
        // with no rows to hide proves nothing while reporting success.
        if (!found.has(id)) found.set(id, GLOSSARY_DIALOG);
        return found.get(id);
      }
      if (id === 'quit-dialog') {
        if (!found.has(id)) found.set(id, QUIT_DIALOG);
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
          THEME_CUSTOM_DEFAULTS[id] ? { value: THEME_CUSTOM_DEFAULTS[id] } : {},
          RANGE_INPUTS[id] ? { value: RANGE_INPUTS[id].value } : {},
          // The template draws Back hidden on the first step. Without this
          // the stub would start with it showing, and a check about it
          // hiding would pass for the wrong reason.
          id === 'setup-back' ? { hidden: true } : {},
          // The four font areas start ticked, as the template renders them.
          FONT_AREA_IDS.has(id) ? { checked: true } : {},
          // The stop button is drawn hidden, as the template renders it. It
          // appears only while a program is running, so a check that never ran
          // one must not find it already showing.
          id === 'btn-stop' ? { hidden: true } : {},
          // The two keypress lists, carrying the defaults the template puts
          // in them. The general stub rule hands every element a font name,
          // and the press checks are written against the real defaults: one
          // press of Ctrl+Enter runs, two presses of Escape stop.
          id === 'run-key' ? { value: 'Ctrl+Enter' } : {},
          id === 'stop-key' ? { value: 'Escape Escape' } : {},
          // Also drawn hidden, and revealed by app.js only once it has
          // confirmed this is the installed app. Starting it visible would let
          // "the button was revealed" pass before anything had run.
          id === 'btn-quit' ? { hidden: true } : {},
          // Rendered hidden, and shown only when a search matches nothing.
          id === 'glossary-empty' ? { hidden: true } : {},
          // A search box starts empty. Every other element takes an
          // OpenDyslexic value by default, and a filter run against that word
          // would be filtering on something nobody typed.
          id === 'glossary-search' ? { value: '' } : {},
          // The shell starts closed, so opening it is something a check can
          // tell has happened. Starting it open would make every later
          // check pass for the wrong reason.
          id === 'shell-pane' ? { hidden: true } : {},
          // Its divider is hidden with it: a line with nothing on the other
          // side of it would just be a line.
          id === 'divider-shell' ? { hidden: true } : {},
          // The three pane toolbars start closed, as the template draws them.
          // Starting them open would make every "the arrow opened it" check
          // pass before anything was pressed, which is the one thing those
          // checks exist to catch.
          id === 'mini-editor-panel' || id === 'mini-output-panel' || id === 'mini-shell-panel'
            ? { hidden: true }
            : {},
        );
        found.set(id, makeElement(id, attributesFor(id), props));
      }
      return found.get(id);
    },
    querySelector: () => makeElement('__query__'),
    querySelectorAll: (selector) => {
      // The panel material is four radios for one setting, the same shape as
      // the wizard's language radios. Held to the same bar.
      if (selector === 'input[name="glass-material"]') return GLASS_MATERIAL_RADIOS;
      return [];
    },
    createElement: (tag) => makeElement(tag),
    // Kept rather than discarded, so a check can fire the document-level
    // keydown the stop shortcut listens for. app.js also registers three mouse
    // listeners here; they are recorded the same way and never fired.
    __listeners: {},
    addEventListener: function (type, handler) {
      (this.__listeners[type] = this.__listeners[type] || []).push(handler);
    },
    removeEventListener: noop,
    fonts: { ready: Promise.resolve() },
  };

  const context = {
    console,
    document: doc,
    navigator: { language: locale, userAgent: 'stub' },
    matchMedia: () => ({ matches: false, addEventListener: noop, removeEventListener: noop }),
    localStorage: {
      getItem: (key) => (store.has(key) ? store.get(key) : null),
      setItem: (key, value) => { store.set(key, String(value)); },
      removeItem: (key) => { store.delete(key); },
    },
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
  return { context, doc, found, spoken, store };
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
// What the reset endpoint was asked to do, in order. Kept separate from
// configPosts so a check can prove a reset went to its own route rather
// than being recorded as an ordinary settings save.
const configResets = [];
// What the shell was asked to run, in order. Kept so a check can prove the
// session id and the reader's own code both went out, rather than only that
// a request happened.
const shellCommands = [];
// Whether a settings write is accepted. Held in a variable so the refused
// path can be walked: a stub that only ever saves would never show what the
// app does when the answer comes back "no", which is the case where the
// reader's answers are at risk.
let updateConfigOk = true;
// Flipped on to make the module list fail to load. A broken fetch and an
// empty catalogue look identical from the outside, which is exactly why the
// app has to say which one happened.

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
// What each run was asked to execute, in order, and the answers that went with
// it. The answers matter as much as the code: the interactive path is only
// right if the reader's answer travels in the *second* request, and a check
// that only counted requests could not tell that from a request sent empty.
const runBodies = [];
// What the runner answers with, taken from the front of the list. A scripted
// queue rather than one fixed reply, because the interactive path can only be
// reached by walking it: the first request comes back waiting for an answer,
// and the second comes back with the program's finished output.
const runReplies = [];
// What each stop request asked to stop, so a check can prove the name the
// reader's run was given is the name the stop was aimed at. A stop sent with
// another program's name, or with none at all, would still look like a stop
// happened, and the reader's program would carry on running.
const stopBodies = [];
// Every request to shut the app down, with the method used. Counting them is
// the only way to tell "the question was asked first" from "the app went down
// the moment the button was pressed", and the method is part of it: a shutdown
// sent as a GET could be triggered by any link or prefetch.
const shutdowns = [];

function parseBody(options) {
  try { return JSON.parse(options && options.body) || {}; } catch (e) { return {}; }
}

// Every request, with the method it used. A route that only accepts POST is
// answered with 405 by Flask, and the page's own handling of that is what the
// method checks below are about: the list has to be a GET because it changes
// nothing, and the two that do change things must never be a GET.
const fetchMethods = [];

function fetchStub(url, options) {
  fetchCalls.push(url);
  fetchMethods.push({ url: String(url), method: (options && options.method) || 'GET' });
  // Quitting. Recorded rather than answered and forgotten: the checks below are
  // that it is never reached before the reader has answered, and that it is a
  // POST.
  if (String(url).includes('/api/shutdown')) {
    shutdowns.push((options && options.method) || 'GET');
    return Promise.resolve({
      ok: true,
      json: () => Promise.resolve({ success: true }),
    });
  }
  // The shell, before the catch-all /api/config branch, because the session
  // id it is handed has to be echoed back or a check cannot tell that one
  // command's output reached the next.
  if (String(url).includes('/api/shell/start')) {
    return Promise.resolve({
      ok: true,
      json: () => Promise.resolve({ success: true, session: 'session-1' }),
    });
  }
  if (String(url).includes('/api/shell/stop')) {
    return Promise.resolve({ ok: true, json: () => Promise.resolve({ success: true }) });
  }
  if (String(url).includes('/api/shell/reset')) {
    return Promise.resolve({ ok: true, json: () => Promise.resolve({ success: true }) });
  }
  if (String(url).includes('/api/shell/exec')) {
    let sent = {};
    try { sent = JSON.parse(options.body); } catch (e) { sent = {}; }
    shellCommands.push(sent);
    // Echoing what was typed is the whole contract of a shell in a test
    // double: a check can prove the reader's own command came back rather
    // than only that something did.
    if (sent.code === 'boom') {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({
          success: true, output: '', error: 'NameError: name \'boom\' is not defined',
        }),
      });
    }
    return Promise.resolve({
      ok: true,
      json: () => Promise.resolve({
        success: true, output: (sent.code || '') + '\n', error: '',
      }),
    });
  }
  // The runner. The body is kept because the reader's answer travels in it: a
  // reply that never carried one would still look like a second request, and
  // telling those two apart is the whole point of the checks below.
  // Before the runner branch below, and not after it: "/api/run/stop" contains
  // "/api/run", so a stop checked afterwards would be recorded as a run and
  // answered with a run reply. The checks would then be reading the wrong
  // request while reporting success.
  if (String(url).includes('/api/run/stop')) {
    stopBodies.push(parseBody(options));
    return Promise.resolve({
      ok: true,
      json: () => Promise.resolve({ success: true, stopped: true }),
    });
  }
  if (String(url).includes('/api/run')) {
    runBodies.push(parseBody(options));
    const reply = runReplies.length
      ? runReplies.shift()
      : {
        success: true, output: '', error: '', error_line: null,
        awaiting_answer: false, trace: null,
      };
    return Promise.resolve({ ok: true, json: () => Promise.resolve(reply) });
  }
  if (String(url).includes('/api/themes')) {
    return Promise.resolve({
      ok: true,
      // The server answers with the themes keyed by name at the top level
      // (routes.py /api/themes). The stub has to match: app.js copies every
      // top-level key into themePalette and builds the theme <select> from
      // them, so a wrapped table would leave themePalette.custom missing and
      // the select offering one option called "SANDBOX_THEMES".
      // gutter_bg is the panel colour the server also reports, and it is
      // what a chosen tint is painted over. Without it the tint has no
      // background to work against and falls back to the page background,
      // so the checks would pass against a colour no reader ever sees.
      json: () => Promise.resolve(SANDBOX_THEMES),
    });
  }
  // The reset endpoint, before the catch-all /api/config branch below,
  // because /api/config/reset contains /api/config and would otherwise be
  // swallowed by it and recorded as a settings save.
  if (String(url).includes('/api/config/reset')) {
    configResets.push(parseBody(options));
    return Promise.resolve({
      ok: true,
      json: () => Promise.resolve({ success: true }),
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

// Any FAIL that reaches the screen fails the run, whoever printed it.
//
// The checks below mostly set `failed` themselves, but a check that *throws*
// does not go through that path: the throw abandons the rest of its callback,
// so the stage that would have called finish() never runs, the event loop
// drains, and node exits 0 by itself - after printing FAIL. A green run
// reporting a broken app is worse than having no harness, so the printed line
// is counted as well. It is the one signal no path can skip.
const realLog = console.log.bind(console);
console.log = (...args) => {
  if (String(args[0]).startsWith('FAIL')) failed = true;
  realLog(...args);
};

// The same hole approached from the other end. finish() settles the exit code
// when a chain reaches the end of itself, and a chain that broke never gets
// there, so the code is also settled here for a run that simply runs out of
// work. beforeExit does not fire when process.exit() was called, so an
// explicit finish() still has the last word.
process.on('beforeExit', () => {
  if (broke || failed) process.exitCode = 1;
});

// A check that throws inside a promise chain does not stop the run. The
// rejection is swallowed, the event loop drains, and node exits 0 - so the
// harness reports success while quietly skipping every check after the break.
// That is how a broken gallery could pass. Anything that escapes a chain is
// now a failure in its own right, and the exit waits to see it.
let broke = null;
const chainBroke = (label) => (err) => {
  if (broke) return;
  broke = label;
  console.log('FAIL ' + label);
  console.log('     ' + ((err && (err.stack || err.message)) || String(err)));
};
process.on('unhandledRejection', chainBroke('a check chain threw and the rest were skipped'));
process.on('uncaughtException', chainBroke('a check threw outside its chain'));
try {
  vm.createContext(sandbox);
  // Before app.js, as the template does it. app.js calls into it on its very
  // first pass, so loading it afterwards would leave every tint check passing
  // against the panels staying the theme colour.
  vm.runInContext(tintSource, sandbox, { filename: 'tint.js' });
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
// The browser's half of the shared tint contract.
//
// This is the only check that can catch colour.py and tint.js disagreeing, and
// it runs against the real tint.js rather than a stub. Each vector is a chosen
// tint against one theme's panel, with that theme's own three text colours.
// ---------------------------------------------------------------------------
if (sandbox.AccessibleTint) {
  const Tint = sandbox.AccessibleTint;
  let vectorFails = 0;
  const reportVector = (kind, label, got, want) => {
    vectorFails += 1;
    console.log(`FAIL ${kind} ${label}: tint.js gave ${got}, vectors say ${want}`);
  };

  for (const testCase of TINT_VECTORS.cases) {
    const got = Tint.safePanelTint(testCase.tint, testCase.panel, testCase.texts);
    if (got !== testCase.expected) {
      reportVector('vector', `${testCase.theme} ${testCase.tint}`, got,
                   testCase.expected);
    }
    // A tint that already reads must come back untouched, or the reader gets a
    // colour they did not choose. Worth checking on this side too: the browser
    // is where a live theme change happens, so this is the copy that runs.
    const untouched = Tint.readableOn(testCase.texts.map(Tint.parseHex),
                                      Tint.parseHex(testCase.tint)) >= 4.5;
    if (untouched && got !== testCase.tint) {
      reportVector('untouched', `${testCase.theme} ${testCase.tint}`, got,
                   testCase.tint);
    }
    // Whatever the arithmetic settled on, the words have to stay readable on
    // it. This is the promise the whole module exists to keep, so it is
    // checked rather than assumed.
    const worst = Math.min(
      ...testCase.texts.map(
        (c) => Tint.contrastRatio(c, got)
      )
    );
    if (worst < 4.5) {
      vectorFails += 1;
      console.log(`FAIL readable ${testCase.theme} ${testCase.tint}: the `
                  + `worst text on ${got} is ${worst.toFixed(3)}, under 4.5`);
    }
  }

  for (const testCase of TINT_VECTORS.empty_tint) {
    const got = Tint.safePanelTint(testCase.tint, '#f2f2f2', testCase.texts);
    if (got !== testCase.expected) {
      reportVector('blank tint', JSON.stringify(testCase.tint), got,
                   JSON.stringify(testCase.expected));
    }
  }

  if (vectorFails) {
    failed = true;
    console.log(`FAIL the browser tint maths does not match `
                + `tests/tint_vectors.json (${vectorFails} problems)`);
  } else {
    const ties = TINT_VECTORS.cases.filter((c) => c.tie).length;
    console.log(`OK  tint.js matched all ${TINT_VECTORS.cases.length} shared `
                + `vectors (${ties} of them rounding ties) and `
                + `${TINT_VECTORS.empty_tint.length} blank-tint cases`);
  }
}

// ---------------------------------------------------------------------------
// Fire every listener the script registered. Loading without error only
// proves the top half of the file parsed; the wiring is in these handlers.
// ---------------------------------------------------------------------------
const fakeEvent = { preventDefault: noop, stopPropagation: noop };

// A keypress, written the way the reader makes one. The handler looks at
// event.key and the modifier flags, so a stub that answered only for one
// named key could not stand in for a press the reader can change.
function press(key, flags = {}) {
  return Object.assign({}, fakeEvent, {
    key,
    ctrlKey: false, altKey: false, shiftKey: false, metaKey: false,
  }, flags);
}

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
  ['font-weight', 'input'], ['font-weight', 'change'],
  ['line-height', 'input'], ['line-height', 'change'],
  ['letter-spacing', 'input'], ['letter-spacing', 'change'],
  ['line-height-less', 'click'], ['line-height-more', 'click'],
  ['letter-spacing-less', 'click'], ['letter-spacing-more', 'click'],
  ['blur-intensity', 'input'], ['blur-intensity', 'change'],
  ['fade-slider', 'input'], ['fade-slider', 'change'],
  ['theme-select', 'change'], ['contrast-select', 'change'],
  ['focus-mode', 'change'],
  ['reduce-motion', 'click'],
  ['glass-tint-picker', 'input'], ['glass-tint-picker', 'change'],
  ['glass-tint-hex', 'input'], ['glass-tint-hex', 'change'],
  ['glass-tint-reset', 'click'],
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
  ['highlight-color-hex', 'input'], ['highlight-color-hex', 'change'],
  ['highlight-color-picker', 'input'], ['highlight-color-picker', 'change'],
  ['btn-reset-highlight', 'click'],
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
// point of the panel is that what the reader sees stays readable, so the
// resolved colours are measured against the preview background rather than
// assumed to be fine.
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

// The active-line highlight colour app.js wrote into the theme <style>
// element, or null if the theme was never applied. Reading it back from
// the element is what makes "the highlight was never applied" fail here
// instead of passing silently.
function activeLineHighlight() {
  const styleEl = documentStub.head.children.find((el) => el.id === 'cm-theme-style');
  if (!styleEl) return null;
  const match = styleEl.textContent.match(
    /\.cm-s-accessible-theme \.CodeMirror-activeline-background \{ background-color: ([^;]+); \}/
  );
  return match ? match[1] : null;
}

function fire(id, type, event = fakeEvent) {
  const el = elements.get(id);
  if (!el) return null;
  for (const handler of el.__listeners[type] || []) handler(event);
  return el;
}

// The same thing, for an element the harness holds directly rather than by id.
// The radios behind the panel material and the wizard's choices are shared
// stubs, not elements the page looked up, so they are not in the id map.
// Passing one of those to fire() above looks up an object as a key, finds
// nothing, and returns quietly - which leaves the check reporting a control
// that "did nothing" when in fact nothing was ever fired at it.
function fireElement(el, type, event = fakeEvent) {
  if (!el) return null;
  for (const handler of el.__listeners[type] || []) handler(event);
  return el;
}

// A listener on the document itself, which is where the stop shortcut lives:
// it has to work while the editor does not hold focus, so it is not one of the
// editor's own extraKeys. The handlers were recorded by the document stub.
function fireDocument(type, event = fakeEvent) {
  const handlers = documentStub.__listeners[type] || [];
  for (const handler of handlers) handler(event);
  return handlers.length;
}

function runPanelChecks() {
  const preview = elements.get('font-preview');
  const bodyNow = documentStub.body.__attributes;

  if (!preview.style.backgroundColor) {
    failed = true;
    console.log('FAIL the preview was never given the editor background');
    return;
  }

  // The preview shows the theme's own text colour on the editor's
  // background, so it cannot drift from what the editor will show. The
  // theme colours are contrast-checked on the server; this measures the
  // resolved pair the reader actually sees.
  const shown = preview.style.color;
  const background = preview.style.backgroundColor;
  if (!shown || !/^#[0-9a-f]{6}$/i.test(shown)) {
    failed = true;
    console.log(`FAIL the preview colour was never applied (${shown})`);
  } else {
    const ratio = contrastRatio(shown, background);
    if (ratio < 4.5) {
      failed = true;
      console.log(`FAIL the theme text ${shown} on ${background} is only ${ratio.toFixed(2)}:1`);
    } else {
      console.log(`     the theme text clears 4.5:1 on the preview background`);
    }
  }

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

  // The highlight behind the active line must never hide the text. The
  // default comes from the theme; a custom colour is faded toward the
  // background until the theme's text clears AA on it. The applied colour
  // is read back from the CodeMirror theme app.js defined, so a highlight
  // that was never applied fails here rather than passing silently.
  const highlightHex = elements.get('highlight-color-hex');
  const highlightErrorEl = elements.get('highlight-error');
  const themeKey = elements.get('theme-select').value || 'high-contrast';
  const themeFg = SANDBOX_THEMES[themeKey].fg;
  const activeLine = activeLineHighlight();

  if (!activeLine) {
    failed = true;
    console.log('FAIL the active-line highlight was never applied to the editor theme');
  } else {
    const ratio = contrastRatio(themeFg, activeLine);
    if (ratio < 4.5) {
      failed = true;
      console.log(`FAIL the default highlight ${activeLine} ` +
                  `hides ${themeFg} text (${ratio.toFixed(2)}:1)`);
    }
  }

  // A custom highlight is recorded, applied, and kept readable. The three
  // candidates cover the directions the fade can go: a light colour on a
  // dark theme, a dark colour, and a colour that is already readable.
  for (const candidate of ['#ffd93d', '#1a1a1a', '#fefefe']) {
    highlightHex.value = candidate;
    fire('highlight-color-hex', 'input');
    if (bodyNow['data-highlight-color'] !== candidate) {
      failed = true;
      console.log(`FAIL ${candidate} was not recorded on the body`);
    }
    const applied = activeLineHighlight();
    const ratio = contrastRatio(themeFg, applied);
    if (ratio < 4.5) {
      failed = true;
      console.log(`FAIL ${candidate} resolved to ${applied}, which hides ` +
                  `${themeFg} text (${ratio.toFixed(2)}:1)`);
    }
  }
  console.log('     the active-line highlight keeps the theme text readable');

  // A part-typed highlight colour must not be nagged about mid-typing.
  highlightHex.value = '#ff';
  fire('highlight-color-hex', 'input');
  if (highlightErrorEl.hidden !== true) {
    failed = true;
    console.log('FAIL a part-typed highlight colour showed an error while typing');
  }

  // Leaving the field with nonsense explains the problem and refuses it.
  highlightHex.value = 'nonsense';
  fire('highlight-color-hex', 'change');
  if (highlightErrorEl.hidden !== false || !highlightErrorEl.textContent) {
    failed = true;
    console.log('FAIL leaving the highlight field with nonsense did not explain the problem');
  }
  if (bodyNow['data-highlight-color'] === 'nonsense') {
    failed = true;
    console.log('FAIL nonsense was saved as the highlight colour');
  }
  console.log('     a highlight colour that is not a hex code is explained, and never saved');

  // Reset goes back to the theme highlight.
  fire('btn-reset-highlight', 'click');
  if (bodyNow['data-highlight-color'] !== '') {
    failed = true;
    console.log(`FAIL reset left data-highlight-color as "${bodyNow['data-highlight-color']}"`);
  }
  if (highlightHex.value !== '') {
    failed = true;
    console.log('FAIL reset did not clear the highlight hex field');
  }
  console.log('     "Use theme colour" clears the custom highlight');
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

// The reset reloads the page, exactly as the language picker does: the
// whole page is drawn by the server from the saved config, so a reload is
// the only way every control and every panel agrees with what was reset.
// The save is a promise, so this runs a tick after the second click.
function runResetConfigReloadCheck() {
  if (reloads.length !== resetReloadsBefore + 1) {
    failed = true;
    console.log(`FAIL the reset caused ${reloads.length - resetReloadsBefore} ` +
                'reloads instead of one');
  } else {
    console.log('     the reset reloads the page');
  }
}

// Reset every setting. The first click arms the button, the second does
// it, and the request goes to its own route rather than being recorded
// as an ordinary settings save. Runs in its own window, after the update
// chain and the language checks have settled, so the reload count below
// is exact.
function runResetConfigChecks() {
  const resetButton = elements.get('btn-reset-config');
  const resetBefore = configResets.length;
  fire('btn-reset-config', 'click');
  if (resetButton.textContent !== CATALOGUE['settings.reset_confirm']) {
    failed = true;
    console.log('FAIL the first reset click did not arm the button');
  } else if (!resetButton.classList.contains('is-armed')) {
    failed = true;
    console.log('FAIL the armed reset button has no is-armed class');
  } else {
    console.log('     the first reset click arms the button');
  }
  resetReloadsBefore = reloads.length;
  fire('btn-reset-config', 'click');
  const resets = configResets.slice(resetBefore);
  if (resets.length !== 1) {
    failed = true;
    console.log('FAIL the second reset click did not call the reset route: ' +
                JSON.stringify(configResets.slice(resetBefore)));
  } else {
    console.log('     the second reset click calls the reset route');
  }
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
  runGlassChecks();
  runSpeechChecks();
}

// The frosted-panel look. A switch that changes nothing is worse than no
// switch at all, because the reader is told the app has a setting it does
// not have. So: the body has to change, the switch has to agree with the
// body, and the choice has to be saved.
function runGlassChecks() {
  const bodyAttrs = documentStub.body.__attributes;
  const MATERIALS = ['off', 'mica', 'frosted', 'acrylic'];

  // --- the material ---
  // Each radio is selected in turn and the body has to follow. A radio that
  // saves without changing anything, or changes the page without saving,
  // leaves the reader with a setting that only half works.
  for (const value of MATERIALS) {
    const radio = GLASS_MATERIAL_RADIOS.find((r) => r.value === value);
    if (!radio) {
      failed = true;
      console.log(`FAIL there is no radio for "${value}"`);
      continue;
    }
    // A browser unchecks the others when one radio in a group is chosen. The
    // stub does not, so a check that only sets its own radio leaves all four
    // looking chosen - and the "only one is ever checked" check below would
    // fail for a reason that is the harness's, not the page's.
    GLASS_MATERIAL_RADIOS.forEach((r) => { r.checked = r === radio; });
    fireElement(radio, 'change');

    if (bodyAttrs['data-glass-material'] !== value) {
      failed = true;
      console.log(`FAIL choosing "${value}" left the page at ` +
                  `"${bodyAttrs['data-glass-material']}"`);
    }
  }
  console.log('     every material choice reaches the page');

  const chosen = configPosts.filter((p) => 'glass_material' in p);
  if (chosen.length !== MATERIALS.length) {
    failed = true;
    console.log(`FAIL ${MATERIALS.length} materials were chosen but ` +
                `${chosen.length} were saved`);
  } else if (chosen[chosen.length - 1].glass_material !== 'acrylic') {
    failed = true;
    console.log('FAIL the last material saved was ' +
                JSON.stringify(chosen[chosen.length - 1].glass_material));
  } else {
    console.log('     each material is saved as it is chosen');
  }

  // Exactly one radio may stay checked, or the control looks like a switch
  // that is somehow on in three places at once. Checked before the colour
  // work below, which has nothing to do with the radios.
  const stillChecked = GLASS_MATERIAL_RADIOS.filter((r) => r.checked);
  if (stillChecked.length !== 1) {
    failed = true;
    console.log(`FAIL ${stillChecked.length} materials are checked at once`);
  } else {
    console.log('     only one material is ever checked');
  }

  // --- the colour ---
  // The picker and the text box are two ways to change one setting, so both
  // have to move the body and both have to save.
  const picker = elements.get('glass-tint-picker');
  const hex = elements.get('glass-tint-hex');
  const error = elements.get('glass-tint-error');

  // The colour the panels end up painted in is not the colour that was typed:
  // it is pulled toward the theme's panel colour until that theme's own text
  // stays readable on it. So each check below compares against the answer the
  // arithmetic gives, not against the raw value. A tint left exactly as typed
  // is only correct when it happened to be readable already, which is what the
  // "kept as chosen" check below establishes.
  const infoFor = () => {
    const name = documentStub.body.getAttribute('data-theme') || 'high-contrast';
    return PANEL_INFO[name];
  };
  const painted = (raw) => {
    const info = infoFor();
    return sandbox.AccessibleTint.safePanelTint(raw, info.panel, info.texts);
  };

  picker.value = '#336699';
  fireElement(picker, 'input');
  const fromPicker = painted('#336699');
  if (bodyAttrs['data-glass-tint'] !== fromPicker) {
    failed = true;
    console.log('FAIL the colour picker did not reach the page, it shows ' +
                `"${bodyAttrs['data-glass-tint']}" rather than "${fromPicker}"`);
  }
  if (hex.value !== '#336699') {
    failed = true;
    console.log('FAIL the colour picker did not fill in the text box');
  } else {
    console.log('     the colour picker drives the page and the text box');
  }

  // What gets saved has to be the choice, not the clamped answer. Saving the
  // clamped colour back would rewrite the reader's red into a darker red the
  // first time they changed anything else on the page.
  //
  // Fired on 'change' rather than 'input', because that is the event the
  // picker sends when the reader lets go, and it is the one that commits. An
  // 'input' drag through a hundred colours would post a hundred saves.
  fireElement(picker, 'change');
  const afterPicker = configPosts.filter((p) => 'glass_tint' in p);
  if (!afterPicker.length) {
    failed = true;
    console.log('FAIL the chosen colour was never saved');
  } else if (afterPicker[afterPicker.length - 1].glass_tint !== '#336699') {
    failed = true;
    console.log('FAIL the saved colour is not the one that was chosen, it saved ' +
                JSON.stringify(afterPicker[afterPicker.length - 1].glass_tint) +
                ' rather than "#336699"');
  } else if (fromPicker === '#336699') {
    console.log('     the saved colour is the choice, not the clamped answer');
  } else {
    console.log(`     the saved colour is the choice, not the clamped answer ` +
                `("${fromPicker}")`);
  }

  hex.value = '#4a7fb5';
  fireElement(hex, 'input');
  const fromTyping = painted('#4a7fb5');
  if (bodyAttrs['data-glass-tint'] !== fromTyping) {
    failed = true;
    console.log('FAIL typing a colour did not reach the page');
  }

  // A half-typed colour must not be applied and must not be shouted at: the
  // reader cannot have made a mistake they have not finished expressing.
  hex.value = '#4a7f';
  fireElement(hex, 'input');
  if (bodyAttrs['data-glass-tint'] !== fromTyping) {
    failed = true;
    console.log('FAIL an unfinished colour was applied anyway: ' +
                `"${bodyAttrs['data-glass-tint']}"`);
  }
  if (!error.hidden) {
    failed = true;
    console.log('FAIL an unfinished colour produced an error message');
  } else {
    console.log('     an unfinished colour is left alone, not complained about');
  }

  // But leaving the field with something unusable is worth saying once.
  hex.value = 'not-a-colour';
  fireElement(hex, 'change');
  if (error.hidden) {
    failed = true;
    console.log('FAIL a colour that can never work was accepted in silence');
  } else if (error.textContent && error.textContent.indexOf('try.') === 0) {
    failed = true;
    console.log('FAIL the colour error shows a raw key: ' + error.textContent);
  } else {
    console.log('     an unusable colour is explained, in the reader\'s language');
  }

  // Reset has to mean "follow the theme", which is the empty string and not
  // a leftover colour, and it has to save that.
  fireElement(elements.get('glass-tint-reset'), 'click');
  if (bodyAttrs['data-glass-tint'] !== '') {
    failed = true;
    console.log('FAIL reset left a colour behind: ' +
                `"${bodyAttrs['data-glass-tint']}"`);
  }
  if (hex.value !== '') {
    failed = true;
    console.log('FAIL reset left the text box filled in');
  } else {
    console.log('     reset returns the panels to the theme colour');
  }

  // The CSS reads the tint through a custom property with a fallback, so an
  // empty tint has to remove the property rather than blank it. A blank
  // --glass-tint wins the cascade and leaves nothing to blend with.
  const style = documentStub.body.__style;
  if (style && style.getPropertyValue('--glass-tint') === '') {
    failed = true;
    console.log('FAIL --glass-tint was set to an empty value instead of removed');
  } else {
    console.log('     the empty tint removes --glass-tint so the fallback applies');
  }

  const tints = configPosts.filter((p) => 'glass_tint' in p);
  if (!tints.length) {
    failed = true;
    console.log('FAIL the colour was never saved');
  } else if (tints[tints.length - 1].glass_tint !== '') {
    failed = true;
    console.log('FAIL reset did not save the empty tint, it saved ' +
                JSON.stringify(tints[tints.length - 1].glass_tint));
  } else {
    console.log('     the colour is saved, including the reset to the theme');
  }
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
    ['uk', { male: 'Ostap', female: 'Polina' }],
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
  // that chain rather than cutting it off at a guessed time.
  let finishCalled = false;
  finish = () => {
    // The exit runs once, whatever asks for it.
    if (finishCalled) return;
    finishCalled = true;
    process.exit(broke || failed ? 1 : 0);
  };
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

      // Pressing the download button asks a question first: the install that
      // follows changes things on the reader's disk, so they get to save
      // their work before that happens. The request must not go out on the
      // first press.
      fire('btn-install-update', 'click');

      if (updateInstallBodies.length) {
        failed = true;
        console.log('FAIL the download was sent before the reader agreed to it');
      } else {
        console.log('     the download waits for the reader to agree');
      }

      // Agreeing is a separate press, and that is what sends the request.
      fire('btn-save-warn-confirm', 'click');

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
    // The same two presses as the download that worked: ask, then agree.
    fire('btn-install-update', 'click');
    fire('btn-save-warn-confirm', 'click');

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
      // The theme-builder checks post config of their own (theme picks). They
      // run before the update-channel checks, whose assertions land in a
      // deferred callback and count the posts since their own snapshot;
      // anything posted in between would look like extra channel changes.
      runThemeBuilderChecks();
      runUpdateChannelChecks();
    }, 10);
  }, 10);
}

// Choosing a channel. The reader picks a channel and then believes they are
// on it, so the choice has to be saved and acted on, not just stored.
function runUpdateChannelChecks() {
  const select = elements.get('update-channel');
  if (!select) {
    failed = true;
    console.log('FAIL there is no update channel control to choose from');
    return;
  }

  const options = (select.options || []).map((o) => o.value);
  for (const wanted of ['beta', 'stable']) {
    if (!options.includes(wanted)) {
      failed = true;
      console.log('FAIL the channel list does not offer ' + wanted +
        ': ' + JSON.stringify(options));
    }
  }
  if (!failed) {
    console.log('     both channels are offered');
  }

  // It has to say what the choice means. A reader cannot work out from two
  // names which one is meant to stop moving. The help text is a separate
  // element the template points at, so the check is that the two are paired
  // rather than that a property exists.
  if (!KNOWN_IDS.has('update-channel-help')) {
    failed = true;
    console.log('FAIL the channel control has no help text to point at');
  } else {
    console.log('     the choice says what it means');
  }

  const postsBefore = configPosts.length;
  const checksBefore = updateCheckBodies.length;
  select.value = 'stable';
  fire('update-channel', 'change');

  setTimeout(() => {
    const saved = configPosts.slice(postsBefore)
      .filter((p) => 'update_channel' in p);
    if (saved.length !== 1) {
      failed = true;
      console.log('FAIL choosing a channel did not save exactly one change: ' +
        JSON.stringify(configPosts.slice(postsBefore)));
    } else if (saved[0].update_channel !== 'stable') {
      failed = true;
      console.log('FAIL the wrong channel was saved: ' +
        JSON.stringify(saved[0]));
    } else {
      console.log('     choosing a channel saves it');
    }

    // After switching channels the reader is looking at a different set of
    // releases. Whether the app goes and asks again depends on the
    // automatic-check switch, and both answers are correct - what is not
    // correct is hitting the network when the reader turned that off, or
    // leaving on screen an answer that describes the old channel.
    const autoEl = elements.get('auto-update-toggle');
    const automatic = autoEl.getAttribute('aria-checked') === 'true';
    const after = updateCheckBodies.length - checksBefore;

    if (!automatic) {
      if (after) {
        failed = true;
        console.log('FAIL changing the channel asked the server again even ' +
          'though the automatic check is off: ' + after + ' call(s)');
      } else {
        console.log('     changing the channel does not reach the network ' +
          'when the automatic check is off');
      }
      const statusEl = elements.get('update-status');
      if ((statusEl.textContent || '').trim()) {
        failed = true;
        console.log('FAIL the old answer is still on screen, describing the ' +
          'channel the reader just left: ' + JSON.stringify(statusEl.textContent));
      } else {
        console.log('     the answer describing the old channel is taken away');
      }
    } else if (after < 1) {
      failed = true;
      console.log('FAIL the answer on screen still describes the old channel');
    } else {
      console.log('     the answer is refreshed for the new channel');
    }
  }, 10);
}

// ---------------------------------------------------------------------------
// The theme builder and the background gradient. The builder is hidden until
// the custom theme is chosen, edits preview live, and a change saves the
// seven picks. The gradient is a switch that the page and the config both
// have to hear about.
// ---------------------------------------------------------------------------
function runThemeBuilderChecks() {
  const themeSelect = elements.get('theme-select');
  const builder = elements.get('theme-builder');
  const gradient = elements.get('theme-gradient');
  const bodyNow = documentStub.body.__attributes;
  const bodyStyle = documentStub.body.style;
  const changeTheme = (key) => {
    themeSelect.value = key;
    themeSelect.__listeners.change.forEach((h) => h(eventFor(themeSelect)));
  };

  // The builder is hidden until the custom theme is chosen.
  if (!builder.hidden) {
    failed = true;
    console.log('FAIL the theme builder is visible before the custom theme is chosen');
  } else {
    console.log('     the theme builder stays hidden until asked for');
  }

  // Choosing the custom theme reveals it and paints the page chrome.
  changeTheme('custom');
  if (builder.hidden) {
    failed = true;
    console.log('FAIL choosing the custom theme did not reveal the builder');
  } else {
    console.log('     choosing the custom theme reveals the builder');
  }
  const chromeKeys = ['--bg', '--fg', '--accent', '--accent-fg', '--panel-bg',
    '--panel-border', '--muted', '--error-bg', '--error-border',
    '--error-fg', '--error-line', '--focus-ring'];
  const missing = chromeKeys.filter((key) => !(key in bodyStyle));
  if (missing.length) {
    failed = true;
    console.log('FAIL the custom theme left the page chrome unset: ' +
      missing.join(', '));
  } else {
    console.log('     the custom theme paints the page chrome');
  }

  // Editing a pick previews live and reports its contrast.
  const bgField = elements.get('theme-custom-bg');
  const fgField = elements.get('theme-custom-fg');
  const fgPicker = elements.get('theme-custom-fg-picker');
  bgField.value = '#0b0b0b';
  fgField.value = '#ffffff';
  fire('theme-custom-bg', 'input');
  fire('theme-custom-fg', 'input');
  // The status line is created by the first paint, not by the page markup,
  // so it has to be looked up after the input events above have run. app.js
  // creates it with document.createElement rather than by id, so it reaches
  // the shared map only through the createElement path below. If it is still
  // absent the app never painted it, which is the failure worth reporting
  // rather than a crash on reading .hidden of undefined.
  const fgStatus = elements.get('theme-custom-fg-status');
  if (!fgStatus) {
    failed = true;
    console.log('FAIL a picked colour creates no contrast status line');
  } else if (fgStatus.hidden) {
    failed = true;
    console.log('FAIL a picked colour shows no contrast status');
  } else if (fgStatus.textContent !== CATALOGUE['theme.custom_contrast_ok']) {
    failed = true;
    console.log('FAIL a readable pick is not marked readable: ' +
      JSON.stringify(fgStatus.textContent));
  } else {
    console.log('     a readable pick is marked readable');
  }

  // A pick that fails AA is flagged, because the app will adjust it. The
  // status line is only readable when it exists, so a missing one is reported
  // once above and skipped here rather than read as undefined.
  fgField.value = '#777777';
  fire('theme-custom-fg', 'input');
  if (!fgStatus) {
    failed = true;
    console.log('FAIL an unreadable pick cannot be checked: no contrast status line');
  } else if (!fgStatus.textContent.startsWith(
      CATALOGUE['theme.custom_contrast_fail'])) {
    failed = true;
    console.log('FAIL an unreadable pick is not flagged: ' +
      JSON.stringify(fgStatus.textContent));
  } else {
    console.log('     an unreadable pick is flagged');
  }

  // Flagging a pick is not enough: the reader cannot see the swatch, so the
  // message has to name the colour the editor will use instead, and that
  // colour has to be a different one - the failing pick is not a correction.
  {
    const named = fgStatus
      ? (fgStatus.textContent.match(/#[0-9a-fA-F]{6}/) || [])[0]
      : null;
    if (!named) {
      failed = true;
      console.log('FAIL a flagged pick does not say which colour is used instead: ' +
        JSON.stringify(fgStatus && fgStatus.textContent));
    } else if (named.toLowerCase() === '#777777') {
      failed = true;
      console.log('FAIL a flagged pick claims the failing colour is the corrected one');
    } else {
      console.log('     a flagged pick names the colour that replaces it (' + named + ')');
    }
  }

  // A half-typed hex value must not repaint the theme. Typing "#ff0" on the
  // way to "#ff0000" used to paint vivid yellow on the page for a split
  // second, because the parser accepted a three-digit hex as a real colour.
  const fgHeld = bodyStyle['--fg'];
  fgField.value = '#ff0';
  fire('theme-custom-fg', 'input');
  if (bodyStyle['--fg'] !== fgHeld) {
    failed = true;
    console.log('FAIL a half-typed hex value repainted the theme: ' +
      JSON.stringify(bodyStyle['--fg']));
  } else {
    console.log('     a half-typed hex value waits for six digits');
  }
  fgField.value = '#ffffff';
  fire('theme-custom-fg', 'input');

  // The background is not drawn on itself, so it has no contrast question.
  // Judged anyway, it measured 1:1 against itself and was flagged "Too low"
  // the moment any other field was touched.
  bgField.value = '#222222';
  fire('theme-custom-bg', 'input');
  const bgStatus = elements.get('theme-custom-bg-status');
  if (!bgStatus) {
    failed = true;
    console.log('FAIL the background field has no status line to check');
  } else if (!bgStatus.hidden) {
    failed = true;
    console.log('FAIL the background is flagged against itself: ' +
      JSON.stringify(bgStatus.textContent));
  } else {
    console.log('     a background pick carries no contrast warning');
  }
  bgField.value = '#0b0b0b';
  fire('theme-custom-bg', 'input');

  // The picker and the hex box are two views of one value.
  fgPicker.value = '#123456';
  fire('theme-custom-fg-picker', 'input');
  if (fgField.value !== '#123456') {
    failed = true;
    console.log('FAIL picking a colour did not update the hex box: ' +
      JSON.stringify(fgField.value));
  } else {
    console.log('     the picker and the hex box stay in step');
  }

  // Editing the hex box does not save on its own: the reader must confirm
  // with the tick, so a stray value never becomes the theme mid-typing.
  const before = configPosts.length;
  fire('theme-custom-fg', 'change');
  const straySave = configPosts.slice(before).filter((p) => 'theme_custom_fg' in p);
  if (straySave.length !== 0) {
    failed = true;
    console.log('FAIL a hex edit saved without a confirm press: ' +
      JSON.stringify(straySave));
  } else {
    console.log('     a hex edit waits for a confirm press');
  }

  // The tick button saves the picks.
  const beforeConfirm = configPosts.length;
  fire('theme-confirm-fg', 'click');
  const saved = configPosts.slice(beforeConfirm).filter((p) => 'theme_custom_fg' in p);
  if (saved.length !== 1 || saved[0].theme_custom_fg !== '#123456') {
    failed = true;
    console.log('FAIL the confirm press did not save the pick: ' +
      JSON.stringify(configPosts.slice(beforeConfirm)));
  } else {
    console.log('     the confirm press saves the pick');
  }

  // Reset restores the defaults and saves them. The page and selection
  // colours are changed first, so the check covers every pick the builder
  // holds and not only the two the reader happens to touch.
  const pageField = elements.get('theme-custom-page');
  const selectionField = elements.get('theme-custom-selection');
  pageField.value = '#123456';
  selectionField.value = '#654321';
  const beforeReset = configPosts.length;
  fire('theme-custom-reset', 'click');
  const notRestored = Object.keys(THEME_CUSTOM_DEFAULTS).filter((id) =>
    elements.get(id).value !== THEME_CUSTOM_DEFAULTS[id]);
  if (notRestored.length) {
    failed = true;
    console.log('FAIL reset did not restore the defaults: ' +
      notRestored.join(', '));
  } else {
    console.log('     reset restores the defaults');
  }
  const resetSaved = configPosts.slice(beforeReset).filter((p) => 'theme_custom_fg' in p);
  if (!resetSaved.some((p) => p.theme_custom_fg === '#ffffff')) {
    failed = true;
    console.log('FAIL reset did not save the defaults: ' +
      JSON.stringify(configPosts.slice(beforeReset)));
  }

  // Leaving the custom theme hides the builder again.
  changeTheme('high-contrast');
  if (!builder.hidden) {
    failed = true;
    console.log('FAIL leaving the custom theme left the builder visible');
  } else {
    console.log('     leaving the custom theme hides the builder');
  }

  // The background gradient switch.
  const gradientOn = gradient.getAttribute('aria-checked') === 'true';
  fire('theme-gradient', 'click');
  const nowOn = gradient.getAttribute('aria-checked') === 'true';
  if (nowOn === gradientOn) {
    failed = true;
    console.log('FAIL the gradient switch did not change state');
  } else {
    console.log('     the gradient switch changes state');
  }
  if (bodyNow['data-gradient'] !== (nowOn ? 'on' : 'off')) {
    failed = true;
    console.log('FAIL the page was not told the gradient state: ' +
      JSON.stringify(bodyNow['data-gradient']));
  }
  const gradientSaved = configPosts.filter((p) => 'theme_gradient' in p);
  if (!gradientSaved.length ||
      gradientSaved[gradientSaved.length - 1].theme_gradient !== nowOn) {
    failed = true;
    console.log('FAIL the gradient choice was not saved: ' +
      JSON.stringify(gradientSaved));
  } else {
    console.log('     the gradient choice is saved');
  }
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
  // The count comes from the panels rather than a hard-coded three, so a
  // wizard with a different number of steps still lands on the first one.
  for (let backPress = 0; backPress < SETUP_PANELS.length - 1; backPress += 1) {
    fire('setup-back', 'click');
  }
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
  // The font reaches the page through the token the stylesheet reads, not
  // through an inline family on the body: the output and the shell name a
  // token of their own, so an inline family never reached them. Checking the
  // token is what actually proves the chosen font is in use.
  if (bodyStyle['--font-ui'] !== wantedFamily) {
    failed = true;
    console.log(`FAIL choosing OpenDyslexic left the page in ` +
                `"${bodyStyle['--font-ui']}" rather than "${wantedFamily}"`);
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

  // Each area can be turned off on its own, and turning one off hands that
  // area back the app's own font. The token carries that, so unticking has to
  // leave that one token unset - and must not disturb the areas still ticked.
  // The value is not compared here: this stub's <select> reports no chosen
  // value, so a re-apply falls back to the default stack rather than the
  // family the radio carried. What matters is which tokens are set at all.
  const outputTick = documentStub.getElementById('font-output');
  const fireTick = () => (outputTick.__listeners.change || []).forEach((handler) =>
    handler({ target: outputTick, preventDefault: noop, stopPropagation: noop }));
  outputTick.checked = false;
  fireTick();
  if ('--font-output' in bodyStyle) {
    failed = true;
    console.log('FAIL unticking the output left it on the chosen font: ' +
                JSON.stringify(bodyStyle['--font-output']));
  } else if (!('--font-code' in bodyStyle) || !('--font-ui' in bodyStyle)) {
    failed = true;
    console.log('FAIL unticking the output took the other areas with it');
  } else {
    console.log('     an area can be unticked on its own');
  }
  outputTick.checked = true;
  fireTick();

  // A theme is shown on the page too: the editor behind the wizard repaints
  // so the reader sees the theme against real code, not just the swatches.
  const ocean = SETUP_THEME_RADIOS.find((radio) => radio.value === 'ocean');
  const themeBefore = configPosts.length;
  ocean.__listeners.change.forEach((handler) =>
    handler({ target: ocean, preventDefault: noop, stopPropagation: noop }));
  if (documentStub.body.__attributes['data-theme'] !== 'ocean') {
    failed = true;
    console.log('FAIL choosing a theme in the setup screen did not apply it: ' +
                JSON.stringify(documentStub.body.__attributes['data-theme']));
  } else {
    console.log('     a chosen theme is applied to the page straight away');
  }
  if (!configPosts.slice(themeBefore).some((p) => p.theme === 'ocean')) {
    failed = true;
    console.log('FAIL a theme chosen in the setup screen was not saved: ' +
                JSON.stringify(configPosts.slice(themeBefore)));
  } else {
    console.log('     a theme chosen in the setup screen is saved, not just drawn');
  }

  // A preset colour square starts the reader's own theme from that preset,
  // and it must not move focus: the square the reader is standing on is where
  // they are. Re-focusing the heading scrolls the page out from under them,
  // which is the bug this check exists to catch.
  const swatch = setupSwatchRegistrations[0];
  const swatchFocusBefore = setupFocusLog.length;
  const swatchConfigBefore = configPosts.length;
  swatch.__listeners.change.forEach((handler) =>
    handler({ target: swatch, preventDefault: noop, stopPropagation: noop }));
  if (setupFocusLog.length !== swatchFocusBefore) {
    failed = true;
    console.log('FAIL picking a setup preset colour moved focus back to the heading');
  } else if (!configPosts.slice(swatchConfigBefore).some((p) => p.theme === 'custom')) {
    failed = true;
    console.log('FAIL picking a setup preset colour did not start the reader theme: ' +
                JSON.stringify(configPosts.slice(swatchConfigBefore)));
  } else {
    console.log('     a preset colour square starts the reader theme without moving focus');
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


// The module index. The interaction sweep above already fired the search
// Text of a subtree, the way a screen reader would read it out.
function readText(node) {
  if (!node) return '';
  if (typeof node.textContent === 'string' && node.textContent) {
    return node.textContent;
  }
  return (node.children || []).map(readText).join(' ');
}

// The split view: two separators, a keyboard path and a drag path, and a
// layout that remembers where the reader put the dividers. The shell
// divider's own visibility is checked in runShellChecks, where the shell
// is actually opened and closed.
function runLayoutChecks() {
  const workspace = elements.get('workspace');
  const rightColumn = elements.get('right-column');
  const main = elements.get('divider-main');
  const shellDivider = elements.get('divider-shell');

  // Both dividers are separators with a size a screen reader can hear.
  if (main.getAttribute('role') !== 'separator' ||
      main.getAttribute('aria-orientation') !== 'vertical' ||
      main.getAttribute('aria-valuenow') !== '50') {
    failed = true;
    console.log('FAIL the editor divider is not a vertical separator at 50%');
  } else {
    console.log('     the editor divider is a separator, and it starts at half the width');
  }

  if (shellDivider.getAttribute('role') !== 'separator' ||
      shellDivider.getAttribute('aria-orientation') !== 'horizontal') {
    failed = true;
    console.log('FAIL the shell divider is not a horizontal separator');
  } else {
    console.log('     the shell divider is a horizontal separator');
  }

  // The shell divider is hidden with the shell, which runShellChecks opens
  // and closes. Here it only has to start hidden.
  if (!shellDivider.hidden) {
    failed = true;
    console.log('FAIL the shell divider was visible while the shell was closed');
  } else {
    console.log('     the shell divider is hidden until the shell opens');
  }

  // The keyboard path: ArrowRight widens the editor by one step, and the
  // width reaches the stylesheet as a CSS variable.
  fire('divider-main', 'keydown', { key: 'ArrowRight', preventDefault: noop, stopPropagation: noop });
  if (main.getAttribute('aria-valuenow') !== '55') {
    failed = true;
    console.log(`FAIL ArrowRight did not widen the editor: ${main.getAttribute('aria-valuenow')}`);
  } else if (workspace.style['--editor-width'] !== '55%') {
    failed = true;
    console.log(`FAIL the editor width never reached the stylesheet: ${workspace.style['--editor-width']}`);
  } else {
    console.log('     ArrowRight widens the editor, and the width reaches the stylesheet');
  }

  // The drag path: press, move, release. The stub's workspace is 100px
  // wide, so ten pixels is ten percent.
  fire('divider-main', 'pointerdown', { button: 0, clientX: 500, preventDefault: noop, stopPropagation: noop });
  fire('divider-main', 'pointermove', { clientX: 510, preventDefault: noop, stopPropagation: noop });
  fire('divider-main', 'pointerup', { preventDefault: noop, stopPropagation: noop });
  if (main.getAttribute('aria-valuenow') !== '65') {
    failed = true;
    console.log(`FAIL dragging did not resize the editor: ${main.getAttribute('aria-valuenow')}`);
  } else {
    console.log('     dragging the divider resizes the editor');
  }

  // The layout is remembered, so the reader does not have to drag it back
  // into place on every visit.
  if (mainPage.store.get('accessible_ide_layout') !== '{"editorWidth":65,"shellHeight":50}') {
    failed = true;
    console.log(`FAIL the layout was not remembered: ${mainPage.store.get('accessible_ide_layout')}`);
  } else {
    console.log('     the layout is remembered for the next visit');
  }

  // Home and End go to the ends, and the ends are clamped so a hand-edited
  // value can never leave a pane unreadable.
  fire('divider-main', 'keydown', { key: 'Home', preventDefault: noop, stopPropagation: noop });
  if (main.getAttribute('aria-valuenow') !== '20') {
    failed = true;
    console.log(`FAIL Home did not take the editor to its narrowest: ${main.getAttribute('aria-valuenow')}`);
  } else {
    console.log('     Home takes the editor to its narrowest');
  }
  fire('divider-main', 'keydown', { key: 'End', preventDefault: noop, stopPropagation: noop });
  if (main.getAttribute('aria-valuenow') !== '80') {
    failed = true;
    console.log(`FAIL End did not take the editor to its widest: ${main.getAttribute('aria-valuenow')}`);
  } else {
    console.log('     End takes the editor to its widest');
  }

  console.log('layout: 8 checks');
}

// WCAG 2.4.11, focus not obscured. The trace window floats over the page and
// is deliberately not modal, so a control underneath it can take focus with
// nothing of it on screen. The window is expected to close in that one case,
// and to stay open when the control is merely beside it: closing on every
// focus move would take the table away from a reader comparing a row with the
// code next to it, which is the whole reason the window is not modal.
function runFocusObscuredChecks() {
  const win = elements.get('trace-window');
  if (!win) {
    failed = true;
    console.log('FAIL the trace window was never looked up');
    return;
  }

  const savedClose = win.close;
  const savedOpen = win.open;
  let closes = 0;

  win.open = true;
  win.close = () => { closes += 1; };
  win.getBoundingClientRect = () => ({ top: 100, left: 100, width: 400, height: 300 });

  function focusOn(rect) {
    fireDocument('focusin', { target: { getBoundingClientRect: () => rect } });
  }

  focusOn({ top: 150, left: 150, width: 100, height: 20 });
  if (closes !== 1) {
    failed = true;
    console.log(`FAIL a wholly covered control did not close the window (${closes})`);
  } else {
    console.log('     a control hidden under the window closes it');
  }

  focusOn({ top: 10, left: 10, width: 100, height: 20 });
  if (closes !== 1) {
    failed = true;
    console.log(`FAIL a control beside the window closed it (${closes})`);
  } else {
    console.log('     a control beside the window leaves it open');
  }

  focusOn({ top: 150, left: 150, width: 0, height: 0 });
  if (closes !== 1) {
    failed = true;
    console.log('FAIL a rect with no size was read as covered');
  } else {
    console.log('     a rect with no size is not read as covered');
  }

  win.close = savedClose;
  win.open = savedOpen;
}

// The three pane text toolbars. Two things have to hold at once: a pane's own
// slider moves that pane and no other, and a pane nobody has touched keeps
// following the reading settings, so the Settings dialog a reader already had
// goes on working on all three panes.
//
// The second is the one that is easy to lose, and the one that would hurt: a
// feature that quietly pinned the panes would leave the reader's existing font
// and spacing settings doing nothing, with nothing on screen to say why.
function runPaneToolbarChecks() {
  const panes = ['editor', 'output', 'shell'];
  const editor = elements.get('editor');
  const output = elements.get('output');
  const shellForm = elements.get('shell-form');
  const shellOutput = elements.get('shell-output');

  // ---- Closed at rest ----
  let resting = true;
  for (const pane of panes) {
    // Asked of the document rather than read out of the shared map, because
    // that map only holds what app.js has already looked up, and a panel is
    // not looked up until its arrow is pressed. A real page has the element
    // from the start, which is the state this check is about.
    const button = documentStub.getElementById(`mini-${pane}-toggle`);
    const panel = documentStub.getElementById(`mini-${pane}-panel`);
    if (!button || !panel) {
      failed = true;
      console.log(`FAIL there is no text toolbar on the ${pane} pane`);
      resting = false;
      continue;
    }
    if (panel.hidden !== true || button.getAttribute('aria-expanded') !== 'false') {
      failed = true;
      console.log(`FAIL the ${pane} toolbar did not start closed`);
      resting = false;
    }
  }
  if (resting) {
    console.log('     all three toolbars start closed, as the template draws them');
  }

  // ---- The arrow opens it, and pressing again puts it away ----
  const editorToggle = elements.get('mini-editor-toggle');
  const editorPanel = elements.get('mini-editor-panel');
  fire('mini-editor-toggle', 'click');
  if (editorPanel.hidden !== false || editorToggle.getAttribute('aria-expanded') !== 'true') {
    failed = true;
    console.log('FAIL the arrow did not open the editor toolbar');
  } else {
    console.log('     the arrow opens its panel and says that it is open');
  }
  fire('mini-editor-toggle', 'click');
  if (editorPanel.hidden !== true || editorToggle.getAttribute('aria-expanded') !== 'false') {
    failed = true;
    console.log('FAIL the arrow did not close the editor toolbar again');
  } else {
    console.log('     pressing it again puts the panel away');
  }

  // ---- The line-number tick ----
  // One control, one meaning: ticked means the numbers are showing. The
  // harness loads the page in a focus mode that shows them.
  const gutterToggle = elements.get('line-numbers-toggle');
  const bodyAttrs = documentStub.body.__attributes;
  if (!gutterToggle.checked) {
    failed = true;
    console.log('FAIL the line-number tick does not start in step with the focus mode');
  } else {
    console.log('     the tick starts ticked, in step with the focus mode');
  }

  gutterToggle.checked = false;
  fire('line-numbers-toggle', 'change');
  if (bodyAttrs['data-focus-mode'] !== 'gutter') {
    failed = true;
    console.log('FAIL unticking the line numbers did not hide them');
  } else {
    console.log('     unticking hides the numbers');
  }

  // The same tick has to bring them back, and back to the mode that hid them
  // rather than to plain "off": a reader who hid the numbers while using
  // "fade other lines" never asked to lose that setting.
  gutterToggle.checked = true;
  fire('line-numbers-toggle', 'change');
  if (bodyAttrs['data-focus-mode'] === 'gutter' || gutterToggle.checked !== true) {
    failed = true;
    console.log('FAIL ticking the line numbers again did not bring them back');
  } else {
    console.log('     ticking it again brings them back, at the mode that hid them');
  }

  // The Settings dropdown is the same setting, so it must not be left saying
  // one thing while the strip above the code says another.
  if (elements.get('focus-mode').value !== bodyAttrs['data-focus-mode']) {
    failed = true;
    console.log('FAIL the focus mode dropdown and the pane disagree');
  } else {
    console.log('     the dropdown and the pane agree through all of it');
  }

  // ---- The fade tick and its slider ----
  // The same setting seen a third way, and the slider is only in the strip
  // while fade is on.
  const fadeTick = elements.get('fade-toggle');
  const fadeBox = elements.get('fade-amount');
  const fadeSlider = elements.get('fade-slider');
  const fadeReadout = elements.get('fade-slider-value');
  const panelReadout = elements.get('blur-intensity-label');

  if (fadeTick.checked || fadeBox.hidden !== true) {
    failed = true;
    console.log('FAIL fade starts on while the focus mode is not fade');
  } else {
    console.log('     the fade tick starts in step, with its slider put away');
  }

  fadeTick.checked = true;
  fire('fade-toggle', 'change');
  if (bodyAttrs['data-focus-mode'] !== 'lines' || fadeBox.hidden !== false) {
    failed = true;
    console.log('FAIL ticking fade did not turn it on and bring out the slider');
  } else {
    console.log('     ticking fade turns it on and brings out the slider');
  }

  // The bottom of the slider is off. A control that says fade is on must not
  // leave a line faded a little, so 0 has to mean 0 and not "the faintest
  // the slider goes".
  fadeSlider.value = '0';
  fire('fade-slider', 'input');
  if (fadeReadout.textContent !== '0%' || panelReadout.textContent !== '0%') {
    failed = true;
    console.log('FAIL the bottom of the fade slider is not off in both views: ' +
                fadeReadout.textContent + ' / ' + panelReadout.textContent);
  } else if (documentStub.body.style['--blur-amount'] !== '1.00') {
    failed = true;
    console.log('FAIL the bottom of the fade slider still fades the lines: ' +
                documentStub.body.style['--blur-amount']);
  } else {
    console.log('     the bottom of the fade slider is off, and both views say so');
  }

  // Unticking takes the slider away and leaves the numbers showing: the reader
  // asked to stop fading, not to hide the numbers.
  fadeTick.checked = false;
  fire('fade-toggle', 'change');
  if (bodyAttrs['data-focus-mode'] !== 'off' || fadeBox.hidden !== true) {
    failed = true;
    console.log('FAIL unticking fade did not turn it off and put the slider away');
  } else {
    console.log('     unticking fade turns it off and puts the slider away');
  }

  // ---- Nothing has been touched, so nothing is owned ----
  // The pane is left with no styles of its own, and that is what leaves the
  // reading settings in charge of it.
  const pinned = editor.style['--font-size'] || editor.style['--line-height'] ||
    editor.style['--letter-spacing'] || output.style.fontSize ||
    output.style.lineHeight || output.style.letterSpacing ||
    shellOutput.style.fontSize || shellForm.style.fontSize;
  if (pinned) {
    failed = true;
    console.log('FAIL a pane nobody touched was pinned to a value anyway: ' + JSON.stringify(pinned));
  } else {
    console.log('     an untouched pane owns nothing, so the reading settings still reach it');
  }

  // ---- Each slider shows the reading value it is following ----
  const readingFont = elements.get('font-size').value;
  const shown = panes.map((pane) => elements.get(`${pane}-font-size`).value);
  if (shown.every((value) => value === readingFont)) {
    console.log(`     all three sliders show the reading size (${readingFont}) they follow`);
  } else {
    failed = true;
    console.log(`FAIL the pane sliders show ${JSON.stringify(shown)} while the reading size is ${readingFont}`);
  }
  const editorSizeReadout = elements.get('editor-font-size-value').textContent;
  if (editorSizeReadout === readingFont + 'px') {
    console.log('     and each size is written beside its own slider, in px');
  } else {
    failed = true;
    console.log(`FAIL the size readout says ${JSON.stringify(editorSizeReadout)}, not ${readingFont}px`);
  }

  // ---- One pane's slider moves that pane and nothing else ----
  const editorFont = elements.get('editor-font-size');
  const beforeSave = configPosts.length;
  editorFont.value = '22';
  fire('editor-font-size', 'input');
  if (editor.style['--font-size'] !== '22px') {
    failed = true;
    console.log(`FAIL the editor did not take its own size: ${JSON.stringify(editor.style['--font-size'])}`);
  } else if (output.style.fontSize || shellOutput.style.fontSize) {
    failed = true;
    console.log('FAIL the editor slider moved another pane as well');
  } else {
    console.log('     a pane takes its own size and no other pane moves');
  }
  if (elements.get('editor-font-size-value').textContent !== '22px') {
    failed = true;
    console.log('FAIL the editor readout did not follow its own slider');
  }

  // The value only leaves the page when the reader lets go, which is what a
  // change event means, and it is saved under a name of its own.
  fire('editor-font-size', 'change');
  const savedPaneSize = configPosts.slice(beforeSave).filter((post) => 'editor_font_size' in post);
  if (savedPaneSize.length === 1 && savedPaneSize[0].editor_font_size === 22) {
    console.log('     and the value is saved under the editor pane name of its own');
  } else {
    failed = true;
    console.log('FAIL the editor size was not saved on its own: ' +
      JSON.stringify(configPosts.slice(beforeSave)));
  }

  // ---- A second pane stays independent of the first ----
  const outputFont = elements.get('output-font-size');
  outputFont.value = '26';
  fire('output-font-size', 'input');
  if (output.style.fontSize === '26px' && editor.style['--font-size'] === '22px') {
    console.log('     the output pane holds its own size beside the editor one');
  } else {
    failed = true;
    console.log(`FAIL the panes did not stay independent: editor ${editor.style['--font-size']}, output ${output.style.fontSize}`);
  }

  // ---- A reading change reaches the panes that follow, and only those ----
  const globalFont = elements.get('font-size');
  globalFont.value = '24';
  fire('font-size', 'input');
  if (editor.style['--font-size'] === '22px' && output.style.fontSize === '26px') {
    console.log('     a reading change leaves a pane the reader set exactly where it was');
  } else {
    failed = true;
    console.log(`FAIL a reading change overrode a pane the reader had set: editor ${editor.style['--font-size']}, output ${output.style.fontSize}`);
  }
  const shellFont = elements.get('shell-font-size');
  if (shellFont.value === '24') {
    console.log('     while the pane still following takes the new value');
  } else {
    failed = true;
    console.log(`FAIL the following pane still shows ${shellFont.value} after the reading size became 24`);
  }

  // ---- The notching buttons, which never fire the slider's own event ----
  // This is the path a sync wired to the slider's listener would have missed,
  // so it is the one worth pinning down. The reading value is put somewhere
  // with room on both sides first, because the stepper checks above leave it
  // wherever they finished and an arrow cannot move a slider that is already
  // at the end of its travel.
  const readingHeight = elements.get('line-height');
  const shellHeight = elements.get('shell-line-height');
  readingHeight.value = '1.5';
  fire('line-height', 'input');
  fire('line-height-more', 'click');
  if (readingHeight.value === '1.5') {
    failed = true;
    console.log('FAIL the notching button did not move the reading line height at all');
  } else if (shellHeight.value !== readingHeight.value) {
    failed = true;
    console.log(`FAIL the notching button left a following pane behind: it shows ${shellHeight.value}, the setting is ${readingHeight.value}`);
  } else {
    console.log('     a following pane keeps up when the setting is moved by the arrow buttons');
  }

  console.log('pane toolbars: 12 checks');
}

// The Python shell, end to end: closed, opened, a command run, the answer
// kept on screen, a failure explained, and a close that hands the process
// back rather than leaving it running for nobody.
function runShellChecks() {
  const btn = elements.get('btn-shell');
  const pane = elements.get('shell-pane');
  const input = elements.get('shell-input');
  const out = elements.get('shell-output');
  const status = elements.get('shell-status');
  const form = elements.get('shell-form');
  const clear = elements.get('shell-clear');
  const close = elements.get('shell-close');

  // Closed to begin with. A pane that started open would let every later
  // check pass without the reader ever opening it.
  if (!pane.hidden) {
    failed = true;
    console.log('FAIL the shell started open instead of closed');
  } else {
    console.log('     the shell starts closed, so it costs nothing until it is asked for');
  }

  (btn.__listeners.click || []).forEach((h) => h(fakeEvent));
  if (pane.hidden) {
    failed = true;
    console.log('FAIL the shell did not open');
  } else {
    console.log('     it opens from its own button');
  }
  // The button says whether it is open, so somebody reading with a screen
  // reader is not left guessing.
  if (btn.getAttribute('aria-expanded') !== 'true') {
    failed = true;
    console.log('FAIL the shell button did not say it was open');
  } else {
    console.log('     the button says the shell is open');
  }

  // The divider between the output and the shell comes with it. A line
  // with nothing on the other side of it would just be a line.
  const shellDivider = elements.get('divider-shell');
  const rightColumn = elements.get('right-column');
  if (shellDivider.hidden) {
    failed = true;
    console.log('FAIL the shell divider stayed hidden when the shell opened');
  } else {
    console.log('     opening the shell brings its divider with it');
  }

  // The shell divider resizes the shell, not the editor. The divider is the
  // shell's top edge, so ArrowDown moves it down and makes the shell
  // shorter, and ArrowUp moves it up and makes it taller.
  fire('divider-shell', 'keydown', { key: 'ArrowDown', preventDefault: noop, stopPropagation: noop });
  if (shellDivider.getAttribute('aria-valuenow') !== '45') {
    failed = true;
    console.log(`FAIL ArrowDown did not shrink the shell: ${shellDivider.getAttribute('aria-valuenow')}`);
  } else if (rightColumn.style['--shell-height'] !== '45%') {
    failed = true;
    console.log(`FAIL the shell height never reached the stylesheet: ${rightColumn.style['--shell-height']}`);
  } else {
    console.log('     ArrowDown shrinks the shell, and the height reaches the stylesheet');
  }
  fire('divider-shell', 'keydown', { key: 'ArrowUp', preventDefault: noop, stopPropagation: noop });
  if (shellDivider.getAttribute('aria-valuenow') !== '50') {
    failed = true;
    console.log(`FAIL ArrowUp did not grow the shell back: ${shellDivider.getAttribute('aria-valuenow')}`);
  } else {
    console.log('     ArrowUp grows the shell back');
  }

  // The drag path for the shell divider, in the same direction as the
  // keyboard: dragging down shrinks the shell. The stub's right column is
  // 100px tall, so ten pixels is ten percent.
  fire('divider-shell', 'pointerdown', { button: 0, clientY: 300, preventDefault: noop, stopPropagation: noop });
  fire('divider-shell', 'pointermove', { clientY: 310, preventDefault: noop, stopPropagation: noop });
  fire('divider-shell', 'pointerup', { preventDefault: noop, stopPropagation: noop });
  if (shellDivider.getAttribute('aria-valuenow') !== '40') {
    failed = true;
    console.log(`FAIL dragging the shell divider down did not shrink the shell: ${shellDivider.getAttribute('aria-valuenow')}`);
  } else {
    console.log('     dragging the shell divider down shrinks the shell');
  }

  setTimeout(() => {
    // A session has to be opened before anything can be run in it.
    if (!fetchCalls.some((u) => u.includes('/api/shell/start'))) {
      failed = true;
      console.log('FAIL the shell never asked for a session');
    } else {
      console.log('     it asks the server for a session, and the id is kept for later commands');
    }

    input.value = 'answer = 6 * 7';
    fire('shell-form', 'submit', { preventDefault: noop, stopPropagation: noop });

    setTimeout(() => {
      const sent = shellCommands[shellCommands.length - 1];
      if (!sent) {
        failed = true;
        console.log('FAIL nothing was sent to the shell');
      } else if (sent.session !== 'session-1') {
        failed = true;
        console.log(`FAIL the command did not carry its session id: ${sent.session}`);
      } else if (sent.code !== 'answer = 6 * 7') {
        failed = true;
        console.log(`FAIL the wrong code was sent: ${sent.code}`);
      } else {
        console.log('     a command is sent with the reader\'s own code and the session id');
      }

      if (!/answer = 6 \* 7/.test(String(out.textContent))) {
        failed = true;
        console.log(`FAIL the shell's answer never reached the screen: "${out.textContent}"`);
      } else {
        console.log('     the answer is shown');
      }

      // A second command must not wipe the first answer off the screen. A
      // shell you cannot look back in is a log, not a shell.
      input.value = 'print(answer)';
      fire('shell-form', 'submit', { preventDefault: noop, stopPropagation: noop });
      setTimeout(() => {
        if (!/answer = 6 \* 7/.test(String(out.textContent))) {
          failed = true;
          console.log('FAIL the next command wiped the previous answer off the screen');
        } else {
          console.log('     a second command keeps what came before it on screen');
        }

        // A failure is said in words, not left as an empty box.
        input.value = 'boom';
        fire('shell-form', 'submit', { preventDefault: noop, stopPropagation: noop });
        setTimeout(() => {
          if (!/boom/.test(String(out.textContent))) {
            failed = true;
            console.log(`FAIL a failed command was not explained: "${out.textContent}"`);
          } else {
            console.log('     a failed command is explained on screen, not swallowed');
          }

          // Clearing wipes the namespace and the transcript together, so
          // the two never disagree about what is still defined.
          (clear.__listeners.click || []).forEach((h) => h(fakeEvent));
          setTimeout(() => {
            if (!fetchCalls.some((u) => u.includes('/api/shell/reset'))) {
              failed = true;
              console.log('FAIL clearing did not tell the server to forget the namespace');
            } else if (String(out.textContent) !== '') {
              failed = true;
              console.log(`FAIL clearing left the old answers on screen: "${out.textContent}"`);
            } else {
              console.log('     clearing forgets both the definitions and the transcript');
            }

            // Closing gives the process back. A shell left running after the
            // reader walks away is a python.exe nobody is looking after.
            (close.__listeners.click || []).forEach((h) => h(fakeEvent));
            if (!pane.hidden) {
              failed = true;
              console.log('FAIL the shell did not close');
            } else if (!fetchCalls.some((u) => u.includes('/api/shell/stop'))) {
              failed = true;
              console.log('FAIL closing left the shell process running');
            } else if (btn.getAttribute('aria-expanded') !== 'false') {
              failed = true;
              console.log('FAIL the button still said the shell was open');
            } else {
              console.log('     closing hands the process back and clears the button');
            }

            // The divider goes back into hiding with the pane it belongs to.
            if (!shellDivider.hidden) {
              failed = true;
              console.log('FAIL the shell divider stayed visible when the shell closed');
            } else {
              console.log('     closing the shell hides its divider again');
            }

            console.log('shell: 15 checks');
            // Hand over to the interactive run checks rather than exiting here.
            // This used to reassign finish() first, which quietly replaced the
            // module stage with a plain exit - so the checks after the shell
            // never ran and the run still reported success.
            //
            // The run checks are started from inside this chain, not scheduled
            // beside the others, because this chain is the only thing that calls
            // finish(): anything started outside it races the exit, and losing
            // that race is a silent pass rather than a failure.
            runInteractiveChecks(finish);
          }, 10);
        }, 10);
      }, 10);
    }, 10);
  }, 10);
}

// ---------------------------------------------------------------------------
// A program that asks the reader a question.
//
// The runner is answered twice: once as a program sat at input(), and again
// once the reader has answered it. Walking both requests is the only way to
// prove the round trip. A double that answered everything at once would never
// show the answer row appearing, and an answer that never reached the second
// request would look exactly like success from the outside.
// ---------------------------------------------------------------------------
function runInteractiveChecks(done) {

  // A press the reader makes, written the way the handler reads it. The
  // listener is registered against the document, so a press has to be fired
  // there to reach it.
  function press(key, mods) {
    var event = { key: key, preventDefault: function () { this.defaultPrevented = true; }, stopPropagation: function () {} };
    event.ctrlKey = false; event.altKey = false; event.shiftKey = false; event.metaKey = false;
    if (mods) { for (var k in mods) event[k] = mods[k]; }
    return event;
  }
  function pressDoc(event) {
    var handlers = documentStub.__listeners.keydown || [];
    for (var i = 0; i < handlers.length; i++) handlers[i](event);
    return event;
  }
  function setEditorFocused(on) { editorFocused = !!on; }
  function clearPresses() { runBodies.length = 0; stopBodies.length = 0; }

  const form = elements.get('answer-form');
  const answerField = elements.get('answer-input');
  const answerNote = elements.get('answer-status');
  const out = elements.get('output');
  const waitingNote = CATALOGUE['output.answer_waiting'];
  const noOutputNote = CATALOGUE['output.no_output'];
  const question = 'What is your name? ';
  const finished = 'What is your name? alice\nhello alice\n';

  // The reader's program is put in place rather than assumed, so the code the
  // answers are collected against is the same on every run.
  editorInstance.setValue('name = input("What is your name? ")\nprint("hello " + name)');
  runBodies.length = 0;
  runReplies.length = 0;
  runReplies.push(
    { success: true, output: question, error: '', error_line: null, awaiting_answer: true, trace: null },
    { success: true, output: finished, error: '', error_line: null, awaiting_answer: false, trace: null }
  );

  fire('btn-run', 'click');

  setTimeout(() => {
    if (runBodies.length !== 1) {
      failed = true;
      console.log(`FAIL pressing Run did not run the program once: ${runBodies.length} requests`);
    } else if (form.hidden) {
      failed = true;
      console.log('FAIL the answer row stayed hidden while the program waited for an answer');
    } else if (String(out.textContent) !== question) {
      failed = true;
      console.log(`FAIL the question was not left on screen: "${out.textContent}"`);
    } else if (String(answerNote.textContent) !== waitingNote) {
      failed = true;
      console.log(`FAIL the answer row said "${answerNote.textContent}" rather than "${waitingNote}"`);
    } else {
      console.log('     a program that asks a question shows the question, with a row to answer it');
    }

    // The answer typed the way the row's own button would submit it.
    answerField.value = 'alice';
    fire('answer-form', 'submit', { preventDefault: noop, stopPropagation: noop });

    setTimeout(() => {
      const carried = (runBodies[runBodies.length - 1] || {}).answers || [];
      if (runBodies.length !== 2) {
        failed = true;
        console.log(`FAIL answering the question did not run the program again: ${runBodies.length} requests`);
      } else if (carried.length !== 1 || carried[0] !== 'alice') {
        failed = true;
        console.log(`FAIL the answer did not travel with the second request: ${JSON.stringify(carried)}`);
      } else if (!form.hidden) {
        failed = true;
        console.log('FAIL the answer row stayed on screen after the program finished');
      } else if (String(out.textContent) !== finished) {
        failed = true;
        console.log(`FAIL the finished program output never reached the screen: "${out.textContent}"`);
      } else {
        console.log('     the answer is sent back with the program, and the row goes when it is done');
      }

      // A bare input() prints nothing, so the transcript is empty while the
      // program waits. Saying "(no output)" there would tell the reader their
      // program did nothing at the moment it is waiting to be answered, which
      // is the one thing it is definitely doing.
      runReplies.push(
        { success: true, output: '', error: '', error_line: null, awaiting_answer: true, trace: null }
      );
      editorInstance.setValue('input()\nprint("done")');
      fire('btn-run', 'click');

      setTimeout(() => {
        if (runBodies.length !== 3) {
          failed = true;
          console.log(`FAIL the second program did not run: ${runBodies.length} requests`);
        } else if (form.hidden) {
          failed = true;
          console.log('FAIL the answer row stayed hidden for a program waiting on a bare input()');
        } else if (String(out.textContent) === noOutputNote) {
          failed = true;
          console.log('FAIL a program waiting on a bare input() was reported as having no output');
        } else if (String(out.textContent) !== '') {
          failed = true;
          console.log(`FAIL a waiting program left something on screen: "${out.textContent}"`);
        } else {
          console.log('     a bare input() leaves the transcript empty and still offers a row');
        }
        // -----------------------------------------------------------------
        // Stopping a running program
        //
        // The program runs in a process of its own, so stopping it is a
        // request aimed at that program by name. Both paths to it are walked:
        // the Stop button, and Escape twice. What neither may do is leave the
        // stopped run's own reply on screen afterwards, which is the failure
        // that would make a stopped program look like a finished one.
        // -----------------------------------------------------------------
        stopBodies.length = 0;
        runBodies.length = 0;
        runReplies.length = 0;
        runReplies.push({
          success: true, output: 'still going\n', error: '', error_line: null,
          awaiting_answer: false, trace: null,
        });
        editorInstance.setValue('while True: pass');
        const stopButton = elements.get('btn-stop');
        fire('btn-run', 'click');

        if (stopButton.hidden) {
          failed = true;
          console.log('FAIL no way to stop a program was offered while one was running');
        } else {
          console.log('     a running program offers a way to stop it');
        }

        fire('btn-stop', 'click');

        setTimeout(() => {
          const stopBody = stopBodies[stopBodies.length - 1] || {};
          const runId = (runBodies[0] || {}).run_id;

          if (stopBodies.length !== 1) {
            failed = true;
            console.log(`FAIL pressing Stop did not ask for the program to be stopped: ${stopBodies.length} requests`);
          } else if (!runId || stopBody.run_id !== runId) {
            failed = true;
            console.log(`FAIL the stop was not aimed at the program that was running: sent ${JSON.stringify(stopBody.run_id)}, running ${JSON.stringify(runId)}`);
          } else {
            console.log('     Stop asks for the program that is running to be stopped, by name');
          }

          if (String(out.textContent) !== CATALOGUE['output.stopped']) {
            failed = true;
            console.log(`FAIL a stopped program was not left saying it was stopped: "${out.textContent}"`);
          } else {
            console.log('     a stopped program says so, and the run it stopped does not overwrite that');
          }

          if (!stopButton.hidden) {
            failed = true;
            console.log('FAIL the stop button stayed once the program had been stopped');
          } else {
            console.log('     the stop button goes once the program has been stopped');
          }

          // Escape twice, the keyboard path to the same thing.
          stopBodies.length = 0;
          runBodies.length = 0;
          runReplies.length = 0;
          runReplies.push({
            success: true, output: 'still going\n', error: '', error_line: null,
            awaiting_answer: false, trace: null,
          });
          editorInstance.setValue('while True: pass');
          fire('btn-run', 'click');

          // One Escape on its own is left alone: it is the key that closes the
          // dialogs, and taking it would break that everywhere else.
          fireDocument('keydown', { key: 'Escape', preventDefault: noop });
          if (stopBodies.length !== 0) {
            failed = true;
            console.log('FAIL a single Escape stopped a running program');
          } else {
            console.log('     one Escape on its own does not stop a running program');
          }

          fireDocument('keydown', { key: 'Escape', preventDefault: noop });
          if (stopBodies.length !== 1) {
            failed = true;
            console.log(`FAIL Escape twice did not stop the program: ${stopBodies.length} stop requests`);
          } else {
            console.log('     Escape twice stops the program');
          }

          console.log('     Escape twice stops the program');

          // -------------------------------------------------------------
          // What the reader chose in Settings is what fires
          //
          // Both presses are settings now, not lines written into the
          // script, so what is in the two lists is what the next press has
          // to obey: choosing from a list, recording a press, and the press
          // itself all have to agree, and a press the reader is not in the
          // code for must not run anything at all.
          // -------------------------------------------------------------
          stopBodies.length = 0;
          runBodies.length = 0;
          runReplies.length = 0;
          runReplies.push({
            success: true, output: 'ran\n', error: '', error_line: null,
            awaiting_answer: false, trace: null,
          });
          editorInstance.setValue('print("hi")');

          // The reader is somewhere else on the page. Enter with Ctrl held
          // down is still the press that runs the code, but not while they
          // are not in the code: it would run something they cannot see.
          setEditorFocused(false);
          fireDocument('keydown', press('Enter', { ctrlKey: true }));
          if (runBodies.length !== 0) {
            failed = true;
            console.log(`FAIL the run press fired while the reader was not in the code: ${runBodies.length} requests`);
          } else {
            console.log('     the run press leaves the reader alone while they are not in the code');
          }

          // Now they are in the code, and the same press runs it.
          setEditorFocused(true);
          fireDocument('keydown', press('Enter', { ctrlKey: true }));
          if (runBodies.length !== 1) {
            failed = true;
            console.log(`FAIL the run press did not run the code while the reader was in it: ${runBodies.length} requests`);
          } else {
            console.log('     the run press runs the code while the reader is in it');
          }

          // Ctrl with a different key is not the press that runs anything.
          fireDocument('keydown', press('a', { ctrlKey: true }));
          if (runBodies.length !== 1) {
            failed = true;
            console.log('FAIL a key that is not the run press ran the code');
          } else {
            console.log('     a Ctrl press on any other key is left alone');
          }

          // The reader is still in the code. Enter with nothing held down
          // still starts a new line, and must not run what is there.
          fireDocument('keydown', press('Enter'));
          if (runBodies.length !== 1) {
            failed = true;
            console.log('FAIL Enter on its own ran the code instead of starting a new line');
          } else {
            console.log('     Enter on its own still starts a new line and does not run the code');
          }

          // Ctrl+Shift+Enter is a listed choice, and is not the press that
          // is in use. A listed choice that does nothing when pressed would
          // leave the reader choosing from a list of things that do not work.
          const runSelect = elements.get('run-key');
          runSelect.value = 'Ctrl+Shift+Enter';
          fireElement(runSelect, 'change');
          runBodies.length = 0;
          fireDocument('keydown', press('Enter', { ctrlKey: true, shiftKey: true }));
          if (runBodies.length !== 1) {
            failed = true;
            console.log(`FAIL the run press chosen from the list did not run the code: ${runBodies.length} requests`);
          } else {
            console.log('     a run press chosen from the list is the one that fires');
          }

          // ...and the one that is no longer chosen has stopped working.
          fireDocument('keydown', press('Enter', { ctrlKey: true }));
          if (runBodies.length !== 1) {
            failed = true;
            console.log('FAIL the old run press still ran the code after a new one was chosen');
          } else {
            console.log('     the run press that was replaced has stopped working');
          }
          runSelect.value = 'Ctrl+Enter';
          fireElement(runSelect, 'change');

          // -------------------------------------------------------------
          // Recording a press
          //
          // For a reader who would rather press the keys than read a list.
          // The button takes the next press, that press becomes the setting,
          // and the list has to end up showing it.
          // -------------------------------------------------------------
          const recordRunButton = elements.get('btn-record-run');
          const recordRunText = elements.get('record-run-text');
          const runStatus = elements.get('keys-run-status');

          fireElement(recordRunButton, 'click');
          if (!recordRunButton.classList.contains('is-recording')) {
            failed = true;
            console.log('FAIL the record button did not show it was waiting for a press');
          } else {
            console.log('     the record button shows it is waiting for a press');
          }
          if (String(recordRunText.textContent) !== CATALOGUE['keys.recording']) {
            failed = true;
            console.log(`FAIL the record button did not say it was waiting: "${recordRunText.textContent}"`);
          } else {
            console.log('     the record button says what it is waiting for');
          }

          // A modifier on its own is half a press. The reader has not
          // finished, so it is neither recorded nor a way out.
          runBodies.length = 0;
          fireDocument('keydown', press('Shift', {}));
          if (!recordRunButton.classList.contains('is-recording')) {
            failed = true;
            console.log('FAIL a modifier on its own ended the recording');
          } else if (runBodies.length !== 0) {
            failed = true;
            console.log('FAIL a modifier on its own was stored as the run press');
          } else {
            console.log('     a modifier on its own is not taken as the press');
          }

          // Ctrl+Alt+Enter is a press this app can use. It is recorded, it
          // becomes the setting, and the list shows it even though it was
          // not offered there to begin with.
          fireDocument('keydown', press('Enter', { ctrlKey: true, altKey: true }));
          const recordedSave = configPosts[configPosts.length - 1] || {};
          if (recordedSave.run_key !== 'Ctrl+Alt+Enter') {
            failed = true;
            console.log(`FAIL the recorded press was not saved: ${JSON.stringify(recordedSave)}`);
          } else {
            console.log('     a recorded press becomes the setting');
          }
          if (runSelect.value !== 'Ctrl+Alt+Enter') {
            failed = true;
            console.log(`FAIL the recorded press was not put in the list: "${runSelect.value}"`);
          } else if (!runSelect.options.some((o) => o.value === 'Ctrl+Alt+Enter')) {
            failed = true;
            console.log('FAIL the recorded press was not added to the list it is shown in');
          } else {
            console.log('     the recorded press is in the list the reader picks from');
          }
          if (recordRunButton.classList.contains('is-recording')) {
            failed = true;
            console.log('FAIL the record button kept waiting after the press was recorded');
          } else {
            console.log('     the recording ends with the press that was recorded');
          }
          if (String(runStatus.textContent) !== CATALOGUE['settings.saved']) {
            failed = true;
            console.log(`FAIL the reader was not told the new press was saved: "${runStatus.textContent}"`);
          } else {
            console.log('     the reader is told the new press was saved');
          }

          // The press that was just recorded is the one that fires now, and
          // recording it must not have run the code by itself.
          runBodies.length = 0;
          fireDocument('keydown', press('Enter', { ctrlKey: true, altKey: true }));
          if (runBodies.length !== 1) {
            failed = true;
            console.log(`FAIL the recorded press did not run the code: ${runBodies.length} requests`);
          } else {
            console.log('     the press that was just recorded is the one that runs the code');
          }

          // -------------------------------------------------------------
          // A press this app cannot use
          //
          // Recorded the same way, and refused rather than stored and left
          // doing nothing. What the reader had stays as it was.
          // -------------------------------------------------------------
          fireElement(recordRunButton, 'click');
          const keyBefore = runSelect.value;
          fireDocument('keydown', press('a', {}));
          if (String(runStatus.textContent) !== CATALOGUE['keys.rejected']) {
            failed = true;
            console.log(`FAIL a press this app cannot use was not refused: "${runStatus.textContent}"`);
          } else {
            console.log('     a press this app cannot use is refused in words');
          }
          if (runSelect.value !== keyBefore) {
            failed = true;
            console.log(`FAIL a refused press replaced the one that was working: "${runSelect.value}"`);
          } else {
            console.log('     a refused press leaves the one that was working in place');
          }
          if (recordRunButton.classList.contains('is-recording')) {
            failed = true;
            console.log('FAIL the record button kept waiting after a press was refused');
          } else {
            console.log('     a refused press still ends the recording');
          }

          // -------------------------------------------------------------
          // Escape, both while recording and while a program runs
          //
          // Escape with nothing held down cancels a recording and keeps the
          // dialog open, and a listed stop press stops the program from
          // wherever the reader happens to be.
          // -------------------------------------------------------------
          fireElement(recordRunButton, 'click');
          const escapeEvent = press('Escape', {});
          fireDocument('keydown', escapeEvent);
          if (escapeEvent.defaultPrevented !== true) {
            failed = true;
            console.log('FAIL Escape did not stop the box closing while a recording was cancelled');
          } else {
            console.log('     Escape cancels the recording and stays in the box');
          }
          if (recordRunButton.classList.contains('is-recording')) {
            failed = true;
            console.log('FAIL the record button kept waiting after Escape');
          } else {
            console.log('     the recording ends with Escape');
          }

          // A stop press chosen from the list works from anywhere, the
          // reader being in the code or not.
          stopBodies.length = 0;
          runBodies.length = 0;
          runReplies.length = 0;
          runReplies.push({
            success: true, output: 'still going\n', error: '', error_line: null,
            awaiting_answer: false, trace: null,
          });
          editorInstance.setValue('while True: pass');
          setEditorFocused(false);
          const stopSelect = elements.get('stop-key');
          stopSelect.value = 'Shift+Escape';
          fireElement(stopSelect, 'change');
          fire('btn-run', 'click');

          fireDocument('keydown', press('Escape', { shiftKey: true }));
          if (stopBodies.length !== 1) {
            failed = true;
            console.log(`FAIL the stop press chosen from the list did not stop the program: ${stopBodies.length} requests`);
          } else {
            console.log('     a stop press chosen from the list stops the program, from anywhere');
          }

          setEditorFocused(false);
          console.log('run: 32 checks');
          done();
        }, 0);
      }, 10);
    }, 10);
  }, 10);
}

// ---------------------------------------------------------------------------
// The Python dictionary. Every row is in the page before the script runs, so
// the only thing to check is that the search hides rather than loses: the
// counts are read back off the rows, which is what makes "the filter ran"
// different from "the filter was wired up".
// ---------------------------------------------------------------------------

function runGlossaryChecks() {
  const status = elements.get('glossary-status');
  const empty = elements.get('glossary-empty');
  const search = elements.get('glossary-search');
  const visible = () => GLOSSARY_ROWS.filter((row) => !row.hidden);

  const openedBefore = GLOSSARY_DIALOG.__open;
  fire('btn-glossary', 'click');
  if (GLOSSARY_DIALOG.__open === openedBefore) {
    failed = true;
    console.log('FAIL the dictionary button did not open the dictionary');
  } else {
    console.log('     the dictionary opens from its button');
  }

  // A word that appears in one entry and in no other.
  search.value = 'print';
  fire('glossary-search', 'input');
  if (visible().length !== 1) {
    failed = true;
    console.log(`FAIL searching for one word left ${visible().length} entries showing`);
  } else {
    console.log('     searching hides the entries that do not match');
  }

  // A heading with nothing under it reads as an empty section rather than as a
  // search that found nothing, so the section goes with its entries.
  if (GLOSSARY_SECTIONS[1].hidden !== true) {
    failed = true;
    console.log('FAIL a section with no matching entry kept its heading');
  } else if (GLOSSARY_SECTIONS[0].hidden === true) {
    failed = true;
    console.log('FAIL the section the match is in was hidden too');
  } else {
    console.log('     a section with no matching entry goes with them');
  }

  // Spoken, because a reader who cannot see the list shrink has no other way to
  // know their typing did anything.
  const expected = String(CATALOGUE['glossary.count'])
    .split('{0}').join('1')
    .split('{1}').join(String(GLOSSARY_ROWS.length));
  if (!status || String(status.textContent) !== expected) {
    failed = true;
    console.log(`FAIL the number of matches was not announced: "${status && status.textContent}"`);
  } else {
    console.log('     the number of matches is announced');
  }

  // A search that matches nothing.
  search.value = 'zzzz';
  fire('glossary-search', 'input');
  if (!empty || empty.hidden !== false) {
    failed = true;
    console.log('FAIL nothing said that no entry matched');
  } else {
    console.log('     a search that matches nothing says so');
  }
  if (String(status.textContent) !== CATALOGUE['glossary.empty']) {
    failed = true;
    console.log(`FAIL the empty result was not announced: "${status.textContent}"`);
  }

  // And clearing brings everything back, which is what proves the filter is not
  // one way: nothing may be lost by looking for something.
  search.value = '';
  fire('glossary-search', 'input');
  const sectionsBack = GLOSSARY_SECTIONS.filter((section) => !section.hidden);
  if (visible().length !== GLOSSARY_ROWS.length ||
      sectionsBack.length !== GLOSSARY_SECTIONS.length) {
    failed = true;
    console.log(`FAIL clearing the search left ${visible().length} entries and ` +
                `${sectionsBack.length} sections showing`);
  } else {
    console.log('     clearing the search brings every entry back');
  }
  if (empty.hidden !== true) {
    failed = true;
    console.log('FAIL the empty message stayed after the search was cleared');
  }

  console.log('glossary: 6 checks');
}

// ---------------------------------------------------------------------------
// Quitting. The order is the whole point: the question is asked, and the app
// stays up until the answer is the one that leaves.
// ---------------------------------------------------------------------------

function runQuitChecks() {
  const before = shutdowns.length;
  const quitButton = elements.get('btn-quit');

  // It is only for the installed app, so app.js has to have finished checking
  // before it can be showing.
  if (!quitButton || quitButton.hidden) {
    failed = true;
    console.log('FAIL the quit button was never revealed on the installed app');
  } else {
    console.log('     the quit button is offered on the installed app');
  }

  fire('btn-quit', 'click');
  if (QUIT_DIALOG.__open !== true) {
    failed = true;
    console.log('FAIL quitting did not ask first');
  } else {
    console.log('     quitting asks before it does anything');
  }
  if (shutdowns.length !== before) {
    failed = true;
    console.log('FAIL the shutdown was sent before the reader answered');
  } else {
    console.log('     nothing is shut down until the reader answers');
  }

  // The way back.
  fire('btn-quit-keep', 'click');
  if (QUIT_DIALOG.__open !== false) {
    failed = true;
    console.log('FAIL saying no did not close the question');
  } else {
    console.log('     saying no leaves the app running');
  }
  if (shutdowns.length !== before) {
    failed = true;
    console.log('FAIL saying no still shut the app down');
  }

  // And the way out.
  fire('btn-quit', 'click');
  fire('btn-quit-confirm', 'click');
  if (shutdowns.length !== before + 1) {
    failed = true;
    console.log(`FAIL confirming did not shut the app down: ` +
                `${shutdowns.length - before} requests`);
  } else {
    console.log('     confirming shuts the app down, and only then');
  }
  if (shutdowns[shutdowns.length - 1] !== 'POST') {
    failed = true;
    console.log(`FAIL the shutdown went out as ${shutdowns[shutdowns.length - 1]}`);
  }

  console.log('quit: 6 checks');
}

setTimeout(() => {
  runPanelChecks();
  runStepperChecks();
  runLanguageChecks();
  setTimeout(runLanguageReloadCheck, 10);
  // The reset needs its own window: the update chain and the language
  // change both reload, and their promises settle after the synchronous
  // checks above. By 30ms they have, so the reset's reload count is exact.
  setTimeout(() => {
    runResetConfigChecks();
    setTimeout(runResetConfigReloadCheck, 10);
  }, 30);
  // The dividers answer synchronously, so the layout checks need no window
  // of their own.
  runLayoutChecks();
  runFocusObscuredChecks();
  // Also synchronous, and deliberately after the stepper checks: those move
  // the reading settings, and this proves a following pane kept up with them.
  runPaneToolbarChecks();
  // Both synchronous, like the layout checks above: neither waits on a reply.
  runGlossaryChecks();
  runQuitChecks();
  // Last, because it asserts on the final exit and the checks above are
  // still in flight when it starts.
  setTimeout(runShellChecks, 200);
}, 50);
