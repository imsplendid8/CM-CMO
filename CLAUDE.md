# CLAUDE.md — CM-CMO 프로젝트 가이드

이 파일은 Claude Code가 이 저장소에서 작업할 때 참고하는 가이드입니다. **새 세션은 먼저 `STATE.md`를 읽으세요** (지금까지의 작업과 재개 절차).

## 프로젝트
**Modooflow** — 한화손해보험 장기CM 마케팅 콘솔. 담당 상품(홈·장기7·일반2·간편심사, 13종)의 검색·마케팅을 돕는 **정적 웹 도구 모음**. 진행 5/10 기능 + 팀 실시간 연동·자동화. 디자인=Clean SaaS Light(흰 배경·Pretendard 자체호스팅).

## 저장소 지도
| 구분 | 위치 |
|---|---|
| 현재 상태·재개 | `STATE.md` (최우선) |
| 위키(정리 문서) | `docs/` — `README.md`(색인)·`architecture.md`·`tools.md`·`roadmap.md`·`daily-brief.md`·`api-from-url.md`(프록시)·`oss-leverage.md`·`enhancements.md` |
| 허브 | `index.html` (상단 고정 내비 + ⚙키설정 + API 사용량 위젯) |
| 도구 6종 | `seo-audit.html` · `keyword-tool.html` · `news-tool.html`(업계·경쟁사+수요 트리거) · `serp-tool.html`(자동 캡쳐) · `seasonal-tool.html` · `terms-tool.html`(약관 용어→쉬운 표현) |
| 팀 실시간 프록시 | `proxy/naver-proxy-worker.js` (Cloudflare Worker · 키=워커 시크릿) |
| 폰트 | `fonts/PretendardVariable.woff2` (자체호스팅) |
| 스크립트 | `scripts/` (workflow용: `naver_searchad_volume`·`naver_trends`·`daily_brief`·`capture_serp`·`check_products_sync`; 로컬 폴백: `naver_local_server`) |
| 스킬 3종 | `.claude/skills/` — `cm-news-analysis`(뉴스·동향 분석) · `card-news-summary`(카드뉴스 요약) · `insurance-terms`(약관 용어 순화) |
| 배포·자동화 | `.github/workflows/` — pages·ci·daily-brief·trends·searchad·serp-capture·technical-seo |

## 작업 규칙
- **트렁크 기반**: main에서 짧은 브랜치 → 검증 → 바로 병합·push(자동 배포). 롱리브 브랜치 금지.
- 도구는 **자체완결 단일 HTML**(외부 라이브러리·빌드 0). 사용자 입력 출력은 `esc()`, 객체 키는 `safeKey()`.
- **디자인**: 각 도구 `<head>`의 `id="mf-saas-theme"` 블록이 통일 뉴트럴 토큰+Pretendard 주입. 툴별 액센트색 유지. 전 페이지 CSP + no-referrer.
- **실시간 데이터**: 브라우저는 네이버 직접호출 불가(CORS·HMAC) → **프록시 경유**(`DEFAULT_PROXY`). 키는 워커 시크릿(팀 공유)/GitHub Secrets(Action)/localStorage(개인). 파일·커밋 금지.
- 새 기능 = 도구 HTML 1개 + 허브 `TOOLS` 카드 1개 + (선택) Artifact 발행. 방법은 `docs/architecture.md`.
- 도구 상품 집합은 5종 모두 동일(13종) — `scripts/check_products_sync.py` 드리프트 가드(CI). 업계·경쟁사(뉴스툴 INDUSTRY)는 상품 마스터와 분리.

## ⚠️ 데이터 거버넌스 (최우선)
- 고객·임직원 개인정보·회사 영업비밀은 **외부 AI/커밋 금지**. 반드시 **샘플·공개·비식별/가상 데이터**만.
- 뉴스 헤드라인·링크·SERP는 공개 정보만. 요약·시사점은 자체 분석.
- 광고성 문구는 배포 전 광고심의 검수 전제. 검색량/입찰가는 각 광고 플랫폼에서 확정.

## 분석 산출물 톤 (cm-news-analysis 스킬)
인사말·미사여구 없이 **[핵심 요약]→[상세]** 2단계, 뉴스는 **이슈–업계영향–담당자 참고** 3요소, **메인 3종(운전자·주택화재·골프)** 비중 강조.
