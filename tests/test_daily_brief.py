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

        self.assertGreaterEqual(len(lines), 1)


class TestHumanizedNews(unittest.TestCase):
    def test_telegram_gist_uses_word_boundary_excerpt(self):
        clip = {"categories": {"driver": {"name": "운전자보험", "items": [{
            "t": "운전자보험 할인 이벤트 출시", "src": "example.com", "date": "2026-08-21",
            "url": "https://example.com/news", "gist": "작성되어진 설명을 자연스럽게 고치고 가입 조건과 제외 조건을 함께 안내합니다."
        }]}}}
        lines = db.pick_news(clip, {"driver": {"name": "운전자보험"}})
        self.assertEqual(len(lines), 1)
        self.assertIn("작성된 설명", lines[0])
        self.assertNotIn("작성되어진", lines[0])


if __name__ == "__main__":
    unittest.main(verbosity=2)
