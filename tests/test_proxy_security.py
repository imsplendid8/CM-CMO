import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
WORKER = (ROOT / "proxy" / "naver-proxy-worker.js").read_text(encoding="utf-8")
HUB = (ROOT / "index.html").read_text(encoding="utf-8")
OVERVIEW = (ROOT / "overview.html").read_text(encoding="utf-8")


class TestProxySecurity(unittest.TestCase):
    def test_searchad_public_route_is_read_only_and_exact(self):
        self.assertIn('p === "/searchad/keywordstool"', WORKER)
        self.assertIn('return method === "GET"', WORKER)
        self.assertNotIn('p.startsWith("/searchad/")', WORKER)
        self.assertNotIn('if (method === "POST") init.body', WORKER)

    def test_searchad_management_paths_are_not_documented_as_allowed(self):
        self.assertNotIn("GET|POST /searchad/*", WORKER)
        self.assertIn("/ncc/* 등 광고 관리 API는 절대 전달하지 않는다", WORKER)

    def test_request_limits_and_fail_closed_rate_limit_exist(self):
        self.assertIn("MAX_QUERY_LENGTH", WORKER)
        self.assertIn("MAX_BODY_BYTES", WORKER)
        self.assertIn("catch (e) { return false; }", WORKER)

    def test_public_pages_ship_no_client_admin_gate(self):
        public_html = HUB + OVERVIEW
        for marker in ("DEFAULT_ADMIN_HASH", "mf_admin_hash", "mf_admin", "brief-setup.html"):
            self.assertNotIn(marker, public_html)


if __name__ == "__main__":
    unittest.main()
