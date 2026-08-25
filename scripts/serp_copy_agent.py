#!/usr/bin/env python3
"""SERP 관측·검색량·상품 마스터를 결합한 소재 입력 신호 생성기."""
import json
from datetime import date
from pathlib import Path

try:
    from scripts.io_utils import atomic_json_write
except ModuleNotFoundError:  # python scripts/serp_copy_agent.py
    from io_utils import atomic_json_write

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/adcopy/serp-candidates.json"


def read(rel, default):
    try:
        return json.loads((ROOT / rel).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def out_of_scope(text, product):
    normalized = str(text).replace(" ", "")
    return any(str(term).replace(" ", "") in normalized for term in product.get("excluded") or [])


def term_score(term, product):
    score = 0
    if term == product.get("serpKw"):
        score += 3
    if "보험" in term:
        score += 2
    if any(bad in term for bad in ("한화생명", "고객센터", "보험금청구")):
        score -= 10
    return score


def volume_keyword(volume, product):
    rows = ((volume.get("products") or {}).get(product["key"]) or {}).get("keywords") or {}
    tokens = [x for x in product.get("core", []) + product.get("special", []) if len(x.replace(" ", "")) >= 3]
    ranked = [(term, row) for term, row in rows.items()
              if any(t.replace(" ", "") in term.replace(" ", "") for t in tokens)
              and not out_of_scope(term, product)]
    ranked.sort(key=lambda x: (-(term_score(x[0], product)),
                               -(int(x[1].get("pc") or 0) + int(x[1].get("mobile") or 0)), x[0]))
    return ranked[0][0] if ranked else product.get("serpKw") or product["name"]


def date_diff(ads):
    dates = sorted({a.get("date") for a in ads if a.get("date")}, reverse=True)
    if not dates:
        return {"latest": None, "previous": None, "entered_brands": [], "exited_brands": []}
    latest, previous = dates[0], dates[1] if len(dates) > 1 else None
    brands = lambda d: {a.get("brand") for a in ads if a.get("date") == d and a.get("brand")}
    now, before = brands(latest), brands(previous) if previous else set()
    return {"latest": latest, "previous": previous,
            "entered_brands": sorted(now-before), "exited_brands": sorted(before-now)}


def generate(products, analysis, volume):
    output = []
    for product in products.get("products") or []:
        if product.get("cat") == "사이트":
            continue
        observed = ((analysis.get("products") or {}).get(product["key"]) or {})
        ads, common = observed.get("observed_ads") or [], observed.get("common_soju") or []
        if not ads:
            continue
        keyword = volume_keyword(volume, product)
        gaps = [x for x in product.get("special") or []
                if not out_of_scope(x, product) and not any(x in c or c in x for c in common)]
        angle = (gaps or product.get("core") or [product["name"]])[0]
        diff = date_diff(ads)
        output.append({
            "product_key": product["key"],
            "keyword": keyword,
            "common_competitor_angles": common,
            "selected_angle": angle,
            "latest_date": diff["latest"] or observed.get("latest_date"),
            "serp_diff": diff,
            "observed_count": len(ads),
            "copy_direction": f"{keyword} 검색 의도와 {angle} 상품 각도를 함께 사용",
            "visual_direction": f"보험종목 장면에서 {angle}을 바로 읽을 수 있게 하고 큰 탐색형 문구를 사용",
            "analysis_status": "ready",
        })
    return {
        "_comment": "경쟁사 원문·수치·브랜드를 복사하지 않고 검색어, 공통 소구, 차별 각도만 소재 입력 신호로 제공한다.",
        "asof": analysis.get("asof") or date.today().isoformat(),
        "products": output,
    }


def main(root=ROOT):
    _ = root
    result = generate(read("data/products.json", {}), read("serp/ad_analysis.json", {}),
                      read("data/volume.json", {}))
    atomic_json_write(OUT, result)
    print(f"[OK] {OUT.relative_to(ROOT)} · 상품 {len(result['products'])} · SERP 소재 입력 신호")
    return result


if __name__ == "__main__":
    main()
