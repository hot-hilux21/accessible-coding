# Changelog

What changed between releases, newest first. The version numbers match the
release tags; the app stamps its own version from the tag at build time, so
`src/accessible_ide/__init__.py` carries the last stable number rather than
the one being released.

---

## Unreleased (v2)

Everything below landed on `main` after v1.1.0 and is on the live site now.

### Accessibility

- Arabic now renders right to left. The `dir` attribute was computed and then
  never applied to the document, so Arabic claimed to be right to left and
  read left to right. The document carries `dir` now, and the editor pins
  `direction: ltr` so Python code, the gutter and the caret stay put in every
  language.
- WCAG 2.2 additions: 2.4.11 focus not obscured (the floating trace window
  closes only when the newly focused control is completely underneath it),
  2.5.7 dragging alternatives, 2.5.8 target size (the setup colour squares
  were 22px, now 24px), 3.2.6 consistent help.
- A reading ruler for line tracking, off by default, under **Settings →
  Reading**. It shades the line under the pointer and draws over nothing.
- One button family: every `.btn`, `.btn-small` and `.tool-select` clears the
  44px target floor, and the disabled treatment keeps its label legible
  (11.89:1 against the background) instead of fading it out.
- Settings and Dictionary carry `aria-expanded` and `aria-controls`, kept in
  sync on open, close and Escape.
- The 320px fallback: panes stack, the settings section list moves above the
  panel, the dividers hide. No fixed width above 320px remains.

### Themes and editor

- Fifteen presets, adding White, AMOLED and the rainbow family with accessible
  variants, alongside the existing High Contrast, Dark, Pastel and others.
- Per-colour resets, so one code colour can be put back without resetting the
  rest.
- Custom code colours moved under **Settings → Colours → Advanced**; the first
  run asks for page, background, text and selection colours only.
- The custom theme contrast note names the colour the editor uses when a pick
  fails AA, instead of only saying it was too low. The background, page and
  selection fields no longer show a note: they are not drawn on the background,
  so measuring them against it flagged the editor background as "Too low".
- One offline icon set replaces the toolbar emoji, and toolbar labels can be
  hidden.

### Packaging and operations

- `/health` is polled by `deploy.yml`, so a green deploy now means a serving
  site, and `pm2 save` keeps the process across a reboot. The boot unit is
  `Type=oneshot` with `RemainAfterExit=yes`, because the `Type=forking` unit
  `pm2 startup` wrote could not be read under SELinux and restarted in a loop.
- `run.sh` loads `.env` and runs gunicorn, so `SECRET_KEY` and `PORT` reach the
  app. `.env.example` documents them. `ALLOWED_HOSTS` was dropped; nothing
  read it.
- The favicon is served instead of answering every load with a 404.
- Render, Railway and Vercel remnants removed (config files, environment
  sniffing, docs). Hosting is Oracle Cloud behind nginx.
- The beta exe smoke test asserted a literal `<html lang="fr">` and went red
  on six consecutive pushes once `dir` was added. It matches the `lang`
  attribute now.

## 1.1.0 — 2026-10-22

- Fixed the release checks that were failing.
- Relaunch after update, access-code lockout, missing i18n keys, and coverage.
- A finished tag keeps the Latest badge instead of losing it to a pre-release.

## 1.0.0 — 2026-10-20

- First stable release: the stamped installer and the source agree on 1.0.0.
- A named pre-release can no longer be published over a finished version.
- Carried in from the beta line: the Python dictionary, stopping a running
  program, Ukrainian, custom run/stop keybindings, per-pane fonts, and an
  installer that replaces the app instead of installing a second copy.
