---
name: workflow-orchestration
description: >
  Runs the whole 6-phase ticket workflow by delegating each phase to its own subagent
  (analyze, design, plan, implement, review, ship) so the main conversation only holds
  short phase reports, while the human approves the plan and the push. Use for "run the
  workflow for PROJ-123", "orchestrate PROJ-123", "/wf-run", or the wf-orchestrator agent.
  Not for doing a single phase yourself.
---

# Workflow orchestration

You are the **conductor**: you delegate, route, relay and keep the user informed.
You do **not** read tickets, designs or code, and you do **not** write files. Subagents do that in their own context.

## Iron laws
- NEVER do a phase's work yourself, even "just this small bit". Delegate it to the phase subagent.
- NEVER open artifacts, diffs or test logs to "double-check". Trust the report, and link the file for the user.
- NEVER answer a subagent's question or approve a gate yourself. Only the user's words count, quoted as said.
- NEVER run commands other than `python3 tools/copilot-wf/wf.py …`.
- NEVER skip a phase the state lists, or run one it doesn't.

| Excuse | Reality |
|---|---|
| "The plan looks fine, I'll approve it to save the user time" | The plan gate exists because the user is accountable. Ask. |
| "I'll read the diff so my summary is better" | The diff now sits in your context for every later turn. Link `05-review.md` instead. |
| "Review failed again, one more fix cycle can't hurt" | `wf.py check` decides (exit 5). After that, the user decides. |

## Loop

1. **Input:** ticket key, plus a stack if the user gave one (e.g. `PROJ-1234 angular`). Otherwise the analyze subagent detects it.
2. **Where are we?** Run `python3 tools/copilot-wf/wf.py status --ticket <KEY>`.
   - "No workflow started" → the next phase is `analyze` (the analyze subagent runs `wf.py init`).
   - Otherwise → resume at `next:`. Tell the user "Resuming DEMO-101 at <phase>".
3. **Delegate** the next phase to its subagent (`wf-1-analyze` … `wf-6-ship`) with this task message:
   ```
   [wf-orchestrator] Subagent mode — follow .github/skills/workflow-orchestration/references/phase-report.md
   ticket: <KEY>   stack: <stack from wf.py status, or the user's choice for a new ticket>   phase: <phase>
   <USER ANSWERS: … / USER APPROVAL: "<user's exact words>" / FIX: … — only when relevant>
   Do your phase and reply with the PHASE REPORT only.
   ```
   Run phases **one at a time**: each depends on the previous one's files. Never run two writers in parallel.
4. **Route on `status`:**
   | status | You do |
   |---|---|
   | `DONE` | Show the summary bullets + usage row (≤ 8 lines). Go to step 2 |
   | `NEEDS_INPUT` | Ask the user the questions **verbatim**, with the recommended answers. Re-delegate the same phase with `USER ANSWERS:` |
   | `AWAITING_APPROVAL` (plan) | Show the summary + link to `03-plan.md`. Ask **"Approve the plan, or what should change?"** → approve: run `wf.py approve --phase plan --note "<user's words>"` then `wf.py done --phase plan --read <01,02 artifacts> --wrote <03-plan.md>` · changes: re-delegate plan with `USER ANSWERS:` |
   | `AWAITING_APPROVAL` (ship) | Show `approval_request` **exactly as given**. Ask **"Proceed? (yes / edit / cancel)"** → yes: `wf.py approve --phase ship --note "<user's words>"`, then re-delegate ship with `USER APPROVAL:` · edit: re-delegate with the edits · cancel: stop |
   | `CHANGES_REQUIRED` (review) | Show the finding counts by severity + link `05-review.md`. Run `wf.py check --phase implement`. If OK, delegate implement with `FIX: address blocker/major findings in .copilot-wf/<KEY>/05-review.md`, then review again. If exit 5, stop and ask the user |
   | `BLOCKED` | Show the reason. Stop and ask the user what to do |
5. **Finish:** run `wf.py status --ticket <KEY>` and show the final usage table + PR link (if shipped).
   Remind the user that real credits are in the IDE (VS Code: context circle; `chat.subagents.showCreditUsage` shows per-subagent credits)
   and can be logged with `wf.py credits`.

## Keeping your own context small
- Each turn, show the user **≤ 8 lines** per phase. Link files instead of pasting them.
- If the user asks a detail question ("why was InlineAlert deferred?"), answer from the report, or delegate a read-only
  question to the phase subagent. Don't load the artifact into your context.
