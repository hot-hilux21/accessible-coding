# Accessibility conformance matrix

Status values: `verified`, `partially_verified`, `not_yet_tested`, `planned`.

| Criterion | Status | Evidence / limitation |
|---|---|---|
| WCAG 2.1 AA contrast | `verified` | `tests/test_contrast.py` covers text and custom theme derivation. |
| Keyboard reachability | `partially_verified` | DOM harness covers controls; full manual pass outstanding. |
| Focus not obscured | `partially_verified` | Floating trace behaviour tested; full dialog sweep outstanding. |
| Target size | `partially_verified` | 24px setup swatches fixed; full product sweep outstanding. |
| Motion | `partially_verified` | Reduced-motion rule in CSS; user testing outstanding. |
| Screen reader | `not_yet_tested` | Full NVDA/VoiceOver pass outstanding. |
| Zoom/reflow | `partially_verified` | Narrow-viewport test exists; full manual sweep outstanding. |
| High contrast / forced colours | `not_yet_tested` | Needs manual browser testing. |
| Internationalisation / RTL | `partially_verified` | Arabic and script fallback tests exist; wider sweep outstanding. |

## Reporting process

Record blocker status, evidence, test method, and known limitation per criterion. Publish known limitations before making broad compliance claims.
