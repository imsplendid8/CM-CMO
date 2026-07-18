# CM-CMO · 장기CM 테크니컬 SEO(Technical SEO) 콘솔

한화손해보험 다이렉트 **CM사업부 장기CM** 담당 상품 페이지의 **테크니컬 SEO** 진단 → 개발 실행 To-Do를 한 화면에서 다루는 자체완결 웹 콘솔입니다. 컨설팅 리포트가 아니라 **현행 화면 실측 → 할 일 → before/after 코드 → 완료 체크**로 SEO 개발자가 바로 착수하도록 만든 실행 보드입니다.

> **범위는 순수 테크니컬 SEO** — 제목/메타/OG 태그, H 구조, canonical, hreflang/모바일 alternate, 구조화 데이터(JSON-LD), robots/sitemap, **분기(리다이렉트) 처리** 등 크롤·색인·마크업 레이어. 콘텐츠 마케팅·백링크 등은 범위 외.

- 단일 HTML · 외부 의존성 0 · 라이트/다크 · 서버 불필요 (`index.html`을 열면 동작)
- 데이터: 네이버 웹문서 색인 실측(2026-07-18). 라이브 DOM(H·alt·OG)은 대상 사이트 봇차단(HTTP 403)으로 미수집 → 실측 확정 필요.

## 상단 3토글 구성

| 토글 | 내용 |
|---|---|
| **장기 (7)** | 주택화재·골프·암·치아(한화 다이렉트 직접) / 운전자·여성건강·임신출산(캐롯 분기) |
| **일반 (1)** | 해외여행(캐롯 분기) |
| **범용 PRO** | 아무 URL의 크롤링 값 입력 → 점수·To-Do·코드·카피 자동생성 |

+ **다이렉트 홈(메인 태그)** 은 양쪽 토글에 고정 노출. TM·오프라인·자동차 등 담당 외 상품은 제외.

### 분기(carrotBridge) 처리 — 이 솔루션의 핵심 테크니컬 이슈
`m.hanwhadirect.com/cmcom/carrotBridge.do?carrot=…` 는 **캐롯으로 URL이 분기(리다이렉트)** 되는 페이지입니다. 실측상 브릿지 자체는 색인 자산이 거의 없고(전체 55건) **랭킹·링크에쿼티를 캐롯이 가져갑니다.** 각 브릿지 상품에 최우선 To-Do로 `301 + canonical` 통일, `campaignId` 파라미터 중복 정리, 또는 CM이 직접 랭킹을 확보할 콘텐츠 랜딩 신설을 제시합니다.

## 오픈소스 적용 (추천 파이프라인)

**unlighthouse(실측 크롤) → 이 콘솔(진단·To-Do·카피) → next-seo · schema-dts(적용)**

| 도구 | 용도 | 라이선스 |
|---|---|---|
| [harlan-zw/unlighthouse](https://github.com/harlan-zw/unlighthouse) | 담당 라우트 전체 테크니컬 SEO 크롤(title·meta·image-alt·heading). 결과 JSON을 PRO에 붙여넣으면 폼 자동 프리필 | MIT |
| [garmeeh/next-seo](https://github.com/garmeeh/next-seo) | After 카피 → `<NextSeo>` 설정 코드 생성 | MIT |
| [google/schema-dts](https://github.com/google/schema-dts) | Product·FAQPage **JSON-LD** 생성·타입검증 | Apache-2.0 |

### 바로 실행되는 적용 파일 (이 저장소에 포함)
| 파일 | 설명 |
|---|---|
| `unlighthouse.config.ts` | **담당 URL만** 크롤하도록 구성된 unlighthouse 설정(모바일·SEO 카테고리). `npx unlighthouse --config-file unlighthouse.config.ts` |
| `.github/workflows/technical-seo.yml` | 매월/수동으로 unlighthouse CI 실행 → 리포트 아티팩트 저장 (SEO 회귀 감지) |

크롤 결과 JSON을 **범용 PRO 탭 → "⚡ 크롤러 결과 불러오기"** 에 붙여넣으면 진단·To-Do가 자동 생성됩니다. Lighthouse 원본(`audits` 포함) JSON도 그대로 인식(`image-alt`·`meta-description` 감사 사용).

## 파일

| 파일 | 역할 |
|---|---|
| `index.html` | 배포/Pages용 전체 문서(모바일 viewport) |
| `seo-audit.html` | 동일 콘텐츠 프래그먼트본 |
| `unlighthouse.config.ts` · `.github/workflows/technical-seo.yml` | 적용형 테크니컬 SEO 자산 |

## 바로 보기

- **GitHub Pages**: Settings → Pages → Source: *Deploy from a branch* → Branch `main`, 폴더 **`/(root)`** → Save → `https://imsplendid8.github.io/CM-CMO/`
  - `/(root)` = 저장소 최상위에 있는 `index.html`을 사이트로 사용한다는 뜻.
- **즉시(설정 불필요)**: `https://htmlpreview.github.io/?https://github.com/imsplendid8/CM-CMO/blob/main/index.html`

## 유의
- 추천 카피는 광고심의 준수 초안(과장표현 배제) — 배포 전 보험협회 광고심의 검수 필요.
- 점수는 6개 축(제목·메타·시맨틱·URL·소셜·신뢰도) 가중 추정값으로 실제 순위를 보장하지 않습니다.
- 데이터·카피는 샘플·공개값 기준(개인정보·영업비밀 미포함).
