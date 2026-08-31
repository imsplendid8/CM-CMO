# 추천 피드백·평가 루프

## 원칙

- 공개 GitHub Pages, 공개 JSON, 브라우저 `localStorage`에는 채택·반려·성과 데이터를 저장하지 않는다.
- 원문 카피는 전송하지 않고 SHA-256 지문과 추천 ID를 기본 키로 사용한다.
- 피드백 API는 Cloudflare Access 또는 사내 인증 뒤에 두고, 인증된 사용자만 기록할 수 있어야 한다.
- 광고 성과는 개인·영업비밀을 제거한 집계 데이터만 연결한다.

## 이벤트

`shared/feedback-client.js`는 다음 이벤트를 `/v1/feedback`으로 보낼 수 있다.

- `copied`: 문구 복사
- `accepted`: 운영 후보 채택
- `edit_requested`: 수정 필요
- `rejected`: 반려

엔드포인트가 설정되지 않으면 네트워크 요청이나 로컬 저장 없이 명시적으로 비활성 상태를 반환한다. 화면은 이를 “피드백 저장소 미연결”로 표시한다.

## 저장소

`docs/feedback-schema.sql`을 비공개 Cloudflare D1 또는 사내 DB에 적용한다. 실제 연결 전 필요한 의사결정은 다음과 같다.

1. Cloudflare Access 사용자 식별자를 일방향 해시한 `actor_hash` 규칙
2. 추천 ID와 실제 캠페인·소재 ID를 연결하는 비공개 매핑
3. 보존 기간과 삭제 정책
4. 성과 데이터 반출·집계 기준

### Cloudflare Worker 연결 순서

Worker 코드는 `/v1/feedback` 경로를 포함하지만, D1과 Access가 연결되기 전에는
저장을 시도하지 않고 `503`으로 닫힌다. 따라서 공개 Pages에 실수로 검수 이력이
노출되지 않는다.

1. `wrangler d1 create modooflow-feedback`으로 D1을 만든다.
2. `docs/feedback-schema.sql`을 원격 D1에 적용한다.
   `wrangler d1 execute modooflow-feedback --remote --file docs/feedback-schema.sql`
3. `proxy/wrangler.toml`의 `[[d1_databases]]`에서 `FEEDBACK_DB` 바인딩과
   `database_id`를 설정한다.
4. `wrangler secret put ACTOR_HASH_SALT`로 32바이트 이상 무작위 salt를
   등록한다. 이메일은 저장하지 않고 이 salt와 결합한 SHA-256 `actor_hash`만
   기록한다.
5. Cloudflare Access에서 `/v1/feedback`을 사내 계정으로 제한한다. Worker는
   `Cf-Access-Authenticated-User-Email`과 `Cf-Access-Jwt-Assertion`이 모두
   있을 때만 이벤트를 저장한다.
6. Worker를 배포한 뒤 브라우저에서 `shared/feedback-client.js`의 저장 상태를
   확인한다. D1 바인딩 누락은 `503`, Access 헤더 누락은 `401`, 원문 `text`를
   전송한 요청은 `400`이어야 한다.

현재 공개 Pages의 `modoo-feedback-endpoint` 메타 값은 비워 둔다. Worker 배포와
Access 정책을 확인하기 전에 브라우저 요청을 활성화하면 사용자는 저장 실패를
반복해서 보게 되기 때문이다. 외부 설정 검증이 끝난 뒤에만 해당 메타 값에 Worker
URL을 넣고 `Access-Control-Allow-Credentials` 동작을 확인한다.

### 전송 계약

피드백 요청은 `action`, `tool`, `productKey`, `recommendationId`와 같은 식별자,
선택적인 `sourceVersion`, `reviewStatus`, `editDistance`, `metadata`만 보낸다.
카피 원문이나 `metadata.text`는 허용하지 않으며, 원문을 대조해야 할 때는
클라이언트에서 계산한 64자리 SHA-256 `textFingerprint`만 사용한다. Worker는
필드 길이와 메타데이터 8KB 상한을 검사하고, IP별 일일 피드백 요청도 200건으로
제한한다.

## 평가

- 채택률 = `accepted / 노출된 추천`
- 수정 요청률과 반려율
- 원문 대비 최종 카피 편집 거리
- 상품·사건 유형별 채택률
- 채택 추천의 CTR·전환율·비용 성과

성과 지표는 충분한 표본과 대조군이 있을 때만 추천 품질 개선에 사용한다.
