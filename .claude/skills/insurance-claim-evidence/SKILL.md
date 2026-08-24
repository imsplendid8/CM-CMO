---
name: insurance-claim-evidence
description: 보험 FAQ·검색광고·랜딩 문구의 상품 근거를 data/evidence/claims.json에서 조회·검증한다. 담보, 가입 대상, 보험료, 할인, 지급조건, 한도, 면책·감액을 쓰거나 문구의 근거 ID·유효기간·채널 허용 여부를 확인할 때 사용한다.
---

# 보험 상품 근거 원장

1. `python scripts/claim_evidence.py validate`를 실행한다.
2. 상품과 채널에 맞는 `review_status=approved` claim만 사용한다.
3. `effective_from` 이전이나 `valid_until` 이후 claim은 사용하지 않는다.
4. `required_disclosure`가 있으면 문구 또는 랜딩 검수 항목에 포함한다.
5. 승인 claim이 없으면 구체적 담보·수치·보험료·가입 가능 답변을 만들지 말고 `product_evidence_required`로 반환한다.
6. Agent가 claim을 승인하거나 reviewer를 대신 입력하지 않는다.

사람이 검토를 마친 뒤에만 `python scripts/claim_evidence.py approve --claim-id ID --reviewer NAME --source-path PATH --effective-from YYYY-MM-DD --channels faq,sa_description` 형식으로 승인한다. 반려는 `reject`와 `--reason`을 사용한다.
저장 전 확인에는 `--dry-run`을 사용한다. 재승인·반려도 기존 `review_history`를 삭제하지 않는다.

스키마는 [references/claims-schema.md](references/claims-schema.md)를 필요할 때 읽는다.
