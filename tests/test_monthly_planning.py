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
        self.assertIn("다른 달의 ‘신년’ 같은 문구가 섞이지 않습니다", adcopy)

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

    def test_seo_proposes_four_review_gated_faqs(self):
        seo = self.read("seo-audit.html")
        self.assertIn("function monthlyFaqs", seo)
        self.assertIn("FAQ 제안 4개", seo)
        self.assertIn('"@type":"FAQPage"', seo)
        self.assertIn("1~3번은 매월 교체, 4번은 상시 유지", seo)
        self.assertIn("상품 담당자·준법·광고심의 검토 후 사용", seo)
        self.assertIn('FAQ_REFERENCE_URL="https://blog.carrotins.com/"', seo)
        self.assertIn("실제 이용자의 상황을 질문으로 쓰고", seo)
        self.assertIn("심의번호·심의 유효기간·검토자를 기록", seo)
        self.assertIn("캐롯 문구나 심의번호를 그대로 재사용하지 않습니다", seo)


if __name__ == "__main__":
    unittest.main()

