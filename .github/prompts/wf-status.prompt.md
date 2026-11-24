---
description: "Show where a ticket is in the workflow, plus its usage so far"
agent: agent
tools: ['execute']
argument-hint: "PROJ-1234"
---

Run `python3 tools/copilot-wf/wf.py status --ticket ${input:ticket:PROJ-1234}` and show its output unchanged.
Then name the next agent to select (`wf-<n>-<phase>`). Do nothing else.
