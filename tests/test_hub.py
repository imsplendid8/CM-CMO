import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
HUB = (ROOT / "index.html").read_text(encoding="utf-8")


class TestHubSecurityAndFlow(unittest.TestCase):
    def test_does_not_ship_client_side_admin_password(self):
        self.assertNotIn("DEFAULT_ADMIN_HASH", HUB)
        self.assertNotIn("mf_admin_hash", HUB)
        self.assertNotIn("관리자 비밀번호", HUB)

    def test_embedded_tools_are_sandboxed(self):
        self.assertIn(
            'sandbox="allow-scripts allow-same-origin allow-forms allow-downloads"',
            HUB,
        )
        self.assertNotIn("allow-top-navigation", HUB)
        self.assertNotIn("allow-popups", HUB)

    def test_workflow_links_cover_each_tool_once(self):
        workflow = HUB.split('<section class="workflow"', 1)[1].split(
            '</section>', 1
        )[0]
        expected = {"kw", "news", "eventcal", "serp", "seo", "adcopy", "power", "materiallab"}
        for tool_id in expected:
            self.assertEqual(workflow.count(f'data-tool="{tool_id}"'), 1)


if __name__ == "__main__":
    unittest.main()
