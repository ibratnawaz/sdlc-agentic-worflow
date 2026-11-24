# Review: Angular specifics

Used by the `code-review` skill on top of the generic checklist. Compare against the closest existing feature in the repo.

## Architecture
- Components are presentational. HTTP and business logic live in `providedIn: 'root'` services (or feature-scoped providers on purpose).
- Shared UI library / Angular Material reused. No literal colours, spacing or fonts in `.scss` (use tokens / CSS custom properties).
- The new code follows the repo's style: standalone vs NgModule, signal `input()` vs `@Input()`, control flow `@if` vs `*ngIf`.
  Mixing styles inside one component is a finding.
- New routes are lazy-loaded (`loadComponent` / `loadChildren`) if the repo lazy-loads elsewhere.

## Angular pitfalls
- **Subscriptions:** every manual `subscribe()` is torn down (`takeUntilDestroyed()`, `async` pipe, `toSignal`). No nested subscribes.
- **Change detection:** `OnPush` components don't mutate inputs in place. They create new objects/arrays or use signals.
- **Templates:** no logic-heavy method calls in bindings (they re-run on every check). Use `computed()` or a pure pipe.
  `@for` has a meaningful `track` expression (not `$index` when items can reorder).
- **Forms:** typed reactive forms. Validators are pure and unit-tested. No `any` via `FormGroup<any>` or untyped `FormControl`.
- **DOM:** no direct `document`/`ElementRef.nativeElement` manipulation where a binding, `Renderer2` or the CDK would do.
- **Security:** no `bypassSecurityTrust…` without a written justification. No `[innerHTML]` with user data.

## Tests
- The spec uses the repo's runner and style (Jasmine vs Jest vs Vitest). No new test libraries were added.
- Component specs query by label/role/accessible attributes, not CSS classes or `By.css('.btn-primary')`.
- `HttpTestingController.verify()` runs after HTTP tests. No real network calls.
- Every AC has a good- and bad-path test, including server-error handling for HTTP-backed features.

## Accessibility
- `[attr.aria-invalid]` / `[attr.aria-describedby]` on invalid fields. Errors announced (`role="alert"` or `LiveAnnouncer`).
- Focus management on submit errors and in dialogs (CDK `cdkTrapFocus`, `MatDialog`). Visible focus styles not removed.
- Material controls used with their labels (`<mat-label>`), and errors via `<mat-error>`.
