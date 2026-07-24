# STATE — 세션 재개용 현재 상태 (읽고 시작하세요)

> **이 문서의 목적**: 대화 세션이 끊겨도 다음 세션(사람이든 Claude든)이 **이 파일 하나만 읽으면** 지금까지 뭘 만들었고 어디를 이어가면 되는지 즉시 파악하도록. 새 작업을 시작하기 전에 항상 먼저 읽으세요.

_최종 갱신: 2026-07-23 · 진행: 5/10 기능 + 팀 실시간 연동·자동화 완비_

## 한 줄 요약
한화손보 장기CM 마케팅 콘솔 **Modooflow** — 담당 상품(홈·장기7·일반2, 13종)의 SEO·키워드·뉴스·SERP·시즌을 다루는 **정적 웹 도구 모음**. 단일 레포·트렁크(main), GitHub Pages 자동 배포. **디자인=Clean SaaS Light(흰 배경·Pretendard 자체호스팅)**. 실시간 데이터는 **팀 공유 Cloudflare 프록시**로, 키 입력 없이 팀 전원 사용.

## 지금까지 만든 것
| # | 작업공간 | 파일 | 실시간 연동 | 상태 |
|---|---|---|---|---|
| 1 | 테크니컬 SEO 콘솔 | `seo-audit.html` | (정적 진단) | ✅ |
| 2 | 검색광고 키워드 추출 | `keyword-tool.html` | **검색량=프록시** `/searchad/keywordstool`(실시간) | ✅ |
| 3 | 카테고리 뉴스 모니터링 | `news-tool.html` | **뉴스=프록시** `/naver/v1/search/news.json` | ✅ |
| 4 | 검색결과 주간 아카이브 | `serp-tool.html` | **자동 캡쳐**(주간 Action) + 수동 업로드 + 전/후 diff | ✅ |
| 5 | 연간 시즈널 이슈 캘린더 | `seasonal-tool.html` | 트렌드=월간 Action(`data/trends.json`) | ✅ |
| — | 통합 허브 | `index.html` | ⚙키설정 + **오늘 API 사용량 위젯** | ✅ |
| — | 데일리 비서 | `scripts/daily_brief.py` + `daily-brief.yml` | 매일 08:00·14:00 KST **텔레그램** | ✅ 작동 확인 |
| — | 상품 마스터 | `data/products.json` + `check_products_sync.py` | 단일 소스 + CI 드리프트 | ✅ |

## 팀 실시간 연동 구조 (이번 세션 신설 · 핵심)
- **왜**: 네이버 API는 브라우저 직접호출 차단(CORS·HMAC). 키를 각자 브라우저(⚙)에 넣으면 팀 공유 안 됨.
- **해법**: 본인 소유 **Cloudflare Worker 프록시**(`proxy/naver-proxy-worker.js`) 1개.
  - 배포 주소: `https://modooflow-naver-proxy.angle0102.workers.dev` (툴에 `DEFAULT_PROXY`로 내장)
  - 키는 **워커 시크릿**(`NAVER_ID/NAVER_SECRET`, `AD_KEY/AD_SECRET/AD_CUSTOMER`)에 서버 저장 → **팀원은 설정 0**으로 사이트만 열면 실시간.
  - `ALLOW_ORIGIN = https://imsplendid8.github.io` (우리 Pages에서만 사용). ⚠️ **배포된 워커가 아직 `*`이면** 최신 코드 재배포 필요.
  - 라우트: `/naver/*`(검색·데이터랩) · `/searchad/*`(HMAC 자동서명) · `/usage`(사용량) · `/health`
- **사용량 위젯**: 워커가 호출수를 **KV(USAGE)**에 일별 집계 → 허브 홈 "오늘 API 사용량"(검색 25,000·데이터랩 1,000 한도 대비). KV 미바인딩 시 위젯 자동 숨김.
- 설정 가이드: **`docs/api-from-url.md`** (워커 시크릿·KV 바인딩·재배포).
- ⚙ 설정창(localStorage `mf_keys`)은 **개인 override**용(팀 공유 아님).

## 자동화 (GitHub Actions)
| 워크플로우 | 주기 | 산출물 |
|---|---|---|
| `pages.yml` | main push | Pages 배포 |
| `ci.yml` | push/PR | 상품 드리프트 + JS 문법 |
| `daily-brief.yml` | 08:00·14:00 KST | 텔레그램 브리프 |
| `trends.yml` | 월 1일 | `data/trends.json`(데이터랩) |
| `searchad.yml` | 주간(일) | `data/volume.json`(검색량) |
| `serp-capture.yml` | 주간(화 06:00) | `serp/*.png` + `manifest.json` (Playwright 네이버 SERP 자동 캡쳐) |
| `technical-seo.yml` | — | unlighthouse |

## 접속
- **Pages(정본)**: https://imsplendid8.github.io/CM-CMO/
- Artifact(미리보기) 발행법: 각 도구 파일에서 `<!doctype>`/`<head>` 래퍼만 제거한 프래그먼트를 같은 파일경로로 재발행(`docs/architecture.md`).

## 저장소·배포 모델
- 레포: `imsplendid8/CM-CMO` (공개) · 기본 브랜치 **main** · 트렁크 기반(짧은 브랜치→바로 병합).
- 디자인: 각 파일 `<head>`의 `id="mf-saas-theme"` 블록이 통일 뉴트럴 토큰 + Pretendard(`fonts/PretendardVariable.woff2`) 주입. 툴별 액센트색은 각자 유지.

## 다음에 할 일 (6~10번 후보 · 사용자 지정 대기)
- 시즌 툴 **트렌드 실시간 버튼**(현재 월간 Action만) — 실효성은 월간이 더 나음, 선택.
- OSS 후보: 모바일 SERP 동시 캡쳐, 공휴일 자동화 등 → `docs/oss-leverage.md`.
- 로드맵: `docs/roadmap.md`.

## 재개 절차 (새 세션이 이어받을 때)
1. 이 `STATE.md` + `docs/README.md` 읽기.
2. `git log --oneline -15` 로 최근 작업 확인.
3. 실시간/프록시 관련이면 `docs/api-from-url.md`, 자동캡쳐면 `serp/README.md` 확인.
4. 새 기능이면: main에서 짧은 브랜치 → 도구 파일 + `index.html` `TOOLS` 카드 → 검증(Playwright 렌더/`node --check`/`check_products_sync.py`) → main 병합·push(자동 배포).
5. **데이터 거버넌스 준수**: 실제 개인정보·영업비밀·실키 커밋 금지, 샘플·공개·비식별만. 키는 워커 시크릿/GitHub Secrets/localStorage에만.

## 점검 이력 (2026-07-23)
- **레거시 제거**: 수동 키워드 파이프라인(`run_keywords.sh`·`naver_searchad_keywords.py`·`google_ads_keywords.py`·`merge_volume.py`) → 자동 Action + 프록시로 대체. `KEYWORD-API.md` 현행화.
- **보안**: 전 페이지 CSP(default 'self' + 프록시 `*.workers.dev`) + no-referrer. 커밋된 시크릿 없음 확인. 남은 권고=워커 `ALLOW_ORIGIN` 최신본 재배포, (선택) 프록시 공유토큰.
- **뉴스 고도화**: 업계·경쟁사(INDUSTRY 빅4/5) + 수요 트리거(TRIGGERS) + 카드뉴스.
- **고도화 후보**: `docs/enhancements.md` (공공데이터 API=소방청·기상청로 트리거 실데이터화 / NaverSearch·Kakao MCP / 스킬 확장).
- **보류(사용자 검토중)**: #3 실측 검색량 월별 그래프, #2 브랜드·계약(단가표 받아둠 → scratchpad).

## 핵심 결정 기록 (왜 이렇게 했나)
- 도구 = **자체완결 단일 HTML**(외부 의존성 0) → 직접접속·Artifact 발행 모두 용이. 폰트만 자체호스팅.
- 뉴스는 키워드 도구에서 **분리**해 독립 작업공간(사용자 요청).
- **SERP 자동 캡처**: ~~봇차단으로 불가~~ → **정정(2026-07-23)**: GitHub Actions(오픈 네트워크)의 Playwright로 네이버 SERP 캡쳐 성공(13/13). 샌드박스 세션 안에서만 외부망 차단이라 안 될 뿐. SERP는 공개 검색결과라 PII 없음 → 캡쳐본 커밋 가능. (경쟁사 **가입화면** 캡쳐는 여전히 로컬 마스킹 후에만.)
- **키 배치**: 팀 공유=워커 시크릿(서버), 개인 임시=⚙(브라우저), 무인 Action=GitHub Secrets. 3층 분리.
- 분석 톤은 `.claude/skills/cm-news-analysis` 스킬로 표준화.
