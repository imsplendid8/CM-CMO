# Review And Copy Guardrails

## Use Review Draft Examples Correctly

Review draft examples show structure, tone, and allowed caution style. They do not automatically approve new claims.

Extract:

- stable field structure;
- sentence length and register;
- acceptable CTA tone;
- how review-sensitive wording is marked;
- which expressions were avoided.

Do not extract:

- old product facts as current facts;
- claim amounts or conditions without current source;
- channel claims such as `전화 없이` or `바로 가입` unless supplied and review-marked.

## News Context

News can explain why a topic is timely. It should not create fear-pressure copy.

Allowed:

- `최근 검색 관심이 커진 배경`
- `계절성 수요를 설명하는 맥락`
- `확인해야 할 항목을 떠올리게 하는 사례`

Avoid:

- sensational incident framing;
- implying the news event is covered;
- `사고가 늘었으니 지금 가입` style urgency.

## Every Line Must Be A Customer Benefit (operator feedback)

Every SA field — title, description, additional description, promotion — must state what the customer gets or a situation they recognize. A line that describes what the landing page will show is not ad copy, even if it is accurate and compliant.

Rejected by the operator as unusable:

- `누수와 풍수재는 보장 조건이 달라 항목별로 나눠 안내해요`
- `보장 한도와 보장하지 않는 경우는 상품설명서에서 안내해요`
- `두 항목의 지급사유와 사고 시점별 적용 조건을 나눠 읽기`
- `확인한 기준일과 최종 선택 내용을 함께 기록`

Use one of three angles instead:

- situation + result: `우리 집 누수로 아랫집에 피해를 줬다면 일상배상책임으로 대비해요`
- benefit: `집 안 누수부터 태풍·호우 피해까지 물로 생긴 손해를 보장해요`
- choice or convenience: `꼭 필요한 특약만 남겨 나에게 맞는 운전자보험을 만들어요`

Do not put guidance or disclosure wording in SA copy: `안내해요`, `알려드려요`, `정리했어요`, `한눈에 비교`, `나눠서`, `약관 기준`, `상품설명서`, `지급 기준/조건`, `보장하지 않는 경우`, `적용 조건`, `읽기`, `대조`, `기록`. Exclusions and limits belong on the landing page and in review, not in the ad line. `scripts/check_material_source_context.py` fails CI on these patterns.

## Prohibited Or Review-Sensitive Copy

Do not use:

- `최저`, `최고`, `1위`, `유일`, `100%`, `무조건`, `완벽`, `확정`;
- `누구나 가입`, `무심사`, `즉시 보장`, `바로 지급`;
- empty reassurance such as `든든`, `안심`, `걱정 끝`;
- generic fear such as `갑작스러운 사고`.

Mark as review needed:

- time claims: `3분`, `즉시`, `바로`;
- channel claims: `전화 없이`, `상담 없이`;
- amount, limit, refund, savings, or price claims;
- terms that depend on current policy wording.
