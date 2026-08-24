#!/usr/bin/env python3
"""SERP 관측·검색량·상품 근거를 결합한 검색광고 검토 후보 생성기."""
import hashlib
import json
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/adcopy/serp-candidates.json"
TITLE_MAX, DESC_MIN, DESC_MAX = 15, 20, 45
BANNED = ("최고", "최저", "1위", "유일", "무조건", "100%", "완벽", "무심사", "누구나")


def read(rel, default):
    try:
        return json.loads((ROOT / rel).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def compact(text, maximum):
    text = " ".join(str(text).split())
    if len(text) <= maximum:
        return text
    words, out = text.split(), ""
    for word in words:
        candidate = f"{out} {word}".strip()
        if len(candidate) > maximum:
            break
        out = candidate
    return out


def volume_keyword(volume, product):
    rows = ((volume.get("products") or {}).get(product["key"]) or {}).get("keywords") or {}
    tokens = [x for x in product.get("core", []) + product.get("special", []) if len(x.replace(" ", "")) >= 3]
    ranked = [(term, row) for term, row in rows.items() if any(t.replace(" ", "") in term.replace(" ", "") for t in tokens)]
    ranked.sort(key=lambda x: (-(term_score(x[0], product)), -(int(x[1].get("pc") or 0) + int(x[1].get("mobile") or 0)), x[0]))
    return ranked[0][0] if ranked else product.get("serpKw") or product["name"]


def term_score(term, product):
    score = 0
    if term == product.get("serpKw"):
        score += 3
    if "보험" in term:
        score += 2
    if any(bad in term for bad in ("한화생명", "고객센터", "보험금청구")):
        score -= 10
    return score


def date_diff(ads):
    dates = sorted({a.get("date") for a in ads if a.get("date")}, reverse=True)
    if not dates:
        return {"latest": None, "previous": None, "entered_brands": [], "exited_brands": []}
    latest, previous = dates[0], dates[1] if len(dates) > 1 else None
    brands = lambda d: {a.get("brand") for a in ads if a.get("date") == d and a.get("brand")}
    now, before = brands(latest), brands(previous) if previous else set()
    return {"latest": latest, "previous": previous, "entered_brands": sorted(now-before), "exited_brands": sorted(before-now)}


def valid(title, desc):
    joined = title + desc
    return 4 <= len(title) <= TITLE_MAX and DESC_MIN <= len(desc) <= DESC_MAX and not any(x in joined for x in BANNED)


def claim_allows_sa(claim, today=None):
    today = today or date.today()
    channels = set(claim.get("allowed_channels") or [])
    if claim.get("review_status") != "approved" or not {"sa_title", "sa_description"} <= channels:
        return False
    start, end = claim.get("effective_from"), claim.get("valid_until")
    return not (start and date.fromisoformat(start) > today) and not (end and date.fromisoformat(end) < today)


def relevant_claim_ids(claims, text):
    normalized = text.replace(" ", "")
    matched = []
    for claim in claims:
        fields = f"{claim.get('claim','')} {claim.get('consumer_text','')}"
        terms = [x for x in fields.replace("·", " ").replace("/", " ").split() if len(x.replace(" ", "")) >= 2]
        if any(term.replace(" ", "") in normalized or normalized in term.replace(" ", "") for term in terms):
            matched.append(claim["claim_id"])
    return matched


def generate(products, analysis, volume, claims):
    approved = {}
    for c in claims.get("claims") or []:
        if claim_allows_sa(c):
            approved.setdefault(c.get("product_key"), []).append(c)
    output = []
    for p in products.get("products") or []:
        observed = ((analysis.get("products") or {}).get(p["key"]) or {})
        ads, common = observed.get("observed_ads") or [], observed.get("common_soju") or []
        if not ads:
            continue
        keyword = volume_keyword(volume, p)
        gaps = [x for x in p.get("special") or [] if not any(x in c or c in x for c in common)]
        angle = (gaps or p.get("core") or [p["name"]])[0]
        short_name = p.get("serpKw") or p["name"]
        intent_title = f"{keyword} 가입 전 확인"
        if len(intent_title) > TITLE_MAX:
            intent_title = f"{short_name} 가입조건"
        raw = [
            ("빈 소구 선점", compact(f"{angle} 확인", TITLE_MAX), f"{angle} 포함 여부와 가입 조건을 온라인에서 확인해 보세요."),
            ("검색 의도 응답", intent_title, f"{keyword} 찾는다면 보장 범위와 제외 조건을 먼저 확인하세요."),
            ("비교 행동 유도", compact(f"{short_name} 보험료 확인", TITLE_MAX), f"{short_name}에서 필요한 담보와 보험료를 직접 비교해 보세요."),
        ]
        candidates = []
        for strategy, title, desc in raw:
            desc = compact(desc, DESC_MAX)
            if not valid(title, desc):
                continue
            fingerprint = hashlib.sha256(f"{p['key']}|{title}|{desc}".encode()).hexdigest()[:16]
            claim_ids = relevant_claim_ids(approved.get(p["key"], []), title + " " + desc)
            candidates.append({"strategy": strategy, "title": title, "description": desc,
                "title_length": len(title), "description_length": len(desc), "claim_ids": claim_ids,
                "evidence_status": "verified" if claim_ids else "product_evidence_required",
                "review_status": "human_review_required", "fingerprint": fingerprint})
        output.append({"product_key": p["key"], "keyword": keyword, "common_competitor_angles": common,
            "selected_angle": angle, "serp_diff": date_diff(ads), "observed_count": len(ads), "candidates": candidates})
    return {"_comment": "공개 SERP를 복제하지 않고 공통 소구·검색량·승인 claim을 결합한 사람 검토용 SA 후보.",
        "asof": analysis.get("asof") or date.today().isoformat(), "products": output}


def main(root=ROOT):
    result = generate(read("data/products.json", {}), read("serp/ad_analysis.json", {}),
                      read("data/volume.json", {}), read("data/evidence/claims.json", {}))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"✔ {OUT.relative_to(ROOT)} · 상품 {len(result['products'])} · 후보 {sum(len(x['candidates']) for x in result['products'])}건")
    return result

if __name__ == "__main__":
    main()
