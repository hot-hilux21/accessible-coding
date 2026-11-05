# AccessibleIDE review

## 1. Repo audit

**Scope of this audit.** I read README.md, accessible-ide-requirements.md, app.py, smoke_test.py and AGENTS.md. GitHub blocked the folder pages, so I could not read src/accessible_ide/ (routes.py, static, templates, updater, config, utils), tests/, .github/workflows/, docs/, scripts/, tools/, render.yaml or installer.iss. Anything about those is marked "verify". WCAG criterion numbers below are from memory; check them against the W3C WCAG 2.1 text.

**What exists today**
- Flask app. app.py runs it in a PyWebView/WebView2 window on Windows; wsgi.py serves the Render deployment.
- CodeMirror Python editor, runner with a 10-second timeout, and in-app sandbox checks (blocked imports, open(), dunder names).
- Optional access code on the web version, and a rate limit of 10 runs per minute per caller.
- Bundled fonts (OpenDyslexic, Atkinson Hyperlegible, Lexend, Nunito), 4 themes, focus mode (hide gutter or blur other lines), text-to-speech (engine not stated), plain-English errors, and an error_line value returned by the run API.
- JSON settings with key and value validation, and a /health endpoint.
- UI in en, fr, ar and uk, which is not in the spec.
- Windows installer, portable exe and a self-updater (app.py calls accessible_ide.updater).
- Tests: smoke_test.py (module-level asserts) covers the page, run success and errors, sandbox, config validation, themes, fonts, access code, language switching and the rate limiter. AGENTS.md refers to tests/test_contrast.py, which I did not read.

**MVP coverage against requirements doc section 10**
- Covered (Must-Have v0.1): editor, runner, 4 themes, font choice, focus mode, plain errors, Flask web, Windows exe, public repo.
- Only partly covered: "Local file save/load" is met for settings only; README defers saving and opening code files to v0.2. "REPL/runner" is a runner only.
- Not present per README (Should-Have): custom theme builder, multiple TTS engines, Drive/OneDrive sync, step-by-step debugger, configurable blur zones, multi-language syntax.
- Unclear: visual error highlighting. README leaves it unchecked, but the API returns error_line. Verify the UI.
- In the spec outside the section 10 list, and not mentioned in README: first-run font picker with live preview, size/weight/line-height/letter-spacing controls, custom font upload, settings export/import, TTS engine choice with descriptions, a WCAG 2.1 AA audit record, and a record of dyslexic tester feedback.
- Out-of-date docs: README says v0.1.0-beta and lists v0.2 items as open. AGENTS.md says "Pre-development" and "all directories are currently empty". The spec checklist is entirely unticked.
- The Releases section on the repo page I fetched showed no releases, though README links to releases/latest/download/. Verify.

## 2. What needs to be added

### P0 (blocking real usability)
- [ ] Save and open .py files from disk, and autosave the current buffer so a closed tab or crash loses nothing (static JS, templates, routes.py).
- [ ] Support input() in the runner with a prompt in the output panel, and do not count waiting time toward the 10-second timeout; smoke_test.py does not cover it (routes.py run endpoint, tests/).
- [ ] Publish a real release and confirm both README download links resolve (.github/workflows/, GitHub Releases).
- [ ] Verify the updater only fetches from this project's release URL over HTTPS and checks a SHA-256 hash or signature before running the installer (src/accessible_ide/updater.py, app.py exit hook).

- [ ] Do not rely on in-app checks alone to run strangers' code on the public web version: run it in an isolated process or container with CPU, memory and time limits and no network, or move web execution into the browser (Pyodide, a Web Worker) (routes.py, wsgi.py, render.yaml).
- [ ] Full keyboard-only pass of every control, with a documented way to leave the editor without a mouse (static JS, templates).
- [ ] Screen reader pass with NVDA (free, open source) and Narrator on both the web app and the WebView2 window, and fix what blocks use (all UI).

### P1 (important)
- [ ] Make the web version fail closed or clearly documented when ACCESS_CODE is unset; smoke_test.py shows the runner is open in that case (routes.py, render.yaml).
- [ ] Check how the rate limiter identifies a caller behind Render's proxy and whether the count is per worker; make the limit configurable, since a classroom on one IP shares it (routes.py RATE_LIMIT).
- [ ] First-run "Pick your font" screen with live code preview and focus returned correctly on close, as in spec 4.1 (templates, static JS, config/).
- [ ] Font controls: size, weight, line height, letter spacing, word spacing, all persisted; the tests only show a font_size key (config/, routes.py allowed keys, style.css).
- [ ] Custom font upload (.ttf/.woff) with type and size checks, stored locally (static JS, routes.py).
- [ ] Custom theme builder that shows live contrast ratios and warns below 4.5:1 for text (static JS, theme table in routes.py, tests/test_contrast.py).
- [ ] Per-token syntax colour editing, as in spec 3.2 (static JS, theme table).
- [ ] Configurable blur zones (line range, block, function, gutter) with a strength control and the spec's "keep syntax sharp" option (static JS, config/).
- [ ] Visual error highlighting in the editor using error_line, with a marker and text, not colour alone (static JS, templates).
- [ ] Step-by-step debugger that shows each line and variable values in plain language (new module under src/accessible_ide/, static JS).
- [ ] TTS: say which engine is used today, then add a selector with at least 3 engines and a short description of each, plus rate, voice, volume, pause/stop and word highlighting (static JS, config/). Check the licence and maintenance status of anything you add; I am not certain Coqui TTS is still maintained, and ReciteMe is proprietary.
- [ ] Code-aware reading for TTS (say "open bracket", "colon", ignore indentation whitespace), switchable in settings (static JS, utils/).
- [ ] Settings export/import as a file, as in spec section 2 (routes.py, config/, templates).
- [ ] Make the web version usable offline after first load, since the spec says offline-first (service worker, local execution).
- [ ] Convert smoke_test.py into pytest tests in tests/, and add cases for input(), infinite loops, large output, unicode, concurrent runs, file save/open and config import (tests/, README "Run tests").
- [ ] Extend the plain-English error tests beyond ZeroDivisionError and SyntaxError, and list which exception types are translated (utils/, tests/).
- [ ] Have fluent speakers review the fr, ar and uk error explanations, and add a "report a bad translation" link (config/ or locale files, docs/).
- [ ] Confirm CI runs tests on every push and pull request, not only on release tags (.github/workflows/).
- [ ] Add an automated accessibility check in CI, such as axe-core (open source) in a headless browser (.github/workflows/, tests/).
- [ ] Pin dependencies and turn on Dependabot (requirements.txt, .github/).
- [ ] Keep one hosting config. render.yaml, railway.json, vercel.json and a committed .vercel/ folder all exist, and README names only Render. Remove the others (repo root).
- [ ] Check the Render plan for sleeping or cold starts against spec section 11 (99% uptime, first run under 2 minutes), and add an uptime monitor (render.yaml, docs/).
- [ ] Code-sign the exe and installer, or at least publish SHA-256 checksums with each release; the unsigned warning is a barrier for the target users (installer.iss, AccessibleIDE.spec, release workflow).
- [ ] Update README (status, version, languages, updater, sandbox limits), AGENTS.md (status, layout, mention of components/), and the spec checklist (README.md, AGENTS.md, accessible-ide-requirements.md).
- [ ] List which standard-library modules work on the web version and which on desktop, and explain blocked code in plain English (docs/, README).
- [ ] Run the spec section 8 loop with 2 to 3 dyslexic testers and record the results (docs/).
- [ ] Write an accessibility statement with tested tools, versions, date and known issues (docs/accessibility.md).

- [ ] Repo files: SECURITY.md (the app runs user code), CONTRIBUTING.md (permission-first PRs per spec section 6), CHANGELOG.md, issue templates including an accessibility report, and licence texts for every bundled font (repo root, .github/).

### P2 (nice to have)
- [ ] Interactive REPL panel in addition to the runner (static JS, routes.py).
- [ ] Optional Google Drive/OneDrive sync, opt-in only (new module, config/).
- [ ] Multi-language syntax starting with JavaScript (static JS, editor config).
- [ ] Linter integration, Jupyter compatibility, plugins, collaborative editing, Linux AppImage (spec "Nice-to-Have").
- [ ] Short guide for adding a UI language, and an RTL layout test (docs/, tests/).
- [ ] README screenshots with alt text, and a short "Project status" section in place of the unclosed parenthetical at the top (README.md).

## 3. Accessibility gaps

I could not read the CSS, JavaScript or templates, so these are checks to run and risks to look at, not confirmed failures.

- **Contrast of syntax colours (1.4.3).** Pastel and light themes are the most likely to fail 4.5:1, especially comments and strings. Confirm tests/test_contrast.py covers every theme and token colour, selection, placeholder and disabled text, error output, and blurred text.
- **Non-text contrast (1.4.11).** Focus rings, gutter markers, error-line highlights and form control borders need 3:1 against their background. Check the same test covers them.
- **Colour as the only signal (1.4.1).** Errors, warnings and success must also use text or an icon. Token types should not depend on colour alone.
- **Keyboard trap in the editor (2.1.1, 2.1.2).** Code editors capture Tab. There must be a documented key to leave the editor, and Ctrl+Enter must not clash with screen reader or browser shortcuts.
- **Focus visibility and order (2.4.7, 2.4.3).** Check that default outlines are not removed, and that the first-run popup and settings dialogs trap and return focus properly.
- **Screen reader support (4.1.2, 4.1.3).** Verify which CodeMirror version is used and how it exposes the text. Run output and errors should be announced through a live region. Controls need programmatic names and roles.
- **Double speech.** If the built-in TTS and a screen reader both speak, the reader gets two voices. Add a "I use a screen reader" setting that turns off automatic reading.
- **TTS voices by language.** Voices for ar, uk and fr may not exist on a given device. Detect this and say so plainly instead of staying silent.
- **Text spacing (1.4.12) and zoom (1.4.4, 1.4.10).** Test with line height 1.5, letter spacing 0.12em and word spacing 0.16em, then 200% and 400% zoom. Fixed-height editor lines, blurred lines and a two-pane layout are the likely breakage points.
- **Proportional fonts for Python.** OpenDyslexic, Lexend and Nunito are proportional, and Python indentation is syntax. Add visible indent guides and an optional whitespace marker, and check whether monospace variants of the bundled fonts exist and are licensed for bundling (I am not certain).
- **Font loading.** Bundled fonts should not cause invisible text or layout jumps on load. Check font-display and the fallback stack.
- **Right-to-left.** The test checks `<html lang="ar">` but not `dir`. The UI should be right-to-left while the editor and run output stay left-to-right.
- **Motion.** Check the CSS honours prefers-reduced-motion, and that the caret blink rate can be turned off in settings.
- **Blur mode.** I am not certain how an auditor would rate deliberately blurred text. Keep it off by default, never blur the error line or output, and let the reader set the strength.
- **Headings and landmarks (1.3.1, 2.4.1).** One h1, landmark regions, a skip link to the editor, and a unique page title per state.
- **Run timeout.** The 10-second limit must be explained in plain words when hit, and be adjustable in settings.
- **Evidence for dyslexia fonts is mixed** to my knowledge. Verify against primary sources before making claims, and keep reader choice and spacing controls central.


## 4. Things to avoid

- Claiming "fully accessible" or "WCAG compliant" in the README or repo description before an audit record exists in docs/.
- Blur on by default, or blur applied to errors, output or the active line.
- Gradient text, glows, animated backgrounds, parallax, bounce or elastic easing, and animation of layout properties. This repeats AGENTS.md; keep enforcing it.
- Cream, beige or purple as the default look. Offer cream as a selectable theme only, as AGENTS.md already says.
- Pure black on pure white as the only high-contrast choice. Reader preference varies, so make it a setting.
- Text below 16 px by default, justified text, all-caps, long italic runs, underlined non-links, and prose lines wider than about 70 to 80 characters.
- Contrast below 4.5:1 for text or below 3:1 for UI components and focus indicators, in any shipped theme.
- Colour-only meaning for errors, success or token types.
- Auto-playing speech, sound effects, or reading on every keystroke.
- Messages that disappear on a timer, tooltips as the only place for instructions, and pop-ups that appear unprompted. Applying updates on exit, as app.py does now, is the right pattern.
- Fixed-height lines or containers that clip when text spacing or size increases.
- Runtime downloads of fonts or scripts from a CDN, and any analytics or tracking.
- Sending a learner's code or errors to a cloud TTS service without a clear opt-in. This applies to ReciteMe if it is added.
- Gamification: streaks, badges, leaderboards, countdown timers, confetti.
- Shipping more UI languages without review by a fluent speaker.
- Starting P2 features before the P0 items are done.
