# CM-CMO · Modooflow

한화손해보험 장기CM 마케팅 업무를 위한 정적 대시보드입니다. 13개 담당 상품의 검색·뉴스·시즌·SERP·광고소재 업무를 한 허브에서 연결하고, GitHub Actions가 공개·비식별 데이터를 주기적으로 갱신합니다.

> 이 저장소의 문구와 추천은 **내부 검토용 초안**입니다. 보험 광고심의 통과, 담보 사실, 네이버 등록 성공을 자동으로 보장하지 않습니다.

## 주요 업무

| 영역 | 화면 | 역할 |
|---|---|---|
| 오늘의 업무 | `index.html` | 업무 흐름, 6종 데이터 신선도, 도구 진입 |
| 검색 인사이트 | `seo-audit.html`, `keyword-tool.html`, `serp-tool.html` | SEO 진단, 키워드·검색량, 검색결과 관측 |
| 시장·이슈 | `news-tool.html`, `seasonal-tool.html` | 뉴스 클리핑, 시즌·이벤트 추천과 상태 전이 |
| 콘텐츠·심의 | `terms-tool.html`, `adcopy-tool.html` | 소비자 표현, 검색광고 소재 후보와 내부 검토 |
| 자료 | `papers-tool.html` | 공개 논문 아카이브 |

광고소재 도구는 상품별 50행, 전체 650행을 생성·검증합니다. 공식 네이버 템플릿을 불러와 필수 열을 매핑하기 전까지 결과물은 업로드 파일이 아니라 내부 검토용입니다.

## 실행

서버 빌드가 없는 정적 사이트라 저장소 루트에서 간단한 HTTP 서버로 확인할 수 있습니다.

```bash
python -m http.server 8765
```

그다음 `http://localhost:8765/`를 엽니다. 운영본은 [GitHub Pages](https://imsplendid8.github.io/CM-CMO/)에서 확인합니다.

## 데이터와 자동화

- 브라우저는 네이버 Secret을 저장하지 않습니다. 실시간 조회는 Cloudflare Worker가 서버 Secret으로 서명합니다.
- GitHub Actions가 뉴스, 수요 신호, 검색량, 트렌드, 논문, SERP와 이벤트 추천을 갱신합니다.
- 화면과 Daily Brief는 원천 데이터 시각으로 `healthy`, `stale`, `missing`, `unknown`을 다시 계산합니다.
- Event Recommendations, Automation Health, Fire Watch는 수동 `workflow_dispatch`를 지원합니다. Fire Watch 실제 발송은 명시적 opt-in입니다.

설정과 운영 문서는 다음을 참조하세요.

- `docs/api-from-url.md` — Worker Secret과 허용 경로
- `docs/automation-runbook.md` — Actions 순서와 충돌 방지
- `docs/daily-brief.md` — Telegram·이메일 브리프
- `docs/feedback-loop.md` — 채택/수정/반려 이벤트와 저장소 결정
- `NEXT.md` — 구현·검증·배포 상태 및 남은 의사결정

## 보안 경계

- Secret, Telegram 토큰, 광고계정 원본, 개인정보를 정적 HTML·`localStorage`·커밋에 넣지 않습니다.
- `/searchad/keywordstool`은 Worker의 읽기 전용 GET만 허용합니다.
- 공개 화면의 숨김 메뉴나 클라이언트 비밀번호는 인증 수단이 아닙니다.
- 관리자·피드백 저장 기능은 서버 인증과 보존 정책을 정한 뒤 연결합니다.

## 검증

```bash
python scripts/check_products_sync.py
python -m unittest discover -s tests -p "test_*.py" -v
node scripts/check_adcopy_export.mjs
node --check shared/mobile-sidebar.js
node --check shared/feedback-client.js
```

CI는 루트의 모든 HTML 인라인 JavaScript도 문법 검사합니다.

## 배포

`main` 변경은 GitHub Pages 워크플로로 배포됩니다. Worker 코드는 저장소 변경만으로 배포되지 않으므로 `proxy/naver-proxy-worker.js`를 Cloudflare에 별도 배포하고 `/health`, Origin 제한, 경로·메서드 거부를 확인해야 합니다.

## 현재 한계

- 여러 독립 HTML을 허브에서 여는 구조라 완전한 단일 App Shell과 공통 사용자 상태는 아직 없습니다.
- 사용자 인증, 역할 기반 권한, 감사 이력, 서버 데이터베이스는 미구현입니다.
- 피드백 UI와 D1 스키마는 있으나 저장 API는 연결하지 않았습니다.
- 검색광고 공식 템플릿은 실제 샘플로 최종 검증해야 합니다.
