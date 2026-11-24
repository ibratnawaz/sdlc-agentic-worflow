---
name: tdd-implementation
description: >
  Implements an approved plan test-first: writes failing unit/integration tests for each
  acceptance criterion's good and bad paths, then the minimum code to pass, then refactors,
  for React/TypeScript or Spring Boot. Enforces accessibility for frontend code. Use for
  "implement the plan", "TDD this", or Step 4 of the copilot workflow.
---

# TDD implementation

Red → Green → Refactor, **one AC at a time**, in the order of the plan.

## Iron laws
- NEVER write production code for an AC before its test exists and has been **seen failing**.
- NEVER skip, delete, `.skip`/`@Disabled`, or weaken a test (looser assertion, broader mock) to get green.
- NEVER expand scope beyond `03-plan.md`. If the plan is wrong, stop and tell the user.
- After **3 failed attempts** at the same failing test, stop and report what you tried.

| Excuse | Reality |
|---|---|
| "I'll write the tests after, it's faster" | Then they test what you wrote, not what the AC says. |
| "That bad path can't happen" | Then the test is quick to write and documents it. |
| "The test is flaky, I'll skip it" | Find out why. Flaky tests in finance code hide real bugs. |
| "It's just a small UI change, a11y doesn't apply" | Every interactive element needs a name, a role and keyboard access. |

## Steps

1. **Read** `.copilot-wf/<KEY>/03-plan.md` (and `02-design.md` for FE).
   **Fix cycle** (asked to address review findings): also read `.copilot-wf/<KEY>/05-review.md`. For each `blocker`/`major`,
   write or tighten a test that exposes it (red), then fix it (green). Append a *Fix cycle N* section to `04-implementation.md`.
   `wf.py check` caps the number of cycles (exit 5 → stop and report `BLOCKED`).
2. **Find the commands** (don't guess):
   - FE: `package.json` scripts → test, lint, type-check (e.g. `npm test -- <file>`, `npm run lint`, `npx tsc --noEmit`).
   - BE: `./mvnw test -Dtest=<Class>` / `./gradlew test --tests <Class>`; full: `./mvnw verify` / `./gradlew check`.
3. **Baseline:** run the full test suite once *before* changing anything. Record pass/fail counts.
   Failures that already exist are not yours. Note them; don't fix them silently.
4. **For each AC in plan order:**
   1. Write the good-path and bad-path tests from the AC → test table.
   2. Run them → confirm they fail **because the behaviour is missing** (not a typo or bad import).
   3. Write the minimum code to pass. Run → green.
   4. Refactor (names, duplication), run again → still green.
   Stack specifics: `references/frontend-testing.md` or `references/backend-testing.md`.
5. **FE accessibility:** go through `references/accessibility-checklist.md` for every new/changed interactive element,
   and add an automated a11y assertion if the repo has the helper.
6. **Full check:** whole test suite + lint + type-check/compile. Everything green, or stop and report.
7. **Write** `.copilot-wf/<KEY>/04-implementation.md`:
   AC → tests → ✅/❌, files changed, commands run with pass/fail counts (baseline vs now), any deviation from the plan and why.
8. **Finish:**
   ```bash
   python3 tools/copilot-wf/wf.py done --ticket <KEY> --phase implement \
     --read .copilot-wf/<KEY>/03-plan.md \
     --wrote .copilot-wf/<KEY>/04-implementation.md <every source/test file you changed or created>
   ```
   (`git status --short` lists them.)
   Paste the usage table.
