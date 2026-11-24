"""Tests for stack profiles: detection, init with a stack, use-stack, and profile completeness.

A "stack" (react, angular, spring-boot, …) = one detection rule in config.json
+ one folder tools/copilot-wf/stacks/<stack>/. These tests are the safety net when you add one.
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


class RepoCase(unittest.TestCase):
    """A throwaway consuming repo with tools/ pointing at the real stack profiles."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self._orig = wf.repo_root
        wf.repo_root = lambda: self.tmp

    def tearDown(self):
        wf.repo_root = self._orig
        shutil.rmtree(self.tmp)

    def write(self, rel: str, text: str = "") -> None:
        p = self.tmp / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)

    def run_wf(self, *args) -> tuple[int, str]:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            try:
                wf.main(list(args))
                return 0, buf.getvalue()
            except SystemExit as e:
                return e.code, buf.getvalue()


class TestDetect(RepoCase):
    def test_angular(self):
        self.write("angular.json", "{}")
        self.write("package.json", '{"dependencies": {"@angular/core": "^20.0.0"}}')
        self.assertEqual(wf.detect_stacks(CFG, self.tmp), ["angular"])

    def test_react(self):
        self.write("package.json", '{"dependencies": {"react": "18.3.1"}}')
        self.assertEqual(wf.detect_stacks(CFG, self.tmp), ["react"])

    def test_spring_boot_maven_and_gradle(self):
        self.write("pom.xml", "<artifactId>spring-boot-starter-web</artifactId>")
        self.assertEqual(wf.detect_stacks(CFG, self.tmp), ["spring-boot"])
        (self.tmp / "pom.xml").unlink()
        self.write("build.gradle.kts", 'id("org.springframework.boot")')
        self.assertEqual(wf.detect_stacks(CFG, self.tmp), ["spring-boot"])

    def test_plain_node_package_is_not_a_known_stack(self):
        self.write("package.json", '{"dependencies": {"express": "4"}}')
        self.assertEqual(wf.detect_stacks(CFG, self.tmp), [])

    def test_monorepo_matches_several(self):
        self.write("angular.json", "{}")
        self.write("pom.xml", "spring-boot")
        self.assertEqual(wf.detect_stacks(CFG, self.tmp), ["angular", "spring-boot"])


class TestInitWithStack(RepoCase):
    def test_auto_detected_stack_sets_side(self):
        self.write("angular.json", "{}")
        code, out = self.run_wf("init", "--ticket", "NG-1", "--type", "Story", "--figma")
        self.assertEqual(code, 0, out)
        self.assertIn("angular", out)
        state = json.loads((self.tmp / ".copilot-wf/NG-1/state.json").read_text())
        self.assertEqual((state["stack"], state["side"]), ("angular", "fe"))
        self.assertIn("design", state["phases"])  # FE + Figma

    def test_monorepo_requires_explicit_stack(self):
        self.write("angular.json", "{}")
        self.write("pom.xml", "spring-boot")
        code, out = self.run_wf("init", "--ticket", "NG-2", "--type", "Story")
        self.assertEqual(code, 1, out)
        self.assertIn("--stack", out)
        code, out = self.run_wf("init", "--ticket", "NG-2", "--type", "Story", "--stack", "spring-boot", "--figma")
        self.assertEqual(code, 0, out)
        state = json.loads((self.tmp / ".copilot-wf/NG-2/state.json").read_text())
        self.assertNotIn("design", state["phases"])  # BE stack → no design, even with Figma

    def test_side_must_match_stack(self):
        code, out = self.run_wf("init", "--ticket", "NG-3", "--type", "Bug", "--stack", "angular", "--side", "be")
        self.assertEqual(code, 1, out)

    def test_unknown_stack_rejected(self):
        code, out = self.run_wf("init", "--ticket", "NG-4", "--type", "Bug", "--stack", "cobol")
        self.assertEqual(code, 1, out)

    def test_nothing_detected_and_no_side_asks_for_stack(self):
        code, out = self.run_wf("init", "--ticket", "NG-5", "--type", "Bug")
        self.assertEqual(code, 1, out)
        self.assertIn("--stack", out)

    def test_legacy_side_only_still_works(self):
        code, out = self.run_wf("init", "--ticket", "NG-6", "--type", "Bug", "--side", "be")
        self.assertEqual(code, 0, out)
        code, out = self.run_wf("status", "--ticket", "NG-6")
        self.assertIn("stack=none", out)


class TestUseStack(RepoCase):
    def setUp(self):
        super().setUp()
        self._orig_stacks = wf.stacks_dir
        wf.stacks_dir = lambda: TOOLS / "stacks"  # real profiles, temp repo

    def tearDown(self):
        wf.stacks_dir = self._orig_stacks
        super().tearDown()

    def test_installs_instructions_for_copilot(self):
        code, out = self.run_wf("use-stack", "angular")
        self.assertEqual(code, 0, out)
        dest = self.tmp / ".github/instructions/angular.instructions.md"
        self.assertEqual(dest.read_text(), (TOOLS / "stacks/angular/instructions.md").read_text())

    def test_refuses_to_overwrite_local_edits(self):
        self.run_wf("use-stack", "angular")
        dest = self.tmp / ".github/instructions/angular.instructions.md"
        dest.write_text(dest.read_text() + "\n- team rule added by hand\n")
        code, out = self.run_wf("use-stack", "angular")
        self.assertEqual(code, 1, out)
        self.assertIn("team rule added by hand", dest.read_text())  # untouched
        code, out = self.run_wf("use-stack", "angular", "--force")
        self.assertEqual(code, 0, out)
        self.assertNotIn("team rule added by hand", dest.read_text())

    def test_warns_when_two_frontend_stacks_are_active(self):
        self.run_wf("use-stack", "react")
        code, out = self.run_wf("use-stack", "angular")
        self.assertEqual(code, 0, out)
        self.assertIn("react", out)  # overlapping *.ts rules warning

    def test_fullstack_repo_can_use_one_fe_and_one_be(self):
        code, out = self.run_wf("use-stack", "angular", "spring-boot")
        self.assertEqual(code, 0, out)
        self.assertNotIn("WARNING", out)


class TestProfilesAreComplete(unittest.TestCase):
    """Every stack in config.json must ship every file the skills will try to read."""

    def test_every_configured_stack_has_its_files(self):
        stacks = {k: v for k, v in CFG["stacks"].items() if not k.startswith("_")}
        self.assertGreaterEqual(set(stacks), {"react", "angular", "spring-boot"})
        for name, prof in stacks.items():
            self.assertEqual(wf.missing_profile_files(name, prof["side"], TOOLS / "stacks"), [], name)

    def test_instructions_have_apply_to(self):
        for f in (TOOLS / "stacks").glob("*/instructions.md"):
            head = f.read_text().split("---")
            self.assertIn("applyTo:", head[1], f)

    def test_status_shows_stack(self):
        tmp = Path(tempfile.mkdtemp())
        orig = wf.repo_root
        wf.repo_root = lambda: tmp
        try:
            (tmp / "angular.json").write_text("{}")
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                wf.main(["init", "--ticket", "NG-9", "--type", "Spike"])
                wf.main(["status", "--ticket", "NG-9"])
            self.assertIn("stack=angular", buf.getvalue())
        finally:
            wf.repo_root = orig
            shutil.rmtree(tmp)


if __name__ == "__main__":
    unittest.main()
