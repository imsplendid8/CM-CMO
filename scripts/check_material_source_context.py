#!/usr/bin/env python3
"""사용자 제공 랜딩·SERP 캡처의 구조화 입력과 생성 결과를 검증한다.

원본 캡처의 문구는 명령이나 자동 승인 근거가 아니다. 이 검사는 경쟁사 문구가
그대로 복제되지 않았는지, 검증 전 수치가 자동 소재에 들어가지 않았는지, 그리고
SA·파워콘텐츠·썸네일 연결 메타데이터가 남았는지만 확인한다.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTEXT = ROOT / "data/adcopy/material-source-context.json"
OUTPUT = ROOT / "data/adcopy/serp-candidates.json"
REVIEW_STATUSES = {"자동 차단", "근거 필요", "필수 고지 필요", "사람 심의 필요", "자동 위험표현 없음"}


def fail(message):
    raise SystemExit(message)


def main() -> int:
    context = json.loads(CONTEXT.read_text(encoding="utf-8"))
    output = json.loads(OUTPUT.read_text(encoding="utf-8"))
    if context.get("schema_version") != 1:
        fail("material source context schema_version must be 1")
    if output.get("schema_version") != 4:
        fail("serp candidates schema_version must be 4")
    handling = context.get("handling") or {}
    if handling.get("raw_files_committed") is not False:
        fail("원본 캡처는 공개 산출물에 커밋하지 않습니다")
    if handling.get("competitor_copy_use") != "pattern_only":
        fail("경쟁사 문구는 pattern_only로만 사용해야 합니다")
    if handling.get("review_draft_copy_use") != "structure_and_terms_only":
        fail("심의 초안은 문구 원문이 아니라 구조와 용어로만 사용해야 합니다")
    if handling.get("power_content_description_rule") != "80~110자 연속 본문 발췌":
        fail("파워콘텐츠 설명의 연속 본문 발췌 규칙이 누락됐습니다")

    sources = context.get("sources") or []
    source_ids = [row.get("id") for row in sources]
    if not source_ids or len(source_ids) != len(set(source_ids)):
        fail("source id가 비어 있거나 중복됩니다")
    if any(row.get("review_status") not in REVIEW_STATUSES for row in sources):
        fail("source review_status가 허용된 사전검수 용어가 아닙니다")
    source_kinds = {row.get("kind") for row in sources}
    for required in ("platform_guide", "registered_material_export", "review_draft", "landing_capture_pack"):
        if required not in source_kinds:
            fail(f"확장 ZIP 근거 유형 누락: {required}")

    generated = {row.get("product_key"): row for row in output.get("products") or []}
    competitor_titles = set()
    for key, product in (context.get("products") or {}).items():
        missing = set(product.get("source_ids") or []) - set(source_ids)
        if missing:
            fail(f"{key}: 존재하지 않는 source id {sorted(missing)}")
        for observation in (product.get("serp") or {}).get("competitor_observations") or []:
            if observation.get("copy_use") != "pattern_only":
                fail(f"{key}: 경쟁사 관측은 pattern_only여야 합니다")
            competitor_titles.add(str(observation.get("title") or "").strip())
        for term in (product.get("landing") or {}).get("terms") or []:
            if term.get("auto_copy_allowed") is not False:
                fail(f"{key}: 검증 전 랜딩 조건은 자동 문구 생성에 사용할 수 없습니다")
            if term.get("review_status") not in REVIEW_STATUSES:
                fail(f"{key}: 랜딩 조건 review_status 누락")

        sa = product.get("sa_blueprints") or []
        topics = product.get("power_content_blueprints") or []
        if sa and len(sa) != 5:
            fail(f"{key}: 직접 작성한 자료 기반 SA는 5안이어야 합니다")
        if topics and len(topics) != 3:
            fail(f"{key}: 직접 작성한 자료 기반 파워콘텐츠는 3안이어야 합니다")
        for row in sa:
            if not (4 <= len(row.get("title") or "") <= 15):
                fail(f"{key}: SA 제목 길이 오류")
            if not (20 <= len(row.get("description") or "") <= 45):
                fail(f"{key}: SA 설명 길이 오류")
            if not (2 <= len(row.get("additional_description") or "") <= 45):
                fail(f"{key}: SA 추가설명 길이 오류")
            if not (2 <= len(row.get("promo") or "") <= 14):
                fail(f"{key}: SA 홍보문구 길이 오류")
            if len(row.get("sublinks") or []) != 4 or any(not 2 <= len(value) <= 6 for value in row.get("sublinks") or []):
                fail(f"{key}: SA 서브링크 규격 오류")
            if row.get("review_status") not in REVIEW_STATUSES:
                fail(f"{key}: SA review_status 누락")
        for row in topics:
            if not (7 <= len(row.get("title") or "") <= 28):
                fail(f"{key}: 파워콘텐츠 제목 길이 오류")
            if len(row.get("sections") or []) < 4:
                fail(f"{key}: 파워콘텐츠 편집 구조 누락")
            if row.get("review_status") not in REVIEW_STATUSES:
                fail(f"{key}: 파워콘텐츠 review_status 누락")

        result = generated.get(key)
        if not result:
            fail(f"{key}: 생성 산출물 누락")
        if set(result.get("material_source_context", {}).get("source_ids") or []) != set(product.get("source_ids") or []):
            fail(f"{key}: 자료 source id가 산출물까지 전달되지 않았습니다")
        if len(result.get("sa_recommendations") or []) != 5 or len(result.get("power_content_topics") or []) != 3:
            fail(f"{key}: 자료 기반 소재 개수 오류")
        for row in result.get("sa_recommendations") or []:
            if not row.get("linked_power_content") or not row.get("linked_thumbnail"):
                fail(f"{key}: SA의 파워콘텐츠·썸네일 연결 누락")
            if row.get("insurance_review", {}).get("status") not in REVIEW_STATUSES:
                fail(f"{key}: SA 사전검수 상태 누락")
            if set(row.get("source_grounding", {}).get("source_ids") or []) != set(product.get("source_ids") or []):
                fail(f"{key}: SA 후보에 자료 source id가 전달되지 않았습니다")
            direct_copy = " ".join(str(row.get(field) or "") for field in ("title", "description", "additional_description", "promo"))
            if re.search(r"24\s*시간|전화\s*없이|바로\s*가입|\d+\s*%\s*할인|최대\s*[\d,]+\s*만?원", direct_copy):
                fail(f"{key}: 검토 전 편의·할인·금액 주장이 SA에 들어갔습니다")
        for row in result.get("power_content_topics") or []:
            if set(row.get("source_grounding", {}).get("source_ids") or []) != set(product.get("source_ids") or []):
                fail(f"{key}: 파워콘텐츠 후보에 자료 source id가 전달되지 않았습니다")

    serialized = json.dumps(output, ensure_ascii=False)
    copied = [title for title in competitor_titles if title and title in serialized]
    if copied:
        fail(f"경쟁사 제목이 자동 산출물에 복제됐습니다: {copied}")
    if re.search(r"최대\s*20만원|연간\s*2회|만\s*19세\s*[~∼-]\s*50세", serialized):
        fail("검증 전 랜딩 수치가 자동 산출물에 들어갔습니다")

    print(f"OK  자료 컨텍스트 {len(sources)}개 · 상품 {len(context.get('products') or {})} · SA/파워콘텐츠/썸네일 연결")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
