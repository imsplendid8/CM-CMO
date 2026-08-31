#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""이미지 생성 대기열을 만든다.

월간 소재 에이전트는 이미지 브리프와 승인 원본만 만들고 유료 이미지 API를 호출하지
않는다. 이 스크립트는 그 경계를 명시적으로 저장한다. 외부 생성기나 운영자가
``asset_path``에 PNG를 넣은 뒤 ``--sync``를 실행하면, 검증된 파일만 월간 계획의
실제 asset으로 승격할 수 있다.
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PLAN_PATH = ROOT / "data/adcopy/serp-candidates.json"
QUEUE_PATH = ROOT / "data/adcopy/image-generation-queue.json"
PRODUCTS_PATH = ROOT / "data/products.json"


def read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(path)


def safe(value: Any) -> str:
    value = re.sub(r"[^0-9A-Za-z가-힣_-]+", "-", str(value or "").strip())
    return value.strip("-") or "image"


def product_names(payload: dict[str, Any]) -> dict[str, str]:
    return {
        str(row.get("key")): str(row.get("name") or row.get("key"))
        for row in payload.get("products") or []
        if row.get("key")
    }


def relative_exists(relative: str, root: Path = ROOT) -> bool:
    if not relative or not relative.startswith("assets/insurance/"):
        return False
    path = (root / relative).resolve()
    try:
        path.relative_to((root / "assets/insurance").resolve())
    except ValueError:
        return False
    return path.is_file()


def status_for(row: dict[str, Any], previous: dict[str, Any], root: Path = ROOT) -> str:
    """현재 파일과 이전 대기열 상태를 합쳐 안전한 상태를 결정한다."""
    asset = str(row.get("asset") or "")
    if previous.get("status") == "failed" and not previous.get("asset_path_exists"):
        return "failed"
    if row.get("generation_required") or row.get("reference_only"):
        # 기존 원본은 스타일 참고일 뿐, 실제 생성 완료로 간주하지 않는다.
        if previous.get("status") in {"generated", "approved"} and previous.get("asset_path_exists"):
            return "generated"
        return "pending"
    return "ready" if relative_exists(asset, root) else "pending"


def build_queue(root: Path = ROOT, plan_path: Path = PLAN_PATH,
                queue_path: Path = QUEUE_PATH) -> dict[str, Any]:
    plan = read_json(plan_path, {})
    previous_payload = read_json(queue_path, {})
    previous = {
        str(item.get("queue_id")): item
        for item in previous_payload.get("items") or []
        if item.get("queue_id")
    }
    names = product_names(read_json(root / "data/products.json", {}))
    items: list[dict[str, Any]] = []
    planning_month = str(plan.get("planning_month") or "")[:7]
    for product in plan.get("products") or []:
        product_key = str(product.get("product_key") or "")
        if not product_key:
            continue
        product_month = str(product.get("month") or planning_month)[:7]
        for index, row in enumerate(product.get("image_directions") or [], 1):
            proposal_id = str(row.get("proposal_id") or f"{product_key}-{product_month}-{index:02d}")
            queue_id = f"{safe(product_key)}-{safe(product_month)}-{safe(proposal_id)}"
            prior = previous.get(queue_id) or {}
            reference_asset = str(row.get("asset") or "")
            expected_name = f"{safe(product_key)}-{safe(product_month)}-{index:02d}.png"
            expected_asset = f"assets/insurance/generated/{expected_name}"
            expected_exists = relative_exists(expected_asset, root)
            status = status_for(row, {**prior, "asset_path_exists": expected_exists}, root)
            # 계획에 이미 생성 경로가 커밋된 경우도 '승인 원본'이 아니라
            # 실제 생성 완료로 표시한다. 그래야 Admin에서 운영자가 새 파일을
            # 즉시 식별하고, 월간 큐 재실행에도 상태가 되돌아가지 않는다.
            if expected_exists and reference_asset == expected_asset:
                status = "generated"
            elif expected_exists and status == "pending":
                status = "generated"
            items.append({
                "queue_id": queue_id,
                "product_key": product_key,
                "product_name": names.get(product_key, str(product.get("keyword") or product_key)),
                "planning_month": product_month,
                "slot": index,
                "role": row.get("role") or "썸네일",
                "proposal_id": proposal_id,
                "concept_id": row.get("concept_id") or "",
                "status": status,
                "asset_path": expected_asset,
                "reference_asset": reference_asset,
                "reference_only": bool(row.get("reference_only") or row.get("generation_required")),
                "scene": row.get("scene") or "",
                "prompt": row.get("generation_brief") or "",
                "style_family": row.get("style_family") or "premium_3d_animation_v4",
                "text_overlay": False,
                "spec": {"width": 214, "height": 214, "format": "png", "max_bytes": 5 * 1024 * 1024},
                "reason": (
                    "실제 생성 API가 연결되지 않아 브리프만 저장됨"
                    if status == "pending" and not reference_asset
                    else "전월 원본은 스타일 참고용이며 새 이미지가 필요함"
                    if status == "pending"
                    else "생성 파일 확인"
                    if status == "generated"
                    else "승인 라이브러리 원본 확인"
                ),
                "attempts": int(prior.get("attempts") or 0),
                "last_error": prior.get("last_error") or "",
            })
    summary = {
        "total": len(items),
        "pending": sum(row["status"] == "pending" for row in items),
        "generated": sum(row["status"] == "generated" for row in items),
        "ready": sum(row["status"] == "ready" for row in items),
        "failed": sum(row["status"] == "failed" for row in items),
    }
    payload = {
        "_comment": "실제 이미지 API는 명시적 실행에서만 호출한다. PNG가 확인된 항목만 계획의 asset으로 승격한다.",
        "schema_version": 1,
        "planning_month": planning_month,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": "data/adcopy/serp-candidates.json",
        "provider": previous_payload.get("provider") or "not_configured",
        "status_contract": ["pending", "generated", "ready", "failed"],
        "summary": summary,
        "items": items,
    }
    if previous_payload.get("provider_model"):
        payload["provider_model"] = previous_payload["provider_model"]
    if previous_payload.get("provider_configured_at"):
        payload["provider_configured_at"] = previous_payload["provider_configured_at"]
    write_json(queue_path, payload)
    return payload


def sync_generated_assets(root: Path = ROOT, plan_path: Path = PLAN_PATH,
                          queue_path: Path = QUEUE_PATH) -> int:
    """실제 PNG가 존재하는 generated 항목만 월간 계획에 반영한다."""
    plan = read_json(plan_path, {})
    queue = read_json(queue_path, {})
    by_proposal = {
        str(item.get("proposal_id")): item
        for item in queue.get("items") or []
        if item.get("proposal_id")
    }
    changed = 0
    for product in plan.get("products") or []:
        for row in product.get("image_directions") or []:
            item = by_proposal.get(str(row.get("proposal_id") or ""))
            asset_path = str(item.get("asset_path") or "") if item else ""
            if not item or item.get("status") not in {"generated", "approved"} or not relative_exists(asset_path, root):
                continue
            if row.get("asset") != asset_path or row.get("generation_required") or row.get("reference_only"):
                row["asset"] = asset_path
                row["generation_required"] = False
                row["reference_only"] = False
                row["reused_from_previous_month"] = False
                row["refresh_action"] = "use_generated_asset"
                changed += 1
    if changed:
        write_json(plan_path, plan)
    return changed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sync", action="store_true", help="확인된 생성 PNG를 계획에 반영")
    parser.add_argument("--validate", action="store_true", help="대기열을 만들고 상태 요약만 출력")
    args = parser.parse_args()
    payload = build_queue()
    synced = sync_generated_assets() if args.sync else 0
    print(
        f"[OK] 이미지 생성 큐 {payload['summary']['total']}건 · "
        f"대기 {payload['summary']['pending']} · 생성완료 {payload['summary']['generated']} · "
        f"승인원본 {payload['summary']['ready']} · 실패 {payload['summary']['failed']}"
        + (f" · 계획 반영 {synced}건" if args.sync else "")
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
