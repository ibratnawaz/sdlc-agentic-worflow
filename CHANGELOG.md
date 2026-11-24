# Changelog

## v-2.0: orchestrator and context isolation
- **New `wf-orchestrator` agent** (`/wf-run PROJ-1234 fe`) runs every phase as a subagent in its own context window. The main
  chat only holds short *phase reports*. It resumes from `wf.py status` if interrupted.
- **New skill `workflow-orchestration`** holds the conductor's loop and the phase-report contract between orchestrator and subagents.
- **Phase agents** gained a "subagent mode": they never ask the user directly. They return `NEEDS_INPUT` / `AWAITING_APPROVAL` /
  `CHANGES_REQUIRED` / `BLOCKED` instead.
- **Code-enforced approvals:** `wf.py approve --phase plan|ship --note "<user's words>"`. `done --phase plan|ship` refuses without
  one, and `check --phase ship --approved` gates the first git command.
- **Fix-cycle cap:** `max_fix_cycles` (default 2) in `config.json`. `check --phase implement` exits 5 when it's reached.
- **Usage accumulates** across re-runs (new *Runs* column) instead of being overwritten. `status` now prints `next:` for resume.
- `wf.py sync` also manages the orchestrator's model (`orchestrate` stage → `fast` tier).
- Step-by-step mode (v1 style) still works unchanged. One manual-mode change: approve the plan with `wf.py approve` before `done`.
- Backward compatible with v1 `state.json` files (no `approvals` key).

## v-1.0
- 6 phase agents + skills, `wf.py` gates and usage table, MCP/scripts switch, Jira/Confluence/Figma fetch scripts, fixtures, tests.
