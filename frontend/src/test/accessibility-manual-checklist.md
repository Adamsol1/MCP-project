# Manual Accessibility Checklist (What axe Cannot Test)

axe-core covers ~30–40% of WCAG 2.1 AA issues automatically. This checklist covers the rest.

---

## 1. Keyboard Navigation

Test by unplugging your mouse entirely and using Tab / Shift+Tab / Enter / Space / Arrow keys.

- [ ] Every interactive element is reachable by keyboard (buttons, links, inputs, dropdowns, modals)
- [ ] Tab order follows the visual reading order (left→right, top→bottom)
- [ ] No keyboard focus trap outside of modals — you can always Tab out of any section
- [ ] Modals trap focus correctly — Tab cycles only within the open modal
- [ ] Focus returns to the trigger element when a modal or popover closes
- [ ] Dropdown menus open and close with Enter/Space, navigate with Arrow keys, close with Escape
- [ ] Custom components (perspective selector buttons, toast close) work with Enter and Space

---

## 2. Focus Visibility

- [ ] Every focused element has a clearly visible focus ring (not just the browser default where it's subtle)
- [ ] Focus ring is visible on both light and dark themes
- [ ] Focus ring has at least 3:1 contrast ratio against its background (WCAG 2.2 §2.4.11)
- [ ] Focus is never hidden behind sticky headers or fixed elements

---

## 3. Screen Reader Testing

Use NVDA + Chrome (Windows) or VoiceOver + Safari (Mac/iOS).

- [ ] Page has a meaningful `<title>` and a single `<h1>`
- [ ] Heading hierarchy is logical (h1 → h2 → h3, no skips)
- [ ] Landmark regions present: `<main>`, `<nav>`, `<header>`, `<aside>` as appropriate
- [ ] All images have descriptive `alt` text (decorative images have `alt=""`)
- [ ] Icon-only buttons have an accessible name (aria-label or visually hidden text)
- [ ] Status messages (toasts) are announced without moving focus (check aria-live regions)
- [ ] Chat messages from the AI are announced as they arrive
- [ ] Loading/processing states are announced (e.g. "Processing review..." state in ChatWindow)
- [ ] Form errors are associated with their inputs and announced on submission
- [ ] Tables (if any) have proper `<caption>`, `<th scope>` markup

---

## 4. Color and Visual

### Color blindness simulation
Use Chrome DevTools → Rendering → **Emulate vision deficiencies** and test all 8 modes:
Protanopia, Deuteranopia, Tritanopia, Achromatopsia, Protanomaly, Deuteranomaly, Tritanomaly, Blurred vision

- [ ] PIR priority labels (High / Medium / Low) are distinguishable without relying on colour alone — check they have a shape/icon indicator
- [ ] Highlighted source cards ([1], [2] refs) are distinguishable from non-highlighted by more than just colour
- [ ] Toast notification types (success/error/warning/info) are distinguishable by icon AND colour (not colour alone)
- [ ] Active/selected states in PerspectiveSelector buttons are distinguishable by shape, not just colour
- [ ] Confidence percentage bars convey meaning beyond their fill colour

### Contrast (beyond what axe checks)
axe checks text contrast but misses some cases:

- [ ] Placeholder text in the message input meets 4.5:1 (placeholders often fail)
- [ ] Disabled button text meets 3:1 (WCAG allows lower for disabled, but check it's readable)
- [ ] Text overlaid on the `surface-deep` dark background in the sidebar meets 4.5:1
- [ ] Text on `primary` coloured buttons meets 4.5:1 in both light and dark themes

---

## 5. Motion and Animation

- [ ] CSS transitions/animations respect `prefers-reduced-motion` — test by enabling "Reduce motion" in OS settings
- [ ] No content flashes more than 3 times per second (seizure threshold)

---

## 6. Cognitive / Content

These require human judgement — axe cannot evaluate them:

- [ ] Error messages explain what went wrong and how to fix it (not just "Error")
- [ ] Timeout/session warnings give the user enough notice
- [ ] Labels and instructions are written in plain language
- [ ] Complex UI sections (IntelligencePanel phases) have visible headings that explain what is shown
- [ ] Form fields have visible labels (not just placeholder text as the label)

---

## 7. Responsive / Zoom

- [ ] UI is usable at 400% browser zoom without horizontal scrolling (WCAG 1.4.10 Reflow)
- [ ] Sidebar collapsed/expanded states are accessible at all zoom levels
- [ ] Touch targets are at least 24×24px (WCAG 2.2 §2.5.8), ideally 44×44px

---

## Quick Reference: axe WCAG Coverage

| Level | Tags used | What it covers |
|-------|-----------|----------------|
| A | `wcag2a`, `wcag21a` | Most critical barriers — missing alt, broken ARIA, no labels |
| AA | `wcag2aa`, `wcag21aa` | Contrast ratios, focus visible, language, resize |
| AA (2.2) | `wcag22aa` | Focus appearance, target size, redundant entry |
| AAA | `wcag2aaa` *(opt-in)* | Enhanced contrast (7:1), sign language, no timing |

**Default axe run covers: WCAG 2.x Level A + AA + WCAG 2.1 AA additions.**
WCAG 2.2 and AAA require explicit tag opt-in and are not included by default.
