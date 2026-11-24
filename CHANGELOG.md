# Changelog

## v-2.1-angular: multi-language stacks (+ Angular)
- **Stack profiles:** `tools/copilot-wf/stacks/<stack>/` holds everything language-specific: `instructions.md`, `testing.md`,
  `review.md`, and `design.md` (FE). The skills are now generic and read the ticket's profile.
- **New: Angular profile** (standalone/signals/OnPush conventions, Karma/Jest/Vitest-neutral test patterns,
  HttpTestingController, Material/CDK a11y, Figma → inputs/outputs/content projection).
- React and Spring Boot specifics moved out of `.github/` into `stacks/react` and `stacks/spring-boot` (git history kept).
- `config.json → stacks`: deterministic detection rules. New `wf.py detect`, `wf.py stacks` (profile completeness), and
  `wf.py use-stack <stack…>` (installs `.github/instructions/<stack>.instructions.md`, refuses to overwrite hand edits,
  warns when two FE stacks overlap).
- `wf.py init` auto-detects the stack (`--stack` for monorepos). Side comes from the stack. `--side` still works for repos
  without a profile. `state.json` and `status` now include `stack`.
- **Migration from v-2.0:** run `wf.py use-stack <your stack>` once, because `.github/instructions/` no longer ships pre-filled.

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
