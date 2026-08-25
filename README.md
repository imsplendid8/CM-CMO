# CM-CMO · Modooflow

한화손해보험 장기CM 마케팅 업무를 위한 정적 대시보드입니다. 13개 담당 상품의 검색·뉴스·시즌·SERP·광고소재 업무를 한 허브에서 연결하고, GitHub Actions가 공개·비식별 데이터를 주기적으로 갱신합니다.

> 이 저장소의 문구와 추천은 **내부 검토용 초안**입니다. 보험 광고심의 통과, 담보 사실, 네이버 등록 성공을 자동으로 보장하지 않습니다.

## 주요 업무

| 영역 | 화면 | 역할 |
|---|---|---|
| 오늘의 업무 | `index.html` | 업무 흐름, 5종 데이터 신선도, 도구 진입 |
| 검색 인사이트 | `seo-audit.html`, `keyword-tool.html`, `serp-tool.html` | SEO 진단, 키워드·검색량, 검색결과 관측 |
| 시장·이슈 | `news-tool.html`, `seasonal-tool.html` | 뉴스 클리핑, 시즌·이벤트 추천과 상태 전이 |
| 콘텐츠·심의 | `adcopy-tool.html`, `powercontent-tool.html` | SA 심의안 초안과 키워드 기반 파워콘텐츠 기획·본문 제작 |

SA 소재 도구는 실제 심의안 순서의 문구와 심의안에 없던 네이버 확장소재 추가설명 4개를 함께 제안하고 Excel 심의안+추가소재 초안을 생성합니다. 파워링크 이미지 1장과 이미지형 서브링크 3장은 SERP의 주요 검색어·경쟁사 공통 소구·추천 소구를 상품별 3D 보험종목 장면과 오버레이 문구에 연결해 214×214px로 제작합니다. PNG 4장과 기준 정보·해시가 든 manifest를 ZIP 하나로 내보내며, 승인 이미지를 올리면 외부 전송 없이 중앙 크롭해 적용합니다. 파워콘텐츠 도구는 SearchAd 키워드 수요에서 대표·연관·본문 보조·시즌 키워드를 고르고 콘텐츠 3안, 도입부, 본문 5개 섹션, FAQ, CTA, 이미지 브리프와 광고 문안을 함께 제안합니다. 선택 상품의 실측·담보·질문·시즌 키워드 전체 후보는 검색량·출처·추천 활용 위치를 포함한 Excel로 내보낼 수 있습니다. 두 결과물 모두 최신 상품자료·약관·준법·광고심의를 거쳐야 합니다.

## 실행

서버 빌드가 없는 정적 사이트라 저장소 루트에서 간단한 HTTP 서버로 확인할 수 있습니다.

```bash
python -m http.server 8765
```

그다음 `http://localhost:8765/`를 엽니다. 운영본은 [GitHub Pages](https://imsplendid8.github.io/CM-CMO/)에서 확인합니다.

## 데이터와 자동화

- 브라우저는 네이버 Secret을 저장하지 않습니다. 실시간 조회는 Cloudflare Worker가 서버 Secret으로 서명합니다.
- GitHub Actions가 뉴스, 수요 신호, 검색량, 트렌드, SERP와 이벤트 추천을 갱신합니다.
- Content Intelligence Agent가 SERP 관측·검색량·상품 마스터를 결합해 검색어, 경쟁사 공통 소구, 차별 소구와 검색 기반 FAQ 질문 기회를 주간 생성합니다. 경쟁사 원문·브랜드·수치·할인은 복사하지 않고 FAQ 답변도 자동 게시하지 않습니다.
- SEO Title Ops가 공개 SearchAd 수요와 비공개 GSC 범주 검증을 결합해 상품별 제목 후보 3개·약점·자기잠식 상태를 생성합니다. GSC 미연결 시 초안만 제공하고 추천은 차단합니다.
- Search Console OAuth Secret을 설정하면 실제 유입 쿼리를 비공개 수집하며, SERP 캡처는 광고 DOM 후보를 `needs_review` 큐로 함께 남깁니다.
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
node scripts/check_powercontent.mjs
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
- 키워드 도구의 대량등록 파일은 실제 광고주센터 샘플로 최종 검증해야 합니다. SA 소재 도구는 공식 템플릿 열 매핑을 제공하지 않습니다.
