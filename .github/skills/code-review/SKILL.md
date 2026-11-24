---
name: code-review
description: >
  Reviews a change against its ticket's acceptance criteria, the approved plan and the
  repo's architecture, and reports real, evidenced issues such as missed ACs, untested
  routes or paths, layering violations, security/PII risks and accessibility gaps. Use for
  "review my changes", "review PROJ-123", or Step 5 of the copilot workflow.
---

# Code review

You are reviewing someone else's work. Find what is **wrong or missing**. "Looks good" is not a review.

## Iron laws
- NEVER report a finding without `file:line` that you opened, and a concrete failure scenario.
- NEVER trust `04-implementation.md`'s claims. Run the tests yourself.
- NEVER pad the report with style nits to look thorough. A short list of real issues is the goal.
- NEVER edit source files. Findings go back to Step 4.

## Steps

1. **Inputs:** `.copilot-wf/<KEY>/01-requirements.md` (ACs), `03-plan.md`, `04-implementation.md`, and the diff:
   ```bash
   git fetch origin --quiet
   git diff origin/main...HEAD; git diff; git status --short   # base branch may be develop/master. Check
   ```
2. **Run** the tests for the changed area and the full suite, plus lint/type-check. Record the results.
3. **Check** each item in `references/review-checklist.md`. For each AC, ask:
   *"If I deleted the code for this AC, which test would fail?"* If the answer is none, that's a finding.
4. **Write** `.copilot-wf/<KEY>/05-review.md` (template below).
5. **Verdict:**
   - Any `blocker`/`major` → **CHANGES REQUIRED**. Tell the user to use the *Back to Step 4* handoff
     (or the `wf-4-implement` agent). **Do not** run `wf.py done`; review runs again after the fixes.
   - Otherwise → **APPROVE**, then:
     ```bash
     python3 tools/copilot-wf/wf.py done --ticket <KEY> --phase review \
       --read .copilot-wf/<KEY>/01-requirements.md .copilot-wf/<KEY>/03-plan.md <changed files> \
       --wrote .copilot-wf/<KEY>/05-review.md
     ```
     Paste the usage table.

## Template — `05-review.md`

```markdown
# <KEY> — review · Verdict: APPROVE | CHANGES REQUIRED
Tests: <n passed / n failed> (baseline <…>) · Lint: ✅/❌ · Types/compile: ✅/❌

## AC coverage
| AC | Implemented in | Proven by test | Good / bad path covered |
## Findings
| # | Severity | Where | Problem | Why it matters | Suggested fix |
|---|---|---|---|---|---|
| 1 | blocker | `TransferController.java:42` | No test for 403 when user doesn't own the account | AC-3 unproven; authz regressions would ship silently | Add `@WebMvcTest` case … |
## Not checked / limitations
```
Severity: **blocker** (wrong behaviour, security/PII, AC missing) · **major** (untested AC path, architecture
violation, a11y failure) · **minor** (maintainability) · **nit** (optional).
