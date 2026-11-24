#!/usr/bin/env python3
"""Fetch a Jira ticket (+ linked Confluence pages) and save TRIMMED markdown.

This is the "scripts" alternative to the Atlassian MCP server. The AI reads a few KB of
markdown instead of large raw JSON responses and tool definitions.

Usage:
  python3 tools/copilot-wf/jira_fetch.py PROJ-1234 [--follow-confluence] [--download-attachments]
  python3 tools/copilot-wf/jira_fetch.py DEMO-101 --follow-confluence --fixture <file.json>   # offline

Environment (never hardcode these, never commit them):
  JIRA_BASE_URL         e.g. https://<your-jira-host>         (required)
  JIRA_PAT              personal access token  → Bearer auth  (Jira Data Center / Server)
  or JIRA_EMAIL + JIRA_API_TOKEN                → Basic auth  (Jira Cloud)
  JIRA_AC_FIELD         optional custom field id holding ACs, e.g. customfield_12345
  CONFLUENCE_BASE_URL   optional; defaults to JIRA_BASE_URL + /wiki for *.atlassian.net
  CONFLUENCE_PAT        optional; Data Center Confluence token (Cloud reuses the Jira email/token)
"""

from __future__ import annotations

import argparse
import base64
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import quote

from _common import (FetchError, approx_tokens, die, env, host_of, http_get, http_get_json,
                     safe_filename, same_host, ticket_source_dir)

FIELDS = ["summary", "issuetype", "status", "priority", "labels", "components", "description",
          "comment", "attachment", "issuelinks", "parent"]
MAX_PAGE_CHARS = 30_000
MAX_ATTACHMENT_BYTES = 5 * 1024 * 1024
DOWNLOADABLE = ("image/", "text/plain")

URL_RE = re.compile(r"https://[^\s|\]\)>\"'<]+")
FIGMA_RE = re.compile(r"https://(?:www\.)?figma\.com/(?:file|design|proto)/[^\s|\]\)>\"'<]+")


# ── pure functions (unit-tested) ─────────────────────────────────────────────

def auth_headers(pat: str | None, email: str | None, token: str | None) -> dict[str, str]:
    if pat:
        return {"Authorization": f"Bearer {pat}"}
    if email and token:
        b64 = base64.b64encode(f"{email}:{token}".encode()).decode()
        return {"Authorization": f"Basic {b64}"}
    raise ValueError("Set JIRA_PAT, or JIRA_EMAIL and JIRA_API_TOKEN")


def default_confluence_base(jira_base: str) -> str | None:
    return jira_base.rstrip("/") + "/wiki" if host_of(jira_base).endswith(".atlassian.net") else None


def find_confluence_page_ids(text: str, confluence_base: str | None) -> list[str]:
    """Page ids from Confluence URLs that live on OUR Confluence host only."""
    if not confluence_base:
        return []
    ids: list[str] = []
    for url in URL_RE.findall(text or ""):
        if not same_host(url, confluence_base):
            continue  # never send our credentials to someone else's server
        m = re.search(r"/pages/(\d+)", url) or re.search(r"[?&]pageId=(\d+)", url)
        if m and m.group(1) not in ids:
            ids.append(m.group(1))
    return ids


def find_figma_links(text: str) -> list[str]:
    out: list[str] = []
    for u in FIGMA_RE.findall(text or ""):
        if u not in out:
            out.append(u)
    return out


def adf_to_text(node) -> str:
    """Minimal Atlassian Document Format → text (Cloud rich-text fields can arrive as ADF)."""
    if node is None:
        return ""
    if isinstance(node, str):
        return node
    if isinstance(node, list):
        return "".join(adf_to_text(n) for n in node)
    t = node.get("type")
    if t == "text":
        return node.get("text", "")
    if t == "hardBreak":
        return "\n"
    inner = adf_to_text(node.get("content", []))
    if t in ("paragraph", "heading"):
        return inner + "\n\n"
    if t == "listItem":
        return "- " + inner.strip() + "\n"
    if t in ("inlineCard", "blockCard"):
        return node.get("attrs", {}).get("url", "")
    return inner


class _StorageToText(HTMLParser):
    """Confluence 'storage' XHTML → readable plain text with light markdown."""

    BLOCK = {"p", "div", "tr", "br", "table", "ul", "ol"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.out: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            self.out.append("\n" + "#" * int(tag[1]) + " ")
        elif tag == "li":
            self.out.append("\n- ")
        elif tag in ("td", "th"):
            self.out.append(" | ")
        elif tag == "a":
            href = dict(attrs).get("href")
            if href:
                self.out.append(f" <{href}> ")
        elif tag in self.BLOCK:
            self.out.append("\n")

    def handle_endtag(self, tag):
        if tag in ("h1", "h2", "h3", "h4", "h5", "h6", "p", "tr"):
            self.out.append("\n")

    def handle_data(self, data):
        self.out.append(data)


def storage_to_text(html: str) -> str:
    p = _StorageToText()
    p.feed(html or "")
    text = "".join(p.out)
    text = re.sub(r"[ \t]+", " ", text)
    return re.sub(r"\n\s*\n\s*\n+", "\n\n", text).strip()


def render_issue_md(issue: dict, remote_links: list[dict], ac_field: str | None) -> str:
    f = issue.get("fields", {})
    name = lambda x: (x or {}).get("name", "—")  # noqa: E731
    lines = [
        f"# {issue.get('key')}: {f.get('summary', '')}",
        f"Type: {name(f.get('issuetype'))} · Status: {name(f.get('status'))} · Priority: {name(f.get('priority'))}",
        f"Labels: {', '.join(f.get('labels') or []) or '—'} · "
        f"Components: {', '.join(c.get('name', '') for c in f.get('components') or []) or '—'}",
    ]
    if f.get("parent"):
        lines.append(f"Parent: {f['parent'].get('key')} — {f['parent'].get('fields', {}).get('summary', '')}")
    lines += ["", "## Description", adf_to_text(f.get("description")).strip() or "_(empty)_"]
    if ac_field:
        lines += ["", "## Acceptance criteria (field)", adf_to_text(f.get(ac_field)).strip() or "_(empty)_"]

    comments = (f.get("comment") or {}).get("comments", [])
    lines += ["", f"## Comments ({len(comments)}, oldest first)"]
    for c in comments:
        author = (c.get("author") or {}).get("displayName", "unknown")
        lines += [f"### {author} · {str(c.get('created', ''))[:10]}", adf_to_text(c.get("body")).strip(), ""]

    atts = f.get("attachment") or []
    lines += ["", f"## Attachments ({len(atts)})"]
    lines += [f"- {a.get('filename')} ({a.get('mimeType')}, {a.get('size', 0) // 1024} KB)" for a in atts] or ["—"]

    links = f.get("issuelinks") or []
    lines += ["", "## Linked issues"]
    for l in links:
        other = l.get("outwardIssue") or l.get("inwardIssue") or {}
        rel = (l.get("type") or {}).get("outward" if "outwardIssue" in l else "inward", "relates to")
        lines.append(f"- {rel} {other.get('key')}: {other.get('fields', {}).get('summary', '')}")
    if not links:
        lines.append("—")

    lines += ["", "## Remote links"]
    lines += [f"- {(r.get('object') or {}).get('title', '')}: {(r.get('object') or {}).get('url', '')}"
              for r in remote_links] or ["—"]
    return "\n".join(lines).strip() + "\n"


def all_text(issue: dict, remote_links: list[dict], ac_field: str | None) -> str:
    f = issue.get("fields", {})
    parts = [adf_to_text(f.get("description"))]
    if ac_field:
        parts.append(adf_to_text(f.get(ac_field)))
    parts += [adf_to_text(c.get("body")) for c in (f.get("comment") or {}).get("comments", [])]
    parts += [(r.get("object") or {}).get("url", "") for r in remote_links]
    return "\n".join(parts)


# ── I/O ─────────────────────────────────────────────────────────────────────

class ApiSource:
    """Live Jira/Confluence over HTTPS, credentials from env vars."""

    def __init__(self, ticket: str) -> None:
        self.ticket = ticket
        self.base = env("JIRA_BASE_URL").rstrip("/")
        try:
            self.headers = auth_headers(env("JIRA_PAT", False), env("JIRA_EMAIL", False), env("JIRA_API_TOKEN", False))
        except ValueError as e:
            die(str(e))
        self.ac_field = env("JIRA_AC_FIELD", False)
        self.conf_base = (env("CONFLUENCE_BASE_URL", False) or default_confluence_base(self.base) or "").rstrip("/")
        conf_pat = env("CONFLUENCE_PAT", False)
        self.conf_headers = {"Authorization": f"Bearer {conf_pat}"} if conf_pat else self.headers

    def issue(self) -> dict:
        fields = ",".join(FIELDS + ([self.ac_field] if self.ac_field else []))
        return http_get_json(f"{self.base}/rest/api/2/issue/{quote(self.ticket)}?fields={fields}", self.headers)

    def remote_links(self) -> list[dict]:
        r = http_get_json(f"{self.base}/rest/api/2/issue/{quote(self.ticket)}/remotelink", self.headers)
        return r if isinstance(r, list) else []

    def page(self, pid: str) -> dict:
        return http_get_json(f"{self.conf_base}/rest/api/content/{pid}?expand=body.storage,version", self.conf_headers)


class FixtureSource:
    """Offline: the same data read from a JSON file (demos, tests, no credentials needed).

    Shape: {"jira_base", "confluence_base", "ac_field"?, "issue", "remote_links", "confluence_pages": {id: page}}
    """

    def __init__(self, path: str) -> None:
        self.data = json.loads(Path(path).read_text(encoding="utf-8"))
        self.base = self.data["jira_base"].rstrip("/")
        self.conf_base = (self.data.get("confluence_base") or "").rstrip("/")
        self.ac_field = self.data.get("ac_field")
        self.headers: dict[str, str] = {}

    def issue(self) -> dict:
        return self.data["issue"]

    def remote_links(self) -> list[dict]:
        return self.data.get("remote_links", [])

    def page(self, pid: str) -> dict:
        if pid not in self.data.get("confluence_pages", {}):
            raise FetchError(f"page {pid} not in fixture")
        return self.data["confluence_pages"][pid]


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("ticket")
    ap.add_argument("--follow-confluence", action="store_true")
    ap.add_argument("--download-attachments", action="store_true")
    ap.add_argument("--fixture", help="offline: read a saved JSON fixture instead of calling the API")
    a = ap.parse_args(argv)

    out = ticket_source_dir(a.ticket)
    src = FixtureSource(a.fixture) if a.fixture else ApiSource(a.ticket)
    base, headers, ac_field = src.base, src.headers, src.ac_field

    try:
        issue = src.issue()
        remote = src.remote_links()
    except FetchError as e:
        die(str(e))

    md = render_issue_md(issue, remote, ac_field)
    text = all_text(issue, remote, ac_field)
    figma = find_figma_links(text)
    md += "\n## Figma links found\n" + ("\n".join(f"- {u}" for u in figma) or "—") + "\n"
    (out / "jira.md").write_text(md, encoding="utf-8")
    written = [("jira.md", md)]

    if a.follow_confluence:
        conf_base = src.conf_base
        if not conf_base:
            print("! CONFLUENCE_BASE_URL not set; skipping Confluence pages.", file=sys.stderr)
        for pid in find_confluence_page_ids(text, conf_base):
            try:
                page = src.page(pid)
            except FetchError as e:
                print(f"! Confluence page {pid}: {e}", file=sys.stderr)
                continue
            body = storage_to_text(page.get("body", {}).get("storage", {}).get("value", ""))
            if len(body) > MAX_PAGE_CHARS:
                body = body[:MAX_PAGE_CHARS] + f"\n\n_(truncated at {MAX_PAGE_CHARS} chars — ask the user which section matters)_"
            page_md = f"# {page.get('title', pid)}\nConfluence page {pid} · version {page.get('version', {}).get('number')}\n\n{body}\n"
            name = f"confluence-{pid}.md"
            (out / name).write_text(page_md, encoding="utf-8")
            written.append((name, page_md))

    if a.download_attachments and not a.fixture:
        att_dir = out / "attachments"
        att_dir.mkdir(exist_ok=True)
        for att in issue.get("fields", {}).get("attachment") or []:
            url, mime, size = att.get("content", ""), att.get("mimeType", ""), att.get("size", 0)
            if not mime.startswith(DOWNLOADABLE) or size > MAX_ATTACHMENT_BYTES or not same_host(url, base):
                continue
            try:
                (att_dir / safe_filename(att.get("filename", "file"))).write_bytes(http_get(url, headers))
                print(f"  ↓ attachments/{safe_filename(att.get('filename', 'file'))}")
            except FetchError as e:
                print(f"! attachment {att.get('filename')}: {e}", file=sys.stderr)

    rel = out.relative_to(out.parents[2])
    print(f"✔ Saved to {rel}/")
    for name, content in written:
        print(f"  {name:<28} ~{approx_tokens(content):>6,} tokens")


if __name__ == "__main__":
    main()
