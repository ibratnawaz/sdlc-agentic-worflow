# Stack profiles: how the workflow supports a language

The workflow's **process** (analyze → design → plan → TDD → review → ship) is the same for every language.
What changes per language is **knowledge**: conventions, test tools, review rules and how designs map to components.
That knowledge lives here, one folder per stack. The skills in `.github/skills/` stay generic and read the right folder.

```
tools/copilot-wf/stacks/
├── react/          instructions.md  testing.md  review.md  design.md
├── angular/        instructions.md  testing.md  review.md  design.md
└── spring-boot/    instructions.md  testing.md  review.md            (backend: no design.md)
```

## Who reads which file

| File | Read by | Used for |
|---|---|---|
| `instructions.md` | **Copilot itself**, after `wf.py use-stack <stack>` copies it to `.github/instructions/` | Coding conventions on every matching file (`applyTo` glob), in and outside the workflow |
| `testing.md` | Step 3 (plan) and Step 4 (TDD) | Commands, test levels, test patterns, bad paths to cover |
| `review.md` | Step 3 (plan) and Step 5 (review) | Architecture rules and stack pitfalls the reviewer checks |
| `design.md` (FE only) | Step 2 (design) | Where shared components/tokens live, and how Figma variants, slots and events map to this stack's component API |

`config.json → stacks` holds the **detection rules** (which files identify the stack) and its `side` (`fe`/`be`).
Detection is code (`wf.py detect`), so it's the same answer every time.

## Add a new stack in 5 steps (example: Vue)

1. **Detection rule** in `tools/copilot-wf/config.json → stacks`. Put more specific stacks first, because the first match wins in a single-stack repo:
   ```json
   "vue": { "label": "Vue 3 + TypeScript", "side": "fe",
            "detect": [{ "file": "package.json", "contains": "\"vue\"" }] }
   ```
2. **Copy the closest profile** as a starting point: `cp -R tools/copilot-wf/stacks/react tools/copilot-wf/stacks/vue`.
3. **Rewrite the four files** for the new stack. Keep the same headings, because the skills rely on them:
   - `instructions.md`: frontmatter `applyTo` for the stack's files (`**/*.{vue,ts}`), then conventions and a11y rules.
   - `testing.md`: **Commands**, **Test levels**, **Patterns**, and **bad paths** to cover.
   - `review.md`: **Architecture**, **pitfalls**, **Tests**, and **Accessibility** (FE).
   - `design.md` (FE): **Where to look**, **How Figma maps to <stack>**, and **Example decision rows**.
4. **Prove it with tests** (in `tools/copilot-wf/tests/test_stacks.py`): add a detection test like `test_angular`, then run:
   ```bash
   python3 -m unittest discover tools/copilot-wf/tests
   python3 tools/copilot-wf/wf.py stacks        # every profile must show ✔
   ```
   `TestProfilesAreComplete` fails automatically if a configured stack is missing a file.
5. **Install it in a repo of that stack:** `python3 tools/copilot-wf/wf.py use-stack vue`, then run one small ticket.

A backend stack (e.g. `dotnet`, `fastapi`, `node-express`) is the same minus `design.md`, with `"side": "be"`.

## Rules of thumb
- **Follow the repo, not the internet.** Each profile says "use what the repo already has". The AI must not switch test runners,
  state libraries or styles because a profile mentions an alternative.
- **One FE + one BE stack per repo is fine.** Two FE stacks in one repo (React *and* Angular) need narrower `applyTo` globs,
  e.g. `apps/admin/**/*.ts`, or they'll both claim every `.ts` file. `wf.py use-stack` warns you about this.
- **Edit the profile, not the installed copy.** `wf.py use-stack` refuses to overwrite a hand-edited `.github/instructions/` copy.
