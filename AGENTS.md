# AGENTS.md — AccessibleIDE (Dyslexia IDE)

## Project Overview

AccessibleIDE is a fully accessible, open-source IDE prioritizing dyslexic and neurodivergent learners. Python-first, with dyslexia-friendly fonts, configurable focus/blur modes, text-to-speech, plain-English errors, and customizable syntax highlighting.

- **Authoritative spec:** `accessible-ide-requirements.md` (root) — read this before planning any feature. The MVP feature checklist is in section 10.
- **Status:** Shipped. Flask web app and Windows `.exe`; version 1.0.0.
- **Live site:** https://accessible-coding.duckdns.org, hosted on Oracle Cloud. Pushing to `main` runs `.github/workflows/deploy.yml`, which pulls on the server and restarts `accessible-coding-py`.

## Repository Layout

```
accessible-coding/
├── app.py                         # Desktop entry point (Flask + WebView2)
├── wsgi.py                        # Web entry point for gunicorn
├── src/accessible_ide/
│   ├── assets/fonts/              # Bundled fonts
│   ├── i18n/                      # en, hi, fr, es, ar, uk catalogues
│   ├── static/css/style.css       # Design tokens and component styles
│   ├── static/js/app.js           # Editor, settings, setup, TTS, theme logic
│   ├── templates/index.html       # The server-rendered page
│   ├── routes.py                  # Routes, themes, config validation
│   ├── shell.py                   # Python shell sessions
│   └── trace_runner.py            # Line-by-line variable trace
├── tests/                         # Python tests and the DOM harness
└── README.md
```

The code exists and is tested. Read the surrounding code before changing it; do not scaffold a second structure beside it.

## Key Constraints (from requirements)

- **MVP target:** ~1 month; ship incrementally (semantic versioning from 0.1.0), not one big v1.
- **Platforms:** Browser web app first, Windows `.exe` (PyInstaller) second; Linux later. Offline-first — all work saved locally.
- **Language support:** Python only for MVP. Multi-language is future work.
- **Stack:** Flask + Jinja server rendering, vanilla JavaScript, CodeMirror 5. No React, no Node build step, no Tailwind, no bundler. Settings are local JSON, saved through `routes.py`.
- **UI library:** HeroUI v3 is not used. It requires React 19 and Tailwind CSS v4, which this app does not have. Do not add HeroUI, React or Tailwind to the server-rendered page; a mixed runtime would break the no-JavaScript setup screen, the token-based themes and the accessibility tests. If a React surface is ever approved, it must be a separate, scoped migration with its own build step, not an island inside `index.html`.
- **Storage:** Local JSON/TOML config; cloud sync (Google Drive/OneDrive) is optional and opt-in only.
- **Accessibility bar:** WCAG 2.1 AA minimum. Every UI change should be checked against this.
- **License/repo:** Open source (MIT/GPL/Apache 2.0), public GitHub from day 1. Solo development; external PRs require permission and review-then-merge.
- **Priority rule:** Reliable uptime > fancy features.

## Working Agreements

- Prefer plain-language, accessible UI copy everywhere — error messages must be jargon-free English.
- Persist user preferences (fonts, themes, blur config) to the config store; never hardcode them.
- Dyslexia-friendly fonts are bundled, not downloaded at runtime (OpenDyslexic, Atkinson Hyperlegible, plus Comic Sans/Courier New options and user-uploaded `.ttf`/`.woff`).
- Validation is user-feedback-driven: iterate feature → test with dyslexic users → refine → deploy.
- Deployment: push to GitHub and update the hosted site on each feature completion.

## UI System — HeroUI principles without the HeroUI runtime

HeroUI v3 is React-only, so this app keeps Flask/Jinja and applies the same design principles in native HTML and CSS. Do not add the HeroUI package, React or Tailwind. When changing the UI:

- **Semantic intent:** one primary action per context (Run). Everything else is secondary or tertiary. A toggle uses `aria-pressed` or `aria-expanded` for its state, never colour alone.
- **Accessibility as foundation:** use native buttons, fieldsets, labels, `<details>`, and real radio groups before reaching for ARIA. Every target is at least 44px.
- **Progressive disclosure:** start with the common settings and keep refinements such as the advanced code colours inside a disclosure. Do not make a reader scan a wall of controls.
- **Predictable components:** one `.btn` family, one size scale, one focus ring, one disabled treatment. A button looks and behaves the same wherever it sits.
- **Composition over configuration:** reuse the tokens in `static/css/style.css` and the existing component classes rather than adding a second styling system.
- **Feedback:** every state has a visible and spoken version. Disabled, hover, focus, active and error states are all styled, and none of them hides the label.
- **Continuity:** a change must survive every font, all six languages and RTL, every theme including Custom, high contrast, the chosen text size and spacing, reduced motion, and a screen reader.

## Design Quality Bar — no AI slop

This app is used by people who will notice a decorative choice and be distracted by it. Machine-generated design is also the most likely thing to *hurt* a dyslexic reader: animated backgrounds, low-contrast text, and moving type all compete with the code. The bar below is a rejection list, not a wish list. A change that trips any of it is wrong even if it looks good.

**Do not use**

- Cream or beige backgrounds, purple and violet palettes. These are the fingerprints of generated design. Cream is not banned outright, because a reader may need it and a custom theme may land on it: the ban is on *shipping* it as the default look. The page, the panels, and the editor background do not start cream. Where cream appears, it is because the theme table in `routes.py` offers it on purpose or the reader picked it, and either way the colours are measured against AA.
- Gradients on headings or any other text. Gradient text fails contrast in ways that are hard to see in a screenshot and impossible to read for some readers.
- Side tabs, rounded-border accent stripes, icon-tile stacks, nested cards, or cards flush against a viewport edge.
- Bounce and elastic easing, hover image zoom, marquees, pulsing dots, blinking cursors. Also anything animated by `width`, `height`, `top`, or `left` — animate `opacity` and `transform` only.
- Glowing accents, radial halos, and spotlight glows in dark mode.
- Oversized headings, tight negative letter-spacing, uppercase eyebrow chips, kicker lines above headings, numbered section markers, italic serif hero text.
- Thin borders combined with wide drop shadows, repeating-stripe backgrounds, grid-paper backgrounds.
- Illustrations assembled from shapes, organic `clip-path` cuts, and raster images that carry no information the words do not.

**Copy**

- No em-dash overuse. No aphorisms, no "theater" phrasing, no marketing words in an app that is a tool. Write the sentence a colleague would write.

**Typography and layout**

- One type hierarchy, taken from the existing tokens in `static/css/style.css`. Do not introduce a font that is not already bundled.
- Body text is never small, never justified, and never all-caps with wide letter-spacing. Headings step up one level at a time; no skipping.
- Keep line length readable and padding consistent between like elements. Cramped padding and uneven heading rhythm are defects, not preferences.

**Non-negotiable**

- WCAG 2.1 AA, measured rather than eyeballed. `tests/test_contrast.py` is the arbiter and must pass before any visual change lands.
- No layout shifts, clipped overflow, or text that can be pushed out of its container.
- No script errors, broken images, content hidden at rest, or the same text repeated inside one container.
- Anything that drifts from the project's own tokens (fonts, colours, radii, sizes) is drift, even when it is an improvement.

If a design idea is only worth doing because it looks expensive, skip it. What earns its place here is what makes the code easier to read.

## Next Steps

1. Test the custom colour grid and Advanced disclosure with dyslexic readers.
2. Add more text-to-speech options and configurable blur zones.
3. Keep the Oracle Cloud deployment green on every push to `main`.
4. Keep `README.md` accurate when features, languages or the live URL change.
