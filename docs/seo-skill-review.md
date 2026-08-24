# 외부 SEO 스킬 4종 코드 리뷰와 적용 결정

_검토일: 2026-08-24_

## 결론

CM-CMO에는 `seo-title-creator`의 한국어 검색 근거 게이트를 주축으로, `seo-ops`의 GSC 개선 구간·사후 측정 루프를 결합한 프로젝트 전용 `cm-seo-title-ops`가 가장 적합하다. `claude-seo` 전체 런타임과 `superseo-skills` 전체 묶음은 설치하지 않고, 최신 품질 게이트와 보험 YMYL용 E-E-A-T 점검만 반영한다.

## 코드 리뷰

### 1. claude-seo

- 검토 원본: `AgriciDaniel/claude-seo@09d37c7`
- 장점: URL 안전성, 자격증명 마스킹, 격리 런타임, 테스트가 비교적 잘 갖춰져 있고 FAQ·HowTo 관련 최신 Google 정책을 반영한다.
- **[중간]** 현재 Codex 스킬 검증기에서는 `argument-hint`, `user-invocable` frontmatter가 허용되지 않아 메인 스킬을 그대로 이식할 수 없다.
- 부적합 지점: 25개 스킬, 53개 Python 스크립트, Chromium과 8개 확장까지 포함해 정적 관리자에 비해 의존성과 운영 범위가 지나치게 크다. IndexNow·Indexing API처럼 외부 상태를 바꾸는 기능도 포함한다.
- 내부 도구에 부적합한 출력: 주요 산출물 뒤에 외부 커뮤니티 홍보 문구를 붙이는 규칙이 있다.
- 결정: 전체 설치 제외. 최신 구조화 데이터 정책과 안전한 데이터 경계만 반영.

### 2. seo-ops

- 검토 원본: `ericosiu/ai-marketing-skills@2eb0f34`의 `seo-ops`
- 장점: GSC 4~20위 개선 구간, 자기잠식, 7·14·28·56일 readback 같은 운영 루프가 실무적이다.
- **[높음]** `SKILL.md`에 YAML frontmatter가 없어 표준 스킬 검증과 자동 탐색에 실패한다.
- **[높음]** 스킬 시작 시 버전 확인 네트워크 호출과 대화형 텔레메트리 초기화를 자동 실행한다. 분석 요청과 무관한 실행·쓰기이므로 내부 운영 스킬에 그대로 적용하지 않는다.
- **[중간]** `trend_scout.py`가 `urllib.request.quote`를 호출해 Brave 검색 분기가 실패한다. `urllib.parse.quote`가 맞다.
- **[중간]** 문서는 `.env.example` 복사를 요구하지만 `seo-ops` 폴더에 해당 파일이 없다.
- 결정: 코드와 텔레메트리는 이식하지 않고 GSC 운영 판정과 사후 측정 방식만 적용.

### 3. seo-title-creator

- 검토 원본: `osomahong/seo-title-creator@cec1749`
- 장점: 한국어 표기 변형, 네이버 검색광고 수요, GSC 자기잠식, 후보별 약점, 근거 없을 때 중단하는 규칙이 CM-CMO에 가장 잘 맞는다.
- **[중간]** 현재 Codex 스킬 검증기에서는 `argument-hint`, `compatibility`, `effort`, `model`, `when_to_use` frontmatter가 허용되지 않아 직접 설치가 실패한다.
- **[중간]** Node `fetch()` 호출에 시간 제한이 없어 API 장애 시 실행이 오래 멈출 수 있다.
- **[중간]** `--days`, `--limit`, `--by` 입력값 검증이 없어 잘못된 차원이나 `NaN`이 Google API까지 전달될 수 있다.
- 적용 조정: 현재 관리자는 GSC Secret이 선택 사항이므로 미연결 상태에서도 제목 초안은 보여주되, 추천 후보 선택은 막는다. 원본 GSC 성과값은 정적 JSON에 남기지 않는다.

### 4. superseo-skills

- 검토 원본: `inhouseseo/superseo-skills@0d8b6fc`
- 장점: 경쟁 페이지 비교, 정보 이득, E-E-A-T, 출처·제한사항 점검은 보험 콘텐츠 검수에 유용하다. 실행 코드가 없어 공급망 위험도 작다.
- **[높음]** `page-audit`와 `content-brief`가 FAQ·HowTo 스키마를 검색 기능으로 계속 추천한다. Google은 HowTo 리치결과를 2023년에 폐기했고 FAQ 리치결과도 2026-05-07부터 표시하지 않는다.
- **[중간]** GSC 없이도 7차원 점수와 예상 순위를 제시해 운영 우선순위가 주관적 평가에 치우칠 수 있다.
- 결정: E-E-A-T·일차 출처·정보 이득 점검만 적용. 스키마와 예상 성과 규칙은 제외.

## 적용 범위

- `.claude/skills/cm-seo-title-ops/`: 프로젝트 전용 스킬
- `scripts/seo_title_agent.py`: SearchAd·FAQ·비공개 GSC를 결합한 파워컨텐츠 제목 검토 큐
- `data/adcopy/powercontent-title-opportunities.json`: 공개 가능한 범주형 산출물
- `powercontent-tool.html`: 파워콘텐츠 제목 후보 3개와 검색 근거·약점·검토 상태, 설명·본문 목차·FAQ 브리프 표시
- `seo-audit.html`: 기술 SEO 진단만 유지하며 콘텐츠 제목 후보는 표시하지 않음
- FAQ JSON-LD 복사 기능 제거: FAQ는 고객 질문 콘텐츠로 유지하되 Google 리치결과 효과로 권장하지 않음
- 자동화와 CI: 주간 생성, 개인정보 누출 방지·제목 길이·3후보 계약 테스트

## 정책 근거

- [Google Search 문서 변경 내역](https://developers.google.com/search/updates): FAQ 리치결과는 2026-05-07부터 중단
- [HowTo·FAQ 리치결과 변경](https://developers.google.com/search/blog/2023/08/howto-faq-changes): HowTo 리치결과 폐기와 비지원 마크업의 가시 효과 설명
- [Google 지원 구조화 데이터 목록](https://developers.google.com/search/docs/appearance): 현재 지원 기능 확인
