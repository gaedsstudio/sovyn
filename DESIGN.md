# SOVYN Signal Design System

## 0. Research Log

- Embedded refs: picked `taste-skill.md` + `linear.app.md` because SOVYN Signal is a dense research app shell that needs precision, restrained hierarchy, and credible financial tone.
- Layout refs: loaded `layout-skill.md` because Today, Asset, Watchlist, and Ask are fixed-navigation product screens with dense panels and content stress risk.
- Lazyweb: skipped because this reboot needs implementation momentum and the chosen embedded reference gives enough app-shell grammar.
- Imagen drafts: skipped because the brief prohibits excessive illustration and asks for a data-first financial product.

## 1. Atmosphere & Identity

SOVYN Signal feels like a quiet research terminal with editorial judgment. The signature is a dark, precise signal tape: ranked market changes, impact paths, and evidence appear as structured findings rather than chat bubbles or decorative dashboards.

## 2. Color

| Role | Token | Value | Usage |
| --- | --- | --- | --- |
| Canvas | `--color-canvas` | `#08090a` | Page background |
| Panel | `--color-panel` | `#0f1011` | Navigation, side regions |
| Surface | `--color-surface` | `#17191c` | Repeated signal rows and forms |
| Surface raised | `--color-raised` | `#202329` | Active selections |
| Text primary | `--color-text` | `#f7f8f8` | Primary labels and values |
| Text secondary | `--color-muted` | `#a7afba` | Body and explanations |
| Text tertiary | `--color-faint` | `#6f7782` | Metadata |
| Border subtle | `--color-border` | `rgba(255,255,255,0.08)` | Default dividers |
| Accent | `--color-accent` | `#7170ff` | Active nav, links, focus |
| Positive | `--color-positive` | `#10b981` | Positive market direction |
| Negative | `--color-negative` | `#f87171` | Negative market direction |
| Warning | `--color-warning` | `#f59e0b` | Medium confidence |

## 3. Typography

Primary font is Inter or the system UI stack. Monospace font is Berkeley Mono, SF Mono, ui-monospace, Menlo, Consolas, monospace. Display text uses tight line height and restrained negative tracking; body text stays at 14px or above. Numeric values use tabular numerals.

## 4. Spacing & Layout

Base unit is 4px. App shell uses a fixed top navigation and document scroll. Main content is constrained to 1280px with 16px mobile margins, 24px tablet gutters, and 32px desktop gutters. Dense tables and signal lists use 8px to 16px internal gaps.

## 5. Components

### App Shell
- Structure: top navigation, constrained main, responsive route content.
- States: active nav item, hover, focus.
- Accessibility: nav landmark, visible focus ring, no hidden primary actions.
- Layout: scroll body owned by the document; no nested body scrollbars.

### Signal Row
- Structure: rank, asset group, value change, explanation, impact links, score.
- Variants: default, watchlist relevant, compact.
- States: hover background shift, focus outline when linked.
- Accessibility: impact score and confidence exposed as text.

### Evidence Panel
- Structure: facts, interpretation, uncertainty, methods.
- Variants: Ask answer, Asset selected move, signal detail.
- States: empty, loading, error.
- Accessibility: clear headings and text labels instead of color-only meaning.

### Watchlist Control
- Structure: symbol input, asset rows, remove controls.
- States: empty, invalid, saved, active.
- Accessibility: labelled input, keyboard reachable buttons.

## 6. Motion & Interaction

Motion is minimal and informational. Interactive rows shift background and border color in 120ms. Buttons move by 1px on active press. Reduced motion receives the same layout with transitions removed.

## 7. Depth & Surface

Depth strategy is mixed but restrained: tonal shifts plus thin translucent borders. No heavy shadows, glassmorphism, or decorative gradients. Radius is 8px for panels and 6px for controls.

## 8. Accessibility Constraints & Accepted Debt

Target WCAG 2.2 AA. Body text contrast must exceed 4.5:1. Focus states must be visible for navigation, buttons, links, and form fields.

Accepted debt: no browser Lighthouse pass yet because dependencies must first be installed and the development server started in this environment.

