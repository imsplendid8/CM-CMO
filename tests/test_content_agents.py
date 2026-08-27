import importlib.util
import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]


def module(name):
    path = ROOT / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


class TestSerpCopyAgent(unittest.TestCase):
    def test_generates_copy_and_visual_inputs_with_diff(self):
        agent = module("serp_copy_agent")
        products = {"products": [{"key": "driver", "name": "운전자보험", "serpKw": "운전자보험",
                    "core": ["운전자보험"], "special": ["벌금", "변호사선임"]}]}
        analysis = {"asof": "2026-08-24", "products": {"driver": {"common_soju": ["벌금"], "observed_ads": [
            {"date": "2026-08-24", "brand": "A"}, {"date": "2026-08-17", "brand": "B"}]}}}
        result = agent.generate(products, analysis, {})["products"][0]
        self.assertEqual(result["selected_angle"], "변호사선임")
        self.assertEqual(result["serp_diff"]["entered_brands"], ["A"])
        self.assertEqual(result["analysis_status"], "ready")
        self.assertIn("변호사선임", result["copy_direction"])
        self.assertIn("보험종목 장면", result["visual_direction"])
        self.assertEqual(len(result["sa_recommendations"]), 3)
        self.assertTrue(all(row.get("additional_description") for row in result["sa_recommendations"]))
        self.assertEqual(len(result["image_directions"]), 4)
        self.assertEqual(len({row["asset"] for row in result["image_directions"]}), 4)
        self.assertTrue(all(row["text_overlay"] is False for row in result["image_directions"]))
        self.assertEqual(result["image_plan"]["refresh_cadence"], "monthly")
        self.assertEqual(result["image_plan"]["unique_asset_count"], 4)
        self.assertEqual(len(result["power_content_topics"]), 3)
        serialized = json.dumps(result, ensure_ascii=False)
        for removed in ("claim_ids", "evidence_status", "review_status"):
            self.assertNotIn(removed, serialized)

    def test_monthly_capture_and_dom_patterns_are_shared_across_materials(self):
        agent = module("serp_copy_agent")
        products = {"products": [{"key": "driver", "name": "운전자보험", "serpKw": "운전자보험",
                    "core": ["운전자보험"], "special": ["벌금", "교통사고"]}]}
        analysis = {"products": {"driver": {"soju": [["벌금", 2]], "observed_ads": [
            {"date": "2026-08-02", "brand": "A", "title": "A 운전자보험", "desc": "보장 확인"}]}}}
        manifest = {"asof": "2026-08-23", "shots": {"driver": {"captures": [
            {"date": "2026-08-02"}, {"date": "2026-08-09"}, {"date": "2026-08-16"}, {"date": "2026-08-23"}]}}}
        dom = {"asof": "2026-08-23", "observations": [{"product": "driver", "date": "2026-08-23",
               "text": "운전자보험 보험료 계산 간편 가입 이벤트"}]}
        result = agent.generate(products, analysis, {}, manifest, dom)["products"][0]
        self.assertEqual(result["month"], "2026-08")
        self.assertEqual(result["monitoring"]["capture_count_35d"], 4)
        self.assertEqual(result["monitoring"]["status"], "current_patterns_ready")
        self.assertIn(["보험료·견적 확인", 1], result["market_patterns"]["message_patterns"])
        self.assertEqual(result["latest_date"], "2026-08-23")

    def test_volume_keyword_avoids_excluded_queries(self):
        agent = module("serp_copy_agent")
        product = {"key": "driver", "name": "운전자보험", "serpKw": "운전자보험",
                   "core": ["운전자보험"], "special": ["교통사고"], "excluded": ["고객센터"]}
        volume = {"products": {"driver": {"keywords": {
            "운전자보험 고객센터": {"pc": 9999, "mobile": 9999},
            "운전자보험": {"pc": 100, "mobile": 200},
        }}}}
        self.assertEqual(agent.volume_keyword(volume, product), "운전자보험")

    def test_monthly_image_plan_rotates_without_duplicate_sources(self):
        agent = module("serp_copy_agent")
        product = {"key": "driver", "name": "운전자보험", "serpKw": "운전자보험",
                   "core": ["운전자보험"], "special": ["교통사고"]}
        products = {"products": [product]}
        analysis = {"products": {"driver": {"observed_ads": [
            {"date": "2026-08-24", "brand": "A", "title": "운전자보험 보장 확인"}]}}}
        august = agent.generate(products, analysis, {}, planning_month="2026-08")["products"][0]
        september = agent.generate(products, analysis, {}, planning_month="2026-09")["products"][0]
        august_assets = [row["asset"] for row in august["image_directions"]]
        september_assets = [row["asset"] for row in september["image_directions"]]
        self.assertEqual(len(august_assets), 4)
        self.assertEqual(len(set(august_assets)), 4)
        self.assertEqual(len(set(september_assets)), 4)
        self.assertNotEqual(set(august_assets), set(september_assets))
        self.assertTrue(all(pathlib.Path(asset).name.startswith("driver-") for asset in august_assets))
        self.assertTrue(all(pathlib.Path(asset).name.startswith("driver-") for asset in september_assets))
        for asset in set(august_assets + september_assets):
            self.assertTrue((ROOT / asset).is_file(), asset)

    def test_monthly_power_topics_rotate_without_repeating_the_same_three(self):
        agent = module("serp_copy_agent")
        product = {"key": "driver", "name": "운전자보험", "serpKw": "운전자보험",
                   "core": ["운전자보험"], "special": ["벌금", "변호사선임", "교통사고"]}
        products = {"products": [product]}
        analysis = {"products": {"driver": {"observed_ads": [
            {"date": "2026-08-24", "brand": "A", "title": "운전자보험 보장 확인"}]}}}
        august = agent.generate(products, analysis, {}, planning_month="2026-08")["products"][0]
        september = agent.generate(products, analysis, {}, planning_month="2026-09")["products"][0]
        august_topics = {row["pattern"] for row in august["power_content_topics"]}
        september_topics = {row["pattern"] for row in september["power_content_topics"]}
        self.assertEqual(len(august_topics), 3)
        self.assertEqual(len(september_topics), 3)
        self.assertNotEqual(august_topics, september_topics)

    def test_monthly_thumbnail_workflow_archives_and_redeploys(self):
        workflow = (ROOT / ".github/workflows/monthly-image-plan.yml").read_text(encoding="utf-8")
        pages = (ROOT / ".github/workflows/pages.yml").read_text(encoding="utf-8")
        self.assertIn('cron: "30 0 1 * *"', workflow)
        self.assertIn("--archive-images", workflow)
        self.assertIn("data/adcopy/image-plans/", workflow)
        self.assertIn('"Monthly Image Thumbnail Plan"', pages)

    def test_brand_home_is_not_emitted_as_product_insight(self):
        agent = module("serp_copy_agent")
        products = {"products": [{"key": "home", "cat": "사이트", "name": "다이렉트 홈",
                    "serpKw": "한화손보 다이렉트", "core": ["한화손보 다이렉트"], "special": ["운전자보험"]}]}
        analysis = {"products": {"home": {"observed_ads": [{"date": "2026-08-24", "brand": "A"}]}}}
        self.assertEqual(agent.generate(products, analysis, {})["products"], [])


class TestFaqOpportunityAgent(unittest.TestCase):
    def test_search_demand_creates_question_review_queue(self):
        agent = module("faq_opportunity_agent")
        products = {"products": [{"key": "chronic", "name": "유병자 간편보험",
                    "core": ["유병자보험"], "special": ["간편심사"]}]}
        volume = {"asof": "2026-08-24", "products": {"chronic": {"keywords": {
            "유병자보험 보험료": {"pc": 10, "mobile": 90},
        }}}}
        row = agent.generate(products, volume)["products"][0]["opportunities"][0]
        self.assertIn("어떤 조건에 따라 달라지나요?", row["question"])
        self.assertEqual(row["review_status"], "content_review_required")
        self.assertEqual(row["next_action"], "상품자료·약관을 확인해 답변 작성")
        serialized = json.dumps(row, ensure_ascii=False)
        self.assertNotIn("claim", serialized)
        self.assertNotIn("evidence", serialized)

    def test_private_gsc_query_never_reaches_public_faq_payload(self):
        agent = module("faq_opportunity_agent")
        products = {"products": [{"key": "chronic", "name": "유병자 간편보험",
                    "core": ["유병자보험"], "special": ["간편심사"]}]}
        volume = {"asof": "2026-08-24", "products": {"chronic": {"keywords": {
            "유병자보험 보험료": {"pc": 10, "mobile": 90},
        }}}}
        gsc = {"rows": [{"query": "내부에서만 보이는 유병자 질문", "impressions": 9876}]}
        serialized = json.dumps(agent.generate(products, volume, gsc), ensure_ascii=False)
        self.assertNotIn("내부에서만 보이는", serialized)
        self.assertNotIn("9876", serialized)
        self.assertNotIn("search_console", serialized)

    def test_generated_outputs_are_loaded_only_where_needed(self):
        seo = (ROOT / "seo-audit.html").read_text(encoding="utf-8")
        adcopy = (ROOT / "adcopy-tool.html").read_text(encoding="utf-8")
        self.assertNotIn("data/seo/faq-opportunities.json", seo)
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
