import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
TOOLS = [
    "adcopy-tool.html",
    "keyword-tool.html",
    "news-tool.html",
    "seo-audit.html",
    "seasonal-tool.html",
    "terms-tool.html",
    "serp-tool.html",
]


class TestMobileAndHealth(unittest.TestCase):
    def test_keyword_product_count_comes_from_product_master(self):
        html = (ROOT / "keyword-tool.html").read_text(encoding="utf-8")
        self.assertIn('PRODUCTS.length+"개 상품(광고그룹)"', html)
        self.assertNotRegex(html, r'\d+개 상품\(광고그룹\)')

    def test_sidebar_tools_load_shared_mobile_drawer(self):
        for name in TOOLS:
            html = (ROOT / name).read_text(encoding="utf-8")
            with self.subTest(name=name):
                self.assertIn('href="shared/mobile-sidebar.css"', html)
                self.assertIn('src="shared/mobile-sidebar.js"', html)

    def test_mobile_drawer_is_accessible_and_closable(self):
        js = (ROOT / "shared" / "mobile-sidebar.js").read_text(encoding="utf-8")
        self.assertIn('aria-controls', js)
        self.assertIn('aria-expanded', js)
        self.assertIn('event.key === "Escape"', js)
        self.assertNotIn("localStorage", js)

    def test_hub_recomputes_six_source_health_and_partial_errors(self):
        hub = (ROOT / "index.html").read_text(encoding="utf-8")
        for path in (
            "data/clips/index.json",
            "data/signals.json",
            "data/volume.json",
            "data/trends.json",
            "data/papers.json",
            "serp/manifest.json",
        ):
            self.assertIn(path, hub)
        self.assertIn('partial:"일부 실패"', hub)
        self.assertIn('function dataErrors', hub)


if __name__ == "__main__":
    unittest.main()
