# Fetching via scripts  (`data_source: "scripts"`)

The script calls the Jira/Confluence REST API, keeps only the fields this workflow needs,
and writes small markdown files. You read the files instead of raw API JSON.

```bash
python3 tools/copilot-wf/jira_fetch.py <KEY> --follow-confluence
# add --download-attachments if screenshots/logs matter (images only, size-capped)
```

Outputs (in `.copilot-wf/<KEY>/source/`):
- `jira.md` — type, status, description, ACs, all comments, attachments list, links, Figma links found
- `confluence-<pageId>.md` — one per linked page on your own Confluence site
- `attachments/` — only with `--download-attachments`

Then read those files and continue with the skill.

## If the script fails
- **Missing environment variable** — tell the user which one (the script prints it) and point them to
  `README.md → Scripts mode setup`. Do **not** ask for the token value in chat.
- **401/403** — the token is wrong or lacks permission. The user fixes it; you stop.
- **404** — wrong key, or no access to that project. Ask the user to confirm the key.
