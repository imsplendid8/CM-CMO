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

    def test_moving_holiday_is_used_only_in_its_dated_month(self):
        agent = module("serp_copy_agent")
        products = {"products": [{"key": "driver", "name": "운전자보험", "serpKw": "운전자보험",
                    "core": ["운전자보험"], "special": ["벌금", "변호사선임"]}]}
        analysis = {"products": {"driver": {"observed_ads": [
            {"date": "2026-08-24", "brand": "A", "title": "운전자보험 보험료"}]}}}
        seasonal = {"seasonal": {"driver": [{"m": [9, 10], "tag": "명절 장거리 운전",
                    "kws": ["추석 운전자보험"]}]}}
        calendar = {"events": [{"id": "chuseok-2026", "type": "명절", "name": "추석 연휴",
                    "start": "2026-09-24", "end": "2026-09-27", "products": ["driver"],
                    "keywords": ["추석", "장거리 운전", "추석 운전자보험"]}]}
        september = agent.generate(products, analysis, {}, planning_month="2026-09",
                                   seasonal=seasonal, calendar=calendar)["products"][0]
        october = agent.generate(products, analysis, {}, planning_month="2026-10",
                                 seasonal=seasonal, calendar=calendar)["products"][0]
        self.assertEqual(september["season_context"]["event_id"], "chuseok-2026")
        self.assertEqual(september["power_content_topics"][0]["pattern"], "seasonal_scene")
        self.assertEqual(october["season_context"]["status"], "evergreen")
        self.assertNotIn("추석", json.dumps(october["sa_recommendations"], ensure_ascii=False))

    def test_copy_uses_multiple_message_axes_without_generic_fear_template(self):
        agent = module("serp_copy_agent")
        products = {"products": [{"key": "driver", "name": "운전자보험", "serpKw": "운전자보험",
                    "core": ["운전자보험"], "special": ["벌금", "변호사선임", "교통사고"]}]}
        analysis = {"products": {"driver": {"common_soju": ["보험료"], "observed_ads": [
            {"date": "2026-08-24", "brand": "A", "title": "보험료 계산", "desc": "간편 가입"}]}}}
        result = agent.generate(products, analysis, {}, planning_month="2026-08")["products"][0]
        rows = result["sa_recommendations"]
        self.assertEqual(len({row["message_axis"] for row in rows}), 3)
        text = json.dumps(rows, ensure_ascii=False)
        for stale in ("갑작스러운", "미리 대비하세요", "든든하게 대비"):
            self.assertNotIn(stale, text)
        self.assertEqual(len({row["description"][-8:] for row in rows}), 3)

    def test_same_annual_event_changes_with_year_and_serp_signature(self):
        agent = module("serp_copy_agent")
        products = {"products": [{"key": "driver", "name": "운전자보험", "serpKw": "운전자보험",
                    "core": ["운전자보험"], "special": ["벌금", "변호사선임", "교통사고"]}]}
        calendar = {"events": [
            {"id": "chuseok-2026", "type": "명절", "name": "추석 연휴", "start": "2026-09-24", "end": "2026-09-27", "products": ["driver"]},
            {"id": "chuseok-2027", "type": "명절", "name": "추석 연휴", "start": "2027-09-14", "end": "2027-09-16", "products": ["driver"]},
        ]}
        analysis_a = {"products": {"driver": {"common_soju": ["보험료"], "observed_ads": [
            {"date": "2026-08-24", "brand": "A", "title": "보험료 계산"}]}}}
        analysis_b = {"products": {"driver": {"common_soju": ["간편가입"], "observed_ads": [
            {"date": "2027-08-24", "brand": "B", "title": "온라인 가입"}]}}}
        first = agent.generate(products, analysis_a, {}, planning_month="2026-09", calendar=calendar)["products"][0]
        second = agent.generate(products, analysis_b, {}, planning_month="2027-09", calendar=calendar)["products"][0]
        self.assertNotEqual(first["variation"]["variation_key"], second["variation"]["variation_key"])
        self.assertNotEqual(first["serp_signature"], second["serp_signature"])
        self.assertNotEqual(first["power_content_topics"][0]["title"], second["power_content_topics"][0]["title"])

    def test_previous_month_images_are_marked_for_new_generation(self):
        agent = module("serp_copy_agent")
        product = {"key": "driver", "name": "운전자보험", "serpKw": "운전자보험",
                   "core": ["운전자보험"], "special": ["벌금", "교통사고"]}
        products = {"products": [product]}
        analysis = {"products": {"driver": {"observed_ads": [
            {"date": "2026-08-24", "brand": "A", "title": "운전자보험"}]}}}
        august = agent.generate(products, analysis, {}, planning_month="2026-08")
        archive = agent.image_plan_archive(august)
        september = agent.generate(products, analysis, {}, planning_month="2026-09",
                                   image_history=[archive])["products"][0]
        self.assertGreaterEqual(september["image_plan"]["new_generation_required"], 3)
        self.assertTrue(all(row["style_family"] == "premium_3d_animation_v4"
                            for row in september["image_directions"]))
        self.assertEqual(len({row["concept_id"] for row in september["image_directions"]}), 4)

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
        build_pages = (ROOT / "scripts" / "build_pages.py").read_text(encoding="utf-8")
        self.assertNotIn("data/seo/faq-opportunities.json", seo)
        self.assertIn("SEO Intelligence", seo)
        self.assertIn("SEO_INTEL_STORE", seo)
        self.assertIn("SEO_INTEL_DRAFT_STORE", seo)
        self.assertIn("data/seo/site-observations.json", seo)
        self.assertIn("리뷰 큐", seo)
        self.assertIn("월간 변화", seo)
        self.assertIn("data/seo/site-observations.json", build_pages)
        self.assertIn("data/adcopy/serp-candidates.json", adcopy)
        self.assertIn("SERP_AGENT", adcopy)

    def test_seo_intel_schema_supports_query_and_diff_fields(self):
        schema = (ROOT / "docs" / "seo-intelligence-schema.md").read_text(encoding="utf-8")
        data = json.loads((ROOT / "data" / "seo" / "site-observations.json").read_text(encoding="utf-8"))
        workflow = (ROOT / ".github" / "workflows" / "content-intelligence.yml").read_text(encoding="utf-8")
        builder = (ROOT / "scripts" / "build_seo_intel.py").read_text(encoding="utf-8")
        self.assertEqual(data["schema_version"], 3)
        self.assertIn("site_query", schema)
        self.assertIn("rising_angles", schema)
        self.assertIn("declining_angles", schema)
        self.assertIn("cannibalization", schema)
        self.assertIn("build_seo_intel.py", workflow)
        self.assertIn("site-query-feed.json", builder)
        self.assertIn("search-console.json", builder)
        self.assertIn("keyword-autocomplete.json", builder)
        self.assertIn("site-query-feed.example.json", schema)

    def test_seo_intel_builds_cannibalization_summary_from_duplicate_queries(self):
        agent = module("build_seo_intel")
        rows = [
            {"domain": "a.example", "site_query": "운전자보험", "query": "운전자보험", "url": "https://a.example/one", "status": "active"},
            {"domain": "a.example", "site_query": "운전자보험", "query": "운전자보험", "url": "https://a.example/two", "status": "review"},
            {"domain": "b.example", "site_query": "운전자보험비교", "query": "운전자보험비교", "url": "https://b.example/x", "status": "active"},
        ]
        result = agent.build_cannibalization(rows)
        self.assertEqual(result["total_conflicted_queries"], 1)
        self.assertEqual(result["conflicted_queries"][0]["query"], "운전자보험")
        self.assertEqual(result["conflicted_queries"][0]["url_count"], 2)

    def test_gsc_and_serp_dom_review_automation_are_wired(self):
        workflow = (ROOT / ".github/workflows/content-intelligence.yml").read_text(encoding="utf-8")
        capture = (ROOT / "scripts/capture_serp.mjs").read_text(encoding="utf-8")
        self.assertIn("scripts/fetch_search_console.py", workflow)
        self.assertIn("GSC_REFRESH_TOKEN", workflow)
        self.assertIn("dom_observations.json", capture)
        self.assertIn('confidence:"needs_review"', capture)


if __name__ == "__main__":
    unittest.main()
