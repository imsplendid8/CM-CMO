#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""이벤트 추천 엔진 회귀 테스트 (P0-EVENT). 표준 라이브러리 unittest + fixture(dict 주입)."""
import os
import sys
import unittest
from datetime import date, timedelta

SCRIPTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts")
sys.path.insert(0, SCRIPTS)
import event_engine as ee  # noqa: E402

TODAY = date(2026, 7, 30)

REQUIRED = {"fingerprint", "fact", "product", "event_state", "title", "description",
            "content_subhead", "reason", "data_used", "valid_from", "valid_to",
            "avoid_phrases", "channels", "product_basis", "review_status", "confidence"}


def clip(*titles):
    return {"categories": {"c": {"items": [
        {"t": t, "src": "src", "date": "2026-07-29", "url": f"http://x/{i}"}
        for i, t in enumerate(titles)]}}}


def bundle(calendar=None, seasonal=None, signals=None, clip_data=None, volume=None, history=None):
    return {
        "products": {"hrmf": {"key": "hrmf", "name": "주택화재보험", "newsQuery": "주택화재보험",
                              "newsExtra": ["대형화재사고"]},
                     "driver": {"key": "driver", "name": "운전자보험", "newsQuery": "운전자보험"},
                     "cncr": {"key": "cncr", "name": "암보험", "newsQuery": "암보험"},
                     "overseas": {"key": "overseas", "name": "해외여행보험", "newsQuery": "해외여행보험"}},
        "main": ["driver", "hrmf"],
        "calendar": calendar or [], "seasonal": seasonal or {},
        "signals": signals or {"asof": "2026-07-30", "weather": {"active": []}},
        "clip": clip_data, "volume": volume or {}, "history": history or [],
    }


class TestState(unittest.TestCase):
    def test_date_states_all_six(self):
        s, e = date(2026, 9, 1), date(2026, 9, 5)
        self.assertEqual(ee.state_from_dates(date(2026, 7, 1), s, e), "upcoming")
        self.assertEqual(ee.state_from_dates(date(2026, 8, 25), s, e), "emerging")
        self.assertEqual(ee.state_from_dates(date(2026, 9, 3), s, e), "active")
        self.assertEqual(ee.state_from_dates(date(2026, 9, 9), s, e), "cooling")
        self.assertEqual(ee.state_from_dates(date(2026, 10, 1), s, e), "ended")
        self.assertEqual(ee.state_from_dates(date(2026, 9, 15), s, e, follow_up_days=14, ongoing=True),
                         "follow_up")

    def test_month_states(self):
        self.assertEqual(ee.state_from_months(date(2026, 7, 15), [6, 7, 8]), "active")
        self.assertEqual(ee.state_from_months(date(2026, 5, 15), [6, 7, 8]), "emerging")
        self.assertEqual(ee.state_from_months(date(2026, 9, 15), [6, 7, 8]), "cooling")
        self.assertEqual(ee.state_from_months(date(2026, 1, 15), [6, 7, 8]), "ended")

    def test_state_changes_purpose_and_validity(self):
        # 상태가 바뀌면 목적과 유효기간이 달라진다
        cal_active = [{"id": "e1", "type": "휴가", "name": "여름 휴가철", "start": "2026-07-18",
                       "end": "2026-08-17", "products": ["overseas"], "keywords": ["휴가"]}]
        r_active = ee.run(bundle(calendar=cal_active), TODAY)["recommendations"]
        self.assertTrue(r_active)
        self.assertEqual(r_active[0]["purpose"], ee.PURPOSE_BY_STATE["active"])
        cal_up = [{"id": "e1", "type": "휴가", "name": "설 연휴", "start": "2026-12-30",
                   "end": "2027-01-02", "products": ["overseas"], "keywords": ["설"]}]
        r_up = ee.run(bundle(calendar=cal_up), TODAY)["recommendations"]
        # 먼 미래(upcoming)면 목적이 다르거나 추천이 억제될 수 있음
        if r_up:
            self.assertNotEqual(r_up[0]["purpose"], ee.PURPOSE_BY_STATE["active"])


class TestRecommendation(unittest.TestCase):
    def _one_active(self, extra_clip=None):
        cal = [{"id": "e1", "type": "휴가", "name": "여름 휴가철", "start": "2026-07-18",
                "end": "2026-08-17", "products": ["overseas"], "keywords": ["휴가", "여행"]}]
        return ee.run(bundle(calendar=cal, clip_data=extra_clip), TODAY)

    def test_required_fields_present(self):
        r = self._one_active()["recommendations"]
        self.assertTrue(r)
        for rec in r:
            self.assertTrue(REQUIRED.issubset(rec.keys()), REQUIRED - set(rec.keys()))

    def test_review_status_never_approved(self):
        out = self._one_active()
        for rec in out["recommendations"]:
            self.assertEqual(rec["product_basis"], "미확인")
            self.assertIn("심의 검토 전", rec["review_status"])
            self.assertNotIn("심의 통과", rec["review_status"])
            self.assertNotIn("등록 가능", rec["review_status"])

    def test_no_fear_pressure_guarantee_in_copy(self):
        out = self._one_active(clip(*ee.AVOID_ALL[:3]))  # 금지어가 뉴스에 있어도 문구엔 안 들어감
        for rec in out["recommendations"]:
            joined = rec["title"] + rec["description"] + rec["content_subhead"]
            self.assertEqual(ee.lint_avoid(joined), [])

    def test_guardrail_drops_copy_with_avoid_term(self):
        # 이벤트명에 공포 표현이 있으면 문구에 섞여 → 추천 자체를 만들지 않음
        cal = [{"id": "bad", "type": "긴급뉴스", "name": "끔찍한 참사", "start": "2026-07-18",
                "end": "2026-08-17", "products": ["hrmf"], "keywords": ["화재"]}]
        r = ee.run(bundle(calendar=cal), TODAY)["recommendations"]
        self.assertFalse([x for x in r if x["event_id"] == "bad"])

    def test_not_hardcoded_to_specific_events(self):
        # 장마·폭염이 아닌 새 이벤트+상품도 추천이 생성된다
        cal = [{"id": "novel", "type": "대회", "name": "신규 스포츠 대회", "start": "2026-07-20",
                "end": "2026-08-10", "products": ["cncr"], "keywords": ["신규대회"]}]
        r = ee.run(bundle(calendar=cal, volume={"cncr": {"keywords": {"암보험": {"pc": 100, "mobile": 200}}}}),
                   TODAY)["recommendations"]
        self.assertTrue([x for x in r if x["event_id"] == "novel" and x["product"] == "cncr"])


class TestFingerprintCooldown(unittest.TestCase):
    def test_fingerprint_same_for_ending_only_change(self):
        a = ee.fingerprint("hrmf", "e1", "시즌 대응", "여름 휴가철 주택화재보험 점검하세요",
                           "보장 범위를 확인해 두세요")
        b = ee.fingerprint("hrmf", "e1", "시즌 대응", "여름 휴가철 주택화재보험 점검합니다",
                           "보장 범위를 확인해 보세요")
        self.assertEqual(a, b)  # 어미만 다르면 같은 fingerprint

    def test_fingerprint_differs_by_product(self):
        a = ee.fingerprint("hrmf", "e1", "시즌 대응", "여름 휴가철 점검", "확인")
        b = ee.fingerprint("driver", "e1", "시즌 대응", "여름 휴가철 점검", "확인")
        self.assertNotEqual(a, b)

    def test_cooldown_suppresses(self):
        cal = [{"id": "e1", "type": "휴가", "name": "여름 휴가철", "start": "2026-07-18",
                "end": "2026-08-17", "products": ["overseas"], "keywords": ["휴가"]}]
        first = ee.run(bundle(calendar=cal), TODAY)["recommendations"]
        self.assertTrue(first)
        fp = first[0]["fingerprint"]
        hist = [{"fp": fp, "date": (TODAY - timedelta(days=3)).isoformat()}]
        out = ee.run(bundle(calendar=cal, history=hist), TODAY)
        self.assertNotIn(fp, {r["fingerprint"] for r in out["recommendations"]})
        self.assertGreaterEqual(out["counts"]["suppressed_cooldown"], 1)

    def test_cooldown_expired_not_suppressed(self):
        cal = [{"id": "e1", "type": "휴가", "name": "여름 휴가철", "start": "2026-07-18",
                "end": "2026-08-17", "products": ["overseas"], "keywords": ["휴가"]}]
        first = ee.run(bundle(calendar=cal), TODAY)["recommendations"][0]
        hist = [{"fp": first["fingerprint"], "date": (TODAY - timedelta(days=30)).isoformat()}]
        out = ee.run(bundle(calendar=cal, history=hist), TODAY)
        self.assertIn(first["fingerprint"], {r["fingerprint"] for r in out["recommendations"]})


class TestUnclassified(unittest.TestCase):
    def test_ambiguous_news_goes_to_queue_no_copy(self):
        cd = clip("아무 상품과도 무관한 지역 축구 소식", "주택화재보험 신상품 출시")
        out = ee.run(bundle(clip_data=cd), TODAY)
        titles = [u["title"] for u in out["unclassified"]]
        self.assertIn("아무 상품과도 무관한 지역 축구 소식", titles)   # 미분류 큐로
        # 매핑되는 뉴스는 미분류에 없음
        self.assertNotIn("주택화재보험 신상품 출시", titles)

    def test_unclassified_produces_no_recommendation(self):
        cd = clip("완전 무관한 뉴스 제목 하나")
        out = ee.run(bundle(clip_data=cd), TODAY)
        self.assertFalse(out["recommendations"])  # calendar/seasonal 없으면 추천 0


if __name__ == "__main__":
    unittest.main(verbosity=2)
