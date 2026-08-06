# STATE — 세션 재개용 현재 상태 (읽고 시작하세요)

> **이 문서의 목적**: 대화 세션이 끊겨도 다음 세션(사람이든 Claude든)이 **이 파일 하나만 읽으면** 지금까지 뭘 만들었고 어디를 이어가면 되는지 즉시 파악하도록. 새 작업을 시작하기 전에 항상 먼저 읽으세요.

_최종 갱신: 2026-08-07 · 도구 8개 + 팀 실시간 연동 + 자동화(수요신호·뉴스클리핑·자동화상태·브리프[텔레그램/이메일]·SERP·논문) · BSA CLI는 부서 전용 private 분리 · **2026-08-07 세션: 캡쳐 재시도·뉴스 카드 자동반영·클립30일 보관·대표키워드 이관·이메일 브리프(08:30)·파이프라인 재정비·보안(브라우저 키 제거+워커 인증정책) 반영**_

## 한 줄 요약
한화손보 장기CM 마케팅 콘솔 **Modooflow** — 담당 상품(홈·장기7·일반2, 13종)의 SEO·키워드·뉴스·SERP·시즌을 다루는 **정적 웹 도구 모음**. 단일 레포·트렁크(main), GitHub Pages 자동 배포. **디자인=Clean SaaS Light(흰 배경·Pretendard 자체호스팅)**. 실시간 데이터는 **팀 공유 Cloudflare 프록시**로, 키 입력 없이 팀 전원 사용.

## 지금까지 만든 것
| # | 작업공간 | 파일 | 실시간 연동 | 상태 |
|---|---|---|---|---|
| 1 | 테크니컬 SEO 콘솔 | `seo-audit.html` | (정적 진단) | ✅ |
| 2 | 검색광고 키워드 추출 | `keyword-tool.html` | **검색량=프록시** `/searchad/keywordstool`(실시간) · **네이버 '바로등록' 포맷**(분석열 제외·입찰가 70원·검색량순) · (구 '이달의 추천 키워드'는 연간플랜 '카테고리 대표키워드'로 이관) | ✅ |
| 3 | 카테고리 뉴스 모니터링 | `news-tool.html` | **뉴스=프록시** `/naver/v1/search/news.json` · **카드 헤드라인=클리핑 아카이브 최신분 자동 반영**(스탬프 실시간/자동수집/스냅샷 3단계) | ✅ |
| 4 | 검색결과 주간 아카이브 | `serp-tool.html` | **자동 캡쳐**(주간 Action) + 수동 업로드 + 전/후 diff · **관측 광고 분석**(`serp/ad_analysis.json` ← `serp_analysis.py`)이 SERP·소재를 근거화 | ✅ |
| 5 | 연간 시즈널 이슈 캘린더 | `seasonal-tool.html` | 트렌드=월간 Action(`data/trends.json`) · **카테고리 대표키워드 카드**(상품별 대표 2개+실측 12개월 스파크라인, 키워드툴서 이관) | ✅ |
| 6 | 약관 용어 변환 | `terms-tool.html` | (정적, 표준약관→소비자 표현·난이도) | ✅ |
| 7 | 검색광고 소재 | `adcopy-tool.html` | 파워링크 등록 양식 5블록·엑셀 + **주차별 소재 캘린더**·**경쟁사 브랜드검색** 탭 + **네이버 소재 등록 구조 CSV**(담당자 바로 등록·캠페인 ID 공란) | ✅ |
| 8 | 논문 아카이브 | `papers-tool.html` | `data/papers.json` ← 월 1회 네이버 학술 자동 적립(`papers.yml`) · **제공자 아닌 '주제' 기준 그룹핑**·자료원 분리·제공자 배지 · 검색 | ✅ |
| 9 | 시즌·이벤트 캘린더 · 뉴스·추천·이벤트 뷰 | `seasonal-tool.html#reco` (구 `event-calendar.html` → 리다이렉트) | `data/events/recommendations.json` ← `scripts/event_engine.py`(규칙 기반·결정론) · 캘린더+시즌+기상+뉴스+검색량 결합 | ✅ **P0-EVENT Phase 1**(문구 엔진) · 시즌 캘린더와 한 툴(사이드바)로 통합 |
| — | 통합 허브 | `index.html` | **오늘 API 사용량 위젯** · **상단 메뉴 전부 펼침 wrap**(모바일 전체폭·높이 캡) + **관리자 소프트 게이트**(🔒·`[data-admin-only]` 숨김) · 전체 안내 `overview.html` | ✅ |
| — | 브리핑 설정 빌더 | `brief-setup.html` | 텔레그램 브리핑 **다중 수신자 + 발송시간** 설정 UI(관리자) → `daily-brief.yml`·`daily_brief.py` 반영 | ✅ |
| — | BSA 운영(부서 전용) | **private `imsplendid8/Private`** | 검색광고 관리 API on/off·계약·키워드·검색량 — 민감데이터라 공개 CM-CMO에서 분리 | ✅ |
| — | 데일리 비서 | `daily_brief.py` + `daily-brief.yml`·`daily-email.yml` | **텔레그램**(08:00·14:00 KST·오늘 할 일 판단형·다중 수신자·기사 링크) + **이메일**(08:30 KST·표 도식형: 핵심 동향+주요 뉴스 상위 8건·SMTP) · 자동화 상태는 브리프 실행 시 재계산(healthy/stale/missing/unknown 분리) | ✅ |
| — | 상품 마스터 | `data/products.json` + `check_products_sync.py` | 단일 소스 + CI 드리프트 | ✅ |

## 팀 실시간 연동 구조 (이번 세션 신설 · 핵심)
- **왜**: 네이버 API는 브라우저 직접호출 차단(CORS·HMAC). 키를 각자 브라우저(⚙)에 넣으면 팀 공유 안 됨.
- **해법**: 본인 소유 **Cloudflare Worker 프록시**(`proxy/naver-proxy-worker.js`) 1개.
  - 배포 주소: `https://modooflow-naver-proxy.angle0102.workers.dev` (툴에 `DEFAULT_PROXY`로 내장)
  - 키는 **워커 시크릿**(`NAVER_ID/NAVER_SECRET`, `AD_KEY/AD_SECRET/AD_CUSTOMER`)에 서버 저장 → **팀원은 설정 0**으로 사이트만 열면 실시간.
  - **인증·요청 허용 정책**(2026-08-07): 허용 Origin/Referer(`ALLOW_ORIGINS`)만 처리(그 외 403) · 키=**워커 시크릿만**(브라우저 헤더 키 override 폐지) · 라우트·메서드 화이트리스트(그 외 404) · (KV 시)IP·일 요청 상한(429). ⚠️ **워커 코드 변경분은 재배포 필요**(대시보드 Edit code 또는 `wrangler deploy`).
  - 라우트: `/naver/*`(검색·데이터랩) · `/searchad/*`(HMAC 자동서명) · `/usage`(사용량) · `/health`
- **사용량 위젯**: 워커가 호출수를 **KV(USAGE)**에 일별 집계 → 허브 홈 "오늘 API 사용량"(검색 25,000·데이터랩 1,000 한도 대비). KV 미바인딩 시 위젯 자동 숨김.
- 설정 가이드: **`docs/api-from-url.md`** (워커 시크릿·KV 바인딩·재배포).
- **브라우저 API 키 입력·저장 제거**(2026-08-07): 개인 키 입력 UI·localStorage(`mf_keys`/`nv_keys`/`nv_news`) 완전 폐지 → 팀 전원 워커 시크릿만(브라우저 키 노출 0).

## 자동화 (GitHub Actions)
**일일 파이프라인 순서(KST)**: 06:30 수요신호 → 07:20 뉴스수집 → 07:40 자동화상태 → 08:00 오전브리프 → 08:30 이메일 / 13:20 뉴스수집 → 13:40 자동화상태 → 14:00 오후브리프. 수집·브리프 워크플로는 전부 공유 레인 `concurrency: cm-cmo-data-writers`(cancel-in-progress:false)로 직렬화.

| 워크플로우 | 주기(KST) | 산출물 |
|---|---|---|
| `signals.yml` | 매일 06:30 | `data/signals.json`(수요 신호) |
| `news-clip.yml` | 매일 07:20·13:20 | `data/clips/`(뉴스 클리핑 · **최신 30일 보관**·`KEEP_DAYS`) |
| `automation-status.yml` | 매일 07:40·13:40 | 자동화 6종 상태 점검(커밋 없음·Run 요약, 브리프 전 체크포인트) |
| `daily-brief.yml` | 매일 08:00·14:00 | 텔레그램 브리프 |
| `daily-email.yml` | 매일 08:30 | 이메일 브리프(표 도식형·SMTP) |
| `event-reco.yml` | 매일 07:45·13:45 | `data/events/recommendations.json` 재생성 |
| `trends.yml` | 월 1일 | `data/trends.json`(데이터랩) |
| `searchad.yml` | 주간(일) | `data/volume.json`(검색량) |
| `serp-capture.yml` | 주간(월 06:20) | `serp/*.png`+`manifest.json`(캡쳐 실패 시 재시도·`CAPTURE_RETRIES`) |
| `pages.yml` | main push / workflow_run | Pages 배포 |
| `ci.yml` | push/PR | 상품 드리프트 + JS 문법 |
| `technical-seo.yml` | 월 1일 | unlighthouse |

## 접속
- **Pages(정본)**: https://imsplendid8.github.io/CM-CMO/
- Artifact(미리보기) 발행법: 각 도구 파일에서 `<!doctype>`/`<head>` 래퍼만 제거한 프래그먼트를 같은 파일경로로 재발행(`docs/architecture.md`).

## 저장소·배포 모델
- 레포: `imsplendid8/CM-CMO` (공개) · 기본 브랜치 **main** · 트렁크 기반(짧은 브랜치→바로 병합).
- 디자인: 각 파일 `<head>`의 `id="mf-saas-theme"` 블록이 통일 뉴트럴 토큰 + Pretendard(`fonts/PretendardVariable.woff2`) 주입. 툴별 액센트색은 각자 유지.

## 다음에 할 일 (후보 · `NEXT.md` 백로그 기준)
- **P0-EVENT 남은 작업**(`NEXT.md`): ①active window(최근3일)↔장기 archive 분리·연동 ②뉴스 캘린더 UI↔데일리 브리프 통합 ③긴급 대형화재 감시→별도 실시간 알림(텔레그램 dry-run).
- **P0-3**(`NEXT.md`): 검색광고 파일을 '내부 검토용'과 '네이버 업로드 흐름'으로 분리(공식 템플릿 확인 전 '업로드 가능' 표시 금지).
- 시즌 툴 **트렌드 실시간 버튼**(현재 월간 Action만) — 선택. OSS 후보 → `docs/oss-leverage.md` · 로드맵 → `docs/roadmap.md`.

## 재개 절차 (새 세션이 이어받을 때)
1. 이 `STATE.md` + `docs/README.md` 읽기.
2. `git log --oneline -15` 로 최근 작업 확인.
3. 실시간/프록시 관련이면 `docs/api-from-url.md`, 자동캡쳐면 `serp/README.md` 확인.
4. 새 기능이면: main에서 짧은 브랜치 → 도구 파일 + `index.html` `TOOLS` 카드 → 검증(Playwright 렌더/`node --check`/`check_products_sync.py`) → main 병합·push(자동 배포).
5. **데이터 거버넌스 준수**: 실제 개인정보·영업비밀·실키 커밋 금지, 샘플·공개·비식별만. 키는 워커 시크릿/GitHub Secrets/localStorage에만.

## 점검 이력 (2026-08-07) — 이번 세션 산출물 (전부 main 반영)
- **캡쳐 재시도**: `capture_serp.mjs`·`capture_brand.mjs` — 렌더 완료 판정(`renderedOk`) 후 스크린샷, 빈 화면/오류면 재로드 재캡쳐(`CAPTURE_RETRIES`, 기본 1). 마지막 시도는 무조건 저장.
- **논문**: `papers-tool.html` — '참고자료 (제목 미확인)' 미확정 플레이스홀더를 아카이브 표시에서 숨김.
- **뉴스**: `news-tool.html` — 카테고리 카드 헤드라인을 **클리핑 아카이브 최신분으로 자동 반영**(`autofillFromClips`), 요약·시사점은 정적 유지, 스탬프 3단계.
- **클립 보관**: `clip_news.py` `KEEP_DAYS=30` — 초과 일자 파일 자동 정리, `news-clip.yml` `git add -A`.
- **대표키워드 이관**: `keyword-tool.html`의 '이달의 추천 키워드' 제거 → `seasonal-tool.html`(연간플랜)에 **카테고리 대표키워드 카드**(상품별 대표 2개+실측 스파크라인) 신설.
- **이메일 브리프**: `daily_brief.py` `render_email()`(표 도식형·HTML+텍스트) + `daily-email.yml`(08:30 KST). 구성=① 핵심 동향(메인3+업계 요약) ② 주요 뉴스(전체 상위 8건, 카테고리당 최대 2건 dedup). 제목 `(장기CM사업부) YY.MM.DD 뉴스 모니터링`. 동향 요약은 news-tool `NEWSMON` 파싱해 단일 소스 재사용(`load_newsmon`). 텔레그램 경로 불변.
- **파이프라인 재정비**: signals 06:30 / news 07:20·13:20 / **automation-status.yml 신규** 07:40·13:40 / brief 08:00·14:00 — 전부 `cm-cmo-data-writers` 레인(daily-brief·daily-email도 편입).
- **자동화 상태**: `check_automation_health.format_lines` — stale·missing·unknown **항상 분리 표기**(브리프 실행 시 재계산은 기존대로). 테스트 15/15.
- **보안**: 브라우저 API 키 입력·localStorage 저장 제거(news·keyword) · 전 HTML CSP `localhost:8787` 제거 · **워커 인증·요청허용 정책**(Origin/Referer 화이트리스트 403 · 워커 시크릿 전용 · 라우트/메서드 화이트리스트 404 · IP·일 상한 429). `docs/api-from-url.md` 갱신. ⚠️ **워커 재배포 필요**.
- **미결(외부)**: 2026-08-06 오후~ **GitHub 광범위 장애**로 Pages 배포+Actions run 생성이 멈춤(코드는 main 반영 완료, 복구 시 자동 배포). 워커는 사용자 대시보드 배포 완료(검증 대기).

## 점검 이력 (2026-08-06) — 코덱스 개선분 반영 확인
Codex가 별도 브랜치로 작업한 개선분이 **PR #9~#23으로 이미 main에 스쿼시 병합**되어 있음을 확인(미병합 원격 `feat/*`·`p0-event/*` 브랜치들은 스쿼시 이전의 오래된 중복본 → 다시 병합하면 오히려 main 회귀). 반영된 항목:
- **시즌·캘린더 통합**: 시즌 소스 단일화·day-level 기상 span(#9)·단일 진입점(#11)·**사이드바 단일 앱 통합**(#12).
- **SERP 근거화**: 관측 광고 분석(`serp_analysis.py`)이 SERP·소재를 근거화(#10).
- **브리핑**: 다중 수신자 + `brief-setup.html` 발송시간 빌더(#13), 부분 발송 감지(종료코드), 뉴스 기사 링크(#23).
- **허브 내비**: 그룹 드롭다운 + 관리자 소프트 게이트(#14) → **전부 펼침 wrap형**으로 정리(#19), 메뉴 라벨 간소화(#22).
- **논문**: 제공자 아닌 '주제' 기준 그룹핑 + 제공자 배지(#15).
- **키워드**: 네이버 '바로등록' 포맷(#16), **이달의 추천 키워드**(#20).
- **소재**: 네이버 소재 등록 구조 CSV(#17).
- **이벤트 엔진**: Phase 2A 상태 전이 + Phase 2B **추천 재생성 워크플로**(`event-reco.yml`).
- **가입플로우 앱**: `flow/`로 통합했다가(#21) **되돌림**(#23) — 공개 CM-CMO엔 미포함(현 상태). 라이트 기본 테마·토글 저장은 전 도구에 반영됨.
- 이번 세션 산출물: 위 반영 상태를 **STATE.md에 현행화**(코드 변경 없음 — 신규 병합 대상 없음).

## 점검 이력 (2026-07-27)
- **검색광고 소재 재구성**: 카드형 후보 → 네이버 파워링크 **실제 등록 양식 5블록**(광고제목·추가제목·설명·홍보문구·서브링크) 롤링 소재 + 글자수 자동 + **엑셀(.xls)/TSV 내보내기**. **주차별 소재 캘린더** 탭(6주×집중 이슈+경쟁사 참고) + **경쟁사 브랜드검색** 탭(serp/brand 이식) 통합.
- **논문 아카이브 대시보드화**: `papers-tool.html`(주제 필터·검색) + `data/papers.json`(← MD 정본, `papers_to_json.py`로 동기화, `papers.yml`이 함께 커밋).
- **데일리 비서 판단형 전환**: 헤드라인 나열 → **오늘 할 일**(수요신호·시즌·클리핑·SERP를 액션 우선순위로) + 뉴스는 행동가치 키워드만 선별.
- **홈 '연말정산' 제거**: 보험 뉴스 아님 → adcopy·seasonal-tool·`data/seasonal.json` 홈 항목 삭제.
- **SERP 로컬(ZIP) 안내**: `file://`로 열면 자동 캡쳐 미표시 배너 + 개인 업로드 라벨 명확화.
- **문서 현행화**: tools.md(5개→8개 도구·serp 자동캡쳐 정정)·README·CLAUDE·roadmap·overview(캡쳐 수치).

## 점검 이력 (2026-07-23)
- **레거시 제거**: 수동 키워드 파이프라인(`run_keywords.sh`·`naver_searchad_keywords.py`·`google_ads_keywords.py`·`merge_volume.py`) → 자동 Action + 프록시로 대체. `KEYWORD-API.md` 현행화.
- **보안**: 전 페이지 CSP(default 'self' + 프록시 `*.workers.dev`) + no-referrer. 커밋된 시크릿 없음 확인. 남은 권고=워커 `ALLOW_ORIGIN` 최신본 재배포, (선택) 프록시 공유토큰.
- **뉴스 고도화**: 업계·경쟁사(INDUSTRY 빅4/5) + 수요 트리거(TRIGGERS) + 카드뉴스.
- **고도화 실현분(구 enhancements.md → 삭제, 여기로 흡수)**: 공공데이터(기상)·검색 기반 수요 신호(`signals.yml`), NaverSearch MCP+`cm-news-analysis` 뉴스 자동화, 스킬 3종, 논문 월간 자동 적립(`papers.yml`).
- **검색광고(SA)·BSA 솔루션**: `docs/검색광고-BSA-로드맵.md` 참조. 완료=A1(키워드 대량등록)·A2(문구 소재+시즌+근거). BSA(B2·B3·키워드·검색량)는 **부서 전용 private `imsplendid8/Private`** 로 이관(민감 계약데이터).
- **보류(사용자 검토중)**: #3 실측 검색량 월별 그래프. (#2 브랜드·계약 판단은 BSA CLI로 구현 완료)

## 핵심 결정 기록 (왜 이렇게 했나)
- 도구 = **자체완결 단일 HTML**(외부 의존성 0) → 직접접속·Artifact 발행 모두 용이. 폰트만 자체호스팅.
- 뉴스는 키워드 도구에서 **분리**해 독립 작업공간(사용자 요청).
- **SERP 자동 캡처**: ~~봇차단으로 불가~~ → **정정(2026-07-23)**: GitHub Actions(오픈 네트워크)의 Playwright로 네이버 SERP 캡쳐 성공(13/13). 샌드박스 세션 안에서만 외부망 차단이라 안 될 뿐. SERP는 공개 검색결과라 PII 없음 → 캡쳐본 커밋 가능. (경쟁사 **가입화면** 캡쳐는 여전히 로컬 마스킹 후에만.)
- **키 배치**: 팀 공유=워커 시크릿(서버), 개인 임시=⚙(브라우저), 무인 Action=GitHub Secrets. 3층 분리.
- 분석 톤은 `.claude/skills/cm-news-analysis` 스킬로 표준화.
