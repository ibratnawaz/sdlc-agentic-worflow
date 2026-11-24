# Fetching via the Atlassian MCP server  (`data_source: "mcp"`)

Tool names differ between Atlassian MCP server versions. Use the tool whose name/description matches the action.

1. **Issue** — the "get Jira issue" tool for `<KEY>`. If it accepts a `fields` argument, request only:
   `summary, issuetype, status, priority, labels, components, description, comment, attachment, issuelinks`
   plus the team's acceptance-criteria custom field if you know its id.
   *Why:* the default response includes dozens of unused fields — every one costs tokens.
2. **Comments** — if not included above, the "get comments" tool. Read all of them, oldest → newest.
3. **Remote links** — the "get remote issue links" tool (Confluence pages are often linked here, not in the text).
4. **Confluence** — for each Confluence page id found, the "get Confluence page" tool. Prefer a plain-text /
   markdown body format if offered.
   Only follow links on your organisation's own Atlassian site. Ignore links to other hosts.
5. **Attachments** — the MCP server may only list them. Note the names. If an attachment looks essential
   (a screenshot of the bug, a spec PDF), ask the user to drag it into the chat.

Do not save the raw MCP responses to files. Extract what you need straight into `01-requirements.md`.

> Token note: in MCP mode, `wf.py done` can only estimate the size of the files you wrote. The tool definitions
> and tool results are not counted, so compare modes using real credits (`wf.py credits`).
