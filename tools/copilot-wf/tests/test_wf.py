"""Tests for wf.py — the deterministic workflow engine.  Run:
    python3 -m unittest discover tools/copilot-wf/tests -v
"""

import contextlib
import io
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(TOOLS))
import wf  # noqa: E402

CFG = wf.load_config()


class TestSelectPhases(unittest.TestCase):
    def test_story_fe_with_figma_runs_everything(self):
        self.assertEqual(wf.select_phases(CFG, "Story", "fe", True),
                         ["analyze", "design", "plan", "implement", "review", "ship"])

    def test_design_skipped_for_backend(self):
        self.assertNotIn("design", wf.select_phases(CFG, "Story", "be", True))

    def test_design_skipped_without_figma(self):
        self.assertNotIn("design", wf.select_phases(CFG, "Bug", "fe", False))

    def test_spike_never_ships_code(self):
        phases = wf.select_phases(CFG, "Spike", "fe", True)
        self.assertNotIn("implement", phases)
        self.assertNotIn("ship", phases)

    def test_unknown_type_rejected(self):
        with self.assertRaises(ValueError):
            wf.select_phases(CFG, "Epic", "fe", False)


class TestGate(unittest.TestCase):
    state = {"phases": ["analyze", "plan", "implement"], "completed": ["analyze"]}

    def test_cannot_implement_before_plan(self):
        self.assertEqual(wf.missing_before(self.state, "implement"), ["plan"])

    def test_plan_may_start_after_analyze(self):
        self.assertEqual(wf.missing_before(self.state, "plan"), [])

    def test_skipped_phase_is_an_error(self):
        with self.assertRaises(ValueError):
            wf.missing_before(self.state, "design")


class TestSyncAgentText(unittest.TestCase):
    AGENT = ("---\nname: x\ntools: ['read', 'edit', 'atlassian/*']\nmodel:\n  - Old (copilot)\n"
             "handoffs: []\n---\nbody\n")

    def test_scripts_mode_removes_mcp_tools_and_sets_model(self):
        out = wf.sync_agent_text(self.AGENT, ["New (copilot)", "Fallback (copilot)"], [])
        self.assertIn("tools: ['read', 'edit']\n", out)
        self.assertIn("model:\n  - New (copilot)\n  - Fallback (copilot)\nhandoffs", out)

    def test_mcp_mode_adds_configured_tools(self):
        out = wf.sync_agent_text(self.AGENT, ["M (copilot)"], ["atlassian/getJiraIssue"])
        self.assertIn("tools: ['read', 'edit', 'atlassian/getJiraIssue']", out)

    def test_real_agent_files_are_syncable(self):
        for f in (TOOLS.parent.parent / ".github" / "agents").glob("wf-*.agent.md"):
            wf.sync_agent_text(f.read_text(encoding="utf-8"), ["M (copilot)"], [])  # raises if malformed


class TestUsageTable(unittest.TestCase):
    def test_empty_credits_total_is_blank_not_stars(self):
        out = wf.render_usage_table([{"stage": "analyze", "est_read": 1, "est_written": 2, "credits": None}])
        self.assertIn("| **Total** | | **1** | **2** |  |", out)
        self.assertNotIn("****", out)

    def test_credits_total(self):
        out = wf.render_usage_table([{"stage": "a", "credits": 2.5}, {"stage": "b", "credits": 10}])
        self.assertIn("**12.5**", out)


class TestEndToEnd(unittest.TestCase):
    """init → check (blocked) → done → check (allowed), in a throwaway repo root."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self._orig = wf.repo_root
        wf.repo_root = lambda: self.tmp

    def tearDown(self):
        wf.repo_root = self._orig
        shutil.rmtree(self.tmp)

    def run_wf(self, *args) -> tuple[int, str]:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            try:
                wf.main(list(args))
                return 0, buf.getvalue()
            except SystemExit as e:
                return e.code, buf.getvalue()

    def test_full_gate_flow(self):
        code, out = self.run_wf("init", "--ticket", "ABC-1", "--type", "Bug", "--side", "be")
        self.assertEqual(code, 0, out)
        self.assertIn("analyze → plan → implement", out)

        code, out = self.run_wf("check", "--ticket", "ABC-1", "--phase", "implement")
        self.assertEqual(code, 2, out)  # plan not approved yet → blocked

        (self.tmp / "req.md").write_text("x" * 400)
        code, out = self.run_wf("done", "--ticket", "ABC-1", "--phase", "analyze", "--wrote", "req.md")
        self.assertEqual(code, 0, out)
        self.assertIn("| analyze | 1 | 0 | 100 |", out)  # 1 run, 400 chars / 4
        code, out = self.run_wf("done", "--ticket", "ABC-1", "--phase", "plan")
        self.assertEqual(code, 4, out)  # no approval recorded yet
        code, out = self.run_wf("approve", "--ticket", "ABC-1", "--phase", "plan", "--note", "approved, go")
        self.assertEqual(code, 0, out)
        code, out = self.run_wf("done", "--ticket", "ABC-1", "--phase", "plan")
        self.assertEqual(code, 0, out)

        code, _ = self.run_wf("check", "--ticket", "ABC-1", "--phase", "implement")
        self.assertEqual(code, 0)

        code, out = self.run_wf("credits", "--ticket", "ABC-1", "--phase", "analyze", "--value", "12.5")
        self.assertIn("12.5", out)

    def test_bad_ticket_key_rejected(self):
        code, _ = self.run_wf("init", "--ticket", "../etc", "--type", "Bug", "--side", "be")
        self.assertEqual(code, 1)

    def test_design_check_on_backend_is_skipped(self):
        self.run_wf("init", "--ticket", "ABC-2", "--type", "Story", "--side", "be")
        code, out = self.run_wf("check", "--ticket", "ABC-2", "--phase", "design")
        self.assertEqual(code, 3, out)


    def _to_review(self, ticket="ABC-3"):
        self.run_wf("init", "--ticket", ticket, "--type", "Bug", "--side", "be")
        self.run_wf("done", "--ticket", ticket, "--phase", "analyze")
        self.run_wf("approve", "--ticket", ticket, "--phase", "plan", "--note", "ok")
        self.run_wf("done", "--ticket", ticket, "--phase", "plan")
        return ticket

    def test_approve_requires_the_users_words(self):
        t = self._to_review()
        code, out = self.run_wf("approve", "--ticket", t, "--phase", "ship", "--note", "   ")
        self.assertEqual(code, 2, out)  # ship can't be approved before implement/review are done
        code, out = self.run_wf("approve", "--ticket", t, "--phase", "plan", "--note", "   ")
        self.assertEqual(code, 1, out)  # empty note rejected

    def test_ship_needs_approval_to_execute_and_complete(self):
        t = self._to_review()
        self.run_wf("done", "--ticket", t, "--phase", "implement")
        self.run_wf("done", "--ticket", t, "--phase", "review")
        code, _ = self.run_wf("check", "--ticket", t, "--phase", "ship")
        self.assertEqual(code, 0)  # may start drafting
        code, out = self.run_wf("check", "--ticket", t, "--phase", "ship", "--approved")
        self.assertEqual(code, 4, out)  # may not execute git yet
        code, out = self.run_wf("done", "--ticket", t, "--phase", "ship")
        self.assertEqual(code, 4, out)
        self.run_wf("approve", "--ticket", t, "--phase", "ship", "--note", "yes, ship it")
        code, _ = self.run_wf("check", "--ticket", t, "--phase", "ship", "--approved")
        self.assertEqual(code, 0)
        code, out = self.run_wf("status", "--ticket", t)
        self.assertIn('approved: "yes, ship it"', out)

    def test_fix_cycles_are_capped_and_usage_accumulates(self):
        t = self._to_review()
        (self.tmp / "f.md").write_text("y" * 40)  # 10 tokens per run
        for _ in range(3):  # first run + 2 fix cycles (max_fix_cycles = 2)
            code, out = self.run_wf("check", "--ticket", t, "--phase", "implement")
            self.assertEqual(code, 0, out)
            self.run_wf("done", "--ticket", t, "--phase", "implement", "--wrote", "f.md")
        code, out = self.run_wf("check", "--ticket", t, "--phase", "implement")
        self.assertEqual(code, 5, out)  # 4th run refused → human decides
        code, out = self.run_wf("status", "--ticket", t)
        self.assertIn("| implement | 3 | 0 | 30 |", out)  # costs added up, not overwritten

    def test_status_reports_next_phase_for_resume(self):
        t = self._to_review()
        code, out = self.run_wf("status", "--ticket", t)
        self.assertIn("next: implement", out)

    def test_v1_state_without_approvals_still_loads(self):
        self.run_wf("init", "--ticket", "ABC-4", "--type", "Spike", "--side", "fe")
        sp = self.tmp / ".copilot-wf" / "ABC-4" / "state.json"
        s = json.loads(sp.read_text()); s.pop("approvals"); sp.write_text(json.dumps(s))
        code, out = self.run_wf("status", "--ticket", "ABC-4")
        self.assertEqual(code, 0, out)


class TestOrchestratorFiles(unittest.TestCase):
    AGENTS = TOOLS.parent.parent / ".github" / "agents"

    def test_sync_manages_the_orchestrator(self):
        self.assertIn(("orchestrate", "wf-orchestrator.agent.md"), wf.agent_files())
        self.assertIn("orchestrate", CFG["models"]["stages"])

    def test_orchestrator_can_only_delegate_to_phase_agents(self):
        text = (self.AGENTS / "wf-orchestrator.agent.md").read_text(encoding="utf-8")
        self.assertIn("'agent'", text)          # needs the subagent tool
        self.assertNotIn("'edit'", text)        # must never write files itself
        for i, phase in enumerate(wf.ALL_PHASES, start=1):
            self.assertIn(f"'wf-{i}-{phase}'", text)
            self.assertTrue((self.AGENTS / f"wf-{i}-{phase}.agent.md").exists())

    def test_every_phase_agent_knows_subagent_mode(self):
        for f in self.AGENTS.glob("wf-[1-6]-*.agent.md"):
            self.assertIn("[wf-orchestrator]", f.read_text(encoding="utf-8"), f.name)


if __name__ == "__main__":
    unittest.main()
