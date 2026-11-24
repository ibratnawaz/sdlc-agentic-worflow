# Design mapping: React specifics

Used by the `figma-to-components` skill (Step 2).

## Where to look
- Shared components: `src/ui/`, `src/components/`, or a design-system package in `package.json` (often `@<org>/ui`).
- Storybook stories (`*.stories.tsx`) show the variants a component already supports.
- Tokens: a `tokens.ts`/`theme.ts`, CSS custom properties, or the design-system package's theme.

## How Figma maps to React
| Figma | React |
|---|---|
| Component instance | an existing component, e.g. `<Button>` |
| Variant property (`Variant=Primary`) | a prop (`variant="primary"`) |
| Text/boolean property | a prop (`label`, `disabled`) |
| Nested slot / content | `children` or a render prop |
| Style (`Color/Text/Muted`) | a token (`tokens.color.text.muted`) |

## Example decision rows
| Figma element | Decision | Component (path) | Props / variant |
|---|---|---|---|
| Primary CTA "Continue" | Reuse | `src/ui/Button/Button.tsx` | `variant="primary"` |
| Allocation donut | **New** | `src/features/x/AllocationChart.tsx` (proposed) | `data, label` |
