#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""담보명 뒤 '(특약)' 표기 · SA 42~45자 회귀 테스트."""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import coverage_terms as ct  # noqa: E402
import serp_copy_agent as agent  # noqa: E402


class TestRiderMarks(unittest.TestCase):
    def test_each_coverage_name_needs_mark_right_after(self):
        self.assertEqual(ct.missing_rider_marks("벌금(특약)·변호사선임비용(특약)까지 대비해요", "driver"), [])
        self.assertEqual(ct.missing_rider_marks("벌금·변호사선임비용까지 대비해요(특약)", "driver"), ["변호사선임비용", "벌금"])

    def test_longest_name_first_and_product_names_skipped(self):
        # '급발진 변호사선임비용' 안의 '변호사선임비용'은 한 번만 본다 · 상품명 '행사배상책임보험'은 담보명이 아니다
        self.assertEqual(ct.missing_rider_marks("일상배상책임(특약)으로 대비해요", "hrmf"), [])
        self.assertEqual(ct.missing_rider_marks("행사배상책임보험 보험료를 계산해요", "event"), [])

    def test_mark_riders_inserts_suffix(self):
        self.assertEqual(ct.mark_riders("풍수재와 임시거주비 보장", "hrmf"), "풍수재(특약)와 임시거주비(특약) 보장")
        self.assertEqual(ct.mark_riders("풍수재(특약) 보장", "hrmf"), "풍수재(특약) 보장")


class TestGeneratedSaLength(unittest.TestCase):
    def test_fallback_templates_fill_42_to_45_with_marks(self):
        product = {"key": "hrmf", "name": "주택화재보험", "serpKw": "주택화재보험"}
        for axis in ("search_action", "decision_detail", "scope_compare", "terms_navigation", "official_path", "serp_whitespace", "seasonal_scene"):
            row = agent._copy_for_axis(axis, product, "주택화재보험", "풍수재", "임시거주비", {"name": "장마"})
            for field in ("description", "additional_description"):
                text = row[field]
                self.assertTrue(42 <= len(text) <= 45, f"{axis} {field} {len(text)}자: {text}")
                self.assertEqual(ct.missing_rider_marks(text, "hrmf"), [], text)
                self.assertTrue(text.endswith("요"), f"문장이 잘림: {text}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
