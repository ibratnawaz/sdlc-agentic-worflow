---
name: ticket-analysis
description: >
  Reads a Jira ticket (type, description, acceptance criteria, comments, attachments)
  and any Confluence pages it links, then writes a finalised, testable statement of
  what needs to be done. Use for "analyze PROJ-123", "what does PROJ-123 need",
  "read this ticket", or Step 1 of the copilot workflow. Not for planning or coding.
---

# Ticket analysis

The output of this skill is the **contract** every later step is checked against.
A vague or invented AC here becomes wrong code in Step 4 and a missed bug in Step 5.

## Iron laws
- NEVER invent an AC, field, or comment you did not read. If something is missing, write it under *Open questions*.
- NEVER silently resolve a conflict (e.g. a comment changes an AC). List it and say which source you followed.
- NEVER paste credentials, tokens, or customer data into files or chat. Attachments may contain PII — summarise, don't copy.
- NEVER ask the user to paste an API token into chat. Tokens live in environment variables only.

| Excuse | Reality |
|---|---|
| "The description is clear enough, I'll skip comments" | Comments are where ACs change. Read all of them. |
| "There are no ACs, I'll write sensible ones" | Derive *candidate* ACs and mark them `(derived — confirm)`. |
| "The Confluence page is long, I'll skim the title" | Read the sections relevant to this ticket; cite them. |

## Steps

1. **Ticket key and stack.** Get the key (`[A-Z][A-Z0-9]+-\d+`) from the user. Find the stack with code, not guesswork:
   ```bash
   python3 tools/copilot-wf/wf.py detect
   ```
   One stack → use it. Several (monorepo) → ask the user which one this ticket touches, or take it from the user's message.
   None → ask the user, or continue with `--side fe|be` (generic guidance only).
2. **Fetch.** Read `data_source` in `tools/copilot-wf/config.json`, then follow
   `references/fetch-mcp.md` or `references/fetch-scripts.md`.
   You need: type, status, summary, description, ACs, every comment, attachments list, linked issues,
   Confluence links (description, comments, remote links), Figma links.
3. **Classify** using `references/ticket-types.md` → one of `Story | Task | Bug | Spike`.
4. **Start the workflow** (deterministic phase selection):
   ```bash
   python3 tools/copilot-wf/wf.py init --ticket <KEY> --type <Type> [--stack <stack>] [--figma]
   ```
   Pass `--stack` when you had to choose (monorepo), and `--figma` only if a Figma link exists. The side (fe/be) comes from
   the stack. Show the user the phase list it prints.
5. **Write** `.copilot-wf/<KEY>/01-requirements.md` using the template below.
6. **Open questions.** If any open question would change *what* gets built, ask the user now and update the file.
   Minor questions can wait for the plan review.
7. **Finish:**
   ```bash
   python3 tools/copilot-wf/wf.py done --ticket <KEY> --phase analyze \
     --read <files under .copilot-wf/<KEY>/source/ if any> \
     --wrote .copilot-wf/<KEY>/01-requirements.md
   ```
   Paste the usage table it prints, then a 5-line summary of the requirements.

## Template — `01-requirements.md`

```markdown
# <KEY>: <summary>
Type: <Story|Task|Bug|Spike> (Jira: <original issue type>) · Stack: <stack> (<FE|BE>) · Status: <status>

## What needs to be done
<2–5 sentences in plain language. For a Bug: expected vs actual behaviour + repro steps.>

## Acceptance criteria
| ID | Given / When / Then | Source |
|---|---|---|
| AC-1 | … | description / comment by <role> on <date> / derived — confirm |

### Bad paths to cover (derived from ACs)
- AC-1-x: <invalid input / missing data / unauthorised / downstream failure> → <expected behaviour>

## Out of scope
## Conflicts found (and which source was followed)
## Open questions
## Sources read
- Jira <KEY> (N comments, M attachments)
- Confluence: <title> (page id) — sections used: …
- Figma: <links> (used in Step 2)
```
