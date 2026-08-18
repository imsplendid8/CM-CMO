#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""긴급 화재 감시의 시간·사건성 필터 회귀 테스트."""
import os
import sys
import unittest
from datetime import datetime, timedelta, timezone

SCRIPTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts")
sys.path.insert(0, SCRIPTS)
import fire_watch as fw  # noqa: E402


class TestFireWatchDetection(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 8, 19, 1, 0, tzinfo=timezone(timedelta(hours=9)))

    def item(self, title, gist="", dt=None):
        return {"t": title, "gist": gist, "dt": dt, "url": title, "src": "example.com"}

    def test_accepts_recent_incident(self):
        items = [
            self.item("평택 물류창고 화재 21시간 만에 진화", "소방당국 조사 중",
                      self.now - timedelta(hours=1)),
            self.item("인천 공장에서 불이 나 2명 부상", "공장 화재로 소방당국이 진화",
                      self.now - timedelta(minutes=20)),
        ]
        self.assertEqual(len(fw.detect(items, self.now, 4)), 2)

    def test_rejects_retrospective_and_cultural_mentions(self):
        items = [
            self.item("산불 전소 교회 재건", "지난해 산불로 전소됐던 교회 재건",
                      self.now - timedelta(minutes=30)),
            self.item("대형 화재 다룬 소설 북토크", "작품 속 화재에서 살아남은 청소년",
                      self.now - timedelta(minutes=20)),
        ]
        self.assertEqual(fw.detect(items, self.now, 4), [])

    def test_rejects_missing_or_stale_timestamp(self):
        items = [
            self.item("아파트 화재로 주민 대피", dt=None),
            self.item("공장 화재 진화", dt=self.now - timedelta(hours=5)),
        ]
        self.assertEqual(fw.detect(items, self.now, 4), [])

    def test_requires_incident_in_title_not_only_description(self):
        items = [self.item("울산 산림 정책토론회 개최", "산불 피해와 진화 정책 논의",
                           self.now - timedelta(minutes=10))]
        self.assertEqual(fw.detect(items, self.now, 4), [])

    def test_deduplicates_different_headlines_for_same_event(self):
        items = [
            self.item("평택 위험물 창고 화재원인, 화학반응에 무게", "21시간 만에 진화",
                      self.now - timedelta(minutes=30)),
            self.item("수시간 연기 뒤 발화…평택 위험물창고 화재 화학반응 추정", "소방당국 조사",
                      self.now - timedelta(minutes=20)),
        ]
        hits = fw.detect(items, self.now, 4)
        self.assertEqual(len(hits), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
