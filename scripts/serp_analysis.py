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
import hashlib
from collections import Counter, defaultdict
from datetime import datetime, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = "serp/ad_observations.json"
OUT = "serp/ad_analysis.json"
DEFAULT_WINDOW_DAYS = 35   # 최신 관측일 기준 lookback(주간 캡쳐 ~5주) — 중단된 프로모션·과거 광고주 제외


def _rank(counter):
    """(항목, 수)를 (-수, 항목) 정렬 → 결정론(동률도 사전순)."""
    return [[k, n] for k, n in sorted(counter.items(), key=lambda kv: (-kv[1], kv[0]))]


def _as_list(value):
    if not value:
        return []
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    return [str(value).strip()] if str(value).strip() else []


def _extensions(o):
    ext = o.get("extensions") or {}
    return {
        "additional_titles": _as_list(ext.get("additional_titles") or o.get("additional_titles")),
        "additional_descriptions": _as_list(ext.get("additional_descriptions") or o.get("additional_descriptions")),
        "promotions": _as_list(ext.get("promotions") or o.get("promotion") or o.get("promo")),
        "sitelinks": _as_list(ext.get("sitelinks") or o.get("sitelinks")),
    }


def _cta_terms(o):
    text = " ".join([str(o.get("cta") or ""), str(o.get("title") or ""), str(o.get("desc") or ""), str(o.get("description") or "")])
    terms = ["계산", "확인", "가입", "비교", "견적", "상담", "청구", "해지", "약관"]
    return [term for term in terms if term in text]


def _risk_flags(o):
    text = " ".join([str(o.get("title") or ""), str(o.get("desc") or ""), str(o.get("description") or ""), str(o.get("promo") or "")])
    flags = []
    patterns = {
        "absolute_or_top_claim": ["최저", "최고", "1위", "유일", "100%"],
        "instant_join_claim": ["바로 가입", "즉시 가입", "누구나 가입"],
        "fear_hook": ["사고", "위험", "불안"],
    }
    for code, words in patterns.items():
        if any(word in text for word in words):
            flags.append(code)
    return flags


def _observation_id(o):
    text = json.dumps({
        "product": o.get("product"), "keyword": o.get("keyword"), "date": o.get("date"),
        "rank": o.get("rank"), "brand": o.get("brand"), "title": o.get("title"), "desc": o.get("desc") or o.get("description"),
    }, ensure_ascii=False, sort_keys=True)
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:16]


def _monthly_diff(obs):
    dated = sorted({str(o.get("date") or "")[:10] for o in obs if o.get("date")})
    if len(dated) < 2:
        return {"latest": dated[-1] if dated else "", "previous": "", "new_brands": [], "dropped_brands": [], "rising_angles": [], "declining_angles": []}
    previous, latest = dated[-2], dated[-1]
    latest_rows = [o for o in obs if str(o.get("date") or "")[:10] == latest]
    previous_rows = [o for o in obs if str(o.get("date") or "")[:10] == previous]
    latest_brands = {o.get("brand", "") for o in latest_rows if o.get("brand")}
    previous_brands = {o.get("brand", "") for o in previous_rows if o.get("brand")}
    latest_angles = Counter(c for o in latest_rows for c in (o.get("covers") or []) if c)
    previous_angles = Counter(c for o in previous_rows for c in (o.get("covers") or []) if c)
    angles = sorted(set(latest_angles) | set(previous_angles))
    return {
        "latest": latest,
        "previous": previous,
        "new_brands": sorted(latest_brands - previous_brands),
        "dropped_brands": sorted(previous_brands - latest_brands),
        "rising_angles": [term for term in angles if latest_angles[term] > previous_angles[term]],
        "declining_angles": [term for term in angles if latest_angles[term] < previous_angles[term]],
    }


def _d(s):
    try:
        return datetime.strptime(str(s)[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def window_cutoff(observations, window_days=DEFAULT_WINDOW_DAYS):
    """최신 관측일 - window_days. 관측일이 없으면 None(전체 사용)."""
    dates = [d for d in (_d(o.get("date")) for o in (observations or [])) if d]
    if not dates:
        return None
    return max(dates) - timedelta(days=window_days)


def _recent(observations, window_days=DEFAULT_WINDOW_DAYS):
    """lookback 창 안(또는 날짜 없는) 관측만. 오래된 관측·과거 광고주를 현재 근거에서 제외."""
    cutoff = window_cutoff(observations, window_days)
    if cutoff is None:
        return list(observations or [])
    return [o for o in observations if (_d(o.get("date")) is None) or (_d(o.get("date")) >= cutoff)]


def analyze(observations, window_days=DEFAULT_WINDOW_DAYS):
    """상품별 관측 소재 집계(최신 lookback 창만). 반환: {product: {n, brands, soju, common_soju, promos, cta, prices}}."""
    byp = defaultdict(list)
    for o in _recent(observations or [], window_days):
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
        observed_ads = sorted(({
            "source_observation_id": _observation_id(o),
            "brand": o.get("brand", ""), "keyword": o.get("keyword", ""),
            "date": o.get("date", ""), "rank": o.get("rank"),
            "title": o.get("title", ""), "desc": o.get("desc", ""),
            "description": o.get("description") or o.get("desc", ""),
            "promo": o.get("promo", ""),
            "extensions": _extensions(o),
            "detected_angles": _as_list(o.get("covers")),
            "cta_terms": _cta_terms(o),
            "risk_flags": _risk_flags(o),
        } for o in obs), key=lambda x: (x["date"], -(x["rank"] or 999), x["brand"]), reverse=True)
        dated = [o["date"] for o in observed_ads if o["date"]]
        out[pk] = {
            "n": len(obs),
            "brands": sorted(brands),
            "soju": _rank(covers),
            "common_soju": common,
            "promos": _rank(promos),
            "cta": _rank(ctas),
            "prices": sorted(set(prices)),
            # 공개 SERP 원문은 비교·회피 근거로만 UI에 노출한다. 우리 문구 생성기에 복사하지 않는다.
            "latest_date": max(dated) if dated else "",
            "observed_ads": observed_ads,
            "monthly_diff": _monthly_diff(obs),
        }
    return out


def load(root=ROOT):
    with open(os.path.join(root, SRC), encoding="utf-8") as f:
        return json.load(f)


def build(root=ROOT, window_days=DEFAULT_WINDOW_DAYS):
    data = load(root)
    obs = data.get("observations", [])
    cutoff = window_cutoff(obs, window_days)
    result = {
        "_comment": "serp/ad_observations.json 관측 소재의 상품별 분석(규칙 기반·결정론·최신 lookback 창). serp_analysis.py가 생성.",
        "schema_version": 2,
        "required_observation_fields": ["product", "keyword", "date", "device", "rank", "brand", "title", "description", "extensions", "detected_angles", "cta_terms", "risk_flags"],
        "asof": data.get("asof", ""),
        "window_days": window_days,
        "since": cutoff.isoformat() if cutoff else None,
        "products": analyze(obs, window_days),
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
