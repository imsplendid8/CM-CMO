#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import sys
import unittest

SCRIPTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts")
sys.path.insert(0, SCRIPTS)
import humanize_korean as hk  # noqa: E402


class TestHumanizeKorean(unittest.TestCase):
    def test_fixes_double_passive_without_changing_facts(self):
        src = "2026년 8월 분석 결과는 37건의 자료에서 도출되어진 것으로 확인됐다."
        out = hk.humanize(src)
        self.assertIn("도출된", out)
        self.assertIn("2026년", out)
        self.assertIn("37건", out)

    def test_preserves_quotes_acronyms_and_numbers(self):
        src = 'API 분석은 “보험료 7% 할인” 문구를 그대로 유지하고, 작성되어진 설명만 고친다.'
        out = hk.humanize(src)
        self.assertIn('API', out)
        self.assertIn('“보험료 7% 할인”', out)
        self.assertIn("작성된", out)

    def test_change_gate_rolls_back_aggressive_edit(self):
        src = "생성되어진 결과"
        self.assertEqual(hk.humanize(src, max_change=0.01), src)

    def test_excerpt_prefers_word_boundary(self):
        out = hk.excerpt("운전자보험 보장 내용을 확인하고 가입 조건과 제외 조건을 함께 살펴보세요.", 24)
        self.assertTrue(out.endswith("…"))
        self.assertLessEqual(len(out), 25)
        self.assertTrue(out[:-1].endswith(("확인하고", "조건과", "조건을", "함께")))

    def test_already_truncated_clip_keeps_last_complete_sentence(self):
        src = "지난해 순위 경쟁이 치열했고 보험사별 실적 차이도 컸다. 대형 사고가 이어지면서 일부 회사는 예상보다 큰 손실을"
        self.assertEqual(hk.excerpt(src, 88), "지난해 순위 경쟁이 치열했고 보험사별 실적 차이도 컸다.")

    def test_excerpt_does_not_show_dangling_number(self):
        src = "보험사 3곳이 지급한 보험금은 시공비 1"
        self.assertNotIn(" 1…", hk.excerpt(src, 20))


if __name__ == "__main__":
    unittest.main(verbosity=2)
