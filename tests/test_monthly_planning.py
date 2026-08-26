import importlib.util
import json
import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]


def load_volume_module():
    path = ROOT / "scripts" / "naver_searchad_volume.py"
    spec = importlib.util.spec_from_file_location("naver_searchad_volume", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestVolumeHistory(unittest.TestCase):
    def test_compacts_pc_and_mobile_and_replaces_same_month(self):
        module = load_volume_module()
        first = {
            "asof": "2026-08-16",
            "products": {"cncr": {"keywords": {"암보험": {"pc": 10, "mobile": 90, "comp": "높음"}}}},
        }
        history = module.update_history({}, first, "2026-08")
        row = history["snapshots"]["2026-08"]["products"]["cncr"]["keywords"]["암보험"]
        self.assertEqual(row, {"total": 100, "comp": "높음"})

        second = {
            "asof": "2026-08-23",
            "products": {"cncr": {"keywords": {"암보험": {"pc": 20, "mobile": 180, "comp": "높음"}}}},
        }
        history = module.update_history(history, second, "2026-08")
        snapshot = history["snapshots"]["2026-08"]
        self.assertEqual(snapshot["asof"], "2026-08-23")
        self.assertEqual(snapshot["products"]["cncr"]["keywords"]["암보험"]["total"], 200)

    def test_keeps_only_latest_retention_months(self):
        module = load_volume_module()
        history = {"snapshots": {f"2025-{month:02d}": {"asof": "old", "products": {}} for month in range(1, 13)}}
        current = {"asof": "2026-01-05", "products": {}}
        updated = module.update_history(history, current, "2026-01", retention=3)
        self.assertEqual(list(updated["snapshots"]), ["2025-11", "2025-12", "2026-01"])

    def test_seed_history_matches_current_volume_month(self):
        volume = json.loads((ROOT / "data" / "volume.json").read_text(encoding="utf-8"))
        history = json.loads((ROOT / "data" / "volume-history.json").read_text(encoding="utf-8"))
        month = volume["asof"][:7]
        self.assertIn(month, history["snapshots"])
        self.assertEqual(history["snapshots"][month]["asof"], volume["asof"])
        self.assertEqual(set(history["snapshots"][month]["products"]), set(volume["products"]))


class TestMonthlyPlanningUiContract(unittest.TestCase):
    def read(self, name):
        return (ROOT / name).read_text(encoding="utf-8")

    def test_shared_month_selector_drives_plan_and_copy(self):
        shared = self.read("shared/planning-context.js")
        seasonal = self.read("seasonal-tool.html")
        adcopy = self.read("adcopy-tool.html")
        self.assertIn("cm_cmo_plan_month", shared)
        self.assertIn('id="planMonth"', seasonal)
        self.assertIn('id="planMonth"', adcopy)
        self.assertIn("선택월·익월 실행 플랜", seasonal)
        self.assertIn("function planningIssues", adcopy)
        self.assertIn("const issues=planningIssues(p)", adcopy)
        self.assertIn("상품 내용과 심의를 확인한 뒤 사용하세요", adcopy)

    def test_naver_volume_and_monthly_mover_contract(self):
        seasonal = self.read("seasonal-tool.html")
        keyword = self.read("keyword-tool.html")
        workflow = self.read(".github/workflows/searchad.yml")
        self.assertIn('fetch("data/volume.json"', seasonal)
        self.assertIn("data/volume-history.json", keyword)
        self.assertIn("NEW_MIN=100", keyword)
        self.assertIn("RISING_MIN_DELTA=50", keyword)
        self.assertIn("RISING_MIN_RATE=.5", keyword)
        self.assertIn("data/volume-history.json", workflow)

    def test_monthly_autocomplete_discovery_and_selected_export_contract(self):
        keyword = self.read("keyword-tool.html")
        workflow = self.read(".github/workflows/monthly-keyword-discovery.yml")
        collector = self.read("scripts/capture_naver_autocomplete.mjs")
        core = self.read("scripts/keyword_autocomplete_core.mjs")
        pages = self.read("scripts/build_pages.py")
        self.assertIn("data/keyword-autocomplete.json", keyword)
        self.assertIn("선택 키워드 등록 CSV", keyword)
        self.assertIn("registration===\"recommended\"", keyword)
        self.assertIn('cron: "45 0 1 * *"', workflow)
        self.assertIn("playwright-visible-ui", core)
        self.assertIn("비공개 API", collector)
        self.assertIn("data/keyword-autocomplete.json", pages)

    def test_seo_proposes_four_review_gated_faqs_without_retired_rich_result(self):
        seo = self.read("seo-audit.html")
        self.assertIn("function faqCandidates", seo)
        self.assertIn("고객 질문형 FAQ 콘텐츠 4개", seo)
        self.assertNotIn('"@type":"FAQPage"', seo)
        self.assertNotIn("검색 데이터가 찾은 다음 FAQ 후보", seo)
        self.assertNotIn("Google FAQ 리치결과", seo)
        self.assertNotIn("월 이름을 억지로 넣지 않고", seo)
        self.assertNotIn("월 시즌 근거 보기", seo)
        self.assertNotIn("ModooPlanning", seo)
        self.assertNotIn("`${month}월 ${current.tag} 시기에", seo)
        self.assertNotIn("`${next}월을 앞두고", seo)
        self.assertIn("유병자보험은 일반건강보험보다 보험료가 비싼가요?", seo)
        self.assertIn("예전에 치료받은 병력이 있어도 가입할 수 있나요?", seo)
        self.assertIn("유병자보험은 무심사보험인가요?", seo)
        self.assertIn("건강이 좋아지면 일반심사형 보험으로 바꿀 수 있나요?", seo)
        self.assertNotIn("답변은 최신 상품 자료와 약관을 확인한 뒤 사용하세요", seo)
        self.assertNotIn("FAQ_EDITORIAL_GUIDE", seo)
        self.assertNotIn("FAQ_REFERENCE_URL", seo)
        self.assertNotIn("캐롯 블로그 표현 참고 기준", seo)


if __name__ == "__main__":
    unittest.main()
