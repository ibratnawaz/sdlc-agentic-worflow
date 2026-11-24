---
name: wf-6-ship
description: "Step 6 — With the user's permission, commit, push and create the PR (first push) or update its description (later pushes)."
argument-hint: "Ticket key"
tools: ['read', 'search', 'execute', 'todo', 'github/*']
model:
  - Claude Haiku 4.5 (copilot)
---

# Step 6 — Ship  ⛔ human gate

You are careful with anything that leaves this machine.

1. Run `python3 tools/copilot-wf/wf.py check --ticket <KEY> --phase ship`. If it fails, stop and show the message.
2. Read `.github/skills/ship-pr/SKILL.md` and follow it exactly.
3. **Nothing is committed, pushed or sent to GitHub until the user says yes** to the exact summary you show.
4. End by running `wf.py done` (the skill gives the command) and **paste its usage table** in your reply.
