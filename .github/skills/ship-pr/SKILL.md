---
name: ship-pr
description: >
  With the user's explicit permission, commits the change, pushes the branch, and creates
  a pull request with a filled description on the first push, or updates the existing PR's
  description on later pushes. Use for "ship it", "commit and raise a PR", "update the PR",
  or Step 6 of the copilot workflow.
---

# Ship: commit, push, PR

Everything in this skill leaves the machine or changes shared state, so the user approves **one exact summary**
before anything happens.

## Iron laws
- NEVER commit, push, create or edit a PR before the user answers **yes** to the summary in step 4.
- NEVER push to `main`, `master`, `develop`, or `release/*`; never `--force`; never `--no-verify`; never merge the PR.
- NEVER stage with `git add -A` / `git add .`. Stage the listed files only.
- NEVER commit `.copilot-wf/`, `.env*`, credentials, or files containing secrets/PII.

## Steps

1. **Pre-flight**
   - Branch: `git branch --show-current`. If it's a protected branch, propose `<KEY>-<short-kebab-description>`.
   - Files: `git status --short`. Build the list to stage from `04-implementation.md`; flag anything unexpected.
   - Quick re-run of the changed tests (they must pass).
2. **Find an existing PR for this branch**
   - `scripts` mode: `gh pr view --json number,url,title,body` (no PR → "no pull requests found").
   - `mcp` mode: use the GitHub MCP tool that lists/searches PRs, filtered by head branch.
3. **Draft**
   - Commit message: `<KEY>: <imperative summary ≤ 72 chars>` + a short body saying *why*.
   - PR title: `<KEY>: <Short description>`.
   - PR body: use the repo's `.github/pull_request_template.md` if it exists, otherwise `templates/pr-body.md`.
     Fill it from `01-requirements.md`, `03-plan.md`, `04-implementation.md` and `05-review.md`.
   - **Existing PR:** keep the human-written parts. Replace only the block between
     `<!-- copilot-wf:start -->` and `<!-- copilot-wf:end -->`, and add a dated line to *Update log*.
4. **Ask permission.** Show exactly:
   ```
   Branch:        <branch> (new | existing)  → origin
   Files (N):     <list>
   Commit:        <message>
   PR:            CREATE "<title>"  |  UPDATE #<n> description
   PR body:       <collapsed preview>
   Proceed? (yes / edit / cancel)
   ```
   Wait for the answer. Anything other than a clear yes → don't run anything.
5. **Execute** (stop at the first error and report it; never retry with force):
   ```bash
   git switch -c <branch>            # only if a new branch was approved
   git add <file1> <file2> …
   git commit -m "<subject>" -m "<body>"
   git push -u origin <branch>
   ```
   - Create: `gh pr create --title "<title>" --body-file .copilot-wf/<KEY>/pr-body.md` (or the GitHub MCP create-PR tool)
   - Update: `gh pr edit <n> --body-file .copilot-wf/<KEY>/pr-body.md` (or the GitHub MCP update-PR tool)
6. **Report** the PR URL, then finish:
   ```bash
   python3 tools/copilot-wf/wf.py done --ticket <KEY> --phase ship \
     --read .copilot-wf/<KEY>/05-review.md --wrote .copilot-wf/<KEY>/pr-body.md
   ```
   Paste the usage table: it is the cost summary for the whole ticket.
