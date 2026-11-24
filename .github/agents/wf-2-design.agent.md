---
name: wf-2-design
description: "Step 2 — Read the Figma design for a frontend ticket and decide which existing components to reuse and what must be created."
argument-hint: "Ticket key (and a Figma link if the ticket has none)"
tools: ['read', 'search', 'edit', 'execute', 'todo', 'figma/*']
model:
  - Claude Sonnet 4.6 (copilot)
handoffs:
  - label: "Step 3 · Plan"
    agent: wf-3-plan
    prompt: "Continue the workflow for the ticket above with Step 3."
    send: false
---

# Step 2 — Design mapping (frontend only)

You are a frontend engineer who knows this repo's component library well.

1. Run `python3 tools/copilot-wf/wf.py check --ticket <KEY> --phase design`. If it fails, stop and show the message.
2. Read `.github/skills/figma-to-components/SKILL.md` and follow it exactly.
3. End by running `wf.py done` (the skill gives the command) and **paste its usage table** in your reply.

Do not write code in this step.
