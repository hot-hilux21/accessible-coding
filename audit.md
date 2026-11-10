# Jojo Code — Product, Website & Engineering Audit

**Audit date:** 5 November 2026  
**Repository:** https://github.com/hot-hilux21/jojo-code-ide  
**Live website:** https://accessible-coding.duckdns.org/  
**Scope:** Public repository overview/README, published live-site interface text, and product documentation visible without a connected GitHub account.

> **Important scope limitation:** This is a public-surface and product audit, not a completed line-by-line source-code, penetration, browser-interaction, or assistive-technology audit. GitHub exposed the repository structure and README, but its source directories/raw files could not be retrieved in this review session. A GitHub connection would allow a deeper inspection of implementation files, tests, workflows, and history. Findings below are labelled so that documented strengths are not mistaken for independently verified implementation.

---

## 1. Executive summary

Jojo Code has a strong and unusually coherent purpose: a Python-first learning IDE designed around reading comfort, focus, plain-English feedback, and user-controlled presentation. The project already describes a substantial feature set: adjustable fonts and spacing, focus modes, a reading ruler, themes, text-to-speech, sound cues, keyboard controls, screen-reader support, a Python dictionary, and Windows/browser delivery.

The most promising aspect is that accessibility is treated as part of the product rather than as a cosmetic overlay. The controls are granular, and the app recognises that the editor, output, shell, and surrounding interface can need different presentation settings.

The biggest risks are not a lack of features. They are:

1. **The browser execution trust boundary.** The README says browser-submitted code is sent to a shared server and that imports such as `os` and `subprocess` are refused. An import restriction alone must not be treated as a secure Python sandbox.
2. **Evidence behind accessibility claims.** The project describes WCAG 2.1 AA as its floor and selected WCAG 2.2 additions. It needs a criterion-by-criterion evidence matrix and real keyboard/screen-reader/manual testing before making broad “fully accessible” claims.
3. **A very large settings surface.** Many options are valuable, but the number of controls can itself become cognitively demanding. Progressive disclosure, good presets, search, and task-based setup can make the power easier to use.
4. **The need for independent user testing.** Font preferences and reading aids are individual. The product should avoid implying that one font or one visual treatment works for every dyslexic or neurodivergent person.
5. **A source-level review remains outstanding.** The public README and rendered website do not establish that every described feature works correctly, safely, or consistently across browsers and the Windows build.

**Overall assessment:** promising and thoughtfully scoped; continue development, but prioritise execution isolation, accessibility verification, and usability testing over adding lots of new visual features.

---

## 2. What is already right

### 2.1 Product direction

- **Clear audience and use case.** Python-first coding for learners is a manageable starting point, rather than trying to compete with every professional IDE.
- **Accessibility is integrated into the workflow.** Reading, focus, output, shell, and settings are all considered.
- **User choice is extensive.** Separate controls for editor/output/shell are better than forcing one global font or spacing choice.
- **The first-run wizard is a good idea.** A preview of the selected font and a persistent Back/Next/Skip area reduce uncertainty.
- **Reset is discoverable.** A reset option is particularly important when a user has selected a colour or font that makes the interface difficult to read.
- **Plain-English errors retain the original error.** This is a good teaching pattern: explain the issue without hiding the real Python diagnostic.
- **The reading ruler is described as non-invasive.** Keeping it separate from the caret and keyboard interaction is the right design intention.
- **Reduced-motion and sound controls exist.** These recognise that motion and sound can help some users and distract others.
- **The project documents local versus hosted execution.** The README distinguishes the Windows app, where code runs locally, from the browser version, where code is sent to the server.
- **There is a test entry point.** The README documents Python unit tests, a smoke test, and a DOM harness.
- **The project has a licence and credits.** This is important for a project using third-party libraries, fonts, and other assets.

### 2.2 Website and interface

The live interface exposes the core IDE actions (Run, Stop, Trace table, Save, Open, Python Shell, Dictionary, Settings) and a substantial settings area. The settings are grouped into understandable topics such as Language, Font, Reading, Colours and contrast, Focus, Motion, Sound, Keyboard, Reading aloud, Updates, Reset, and About.

Positive details visible in the live interface include:

- Font preview text before choosing a font.
- Separate font application to code, output, shell, and the rest of the app.
- Adjustable font size, weight, line height, letter spacing, and word spacing.
- A reading-ruler control.
- Theme and contrast controls, plus custom colours.
- A reduced-motion option.
- A setting to show button labels rather than icons alone.
- Configurable Run and Stop keyboard combinations.
- Voice selection, speech speed, and a sample-reading control.
- Settings backup and restore controls.
- A reset action that says it leaves the user's code alone.

These are sensible capabilities. Their actual accessibility and reliability still need interactive testing.

---

## 3. Problems, risks, and things to verify

Severity definitions:

- **P0 — Critical:** address before exposing the affected capability to untrusted users.
- **P1 — High:** important for safety, accessibility, or core usability.
- **P2 — Medium:** meaningful quality or maintainability improvement.
- **P3 — Low:** polish or optional enhancement.

### P0 — Browser Python execution must have a real security boundary

The README states that browser code is sent to the hosting server and run there, and that imports such as `os` and `subprocess` are refused. This is an important privacy and security disclosure, but it is not enough to establish that execution is safe.

A Python import blocklist is not a security sandbox. Python is introspective, and dangerous capabilities can sometimes be reached indirectly. Even code that cannot escape a process can consume memory, CPU, file descriptors, processes, or output bandwidth.

**Required actions:**

- Run each submitted program in a disposable, isolated worker/container or equivalent hardened sandbox.
- Run as an unprivileged user; never execute submitted code in the Flask/Gunicorn web worker.
- Disable network access unless a carefully designed feature explicitly needs it.
- Use a read-only base filesystem and a fresh, size-limited temporary workspace.
- Enforce CPU, memory, process-count, file-size, output-size, and wall-clock limits outside the Python code itself.
- Kill the entire process tree on timeout or cancellation.
- Apply syscall/container restrictions where supported; do not rely on Python-level checks.
- Keep secrets, environment variables, deployment credentials, and host files out of the execution environment.
- Rate-limit requests and protect the service against concurrent-run exhaustion.
- Log operational metadata without unnecessarily retaining submitted source code or personal data.
- Test hostile examples in a controlled environment before enabling public execution.

**Acceptance test:** a malicious or resource-exhausting program cannot read host secrets, access other users' files, reach internal services, spawn unlimited processes, or prevent other users from using the service.

If the browser runner is not already isolated at the operating-system/container level, treat this as the first engineering priority.

### P1 — Accessibility claims need a transparent evidence matrix

The README describes WCAG 2.1 AA as the baseline and selected WCAG 2.2 requirements. That is a useful target, but a passing contrast test does not demonstrate WCAG conformance.

**Required actions:**

- Publish a `docs/accessibility-conformance.md` matrix listing each applicable WCAG 2.2 A/AA criterion, status, evidence, test method, and known limitation.
- Separate **automated checks**, **manual checks**, and **user testing**.
- Test the complete app, not just the editor or landing view.
- Test dialogs, settings, setup wizard, shell, trace table, file controls, error states, and interactive prompts.
- Include keyboard-only testing, browser accessibility-tree inspection, and screen-reader testing.
- Test at 200% and 400% zoom, narrow viewports, high contrast/forced-colours mode, and text resizing.
- Verify visible focus, focus order, focus not being obscured, and focus return after closing dialogs.
- Check contrast for text, syntax tokens, focus indicators, selected states, borders, icons, and controls—not only body text.
- Avoid saying “fully accessible” or “WCAG compliant” until the full conformance requirements have been evaluated.

**Suggested target:** WCAG 2.2 AA, with a published statement of what was and was not tested.

### P1 — Do not assume dyslexia-friendly means one font fits everyone

OpenDyslexic, Atkinson Hyperlegible, Lexend, Nunito, Andika, and user-supplied fonts provide choice. That is good. However, there is no universal dyslexia font, and a font that helps one person may be uncomfortable for another.

**Required actions:**

- Present fonts as personal preferences, not treatments or guaranteed improvements.
- Keep a readable system-font option and make switching back easy.
- Test punctuation, brackets, indentation, `1/l/I`, `0/O`, underscores, operators, and long code lines in every bundled font.
- Ensure custom font loading cannot break layout or make controls unreadable.
- Include a clear fallback if a font file is invalid or fails to load.
- Test font choices with actual learners, including people who prefer ordinary monospace fonts.

### P1 — Settings complexity could become its own accessibility barrier

The number of settings is impressive, but a new learner may find the settings panel overwhelming. A user should not need to understand typography, contrast ratios, focus fading, or speech configuration before writing their first program.

**Improvements:**

- Add a small set of optional starting profiles, for example **Comfortable reading**, **Low distraction**, **High contrast**, **Screen reader**, and **My own settings**.
- Explain that profiles are starting points and can be changed.
- Keep the existing individual controls available under Advanced settings.
- Add settings search.
- Group related controls and use short descriptions with examples.
- Avoid opening every advanced colour control by default.
- Make it easy to undo the last setting change as well as reset everything.
- Offer a “restore recommended defaults” option that is distinct from a full reset.

### P1 — Hosted execution privacy needs to be prominent at the point of use

The README explains that browser code is transmitted to the server. The live app should repeat this information before the first hosted run, not rely on a user reading GitHub documentation.

**Improvements:**

- Display a short, plain-language notice beside the Run action or on first use: browser code is sent to the server to execute.
- Link to the privacy policy from that notice.
- State whether source code, input, output, IP addresses, or operational logs are retained, and for how long.
- State who operates the server and how users can report a security issue.
- Make the Windows/local execution distinction equally clear.
- Do not imply that browser execution is private or local.

### P2 — The website's initial and error states need a deliberate review

The text exposed by the live page includes a “Something went wrong” panel and controls such as “Clear the shell” and “Close”. This may be a hidden dialog or a state included in the page markup rather than an error actually displayed on initial load. It should be checked in a real browser.

**Verify:**

- On a fresh visit, is an error panel visibly displayed before the user runs anything?
- If hidden, is it also hidden from keyboard navigation and the accessibility tree?
- Does it have the correct dialog semantics, accessible name, and focus behaviour when opened?
- Does closing it return focus to the control that opened it?
- Are errors announced once, clearly, without repeated or competing live-region announcements?

Do not treat the text extraction alone as proof of a live bug.

### P2 — Voice selection wording should avoid guessing gender

The live settings text says computers do not label voices male or female and that the app guesses from voice names. Guessing a voice's gender from its name can be inaccurate and may be confusing.

**Improvements:**

- Show the voice's actual system-provided name.
- Provide a Preview button next to each voice.
- Let users choose by voice name, language, and available accent metadata.
- Avoid assigning a gender label unless the platform explicitly supplies reliable metadata and the user wants to see it.
- Explain when voices depend on Windows/browser-installed speech engines.

### P2 — Make the website and README feature descriptions stay in sync

The README and live app expose many features, but the README, running version, Windows build, and browser build should be checked against one shared release checklist.

**Improvements:**

- Add a version/build identifier to the About panel and a visible commit or release identifier to deployment diagnostics.
- Document which features are local-only, browser-only, Windows-only, or dependent on system voices.
- Test every release against the same feature checklist.
- Make the release notes describe user-visible changes and known limitations.
- Add a deployment health check and a rollback procedure.

### P2 — Responsive and small-screen usability needs hands-on testing

The IDE has multiple panes, toolbars, a shell, a trace table, and a large settings panel. The text view alone cannot confirm whether these work well on smaller screens.

**Test:**

- 320 CSS-pixel viewport width.
- 200% and 400% zoom.
- Portrait and landscape tablet layouts.
- Touch targets and spacing.
- Whether the editor remains usable without horizontal page scrolling.
- Whether settings panels and dialogs fit without trapping the user.
- Whether the shell/output can be reached without dragging or precision gestures.

### P2 — Code editor accessibility requires specialised testing

Code editors are more complex than normal text fields. CodeMirror's keyboard model, cursor, selection, line numbers, autocomplete (if added), and screen-reader announcements need testing as a complete interaction model.

**Test:**

- Tab/Shift+Tab indentation behaviour and whether it can be changed.
- Arrow-key navigation and selection.
- Home/End and Ctrl/Cmd+Arrow behaviour.
- Copy, paste, undo, redo, and select-all.
- Whether screen readers announce the current line and relevant editor state without excessive repetition.
- Whether focus fading and the reading ruler follow keyboard navigation as well as pointer movement.
- Whether syntax highlighting remains understandable without colour.

---

## 4. Features worth adding

These are product recommendations, not claims that the features are currently absent from every branch or build.

### Highest-value additions

| Feature | Why it matters | Priority |
|---|---|---:|
| Guided first Python lesson | Helps a new learner move from opening the IDE to running their first program | P1 |
| Step-by-step debugger | Makes program flow and variable changes easier to understand | P1 |
| Error explanation with a “show original error” toggle | Supports learning without hiding the real diagnostic | P1 |
| Autosave and crash recovery | Prevents losing work | P1 |
| Local project/folder support | Makes the IDE useful beyond one-off scripts | P1 |
| Accessible keyboard-shortcut reference | Makes keyboard operation discoverable | P1 |
| In-app accessibility feedback/report issue | Gives users a route to report barriers | P1 |
| Secure hosted execution isolation | Protects the service and its users | P0 |

### Learning and dyslexia/dyscalculia support

- **Visual execution timeline:** show which line ran, what changed, and what happened next.
- **Variable inspector:** display variable names, types, and values in a readable table.
- **Number-format helper:** optionally group long numbers, explain decimal places, and distinguish decimal points from thousands separators without changing actual code values.
- **Trace table explanations:** explain what each column means and why a row appeared.
- **Worked examples:** let users run, change, and compare short Python examples.
- **Error-to-example links:** connect common errors to a small example and a safe practice task.
- **Reading-friendly documentation:** short paragraphs, clear headings, literal examples, and consistent terminology.
- **Optional line-by-line reading:** allow the user to move through code and hear one line at a time.
- **Optional indentation guides:** make Python block structure easier to follow without relying only on colour.
- **Configurable punctuation speech:** let users decide whether TTS says symbols such as colon, comma, brackets, and underscore.

### Focus and cognitive accessibility

- **Distraction-free mode:** hide optional panels while keeping essential Run/Stop and recovery controls available.
- **Progressive disclosure:** beginner view first; advanced settings on request.
- **Session goals:** optional small tasks such as “write a variable” or “run a loop”.
- **Break reminders:** optional, quiet, fully configurable, and off by default.
- **Undo last setting change:** easier than resetting all preferences.
- **Stable layouts:** avoid panels moving unexpectedly while the user is typing.
- **No surprise audio:** keep sound and speech opt-in and respect system/browser preferences.

### Developer experience and portability

- **Project templates:** beginner exercises, coursework starter projects, and blank projects.
- **Export/import projects:** a portable project format with clear file boundaries.
- **Python environment indicator:** show the Python version and execution environment.
- **Dependency guidance:** explain unavailable packages and how local installation differs from hosted execution.
- **Test runner panel:** show test results and explain failed assertions in plain English.
- **Git integration (later):** only after the basic project/file workflow is robust and understandable.
- **Extension/API design (later):** keep the core small and expose documented extension points rather than adding every feature directly to the main application.

---

## 5. Engineering and repository improvements

The repository structure is encouraging: separate frontend, Python package, tests, docs, deployment, scripts, and installer assets are visible. The following should be verified in the source before making implementation claims.

### Architecture

- Keep UI state, settings persistence, Python execution, translation, and accessibility helpers separated.
- Avoid a single oversized JavaScript file or route module becoming the home of unrelated features.
- Centralise settings schema, defaults, validation, migrations, and reset behaviour.
- Version the settings format so future releases can migrate old preferences safely.
- Keep shared UI behaviour consistent between the browser and Windows wrapper.
- Make local and hosted execution explicit backends with different security and privacy policies.

### Testing and CI

Add or confirm automated checks for:

- Python unit tests and type/lint checks.
- JavaScript formatting/linting and DOM tests.
- Build and installer smoke tests.
- Settings migration and backup/restore.
- Keyboard navigation and focus management.
- Automated accessibility checks (axe-core or equivalent) on representative states.
- Contrast for every theme and syntax token.
- Internationalisation completeness and right-to-left layout.
- Browser execution security and resource limits.
- Regression tests for error prompts, input prompts, stop/cancel, and concurrent runs.

Automated accessibility tools catch only part of the problem. Manual keyboard and screen-reader testing remains necessary.

### Dependency and release hygiene

- Pin or constrain dependencies deliberately and test upgrades.
- Run dependency vulnerability checks in CI.
- Generate a software bill of materials (SBOM) for releases.
- Keep third-party font and library licences in the credits/licence documentation.
- Sign Windows installers and publish checksums.
- Use GitHub Releases with a changelog and known-issues section.
- Add a security policy (`SECURITY.md`) with a private vulnerability-reporting route.
- Add an accessibility statement or `ACCESSIBILITY.md` explaining the project's accessibility goals and how to report barriers.

### Documentation

Recommended documentation files:

- `SECURITY.md` — threat model, supported versions, and vulnerability reporting.
- `ACCESSIBILITY.md` — accessibility goals, known barriers, testing approach, and reporting route.
- `docs/accessibility-conformance.md` — WCAG 2.2 A/AA evidence matrix.
- `docs/architecture.md` — application components and data flow.
- `docs/execution-security.md` — local versus hosted execution and sandbox design.
- `docs/testing.md` — repeatable test commands and manual test procedures.
- `docs/known-limitations.md` — honest limitations by platform and assistive technology.

---

## 6. Suggested accessibility test matrix

Run these tests on the current browser release and the Windows desktop release. Record browser/OS versions, assistive technology versions, exact steps, expected result, actual result, and evidence.

| Test area | Minimum test | Pass condition |
|---|---|---|
| Keyboard | Complete workflow without mouse | All actions reachable and operable; no keyboard trap |
| Focus | Open/close settings, dialogs, prompts | Focus moves predictably and returns to the opener |
| Screen reader | NVDA + Firefox/Chrome; Narrator + Edge | Controls, labels, errors, prompts, and updates are understandable |
| Zoom/reflow | 200% and 400% | Essential content and controls remain usable |
| Contrast | All presets and custom colours | Text, controls, focus, and states meet applicable contrast requirements |
| Forced colours | Windows High Contrast | Controls and focus remain visible and distinguishable |
| Motion | OS reduced-motion preference and app setting | Non-essential movement is removed or reduced |
| Speech | Voice unavailable, slow voice, speech interrupted | Clear fallback and no blocking interaction |
| Editor | Keyboard-only editing and navigation | Cursor, selection, indentation, and shortcuts work predictably |
| Internationalisation | Arabic RTL plus an LTR language | UI direction changes correctly; code remains LTR |
| Small viewport | 320 CSS px and tablet | No essential control becomes unreachable |
| Hosted runner | Timeout, infinite loop, memory pressure, hostile code | Worker is contained and other users remain unaffected |
| Recovery | Refresh/crash during editing | User can recover saved work where autosave is enabled |

**Suggested human testing group:** recruit a small, varied group of actual learners, including people with dyslexia, dyscalculia, ADHD, and people who use screen readers or keyboard-only navigation. Ask participants to complete real tasks rather than simply rate the appearance. Do not assume that one participant represents an entire group.

---

## 7. Recommended implementation order

### Phase 1 — Safety and trust

1. Verify the hosted runner's isolation architecture.
2. Add operating-system-enforced resource limits and process-tree termination.
3. Make the browser code-transfer notice prominent.
4. Publish the execution and privacy model.
5. Add a security reporting policy.

### Phase 2 — Prove accessibility

1. Create the WCAG 2.2 AA evidence matrix.
2. Test the full application with keyboard and screen readers.
3. Test dialogs, prompts, trace table, settings, and error states.
4. Test zoom, reflow, forced colours, and reduced motion.
5. Fix the highest-severity issues and publish known limitations.

### Phase 3 — Reduce cognitive load

1. Add optional starting profiles.
2. Add settings search and progressive disclosure.
3. Improve beginner onboarding and the first Python lesson.
4. Make keyboard shortcuts discoverable.
5. Test the settings experience with real learners.

### Phase 4 — Improve learning workflow

1. Add autosave/recovery.
2. Improve the trace table and variable inspector.
3. Add a step-by-step debugger.
4. Add project/folder support and templates.
5. Add guided examples and error-learning links.

### Phase 5 — Quality and release maturity

1. Expand CI and regression coverage.
2. Add release health checks and rollback.
3. Keep documentation aligned with the shipped build.
4. Publish an accessibility statement and known limitations.
5. Gather feedback and repeat user testing after major changes.

---

## 8. Final verdict

**Keep the core direction.** The project has a clear reason to exist, and its emphasis on user-controlled reading, focus, and learning support is a genuine strength.

Do not prioritise adding more themes, visual effects, or dozens of settings until the hosted execution boundary and accessibility evidence are solid. The best next version is not necessarily the one with the most features; it is the one that is safe, predictable, understandable, and demonstrably usable by the people it is intended to support.

### Audit confidence

- **Product direction and documented feature set:** medium-high confidence.
- **Live interface content and visible settings:** medium confidence; based on publicly retrievable page content, not hands-on interaction.
- **Accessibility conformance:** not independently established.
- **Source-code correctness and maintainability:** not established; line-by-line source retrieval was unavailable in this review.
- **Hosted runner security:** high-priority risk area requiring source and deployment inspection; no exploit test was performed.

### References

- Repository: https://github.com/hot-hilux21/jojo-code-ide
- Live application: https://accessible-coding.duckdns.org/
- GitHub accessibility page guidance: https://docs.github.com/en/communities/setting-up-your-project-for-healthy-contributions/adding-an-accessibility-page-to-your-repository
- WCAG overview (MDN): https://developer.mozilla.org/en-US/docs/Web/Accessibility/Guides/Understanding_WCAG
- Accessibility tooling and manual testing (MDN): https://developer.mozilla.org/en-US/docs/Learn_web_development/Core/Accessibility/Tooling
- Chrome accessibility guidance: https://developer.chrome.com/docs/modern-web-guidance/guides/accessibility/accessibility
