#!/usr/bin/env python3
"""공개 SearchAd 검색량에서 고객 질문형 FAQ 기회를 발굴한다."""
import json
from datetime import date
from pathlib import Path

try:
    from scripts.io_utils import atomic_json_write
except ModuleNotFoundError:  # python scripts/faq_opportunity_agent.py
    from io_utils import atomic_json_write

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/seo/faq-opportunities.json"


def read(rel, default):
    try:
        return json.loads((ROOT / rel).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def topic_particle(term):
    last = term[-1]
    code = ord(last)
    has_batchim = 0xAC00 <= code <= 0xD7A3 and (code - 0xAC00) % 28 != 0
    return term + ("은" if has_batchim else "는")


def question_for(term):
    if "보험료" in term:
        return f"{term}는 어떤 조건에 따라 달라지나요?"
    if "가입" in term:
        return f"{term}할 때 무엇을 먼저 확인해야 하나요?"
    if "다이렉트" in term:
        return f"{topic_particle(term)} 어떤 보험을 온라인에서 확인할 수 있나요?"
    if "보험" in term:
        return f"{topic_particle(term)} 무엇을 보장하는 보험인가요?"
    return f"{term} 관련 보장은 가입 전에 무엇을 확인해야 하나요?"


def generate(products, volume, search_console=None):
    """공개 FAQ 후보에는 SearchAd 데이터만 사용하고 답변은 자동 생성하지 않는다."""
    _ = search_console
    out = []
    for product in products.get("products") or []:
        volume_rows = ((volume.get("products") or {}).get(product["key"]) or {}).get("keywords") or {}
        terms = []
        tokens = [x.replace(" ", "") for x in product.get("core", []) + product.get("special", [])
                  if len(x.replace(" ", "")) >= 3]
        for term, row in volume_rows.items():
            compact_term = term.replace(" ", "")
            if any(excluded.replace(" ", "") in compact_term for excluded in product.get("excluded") or []):
                continue
            if not any(token in compact_term for token in tokens):
                continue
            if any(noise in term for noise in ("한화생명", "고객센터", "보험금청구", "메리츠", "삼성", "현대해상", "DB손해", "KB손해", "라이나")):
                continue
            total = int(row.get("pc") or 0) + int(row.get("mobile") or 0)
            terms.append((term, total, "searchad"))
        seen, candidates = set(), []
        for term, demand, source in sorted(terms, key=lambda x: (-x[1], x[0])):
            normalized = "".join(term.split())
            if not term or normalized in seen:
                continue
            seen.add(normalized)
            candidates.append({
                "query": term,
                "question": question_for(term),
                "demand": demand,
                "source": source,
                "review_status": "content_review_required",
                "next_action": "상품자료·약관을 확인해 답변 작성",
            })
            if len(candidates) == 4:
                break
        if candidates:
            out.append({"product_key": product["key"], "opportunities": candidates})
    return {
        "_comment": "SearchAd 수요에서 발굴한 공개 FAQ 질문 후보. 답변은 자동 생성하지 않는다.",
        "asof": volume.get("asof") or date.today().isoformat(),
        "products": out,
    }


def main():
    result = generate(read("data/products.json", {}), read("data/volume.json", {}),
                      read("data/search-console.json", {}))
    atomic_json_write(OUT, result)
    print(f"[OK] {OUT.relative_to(ROOT)} · 상품 {len(result['products'])} · 기회 {sum(len(x['opportunities']) for x in result['products'])}건")
    return result


if __name__ == "__main__":
    main()
