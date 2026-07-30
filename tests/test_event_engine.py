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


class TestReviewFixes(unittest.TestCase):
    """Codex PR#3 P2 3건 회귀."""
    def test_emerging_valid_from_is_today_not_future(self):
        # 리드기간(emerging) 추천은 지금 노출돼야 → valid_from == 오늘
        cal = [{"id": "e1", "type": "명절", "name": "추석", "start": "2026-08-10",
                "end": "2026-08-13", "products": ["driver"], "keywords": ["추석"]}]
        r = ee.run(bundle(calendar=cal), TODAY)["recommendations"]
        em = [x for x in r if x["event_id"] == "e1"]
        self.assertTrue(em)
        self.assertEqual(em[0]["event_state"], "emerging")
        self.assertEqual(em[0]["valid_from"], TODAY.isoformat())      # 미래 시작일 아님
        self.assertGreaterEqual(em[0]["valid_to"], em[0]["valid_from"])

    def test_follow_up_window_not_inverted(self):
        # follow_up 은 end+TAIL 이후 시작 → valid_to 가 follow_up_days 만큼 연장돼 역전되지 않음
        start, end = TODAY - timedelta(days=20), TODAY - timedelta(days=12)  # end+7=TODAY-5 < today
        cal = [{"id": "fu", "type": "명절", "name": "지난 연휴", "start": start.isoformat(),
                "end": end.isoformat(), "products": ["driver"], "keywords": ["연휴사고"],
                "follow_up_days": 20}]
        cd = clip("연휴사고 관련 최근 뉴스")  # today 근처 날짜(2026-07-29) → 최근 evidence
        out = ee.run(bundle(calendar=cal, clip_data=cd), TODAY)
        fu = [x for x in out["recommendations"] if x["event_id"] == "fu"]
        if fu:  # follow_up 로 승격됐다면 창이 유효해야
            self.assertEqual(fu[0]["event_state"], "follow_up")
            self.assertLessEqual(fu[0]["valid_from"], fu[0]["valid_to"])

    def test_follow_up_ignores_stale_article(self):
        # 오래된 기사만 있으면 follow_up 승격 안 됨(ended)
        start, end = date(2026, 6, 1), date(2026, 6, 5)
        cal = [{"id": "old", "type": "명절", "name": "옛 연휴", "start": start.isoformat(),
                "end": end.isoformat(), "products": ["driver"], "keywords": ["옛연휴"],
                "follow_up_days": 60}]
        stale = {"categories": {"c": {"items": [
            {"t": "옛연휴 관련 오래된 뉴스", "src": "s", "date": "2026-06-02", "url": "u"}]}}}
        events = ee.build_events(bundle(calendar=cal, clip_data=stale), TODAY)
        st = {e["id"]: e["state"] for e in events}
        self.assertEqual(st["old"], "ended")   # 오래된 기사로 follow_up 되지 않음

    def test_run_reports_unclassified_count(self):
        cd = clip("완전 무관한 지역 소식 하나", "또 다른 무관한 소식")
        out = ee.run(bundle(clip_data=cd), TODAY)
        self.assertEqual(out["counts"]["unclassified"], len(out["unclassified"]))
        self.assertGreater(out["counts"]["unclassified"], 0)


class TestRobustness(unittest.TestCase):
    """불완전·악의적 입력에 대한 방어(조용히 정상처리하지 않고 skip/미분류)."""
    def test_calendar_event_missing_name_does_not_crash(self):
        # name/type 이 없는 캘린더 행이 있어도 run() 이 예외 없이 동작
        cal = [{"id": "x"}, {"id": "y", "start": "2026-07-01", "end": "2026-08-30",
                             "products": ["hrmf"], "keywords": ["y"]}]
        out = ee.run(bundle(calendar=cal), TODAY)          # 예외가 나면 실패
        self.assertEqual(out["counts"]["events"], 2)
        self.assertEqual(out["counts"]["unclassified"], len(out["unclassified"]))

    def test_empty_keyword_does_not_swallow_review_queue(self):
        # 이벤트 키워드에 빈 문자열이 섞여도 무관 뉴스는 미분류 큐로 가야 함
        cal = [{"id": "e", "type": "휴가", "name": "E", "start": "2026-07-01",
                "end": "2026-08-30", "products": ["hrmf"], "keywords": [""]}]
        cd = clip("아무 상품과도 무관한 지역 소식")
        out = ee.run(bundle(calendar=cal, clip_data=cd), TODAY)
        self.assertIn("아무 상품과도 무관한 지역 소식",
                      [u["title"] for u in out["unclassified"]])

    def test_empty_keyword_no_spurious_follow_up(self):
        # 빈 키워드가 모든 기사를 최근 뉴스로 오인해 follow_up 시키지 않음
        start, end = date(2026, 6, 1), date(2026, 6, 5)
        cal = [{"id": "z", "type": "명절", "name": "Z", "start": start.isoformat(),
                "end": end.isoformat(), "products": ["driver"], "keywords": [""],
                "follow_up_days": 90}]
        cd = clip("전혀 무관한 뉴스")
        events = ee.build_events(bundle(calendar=cal, clip_data=cd), TODAY)
        self.assertEqual({e["id"]: e["state"] for e in events}["z"], "ended")

    def test_expanded_guardrail_blocks_absolute_claims(self):
        # 과장·단정 표현이 이벤트명에 있으면 추천을 만들지 않음
        for bad_name in ("무조건 보장 이벤트", "업계 최고 캠페인", "100% 환급 행사"):
            cal = [{"id": "g", "type": "캠페인일", "name": bad_name, "start": "2026-07-20",
                    "end": "2026-08-20", "products": ["hrmf"], "keywords": ["g"]}]
            r = ee.run(bundle(calendar=cal), TODAY)["recommendations"]
            self.assertFalse([x for x in r if x["event_id"] == "g"], bad_name)


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
