---
applyTo: "**/*.{ts,html,scss,css}"
---

# Angular + TypeScript conventions

<!-- Installed into .github/instructions/ by `wf.py use-stack angular`. Copilot loads it only for matching files.
     Edit THIS file (tools/copilot-wf/stacks/angular/instructions.md), not the installed copy.
     Replace the examples with your team's real rules. Match the Angular version in package.json. -->

## Components
- Follow what the repo already does. For new code in Angular 17+: **standalone** components, `ChangeDetectionStrategy.OnPush`,
  built-in control flow (`@if`, `@for (x of xs; track x.id)`, `@switch`), and `inject()` for dependencies.
- Inputs/outputs: use signal `input()` / `output()` if the repo uses them, otherwise `@Input()` / `@Output()`. Don't mix both styles in one component.
- Keep templates dumb: no method calls with logic in bindings. Use `computed()` signals or pipes instead.
- Reuse the shared component library (Angular Material/CDK or the team's UI lib) before writing a new component.
  Never hardcode colours, spacing or fonts. Use theme tokens / CSS custom properties.

## Data and state
- HTTP lives in `@Injectable({ providedIn: 'root' })` services using `HttpClient`, never in components.
- Component state: signals (`signal`, `computed`). RxJS streams: the `async` pipe or `toSignal()`.
- Manual `subscribe()` must be torn down (`takeUntilDestroyed()`). Never nest subscribes. Compose with operators instead.
- Forms: **typed reactive forms** (`FormGroup<…>`, `NonNullableFormBuilder`). Validators are pure functions, so they're easy to unit-test.
- No `any`. No non-null `!` assertions to silence the compiler.

## Accessibility (WCAG 2.2 AA), required
- Native elements first (`button`, `a`, `label` + `for`). A `div (click)` is a bug.
- Form errors: `[attr.aria-invalid]` and `[attr.aria-describedby]` pointing at the error element, announced via
  `role="alert"` or the CDK `LiveAnnouncer`. With Material, `<mat-error>` inside `<mat-form-field>` does the linking for you.
- Dialogs/overlays trap and restore focus (CDK `cdkTrapFocus` / `MatDialog`). Moving focus to the first invalid field on submit is expected.
- Use the CDK `a11y` module instead of hand-rolled focus or keyboard handling.

## Tests
- Every component gets a spec. Prefer Angular Testing Library (role/label queries) if installed, otherwise TestBed plus
  accessible-attribute queries. Use Material **component harnesses** for Material controls.
- HTTP: `provideHttpClient()` + `provideHttpClientTesting()` with `HttpTestingController`. Never hit a real backend.
