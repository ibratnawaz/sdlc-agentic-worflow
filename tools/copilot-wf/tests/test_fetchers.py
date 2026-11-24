"""Tests for the pure (no-network) parts of jira_fetch.py and figma_fetch.py."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import figma_fetch  # noqa: E402
import jira_fetch  # noqa: E402
from _common import FetchError, http_get, safe_filename, same_host  # noqa: E402

CONF = "https://acme.atlassian.net/wiki"


class TestJiraHelpers(unittest.TestCase):
    def test_bearer_preferred_over_basic(self):
        self.assertEqual(jira_fetch.auth_headers("pat", "e", "t"), {"Authorization": "Bearer pat"})

    def test_basic_auth(self):
        self.assertTrue(jira_fetch.auth_headers(None, "e", "t")["Authorization"].startswith("Basic "))

    def test_no_credentials(self):
        with self.assertRaises(ValueError):
            jira_fetch.auth_headers(None, None, None)

    def test_confluence_ids_only_from_our_host(self):
        text = (f"See {CONF}/spaces/ENG/pages/123/Title and "
                "https://evil.example.com/wiki/spaces/X/pages/999 and "
                f"{CONF}/pages/viewpage.action?pageId=456 and again {CONF}/spaces/ENG/pages/123/Title")
        self.assertEqual(jira_fetch.find_confluence_page_ids(text, CONF), ["123", "456"])

    def test_no_confluence_base_means_no_follow(self):
        self.assertEqual(jira_fetch.find_confluence_page_ids(f"{CONF}/pages/1", None), [])

    def test_default_confluence_base_cloud_only(self):
        self.assertEqual(jira_fetch.default_confluence_base("https://acme.atlassian.net"), CONF)
        self.assertIsNone(jira_fetch.default_confluence_base("https://jira.internal.example"))

    def test_figma_links(self):
        t = "design: https://www.figma.com/design/AbC123/Name?node-id=1-2| and https://figma.com/file/Zz9/X"
        self.assertEqual(len(jira_fetch.find_figma_links(t)), 2)

    def test_adf_to_text(self):
        adf = {"type": "doc", "content": [
            {"type": "paragraph", "content": [{"type": "text", "text": "Hello"}]},
            {"type": "bulletList", "content": [
                {"type": "listItem", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "AC one"}]}]}]}]}
        out = jira_fetch.adf_to_text(adf)
        self.assertIn("Hello", out)
        self.assertIn("- AC one", out)

    def test_storage_to_text(self):
        html = "<h2>Scope</h2><p>Do <strong>this</strong>.</p><ul><li>One</li><li>Two</li></ul>"
        out = jira_fetch.storage_to_text(html)
        self.assertIn("## Scope", out)
        self.assertIn("- One", out)
        self.assertIn("Do this.", out)

    def test_render_issue_md(self):
        issue = {"key": "ABC-1", "fields": {
            "summary": "Sum", "issuetype": {"name": "Story"}, "status": {"name": "To Do"},
            "description": "Desc", "comment": {"comments": [
                {"author": {"displayName": "PO"}, "created": "2026-11-01T10:00", "body": "AC changed"}]},
            "attachment": [{"filename": "s.png", "mimeType": "image/png", "size": 2048}]}}
        md = jira_fetch.render_issue_md(issue, [], None)
        for expected in ("# ABC-1: Sum", "Type: Story", "### PO · 2026-11-01", "AC changed", "s.png (image/png, 2 KB)"):
            self.assertIn(expected, md)


class TestFigmaHelpers(unittest.TestCase):
    def test_parse_design_url(self):
        self.assertEqual(figma_fetch.parse_figma_url("https://www.figma.com/design/AbC123/My-File?node-id=12-34"),
                         ("AbC123", "12:34"))

    def test_parse_branch_url_uses_branch_key(self):
        self.assertEqual(figma_fetch.parse_figma_url("https://figma.com/design/Main1/branch/Br2/X?node-id=1-2"),
                         ("Br2", "1:2"))

    def test_parse_without_node(self):
        self.assertEqual(figma_fetch.parse_figma_url("https://figma.com/file/K9/X"), ("K9", None))

    def test_rejects_other_hosts(self):
        with self.assertRaises(ValueError):
            figma_fetch.parse_figma_url("https://figma.com.evil.io/design/K/X")

    def test_outline_compacts_tree(self):
        tree = {"type": "FRAME", "name": "Screen", "layoutMode": "VERTICAL", "itemSpacing": 16,
                "absoluteBoundingBox": {"width": 375, "height": 812}, "children": [
                    {"type": "TEXT", "name": "Title", "characters": "Transfer funds", "styles": {"text": "S1"}},
                    {"type": "INSTANCE", "name": "CTA", "componentId": "C1",
                     "componentProperties": {"Variant#1:0": {"type": "VARIANT", "value": "Primary"}},
                     "children": [{"type": "TEXT", "characters": "Continue"},
                                  {"type": "VECTOR", "name": "icon"}]},
                    {"type": "FRAME", "name": "hidden", "visible": False},
                    {"type": "VECTOR", "name": "decoration"}]}
        lines, comps, styles, omitted = figma_fetch.outline(
            tree, {"C1": {"name": "Button"}}, {"S1": {"name": "Heading/H2"}})
        text = "\n".join(lines)
        self.assertIn('FRAME "Screen" [auto-layout vertical, gap 16] (375×812)', text)
        self.assertIn('component "Button" {Variant=Primary}', text)
        self.assertIn("text=['Continue']", text)
        self.assertNotIn("hidden", text)
        self.assertNotIn("decoration", text)
        self.assertEqual(comps["Button"], 1)
        self.assertEqual(styles["Heading/H2"], 1)
        self.assertEqual(omitted, 0)

    def test_outline_respects_max_nodes(self):
        tree = {"type": "FRAME", "name": "F", "children": [{"type": "FRAME", "name": f"c{i}"} for i in range(10)]}
        lines, _, _, omitted = figma_fetch.outline(tree, {}, {}, max_nodes=3)
        self.assertEqual(len(lines), 3)
        self.assertEqual(omitted, 8)


class TestFixtureMode(unittest.TestCase):
    """Run both scripts end-to-end offline against the demo fixtures."""

    FIX = Path(__file__).resolve().parent / "fixtures"

    def setUp(self):
        import _common
        import shutil
        import tempfile
        self._common, self._shutil = _common, shutil
        self.tmp = Path(tempfile.mkdtemp())
        self._orig = _common.repo_root
        _common.repo_root = lambda: self.tmp

    def tearDown(self):
        self._common.repo_root = self._orig
        self._shutil.rmtree(self.tmp)

    def _run(self, fn, args):
        import contextlib
        import io
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            fn(args)

    def test_jira_fixture(self):
        self._run(jira_fetch.main, ["DEMO-101", "--follow-confluence", "--fixture", str(self.FIX / "demo-101.jira.json")])
        src = self.tmp / ".copilot-wf" / "DEMO-101" / "source"
        jira = (src / "jira.md").read_text()
        self.assertIn("Product Owner (demo)", jira)
        self.assertIn("figma.com/design/DeMo123abc", jira)
        self.assertTrue((src / "confluence-770001.md").exists())
        self.assertEqual(len(list(src.glob("confluence-*.md"))), 1)  # off-host page 999 ignored

    def test_figma_fixture(self):
        self._run(figma_fetch.main, ["https://www.figma.com/design/DeMo123abc/Transfers?node-id=42-7",
                                     "--ticket", "DEMO-101", "--fixture", str(self.FIX / "demo-101.figma.json")])
        md = (self.tmp / ".copilot-wf" / "DEMO-101" / "source" / "figma.md").read_text()
        self.assertIn("- Button × 2", md)
        self.assertIn("InlineAlert", md)
        self.assertNotIn("Old layout", md)


class TestCommon(unittest.TestCase):
    def test_refuses_http(self):
        with self.assertRaises(FetchError):
            http_get("http://example.com")

    def test_same_host(self):
        self.assertTrue(same_host("https://a.com/x", "https://a.com/wiki"))
        self.assertFalse(same_host("https://a.com.evil.io/x", "https://a.com"))

    def test_safe_filename(self):
        self.assertEqual(safe_filename("../../etc/passwd"), "etc_passwd")


if __name__ == "__main__":
    unittest.main()
