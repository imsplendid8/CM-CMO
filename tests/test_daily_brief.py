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

    def test_unchanged_season_tasks_rotate_instead_of_all_repeating_daily(self):
        products = {
            "hrmf": {"name": "주택화재보험"}, "driver": {"name": "운전자보험"},
            "golf": {"name": "골프보험"}, "overseas": {"name": "여행보험"},
        }
        seasonal = {
            "hrmf": [{"tag": "장마", "m": [8]}],
            "driver": [{"tag": "휴가철", "m": [8]}],
        }
        day1 = db.compute_action_lines(products, ["hrmf", "driver"], seasonal, {}, datetime(2026, 8, 21, tzinfo=timezone.utc))
        day2 = db.compute_action_lines(products, ["hrmf", "driver"], seasonal, {}, datetime(2026, 8, 22, tzinfo=timezone.utc))
        season1 = [line for line in day1 if "이번 달" in line]
        season2 = [line for line in day2 if "이번 달" in line]
        self.assertEqual(len(season1), 1)
        self.assertEqual(len(season2), 1)
        self.assertNotEqual(season1, season2)


class TestHumanizedNews(unittest.TestCase):
    def test_shared_digest_humanizes_news_for_all_channels(self):
        clip = {"categories": {"driver": {"name": "운전자보험", "items": [{
            "t": "운전자보험 할인 이벤트 출시", "src": "example.com", "date": "2026-08-21",
            "url": "https://example.com/news", "gist": "작성되어진 설명을 자연스럽게 고치고 가입 조건과 제외 조건을 함께 안내합니다."
        }]}}}
        digest = db.content_brief.build_digest(clip, {"driver": {"name": "운전자보험"}}, ["driver"])
        self.assertEqual(len(digest["stories"]), 1)
        self.assertIn("작성된 설명", digest["stories"][0]["what"])
        self.assertNotIn("작성되어진", digest["stories"][0]["what"])


class TestChannelRendering(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 8, 24, 8, 0, tzinfo=timezone.utc)
        self.products = {
            "hrmf": {"name": "주택화재보험"},
            "golf": {"name": "골프보험"},
            "driver": {"name": "운전자보험"},
            "overseas": {"name": "해외여행보험"},
        }
        self.context = (self.products, list(self.products), ["hrmf"], {}, {}, {"date": "2026-08-24"}, self.now)
        self.digest = {
            "categories": {
                "hrmf": {
                    "summary": "긴 뉴스 요약도 모바일 화면 폭에 맞춰 자연스럽게 줄바꿈되어야 합니다.",
                    "insight": "이 문장은 알림 채널에 노출하지 않습니다.",
                }
            },
            "stories": [{
                "tag": "경쟁사·현대해상",
                "title": "아주 긴 뉴스 제목도 한 줄 폭을 넘기지 않고 표시",
                "what": "뉴스의 핵심 내용만 짧고 자연스러운 한 문단으로 전달합니다.",
                "why": "왜 중요한지 설명하는 별도 판단 문구",
                "action": "오늘 바로 실행하라는 별도 대응 문구",
                "source": "example.com",
                "date": "2026-08-24",
                "url": "https://example.com/news?x=1&y=2",
            }],
        }

    def patches(self):
        return (
            mock.patch.object(db, "_load_context", return_value=self.context),
            mock.patch.object(db, "shared_digest", return_value=self.digest),
            mock.patch.object(db.cah, "compute_health", return_value={}),
            mock.patch.object(db.cah, "format_lines", return_value=["[데이터 상태]", "· 정상"]),
        )

    def test_telegram_news_uses_summary_only(self):
        p1, p2, p3, p4 = self.patches()
        with p1, p2, p3, p4:
            message = db.build_message()

        self.assertIn("뉴스의 핵심 내용만", message)
        self.assertIn("example.com · 2026-08-24", message)
        self.assertIn("원문</a>", message)
        self.assertNotIn("무슨 일", message)
        self.assertNotIn("왜 중요", message)
        self.assertNotIn("오늘 대응", message)
        self.assertNotIn("별도 판단 문구", message)

    def test_email_is_single_column_wrapping_summary(self):
        p1, p2, p3, p4 = self.patches()
        with p1, p2, p3, p4:
            _, email_html, plain = db.render_email()

        self.assertIn('charset="utf-8"', email_html)
        self.assertIn('name="viewport"', email_html)
        self.assertIn("table-layout:fixed", email_html)
        self.assertIn("overflow-wrap:anywhere", email_html)
        self.assertIn("width:100%;box-sizing:border-box", email_html)
        self.assertNotIn("white-space:nowrap", email_html)
        self.assertNotIn("<th", email_html)
        self.assertNotIn("왜 중요", email_html + plain)
        self.assertNotIn("권장 대응", email_html + plain)
        self.assertNotIn("별도 대응 문구", email_html + plain)
        self.assertNotIn("핵심 동향", email_html + plain)
        self.assertIn("뉴스의 핵심 내용만", email_html)
        self.assertIn("뉴스의 핵심 내용만", plain)
        self.assertIn("https://example.com/news?x=1&amp;y=2", email_html)


if __name__ == "__main__":
    unittest.main(verbosity=2)
