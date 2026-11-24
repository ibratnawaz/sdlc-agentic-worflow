---
description: "Run the whole workflow for a ticket with the orchestrator (one subagent per phase, clean contexts)"
agent: wf-orchestrator
argument-hint: "PROJ-1234 [stack]"
---

Run the workflow for: ${input:ticket:PROJ-1234}

Start or resume from the ticket's current phase, as your instructions say.
