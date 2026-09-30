#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""파워콘텐츠 원고 재료 ↔ 도구 연결 계약 테스트."""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARTICLES = json.loads((ROOT / "data/adcopy/power-content-articles.json").read_text(encoding="utf-8"))
CONTEXT = json.loads((ROOT / "data/adcopy/material-source-context.json").read_text(encoding="utf-8"))
POWER = (ROOT / "powercontent-tool.html").read_text(encoding="utf-8")


class TestPowerContentArticles(unittest.TestCase):
    def test_main_products_have_article_for_every_planned_topic(self):
        # 메인 3종은 기획된 주제(power_content_blueprints)마다 사실 기반 원고 재료가 있어야 한다
        for key in ("driver", "hrmf", "golf"):
            planned = {b["target_query"] for b in CONTEXT["products"][key]["power_content_blueprints"]}
            written = {a["target_query"] for a in ARTICLES["articles"][key]}
            self.assertEqual(planned - written, set(), f"{key}: 원고 재료 없는 주제")

    def test_tool_assembles_article_instead_of_generic_template(self):
        self.assertIn('fetch("data/adcopy/power-content-articles.json"', POWER)
        self.assertIn("function articleFor(p,c)", POWER)
        self.assertIn("if(art)draft.splice(0,draft.length,...art.sections", POWER)
        self.assertIn("if(art)faq.splice(0,faq.length,...art.faq", POWER)
        self.assertIn("source:art?\"article\":\"template\"", POWER)

    def test_ambiguous_term_with_product_stem_is_in_scope(self):
        # '골프 배상책임'처럼 모호어(배상책임)가 상품 어근(골프)과 함께 쓰이면 주제 후보에서 빠지지 않는다
        self.assertIn('replace(/보험$/,"")', POWER)
        self.assertIn("AMBIGUOUS.has(v)&&value.includes", POWER)

    def test_articles_are_marked_for_human_review(self):
        for key, rows in ARTICLES["articles"].items():
            for row in rows:
                self.assertEqual(row["review_status"], "사람 심의 필요", f"{key} {row['title']}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
