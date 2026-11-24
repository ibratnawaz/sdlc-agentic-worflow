---
applyTo: "**/*.{ts,tsx}"
---

# React + TypeScript conventions

<!-- Loaded only when Copilot works on matching files. Replace the examples with your team's real rules. -->

- Function components + hooks only. Props typed with an `interface`, no `any`.
- Reuse the shared design-system components before writing new ones. Never hardcode colours, spacing or fonts; use design tokens.
- Keep data fetching in hooks/services, not inside presentational components.

## Accessibility (WCAG 2.2 AA) — required, not optional
- Use semantic elements (`button`, `nav`, `label`) before ARIA. A `div` with `onClick` is a bug.
- Every input has an associated label; every image has meaningful `alt` (or `alt=""` if decorative).
- Everything works with keyboard only; focus is visible and moves logically (modals trap and restore focus).
- Colour is never the only signal; text contrast ≥ 4.5:1 (comes from tokens).
- Errors are announced (`aria-live` or `role="alert"`) and tied to fields with `aria-describedby`.

## Tests
- React Testing Library: query by role/label (`getByRole`), not test IDs or class names.
- Every new component gets an automated a11y check (e.g. `jest-axe` / `vitest-axe`) if the repo has it.
