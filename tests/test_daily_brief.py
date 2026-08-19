#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""데일리 브리핑 수신자 파싱 회귀 테스트(표준 unittest).

recipients() = TELEGRAM_CHAT_IDS(콤마/줄바꿈/세미콜론 다중) 우선, 없으면 TELEGRAM_CHAT_ID(단일).
chat_id 는 개인 식별자라 저장소에 커밋하지 않고 Secrets 로만 주입 — 여기선 env 를 주입해 파싱만 검증.
"""
import os
import sys
import unittest
from datetime import datetime, timezone
from unittest import mock

SCRIPTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts")
sys.path.insert(0, SCRIPTS)
import daily_brief as db  # noqa: E402


def recip(**env):
    """지정한 텔레그램 env 만 두고(나머지 제거) recipients() 호출."""
    clean = {k: v for k, v in os.environ.items()
             if k not in ("TELEGRAM_CHAT_IDS", "TELEGRAM_CHAT_ID")}
    clean.update(env)
    with mock.patch.dict(os.environ, clean, clear=True):
        return db.recipients()


class TestRecipients(unittest.TestCase):
    def test_comma_separated(self):
        self.assertEqual(recip(TELEGRAM_CHAT_IDS="1,2,3"), ["1", "2", "3"])

    def test_newline_and_semicolon(self):
        self.assertEqual(recip(TELEGRAM_CHAT_IDS="1\n2;3"), ["1", "2", "3"])

    def test_trims_whitespace(self):
        self.assertEqual(recip(TELEGRAM_CHAT_IDS=" 1 , 2 ,\t3 "), ["1", "2", "3"])

    def test_dedup_preserves_order(self):
        self.assertEqual(recip(TELEGRAM_CHAT_IDS="2,1,2,1,3"), ["2", "1", "3"])

    def test_skips_empty_tokens(self):
        self.assertEqual(recip(TELEGRAM_CHAT_IDS="1,,2,;,3,"), ["1", "2", "3"])

    def test_falls_back_to_single_chat_id(self):
        self.assertEqual(recip(TELEGRAM_CHAT_ID="99"), ["99"])

    def test_ids_take_precedence_over_single(self):
        self.assertEqual(recip(TELEGRAM_CHAT_IDS="1,2", TELEGRAM_CHAT_ID="99"), ["1", "2"])

    def test_empty_when_unset(self):
        self.assertEqual(recip(), [])

    def test_blank_value_is_empty(self):
        self.assertEqual(recip(TELEGRAM_CHAT_IDS="   ,  ; \n "), [])

    def test_negative_group_ids_kept(self):
        # 텔레그램 그룹 chat_id 는 음수 — 문자열 그대로 보존(형식 강제 안 함)
        self.assertEqual(recip(TELEGRAM_CHAT_IDS="-1001234567890,777"),
                         ["-1001234567890", "777"])


class TestActionLines(unittest.TestCase):
    PRODUCTS = {
        "hrmf": {"name": "주택화재보험"},
        "golf": {"name": "골프보험"},
        "driver": {"name": "운전자보험"},
        "overseas": {"name": "해외여행보험"},
    }

    def test_weather_active_accepts_string_and_object_entries(self):
        products = {"hrmf": {"name": "주택화재보험"}, "driver": {"name": "운전자보험"}}
        signals = {"weather": {"active": ["폭염", {"note": "호우 특보"}]}}

        lines = db.compute_action_lines(
            products, ["hrmf"], {}, signals,
            datetime(2026, 8, 18, tzinfo=timezone.utc),
        )

        self.assertTrue(any("폭염" in line or "호우 특보" in line for line in lines))

    def test_malformed_trigger_and_weather_shapes_do_not_abort_brief(self):
        lines = db.compute_action_lines(
            {"hrmf": {"name": "주택화재보험"}, "overseas": {"name": "해외여행보험"}},
            ["hrmf"], {}, {"triggers": ["급등"], "weather": "오류"},
            datetime(2026, 8, 18, tzinfo=timezone.utc),
        )

        self.assertEqual(lines, [])

    def test_afternoon_omits_unchanged_planning_actions(self):
        lines = db.compute_action_lines(
            self.PRODUCTS, ["hrmf"],
            {"hrmf": [{"m": [8], "tag": "여름 위험"}]},
            {"triggers": {"overseas": {"level": "high"}}},
            datetime(2026, 8, 18, 14, tzinfo=timezone.utc),
        )

        self.assertEqual(lines, [])

    def test_afternoon_message_labels_repeat_suppression(self):
        afternoon = datetime(2026, 8, 18, 14, tzinfo=timezone.utc)
        context = (
            self.PRODUCTS, list(self.PRODUCTS), ["hrmf"], {},
            {"triggers": {"overseas": {"level": "high"}}}, None, afternoon,
        )
        with mock.patch.object(db, "_load_context", return_value=context), \
                mock.patch.object(db.cah, "compute_health", side_effect=RuntimeError):
            message = db.build_message()

        self.assertIn("오후 업데이트", message)
        self.assertIn("오전 계획 반복 생략", message)
        self.assertNotIn("오늘 할 일 (우선순위)", message)

    def test_demand_action_requests_review_instead_of_forced_bid_raise(self):
        lines = db.compute_action_lines(
            self.PRODUCTS, ["hrmf"], {},
            {"triggers": {"overseas": {"level": "high"}}},
            datetime(2026, 8, 18, 8, tzinfo=timezone.utc),
        )

        self.assertTrue(any("입찰 조정 검토" in line for line in lines))
        self.assertFalse(any("입찰 강화" in line for line in lines))

    def test_medium_signal_is_limited_to_monday_and_thursday(self):
        signals = {"triggers": {"overseas": {"level": "medium"}}}
        monday = db.compute_action_lines(
            self.PRODUCTS, [], {}, signals,
            datetime(2026, 8, 17, 8, tzinfo=timezone.utc),
        )
        tuesday = db.compute_action_lines(
            self.PRODUCTS, [], {}, signals,
            datetime(2026, 8, 18, 8, tzinfo=timezone.utc),
        )

        self.assertTrue(any("검색수요 상승" in line for line in monday))
        self.assertFalse(any("검색수요 상승" in line for line in tuesday))

    def test_seasonal_and_serp_routines_run_weekly(self):
        seasonal = {"hrmf": [{"m": [8], "tag": "여름 위험"}]}
        monday = db.compute_action_lines(
            self.PRODUCTS, ["hrmf"], seasonal, {},
            datetime(2026, 8, 17, 8, tzinfo=timezone.utc),
        )
        tuesday = db.compute_action_lines(
            self.PRODUCTS, ["hrmf"], seasonal, {},
            datetime(2026, 8, 18, 8, tzinfo=timezone.utc),
        )

        self.assertTrue(any("여름 위험" in line for line in monday))
        self.assertTrue(any("주간 SERP 점검" in line for line in monday))
        self.assertEqual(tuesday, [])

    def test_next_month_prep_runs_only_on_twentieth(self):
        seasonal = {"hrmf": [{"m": [9], "tag": "가을 준비"}]}
        before = db.compute_action_lines(
            self.PRODUCTS, ["hrmf"], seasonal, {},
            datetime(2026, 8, 19, 8, tzinfo=timezone.utc),
        )
        due = db.compute_action_lines(
            self.PRODUCTS, ["hrmf"], seasonal, {},
            datetime(2026, 8, 20, 8, tzinfo=timezone.utc),
        )

        self.assertFalse(any("가을 준비" in line for line in before))
        self.assertTrue(any("가을 준비" in line for line in due))

    def test_span_boundary_surfaces_outside_weekly_cadence(self):
        seasonal = {
            "hrmf": [{"m": [8], "tag": "호우 기간", "span": [["08-18", "08-25"]]}]
        }
        lines = db.compute_action_lines(
            self.PRODUCTS, ["hrmf"], seasonal, {},
            datetime(2026, 8, 18, 8, tzinfo=timezone.utc),
        )

        self.assertTrue(any("호우 기간" in line for line in lines))


if __name__ == "__main__":
    unittest.main(verbosity=2)
