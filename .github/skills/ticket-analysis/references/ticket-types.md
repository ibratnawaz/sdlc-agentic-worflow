# Mapping Jira issue types → workflow types

The AI decides the *type*. `config.json → phase_sets` decides the *phases*. Keep it that way.

| Jira issue type (examples) | Workflow type | Why |
|---|---|---|
| Story, User Story, Feature | `Story` | User-facing behaviour with ACs |
| Task, Sub-task, Improvement, Tech Debt, Chore | `Task` | Work with a clear outcome, often no user story |
| Bug, Defect, Production Issue | `Bug` | Expected ≠ actual; needs a regression test first |
| Spike, Research, Investigation, POC | `Spike` | Answers a question; no production code, no PR |

Rules:
- A Sub-task inherits nothing automatically. Classify by what *it* asks for.
- If the Jira type and the content disagree (a "Task" that is clearly a defect), say so and ask the user which to use.
- A Spike that ends with "and implement it" is two tickets. Recommend splitting; don't widen the spike.
