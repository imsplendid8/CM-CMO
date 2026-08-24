#!/usr/bin/env python3
"""공개 SearchAd 수요와 비공개 GSC 범주 판정으로 SEO 제목 검토 큐를 만든다."""
from __future__ import annotations

import argparse
import json
import re
from datetime import date
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PRODUCTS = ROOT / "data/products.json"
DEFAULT_VOLUME = ROOT / "data/volume.json"
DEFAULT_FAQ = ROOT / "data/seo/faq-opportunities.json"
DEFAULT_GSC = ROOT / "data/search-console.json"
DEFAULT_OUTPUT = ROOT / "data/seo/title-opportunities.json"
METHOD_VERSION = "cm-seo-title-ops/1.1"

COMPETITOR_TOKENS = (
    "db", "동부", "현대", "삼성", "kb", "롯데", "메리츠", "농협", "라이나",
    "교보", "흥국", "axa", "악사", "한화생명",
)
TAIL_SIGNALS = (
    "비교", "추천", "가격", "비용", "보험료", "가입시기", "조건", "청구", "지연",
    "누수", "합의금", "진단비", "치료비", "다이렉트", "사이트",
)


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def norm(value: Any) -> str:
    return re.sub(r"[^0-9a-z가-힣]", "", str(value or "").lower())


def positive_impressions(row: dict[str, Any]) -> bool:
    try:
        return float(row.get("impressions", 0) or 0) > 0
    except (TypeError, ValueError):
        return False


def out_of_scope(query: str, product: dict[str, Any]) -> bool:
    value = norm(query)
    return any(norm(term) in value for term in product.get("excluded") or [])


def char_len(value: str) -> int:
    return len(value)


def is_competitor_query(query: str) -> bool:
    value = norm(query)
    return any(norm(token) in value for token in COMPETITOR_TOKENS)


def query_tier(query: str, product: dict[str, Any]) -> str:
    value = norm(query)
    heads = {norm(product.get("serpKw")), *(norm(x) for x in product.get("core", []))}
    if value in heads:
        return "head"
    if any(norm(signal) in value for signal in TAIL_SIGNALS):
        return "tail"
    return "body"


def fit_title(options: list[str]) -> str:
    cleaned = [re.sub(r"\s+", " ", x).strip(" |:") for x in options]
    for value in cleaned:
        if 15 <= char_len(value) <= 34:
            return value
    for value in cleaned:
        if char_len(value) < 15:
            expanded = f"{value} 한눈에 보기"
            if char_len(expanded) <= 34:
                return expanded
    return cleaned[-1][:34].rstrip(" |:")


def title_for(pattern: str, query: str, product: dict[str, Any]) -> str:
    name = product.get("serpKw") or product["name"]
    if pattern == "situation_first":
        return fit_title([f"{query} 가입 전 확인할 조건", f"{query} 가입 전 체크"])
    if pattern == "subject_first":
        if norm(name) == norm(query):
            return fit_title([f"{name}: 가입 전 선택 기준과 주의사항", f"{name}: 가입 전 선택 기준"])
        return fit_title([f"{name}: {query} 선택 기준과 주의사항", f"{name}: {query} 선택 기준"])
    return fit_title([f"{query} 비교할 때 놓치기 쉬운 조건", f"{query} 비교 기준"])


def relevant_volume_rows(product: dict[str, Any], volume: dict[str, Any]) -> list[dict[str, Any]]:
    rows = ((volume.get("products") or {}).get(product["key"]) or {}).get("keywords") or {}
    anchors = [*product.get("core", []), *product.get("special", []), product.get("serpKw", "")]
    anchors = [norm(x) for x in anchors if norm(x)]
    result = []
    for query, data in rows.items():
        qn = norm(query)
        if is_competitor_query(query) or out_of_scope(query, product) or not any(a in qn or qn in a for a in anchors):
            continue
        result.append({
            "query": query,
            "demand": int(data.get("pc", 0) or 0) + int(data.get("mobile", 0) or 0),
            "competition": data.get("comp") or "미확인",
        })
    return sorted(result, key=lambda row: (-row["demand"], row["query"]))


def opportunity_rows(product: dict[str, Any], volume: dict[str, Any], faq: dict[str, Any]) -> list[dict[str, Any]]:
    faq_map = {row.get("product_key"): row for row in faq.get("products", [])}
    volume_rows = relevant_volume_rows(product, volume)
    volume_map = {norm(row["query"]): row for row in volume_rows}
    candidates: list[dict[str, Any]] = []
    for row in (faq_map.get(product["key"], {}).get("opportunities") or []):
        query = str(row.get("query") or "").strip()
        if not query or is_competitor_query(query) or out_of_scope(query, product):
            continue
        measured = volume_map.get(norm(query), {})
        candidates.append({
            "query": query,
            "demand": int(row.get("demand", measured.get("demand", 0)) or 0),
            "competition": measured.get("competition", "미확인"),
        })
    candidates.extend(volume_rows)
    seen: set[str] = set()
    unique = []
    for row in candidates:
        key = norm(row["query"])
        if key and key not in seen:
            seen.add(key)
            unique.append(row)
    for query in [product.get("serpKw", ""), *product.get("core", []), *product.get("special", [])]:
        key = norm(query)
        if query and key not in seen and not is_competitor_query(query) and not out_of_scope(query, product):
            seen.add(key)
            unique.append({"query": query, "demand": 0, "competition": "미확인"})
    return unique[:3]


def gsc_is_current(gsc: dict[str, Any] | None, today: date | None = None, max_age_days: int = 40) -> bool:
    if not isinstance(gsc, dict) or not isinstance(gsc.get("rows"), list):
        return False
    if not any(norm(row.get("query")) and positive_impressions(row)
               for row in gsc["rows"] if isinstance(row, dict)):
        return False
    try:
        asof = date.fromisoformat(str(gsc.get("asof") or ""))
    except ValueError:
        return False
    age = ((today or date.today()) - asof).days
    return 0 <= age <= max_age_days


def gsc_signal(query: str, rows: list[dict[str, Any]] | None) -> tuple[str, list[dict[str, Any]]]:
    if rows is None:
        return "not_connected", []
    target = norm(query)
    # 부분 문자열은 암보험/유방암보험처럼 다른 의도를 한 검색어로 오인하므로 정확히 일치시킨다.
    matches = [row for row in rows
               if target and target == norm(row.get("query"))
               and positive_impressions(row)]
    if not matches:
        return "no_signal", []
    pages = {
        str(row.get("page") or "") for row in matches
        if float(row.get("impressions", 0) or 0) > 0 and row.get("page")
    }
    if len(pages) > 1:
        return "cannibalization_detected", matches
    positions = [
        float(row.get("position", 0) or 0) for row in matches
        if float(row.get("position", 0) or 0) > 0
    ]
    if any(position <= 3 for position in positions):
        return "top3", matches
    if any(4 <= position <= 20 for position in positions):
        return "striking_distance", matches
    return "low_visibility", matches


def authority_band(impressions: int, connected: bool) -> str:
    if not connected:
        return "not_checked"
    if impressions < 100:
        return "low"
    if impressions < 1000:
        return "growing"
    return "established"


def choose_candidate(candidates: list[dict[str, Any]], authority: str, connected: bool) -> str | None:
    if not connected:
        return None
    eligible = [row for row in candidates
                if row["gsc_status"] not in {"cannibalization_detected", "no_signal", "not_connected"}]
    if not eligible:
        return None
    status_weight = {"striking_distance": 6, "top3": 3, "low_visibility": 1}
    tier_weight = {
        "low": {"head": 0, "body": 2, "tail": 3},
        "growing": {"head": 1, "body": 3, "tail": 2},
        "established": {"head": 3, "body": 2, "tail": 1},
    }
    ranked = sorted(
        eligible,
        key=lambda row: (
            status_weight.get(row["gsc_status"], 0) + tier_weight.get(authority, {}).get(row["query_tier"], 0),
            row["search_demand"],
        ),
        reverse=True,
    )
    return ranked[0]["id"]


def generate(
    products: dict[str, Any],
    volume: dict[str, Any],
    faq: dict[str, Any],
    gsc: dict[str, Any] | None = None,
    today: date | None = None,
) -> dict[str, Any]:
    has_gsc_rows = isinstance(gsc, dict) and isinstance(gsc.get("rows"), list)
    raw_gsc_rows = gsc.get("rows") if has_gsc_rows else []
    connected = gsc_is_current(gsc, today=today)
    try:
        gsc_date = date.fromisoformat(str((gsc or {}).get("asof") or ""))
        gsc_date_fresh = 0 <= ((today or date.today()) - gsc_date).days <= 40
    except ValueError:
        gsc_date_fresh = False
    if connected:
        gsc_source = "verified_privately"
    elif has_gsc_rows and not raw_gsc_rows:
        gsc_source = "empty"
    elif has_gsc_rows and gsc_date_fresh:
        gsc_source = "insufficient"
    elif has_gsc_rows:
        gsc_source = "stale"
    else:
        gsc_source = "not_connected"
    gsc_rows = gsc["rows"] if connected else None
    searchad_connected = volume.get("source") == "searchad"
    dates = [str(x.get("asof") or "") for x in (volume, faq, gsc or {}) if isinstance(x, dict)]
    asof = max(
        (value for value in dates if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value)),
        default="unknown",
    )
    output_products = []
    patterns = ("situation_first", "subject_first", "scope_limited")
    weaknesses = {
        "situation_first": "질문 의도에 바로 답하는 본문이 없으면 제목의 약속이 과해질 수 있음",
        "subject_first": "상품명 중심이라 비브랜드 검색의 클릭 유인이 상대적으로 약할 수 있음",
        "scope_limited": "검색 범위를 좁혀 전체 수요보다 노출 기회가 작을 수 있음",
    }
    for product in products.get("products", []):
        rows = opportunity_rows(product, volume, faq)
        candidates = []
        private_rows: dict[tuple[str, str], float] = {}
        for index, (pattern, row) in enumerate(zip(patterns, rows), 1):
            signal, matches = gsc_signal(row["query"], gsc_rows)
            for match in matches:
                key = (norm(match.get("query")), str(match.get("page") or ""))
                private_rows[key] = max(private_rows.get(key, 0), float(match.get("impressions", 0) or 0))
            title = title_for(pattern, row["query"], product)
            candidates.append({
                "id": f"{product['key']}-title-{index}",
                "pattern": pattern,
                "title": title,
                "title_length": char_len(title),
                "target_query": row["query"],
                "search_demand": row["demand"],
                "competition": row["competition"],
                "query_tier": query_tier(row["query"], product),
                "gsc_status": signal,
                "weakness": weaknesses[pattern],
                "body_alignment_required": True,
                "review_status": "human_review_required",
            })
        product_gsc_verified = bool(private_rows)
        authority = authority_band(int(sum(private_rows.values())), product_gsc_verified)
        recommendation_allowed = searchad_connected and product_gsc_verified
        recommended = choose_candidate(candidates, authority, recommendation_allowed)
        for candidate in candidates:
            if candidate["gsc_status"] == "cannibalization_detected":
                candidate["decision"] = "rejected_cannibalization"
            elif candidate["gsc_status"] in {"no_signal", "not_connected"}:
                candidate["decision"] = "review_only_no_gsc_signal"
            elif candidate["id"] == recommended:
                candidate["decision"] = "recommended"
            else:
                candidate["decision"] = "review_only"
        if not searchad_connected:
            status = "blocked_searchad"
            next_action = "SearchAd 검색량 갱신"
        elif not product_gsc_verified or recommended is None:
            status = "blocked_gsc"
            next_action = "비공개 GSC에서 후보 검색어의 노출·페이지 확인"
        else:
            status = "ready_for_review"
            next_action = "본문 일치·상품 근거·준법·광고심의 검토"
        output_products.append({
            "product_key": product["key"],
            "status": status,
            "authority_band": authority,
            "recommended_candidate_id": recommended,
            "candidates": candidates,
            "next_action": next_action,
        })
    return {
        "_comment": "공개 배포용 제목 검토 큐. 비공개 GSC 원본 행과 상세 성과 수치는 포함하지 않는다.",
        "asof": asof,
        "method_version": METHOD_VERSION,
        "sources": {
            "searchad": "connected" if searchad_connected else "missing",
            "gsc": gsc_source,
        },
        "products": output_products,
    }


def validate(payload: dict[str, Any]) -> list[str]:
    errors = []
    products = payload.get("products")
    if not isinstance(products, list):
        return ["products must be a list"]
    for product in products:
        candidates = product.get("candidates") or []
        if len(candidates) != 3:
            errors.append(f"{product.get('product_key')}: exactly 3 candidates required")
        if str(product.get("status", "")).startswith("blocked_") and product.get("recommended_candidate_id") is not None:
            errors.append(f"{product.get('product_key')}: blocked result cannot recommend")
        for candidate in candidates:
            length = candidate.get("title_length", 0)
            if not 15 <= length <= 34:
                errors.append(f"{candidate.get('id')}: title length must be 15..34")
            if candidate.get("review_status") != "human_review_required":
                errors.append(f"{candidate.get('id')}: review status must remain human_review_required")
    serialized = json.dumps(payload, ensure_ascii=False)
    for private_field in ('"page"', '"clicks"', '"impressions"', '"ctr"', '"position"'):
        if private_field in serialized:
            errors.append(f"public output contains private field {private_field}")
    return errors


def write_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--products", type=Path, default=DEFAULT_PRODUCTS)
    parser.add_argument("--volume", type=Path, default=DEFAULT_VOLUME)
    parser.add_argument("--faq", type=Path, default=DEFAULT_FAQ)
    parser.add_argument("--gsc", type=Path, default=DEFAULT_GSC)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--validate", action="store_true")
    args = parser.parse_args()
    if args.validate:
        errors = validate(read_json(args.output, {}))
        if errors:
            print("\n".join(f"ERROR: {error}" for error in errors))
            return 1
        print("[OK] SEO title opportunities valid")
        return 0
    payload = generate(
        read_json(args.products, {}),
        read_json(args.volume, {}),
        read_json(args.faq, {}),
        read_json(args.gsc, None),
    )
    errors = validate(payload)
    if errors:
        raise ValueError("; ".join(errors))
    if args.dry_run:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        write_atomic(args.output, payload)
        print(f"[OK] SEO title ops: {len(payload['products'])} products, {payload['sources']['gsc']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
