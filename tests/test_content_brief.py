#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import content_brief as cb  # noqa: E402
import papers_to_json as pj  # noqa: E402


def item(title, gist, url):
    return {"t": title, "gist": gist, "url": url, "src": "example.com", "date": "2026-08-21"}


class TestContentBrief(unittest.TestCase):
    def test_noise_stock_story_is_excluded_and_ad_review_story_selected(self):
        clip = {"date": "2026-08-21", "asof": "2026-08-21 08:00", "categories": {
            "ind_samsung": {"name": "삼성화재", "q": "삼성화재", "items": [
                item("삼성화재 목표주가 상향, 업종 1위", "증권사가 투자의견과 목표주가를 조정했다.", "https://e/stock"),
            ]},
            "ind_kb": {"name": "KB손해보험", "q": "KB손해보험", "items": [
                item("KB손해보험 배너광고 심의 제재", "보험 광고 위반에 과징금이 부과돼 광고 심의 점검이 필요하다.", "https://e/ad"),
            ]},
        }}
        digest = cb.build_digest(clip, {}, [])
        urls = [story["url"] for story in digest["stories"]]
        self.assertNotIn("https://e/stock", urls)
        self.assertIn("https://e/ad", urls)
        self.assertIn("파워콘텐츠", digest["stories"][0]["action"])

    def test_digest_has_shared_decision_fields_and_all_relevant_categories(self):
        clip = {"date": "2026-08-21", "categories": {
            "driver": {"name": "운전자보험", "q": "운전자보험", "items": [
                item("운전자보험 상품 개편", "가입 조건과 사고 보장 범위가 개편됐다.", "https://e/driver")
            ]},
            "hrmf": {"name": "주택화재보험", "q": "주택화재보험", "items": [
                item("폭우 침수 피해 급증", "침수 사고가 늘어 주택 보험 보장 문의가 증가했다.", "https://e/fire")
            ]},
        }}
        digest = cb.build_digest(clip, {}, ["driver", "hrmf"], limit=1)
        self.assertEqual(len(digest["stories"]), 1)
        self.assertEqual(set(digest["categories"]), {"driver", "hrmf"})
        for field in ("what", "why", "action", "evidence_scope", "confidence"):
            self.assertIn(field, digest["stories"][0])

    def test_concise_does_not_cut_a_word_at_requested_limit(self):
        result = cb.concise("보험 광고 심의 기준이 변경되어 모든 배너 소재를 다시 확인해야 합니다. 후속 조치도 필요합니다.", 45)
        self.assertTrue(result.endswith((".", "!", "?", "다", "요", "…")))
        self.assertNotIn("확인해야 합…", result)

    def test_same_event_and_golf_homonym_are_filtered(self):
        clip = {"date": "2026-08-21", "categories": {
            "golf": {"name": "골프보험", "q": "골프보험", "items": [
                item("폭스바겐 골프 신형 출시", "자동차 보험료와 제약사 소식", "https://e/vw")
            ]},
            "driver": {"name": "운전자보험", "q": "운전자보험", "items": [
                item("현대해상 페달 오조작 보험료 할인", "자동차보험 안전장치 할인 특약", "https://e/a"),
                item("페달 오조작 안전장치 보험 할인 확대", "현대해상 자동차보험 할인", "https://e/b"),
            ]},
        }}
        digest = cb.build_digest(clip, {}, ["golf", "driver"])
        urls = [story["url"] for story in digest["stories"]]
        self.assertNotIn("https://e/vw", urls)
        self.assertEqual(len([u for u in urls if u in ("https://e/a", "https://e/b")]), 1)


class TestPaperBrief(unittest.TestCase):
    def test_auto_paper_discloses_abstract_scope_and_limit(self):
        paper = {"title": "보험 디지털 전환 연구", "desc": "디지털 편의성이 구매의도에 미치는 영향을 분석했다.",
                 "note": "가입 UX 개선 근거.", "auto": True}
        brief = pj.paper_brief(paper)
        self.assertEqual(brief["evidence_scope"], "공개 서지·초록 기반")
        self.assertIn("원문 전체", brief["limitations"])
        self.assertTrue(brief["findings"])

    def test_link_only_paper_does_not_claim_it_was_read(self):
        brief = pj.paper_brief({"title": "제목 미확인", "desc": "", "note": "", "auto": False})
        self.assertEqual(brief["evidence_scope"], "링크만 확인")
        self.assertEqual(brief["confidence"], "낮음")


if __name__ == "__main__":
    unittest.main()
