# OSS 활용안 — Modooflow에 붙인/붙일 오픈소스

> "타인의 레포(OSS)를 활용해 업데이트할 사항" 정리.
> 원칙: **자체완결 정적 앱 유지**(빌드·런타임 의존 0). OSS는 ①폰트/에셋으로 내장하거나 ②GitHub Actions(빌드타임)에서만 쓰고 결과물(이미지·JSON)만 커밋.

## ✅ 지금 반영됨

| OSS | 라이선스 | 용도 | 반영 위치 |
|---|---|---|---|
| **Pretendard** (orioncactus) | SIL OFL 1.1 | 무료 고딕 웹폰트 자체호스팅 → 시스템 폰트 의존 제거 | `fonts/PretendardVariable.woff2`, 전 화면 |
| **Playwright** (microsoft) | Apache-2.0 | 네이버 SERP **자동 스크린샷 캡쳐** | `scripts/capture_serp.mjs`, `.github/workflows/serp-capture.yml` |
| **pixelmatch** 방식 (mapbox) | ISC | 전/후 스크린샷 **시각 diff**(YIQ 픽셀 비교) — 라이브러리 없이 canvas로 내장 구현 | `serp-tool.html` `diffImages()` |
| **Unlighthouse** (harlan-zw) | MIT | Lighthouse 대량 크롤 → SEO 점수 | `unlighthouse.config.ts`, `technical-seo.yml` |
| **advertools** (kw_generate 방식) | MIT | 키워드 시드×수식어 조합 로직 | `keyword-tool.html` |

## 🔜 붙일 만한 후보 (효용순)

1. **shot-scraper 스타일 다중 캡쳐** — 이미 Playwright로 구현했으니, 캡쳐 대상에 **모바일 뷰포트(390px)** 추가 → PC/모바일 SERP 동시 아카이브. `capture_serp.mjs`에 컨텍스트 하나만 추가하면 됨. (저비용·고효용)
2. **resemble.js / odiff** — diff를 더 정교하게(안티앨리어싱 무시, 영역 클러스터링). 현재 자체 pixelmatch로 충분하지만 오탐 많으면 교체 검토.
3. **feedparser + trafilatura** (Actions에서) — 뉴스 원문 본문 추출 품질 개선. 현재 네이버 검색 API 요약으로 충분하면 보류.
4. **Kagi/serpapi 대체는 지양** — 유료·ToS 이슈. 네이버 검색 API + Playwright 자가 캡쳐로 무료 유지.
5. **date-holidays** (npm) — 시즌 캘린더 공휴일 자동화(현재 수동 seasonal.json). Actions 빌드타임에 JSON 생성해 커밋하면 자체완결 유지.

## 원칙 체크
- 커밋되는 것은 **결과물(폰트·이미지·JSON)** 뿐 — `node_modules`·런타임 의존은 `.gitignore` + Actions 안에서만.
- SERP·뉴스는 **공개 데이터** → 캡쳐/요약 커밋 가능. 경쟁사 **가입화면 캡쳐는 여전히 로컬 마스킹 후에만**(데이터 거버넌스 원칙).
- 모든 라이선스는 OFL/MIT/Apache/ISC = 상업이용·재배포 허용 계열만 사용.
