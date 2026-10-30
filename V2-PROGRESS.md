# Progress towards v2

Last updated: 2026-10-30
Current release: **1.1.0** (tagged 2026-10-22). v2 is not released yet; the work below is on `main` and on the live site.
Live site: https://accessible-coding.duckdns.org (Oracle Cloud, deployed from `main` by `.github/workflows/deploy.yml`)

This file is the working checklist between v1 and v2. It records what is shipped, what was done in the latest pass, what is still open, and what still needs a human to confirm. Update it when a feature lands or the plan changes.

---

## 1. What is shipped in 1.0.0

| Area | State |
| --- | --- |
| Editor | CodeMirror 5, Python mode, active line, bracket matching, 10 second run timeout |
| Themes | High Contrast, Dark, Pastel, Light, Ocean, Forest, White, AMOLED, Red, Orange, Yellow, Green, Blue, Indigo, Violet, plus Custom |
| Custom theme | Hex grid, native colour picker and hex text field for page, background, text and selection |
| Code colours | Keyword, string, comment, number and function live under Settings then Colours then Advanced |
| Onboarding | Language, font, theme (with an extra custom-colour step), what the app does. Custom code colours are carried through hidden inputs, not asked on the startup screen |
| Fonts | OpenDyslexic (default), Atkinson Hyperlegible, Lexend, Nunito, Almarai, Mukta, plus running system fonts and user uploads |
| Text controls | Size, line height, letter spacing and weight, separately for editor, output and shell |
| Languages | English, Hindi, French, Spanish, Arabic (right to left), Ukrainian |
| Text to speech | Output, errors, hover and click reading, voice choice, speed, hover delay |
| Screen readers | Native landmarks, live regions, focus return on dialog close, setup steps announce themselves, no-JS readable setup and dictionary |
| Errors | Plain-English translations of Python errors, with the original kept |
| Shell and trace | Python shell sessions, line-by-line variable trace table |
| Packaging | Windows `.exe` (PyInstaller, Inno Setup), browser build, gunicorn entry point |
| Storage | Local JSON config, offline first, no account |

---

## 2. Done in this pass

- Applied HeroUI v3 design principles without the HeroUI runtime (React and Tailwind are not in this app, and adding them would break the no-JavaScript setup screen and the token-based themes). Written down in `AGENTS.md` under **UI System** so the next change follows it.
- Toolbar reduced to four clear groups: run tools, file tools, editor tools, and reference plus settings. The trace button no longer sits in a group of its own.
- One button family: every `.btn`, `.btn-small` and `.tool-select` now clears the 44px target floor. Before this pass `.btn-small` and the toolbar select were 40px.
- One disabled treatment for buttons that keeps the label readable. Measured at 11.89:1 against the background, so a disabled control is still legible instead of faded out.
- The Settings and Dictionary triggers now carry `aria-expanded` and `aria-controls`, kept in sync on open, close and Escape. A screen reader hears the state of the dialog it can open.
- `README.md` encoding repaired (the file held real mojibake, not just display noise), accessibility section added, stale feature list corrected, live URL replaced, installer URL updated.
- `AGENTS.md` corrected: it still described the project as pre-development and listed the stack as undecided.
- The reading ruler landed under **Settings → Reading**, off by default. It shades the line under the pointer through a CodeMirror line class, so it costs no contrast and never paints over the text.
- `README.md` brought back in line with the shipped app: 15 presets rather than 6, the per-colour reset, the reading ruler, the per-pane toolbars, and a short standards note for the WCAG 2.2 items. `AGENTS.md` now names those items in the accessibility bar so the next change cannot quietly drop them.
- Committed as `ca6c6fb`, *Apply RTL at the document, add a reading ruler, close WCAG 2.2 gaps*.

### Deployment pass

- **The live site was down from 29 October until 30 October.** The server rebooted, PM2 had never been told to save its process list, so nothing came back. Deploy run #8 then failed against the name `accessible-coding-py`, which does not exist, and the workflow still had no way to tell that the site was dead.
- `run.sh` loads `.env` and runs gunicorn, so `SECRET_KEY` and `PORT` actually reach the app and the production server replaces the Flask development server. PM2 starts the process from it. `.env.example` documents the variables; `ALLOWED_HOSTS` was dropped, it was never read.
- `deploy.yml` restarts the process that exists, starts it if it is missing, runs `pm2 save` so a reboot resurrects it, and fails the run when `/health` does not answer. A green deploy now means a serving site.
- **The boot unit was broken too.** `pm2 startup` had written `Type=forking` with `PIDFile=/home/opc/.pm2/pm2.pid`, which systemd (root, under SELinux) cannot read, so it timed out after 90 seconds and restarted in a loop while the app came up anyway. It is `Type=oneshot` with `RemainAfterExit=yes` now, kept in `deploy/pm2-opc.service`, and a stop/start of the unit proves it resurrects the process from a dead daemon.
- Committed as `c7196de`, *Keep the live site up across reboots*.

### Accessibility pass 2

- **Arabic right to left was not applied at all.** `direction` was computed in `routes.py` and handed to the template, and nothing put it on the document, so Arabic claimed to be right to left and rendered left to right. The template now renders `<html lang="ar" dir="rtl">`, and `.CodeMirror` pins `direction: ltr` so the editor, gutter, caret and scrollbar do not mirror Python that is still written left to right.
- **WCAG 2.4.11 (focus not obscured).** The trace window is a floating, deliberately non-modal table, so a control underneath it could take focus with nothing of it on screen. It now closes only when the newly focused control is completely covered by it, and stays open when the control is merely beside it, which keeps the table usable for comparing a row against the code.
- **WCAG 2.5.8 (target size).** `.setup-swatch-cell` was 22x22. It is 24x24 now. `.hex-grid-cell` was already 24.
- **WCAG 2.5.7 (dragging alternatives)** and **2.4.7** were already met: the pane dividers and the trace grip both answer the arrow keys, and the grip's Home key puts the window back.

### How this pass was checked

- `python -m unittest discover -s tests -t .`: 713 tests, all passing.
- `node tests/dom_harness.js`: 32 labelled checks passing, plus three new focus-not-obscured checks.
- New tests: `test_html_lang_attribute_is_dynamic` now asserts the `dir` attribute, `test_arabic_renders_right_to_left` renders the page in Arabic, `test_the_editor_keeps_code_left_to_right` pins the editor direction, `ReflowCssTests` covers the 320px fallback, and `TargetSizeCssTests` measures both colour grids.
- Ran the app on port 5077 with a throwaway profile. Setup, settings and dictionary dialogs open and close, `aria-expanded` flips correctly, no console errors.
- Computed styles confirmed at runtime: every toolbar control renders 50px tall, disabled trace stays 50px, disabled contrast 11.89:1, primary button 14.29:1.

### Not checked

- Not re-tested with dyslexic readers after these changes.
- No screen-reader pass with NVDA, JAWS or VoiceOver in this pass.
- No visual screenshot review; layout was verified by DOM metrics, not by eye.
- The deployed site only reflects these changes after the workflow finishes on `main`.

---

## 3. What needs doing for v2

### P0: finish the accessibility promise

- [ ] Screen-reader pass on Windows (NVDA) and macOS (VoiceOver): setup wizard, settings dialog, dictionary search, trace table, shell, error output. Still needs a human with a screen reader; the markup is ready for it.
- [x] Keyboard-only pass that covers every new control, including the hex grid and the Advanced disclosure. The hex grid is native radio inputs inside their labels, so Tab reaches the group and the arrow keys move within it with no script. Advanced is a `<details>`, so Enter and Space open it. Both pane dividers and the trace grip answer the arrow keys. A hands-on pass with a keyboard is still worth doing, but nothing here depends on a pointer.
- [x] WCAG 2.2 additions beyond 2.1 AA:
  - 2.4.11 focus not obscured: the floating trace window now closes when the control that takes focus is completely underneath it.
  - 2.5.7 dragging alternatives: already met by the dividers and the trace grip.
  - 2.5.8 target size: the setup colour squares were 22px and are now 24px; every other target is already at least 24px.
  - 3.2.6 consistent help: this is one page, and the Dictionary and Settings triggers sit in the same place in the toolbar at every width, so the help mechanism never moves.
- [x] Check Arabic right-to-left layout inside CodeMirror, not only around it. The document is now `dir="rtl"` and the editor pins `direction: ltr`: code, gutter, caret and scrollbar stay in the same place in every language.
- [x] Test with 200% browser zoom and a 320px wide viewport; record any clipped overflow. The narrow layout stacks the panes, moves the settings section list above the panel and hides the dividers; `ReflowCssTests` fails if that fallback is lost. No fixed width above 320px remains.
- [x] Confirm reduced motion is respected for every transition, not only the ones covered by tests. Both rules are `body[data-reduce-motion='true'] *` and the `:before`/`:after` pseudos, so they cover every transition and animation in the file rather than a list that can drift.

### P1: reading comfort

- [ ] Let readers adjust the blur radius and choose which panes blur in focus mode (today the mode is fixed presets).
- [x] Add a reading ruler option (a horizontal highlight that follows the pointer) for line tracking. It lives in **Settings → Reading**, is off by default, and shades the line under the pointer with `background` only, so it costs no contrast and never draws over the text. The caret and the keyboard are untouched: this is a pointer aid, not a second cursor.
- [x] Tune the custom theme contrast nudge. A failing pick now names the colour the editor uses instead, taken from the same derivation that paints the theme, so the message cannot drift from what is shown. The background, page and selection fields stopped being flagged: they were measured against the background they are not drawn on, so "Editor background" read "Too low" the moment any other field was touched.
- [x] Allow exporting and importing settings as a small JSON file, so a reader can carry them between machines. The existing Settings backup (`/api/config/export`, `/api/config/import`) already carries every setting including the custom theme and is validated exactly as the panel is, so no separate theme file was needed.
- [ ] Review the font list against user demand; add any missing open-licence dyslexia font with its licence file.

### P1: speech and language

- [x] Per-language voice selection, so switching to Hindi or Arabic does not keep an English voice. The voice is chosen per language and gender from the system list, and `tests/dom_harness.js` holds the names it must pick for all six languages.
- [ ] Remember the last spoken position in the output, so "read from here" is possible after a long run.
- [ ] Add pause and resume for long files instead of stop and restart.
- [ ] Complete translation review for all six catalogues by a native speaker; the current strings are consistent but not professionally reviewed.

### P2: editor and runtime

- [ ] Large file handling: measure typing latency at 5,000 and 20,000 lines, then decide whether to add a lazy mode.
- [ ] Multi-file projects (open a folder, not a single file). This is the largest single change in v2 and needs its own design pass.
- [ ] Optional opt-in cloud sync (Google Drive or OneDrive). Offline remains the default and the only mode that works without an account.
- [ ] Linux build and packaging.
- [ ] Python-only remains the contract; any second language is a v3 question.

### P2: operations

- [x] Add a health endpoint and a deploy check that fails loudly when the Oracle service does not come back up. Shipped: `/health` existed but nothing checked it. `deploy.yml` now polls it and fails the run, and `pm2 save` keeps the process across a reboot.
- [x] Fix the missing `/favicon.ico` (was a 404 on every load). Shipped: the app serves a real icon.
- [ ] Keep the Windows auto-update path tested against a real signed release, not only in unit tests.
- [x] Add a short changelog so readers can see what changed without reading commit history. Shipped as `CHANGELOG.md`: v1.0.0, v1.1.0, and an Unreleased (v2) section written from the commits since v1.1.0.

---

## 4. Open decisions for v2

1. Multi-file projects: tabbed editor in the existing page, or a file tree in a second pane? Decide before writing code.
2. Cloud sync: build it, or document a manual export and drop the promise? It is currently listed as optional and nothing depends on it.
3. Reading ruler and blur radius: do they belong in Settings, or in the per-pane mini toolbar? Avoid growing Settings into a wall of controls. **Reading ruler is settled**: it is a single switch under Settings → Reading, next to the text size and spacing controls it belongs with. Blur radius is still open.
4. Whether to publish a public roadmap, given the project is solo-maintained and dates slip.

---

## 5. Definition of done for v2

A feature is done when all of these hold:

- It works in every font, all six languages, both text directions, every theme including Custom, and high contrast.
- It clears WCAG 2.1 AA in `tests/test_contrast.py`, and the new WCAG 2.2 items above where they apply.
- It is reachable and operable by keyboard and announced correctly by a screen reader.
- It adds no layout shift, no clipped text and no console error.
- It has a test that would fail if the behaviour regressed.
- It is documented in `README.md` and, where it changes how the app is built, in `AGENTS.md`.
