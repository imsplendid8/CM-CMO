# STATE — 세션 재개용 현재 상태

_최종 갱신: 2026-08-19_

## 한 줄 요약

Modooflow는 13개 보험상품의 SEO·키워드·뉴스·SERP·시즌·광고소재 업무를 잇는 GitHub Pages 기반 부서용 대시보드다. 현재 단계는 **제품화 중인 팀 도구**이며, 사용자 인증·서버 저장·완전한 단일 App Shell은 아직 없다.

## 현재 브랜치 작업

- 브랜치: `agent/full-hardening`
- 목적: 공개 Secret 제거, SearchAd 프록시 제한, 13×50 소재 내보내기, 모바일 진입, 데이터 신선도, 피드백 루프, 운영 자동화 검증
- 상태: 로컬 구현·브라우저·운영 드라이런 완료, 원격 푸시 및 [Draft PR #24](https://github.com/imsplendid8/CM-CMO/pull/24) 생성. CI 104개 테스트·전체 JS·650행 검증 성공
- 상세 완료 조건과 외부 작업은 `NEXT.md` 참조

## 사용자 화면

| 화면 | 역할 | 상태 |
|---|---|---|
| `index.html` | 오늘의 업무 흐름, 6종 데이터 상태, 도구 허브 | 구현 |
| `seo-audit.html` | 테크니컬 SEO 진단 | 운영 |
| `keyword-tool.html` | 키워드·검색량과 내부 검토용 내보내기 | 운영 |
| `news-tool.html` | 뉴스 모니터링과 클리핑 | 운영 |
| `serp-tool.html` | 검색결과 캡처·diff·광고 관측 | 운영 |
| `seasonal-tool.html` | 시즌·이벤트 추천과 상태 전이 | 운영 |
| `terms-tool.html` | 약관 표현 변환 | 운영 |
| `adcopy-tool.html` | 소재 후보, 검토 상태, 50/650행 내보내기, 공식 템플릿 매핑 | 제품화 |
| `papers-tool.html` | 공개 논문 아카이브 | 운영 |
| `overview.html` | 전체 기능 안내 | 운영 |

모바일 사이드바 도구는 `shared/mobile-sidebar.css`와 `shared/mobile-sidebar.js`를 사용한다. 피드백 UI는 `shared/feedback-client.js`를 사용한다.

## 상품 마스터

- 정본: `data/products.json`
- 총 13개 상품
- `scripts/check_products_sync.py`가 6개 주요 화면의 키·이름 드리프트를 검사
- 광고소재 검증: `scripts/check_adcopy_export.mjs`가 상품별 50행, 총 650행과 길이·금지어·중복을 검사

## Secret과 프록시

- 브라우저 API Secret 저장은 제거했다. 공개 클라이언트 비밀번호도 인증으로 사용하지 않는다.
- Worker: `proxy/naver-proxy-worker.js`
- 실시간 뉴스·데이터랩: 허용된 `/naver/*` 경로
- SearchAd 검색량: 정확히 `GET /searchad/keywordstool`만 허용
- 요청 크기·쿼리 제한, Origin/Referer 허용 목록, KV rate-limit fail-closed 적용
- **중요:** 저장소의 Worker 보강 코드는 Cloudflare에 별도 재배포해야 실제 운영에 반영된다.
- 설정: `docs/api-from-url.md`

## 광고소재 내보내기 원칙

- 기본 CSV는 내부 검토용이며 `심의 검토 전`, `상품 근거 미확인`, `운영 후보` 상태다.
- 공식 네이버 템플릿을 불러오고 필수 열 매핑이 끝난 경우에만 공식 형식 내보내기 버튼이 활성화된다.
- “바로 등록”, “업로드 가능”, “심의 통과”를 자동으로 표시하지 않는다.
- 실제 공식 템플릿 샘플로 인코딩과 열 매핑을 추가 검증해야 한다.

## 자동화

| 워크플로 | 역할 | 최신 운영 확인 |
|---|---|---|
| `signals.yml` | 수요 신호 | 데이터 신선도에 포함 |
| `news-clip.yml` | 뉴스 클리핑 | 데이터 신선도에 포함 |
| `automation-status.yml` | 6종 상태 읽기 전용 점검 | 2026-08-19 수동 실행 성공, healthy 6/6 |
| `event-reco.yml` | 이벤트 추천·상태 저널 재생성 | 2026-08-19 수동 실행 성공, main 갱신 |
| `daily-brief.yml` | Telegram 브리프 | 최근 예약 실행 성공; 수동 발송 금지 |
| `daily-email.yml` | 이메일 브리프 | 예약 실행 |
| `fire-watch.yml` | 긴급 화재 뉴스 감시 | 2026-08-19 브랜치 `send=false` 성공; 후보 16건→사건 2건, 실제 발송 없음 |
| `searchad.yml` | 주간 검색량 | 데이터 신선도에 포함 |
| `trends.yml` | 월간 트렌드 | 데이터 신선도에 포함 |
| `serp-capture.yml` | 주간 SERP 캡처 | 데이터 신선도에 포함 |
| `papers.yml` | 월간 논문 아카이브 | 데이터 신선도에 포함 |
| `ci.yml` | 테스트, 전체 HTML/공유 JS, 상품·650행 계약 검사 | PR #24 성공 |

과거 Daily Brief 실패 원인은 `signals.weather.active`에 문자열이 들어왔는데 객체로 가정한 것이었다. 현재 브랜치에서 문자열·객체 혼재와 잘못된 상위 데이터 형식을 방어하고 회귀 테스트를 추가했다.

## 피드백 루프

- 소재 카드에서 `채택`, `수정 필요`, `반려`를 선택할 수 있다.
- 현재 저장 endpoint는 비어 있으며, UI는 저장 성공을 거짓으로 표시하지 않는다.
- 원문 대신 해시를 준비하며 D1 스키마는 `docs/feedback-schema.sql`에 있다.
- 서버 연결 전 결정할 것: 인증, 역할, 보존기간, 원문 저장 금지, 조회·삭제 권한.

## 테스트

- Python: `python -m unittest discover -s tests -p "test_*.py" -v`
- 상품: `python scripts/check_products_sync.py`
- 소재: `node scripts/check_adcopy_export.mjs`
- 공유 JS: `node --check shared/mobile-sidebar.js`, `node --check shared/feedback-client.js`
- CI는 루트의 모든 HTML 인라인 JavaScript를 검사

## 재개 순서

1. `git status --short --branch`와 `git log --oneline --decorate -10` 확인
2. `NEXT.md`의 상태 원장과 P0 완료 조건 확인
3. `git fetch origin` 후 main이 자동화 커밋으로 전진했는지 확인
4. 전체 테스트 실행
5. 브랜치 푸시 후 Fire Watch를 `send=false`로 브랜치에서 재실행
6. Draft PR CI 확인

## 절대 커밋하지 않는 것

- 실제 API Secret, Telegram 토큰, 광고계정 자격증명
- 개인정보·임직원 정보·계약 원본·실제 광고계정 원본
- 보험 광고심의 최종 승인으로 오해할 수 있는 자동 상태
- 근거 없는 성과 수치
