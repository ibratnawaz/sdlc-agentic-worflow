# Accessibility checklist (WCAG 2.2 AA) — per interactive element

- [ ] **Semantic element** used (`button`, `a`, `input`, `select`, `dialog`), with ARIA only where HTML can't express it
- [ ] **Accessible name** — visible label, `aria-label`, or `aria-labelledby`; icon-only buttons have one
- [ ] **Keyboard** — reachable with Tab, works with Enter/Space (and arrows for menus/tabs), no keyboard trap
- [ ] **Focus** — visible focus indicator; modals move focus in, trap it, and restore it on close
- [ ] **Errors** — text (not only colour), announced (`role="alert"`/`aria-live`), linked via `aria-describedby`
- [ ] **State exposed** — `aria-expanded`, `aria-selected`, `aria-busy`, `disabled` as appropriate
- [ ] **Images** — meaningful `alt`, or `alt=""` if decorative
- [ ] **Contrast and size** — from design tokens (text ≥ 4.5:1); touch targets ≥ 24×24 px
- [ ] **Motion** — respects `prefers-reduced-motion`
- [ ] **Zoom/reflow** — usable at 200% zoom and 320 px width without horizontal scrolling
- [ ] **Headings and landmarks** — logical heading order; page regions use `main`, `nav`, etc.
