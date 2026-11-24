# Repository rules for Copilot

<!-- This file is sent with EVERY request, so every line costs tokens on every turn.
     Keep it short. Put stack detail in .github/instructions/ (loaded only for matching files)
     and process detail in .github/skills/ (loaded only when needed). -->

## Workflow
- Ticket work follows the 6-phase workflow in `.github/agents/wf-*.agent.md`.
- Workflow state and phase gates are owned by `tools/copilot-wf/wf.py`. Never edit `.copilot-wf/*/state.json` by hand.
- Workflow artifacts live in `.copilot-wf/<TICKET>/` and are never committed.

## Always
- Tests first (TDD). Never mark work done while a test fails.
- Never invent ticket content, design details, file paths or APIs you have not read.
- Ask before: commit, push, creating/updating a PR, adding a dependency.

## Never
- Commit secrets, tokens, `.env` files, or real customer data (this is financial-services code).
- Log PII (names, emails, account numbers, SSNs, addresses).
- Push to `main`/`master`/`release/*`, force-push, or use `--no-verify`.
- Hardcode internal URLs, hostnames, or credentials.
