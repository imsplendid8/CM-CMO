#!/usr/bin/env python3
"""첨부 소재생성가이드의 공개 가능한 규칙이 산출물에 적용됐는지 검사한다.

이 검사는 심의 승인 판정이 아니다. 가이드 버전·필수 메타데이터·상품별
소재 슬롯·이미지 중복만 확인하고, 보험료·혜택·지급 여부는 사람 검토로 남긴다.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GUIDE = ROOT / "data/adcopy/material-generation-guide.json"
OUTPUT = ROOT / "data/adcopy/serp-candidates.json"


def main() -> int:
    guide = json.loads(GUIDE.read_text(encoding="utf-8"))
    output = json.loads(OUTPUT.read_text(encoding="utf-8"))
    if guide.get("schema_version") != 1:
        raise SystemExit("guide schema_version must be 1")
    version = guide.get("guide_version")
    if output.get("guide_basis", {}).get("guide_version") != version:
        raise SystemExit("산출물과 가이드 버전이 다릅니다")
    required = set(guide.get("quality_gate", {}).get("required_for_every_material") or [])
    if not required:
        raise SystemExit("quality_gate.required_for_every_material이 비어 있습니다")
    for product in output.get("products") or []:
        key = product.get("product_key")
        if len(product.get("sa_recommendations") or []) != 3:
            raise SystemExit(f"{key}: SA 3안이 아닙니다")
        if len(product.get("power_content_topics") or []) != 3:
            raise SystemExit(f"{key}: 파워콘텐츠 3안이 아닙니다")
        images = product.get("image_directions") or []
        if len(images) != 4 or len({row.get("asset") for row in images}) != 4:
            raise SystemExit(f"{key}: 이미지 4슬롯 또는 원본 중복 오류")
        qa = product.get("quality_assurance") or {}
        if not required.issubset(set(qa.get("required_checks") or [])):
            raise SystemExit(f"{key}: 필수 품질 게이트 메타데이터 누락")
        if qa.get("status") != "ready_for_human_review":
            raise SystemExit(f"{key}: 사람 검토 준비 상태가 아닙니다")
        if any(not row.get("guide_pattern_id") for row in product.get("sa_recommendations") or []):
            raise SystemExit(f"{key}: SA 가이드 문구 구조 누락")
        if any(not row.get("guide_pattern_id") for row in product.get("power_content_topics") or []):
            raise SystemExit(f"{key}: 파워콘텐츠 가이드 문구 구조 누락")
        if any(row.get("text_overlay") is not False for row in images):
            raise SystemExit(f"{key}: 텍스트 없는 이미지 규칙 누락")
    print(f"OK  소재생성가이드 {version} · 상품 {len(output.get('products') or [])} · SA/파워콘텐츠/썸네일 게이트")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
