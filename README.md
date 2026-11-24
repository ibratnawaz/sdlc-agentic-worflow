# Copilot full-stack workflow

A 6-step, human-gated workflow for GitHub Copilot (VS Code for React/TS, IntelliJ for Spring Boot):

```
1 Analyze ──► 2 Design ──► 3 Plan ──⛔ you approve ──► 4 Implement (TDD) ──► 5 Review ──⛔ you approve ──► 6 Ship
 Jira +        Figma →      AC→test     plan            red→green→refactor     different      commit/push/PR
 Confluence    components   mapping                     + accessibility        model          create or update
                (FE only)
```

After every step you see a usage table (an estimate, plus the real credits if you log them).
To learn *why* it's built this way, read **[LEARNING.md](LEARNING.md)**.

## What's inside

```
.github/
├── copilot-instructions.md     always-on rules (kept short: costs tokens on every request)
├── instructions/               stack rules, loaded only for matching files
│   ├── react-ts.instructions.md      applyTo **/*.ts,tsx
│   └── spring-boot.instructions.md   applyTo **/*.java
├── agents/                     WHO does each step: model, tools, handoff buttons
│   └── wf-1-analyze … wf-6-ship.agent.md
├── skills/                     HOW each step is done: method, iron laws, templates
│   ├── ticket-analysis/  figma-to-components/  implementation-plan/
│   └── tdd-implementation/  code-review/  ship-pr/
└── prompts/                    slash commands: /wf-start, /wf-status
tools/copilot-wf/               deterministic code (no AI)
├── config.json                 phase sets, mcp/scripts switch, model tiers
├── wf.py                       state, gates, usage table, sync
├── jira_fetch.py               scripts mode: Jira + Confluence → trimmed markdown
├── figma_fetch.py              scripts mode: one Figma frame → compact outline (+PNG)
└── tests/                      python3 -m unittest discover tools/copilot-wf/tests
```

## Install into a repo (FE repo and BE repo separately)

1. Copy `.github/` and `tools/` into the repo root. If the repo already has `.github/copilot-instructions.md`, **merge**
   the two files instead of overwriting yours.
2. Add the artifacts folder to `.gitignore` (it holds ticket content and must never be committed):
   ```
   .copilot-wf/
   ```
3. Replace the example conventions in `.github/instructions/*.instructions.md` with your team's real ones.
4. Make the MCP server names match: the agents use `atlassian/*`, `figma/*`, `github/*`. If your MCP config names
   the servers differently, edit `mcp_tools` in `tools/copilot-wf/config.json`, then run `python3 tools/copilot-wf/wf.py sync`.
5. Check the model names in `config.json → models.tiers` against your Copilot model picker, then run `wf.py sync`.

## Use it

**VS Code (frontend)**: in Copilot Chat run `/wf-start PROJ-1234 fe`, then click the handoff button at the end of each
step (e.g. *Step 3 · Plan*). Or pick `wf-1-analyze` … `wf-6-ship` from the agent picker.

**IntelliJ (backend)**: select the `wf-1-analyze` agent in Copilot Chat and type `PROJ-1234 be`. At the end of each step,
select the agent it names next (handoff buttons are a VS Code feature). `/wf-start` also works where prompt files are supported.

Anytime: `/wf-status PROJ-1234`, or run `python3 tools/copilot-wf/wf.py status --ticket PROJ-1234`.
(On Windows use `python` or `py` instead of `python3`.)

## MCP mode vs scripts mode

```jsonc
// tools/copilot-wf/config.json
"data_source": "mcp"      // or "scripts"
```
Then run `python3 tools/copilot-wf/wf.py sync`. That also adds or removes the MCP tools on the agents.
LEARNING.md §3 explains the trade-off and how to measure it.

### Scripts mode setup

Set these as **environment variables** (shell profile, or your OS keychain/secret manager). Never in a file in the repo:

| Variable | For | Notes |
|---|---|---|
| `JIRA_BASE_URL` | Jira | your Jira site, `https://…` |
| `JIRA_PAT` | Jira Data Center/Server | **or** the pair below |
| `JIRA_EMAIL` + `JIRA_API_TOKEN` | Jira Cloud | |
| `JIRA_AC_FIELD` | optional | custom field id holding ACs, e.g. `customfield_12345` |
| `CONFLUENCE_BASE_URL` | optional | defaults to `<JIRA_BASE_URL>/wiki` on `*.atlassian.net` |
| `CONFLUENCE_PAT` | optional | Confluence Data Center token |
| `FIGMA_TOKEN` | Figma | personal access token, read-only scope |
| — | GitHub | `gh auth login` once (the `gh` CLI) |

Try it by hand:
```bash
python3 tools/copilot-wf/jira_fetch.py PROJ-1234 --follow-confluence
python3 tools/copilot-wf/figma_fetch.py "https://www.figma.com/design/<key>/<name>?node-id=1-2" --ticket PROJ-1234 --image
```

## Safety built in
- Credentials only from env vars; never printed; only sent to the host they belong to; HTTPS only.
- Confluence links on other hosts are ignored. Attachments are downloaded only from your Jira host, images/text only, max 5 MB.
- `wf.py check` blocks a phase until the earlier ones are done (e.g. no coding before the plan is approved).
- Step 6 shows one exact summary and does nothing until you say yes. No force-push, no `--no-verify`, no pushes to protected branches, no merging.
