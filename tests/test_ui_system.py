import json
import pathlib
import re
import struct
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
APP_PAGES = [
    "index.html",
    "overview.html",
    "seo-audit.html",
    "keyword-tool.html",
    "news-tool.html",
    "serp-tool.html",
    "seasonal-tool.html",
    "adcopy-tool.html",
]
TOOL_PAGES = APP_PAGES[2:]


class TestUiSystem(unittest.TestCase):
    def read(self, name):
        return (ROOT / name).read_text(encoding="utf-8")

    def test_new_brand_mark_is_safe_and_used_everywhere(self):
        mark = self.read("icons/modoo-mark.svg")
        self.assertIn('viewBox="0 0 64 64"', mark)
        self.assertIn("linearGradient", mark)
        self.assertNotIn("<script", mark.lower())
        self.assertNotIn("foreignObject", mark)

        for page in APP_PAGES + ["event-calendar.html"]:
            with self.subTest(page=page):
                html = self.read(page)
                self.assertIn('type="image/svg+xml" href="icons/modoo-mark.svg"', html)
                self.assertIn('<meta name="theme-color" content="#111827">', html)
                self.assertNotIn('sizes="16x16"', html)

    def test_manifest_and_generated_png_dimensions(self):
        manifest = json.loads(self.read("site.webmanifest"))
        self.assertEqual(manifest["theme_color"], "#111827")
        self.assertEqual(manifest["icons"][0]["src"], "icons/modoo-mark.svg")

        expected = {
            "modoo-16.png": 16,
            "modoo-32.png": 32,
            "modoo-180.png": 180,
            "modoo-192.png": 192,
            "modoo-512.png": 512,
            "modoo-maskable-512.png": 512,
        }
        for name, size in expected.items():
            with self.subTest(icon=name):
                raw = (ROOT / "icons" / name).read_bytes()
                self.assertEqual(raw[:8], b"\x89PNG\r\n\x1a\n")
                width, height = struct.unpack(">II", raw[16:24])
                self.assertEqual((width, height), (size, size))

    def test_app_pages_load_shared_visual_and_icon_layers(self):
        for page in APP_PAGES:
            with self.subTest(page=page):
                html = self.read(page)
                self.assertIn('href="shared/ui-polish.css"', html)
                self.assertIn('src="shared/ui-icons.js"', html)
                self.assertNotRegex(html, r'id="themeBtn"[^>]*>\s*◐\s*</button>')

        for page in TOOL_PAGES:
            with self.subTest(page=page):
                html = self.read(page)
                self.assertRegex(html, r'class="brand-logo"[^>]*aria-hidden="true"[^>]*>\s*</(?:div|span)>')

    def test_hub_prioritizes_core_jobs_and_keyboard_access(self):
        hub = self.read("index.html")
        self.assertIn('const DESKTOP_CORE=["eventcal","kw","adcopy","news"]', hub)
        self.assertIn('const MOBILE_TABS=["eventcal","kw","adcopy","news"]', hub)
        self.assertIn('data-act="tools" aria-haspopup="menu" aria-expanded="false"', hub)
        self.assertIn('class="home-hero"', hub)
        self.assertIn('class="quick-actions"', hub)
        self.assertIn('tabindex="0" role="button"', hub)
        self.assertIn('e.key==="Enter"||e.key===" "', hub)

    def test_shared_layer_covers_focus_motion_and_mobile_navigation(self):
        css = self.read("shared/ui-polish.css")
        icons = self.read("shared/ui-icons.js")
        mobile = self.read("shared/mobile-sidebar.js")
        self.assertIn(":focus-visible", css)
        self.assertIn("prefers-reduced-motion:reduce", css)
        self.assertIn("min-height:44px", css)
        self.assertIn("본문으로 건너뛰기", icons)
        self.assertIn("MutationObserver", icons)
        self.assertIn("상품과 화면 메뉴 열기", mobile)
        self.assertIn("<svg", mobile)


if __name__ == "__main__":
    unittest.main()
