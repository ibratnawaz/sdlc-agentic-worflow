---
name: figma-to-components
description: >
  Reads a Figma design for a frontend ticket and maps every element to an existing
  component in this repo (reuse), a composition of existing parts, or a genuinely new
  component, with tokens, states and accessibility notes. Use for "map this Figma",
  "which components do I need", or Step 2 of the copilot workflow. Not for writing code.
---

# Figma → components

**The design system is the source of truth, not the mock-up.** Figma tells you layout, hierarchy, copy
and interaction intent. It does not authorise literal hex colours, pixel spacing, fonts, radii or shadows.

## Iron laws
- NEVER propose a new component before searching the repo for an existing one (name, props, stories).
- NEVER put a literal colour/spacing/font value in the decision table. Map it to an existing token, or list it under *Open questions*.
- NEVER claim a component exists without the file path you opened.

| Excuse | Reality |
|---|---|
| "It's faster to build a new button that matches exactly" | Two buttons = two a11y bugs and a design-drift ticket later. Reuse with a variant. |
| "Figma doesn't show error/loading/empty states, so there aren't any" | There always are. List them as open questions. |

## Steps

1. **Link.** Take the Figma link from `.copilot-wf/<KEY>/01-requirements.md`, or ask the user.
   Prefer a link to a specific frame (`?node-id=…`). A whole-file link is too big; ask which frame.
2. **Fetch.** Read `data_source` in `tools/copilot-wf/config.json`, then:
   - `mcp` — use the Figma MCP tools for the node: design context/metadata first, plus a screenshot.
     Ask for one node, not the whole file.
   - `scripts` — run `python3 tools/copilot-wf/figma_fetch.py "<figma-url>" --ticket <KEY> --image`
     and read `.copilot-wf/<KEY>/source/figma.md` (plus `figma.png` if you need to see it).
3. **Inventory the repo.** Find the shared component library (look for a `components/`/`ui/` folder, a
   design-system package in `package.json`, Storybook stories) and the token files. Open the candidates.
4. **Map** every meaningful Figma element using the table below. Order of preference:
   **reuse as-is → reuse with variant/props → compose from existing → new** (justify every "new").
5. **States and a11y.** For each interactive element, list states (default, hover, focus, disabled, loading,
   error, empty) and accessibility needs (role, accessible name, keyboard, focus order, announcements).
   Use `../tdd-implementation/references/accessibility-checklist.md`.
6. **Write** `.copilot-wf/<KEY>/02-design.md` (template below).
7. **Finish:**
   ```bash
   python3 tools/copilot-wf/wf.py done --ticket <KEY> --phase design \
     --read .copilot-wf/<KEY>/01-requirements.md [.copilot-wf/<KEY>/source/figma.md] \
     --wrote .copilot-wf/<KEY>/02-design.md
   ```
   Paste the usage table.

## Template — `02-design.md`

```markdown
# <KEY> — design mapping
Figma: <link to frame>

## Component decisions
| Figma element | Decision | Component (path) | Props / variant | Notes |
|---|---|---|---|---|
| Primary CTA "Continue" | Reuse | `src/ui/Button/Button.tsx` | `variant="primary"` | |
| Account summary card | Compose | `Card` + `Stack` + `Text` | | |
| Allocation donut | **New** | `src/features/x/AllocationChart.tsx` (proposed) | `data, label` | No chart exists — confirmed by searching `chart`, `donut`, `pie` |

## Tokens used
| Figma value | Token | Note |
## States (per interactive element)
## Accessibility notes
## New components — proposed API
## Open questions (missing states, unmapped values, unclear behaviour)
```
