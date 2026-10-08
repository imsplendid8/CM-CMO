#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""워커 /health 판정 — 누락 설정·정시 호출 실패를 사람이 읽을 문제로 바꾸는지."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
import check_worker_health as cwh  # noqa: E402


class TestWorkerHealth(unittest.TestCase):
    def test_healthy(self):
        h = {"ok": True, "missing": [], "scheduler": {"slot": "23:00", "results": [{"workflow": "daily-brief.yml", "status": 204, "ok": True}]}}
        self.assertEqual(cwh.problems(h), [])

    def test_missing_and_expired_token(self):
        h = {"missing": ["GH_DISPATCH_TOKEN"], "scheduler": {"slot": "22:20", "results": [{"workflow": "news-clip.yml", "status": 401, "ok": False}]}}
        out = cwh.problems(h)
        self.assertEqual(len(out), 2)
        self.assertIn("GH_DISPATCH_TOKEN", out[0])
        self.assertIn("토큰 만료", out[1])

    def test_outdated_worker_code(self):
        self.assertIn("최신이 아님", cwh.problems({"ok": True, "service": "modooflow-naver-proxy"})[0])

    def test_unreadable(self):
        self.assertTrue(cwh.problems(None))


class TestLateNotice(unittest.TestCase):
    def test_only_on_fallback(self):
        import datetime
        from unittest.mock import patch
        import daily_brief
        now = datetime.datetime(2026, 10, 9, 10, 40)
        with patch.dict(os.environ, {"BRIEF_TRIGGER": ""}):
            self.assertEqual(daily_brief.late_notice(now), "")
        with patch.dict(os.environ, {"BRIEF_TRIGGER": "fallback"}):
            self.assertIn("10:40", daily_brief.late_notice(now))


if __name__ == "__main__":
    unittest.main()
