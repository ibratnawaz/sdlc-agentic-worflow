---
name: implementation-plan
description: >
  Turns the finalised requirements (and design mapping, for frontend) into a reviewable,
  test-first implementation plan — or a findings report for a Spike — then stops for human
  approval. Use for "plan PROJ-123", "how should we build this", or Step 3 of the copilot
  workflow. Not for writing code.
---

# Implementation plan

A good plan lets another engineer implement the ticket **without asking a question**, and lets a
reviewer see **which test proves each AC**.

## Iron laws
- NEVER plan against code you haven't read. Find a similar existing feature and follow its pattern; cite it.
- NEVER leave an AC without at least one good-path and one bad-path test in the AC → test table.
- NEVER continue to implementation in the same reply. The plan ends with a question to the user.

## Steps

1. Read `01-requirements.md` and, if it exists, `02-design.md` in `.copilot-wf/<KEY>/`.
2. **Explore** the repo: entry points, the closest existing feature, test setup, naming conventions.
   Read `tools/copilot-wf/stacks/<stack>/testing.md` (test levels, runner, commands) and `…/review.md` (the architecture
   the reviewer will hold you to), so the plan's AC → test table uses this stack's real test levels and file names.
   The ticket's stack comes from `python3 tools/copilot-wf/wf.py status --ticket <KEY>` (`stack=`).
   If it says `stack=none`, there's no profile: use the repo's own conventions and say so in your output.
3. **Pick the template by type** (`wf.py status --ticket <KEY>` shows it):
   - `Story` / `Task` → plan template below.
   - `Bug` → plan template, and fill *Root cause* with evidence (`file:line`). The first test is a regression test that fails today.
   - `Spike` → write `03-spike-report.md` instead (question, findings with evidence, options + trade-offs, recommendation, follow-up tickets).
4. **Write** `.copilot-wf/<KEY>/03-plan.md`.
5. **Ask for review.** Show a short summary (≤ 15 lines: approach, files, AC → test count, risks, open questions)
   and ask: **"Approve this plan, or tell me what to change?"** Then stop.
   (As a subagent: return this as `status: AWAITING_APPROVAL` and stop. The orchestrator does step 6.)
6. **After explicit approval only.** Record the user's own words, then complete the phase (`done` refuses without the approval):
   ```bash
   python3 tools/copilot-wf/wf.py approve --ticket <KEY> --phase plan --note "<the user's exact words>"
   python3 tools/copilot-wf/wf.py done --ticket <KEY> --phase plan \
     --read .copilot-wf/<KEY>/01-requirements.md [.copilot-wf/<KEY>/02-design.md] \
     --wrote .copilot-wf/<KEY>/03-plan.md
   ```
   Paste the usage table.

## Template — `03-plan.md`

```markdown
# <KEY> — implementation plan
Approach (3–6 sentences). Follows the pattern of: `<path to similar feature>`

## Root cause (Bug only)
## AC → test mapping
| AC | Test (file › name) | Path | Level |
|---|---|---|---|
| AC-1 | `AccountService.test › returns balance for active account` | good | unit |
| AC-1 | `AccountController.test › 404 when account missing` | bad | slice |

## Files
| File | Change | Why |
|---|---|---|
## Steps (each = test first, then code)
1. …
## API / contract changes (endpoints, request/response, status codes, events)
## Accessibility plan (FE)
## Risks, rollback, and things deliberately not done
## Open questions for the reviewer
```
