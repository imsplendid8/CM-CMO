#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SERP 관측 소재 분석 회귀 테스트. 표준 라이브러리 unittest + fixture 주입."""
import json
import os
import sys
import unittest

SCRIPTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts")
sys.path.insert(0, SCRIPTS)
import serp_analysis as sa  # noqa: E402

ROOT = os.path.dirname(SCRIPTS)

OBS = [
    {"product": "driver", "brand": "현대해상", "keyword": "운전자보험", "date": "2026-07-26", "rank": 1,
     "title": "현대 운전자보험", "desc": "관측 설명", "covers": ["형사합의금", "변호사선임", "벌금"],
     "promo": "7% 할인", "cta": "가입", "price": "7% 할인"},
    {"product": "driver", "brand": "DB손보", "covers": ["형사합의금", "변호사선임", "벌금"],
     "promo": "10년 1위", "cta": "비교", "price": ""},
    {"product": "hrmf", "brand": "메리츠", "covers": ["누수", "풍수재"], "promo": "맞춤", "cta": "견적"},
]


class TestAnalyze(unittest.TestCase):
    def test_counts_and_brands(self):
        a = sa.analyze(OBS)
        self.assertEqual(a["driver"]["n"], 2)
        self.assertEqual(a["driver"]["brands"], ["DB손보", "현대해상"])
        self.assertEqual(a["hrmf"]["n"], 1)

    def test_common_soju_needs_two_brands(self):
        a = sa.analyze(OBS)
        # 형사합의금·변호사선임·벌금은 두 브랜드 공통 → common_soju
        self.assertEqual(a["driver"]["common_soju"], ["벌금", "변호사선임", "형사합의금"])
        # hrmf 소구는 한 브랜드뿐 → 공통 없음
        self.assertEqual(a["hrmf"]["common_soju"], [])

    def test_soju_ranked_desc_then_lexical(self):
        a = sa.analyze(OBS)
        soju = a["driver"]["soju"]
        counts = [n for _, n in soju]
        self.assertEqual(counts, sorted(counts, reverse=True))       # 내림차순
        self.assertEqual(soju[0][1], 2)                              # 형사합의금 등 2회

    def test_deterministic(self):
        self.assertEqual(json.dumps(sa.analyze(OBS), ensure_ascii=False, sort_keys=True),
                         json.dumps(sa.analyze(OBS), ensure_ascii=False, sort_keys=True))

    def test_promos_and_cta_and_prices(self):
        a = sa.analyze(OBS)["driver"]
        self.assertIn(["7% 할인", 1], a["promos"])
        self.assertIn(["가입", 1], a["cta"])
        self.assertIn("7% 할인", a["prices"])

    def test_preserves_dated_public_ad_evidence(self):
        a = sa.analyze(OBS)["driver"]
        self.assertEqual(a["latest_date"], "2026-07-26")
        self.assertEqual(a["observed_ads"][0]["keyword"], "운전자보험")
        self.assertEqual(a["observed_ads"][0]["title"], "현대 운전자보험")

    def test_structured_text_observation_fields(self):
        a = sa.analyze(OBS)["driver"]
        ad = a["observed_ads"][0]
        self.assertIn("source_observation_id", ad)
        self.assertIn("description", ad)
        self.assertIn("extensions", ad)
        self.assertIn("detected_angles", ad)
        self.assertIn("cta_terms", ad)
        self.assertIn("risk_flags", ad)
        self.assertIn("landing", ad)
        self.assertIn("price", ad)
        self.assertIn("monthly_diff", a)

    def test_empty_safe(self):
        self.assertEqual(sa.analyze([]), {})
        self.assertEqual(sa.analyze(None), {})


class TestWindow(unittest.TestCase):
    def test_old_observations_excluded(self):
        obs = [
            {"product": "driver", "brand": "A", "covers": ["형사합의금"], "date": "2026-07-26"},
            {"product": "driver", "brand": "B", "covers": ["형사합의금"], "date": "2026-01-01"},  # 창 밖
        ]
        # 최신(07-26) 기준 35일 창 → 01-01 제외 → 공통소구 아님(한 브랜드만)
        a = sa.analyze(obs, window_days=35)
        self.assertEqual(a["driver"]["n"], 1)
        self.assertEqual(a["driver"]["common_soju"], [])

    def test_window_included_when_recent(self):
        obs = [
            {"product": "driver", "brand": "A", "covers": ["형사합의금"], "date": "2026-07-26"},
            {"product": "driver", "brand": "B", "covers": ["형사합의금"], "date": "2026-07-10"},  # 창 안
        ]
        a = sa.analyze(obs, window_days=35)
        self.assertEqual(a["driver"]["n"], 2)
        self.assertEqual(a["driver"]["common_soju"], ["형사합의금"])


class TestRealData(unittest.TestCase):
    def test_repo_observations_analyze(self):
        data = sa.load(ROOT)
        res = sa.analyze(data.get("observations", []))
        self.assertTrue(res)                       # 상품별 결과 존재
        for pk, v in res.items():
            self.assertIn("common_soju", v)
            self.assertIsInstance(v["soju"], list)
            self.assertIn("monthly_diff", v)

    def test_committed_analysis_is_current(self):
        # ad_observations.json 변경 후 재생성을 강제 — 커밋된 산출물이 build()와 일치해야 함
        with open(os.path.join(ROOT, "serp", "ad_analysis.json"), encoding="utf-8") as f:
            committed = json.load(f)
        built = sa.build(ROOT)
        self.assertEqual(json.dumps(built, ensure_ascii=False, sort_keys=True),
                         json.dumps(committed, ensure_ascii=False, sort_keys=True),
                         "serp/ad_analysis.json 이 최신이 아님 — `python3 scripts/serp_analysis.py` 재실행 필요")
        self.assertEqual(built["schema_version"], 3)
        for pk, row in built["products"].items():
            self.assertIn("autocomplete", row)
            self.assertIn("dom", row)


if __name__ == "__main__":
    unittest.main(verbosity=2)
