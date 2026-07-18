# CM-CMO · 장기보험 SEO To-Do 콘솔

손해보험 다이렉트(CM) 장기상품 페이지의 **테크니컬 SEO 진단 → 개발 실행 To-Do**를 한 화면에서 다루는 자체완결 웹 콘솔입니다. 컨설팅 리포트가 아니라, **현행 화면 실측값 → 할 일 → before/after 코드 → 완료 체크**로 개발자가 바로 착수할 수 있게 만든 실행 보드입니다.

- 단일 HTML · 외부 의존성 0 · 라이트/다크 대응 · 서버 불필요 (`index.html`을 브라우저로 열면 동작)
- 데이터: 네이버 웹문서 색인 실측(2026-07-18) + 데이터랩 검색수요. 라이브 DOM(H·alt·OG)은 대상 사이트 봇차단(HTTP 403)으로 미수집 → 실측 확정 필요.

## 두 가지 모드

| 모드 | 내용 |
|---|---|
| **한화 장기CM** | 실측 6개 화면 고정 진단 — 주택화재·암·치아·골프(hanwhadirect.com), 여성건강·운전자(carrotins.com). 화면별 현재 Title/Description(실측) → 우선순위 To-Do(제목·메타·OG·H1·alt) → 코드 → 완료 체크(localStorage) |
| **범용 SEO 솔루션 `PRO`** | 아무 상품 페이지의 크롤링 값을 입력하면 점수·To-Do·코드·검색엔진별 카피를 자동 생성. 어떤 회사/상품에도 재사용 |

## 오픈소스 연동 (추천 파이프라인)

**unlighthouse(실측 크롤) → 이 콘솔(진단·To-Do·카피) → next-seo · schema-dts(실제 적용)**

| 도구 | 용도 | 라이선스 |
|---|---|---|
| [harlan-zw/unlighthouse](https://github.com/harlan-zw/unlighthouse) | 사이트 전 페이지 Lighthouse 크롤 → title·meta·**image-alt·heading** 실측. PRO 모드에서 결과 JSON을 붙여넣으면 폼 자동 프리필. 적용 후 재검증 커맨드도 각 화면에 생성 | MIT |
| [garmeeh/next-seo](https://github.com/garmeeh/next-seo) | After 카피를 `<NextSeo>` 설정 코드로 생성 (Next.js) | MIT |
| [google/schema-dts](https://github.com/google/schema-dts) | Product·FAQPage **JSON-LD** 생성 + 타입 검증 | Apache-2.0 |
| [sethblack/python-seo-analyzer](https://github.com/sethblack/python-seo-analyzer) | (대안) 서버사이드 크롤러로 403 우회, 동일 JSON 포맷으로 프리필 | MIT |

> 위 저장소는 각 원저작자/라이선스에 귀속됩니다. 본 콘솔은 산출물(JSON) 연동과 코드 생성만 수행하며 소스를 포함하지 않습니다.

### PRO 모드 입력 JSON 예시
```json
{ "url": "https://example.com/product",
  "title": "현재 <title> 값",
  "description": "현재 meta description",
  "h1Count": 1,
  "ogPresent": false,
  "imagesMissingAlt": 7 }
```
Lighthouse/unlighthouse 원본(`audits` 키 포함) JSON도 그대로 인식합니다(`image-alt`·`meta-description` 감사 항목 사용).

## 파일

| 파일 | 역할 |
|---|---|
| `index.html` | 배포/Pages용 전체 문서 (모바일 viewport 포함) |
| `seo-audit.html` | 동일 콘텐츠 프래그먼트본 |

## 보기

GitHub Pages: **Settings → Pages → Deploy from a branch → `main` / `(root)`** → `https://imsplendid8.github.io/CM-CMO/`

## 유의

- 추천 카피는 **광고심의 준수 초안**(과장표현 배제) — 배포 전 보험협회 광고심의 검수 필요.
- 점수는 6개 축(제목·메타·시맨틱·URL·소셜·신뢰도)에 구글/네이버 가중치를 적용한 추정값이며 실제 검색 순위를 보장하지 않습니다.
- 데이터·카피는 모두 샘플·공개값 기준(개인정보·영업비밀 미포함).
