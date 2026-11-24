"""Shared helpers for the fetch scripts: env vars, HTTPS GET, paths.

Security rules baked in here so every script gets them for free:
  * credentials come only from environment variables and are never printed
  * HTTPS only
  * a credential is only ever sent to the host it belongs to
  * responses are size-capped
"""

from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

HERE = Path(__file__).resolve().parent
TICKET_RE = re.compile(r"^[A-Z][A-Z0-9]+-\d+$")
MAX_BYTES = 20 * 1024 * 1024
USER_AGENT = "copilot-wf/0.1"


class FetchError(Exception):
    pass


def die(msg: str, code: int = 1) -> None:
    print(f"✖ {msg}", file=sys.stderr)
    sys.exit(code)


def env(name: str, required: bool = True) -> str | None:
    val = os.environ.get(name, "").strip()
    if required and not val:
        die(f"Environment variable {name} is not set. See README.md → 'Scripts mode setup'.")
    return val or None


def repo_root() -> Path:
    return HERE.parent.parent


def ticket_source_dir(ticket: str) -> Path:
    if not TICKET_RE.match(ticket):
        die(f"'{ticket}' is not a ticket key like PROJ-1234")
    cfg = json.loads((HERE / "config.json").read_text(encoding="utf-8"))
    d = repo_root() / cfg["artifacts_dir"] / ticket / "source"
    d.mkdir(parents=True, exist_ok=True)
    return d


def host_of(url: str) -> str:
    return (urlparse(url).hostname or "").lower()


def same_host(url: str, base: str) -> bool:
    return host_of(url) == host_of(base) and host_of(url) != ""


def http_get(url: str, headers: dict[str, str] | None = None, timeout: int = 30) -> bytes:
    if urlparse(url).scheme != "https":
        raise FetchError(f"Refusing non-HTTPS URL: {url}")
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, **(headers or {})})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = resp.read(MAX_BYTES + 1)
    except urllib.error.HTTPError as e:
        hint = {401: "token invalid or expired", 403: "no permission", 404: "not found / no access",
                429: "rate limited, wait and retry"}.get(e.code, "")
        # Print the path only: query strings can carry identifiers we don't want in logs.
        raise FetchError(f"HTTP {e.code} for {urlparse(url).path} {('— ' + hint) if hint else ''}") from None
    except urllib.error.URLError as e:
        raise FetchError(f"Network error for {host_of(url)}: {e.reason}") from None
    if len(data) > MAX_BYTES:
        raise FetchError(f"Response from {host_of(url)} larger than {MAX_BYTES // 1024 // 1024} MB")
    return data


def http_get_json(url: str, headers: dict[str, str] | None = None) -> dict:
    return json.loads(http_get(url, {"Accept": "application/json", **(headers or {})}))


def safe_filename(name: str) -> str:
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("._")
    return name[:120] or "file"


def approx_tokens(text: str) -> int:
    return round(len(text) / 4)
