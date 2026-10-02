# AGENTS.md — AccessibleIDE (Dyslexia IDE)

## Project Overview

AccessibleIDE is a fully accessible, open-source IDE prioritizing dyslexic and neurodivergent learners. Python-first, with dyslexia-friendly fonts, configurable focus/blur modes, text-to-speech, plain-English errors, and customizable syntax highlighting.

- **Authoritative spec:** `accessible-ide-requirements.md` (root) — read this before planning any feature. The MVP feature checklist is in section 10.
- **Status:** Pre-development. The requirements doc was created 2026-09-23; no application code exists yet.

## Repository Layout

```
Dyslexia IDE/
├── AGENTS.md                     # This file
├── accessible-ide-requirements.md # Full requirements & specifications
└── accessible-coding/             # Intended application repository root
    ├── .github/workflows/         # CI (empty — to be added)
    ├── docs/                      # Documentation (empty)
    ├── src/accessible_ide/
    │   ├── assets/                # Fonts (OpenDyslexic, Atkinson Hyperlegible), static assets
    │   ├── components/            # Editor, focus mode, TTS, theme builder UI
    │   ├── config/                # JSON/TOML settings load/save
    │   └── utils/                 # Helpers (error translation, TTS wrappers, etc.)
    └── tests/                     # Test suite (empty)
```

All directories are currently empty scaffolding. Do not assume existing patterns — establish them as code is written.

## Key Constraints (from requirements)

- **MVP target:** ~1 month; ship incrementally (semantic versioning from 0.1.0), not one big v1.
- **Platforms:** Browser web app first, Windows `.exe` (PyInstaller) second; Linux later. Offline-first — all work saved locally.
- **Language support:** Python only for MVP. Multi-language is future work.
- **Stack (open decisions):** Streamlit vs Flask/FastAPI undecided; editor is Monaco, CodeMirror, or Ace — finalize before building the editor.
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

## Next Steps (from spec §13)

1. UI mockups (focus mode, theme customizer)
2. Finalize tech stack (Streamlit vs Flask; editor component)
3. Minimal prototype: Python editor + runner
4. TTS integration tests (ReciteMe, pyttsx3, eSpeak-ng, Coqui)
5. Recruit 2–3 dyslexic testers
6. Deploy v0.1 MVP
