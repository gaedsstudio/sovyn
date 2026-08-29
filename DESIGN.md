# SOVYN Website Design System

## 0. Research Log

- Concrete reference: `C:\Users\장서원\Downloads\sovyn-v2.html` is the visual source of truth for this pass. Its Tailwind CDN, placeholder anchors, emoji glyphs, and inline behavior script are not implementation instructions.
- Existing system: the production site already uses Next.js App Router, TypeScript, global CSS primitives, and server-rendered registry data. The v2 pass keeps that architecture.
- Intent: a bright public-alpha website for an open-source local agent runtime, with the Hub still backed by the real Registry API.

## 1. Atmosphere & Identity

SOVYN v2 feels open, practical, and inspectable: a white/off-white developer-product surface with confident slate typography and one memorable orange action color. The signature is lightweight public-alpha clarity, not a dark control room.

## 2. Color

| Role | Token | Value | Usage |
| --- | --- | --- | --- |
| Surface canvas | --surface-canvas | #fafafa | Page background |
| Surface panel | --surface-panel | #ffffff | Header, cards, content panels |
| Surface raised | --surface-raised | #f8fafc | Subtle secondary panels |
| Surface inset | --surface-inset | #0f172a | Terminal and final CTA |
| Text primary | --text-primary | #020617 | Headlines and important labels |
| Text secondary | --text-secondary | #334155 | Body copy |
| Text muted | --text-muted | #64748b | Supporting copy |
| Text faint | --text-faint | #94a3b8 | Quiet labels and metadata |
| Border default | --border-default | #e2e8f0 | Cards and controls |
| Border strong | --border-strong | #cbd5e1 | Focusable controls |
| Accent | --accent | #ff542e | Primary actions and brand highlights |
| Accent hover | --accent-hover | #e04420 | Primary action hover |
| Accent soft | --accent-soft | #fff1ee | Accent icon wells and badges |
| Success | --success | #059669 | Verified status |
| Warning | --warning | #d97706 | Permission attention |

## 3. Typography

| Level | Size | Weight | Line Height | Tracking | Usage |
| --- | --- | --- | --- | --- | --- |
| Display | clamp(3rem, 7vw, 4.75rem) | 800 | 1.08 | 0 | Homepage hero |
| H1 | clamp(2.4rem, 5vw, 4rem) | 800 | 1.08 | 0 | Page headlines |
| H2 | clamp(1.85rem, 3vw, 2.5rem) | 800 | 1.12 | 0 | Section titles |
| H3 | 1.125rem | 700 | 1.3 | 0 | Card titles |
| Body large | 1.125rem | 400 | 1.7 | 0 | Lead copy |
| Body | 1rem | 400 | 1.65 | 0 | Default copy |
| Small | 0.875rem | 500 | 1.6 | 0 | Secondary copy |
| Label | 0.75rem | 700 | 1.4 | 0.06em | Uppercase metadata |
| Mono | 0.875rem | 500 | 1.65 | 0 | Terminal and code |

Primary font: Plus Jakarta Sans with system fallbacks. Mono font: JetBrains Mono with SFMono-Regular, Consolas, and Liberation Mono fallbacks.

## 4. Spacing & Layout

Base unit: 4px.

| Token | Value | Usage |
| --- | --- | --- |
| --space-2 | 8px | Tight inline groups |
| --space-3 | 12px | Control padding |
| --space-4 | 16px | Compact panels |
| --space-6 | 24px | Default card padding |
| --space-8 | 32px | Grid gaps |
| --space-10 | 40px | Search and content rhythm |
| --space-12 | 48px | Section internals |
| --space-16 | 64px | Page sections |
| --space-20 | 80px | Large section rhythm |
| --space-24 | 96px | Hero rhythm |

Max content width is 1152px. Pages use a centered content rail, document scrolling, full-width bands, and responsive grids with `minmax(min(100%, 16rem), 1fr)`.

## 5. Components

### Site Header
- Structure: sticky white header, brand link, primary route nav, GitHub/Discord external links, and a compact primary CTA.
- States: scroll shadow/hairline, text hover, visible focus.
- Accessibility: semantic nav and real route anchors.

### Pill Button
- Structure: rounded pill anchor or button in primary, secondary, and dark variants.
- States: hover translates up 1px, active returns down 1px, focus visible.
- Motion: 180-240ms transform, border, color, and background transitions.

### Feature Card
- Structure: white card, thin slate border, centered compact icon well, title, and short copy.
- States: hover lifts slightly and raises border/shadow.
- Accessibility: decorative icon wells are hidden from assistive tech.

### Search Form
- Structure: pill search container with visible label, text input, and submit button.
- States: focus-within border changes to accent, keyboard submit works.
- Accessibility: `label` remains available; placeholder is not the only label.

### Package Card
- Structure: article with package name, status badge, license badge, description, permissions, source link, and detail link.
- States: links are real anchors; hover applies only to actionable controls.
- Accessibility: external source and internal detail destinations are explicit.

### FAQ Item
- Structure: native `details`/`summary` accordion with plus marker.
- States: open marker rotates; content expands through native browser behavior.
- Accessibility: no custom script required for basic operation.

### Terminal Panel
- Structure: dark inset panel for command examples and security chains.
- States: static read surface.
- Accessibility: code remains selectable HTML text.

## 6. Motion & Interaction

Micro interactions use 180-300ms transitions on color, border-color, box-shadow, opacity, and transform. No constant animation. Reduced-motion disables transitions where users request it.

## 7. Depth & Surface

Depth strategy: white surfaces, thin slate borders, and restrained shadow. The final CTA and terminal panels use dark slate contrast so the page has a clear close without returning to the old dark theme.

## 8. Accessibility Constraints & Accepted Debt

Target WCAG 2.2 AA. Every interactive element must be keyboard reachable, have visible focus, retain readable contrast, and preserve layout at 375px without horizontal document overflow.

| Item | Location | Why accepted | Owner / Exit |
| --- | --- | --- | --- |
| Full browser Lighthouse 100 loop | Deployed `https://sovyn.org` | This pass prioritizes user-requested lint/type/test/build/OpenNext, registry QA, deployment, and visual breakpoints | Run as a separate performance hardening pass if release gate demands exact Lighthouse scoring |
