#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""serp_observation_agent 회귀 테스트 — 자동 캡쳐 DOM → 경쟁사 관측 정규화(가상 fixture)."""
import json
import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import serp_observation_agent as agent  # noqa: E402

PRODUCTS = [{"key": "driver", "core": ["운전자보험"], "special": ["벌금", "변호사선임", "형사합의금"]},
            {"key": "cncr", "core": ["암보험"], "special": ["유사암", "진단비", "표적항암"]}]


def ad(rank, brand, domain, title, desc, ext=(), date="2026-10-04", product="driver"):
    return {"product": product, "keyword": "운전자보험", "date": date, "kind": "powerlink", "rank": rank,
            "brand": brand, "domain": domain, "title": title, "desc": desc, "extensions": list(ext)}


class TestNormalize(unittest.TestCase):
    def test_structured_ads_become_competitor_observations(self):
        rows = [
            {"product": "driver", "date": "2026-10-04", "text": "운전자보험 관련 광고 이 광고가 표시된 이유"},  # 이전 추출기 머리글 행
            ad(1, "가상손해보험다이렉트", "direct.example-ins.co.kr", "가상다이렉트 공식 운전자보험",
               "형사합의금·변호사선임비용 보장, 온라인 가입 시 5% 할인", ["24시간가입", "보험료계산"]),
            ad(2, "한화손보다이렉트", "hanwhadirect.com", "한화 다이렉트 운전자보험", "자사 광고 가상 문구입니다 충분히 길게"),
            ad(3, "샘플화재다이렉트", "sample-fire.com", "샘플화재 다이렉트 운전자보험",
               "지금 가입하면 네이버페이 포인트 최대 3만원 증정!", ["간편가입", "가입이벤트"]),
        ]
        out = agent.normalize_rows(rows, PRODUCTS)
        self.assertEqual([o["brand"] for o in out], ["가상손해보험다이렉트", "샘플화재다이렉트"])
        self.assertEqual([o["rank"] for o in out], [1, 2], "자사 제외 후 경쟁사 순위")
        first, second = out
        self.assertEqual(first["covers"][:2], ["변호사선임", "형사합의금"])
        self.assertNotIn("운전자보험", first["covers"], "상품명은 소구(보장 항목)가 아님")
        self.assertEqual(first["price"], "5% 할인")
        self.assertIn("가입", first["cta"])
        self.assertIn("견적", first["cta"])
        self.assertEqual(first["landing"], "가상손해보험다이렉트 공식")
        self.assertEqual(first["source"], agent.AUTO_SOURCE)
        self.assertEqual(second["price"], "최대 3만원")
        self.assertIn("증정", second["promo"])
        self.assertEqual(second["extensions"]["promotions"], ["가입이벤트"])

    def test_duplicate_ad_in_same_capture_is_counted_once(self):
        row = ad(1, "가상", "a.example.com", "가상 운전자보험 공식", "벌금까지 챙기는 가상 운전자보험 설명 문구")
        self.assertEqual(len(agent.normalize_rows([row, dict(row, rank=4)], PRODUCTS)), 1)

    def test_raw_fallback_splits_by_domain_line(self):
        raw = {"product": "cncr", "keyword": "암보험", "date": "2026-10-04", "kind": "powerlink", "raw": True, "lines": [
            "암보험 관련 광고", "가상생명 · virtual-life.co.kr 광고", "가상생명 암보험 비갱신형 · 진단비 한번에",
            "유사암 진단비까지 챙기는 가상생명 암보험. 온라인 전용 상품으로 부담을 줄였어요.", "보험료계산",
            "샘플손해보험 · sample-ins.com 광고", "샘플 다이렉트 암보험 · 첫날부터 보장",
            "표적항암 치료비까지 준비하는 샘플 암보험, 신규 가입 고객 상품권 증정 이벤트 진행 중.", "가입이벤트"]}
        out = agent.normalize_rows([raw], PRODUCTS)
        self.assertEqual([(o["brand"], o["domain"]) for o in out],
                         [("가상생명", "virtual-life.co.kr"), ("샘플손해보험", "sample-ins.com")])
        self.assertEqual(out[0]["title"], "가상생명 암보험 비갱신형 · 진단비 한번에")
        self.assertIn("유사암", out[0]["covers"])
        self.assertIn("상품권", out[1]["promo"])


class TestMerge(unittest.TestCase):
    def test_refresh_replaces_only_same_capture_auto_rows(self):
        seed = {"product": "driver", "date": "2026-07-26", "rank": 1, "brand": "초기 샘플"}
        old_auto = {"product": "driver", "date": "2026-10-04", "rank": 1, "brand": "이전 실행", "source": agent.AUTO_SOURCE}
        other_week = {"product": "driver", "date": "2026-09-27", "rank": 1, "brand": "지난주", "source": agent.AUTO_SOURCE}
        new = [{"product": "driver", "date": "2026-10-04", "rank": 1, "brand": "재실행", "source": agent.AUTO_SOURCE}]
        merged = agent.merge([seed, old_auto, other_week], new)
        self.assertEqual([o["brand"] for o in merged], ["초기 샘플", "지난주", "재실행"])

    def test_build_updates_asof_from_new_capture(self):
        with tempfile.TemporaryDirectory() as root:
            os.makedirs(os.path.join(root, "serp"))
            os.makedirs(os.path.join(root, "data"))
            with open(os.path.join(root, "data/products.json"), "w", encoding="utf-8") as f:
                json.dump({"products": PRODUCTS}, f)
            with open(os.path.join(root, agent.OUT), "w", encoding="utf-8") as f:
                json.dump({"asof": "2026-08-02", "observations": [{"product": "driver", "date": "2026-07-26", "rank": 1}]}, f)
            with open(os.path.join(root, agent.DOM_SRC), "w", encoding="utf-8") as f:
                json.dump({"observations": [ad(1, "가상", "a.example.com", "가상 운전자보험 공식", "벌금까지 챙기는 가상 운전자보험 설명")]}, f)
            result, n_auto = agent.build(root)
        self.assertEqual(n_auto, 1)
        self.assertEqual(result["asof"], "2026-10-04")
        self.assertEqual(len(result["observations"]), 2)


class TestDomSignal(unittest.TestCase):
    def test_summarizes_latest_capture_domains_and_changes(self):
        import serp_analysis
        dom = {"source": "playwright-powerlink", "observations": [
            {"product": "driver", "date": "2026-09-20", "kind": "powerlink", "domain": "a.example.com"},
            {"product": "driver", "date": "2026-09-20", "kind": "powerlink", "domain": "b.example.com"},
            {"product": "driver", "date": "2026-09-27", "kind": "powerlink", "domain": "a.example.com"},
            {"product": "driver", "date": "2026-09-27", "kind": "powerlink", "domain": "c.example.com"},
            {"product": "driver", "date": "2026-09-27", "text": "운전자보험 관련 광고"},  # 이전 추출기 머리글 행
            {"product": "cncr", "date": "2026-09-27", "kind": "powerlink", "domain": "z.example.com"},
        ]}
        sig = serp_analysis._dom_signal("driver", dom)
        self.assertEqual(sig["latest"], "2026-09-27")
        self.assertEqual(sig["ads"], 2)
        self.assertEqual(sig["domains"], ["a.example.com", "c.example.com"])
        self.assertEqual(sig["new_domains"], ["c.example.com"])
        self.assertEqual(sig["dropped_domains"], ["b.example.com"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
