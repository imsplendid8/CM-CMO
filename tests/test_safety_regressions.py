import importlib.util
import io
import json
import pathlib
import tempfile
import unittest
from contextlib import redirect_stderr
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[1]


def load_script(name):
    path = ROOT / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


class TestTelegramSafety(unittest.TestCase):
    def test_html_message_is_split_only_between_complete_lines(self):
        utils = load_script("telegram_utils")
        line = '<a href="https://example.invalid/news?x=1&amp;y=2">기사 원문</a> · 뉴스 요약'
        chunks = utils.split_html_message("\n".join([line] * 100), maximum=300)
        self.assertGreater(len(chunks), 1)
        for chunk in chunks:
            self.assertLessEqual(len(chunk), 300)
            self.assertEqual(chunk.count("<a "), chunk.count("</a>"))

    def test_recipient_identifiers_are_not_logged(self):
        daily = (ROOT / "scripts/daily_brief.py").read_text(encoding="utf-8")
        fire = (ROOT / "scripts/fire_watch.py").read_text(encoding="utf-8")
        self.assertNotIn("{chat}: 예외", daily + fire)
        self.assertNotIn("', '.join(to)", daily)


class TestSearchAdLastKnownGood(unittest.TestCase):
    def setUp(self):
        self.agent = load_script("naver_searchad_volume")

    def make_root(self, directory, products):
        root = pathlib.Path(directory)
        (root / "data").mkdir()
        (root / "data/products.json").write_text(json.dumps({"products": products}), encoding="utf-8")
        (root / "data/volume.json").write_text('{"sentinel":"keep"}', encoding="utf-8")
        return root

    def test_missing_secrets_preserves_existing_volume(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.make_root(tmp, [{"key": "driver", "core": ["운전자보험"]}])
            with mock.patch.object(self.agent, "ROOT", str(root)), \
                 mock.patch.object(self.agent, "API_KEY", None), \
                 mock.patch.object(self.agent, "SECRET", None), \
                 mock.patch.object(self.agent, "CUSTOMER", None), \
                 redirect_stderr(io.StringIO()):
                self.assertEqual(self.agent.main(), 2)
            self.assertEqual(json.loads((root / "data/volume.json").read_text(encoding="utf-8")), {"sentinel": "keep"})

    def test_partial_fetch_preserves_existing_volume(self):
        products = [
            {"key": "driver", "core": ["운전자보험"]},
            {"key": "golf", "core": ["골프보험"]},
        ]
        response = {"keywordList": [{
            "relKeyword": "운전자보험", "monthlyPcQcCnt": 10,
            "monthlyMobileQcCnt": 20, "compIdx": "높음",
        }]}
        with tempfile.TemporaryDirectory() as tmp:
            root = self.make_root(tmp, products)
            with mock.patch.object(self.agent, "ROOT", str(root)), \
                 mock.patch.object(self.agent, "API_KEY", "key"), \
                 mock.patch.object(self.agent, "SECRET", "secret"), \
                 mock.patch.object(self.agent, "CUSTOMER", "customer"), \
                 mock.patch.object(self.agent, "keywordstool", side_effect=[response, RuntimeError("fail")]), \
                 mock.patch.object(self.agent.time, "sleep"), \
                 redirect_stderr(io.StringIO()):
                self.assertEqual(self.agent.main(), 1)
            self.assertEqual(json.loads((root / "data/volume.json").read_text(encoding="utf-8")), {"sentinel": "keep"})


class TestPagesAllowlist(unittest.TestCase):
    def test_build_contains_public_assets_only(self):
        builder = load_script("build_pages")
        with tempfile.TemporaryDirectory() as tmp:
            files = builder.build(ROOT, pathlib.Path(tmp) / "site")
            relative = {str(path.relative_to(pathlib.Path(tmp) / "site")).replace("\\", "/") for path in files}
        self.assertIn("index.html", relative)
        self.assertIn("data/seo/faq-opportunities.json", relative)
        self.assertNotIn("data/search-console.json", relative)
        self.assertNotIn("data/evidence/claims.json", relative)
        self.assertFalse(any(path.startswith("scripts/") or path.startswith(".github/") for path in relative))


if __name__ == "__main__":
    unittest.main()
