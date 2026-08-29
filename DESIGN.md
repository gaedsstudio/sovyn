# SOVYN Website Design System

## 0. Research Log

- Embedded refs: shortlisted Linear, Vercel, Stripe -> picked minimalist execution + Linear because the site needs a restrained developer-product surface with terminal clarity and thin hierarchy.
- Lazyweb: skipped because existing brief named enough concrete references and this environment is already anchored by local design references.
- Imagen drafts: skipped because the brief rejects generated-looking illustration and asks for typography, terminal examples, code, tables, and flat technical surfaces.
- Skipped lanes: React dev tooling install deferred because the site has not existed in this repo before this pass and launch scope favors minimal production dependencies.

## 1. Atmosphere & Identity

SOVYN feels like a local command center for inspectable work: quiet, exact, and permission-aware. The signature is a thin-lined terminal and registry language where every action exposes source, permissions, and local ownership before persuasion.

## 2. Color

| Role | Token | Value | Usage |
| --- | --- | --- | --- |
| Surface canvas | --surface-canvas | #08090a | Page background |
| Surface panel | --surface-panel | #0f1011 | Header and large panels |
| Surface raised | --surface-raised | #17191d | Cards, code blocks, package rows |
| Surface inset | --surface-inset | #050607 | Terminal wells |
| Text primary | --text-primary | #f7f8f8 | Headlines and primary copy |
| Text secondary | --text-secondary | #d0d6e0 | Body copy |
| Text muted | --text-muted | #8a8f98 | Metadata and supporting copy |
| Text faint | --text-faint | #62666d | Quiet labels |
| Border default | --border-default | rgba(255,255,255,0.08) | Cards and controls |
| Border subtle | --border-subtle | rgba(255,255,255,0.05) | Dividers |
| Accent | --accent | #7170ff | Links, focus, primary action |
| Accent hover | --accent-hover | #828fff | Interactive hover |
| Success | --success | #10b981 | Verified and completion status |
| Warning | --warning | #f59e0b | Permission attention |

## 3. Typography

| Level | Size | Weight | Line Height | Tracking | Usage |
| --- | --- | --- | --- | --- | --- |
| Display | clamp(3rem, 7vw, 5.8rem) | 520 | 0.96 | 0 | Hero wordmark |
| H1 | clamp(2.25rem, 5vw, 4.5rem) | 520 | 1.02 | 0 | Page headlines |
| H2 | clamp(1.75rem, 3vw, 3rem) | 520 | 1.08 | 0 | Section titles |
| H3 | 1.25rem | 590 | 1.3 | 0 | Card titles |
| Body large | 1.125rem | 400 | 1.65 | 0 | Lead copy |
| Body | 1rem | 400 | 1.6 | 0 | Default copy |
| Small | 0.875rem | 400 | 1.55 | 0 | Secondary copy |
| Label | 0.75rem | 590 | 1.4 | 0.08em | Uppercase metadata |
| Mono | 0.875rem | 400 | 1.65 | 0 | Terminal and code |

Primary font: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif.
Mono font: "SFMono-Regular", Consolas, "Liberation Mono", monospace.

## 4. Spacing & Layout

Base unit: 4px.

| Token | Value | Usage |
| --- | --- | --- |
| --space-2 | 8px | Tight inline groups |
| --space-3 | 12px | Control padding |
| --space-4 | 16px | Compact panels |
| --space-6 | 24px | Default card padding |
| --space-8 | 32px | Grid gaps |
| --space-12 | 48px | Section internals |
| --space-16 | 64px | Page sections |
| --space-24 | 96px | Hero rhythm |

Max content width is 1180px. Pages use a centered content rail, responsive grids with `minmax(min(100%, 18rem), 1fr)`, and document scrolling rather than app-shell scrolling.

## 5. Components

### Site Header
- Structure: sticky `header`, brand link, primary nav, external links.
- States: hover raises text luminance, focus uses the accent outline.
- Accessibility: semantic nav and text labels on every link.

### Button Link
- Structure: anchor styled as primary or secondary action.
- States: hover changes border/text color, active translates 1px, focus visible.
- Motion: 180ms transform and color.

### Terminal Panel
- Structure: labelled code-like ordered lines with status glyphs.
- States: static read surface.
- Accessibility: text remains plain HTML, not canvas.

### Package Card
- Structure: article with status, metadata, permissions, and source link.
- States: hover only on links, no fake popularity affordances.
- Accessibility: source and detail links are real anchors.

### Permission Matrix
- Structure: grouped permission rows for filesystem, shell, and network.
- States: empty values read as `None`.
- Accessibility: table or definition-list semantics depending on context.

### Search Form
- Structure: labelled GET form with text input and submit button.
- States: hover/focus/active on controls, empty-state result text.
- Accessibility: visible label and keyboard-submittable form.

## 6. Motion & Interaction

Micro interactions use 150-220ms transitions on color, border-color, opacity, and transform. No constant animation. Reduced-motion disables transitions where users request it.

## 7. Depth & Surface

Depth strategy: tonal shift plus thin borders. Panels step from canvas to panel to raised/inset surfaces with subtle borders. Shadows are avoided.

## 8. Accessibility Constraints & Accepted Debt

Target WCAG 2.2 AA. Every interactive element must be keyboard reachable, have visible focus, retain readable contrast on dark surfaces, and preserve layout at 375px without horizontal document overflow.

| Item | Location | Why accepted | Owner / Exit |
| --- | --- | --- | --- |
| Full production Lighthouse run | Deployed `https://sovyn.org` | Requires Cloudflare auth and live deployment | Run after `wrangler login` and deployment |
