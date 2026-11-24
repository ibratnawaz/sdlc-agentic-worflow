#!/usr/bin/env python3
"""Fetch ONE Figma frame and save a compact outline (+ optional PNG).

The "scripts" alternative to the Figma MCP server. A raw Figma node tree is often
hundreds of KB; this keeps only what Step 2 needs: structure, component instances
(with variants), text, auto-layout, and the style names that map to design tokens.

Usage:
  python3 tools/copilot-wf/figma_fetch.py "<figma frame URL>" --ticket PROJ-1234 [--image]

Environment:
  FIGMA_TOKEN   Figma personal access token (read-only scope is enough). Never commit it.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from urllib.parse import parse_qs, quote, urlparse

from _common import FetchError, approx_tokens, die, env, http_get, http_get_json, ticket_source_dir

API = "https://api.figma.com/v1"
SKIP_TYPES = {"VECTOR", "BOOLEAN_OPERATION", "LINE", "ELLIPSE", "STAR", "REGULAR_POLYGON"}


# ── pure functions (unit-tested) ─────────────────────────────────────────────

def parse_figma_url(url: str) -> tuple[str, str | None]:
    """Return (file_key, node_id or None). Handles /file/, /design/, /proto/ and branch URLs."""
    u = urlparse(url)
    if u.scheme != "https" or (u.hostname or "") not in ("figma.com", "www.figma.com"):
        raise ValueError("Not a figma.com HTTPS link")
    m = re.match(r"^/(?:file|design|proto)/([A-Za-z0-9]+)(?:/branch/([A-Za-z0-9]+))?", u.path)
    if not m:
        raise ValueError("Could not find a file key in the Figma URL")
    key = m.group(2) or m.group(1)
    node = (parse_qs(u.query).get("node-id") or [None])[0]
    return key, node.replace("-", ":") if node else None


def _variant(props: dict | None) -> str:
    if not props:
        return ""
    vals = [f"{k.split('#')[0]}={v.get('value')}" for k, v in props.items() if isinstance(v, dict)]
    return " {" + ", ".join(vals) + "}" if vals else ""


def _texts(node: dict, limit: int = 3) -> list[str]:
    found: list[str] = []
    stack = [node]
    while stack and len(found) < limit:
        n = stack.pop(0)
        if n.get("type") == "TEXT" and n.get("characters", "").strip():
            found.append(n["characters"].strip()[:60])
        stack.extend(n.get("children", []))
    return found


def outline(root: dict, components: dict, styles: dict, max_nodes: int = 400) -> tuple[list[str], Counter, Counter, int]:
    """Walk the tree → (lines, component usage, style usage, nodes omitted)."""
    lines: list[str] = []
    used_components: Counter = Counter()
    used_styles: Counter = Counter()
    omitted = 0

    def walk(n: dict, depth: int) -> None:
        nonlocal omitted
        if n.get("visible") is False:
            return
        for sid in (n.get("styles") or {}).values():
            if sid in styles:
                used_styles[styles[sid].get("name", sid)] += 1
        t = n.get("type", "?")
        if t in SKIP_TYPES:
            return
        if len(lines) >= max_nodes:
            omitted += 1
            return
        pad = "  " * depth
        name = n.get("name", "")
        if t == "INSTANCE":
            comp = components.get(n.get("componentId", ""), {}).get("name", name)
            used_components[comp] += 1
            label = _texts(n)
            lines.append(f"{pad}- INSTANCE \"{name}\" → component \"{comp}\"{_variant(n.get('componentProperties'))}"
                         + (f" text={label}" if label else ""))
            return  # don't descend: children are the component's internals
        if t == "TEXT":
            lines.append(f"{pad}- TEXT \"{name}\": {n.get('characters', '').strip()[:120]!r}")
            return
        extra = ""
        if n.get("layoutMode") in ("HORIZONTAL", "VERTICAL"):
            extra += f" [auto-layout {n['layoutMode'].lower()}, gap {n.get('itemSpacing', 0)}]"
        box = n.get("absoluteBoundingBox")
        if box and t in ("FRAME", "COMPONENT", "SECTION") and depth <= 1:
            extra += f" ({round(box.get('width', 0))}×{round(box.get('height', 0))})"
        lines.append(f"{pad}- {t} \"{name}\"{extra}")
        for c in n.get("children", []):
            walk(c, depth + 1)

    walk(root, 0)
    return lines, used_components, used_styles, omitted


def render_md(url: str, node_id: str, lines: list[str], comps: Counter, styles: Counter, omitted: int) -> str:
    md = [f"# Figma frame {node_id}", f"Source: {url}", "",
          "## Components used (instances)", *(f"- {c} × {n}" for c, n in comps.most_common()), "",
          "## Styles used (→ map to design tokens)", *(f"- {s} × {n}" for s, n in styles.most_common()), "",
          "## Structure", *lines]
    if omitted:
        md += ["", f"_({omitted} more nodes omitted — fetch a smaller frame if they matter)_"]
    return "\n".join(md) + "\n"


# ── I/O ─────────────────────────────────────────────────────────────────────

def write_outline(a: argparse.Namespace, data: dict, node: str, out: Path) -> None:
    entry = (data.get("nodes") or {}).get(node)
    if not entry:
        die(f"Node {node} not found (deleted, or no access).")
    raw_tokens = approx_tokens(json.dumps(entry))
    lines, comps, styles, omitted = outline(entry["document"], entry.get("components", {}),
                                            entry.get("styles", {}), a.max_nodes)
    md = render_md(a.url, node, lines, comps, styles, omitted)
    (out / "figma.md").write_text(md, encoding="utf-8")
    print(f"✔ figma.md  ~{approx_tokens(md):,} tokens (raw API response was ~{raw_tokens:,})  "
          f"({len(lines)} nodes, {len(comps)} components)")


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("url")
    ap.add_argument("--ticket", required=True)
    ap.add_argument("--depth", type=int, default=8)
    ap.add_argument("--max-nodes", type=int, default=400)
    ap.add_argument("--image", action="store_true", help="also save a PNG of the frame")
    ap.add_argument("--fixture", help="offline: a saved /v1/files/:key/nodes JSON response instead of the API")
    a = ap.parse_args(argv)

    try:
        key, node = parse_figma_url(a.url)
    except ValueError as e:
        die(str(e))
    out = ticket_source_dir(a.ticket)

    if a.fixture:
        if not node:
            die("--fixture needs a link with ?node-id=")
        data = json.loads(Path(a.fixture).read_text(encoding="utf-8"))
        write_outline(a, data, node, out)
        return

    headers = {"X-Figma-Token": env("FIGMA_TOKEN")}
    try:
        if not node:
            # No frame chosen: list pages and top-level frames so the user can pick one.
            f = http_get_json(f"{API}/files/{key}?depth=2", headers)
            print("No node-id in the link. Pick a frame and re-run with its link:\n")
            for page in f.get("document", {}).get("children", []):
                print(f"Page: {page.get('name')}")
                for fr in page.get("children", [])[:40]:
                    print(f"  - {fr.get('type')} \"{fr.get('name')}\"  node-id={fr.get('id', '').replace(':', '-')}")
            return

        data = http_get_json(f"{API}/files/{key}/nodes?ids={quote(node)}&depth={a.depth}", headers)
        write_outline(a, data, node, out)

        if a.image:
            img = http_get_json(f"{API}/images/{key}?ids={quote(node)}&format=png&scale=1", headers)
            img_url = (img.get("images") or {}).get(node)
            if img_url:
                # The PNG lives on Figma's CDN: fetch WITHOUT our token.
                (out / "figma.png").write_bytes(http_get(img_url))
                print("✔ figma.png")
    except FetchError as e:
        die(str(e))


if __name__ == "__main__":
    main()
