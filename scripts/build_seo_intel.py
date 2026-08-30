#!/usr/bin/env python3
"""SEO 인텔 입력을 여러 소스에서 합쳐 data/seo/site-observations.json으로 정규화한다.

우선순위는 수동 검수 > site: 도메인 관측 > Search Console > 기타 원시 수집이다.
소스 파일이 없으면 조용히 넘어가며, 있는 것만 합친다.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "seo" / "site-observations.json"
MANUAL = ROOT / "data" / "seo" / "site-query-feed.json"
GSC = ROOT / "data" / "search-console.json"
SERP = ROOT / "serp" / "ad_analysis.json"
AUTOCOMPLETE = ROOT / "data" / "keyword-autocomplete.json"


def read_json(path: Path) -> Any | None:
    if not path.exists():
        return None
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def text(value: Any) -> str:
    return str(value or "").strip()


def normalize_status(value: Any) -> str:
    t = text(value).lower()
    if not t:
        return "active"
    if any(token in t for token in ("ended", "expired", "closed", "sold", "discontinued", "종료", "만료", "폐점")):
        return "ended"
    if any(token in t for token in ("review", "pending", "hold", "검토")):
        return "review"
    return t


def default_doc() -> dict[str, Any]:
    return {
        "_comment": "SEO 인텔 입력 스키마. site: 도메인 검색, 크롤링, 수동 점검 결과를 한 파일에 모으되 종료 이벤트·판매 종료 랜딩은 제외 플래그로 남긴다.",
        "schema_version": 2,
        "asof": "",
        "sources": ["manual_review", "search_console", "serp_analysis", "autocomplete"],
        "observations": [],
        "site_queries": [],
        "domain_queries": [],
        "monthly_diff": {
            "latest": "",
            "previous": "",
            "new_domains": [],
            "dropped_domains": [],
            "new_queries": [],
            "dropped_queries": [],
            "rising_angles": [],
            "declining_angles": [],
        },
        "default_filters": {
            "exclude_flags": ["ended_event", "expired_product", "sales_ended", "noindex", "redirect_chain"],
            "exclude_status": ["ended", "expired", "closed", "sold_out", "discontinued"],
        },
    }


def feed_observations(feed: Any, source: str, kind: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not isinstance(feed, dict):
        return rows
    items = feed.get("observations") or feed.get("rows") or feed.get("site_queries") or feed.get("domain_queries") or []
    if not isinstance(items, list):
        return rows
    for item in items:
        if not isinstance(item, dict):
            continue
        query = text(item.get("site_query") or item.get("query") or item.get("keyword") or item.get("target_query"))
        domain = text(item.get("domain") or item.get("site") or item.get("host") or (query.split("site:", 1)[1].split()[0] if query.startswith("site:") and len(query.split()) else ""))
        url = text(item.get("url") or item.get("page") or item.get("link"))
        title = text(item.get("title"))
        description = text(item.get("description") or item.get("desc"))
        status = normalize_status(item.get("status"))
        flags = item.get("flags") or item.get("tags") or item.get("risk_flags") or []
        if not isinstance(flags, list):
            flags = [flags]
        flags = [text(flag) for flag in flags if text(flag)]
        rows.append({
            "domain": domain,
            "site_query": query,
            "query": query,
            "url": url,
            "title": title,
            "description": description,
            "status": status,
            "reason": text(item.get("reason") or item.get("note") or item.get("exclusion_reason")),
            "flags": flags,
            "source": item.get("source") or source,
            "captured_at": text(item.get("captured_at") or item.get("date") or feed.get("asof") or ""),
            "kind": kind,
        })
    return rows


def autocomplete_observations(feed: Any) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not isinstance(feed, dict):
        return rows
    products = feed.get("products") or {}
    if not isinstance(products, dict):
        return rows
    for product_key, payload in products.items():
        if not isinstance(payload, dict):
            continue
        suggestions = payload.get("suggestions") or []
        if not isinstance(suggestions, list):
            continue
        for row in suggestions[:30]:
            if not isinstance(row, dict):
                continue
            keyword = text(row.get("keyword"))
            if not keyword:
                continue
            rows.append({
                "domain": "autocomplete",
                "site_query": keyword,
                "query": keyword,
                "url": "",
                "title": f"{product_key}:{keyword}",
                "description": text(row.get("intent") or row.get("reason") or ""),
                "status": row.get("registration") or "review",
                "reason": text(row.get("reason")),
                "flags": [text(row.get("intent"))] if text(row.get("intent")) else [],
                "source": "naver-visible-autocomplete",
                "captured_at": text(feed.get("asof") or ""),
                "kind": "autocomplete",
            })
    return rows


def dedupe(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[str, str, str]] = set()
    out: list[dict[str, Any]] = []
    for row in rows:
        key = (row.get("domain", ""), row.get("site_query", ""), row.get("url", ""))
        if key in seen:
            continue
        seen.add(key)
        out.append(row)
    return out


def build() -> dict[str, Any]:
    doc = default_doc()
    manual = read_json(MANUAL)
    gsc = read_json(GSC)
    serp = read_json(SERP)
    autocomplete = read_json(AUTOCOMPLETE)

    rows: list[dict[str, Any]] = []
    for source, feed, kind in (
        ("manual_review", manual, "manual"),
        ("search_console", gsc, "gsc"),
        ("serp_analysis", serp, "serp"),
    ):
        rows.extend(feed_observations(feed, source=source, kind=kind))
    rows.extend(autocomplete_observations(autocomplete))

    doc["observations"] = dedupe(rows)
    doc["site_queries"] = [row for row in doc["observations"] if row.get("site_query")]
    doc["domain_queries"] = [row for row in doc["observations"] if row.get("domain")]
    if manual and isinstance(manual, dict):
        doc["monthly_diff"] = {**doc["monthly_diff"], **(manual.get("monthly_diff") or {})}
        doc["asof"] = text(manual.get("asof"))
    elif gsc and isinstance(gsc, dict):
        doc["asof"] = text(gsc.get("asof"))
    elif serp and isinstance(serp, dict):
        doc["asof"] = text(serp.get("asof"))
    elif autocomplete and isinstance(autocomplete, dict):
        doc["asof"] = text(autocomplete.get("asof"))
        doc["monthly_diff"] = {**doc["monthly_diff"], "latest": text(autocomplete.get("month"))}
    return doc


def main() -> int:
    doc = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"✔ SEO 인텔 병합 · 관측 {len(doc['observations'])}건 · {doc.get('asof') or 'asof 없음'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
