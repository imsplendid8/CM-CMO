#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""뉴스 원문 보강 회귀 테스트 — 잘린 제목·설명문('...') 대신 완결 문장 요약(가상 기사 fixture)."""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import news_enrich as ne  # noqa: E402

ARTICLE = open(os.path.join(ROOT, "tests", "fixtures", "news_article_naver.html"), encoding="utf-8").read()
TRUNCATED_TITLE = "같은 범퍼인데 '고무줄' 수리비…과잉수리가 車보험료 ..."
SNIPPET = ("일부 정비업체의 과잉수리와 수리비 부풀리기 등으로 보험금 누수가 이어지면서 자동차보험 대물 보험금이 늘고 있다. "
           "이 같은 보험금 누수가 자동차보험 손해율을 끌어올려 결국 자동차보험료 인상으로 이어질 수...")


class TestExtract(unittest.TestCase):
    def test_body_container_only_without_byline_menu_or_copyright(self):
        art = ne.extract_article(ARTICLE)
        self.assertEqual(art["title"], "같은 범퍼인데 '고무줄' 수리비…과잉수리가 車보험료 올린다")
        self.assertTrue(art["text"].startswith("일부 정비업체의"), "기자 표기만 떼고 리드 문장은 살린다")
        for noise in ("홍길동 기자", "무단 전재", "많이 본 뉴스", "이용약관", "사진="):
            self.assertNotIn(noise, art["text"])

    def test_link_heavy_lines_are_dropped_but_inline_links_kept(self):
        # 본문 안 관련기사 목록(링크만 있는 줄)은 버리고, 문장 속 한 단어 링크는 본문으로 남긴다(Readability·trafilatura의 링크 밀도)
        art = ne.extract_article(ARTICLE)
        self.assertNotIn("보험료 인상 검토가 본격화된다", art["text"])
        self.assertNotIn("단속이 전국으로 확대된다", art["text"])
        self.assertIn("관련 자료는 가상보험연구원 누리집에서", art["text"])
        self.assertNotIn("본격화된다", ne.summarize(art["title"], art["text"]))

    def test_title_site_suffix_removed(self):
        self.assertEqual(ne._clean_title("손보사 손해율 상승 - 가상경제"), "손보사 손해율 상승")


class TestSummarize(unittest.TestCase):
    def test_complete_sentences_matching_title_no_ellipsis(self):
        art = ne.extract_article(ARTICLE)
        summary = ne.summarize(art["title"], art["text"])
        self.assertTrue(summary.startswith("일부 정비업체의 과잉수리"))
        self.assertIn("범퍼 교체 수리비", summary, "제목 핵심어(범퍼·수리비)가 담긴 근거 문장")
        self.assertLessEqual(len(summary), ne.SUMMARY_MAX)
        self.assertNotIn("…", summary)
        self.assertTrue(summary.endswith("다."))

    def test_snippet_fallback_drops_cut_sentence(self):
        out = ne.sentences_from_snippet(SNIPPET)
        self.assertEqual(out, "일부 정비업체의 과잉수리와 수리비 부풀리기 등으로 보험금 누수가 이어지면서 자동차보험 대물 보험금이 늘고 있다.")

    def test_snippet_fallback_strips_photo_and_byline_segments(self):
        out = ne.sentences_from_snippet("사진=가상화재 | 가상뉴스= 홍길동 기자 | 가상화재의 소송 건수가 업계에서 가장 많았다. 이는...")
        self.assertEqual(out, "가상화재의 소송 건수가 업계에서 가장 많았다.")

    def test_decimal_numbers_are_not_sentence_breaks(self):
        self.assertEqual(len(ne.split_sentences("손해율이 3.5% 올랐다. 보험료도 오른다.")), 2)


class TestEnrich(unittest.TestCase):
    def test_truncated_title_replaced_by_article_title(self):
        out = ne.enrich_item({"t": TRUNCATED_TITLE, "url": "https://example.com/a", "gist": SNIPPET}, fetcher=lambda u: ARTICLE)
        self.assertEqual(out["t"], "같은 범퍼인데 '고무줄' 수리비…과잉수리가 車보험료 올린다")
        self.assertEqual(out["summary_source"], "article")

    def test_fetch_failure_falls_back_to_snippet_and_tidy_title(self):
        def boom(_url):
            raise OSError("403")
        out = ne.enrich_item({"t": "보험 생활밀착형 보장 확대·AI 금융 진출…보험사기 대...", "url": "x", "gist": SNIPPET}, fetcher=boom)
        self.assertEqual(out["t"], "보험 생활밀착형 보장 확대·AI 금융 진출…보험사기")
        self.assertEqual(out["summary_source"], "snippet")
        self.assertNotIn("...", out["summary"])

    def test_enrich_items_skips_already_summarized(self):
        calls = []
        items = [{"t": "가상 기사 제목입니다", "url": "u1", "gist": "", "summary": "이미 있는 요약이다."},
                 {"t": TRUNCATED_TITLE, "url": "u2", "gist": SNIPPET}]
        ok, n = ne.enrich_items(items, fetcher=lambda u: calls.append(u) or ARTICLE)
        self.assertEqual((ok, n, calls), (1, 1, ["u2"]))
        self.assertEqual(items[0]["summary"], "이미 있는 요약이다.")


if __name__ == "__main__":
    unittest.main(verbosity=2)
