# Phase report: the contract between the orchestrator and a phase subagent

The orchestrator's context only ever holds **these reports**, never ticket text, Figma trees, diffs or test logs.
That's what keeps the main context clean. Everything detailed goes into files under `.copilot-wf/<KEY>/`.

## How a phase agent knows it's a subagent
The task message starts with **`[wf-orchestrator]`**. Then:

1. **You cannot talk to the user.** Wherever your skill says "ask the user", put the question in your report
   with `STATUS: NEEDS_INPUT` (or `AWAITING_APPROVAL` at a gate) and stop. The orchestrator asks, then calls you again.
2. **You are stateless.** Each call starts fresh. Re-read the ticket's files (`state.json` via `wf.py status`,
   and the `0x-*.md` artifacts) instead of assuming you remember anything.
3. **User answers arrive in the task message** under `USER ANSWERS:` or `USER APPROVAL:`. Use them exactly. Never invent an answer or approval.
4. **Run the same `wf.py` commands as always** (check / done). The gates apply to subagents too.
5. **Your final message is the report below and nothing else.** No preamble, no copy of the artifact.

## Report format (≤ 20 lines)

```
PHASE REPORT
ticket: <KEY>
phase: <analyze|design|plan|implement|review|ship>
status: DONE | NEEDS_INPUT | AWAITING_APPROVAL | CHANGES_REQUIRED | BLOCKED
artifact: <repo-relative path(s) you wrote>
summary:
  - <max 5 bullets a busy tech lead needs: decisions, counts, risks>
questions:            # only for NEEDS_INPUT / AWAITING_APPROVAL
  1. <question, with your recommended answer in brackets>
approval_request: |   # only for AWAITING_APPROVAL. Exactly what the user is approving (ship: the exact git/PR summary)
  ...
usage: <the stage's row from the table wf.py done printed, or "not recorded yet">
next: <next phase from wf.py, or "same phase again after input">
```

## Which status, when
| Phase | Typical status |
|---|---|
| analyze | `DONE`. `NEEDS_INPUT` only if an open question changes *what* gets built |
| design | `DONE`, or `NEEDS_INPUT` if no Figma frame link is available |
| plan | **`AWAITING_APPROVAL`** (plan written; `wf.py done` NOT run: the orchestrator records approval and completes the phase) |
| implement | `DONE`, or `BLOCKED` (3 failed attempts, gate refused, plan is wrong) |
| review | `DONE` (verdict APPROVE) or **`CHANGES_REQUIRED`** (blockers/majors: `wf.py done` NOT run) |
| ship, 1st call | **`AWAITING_APPROVAL`** with the exact commit/push/PR summary; nothing executed |
| ship, 2nd call (`USER APPROVAL:` present) | `DONE` with the PR URL, or `BLOCKED` with the git/gh error |
