# Modooflow 위키 — CM-CMO

한화손보 장기CM 마케팅 콘솔의 정리 문서입니다. (GitHub에서 그대로 렌더링됩니다.)

## 색인
- **[../STATE.md](../STATE.md)** — 현재 상태·세션 재개 절차 (**먼저 읽기**)
- **[architecture.md](architecture.md)** — 저장소 구조·디자인 시스템·브랜치/배포·데이터 거버넌스
- **[tools.md](tools.md)** — 도구별 목적·데이터 모델·사용법
- **[검색광고-BSA-로드맵.md](검색광고-BSA-로드맵.md)** — 검색광고(SA)·브랜드검색(BSA) 솔루션 로드맵(A1~A6·B1~B3)
- **[roadmap.md](roadmap.md)** — 진행 현황·고도화 아이디어(OSS 활용 포함)
- **[api-from-url.md](api-from-url.md)** — 팀 실시간 연동(Cloudflare 프록시·워커 시크릿·KV 사용량)
- **[monthly-planning-loop.md](monthly-planning-loop.md)** — 기준월·당월/익월 플랜·FAQ·소재·신규/급상승 키워드 연결
- **[naver-ad-material-guide.md](naver-ad-material-guide.md)** — SA·파워컨텐츠 공통 소재 규격·수동 입력 원칙
- **[ui-system.md](ui-system.md)** — 새 브랜드 마크·공통 아이콘·허브/도구 UI·접근성 규칙
- **[content-briefing.md](content-briefing.md)** — 세 채널 공통 뉴스 요약·반복 억제
- **[oss-leverage.md](oss-leverage.md)** — 활용 OSS(Pretendard·Playwright·pixelmatch 등)
- **[daily-brief.md](daily-brief.md)** — 데일리 텔레그램 비서 브리핑 설정
- **[../serp/README.md](../serp/README.md)** — SERP 자동 캡쳐 아카이브

## 도구 (허브: `index.html` · 전체 안내: `overview.html`)
1. **테크니컬 SEO** — `seo-audit.html`
2. **검색광고 키워드** — `keyword-tool.html` (네이버 실시간 검색량 + **대량등록 파일 내보내기**)
3. **카테고리 뉴스** — `news-tool.html` (업계·경쟁사 동향·수요 트리거·**클리핑 아카이브**)
4. **SERP 아카이브** — `serp-tool.html` (전/후 diff + **경쟁사 브랜드검색 갤러리**)
5. **시즌 캘린더** — `seasonal-tool.html`
6. **검색광고 소재** — `adcopy-tool.html` (실제 심의안 구조 Excel 초안 + 파워링크 소재·경쟁사 문구 구조 활용 + **주차별 소재 캘린더** + **경쟁사 브랜드검색** 탭)
7. **파워콘텐츠 소재** — `powercontent-tool.html` (키워드 전략 + 콘텐츠 3안 + 본문·FAQ·광고 문안 브리프)

## 자동화 (GitHub Actions)
- **뉴스 클리핑** 하루 2회(09·13시) · **SERP 캡쳐** 주간(경쟁사 브랜드검색 포함) · **수요 신호**(기상·검색) · **데일리 브리핑**(텔레그램) · **트렌드**(데이터랩 월간) · **검색량**(검색광고 주간) · **Pages 배포**

## 별도 도구 (대시보드와 독립)
- **BSA(브랜드검색) 운영 CLI** — 계약·단가 등 민감데이터라 **부서 전용 private 저장소 `imsplendid8/Private`** 로 분리(공개 대시보드와 독립). on/off 모니터링·계약 재계약 판단·키워드 제안·검색량 우선순위 + 매일 자동 실행(private Actions).

## 빠른 링크
- 배포(정본): https://imsplendid8.github.io/CM-CMO/ (전체 안내: `/overview.html`)
- 저장소: https://github.com/imsplendid8/CM-CMO

## 이 콘솔이 하는 일
담당 상품의 **검색 노출(SEO) → 검색광고 키워드·소재 → 카테고리 뉴스 → 검색결과(SERP)·브랜드검색 → 시즌 선제대응**을 한 곳에서. 진단·근거·실행·운영을 개발·마케팅이 바로 쓰도록 정적 대시보드 + 자동화로 제공합니다.
