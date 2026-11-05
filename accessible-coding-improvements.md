# AccessibleIDE: Review, Rating and Next Steps

Source reviewed: https://github.com/hot-hilux21/accessible-coding (code and README, read from the public repo; the live app and a screen reader were not tested).

## Rating: 7.5 / 10 (beta v0.1.0)

Strong points
- Clear purpose for dyslexic and neurodivergent learners, with real features: OpenDyslexic and other reading fonts, focus mode, TTS, plain-English errors, four themes.
- Solid semantic markup: `lang` set from locale, skip links, `role="switch"`, `aria-live` and `role="alert"` for output and errors, `aria-describedby`/`aria-label` on controls.
- Accessibility is tested in code: contrast tests, font tests, i18n tests, a DOM harness, and CI that runs tests before building releases.
- Uses `:focus-visible` and `prefers-reduced-motion`, and removes no outlines without replacement.
- Languages beyond English (fr, es, hi, ar), MIT license, documented requirements.

Gaps and risks
1. Not verified with real assistive technology. Run NVDA and JAWS on Windows, and test the editor with keyboard only.
2. The code editor (CodeMirror) needs a check for keyboard traps and whether screen readers announce the current line, indentation, and errors.
3. Windows-only desktop app (WebView2); the web app path should be tested on mobile and with zoom at 400%.
4. The `.exe` is not code-signed, so Windows SmartScreen warns users. This is a barrier for classmates.
5. Run output and errors should be announced through a live region; confirm this with a screen reader.
6. Real user testing with dyslexic and neurodivergent learners is listed as welcome but not yet documented. Add a test plan and feedback results.
7. Hosting: the README gives accessible-coding.onrender.com, but you mentioned accessible-coding.render.com. Confirm which URL is live and keep README and links consistent.
8. The README says the code was "vibe-coded". Consider adding a short note on what was reviewed and tested by hand, since accessibility claims need evidence.
9. Smoke tests and unit tests did not run in my environment (pytest is not installed here), so I have not confirmed the test results.

## Questions for you
1. Which URL is the live app: accessible-coding.onrender.com or accessible-coding.render.com?
2. Have you tested with NVDA or JAWS yourself? If so, what broke?
3. Who are your test users, and can you run a small session with them?
4. Is code signing something you can afford or plan for?
5. Should v0.2 focus on file save/open first, or on accessibility fixes first?

## Next steps
1. Screen reader test pass (NVDA, Windows) on editor, run button, errors, settings. Record results in docs/.
2. Keyboard-only walkthrough and fix any traps or missing focus states.
3. Confirm live URL and update README links.
4. Add a short user testing plan and feedback form to docs/.
5. Decide on code signing or add clear install guidance for SmartScreen.
6. Run the full test suite locally (install pytest) and record the results.
7. Plan v0.2 priorities from the questions above.

## Verification note
I have not verified the live site, rendered UI, or screen reader behaviour. Check standards (WCAG 2.2 AA) and tool behaviour against current official documentation.
