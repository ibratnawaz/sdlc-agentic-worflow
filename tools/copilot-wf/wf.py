#!/usr/bin/env python3
"""wf.py — the deterministic "workflow" half of the Copilot workflow.

The AI agents do the judgment work (reading tickets, planning, coding).
This script does what must ALWAYS be true and should never be left to a prompt:

  init         pick the phase list from the ticket type (config.json → phase_sets)
  check        refuse to start a phase whose earlier phases are not done (the gate)
               --approved: also require a recorded human approval (plan, ship)
  approve      record a human approval, with the user's own words, for an audit trail
  done         mark a phase complete, add a usage estimate, print the usage table
  credits      record the REAL credits you read from the IDE (to compare MCP vs scripts)
  status       show where a ticket is (also used by the orchestrator to resume)
  sync         apply config.json (model tiers + mcp/scripts mode) to .github/agents/*.agent.md

Exit codes: 0 ok · 1 usage/input error · 2 earlier phase missing · 3 phase skipped for this type
            4 approval missing · 5 fix-cycle limit reached

Standard library only — no pip install needed on locked-down machines.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
CONFIG_PATH = HERE / "config.json"
TICKET_RE = re.compile(r"^[A-Z][A-Z0-9]+-\d+$")
ALL_PHASES = ["analyze", "design", "plan", "implement", "review", "ship"]
APPROVAL_PHASES = ("plan", "ship")  # phases a human must approve
ORCHESTRATOR_STAGE = "orchestrate"


# ── helpers ──────────────────────────────────────────────────────────────────

def load_config(path: Path = CONFIG_PATH) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def fail(msg: str, code: int = 1) -> None:
    print(f"✖ {msg}", file=sys.stderr)
    sys.exit(code)


def validate_ticket(ticket: str) -> str:
    # Also stops path tricks like "../../etc" because the key becomes a folder name.
    if not TICKET_RE.match(ticket):
        fail(f"'{ticket}' is not a ticket key like PROJ-1234")
    return ticket


def repo_root() -> Path:
    """The consuming repo root = two levels above tools/copilot-wf/."""
    return HERE.parent.parent


def ticket_dir(cfg: dict, ticket: str) -> Path:
    return repo_root() / cfg["artifacts_dir"] / ticket


def state_path(cfg: dict, ticket: str) -> Path:
    return ticket_dir(cfg, ticket) / "state.json"


def read_state(cfg: dict, ticket: str) -> dict:
    p = state_path(cfg, ticket)
    if not p.exists():
        fail(f"No workflow started for {ticket}. Run: wf.py init --ticket {ticket} ...")
    state = json.loads(p.read_text(encoding="utf-8"))
    state.setdefault("approvals", {})  # v1 state files have none
    return state


def write_state(cfg: dict, ticket: str, state: dict) -> None:
    p = state_path(cfg, ticket)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# ── pure logic (unit-tested) ─────────────────────────────────────────────────

def select_phases(cfg: dict, ticket_type: str, side: str, has_figma: bool) -> list[str]:
    sets = {k: v for k, v in cfg["phase_sets"].items() if not k.startswith("_")}
    if ticket_type not in sets:
        raise ValueError(f"Unknown ticket type '{ticket_type}'. Known: {', '.join(sets)}")
    if side not in ("fe", "be"):
        raise ValueError("side must be 'fe' or 'be'")
    phases = list(sets[ticket_type])
    if "design" in phases and not (side == "fe" and has_figma):
        phases.remove("design")
    return phases


def missing_before(state: dict, phase: str) -> list[str]:
    """Phases that must be completed before `phase` may start."""
    phases = state["phases"]
    if phase not in phases:
        raise ValueError(f"Phase '{phase}' is not part of this ticket's workflow: {phases}")
    earlier = phases[: phases.index(phase)]
    return [p for p in earlier if p not in state["completed"]]


def runs_of(state: dict, phase: str) -> int:
    return next((u.get("runs", 1) for u in state["usage"] if u["stage"] == phase), 0)


def fix_cycles_exhausted(state: dict, cfg: dict) -> bool:
    """Implement may run once, plus `max_fix_cycles` re-runs after review findings."""
    limit = 1 + cfg.get("max_fix_cycles", 2)
    return runs_of(state, "implement") >= limit


def add_usage(state: dict, entry: dict) -> None:
    """Accumulate per stage, so a re-run (e.g. a fix cycle) adds to the cost instead of hiding it."""
    for u in state["usage"]:
        if u["stage"] == entry["stage"]:
            u["est_read"] = u.get("est_read", 0) + entry["est_read"]
            u["est_written"] = u.get("est_written", 0) + entry["est_written"]
            u["runs"] = u.get("runs", 1) + 1
            u["at"] = entry["at"]
            return
    state["usage"].append({**entry, "runs": 1})


def next_phase(state: dict) -> str | None:
    return next((p for p in state["phases"] if p not in state["completed"]), None)


def estimate_tokens(paths: list[Path], chars_per_token: int) -> int:
    total = 0
    for p in paths:
        if p.is_file():
            total += len(p.read_text(encoding="utf-8", errors="ignore"))
    return round(total / chars_per_token)


def render_usage_table(usage: list[dict]) -> str:
    lines = [
        "| Stage | Runs | Est. tokens read | Est. tokens written | Real credits (if logged) |",
        "|---|---:|---:|---:|---:|",
    ]
    tr = tw = 0
    tc = 0.0
    for u in usage:
        tr += u.get("est_read", 0)
        tw += u.get("est_written", 0)
        c = u.get("credits")
        tc += c or 0
        lines.append(
            f"| {u['stage']} | {u.get('runs', 1)} | {u.get('est_read', 0):,} | {u.get('est_written', 0):,} | "
            f"{'' if c is None else c} |"
        )
    credits_total = f"**{tc:g}**" if tc else ""
    lines.append(f"| **Total** | | **{tr:,}** | **{tw:,}** | {credits_total} |")
    return "\n".join(lines)


# ── commands ─────────────────────────────────────────────────────────────────

def cmd_init(a: argparse.Namespace) -> None:
    cfg = load_config()
    t = validate_ticket(a.ticket)
    try:
        phases = select_phases(cfg, a.type, a.side, a.figma)
    except ValueError as e:
        fail(str(e))
    if state_path(cfg, t).exists() and not a.force:
        fail(f"{t} already started. Use 'status', or --force to restart.")
    state = {
        "ticket": t, "type": a.type, "side": a.side, "has_figma": a.figma,
        "data_source": cfg["data_source"], "phases": phases, "completed": [],
        "approvals": {}, "usage": [], "created_at": now(),
    }
    write_state(cfg, t, state)
    skipped = [p for p in ALL_PHASES if p not in phases]
    print(f"✔ {t} ({a.type}, {a.side.upper()}) → phases: {' → '.join(phases)}")
    if skipped:
        print(f"  skipped: {', '.join(skipped)}")


def cmd_check(a: argparse.Namespace) -> None:
    cfg = load_config()
    state = read_state(cfg, validate_ticket(a.ticket))
    if a.phase not in state["phases"]:
        fail(f"'{a.phase}' is skipped for this {state['type']}. Phases: {state['phases']}", 3)
    missing = missing_before(state, a.phase)
    if missing:
        fail(f"Cannot start '{a.phase}': finish {', '.join(missing)} first.", 2)
    if a.phase == "implement" and fix_cycles_exhausted(state, cfg):
        fail(f"'implement' has run {runs_of(state, 'implement')} times (limit 1 + max_fix_cycles="
             f"{cfg.get('max_fix_cycles', 2)}). Stop and ask the user how to proceed.", 5)
    if a.approved and a.phase not in state["approvals"]:
        fail(f"No recorded user approval for '{a.phase}'. Ask the user, then run 'wf.py approve'.", 4)
    print(f"✔ '{a.phase}' may start." + (" (approved)" if a.approved else ""))


def cmd_approve(a: argparse.Namespace) -> None:
    cfg = load_config()
    t = validate_ticket(a.ticket)
    state = read_state(cfg, t)
    if a.phase not in state["phases"]:
        fail(f"'{a.phase}' is skipped for this {state['type']}.", 3)
    missing = missing_before(state, a.phase)
    if missing:
        fail(f"Cannot approve '{a.phase}' before {', '.join(missing)} are done.", 2)
    if not a.note.strip():
        fail("--note must quote what the user actually said (audit trail).")
    state["approvals"][a.phase] = {"at": now(), "note": a.note.strip()}
    write_state(cfg, t, state)
    print(f"✔ {t}: '{a.phase}' approved — \"{a.note.strip()}\"")


def cmd_done(a: argparse.Namespace) -> None:
    cfg = load_config()
    t = validate_ticket(a.ticket)
    state = read_state(cfg, t)
    if a.phase not in state["phases"]:
        fail(f"'{a.phase}' is skipped for this {state['type']}.", 3)
    missing = missing_before(state, a.phase)
    if missing:
        fail(f"Cannot complete '{a.phase}' before {', '.join(missing)}.", 2)
    if a.phase in APPROVAL_PHASES and a.phase not in state["approvals"]:
        fail(f"'{a.phase}' needs a recorded user approval first ('wf.py approve').", 4)

    cpt = cfg["usage"]["chars_per_token"]
    root = repo_root()
    add_usage(state, {
        "stage": a.phase,
        "est_read": estimate_tokens([root / p for p in a.read], cpt),
        "est_written": estimate_tokens([root / p for p in a.wrote], cpt),
        "credits": None,
        "data_source": state["data_source"],
        "at": now(),
    })
    if a.phase not in state["completed"]:
        state["completed"].append(a.phase)
    write_state(cfg, t, state)

    nxt = next_phase(state)
    print(f"✔ {t}: '{a.phase}' complete.\n")
    print("### Usage so far (estimate)\n")
    print(render_usage_table(state["usage"]))
    print(
        "\nEstimate = size of files this stage read/wrote. It does NOT include the system\n"
        "prompt, tool definitions (e.g. MCP schemas) or chat history, so real usage is higher.\n"
        "Exact credits → VS Code: hover the context-window circle in the chat input\n"
        "(and enable chat.subagents.showCreditUsage to see each subagent's credits).\n"
        "Then record it:  python3 tools/copilot-wf/wf.py credits "
        f"--ticket {t} --phase {a.phase} --value <number>\n"
    )
    print(f"Next phase: {nxt}" if nxt else "All phases complete. 🎉")


def cmd_credits(a: argparse.Namespace) -> None:
    cfg = load_config()
    t = validate_ticket(a.ticket)
    state = read_state(cfg, t)
    for u in state["usage"]:
        if u["stage"] == a.phase:
            u["credits"] = a.value
            write_state(cfg, t, state)
            print(render_usage_table(state["usage"]))
            return
    fail(f"No usage entry for '{a.phase}' yet — run 'done' first.")


def cmd_status(a: argparse.Namespace) -> None:
    cfg = load_config()
    s = read_state(cfg, validate_ticket(a.ticket))
    print(f"{s['ticket']}  type={s['type']}  side={s['side']}  data_source={s['data_source']}")
    for p in s["phases"]:
        mark = "✔" if p in s["completed"] else "·"
        appr = f"  (approved: \"{s['approvals'][p]['note']}\")" if p in s["approvals"] else ""
        print(f"  {mark} {p}{appr}")
    nxt = next_phase(s)
    print(f"next: {nxt}" if nxt else "next: — (all phases complete)")
    if s["usage"]:
        print()
        print(render_usage_table(s["usage"]))


def sync_agent_text(text: str, models: list[str], mcp_tools: list[str]) -> str:
    """Return agent file text with its `model:` list and MCP tools replaced."""
    block = "model:\n" + "".join(f"  - {m}\n" for m in models)
    text, n = re.subn(r"^model:\n(?:  - .*\n)+", block, text, count=1, flags=re.M)
    if n == 0:
        raise ValueError("no 'model:' list to replace")

    m = re.search(r"^tools: \[(.*)\]$", text, flags=re.M)
    if not m:
        raise ValueError("no single-line 'tools: [...]' to replace")
    current = [t.strip().strip("'\"") for t in m.group(1).split(",") if t.strip()]
    built_in = [t for t in current if "/" not in t]  # MCP tools look like 'server/tool'
    tools = built_in + mcp_tools
    line = "tools: [" + ", ".join(f"'{t}'" for t in tools) + "]"
    return text[: m.start()] + line + text[m.end():]


def agent_files() -> list[tuple[str, str]]:
    """(stage, filename) for every agent wf.py manages."""
    return [(s, f"wf-{i}-{s}.agent.md") for i, s in enumerate(ALL_PHASES, start=1)] + [
        (ORCHESTRATOR_STAGE, "wf-orchestrator.agent.md")
    ]


def cmd_sync(a: argparse.Namespace) -> None:
    """Apply config.json (model tiers + data_source) to .github/agents/wf-*.agent.md."""
    cfg = load_config()
    tiers, stages = cfg["models"]["tiers"], cfg["models"]["stages"]
    use_mcp = cfg["data_source"] == "mcp"
    agents_dir = repo_root() / ".github" / "agents"
    print(f"data_source = {cfg['data_source']}")
    for stage, name in agent_files():
        f = agents_dir / name
        if not f.exists():
            print(f"  skip {f.name} (missing)")
            continue
        models = tiers[stages[stage]]
        mcp = cfg["mcp_tools"].get(stage, []) if use_mcp else []
        try:
            f.write_text(sync_agent_text(f.read_text(encoding="utf-8"), models, mcp), encoding="utf-8")
        except ValueError as e:
            fail(f"{f.name}: {e}")
        print(f"  {f.name}: model={stages[stage]} ({models[0]}), mcp={mcp or 'none'}")


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("init");  p.set_defaults(fn=cmd_init)
    p.add_argument("--ticket", required=True); p.add_argument("--type", required=True)
    p.add_argument("--side", required=True, choices=["fe", "be"])
    p.add_argument("--figma", action="store_true", help="a Figma link exists for this ticket")
    p.add_argument("--force", action="store_true")

    for name, fn in (("check", cmd_check), ("done", cmd_done)):
        p = sub.add_parser(name); p.set_defaults(fn=fn)
        p.add_argument("--ticket", required=True)
        p.add_argument("--phase", required=True, choices=ALL_PHASES)
        if name == "check":
            p.add_argument("--approved", action="store_true", help="also require a recorded user approval")
        if name == "done":
            p.add_argument("--read", nargs="*", default=[], help="repo-relative files this stage read")
            p.add_argument("--wrote", nargs="*", default=[], help="repo-relative files this stage wrote")

    p = sub.add_parser("approve"); p.set_defaults(fn=cmd_approve)
    p.add_argument("--ticket", required=True); p.add_argument("--phase", required=True, choices=APPROVAL_PHASES)
    p.add_argument("--note", required=True, help="the user's own words, e.g. 'approved, go ahead'")

    p = sub.add_parser("credits"); p.set_defaults(fn=cmd_credits)
    p.add_argument("--ticket", required=True); p.add_argument("--phase", required=True, choices=ALL_PHASES)
    p.add_argument("--value", required=True, type=float)

    p = sub.add_parser("status"); p.set_defaults(fn=cmd_status)
    p.add_argument("--ticket", required=True)

    p = sub.add_parser("sync"); p.set_defaults(fn=cmd_sync)

    a = ap.parse_args(argv)
    a.fn(a)


if __name__ == "__main__":
    main()
