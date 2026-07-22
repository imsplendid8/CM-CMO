# STATE — 세션 재개용 현재 상태 (읽고 시작하세요)

> **이 문서의 목적**: 대화 세션이 끊겨도 다음 세션(사람이든 Claude든)이 **이 파일 하나만 읽으면** 지금까지 뭘 만들었고 어디를 이어가면 되는지 즉시 파악하도록. 새 작업을 시작하기 전에 항상 먼저 읽으세요.

_최종 갱신: 2026-07-22 · 진행: 5/10 기능_

## 한 줄 요약
한화손보 장기CM 마케팅 콘솔 **Modooflow** — 담당 상품(홈·장기7·일반2)의 SEO·키워드·뉴스·SERP·시즌을 다루는 **정적 웹 도구 모음**. 단일 레포·트렁크(main) 기반, GitHub Pages 자동 배포.

## 지금까지 만든 것 (5/10)
| # | 작업공간 | 파일 | 역할 | 상태 |
|---|---|---|---|---|
| 1 | 테크니컬 SEO 콘솔 | `seo-audit.html` | 현행 화면 진단·HTML 태깅 가이드·robots.txt | ✅ |
| 2 | 검색광고 키워드 추출 | `keyword-tool.html` | 키워드 생성·분류·CSV, 네이버 키워드도구 .xlsx 병합·검색량 매핑 | ✅ |
| 3 | 카테고리 뉴스 모니터링 | `news-tool.html` | 상품별 뉴스 요약·시사점, 로컬서버 실시간 갱신 | ✅ |
| 4 | 검색결과 주간 아카이브 | `serp-tool.html` | 대표키워드 SERP 스크린샷 주간 저장·전후 비교·경쟁사 소구포인트 | ✅ |
| 5 | 연간 시즈널 이슈 캘린더 | `seasonal-tool.html` | 상품별 계절 이슈·키워드·선제 대응 시점·히트맵 | ✅ |
| — | 통합 허브 | `index.html` | 5개 작업공간 진입점 | ✅ |
| — | 데일리 비서 | 루틴 `trig_01MvXuRQSJXHdwj97mvqSR7S` | 매일 08:00 KST 카카오 브리핑 | ⚠️ 커넥터 연결 필요(§운영) |

## 접속 (직접 접속·직접 배포)
- **Pages(정본, push 시 자동 갱신)**: https://imsplendid8.github.io/CM-CMO/
- Artifact(미리보기): 허브 `a354d70a-…` · SEO `8a9868bf-…` · 키워드 `42429a9c-…` · 뉴스 `5b1757b0-…` · SERP `72a87db9-…` · 시즌 `c21016a1-…`
  - 갱신법: 각 도구 파일에서 `<!doctype>`/`<head>` 래퍼만 제거한 프래그먼트를 만들어 같은 파일경로로 재발행. 자세한 건 `docs/architecture.md`.

## 저장소·배포 모델
- 레포: `imsplendid8/CM-CMO` (공개) · 기본 브랜치 **main**
- **트렁크 기반**: 새 기능은 main에서 짧은 브랜치 → 바로 병합. 롱리브 브랜치 금지.
- 배포: `.github/workflows/pages.yml` (main push → Pages). Source=GitHub Actions (설정 완료).

## 다음에 할 일 (6~10번 후보)
로드맵·고도화 아이디어(OSS 활용 포함)는 **`docs/roadmap.md`** 참고. 사용자가 다음 기능을 지정하면 착수.

## 재개 절차 (새 세션이 이어받을 때)
1. 이 `STATE.md` + `docs/README.md` 읽기.
2. `git log --oneline -15` 로 최근 작업 확인.
3. 새 기능이면: `git checkout -b feature/<이름> origin/main` → 도구 파일 1개 추가 + `index.html` 카드 1개 → 검증(Playwright/문법) → main 병합·push(자동 배포) → Artifact 발행(선택).
4. **데이터 거버넌스 준수**: 실제 개인정보·영업비밀 금지, 샘플·공개·비식별만. (`docs/architecture.md`§거버넌스)

## 핵심 결정 기록 (왜 이렇게 했나)
- 도구 = **자체완결 단일 HTML**(외부 의존성 0) → 직접접속·Artifact 발행 모두 용이.
- 뉴스는 키워드 도구에서 **분리**해 독립 작업공간으로(사용자 요청).
- SERP 자동 캡처는 네이버 봇차단으로 불가 → **브라우저 수동 아카이브(localStorage)**로 설계.
- 분석 톤은 `.claude/skills/cm-news-analysis` 스킬로 표준화(핵심요약+상세, 이슈-영향-참고, 메인3종 강조).
