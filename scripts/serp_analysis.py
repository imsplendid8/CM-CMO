#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SERP 관측 소재 분석 — serp/ad_observations.json → serp/ad_analysis.json.

캡쳐(serp/*.png)에서 사람이 확인한 경쟁사 공개 광고 요소(관측 소재)를 상품별로 집계해
'경쟁 공통 소구(회피/차별 대상)·프로모션 유형·가격 신호·CTA 패턴'을 산출한다. 규칙 기반·결정론.
serp-tool(소재분석)과 adcopy-tool(문구 근거)이 이 산출물을 공유한다.

전부 샘플·공개 데이터. 순수 함수(analyze)는 주입된 리스트로 동작해 테스트가 fixture를 넣을 수 있다.
표준 라이브러리만 사용.
"""
import json
import os
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = "serp/ad_observations.json"
OUT = "serp/ad_analysis.json"


def _rank(counter):
    """(항목, 수)를 (-수, 항목) 정렬 → 결정론(동률도 사전순)."""
    return [[k, n] for k, n in sorted(counter.items(), key=lambda kv: (-kv[1], kv[0]))]


def analyze(observations):
    """상품별 관측 소재 집계. 반환: {product: {n, brands, soju, common_soju, promos, cta, prices}}."""
    byp = defaultdict(list)
    for o in observations or []:
        byp[o.get("product", "")].append(o)
    out = {}
    for pk in sorted(byp):
        obs = byp[pk]
        covers, promos, ctas = Counter(), Counter(), Counter()
        cover_brands = defaultdict(set)
        brands, prices = set(), []
        for o in obs:
            b = o.get("brand", "")
            if b:
                brands.add(b)
            for c in (o.get("covers") or []):
                if c:
                    covers[c] += 1
                    cover_brands[c].add(b)
            if o.get("promo"):
                promos[o["promo"]] += 1
            if o.get("cta"):
                ctas[o["cta"]] += 1
            if o.get("price"):
                prices.append(o["price"])
        # 2개 이상 브랜드가 함께 쓰는 소구 = 경쟁 공통(차별화 위해 회피/우회 대상)
        common = sorted(c for c, bs in cover_brands.items() if len({x for x in bs if x}) >= 2)
        out[pk] = {
            "n": len(obs),
            "brands": sorted(brands),
            "soju": _rank(covers),
            "common_soju": common,
            "promos": _rank(promos),
            "cta": _rank(ctas),
            "prices": sorted(set(prices)),
        }
    return out


def load(root=ROOT):
    with open(os.path.join(root, SRC), encoding="utf-8") as f:
        return json.load(f)


def build(root=ROOT):
    data = load(root)
    result = {
        "_comment": "serp/ad_observations.json 관측 소재의 상품별 분석(규칙 기반·결정론). serp_analysis.py가 생성.",
        "asof": data.get("asof", ""),
        "products": analyze(data.get("observations", [])),
    }
    return result


def main(root=ROOT):
    result = build(root)
    with open(os.path.join(root, OUT), "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=1)
    n = sum(v["n"] for v in result["products"].values())
    print(f"✔ {OUT} · 상품 {len(result['products'])} · 관측 {n}건")
    return result


if __name__ == "__main__":
    main()
