# Learning guide: how this workflow is designed, and why

Read it top to bottom once. Each section ends with **"See it in"**, pointing to the files that put the idea into practice.

---

## 1. Workflow or agent? Both: a workflow on the outside, agents on the inside

| Part | Who decides | Why |
|---|---|---|
| Order of steps, which steps run, gates | **Code** (`wf.py` + `config.json`) | Must always be true. Auditable. Can't be "talked out of" by a prompt |
| Reading tickets, mapping designs, planning, TDD loop, reviewing | **The AI** (agents + skills) | Needs judgment; every ticket is different |
| Approving the plan, approving the push | **You** | High-impact, hard to undo |

Rule of thumb: **if breaking a rule would be bad, enforce it in code, not just in a prompt.**
That's why `wf-4-implement` starts with `wf.py check`. The prompt says "don't code before the plan is approved",
and the script *refuses* if it wasn't.

**See it in:** `tools/copilot-wf/wf.py` (`select_phases`, `missing_before`), and step 1 of every agent file.

---

## 2. Copilot's building blocks, and what each costs in tokens

| Block | File | When it's loaded | Token cost |
|---|---|---|---|
| Repo instructions | `.github/copilot-instructions.md` | **Every request** | Paid on every turn, so keep it tiny |
| Path instructions | `.github/instructions/*.instructions.md` | When matching files are involved | Medium |
| Custom agent | `.github/agents/*.agent.md` | When you select that agent | Its body plus **its tools' definitions** |
| Skill | `.github/skills/*/SKILL.md` | Name and description always; body only when used | Low until used |
| Skill references | `skills/*/references/*.md` | Only if the skill says "read X" | Zero until needed |
| Prompt file | `.github/prompts/*.prompt.md` | When you type `/name` | Low |
| MCP tools | your MCP config | Their definitions go with **every request** of an agent that has them | Can be large |

**Agent vs skill**: the agent says **who** (model, tools, next step). The skill says **how** (method, iron laws, template).
Keeping them apart means you can switch a step's model without touching its method, and a skill like `code-review` also works on its own
("review my changes") outside the workflow.

**Iron laws + excuse table**: LLMs take shortcuts ("the fix is obvious, skip the test"). Naming the shortcut and answering it ahead of
time works much better than a general "be careful".

**See it in:** any `SKILL.md`, and the `wf-*.agent.md` files.

---

## 3. Does MCP use a lot of tokens? Yes, for two reasons

1. **Tool definitions.** Every tool an agent has (name + description + JSON schema) is sent with **every request in the agent loop**.
   An MCP server can expose dozens of tools. An agent with `atlassian/*` + `figma/*` + `github/*` can carry many thousands of tokens
   of definitions on every turn, even turns that don't use them.
2. **Tool results.** A raw Jira issue (every field, rendered HTML, metadata) or a Figma node tree can be far larger than the few
   facts you need, and it then stays in the conversation history for the rest of the step.

### Ways to reduce it (in order of effort)
1. **Give each agent only the MCP servers it needs.** Already done here: only Step 1 has Atlassian, only Step 2 has Figma,
   only Step 6 has GitHub. Steps 3–5 have none.
2. **Narrow `/*` to specific tools** in `config.json → mcp_tools` (e.g. `atlassian/getJiraIssue`), then run `wf.py sync`.
3. **Ask for less**: request specific fields and one Figma frame, not the whole file (the skills already say so).
4. **Scripts mode**: deterministic scripts fetch → **trim** → save small markdown files; the agent reads the files.
   There are no MCP tool definitions at all.

### One workflow with a switch, not two copies
Only Steps 1, 2 and 6 fetch data, so one `data_source` switch is enough. Two full copies would slowly drift apart.

| | MCP mode | Scripts mode |
|---|---|---|
| Setup | MCP config in the IDE | env vars + `gh` CLI |
| Tokens | higher (definitions + raw results) | lower (trimmed files) |
| Flexibility | AI can explore anything the server offers | only what the script fetches |
| Figma quality | Dev Mode context (can include code hints) | structure, components, styles, PNG |
| Maintenance | none (vendor maintains it) | you own ~400 lines of Python + tests |
| Determinism | AI decides what to call | same input → same output, unit-tested |

### Measure it yourself, don't guess
Run the **same ticket** through both modes, log the real credits after each step (§4), and compare `wf.py status` tables.

**See it in:** `config.json` (`data_source`, `mcp_tools`), `wf.py sync`, `jira_fetch.py`, `figma_fetch.py`,
`skills/ticket-analysis/references/fetch-*.md`.

---

## 4. Showing token / credit usage after each step

Since June 2026, Copilot Business/Enterprise usage is billed in **AI Credits**, calculated from tokens and the model used.
An agent **cannot read its own exact token count**, so the workflow uses two numbers:

| Number | Where it comes from | Accuracy |
|---|---|---|
| **Estimate** | `wf.py done` counts the characters of files the step read and wrote (÷ 4) | Lower bound. Misses the system prompt, tool definitions and chat history |
| **Real credits** | VS Code: hover the **context-window circle** in the chat input. The session popover shows credits and tokens | Exact |

Record the real number so the table holds both:
```bash
python3 tools/copilot-wf/wf.py credits --ticket PROJ-1234 --phase analyze --value 37
```
The estimate is still useful: it shows *which file* was big (e.g. a 40k-token Confluence page), which tells you what to trim.

**See it in:** `wf.py` → `cmd_done`, `render_usage_table`, `cmd_credits`.

---

## 5. Choosing a model for each step

### The criteria
1. **How much reasoning does it need?** Ambiguous, high-level decisions (planning, finding subtle bugs) gain the most from a stronger model.
2. **How costly is a mistake downstream?** A wrong plan leads to wrong code, tests and review. A clumsy PR description costs nothing.
3. **How many tokens does it use?** Implementation loops many times (run tests, read errors, edit). Price × volume adds up fastest here.
4. **Does it need vision?** Step 2 reads Figma screenshots, so it needs a multimodal model.
5. **Different perspective.** The reviewer should be a **different model family** from the implementer so they don't share blind spots.
6. **Availability and policy.** Only models your org has enabled count. Check the model picker.

### The default choice here
| Step | Tier | Why |
|---|---|---|
| 1 Analyze | balanced | Careful reading and extraction; moderate reasoning |
| 2 Design | balanced (vision) | Matching against the repo; needs to see images |
| 3 Plan | **deep** | Short output, but every later step depends on it, so it's the best place to spend |
| 4 Implement | balanced | Strong at code, affordable across many loop turns |
| 5 Review | **second-opinion** | Strong *and* a different family from Step 4 |
| 6 Ship | fast | Mechanical: git commands and a template |

### Tuning it
Tiers live in `config.json → models`. Change a tier or a stage, run `python3 tools/copilot-wf/wf.py sync`, and every agent file updates.
Then run 3–5 real tickets and compare **quality** (review findings, rework) against **credits** (the usage table). Move a step down a tier if
quality holds, or up a tier if it doesn't.

---

## 6. VS Code vs IntelliJ

The same files work in both. Differences to know:
- **Handoff buttons** (`handoffs:` in agent files) are a VS Code feature. In IntelliJ, you pick the next agent yourself. Each step tells you which.
- JetBrains support for custom agents, skills and prompt files reached general availability during 2026, but details still change. If something
  doesn't load, check GitHub's *Copilot customization cheat sheet* for your plugin version.
- The `tools:` names (`read`, `edit`, `search`, `execute`, `todo`) are VS Code's built-in tool sets. Unknown names are ignored, not errors.

---

## 7. Exercises (do them in order)

1. **Dry run.** In a sandbox repo, run `wf.py init --ticket DEMO-1 --type Bug --side be`, then `check --phase implement`. Why is it blocked?
2. **Change the rules.** Add a new type `Hotfix` with phases `analyze, implement, review, ship`. Add a test in `tests/test_wf.py` first, then make it pass.
3. **Trim more.** Narrow `atlassian/*` to the 3–4 tools Step 1 actually calls, run `wf.py sync`, and compare credits on the same ticket.
4. **Strengthen a gate.** Make `wf.py done --phase review` refuse unless `.copilot-wf/<KEY>/05-review.md` contains `Verdict: APPROVE`.
   (This turns a prompt rule into a code rule.)
5. **New skill.** Write a `sonar-fix` or `api-contract-check` skill. Write the `description` first (when it should and shouldn't trigger).
6. **A/B the models.** Run Step 5 with two different models on the same diff. Which finds more *real* issues per credit?
