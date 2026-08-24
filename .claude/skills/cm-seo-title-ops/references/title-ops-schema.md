# 제목 운영 산출물 스키마

`data/seo/title-opportunities.json`은 정적 관리자 화면에 배포 가능한 공개 요약이다.

## 최상위 필드

- `asof`: 입력 데이터 가운데 가장 최근 기준일
- `method_version`: 생성 규칙 버전
- `sources.searchad`: `connected` 또는 `missing`
- `sources.gsc`: `verified_privately`, `not_connected`, `stale` 중 하나
- `products`: 상품별 제목 운영 결과

## 상품 필드

- `status`: `ready_for_review` 또는 `blocked_gsc`
- `authority_band`: `not_checked`, `low`, `growing`, `established`
- `recommended_candidate_id`: 비공개 GSC 검증 후 선택된 후보 ID. 미연결이면 `null`
- `candidates`: 상황형·상품형·범위 제한형 3개

## 후보 필드

- `target_query`, `search_demand`, `competition`: 공개 SearchAd 근거
- `query_tier`: `head`, `body`, `tail`
- `gsc_status`: `not_connected`, `no_signal`, `top3`, `striking_distance`, `low_visibility`, `cannibalization_detected`
- `decision`: `recommended`, `review_only`, `rejected_cannibalization`
- `weakness`: 선택 시 감수할 손실 또는 본문 조건
- `review_status`: 항상 `human_review_required`

## 공개 금지 필드

원본 GSC 검색어 행, 페이지 URL, 클릭, 노출, CTR, 평균순위, OAuth/API 자격증명을 이 파일에 추가하지 않는다. 검증 결과는 범주값으로만 공개한다.
