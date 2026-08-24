import importlib.util
import json
import pathlib
import unittest
from datetime import date

ROOT = pathlib.Path(__file__).resolve().parents[1]


def module():
    path = ROOT / "scripts" / "seo_title_agent.py"
    spec = importlib.util.spec_from_file_location("seo_title_agent", path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


class TestSeoTitleOps(unittest.TestCase):
    def setUp(self):
        self.agent = module()
        self.products = {"products": [{
            "key": "driver", "name": "운전자보험", "serpKw": "운전자보험",
            "core": ["운전자보험"], "special": ["변호사선임", "교통사고"],
        }]}
        self.volume = {"asof": "2026-08-24", "source": "searchad", "products": {"driver": {"keywords": {
            "운전자보험": {"pc": 100, "mobile": 900, "comp": "높음"},
            "운전자보험비교": {"pc": 30, "mobile": 270, "comp": "중간"},
            "교통사고합의금": {"pc": 20, "mobile": 180, "comp": "높음"},
            "DB운전자보험": {"pc": 500, "mobile": 5000, "comp": "높음"},
        }}}}
        self.faq = {"asof": "2026-08-24", "products": [{"product_key": "driver", "opportunities": [
            {"query": "운전자보험", "demand": 1000},
            {"query": "DB운전자보험", "demand": 5500},
            {"query": "운전자보험비교", "demand": 300},
            {"query": "교통사고합의금", "demand": 200},
        ]}]}

    def test_missing_gsc_keeps_three_drafts_without_recommendation(self):
        result = self.agent.generate(self.products, self.volume, self.faq)
        product = result["products"][0]
        self.assertEqual(product["status"], "blocked_gsc")
        self.assertIsNone(product["recommended_candidate_id"])
        self.assertEqual(len(product["candidates"]), 3)
        self.assertFalse(any("DB" in row["target_query"] for row in product["candidates"]))
        for row in product["candidates"]:
            self.assertGreaterEqual(row["title_length"], 15)
            self.assertLessEqual(row["title_length"], 34)
            self.assertEqual(row["review_status"], "human_review_required")
            self.assertTrue(row["weakness"])

    def test_private_gsc_is_reduced_to_categories_and_cannibalization_blocks(self):
        gsc = {"asof": "2026-08-24", "rows": [
            {"query": "운전자보험", "page": "https://example.invalid/a", "impressions": 90, "position": 8},
            {"query": "운전자보험", "page": "https://example.invalid/b", "impressions": 20, "position": 11},
            {"query": "운전자보험비교", "page": "https://example.invalid/c", "impressions": 120, "position": 9},
        ]}
        result = self.agent.generate(self.products, self.volume, self.faq, gsc, today=date(2026, 8, 24))
        product = result["products"][0]
        blocked = next(row for row in product["candidates"] if row["target_query"] == "운전자보험")
        self.assertEqual(blocked["decision"], "rejected_cannibalization")
        self.assertNotEqual(product["recommended_candidate_id"], blocked["id"])
        text = json.dumps(result, ensure_ascii=False)
        for private in ('"page"', '"clicks"', '"impressions"', '"ctr"', '"position"'):
            self.assertNotIn(private, text)
        self.assertNotIn("example.invalid", text)

    def test_stale_gsc_cannot_unlock_recommendation(self):
        gsc = {"asof": "2026-01-01", "rows": [
            {"query": "운전자보험", "page": "https://example.invalid/a", "impressions": 90, "position": 8},
        ]}
        result = self.agent.generate(self.products, self.volume, self.faq, gsc, today=date(2026, 8, 24))
        self.assertEqual(result["sources"]["gsc"], "stale")
        self.assertIsNone(result["products"][0]["recommended_candidate_id"])

    def test_repository_output_contract(self):
        payload = json.loads((ROOT / "data/seo/title-opportunities.json").read_text(encoding="utf-8"))
        self.assertEqual(len(payload["products"]), 13)
        self.assertEqual(self.agent.validate(payload), [])
        workflow = (ROOT / ".github/workflows/content-intelligence.yml").read_text(encoding="utf-8")
        page = (ROOT / "seo-audit.html").read_text(encoding="utf-8")
        self.assertIn("scripts/seo_title_agent.py", workflow)
        self.assertIn("data/seo/title-opportunities.json", page)


if __name__ == "__main__":
    unittest.main()
