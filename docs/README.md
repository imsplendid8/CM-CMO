# Modooflow 위키 — CM-CMO

한화손보 장기CM 마케팅 콘솔의 정리 문서입니다. (GitHub에서 그대로 렌더링됩니다.)

## 색인
- **[../STATE.md](../STATE.md)** — 현재 상태·세션 재개 절차 (**먼저 읽기**)
- **[architecture.md](architecture.md)** — 저장소 구조·디자인 시스템·브랜치/배포·데이터 거버넌스
- **[tools.md](tools.md)** — 도구별 목적·데이터 모델·사용법
- **[검색광고-BSA-로드맵.md](검색광고-BSA-로드맵.md)** — 검색광고(SA)·브랜드검색(BSA) 솔루션 로드맵(A1~A6·B1~B3)
- **[roadmap.md](roadmap.md)** — 진행 현황·고도화 아이디어(OSS 활용 포함)
- **[api-from-url.md](api-from-url.md)** — 팀 실시간 연동(Cloudflare 프록시·워커 시크릿·KV 사용량)
- **[oss-leverage.md](oss-leverage.md)** — 활용 OSS(Pretendard·Playwright·pixelmatch 등)
- **[daily-brief.md](daily-brief.md)** — 데일리 텔레그램 비서 브리핑 설정
- **[논문-아카이브.md](논문-아카이브.md)** — CM 마케팅 참고 논문(월 1회 GitHub Actions 자동 적립)
- **[../serp/README.md](../serp/README.md)** — SERP 자동 캡쳐 아카이브

## 도구 (허브: `index.html` · 전체 안내: `overview.html`)
1. **테크니컬 SEO** — `seo-audit.html`
2. **검색광고 키워드** — `keyword-tool.html` (네이버 실시간 검색량 + **대량등록 파일 내보내기**)
3. **카테고리 뉴스** — `news-tool.html` (업계·경쟁사 동향·수요 트리거·**클리핑 아카이브**)
4. **SERP 아카이브** — `serp-tool.html` (전/후 diff + **경쟁사 브랜드검색 갤러리**)
5. **시즌 캘린더** — `seasonal-tool.html`
6. **약관 용어 변환** — `terms-tool.html`
7. **검색광고 소재** — `adcopy-tool.html` (파워링크 규격·심의 린트·**시즌 이슈**·**뉴스/SERP 근거**)

## 자동화 (GitHub Actions)
- **뉴스 클리핑** 하루 2회(09·13시) · **SERP 캡쳐** 주간(경쟁사 브랜드검색 포함) · **수요 신호**(기상·검색) · **논문 월간 적립** · **데일리 브리핑**(텔레그램) · **트렌드**(데이터랩 월간) · **검색량**(검색광고 주간) · **Pages 배포**

## 별도 도구 (대시보드와 독립)
- **`naver-searchad-bsa-monitor/`** — 네이버 검색광고 **관리 API**로 BSA on/off 모니터링 + 계약 D-day·**재계약 판단**(Python CLI). 키(`NAVER_SEARCHAD_*`)는 환경변수, 실계약 원장은 `.gitignore`.

## 빠른 링크
- 배포(정본): https://imsplendid8.github.io/CM-CMO/ (전체 안내: `/overview.html`)
- 저장소: https://github.com/imsplendid8/CM-CMO

## 이 콘솔이 하는 일
담당 상품의 **검색 노출(SEO) → 검색광고 키워드·소재 → 카테고리 뉴스 → 검색결과(SERP)·브랜드검색 → 시즌 선제대응**을 한 곳에서. 진단·근거·실행·운영을 개발·마케팅이 바로 쓰도록 정적 대시보드 + 자동화로 제공합니다.
