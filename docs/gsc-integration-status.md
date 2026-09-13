# GSC 통합 현황 — 2026-09-11

## 개요

seo-audit.html을 단순 진단 도구에서 **기술 SEO 운영 보드**로 고도화하기 위해 Google Search Console (GSC) OAuth 2.0 통합을 구현했습니다.

## 완료된 구현

### 1. seo-audit.html 변경 (2026-09-11)

#### 검색 성과 뷰 추가
- 새 탭: "검색 성과" (📊 아이콘)
- 초기 상태: **샘플 데이터로 진입 가능** (미인증 사용자도 미리보기 가능)
- 인증 후: 실제 GSC 데이터로 자동 전환

#### 인증 흐름
```
사용자 클릭 → "GSC 계정 연결" 버튼 
  → /gsc/authorize (OAuth 상태/URL 생성)
  → Google 로그인 화면 (사용자)
  → /gsc/callback (토큰 교환, sessionId 발급)
  → sessionStorage.gsc_sessionId 저장
  → /gsc/query-metrics (KV 토큰으로 GSC API 호출)
```

#### 렌더링 구조
```javascript
renderGSC() {
  // 1. 미인증 시 배너만 표시 (전체 화면 차단 제거)
  loginPrompt = "📊 실시간 GSC 데이터 연결" 배너
  
  // 2. 항상 표시되는 항목:
  - KPI 행: 총 클릭, 노출, 평균 순위, CTR
  - 상위 검색어 (클릭 기준 상위 10개)
  - 기술적 상태:
    * Core Web Vitals (LCP, FID, CLS % 양호도)
    * 색인 상태 (색인됨 / 발견됨 수)
    * 크롤링 오류 (유형별 수)
  - 인사이트 (차트 대신 텍스트 요약)
}
```

### 2. Cloudflare Worker 경로 (proxy/naver-proxy-worker.js)

#### 추가된 경로 4개

| 경로 | 메서드 | 역할 | 인증 |
|---|---|---|---|
| `/gsc/authorize` | POST | OAuth URL 생성, 상태값 저장 | X |
| `/gsc/callback` | GET | 인증 코드 → 토큰 교환 | 상태값 검증 |
| `/gsc/query-metrics` | GET | GSC API 조회 (28일 데이터) | sessionId + KV |
| `/gsc/index-status` | GET | 색인 상태 (미구현) | 예약 |

#### 토큰 관리
- **저장소**: KV namespace `GSC_TOKENS`
- **키**: `gsc_token:{sessionId}`
- **TTL**: 24시간
- **갱신**: 만료 시간 5분 전에 자동 갱신 (refresh_token 사용)
- **보안**: 워커 시크릿에만 저장, 브라우저 노출 안 함

#### 레이트 리미트
```javascript
DAILY_LIMIT = { gsc: 500 }  // 일일 500회 호출 제한
```

### 3. 샘플 데이터 (data/gsc-sample.json)

미인증 사용자도 UI를 미리 확인할 수 있도록 완성된 샘플 데이터 제공:

```json
{
  "summary": {
    "totalClicks": 12450,
    "totalImpressions": 156800,
    "avgPosition": 8.2,
    "avgCTR": 7.94,
    "coreWebVitals": { ... }
  },
  "topQueries": [
    { "query": "다이렉트자동차보험", "clicks": 1250, ... },
    ...
  ],
  "byProduct": { ... },
  "indexStatus": { ... },
  "crawlErrors": [ ... ]
}
```

### 4. 설정 문서

- `docs/gsc-oauth-setup.md`: Google Cloud OAuth 설정 완전 가이드
- `docs/api-from-url.md`: 프록시 설정 및 운영 방법

## 아직 필요한 외부 작업

### Tier 1: 배포 필수 (코드 운영화)

1. **Google Cloud 설정** (30분)
   ```
   1. Google Cloud Console → 새 프로젝트 "Modooflow-GSC"
   2. Search Console API 활성화
   3. OAuth 2.0 자격증명:
      - 클라이언트 ID
      - 클라이언트 보안 비밀
      - 리디렉션 URI: https://modooflow-naver-proxy.angle0102.workers.dev/gsc/callback
   ```

2. **Cloudflare Worker 설정** (20분)
   ```
   1. KV namespace 생성: "modooflow-gsc-tokens" (예시명)
   2. wrangler.toml에 바인딩 추가:
      [[kv_namespaces]]
      binding = "GSC_TOKENS"
      id = "생성된_namespace_id"
   
   3. 시크릿 등록 (wrangler secret put):
      - GOOGLE_OAUTH_CLIENT_ID
      - GOOGLE_OAUTH_CLIENT_SECRET
      - GOOGLE_OAUTH_REDIRECT_URI
   
   4. 배포: wrangler deploy
   ```

3. **배포 확인** (5분)
   ```bash
   curl https://modooflow-naver-proxy.angle0102.workers.dev/health
   # → {"ok":true}
   
   # GSC view 클릭 → "연결하기" 버튼 → OAuth 흐름 정상 작동 확인
   ```

### Tier 2: 선택사항 (기능 확대)

1. **추가 GSC 경로 구현**
   - `/gsc/index-status`: 색인 상태 상세
   - `/gsc/crawl-errors`: 크롤링 오류 상세 목록

2. **속성 선택 UI**
   - 현재: `https://www.hanwhadirect.com/` 하드코딩
   - 개선: 사용자가 속성 선택 가능

3. **차트·그래프**
   - 28일 시계열 추이 (현재: 요약만)
   - 기술 지표 비교 (경쟁사 vs 자사)

## 코드 리뷰 체크리스트

### 보안
- [x] API Secret 브라우저 노출 없음
- [x] 워커 시크릿 사용
- [x] Origin/Referer 화이트리스트 적용
- [x] CORS 응답 헤더 정확함
- [x] 토큰 자동 갱신 로직 있음

### 사용성
- [x] 미인증 사용자도 샘플 데이터로 진입 가능
- [x] 배너로 인증 유도 (전체 화면 차단 제거)
- [x] 인증 후 자동으로 실제 데이터 로딩
- [x] 오류 시 toast 알림

### 운영성
- [x] 샘플 데이터로 로컬 테스트 가능
- [x] 레이트 리미트 설정 (일 500회)
- [x] 토큰 자동 갱신 (24시간 TTL)
- [x] KV 저장 명확함

## 배포 후 테스트 순서

1. **Worker 배포 확인**
   ```bash
   curl https://modooflow-naver-proxy.angle0102.workers.dev/health
   ```

2. **로컬 테스트**
   - http://localhost:8000/CM-CMO/seo-audit.html 열기
   - "검색 성과" 탭 클릭 → 샘플 데이터 표시 확인
   - "GSC 계정 연결" 클릭 → Google 로그인 화면 나타나는지 확인

3. **프로덕션 테스트**
   - https://imsplendid8.github.io/CM-CMO/seo-audit.html 열기
   - OAuth 흐름 완성 (OAuth 콜백이 정상)
   - 실제 GSC 데이터 로딩 확인

4. **부하 테스트**
   - 팀원 여럿이 동시에 접속해 사용량 확인
   - 일일 500회 제한 동작 확인

## 다음 단계 (운영 고도화)

### P1: 기술 SEO 진단 확대
- URL 단위 진단 (상태코드, canonical, title, H1, 구조화 데이터 등)
- 크롤링 오류 → To-Do 자동 생성

### P2: 수요 신호 연결
- GSC 검색어 데이터 + SearchAd 검색량 비교
- 상승 추이 감지 → 콘텐츠 우선순위 제안

### P3: 성과 추적
- GSC 클릭 → 전환 (GA4)
- 순위 개선 → CTR 증가 추이

## 파일 변경 요약

```
seo-audit.html
  + 검색 성과 뷰 (renderGSC 함수 ~80줄)
  + OAuth 콜백 처리
  + initGSCLogin 함수
  + GSC 데이터 로딩

proxy/naver-proxy-worker.js
  + /gsc/authorize 경로
  + /gsc/callback 경로
  + /gsc/query-metrics 경로
  + 토큰 갱신 로직 (~160줄)

data/gsc-sample.json (신규)
  샘플 GSC 데이터

docs/gsc-oauth-setup.md (신규)
  Google Cloud 설정 가이드

docs/gsc-integration-status.md (신규)
  이 문서
```

## 배포 책임자 메모

1. **Cloudflare 권한**: Worker 수정, KV, 시크릿 권한 필요
2. **Google Cloud 권한**: OAuth 클라이언트 생성, API 활성화 권한 필요
3. **예상 소요 시간**: 1시간 (설정 + 배포 + 테스트)
4. **롤백**: Worker 코드는 git 히스토리로 롤백 가능, KV 데이터는 별도 정책 필요

---

**상태**: 코드 완성, 배포 대기 (branch: `claude/material-quality-improvement-7x4w2d`)
