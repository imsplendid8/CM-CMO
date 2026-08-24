import importlib.util
import json
import pathlib
import unittest
from datetime import date

ROOT = pathlib.Path(__file__).resolve().parents[1]


def module(name):
    path = ROOT / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


class TestClaimEvidence(unittest.TestCase):
    def test_registry_is_valid_and_unapproved_by_default(self):
        claims = json.loads((ROOT / "data/evidence/claims.json").read_text(encoding="utf-8"))
        products = json.loads((ROOT / "data/products.json").read_text(encoding="utf-8"))
        errors = module("claim_evidence").validate(claims, {p["key"] for p in products["products"]})
        self.assertEqual(errors, [])
        self.assertEqual(len(claims["claims"]), 13)
        self.assertFalse(any(c["review_status"] == "approved" for c in claims["claims"]))

    def test_only_current_channel_approved_claims_resolve(self):
        ce = module("claim_evidence")
        base = {"claim_id": "x", "product_key": "driver", "review_status": "approved",
                "allowed_channels": ["faq"], "effective_from": "2026-01-01", "valid_until": "2026-12-31"}
        self.assertEqual(len(ce.active_claims({"claims": [base]}, "driver", "faq", date(2026, 8, 24))), 1)
        self.assertEqual(ce.active_claims({"claims": [base]}, "driver", "sa_title", date(2026, 8, 24)), [])

    def test_review_cli_requires_real_reviewer_and_source(self):
        source = (ROOT / "scripts/claim_evidence.py").read_text(encoding="utf-8")
        self.assertIn("실제 검토자 --reviewer가 필요합니다", source)
        self.assertIn("--source-path, --effective-from, --channels", source)

    def test_review_is_immutable_and_keeps_history(self):
        ce = module("claim_evidence")
        original = {"updated": "2026-01-01", "claims": [{"claim_id": "x", "product_key": "driver",
            "claim": "변호사선임비용", "review_status": "needs_product_review", "source": {}, "allowed_channels": []}]}
        reviewed = ce.review_claim(original, "x", "approve", "상품 담당", source_path="설명서.pdf#p=12",
            effective_from="2026-08-01", valid_until="2027-07-31", channels=["faq"], disclosure="지급조건 확인")
        self.assertEqual(original["claims"][0]["review_status"], "needs_product_review")
        claim = reviewed["claims"][0]
        self.assertEqual(claim["review_status"], "approved")
        self.assertEqual(claim["review_history"][0]["from_status"], "needs_product_review")
        self.assertEqual(claim["source"]["path"], "설명서.pdf#p=12")

    def test_registry_rejects_invalid_date_range(self):
        ce = module("claim_evidence")
        claim = {"claim_id": "x", "product_key": "driver", "review_status": "approved", "reviewer": "담당",
            "source": {"path": "x"}, "effective_from": "2027-01-01", "valid_until": "2026-01-01", "allowed_channels": ["faq"]}
        self.assertTrue(any("valid_until" in e for e in ce.validate({"claims": [claim]}, {"driver"})))


class TestSerpCopyAgent(unittest.TestCase):
    def test_faq_only_or_expired_claim_does_not_verify_sa(self):
        agent = module("serp_copy_agent")
        base = {"review_status": "approved", "effective_from": "2026-01-01", "valid_until": "2026-12-31"}
        self.assertFalse(agent.claim_allows_sa({**base, "allowed_channels": ["faq"]}, date(2026, 8, 24)))
        self.assertFalse(agent.claim_allows_sa({**base, "allowed_channels": ["sa_title", "sa_description"], "valid_until": "2026-01-31"}, date(2026, 8, 24)))
        self.assertTrue(agent.claim_allows_sa({**base, "allowed_channels": ["sa_title", "sa_description"]}, date(2026, 8, 24)))

    def test_unrelated_approved_claim_does_not_verify_candidate(self):
        agent = module("serp_copy_agent")
        claims = [{"claim_id": "dental", "claim": "임플란트 보장", "consumer_text": "임플란트"}]
        self.assertEqual(agent.relevant_claim_ids(claims, "변호사선임비용 가입 조건 확인"), [])
        self.assertEqual(agent.relevant_claim_ids(claims, "임플란트 보장 여부 확인"), ["dental"])

    def test_generates_review_only_safe_pairs_and_diff(self):
        agent = module("serp_copy_agent")
        products = {"products": [{"key": "driver", "name": "운전자보험", "serpKw": "운전자보험",
                    "core": ["운전자보험"], "special": ["벌금", "변호사선임"]}]}
        analysis = {"asof": "2026-08-24", "products": {"driver": {"common_soju": ["벌금"], "observed_ads": [
            {"date": "2026-08-24", "brand": "A"}, {"date": "2026-08-17", "brand": "B"}]}}}
        result = agent.generate(products, analysis, {}, {"claims": []})["products"][0]
        self.assertEqual(result["selected_angle"], "변호사선임")
        self.assertEqual(result["serp_diff"]["entered_brands"], ["A"])
        self.assertTrue(result["candidates"])
        for row in result["candidates"]:
            self.assertLessEqual(row["title_length"], 15)
            self.assertGreaterEqual(row["description_length"], 20)
            self.assertLessEqual(row["description_length"], 45)
            self.assertEqual(row["evidence_status"], "product_evidence_required")
            self.assertEqual(row["review_status"], "human_review_required")


class TestFaqOpportunityAgent(unittest.TestCase):
    def test_expired_or_wrong_channel_claim_does_not_unlock_faq(self):
        agent = module("faq_opportunity_agent")
        base = {"review_status": "approved", "effective_from": "2026-01-01", "valid_until": "2026-12-31"}
        self.assertFalse(agent.claim_allows_faq({**base, "allowed_channels": ["sa_title"]}, date(2026, 8, 24)))
        self.assertFalse(agent.claim_allows_faq({**base, "allowed_channels": ["faq"], "valid_until": "2026-01-31"}, date(2026, 8, 24)))
        self.assertTrue(agent.claim_allows_faq({**base, "allowed_channels": ["faq"]}, date(2026, 8, 24)))

    def test_unrelated_product_claim_does_not_unlock_question(self):
        agent = module("faq_opportunity_agent")
        claims = [{"claim_id": "price", "claim": "보험료 산출 조건", "consumer_text": "보험료"}]
        self.assertEqual(agent.relevant_claim_ids(claims, "유병자보험 가입 가능 여부"), [])
        self.assertEqual(agent.relevant_claim_ids(claims, "유병자보험 보험료는 어떻게 달라지나요"), ["price"])

    def test_search_demand_creates_questions_but_not_answers_without_claim(self):
        agent = module("faq_opportunity_agent")
        products = {"products": [{"key": "chronic", "name": "유병자 간편보험", "core": ["유병자보험"], "special": ["간편심사"]}]}
        volume = {"asof": "2026-08-24", "products": {"chronic": {"keywords": {"유병자보험 보험료": {"pc": 10, "mobile": 90}}}}}
        result = agent.generate(products, volume, {}, {"claims": []})
        row = result["products"][0]["opportunities"][0]
        self.assertIn("어떤 조건에 따라 달라지나요?", row["question"])
        self.assertEqual(row["answer_status"], "evidence_required")
        self.assertFalse(result["search_console_connected"])

    def test_generated_outputs_are_loaded_by_user_tools(self):
        seo = (ROOT / "seo-audit.html").read_text(encoding="utf-8")
        adcopy = (ROOT / "adcopy-tool.html").read_text(encoding="utf-8")
        self.assertIn("data/seo/faq-opportunities.json", seo)
        self.assertIn("승인된 상품 근거가 없는 질문은 공개 FAQ에 자동 추가하지 않습니다", seo)
        self.assertIn("FAQPage를 검색 노출 혜택으로 권장하지 않습니다", seo)
        self.assertIn("data/adcopy/serp-candidates.json", adcopy)
        self.assertIn("SERP_AGENT", adcopy)

    def test_gsc_and_serp_dom_review_automation_are_wired(self):
        workflow = (ROOT / ".github/workflows/content-intelligence.yml").read_text(encoding="utf-8")
        capture = (ROOT / "scripts/capture_serp.mjs").read_text(encoding="utf-8")
        self.assertIn("scripts/fetch_search_console.py", workflow)
        self.assertIn("GSC_REFRESH_TOKEN", workflow)
        self.assertIn("dom_observations.json", capture)
        self.assertIn('confidence:"needs_review"', capture)


if __name__ == "__main__":
    unittest.main()
