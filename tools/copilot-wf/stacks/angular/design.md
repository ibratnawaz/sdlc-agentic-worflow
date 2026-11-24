# Design mapping: Angular specifics

Used by the `figma-to-components` skill (Step 2).

## Where to look
- **Workspace libraries:** `projects/<lib>/` (Angular CLI) or `libs/ui/` (Nx). Their `public-api.ts` / `index.ts` lists what's exported.
- **Selector prefix:** `angular.json` → `prefix` (e.g. `app-`). Search templates for `<app-…` to see what's already used.
- **Angular Material / CDK:** if `@angular/material` is in `package.json`, prefer `mat-*` components and CDK behaviours.
- **Storybook** (`*.stories.ts`) shows supported inputs and variants.
- **Tokens:** SCSS partials (`_tokens.scss`, `_variables.scss`), CSS custom properties, or the Material theme
  (`styles.scss` / `theme.scss`).

## How Figma maps to Angular
| Figma | Angular |
|---|---|
| Component instance | an existing component selector, e.g. `<app-button>` or `<button mat-flat-button>` |
| Variant property (`Variant=Primary`) | an input: `variant = input<'primary' \| 'secondary'>('primary')` (or `@Input()`) |
| Text/boolean property | an input (`label`, `disabled`) |
| Slot / nested content | content projection: `<ng-content />` or `<ng-content select="[slot=icon]" />` |
| Interaction (click → next) | an output: `continue = output<void>()` (or `@Output()`) |
| Error state | form control state + `<mat-error>` / the shared field's error input. Not a separate component |
| Style (`Color/Text/Muted`) | a token: SCSS variable, CSS custom property, or Material theme token |

## Example decision rows
| Figma element | Decision | Component (path) | Inputs / variant |
|---|---|---|---|
| Primary CTA "Continue" | Reuse | `projects/ui/src/lib/button/button.component.ts` (`<app-button>`) | `variant="primary"`, `type="submit"` |
| Amount field (Error) | Reuse | `<mat-form-field>` + `<input matInput>` + `<mat-error>` | `formControlName="amount"` |
| Allocation donut | **New** | `src/app/features/x/allocation-chart.component.ts` (proposed) | `data = input.required<Slice[]>()`, `label = input<string>()` |

## Angular-specific open questions to raise
- Should the new component go into the shared library (reused) or stay in the feature folder (one-off)?
- Is there a Material equivalent the team prefers over a custom component?
