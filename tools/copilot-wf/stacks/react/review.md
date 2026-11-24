# Review: React + TypeScript specifics

Used by the `code-review` skill on top of the generic checklist. Compare against the closest existing feature in the repo.

## Architecture
- Components are presentational. Data fetching and side effects live in hooks/services, not inline in JSX.
- Shared design-system components and tokens are reused. No literal colours, spacing or fonts.
- State is as local as possible. No global store for data used in one component.
- Props typed with an `interface`; no `any`, no `as` casts to silence the compiler.

## React pitfalls
- `useEffect` has correct dependencies, and no effect that only derives data (compute it during render instead).
- List items have stable `key`s (not the array index when the list can change).
- No state updates after unmount (abort fetches / ignore late responses).
- Event handlers aren't recreated in ways that defeat `memo` where it matters (only flag this with evidence).

## Tests
- Queries by role/label (`getByRole`, `getByLabelText`), not test IDs or class names.
- User interactions via `user-event`, not `fireEvent`, unless there's a reason.
- Loading, error and empty states are covered. Snapshot-only tests don't count.

## Accessibility
- Interactive elements are real `button` / `a` / form controls. No `div onClick`.
- Errors: `aria-invalid`, `aria-describedby`, announced (`role="alert"` / live region). Focus moves sensibly.
