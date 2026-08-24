#!/usr/bin/env python3
"""검색량·선택적 Search Console 스냅샷에서 고객 질문형 FAQ 기회를 발굴한다."""
import json
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/seo/faq-opportunities.json"
QUESTION_HINTS = ("어떻게", "왜", "언제", "가능", "차이", "비교", "가입", "보장", "보험료", "필요")


def read(rel, default):
    try:
        return json.loads((ROOT / rel).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


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


def topic_particle(term):
    last = term[-1]
    code = ord(last)
    has_batchim = 0xAC00 <= code <= 0xD7A3 and (code - 0xAC00) % 28 != 0
    return term + ("은" if has_batchim else "는")


def claim_allows_faq(claim, today=None):
    today = today or date.today()
    if claim.get("review_status") != "approved" or "faq" not in (claim.get("allowed_channels") or []):
        return False
    start, end = claim.get("effective_from"), claim.get("valid_until")
    return not (start and date.fromisoformat(start) > today) and not (end and date.fromisoformat(end) < today)


def relevant_claim_ids(claims, text):
    normalized = text.replace(" ", "")
    out = []
    for claim in claims:
        fields = f"{claim.get('claim','')} {claim.get('consumer_text','')}"
        terms = [x for x in fields.replace("·", " ").replace("/", " ").split() if len(x.replace(" ", "")) >= 2]
        if any(t.replace(" ", "") in normalized or normalized in t.replace(" ", "") for t in terms):
            out.append(claim["claim_id"])
    return out


def generate(products, volume, search_console, claims):
    approved = {}
    for claim in claims.get("claims") or []:
        if claim_allows_faq(claim): approved.setdefault(claim.get("product_key"), []).append(claim)
    gsc_rows = search_console.get("rows") or []
    out = []
    for p in products.get("products") or []:
        volume_rows = ((volume.get("products") or {}).get(p["key"]) or {}).get("keywords") or {}
        terms = []
        tokens = [x.replace(" ", "") for x in p.get("core", []) + p.get("special", []) if len(x.replace(" ", "")) >= 3]
        for term, row in volume_rows.items():
            compact_term = term.replace(" ", "")
            if not any(token in compact_term for token in tokens):
                continue
            if any(noise in term for noise in ("한화생명", "고객센터", "보험금청구", "메리츠", "삼성", "현대해상", "DB손해", "KB손해", "라이나")):
                continue
            total = int(row.get("pc") or 0) + int(row.get("mobile") or 0)
            terms.append((term, total, "searchad"))
        tokens = p.get("core", []) + p.get("special", [])
        for row in gsc_rows:
            query = str(row.get("query") or "")
            if any(t in query for t in tokens) and any(h in query for h in QUESTION_HINTS):
                terms.append((query, int(row.get("impressions") or 0), "search_console"))
        seen, candidates = set(), []
        for term, demand, source in sorted(terms, key=lambda x: (-x[1], x[0])):
            normalized = "".join(term.split())
            if not term or normalized in seen:
                continue
            seen.add(normalized)
            question = question_for(term); claim_ids = relevant_claim_ids(approved.get(p["key"], []), term + " " + question)
            candidates.append({"query": term, "question": question, "demand": demand, "source": source,
                "claim_ids": claim_ids, "answer_status": "draft_allowed" if claim_ids else "evidence_required",
                "next_action": "승인 claim으로 답변 작성" if claim_ids else "이 질문과 관련된 상품 근거 승인 후 답변 작성"})
            if len(candidates) == 4:
                break
        if candidates:
            out.append({"product_key": p["key"], "opportunities": candidates})
    return {"_comment": "SearchAd와 선택적 data/search-console.json에서 발굴한 FAQ 기회. evidence_required는 답변 자동 생성 금지.",
        "asof": volume.get("asof") or date.today().isoformat(), "search_console_connected": bool(gsc_rows), "products": out}


def main():
    result = generate(read("data/products.json", {}), read("data/volume.json", {}),
                      read("data/search-console.json", {}), read("data/evidence/claims.json", {}))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"✔ {OUT.relative_to(ROOT)} · 상품 {len(result['products'])} · 기회 {sum(len(x['opportunities']) for x in result['products'])}건 · GSC {'연결' if result['search_console_connected'] else '미연결'}")
    return result

if __name__ == "__main__":
    main()
