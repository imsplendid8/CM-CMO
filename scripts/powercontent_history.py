#!/usr/bin/env python3
"""현재 파워콘텐츠 제안을 다음 생성 전 이력으로 보존한다."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import date
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "data/adcopy/powercontent-history.json"
SOURCE_FILES = (
    ("data/adcopy/serp-candidates.json", "monthly_serp"),
    ("data/adcopy/powercontent-title-opportunities.json", "search_demand"),
)
EXCLUDED_PRODUCTS = {"home"}
EXCLUDED_TEXT = re.compile(r"(?<![A-Za-z])TM(?![A-Za-z])|텔레마케팅", re.I)


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def normalize(value: Any) -> str:
    return re.sub(r"[^0-9a-z가-힣]", "", str(value or "").lower())


def fingerprint(product_key: str, title: str, target_query: str, angle: str) -> str:
    raw = "|".join(normalize(value) for value in (product_key, title, target_query, angle))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:20]


def source_entries(root: Path = ROOT) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for relative, source in SOURCE_FILES:
        payload = read_json(root / relative, {})
        asof = str(payload.get("asof") or date.today().isoformat())
        default_month = str(payload.get("planning_month") or asof[:7])
        for product in payload.get("products") or []:
            product_key = str(product.get("product_key") or "")
            if not product_key or product_key in EXCLUDED_PRODUCTS:
                continue
            candidates = product.get("power_content_topics") if source == "monthly_serp" else product.get("candidates")
            for candidate in candidates or []:
                title = str(candidate.get("title") or "").strip()
                target_query = str(candidate.get("target_query") or "").strip()
                angle = str(candidate.get("angle") or candidate.get("pattern") or "").strip()
                text = " ".join((title, target_query, angle))
                if not title or EXCLUDED_TEXT.search(text):
                    continue
                sections = [str(value).strip() for value in candidate.get("sections") or [] if str(value).strip()]
                entries.append({
                    "fingerprint": fingerprint(product_key, title, target_query, angle),
                    "product_key": product_key,
                    "planning_month": str(product.get("month") or default_month)[:7],
                    "asof": asof[:10],
                    "title": title,
                    "target_query": target_query,
                    "angle": angle,
                    "sections": sections[:6],
                    "source": source,
                })
    return entries


def archive(root: Path = ROOT, output: Path | None = None, keep: int = 600) -> dict[str, Any]:
    output = output or (root / "data/adcopy/powercontent-history.json")
    previous = read_json(output, {"entries": []})
    merged: dict[str, dict[str, Any]] = {}
    for row in [*(previous.get("entries") or []), *source_entries(root)]:
        key = str(row.get("fingerprint") or "")
        if key and row.get("product_key") not in EXCLUDED_PRODUCTS:
            merged[key] = row
    entries = sorted(merged.values(), key=lambda row: (str(row.get("planning_month") or ""), str(row.get("asof") or ""), row["fingerprint"]), reverse=True)[:keep]
    payload = {
        "_comment": "월간 파워콘텐츠 반복 제안과 검색 의도 카니벌라이제이션을 막기 위한 공개 최소 이력. 성과·내부 URL은 포함하지 않는다.",
        "schema_version": 1,
        "updated_at": date.today().isoformat(),
        "retention": f"latest_{keep}_unique_proposals",
        "entries": entries,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    temp = output.with_suffix(output.suffix + ".tmp")
    temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(output)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--keep", type=int, default=600)
    args = parser.parse_args()
    payload = archive(output=args.output, keep=args.keep)
    print(f"[OK] 파워콘텐츠 제안 이력 {len(payload['entries'])}건 · 다이렉트 홈/TM 제외")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
