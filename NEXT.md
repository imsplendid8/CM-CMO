# NEXT — CM-CMO 다음 구현

## P0-EVENT — 이벤트 기반 뉴스·시즌 캘린더 추천 엔진

> 상태: **Phase 1(뉴스 캘린더 문구 엔진) 완료 · main 병합됨** · P0-EVENT **전체는 진행 중**.
> 상세: `docs/news-calendar-copy-engine.md`. 화면 `event-calendar.html`.

### Phase 1 완료분 (규칙 기반 문구 엔진)

전체 뉴스·시즌 캘린더를 결합해 상품별 문구를 **규칙 기반**으로 추천(LLM 없이 결정론). 특정
이벤트(장마·폭염)에 하드코딩하지 않음.
- 소스 결합: 예정 이벤트(`data/events/calendar.json`)·계절(`seasonal.json`)·기상(`signals.json`)·
  뉴스(`clips/`)·검색량(`volume.json`)·사용 이력(`copy_history.json`)
- 이벤트 상태 `upcoming/emerging/active/cooling/ended/follow_up` — 상태 바뀌면 목적·유효기간도 변경
- 추천 1건: 확인된 사실·관련 상품·상태·제목/설명/소제목·이유+데이터·유효기간·피할 표현·채널·
  상품근거(미확인)·심의(검토 전·운영 후보)·confidence·fingerprint
- 상품 전체(주택화재·운전자·골프/홀인원·해외여행/장기·행사배상·암/여성/치아/유병자) 매핑
- 중복 방지: 상품+사건+목적+문구 **fingerprint(어미 제거)** + **cooldown**
- 가드레일: 공포·사건 이용 압박·담보/보험금 단정·과장/최상급 문구 **생성 금지**, 자동 "심의통과/등록가능" 표시 안 함
- 분류 불확실 뉴스 → **unclassified 검토 큐**(자동 문구 X). 빈 키워드가 큐를 비우지 않도록 방어
- 화면 `event-calendar.html`: 오늘/7일/30일·예정/진행/종료/후속·상품·이벤트 필터
- fixture 회귀 테스트 `tests/test_event_engine.py`(22) — 상태·fingerprint·cooldown·가드레일·미분류·비하드코딩·견고성

### Phase 2A — 상태 전이(transition/episode) 엔진 ✅ 완료(main 병합 `1671f90`)

이벤트 상태 **변화**를 감지해 목적·유효기간이 바뀌는 전이 추천을 산출. 상태 델타로만 판정하며
특정 이벤트·날씨에 하드코딩하지 않음.
- **상태 저널** `data/events/state_history.json` — 매 실행 오늘 스냅샷 append(같은 날짜 멱등, 최근 120일)
- `detect_transitions()` — 이전 스냅샷 대비: `onset`(→active)·`winddown`(→cooling)·`resurge`(재활성)·
  `follow_up`·`lifted`(기상특보 해제)·`handoff`(해제 특보 ↔ 신규 특보가 상품 공유 = 장마→폭염식 **전환**)
- 전이 감지 시 목적이 `PURPOSE_BY_TRANSITION`로 바뀌고 **fingerprint·유효기간도 자동 변경**(별개 추천)
- 기상특보→상품 매핑을 **속성 규칙**(`_weather_products`)으로 일반화(종류 하드코딩 제거)
- 화면: `event-calendar.html` 카드에 🔄 전이 배지 + 상태 전이 섹션 + KPI
- 회귀 테스트 `tests/test_event_engine.py`(총 29) — onset/lifted/handoff·**비하드코딩**·전이 fingerprint 변화·결정론

### Phase 2B — 추천 재생성 워크플로 🔶 진행(별도 PR `p0-event/phase2-reco-workflow`)

- `.github/workflows/event-reco.yml` — 매일 07:45·13:45 KST(수집 뒤·브리프 전) `event_engine.py` 재생성 →
  `recommendations.json`·`state_history.json` 커밋. 공유 레인 `cm-cmo-data-writers`·분 분리·안전 push(P0-2)
- 런북(`docs/automation-runbook.md`) 순서·충돌표 갱신, 정적 회귀 테스트(`tests/test_workflows.py`) 추가
- 효과: 클리핑 갱신에 따라 stale해지던 `recommendations.json`을 자동 신선화

### P0-EVENT 남은 작업 (전체 완료 아님)

1. **active window(최근 3일)** 와 **장기 뉴스 archive** 분리·연동 (다음)
2. 뉴스 캘린더 UI ↔ 기존 데일리 브리프 **통합**
3. 긴급 대형화재 감시 → **별도 실시간 알림**(텔레그램 dry-run) 분리

## P0-1 — 브리프 자동화 상태 오표시 수정 ✅ 완료

> 상태: **완료 · main 병합됨(PR #1, squash `11272fc`)**. `scripts/check_automation_health.py`(순수 함수) +
> `scripts/daily_brief.py` 연동 + `tests/test_automation_health.py`(15개) + `ci.yml` 반영.
> Codex 리뷰 P2 2건 반영(미래 날짜 unknown, 논문 no-op 시 papers.json updated 갱신).

### 현재 문제

scripts/daily_brief.py가 저장된 data/automation_health.json의 summary를 그대로 사용하면,
상태 파일 자체가 오래된 경우 실제로 stale인 수집도
“자동수집 6종 정상”으로 표시할 수 있다.

### 구현 대상

- scripts/check_automation_health.py
- scripts/daily_brief.py
- tests/test_news_brief.py 또는 별도 자동화 상태 테스트
- 필요할 경우 docs/daily-brief.md
- 필요할 경우 data/automation_health.json 구조

### 구현 요구사항

1. scripts/check_automation_health.py의 상태 계산 로직을
   다른 코드에서 import할 수 있는 순수 함수로 분리한다.

2. 상태 계산 함수는 각 자동화 항목에 대해 다음 상태를 반환한다.
   - healthy
   - stale
   - missing
   - unknown 또는 unavailable

3. scripts/daily_brief.py는 저장된 summary만 신뢰하지 않는다.
   브리프 메시지 생성 직전에 현재 상태를 다시 계산한다.

4. Git 이력이나 원천 파일을 읽을 수 없으면
   “자동수집 정상”으로 처리하지 말고 “상태 확인 불가”로 표시한다.

5. 브리프에는 최소한 다음 내용을 표시한다.
   - 정상 건수
   - 갱신 필요 건수
   - 누락 또는 확인 불가 건수
   - 갱신이 필요한 자동화 이름
   - 상태 기준 시각

6. 상태 확인만 실행했을 때 data/automation_health.json 등
   추적 파일이 불필요하게 변경되지 않아야 한다.

7. 동일 상태로 재실행하면 결과가 불필요하게 달라지지 않아야 한다.

### 권장 출력 예시

    [데이터 상태]
    · 정상 4건
    · 갱신 필요 2건: 뉴스 클리핑, 수요 신호
    · 누락 0건
    · 기준 시각: 2026-07-27 08:00 KST

상태 계산이 실패하면:

    [데이터 상태]
    · 상태 확인 불가
    · 자동수집이 정상이라고 단정할 수 없음

### 필수 테스트

1. 모든 항목이 최신이면 healthy 개수가 정확한지 확인
2. 허용 기간을 넘긴 항목이 stale로 표시되는지 확인
3. 원천 파일이 없으면 missing으로 표시되는지 확인
4. Git 이력을 사용할 수 없으면 정상으로 오표시하지 않는지 확인
5. 오래된 automation_health.json fixture가 있어도
   “자동수집 6종 정상”으로 잘못 표시되지 않는지 확인
6. dry-run 또는 상태 조회만으로 추적 파일이 변경되지 않는지 확인

### 완료 조건

- 오래된 fixture에서 “자동수집 6종 정상”이 출력되지 않는다.
- healthy, stale, missing, Git 이력 없음 테스트가 있다.
- 테스트가 모두 통과한다.
- 상태 계산 때문에 데이터 스냅샷이 불필요하게 수정되지 않는다.
- 변경 내용을 문서에 간단히 기록한다.
- 별도 작업 브랜치에 커밋하고 PR을 만든다.

### 구현 메모(2026-07-27)

- 상태 판정은 **git 이력이 아니라** 각 산출물 내부 날짜 필드(asof/updated)로 한다 → 결정론·재현 가능.
  시각을 읽을 수 없으면(파일 없음/필드 없음/파싱 실패) healthy 로 처리하지 않는다.
- 대상 자동화 6종: 뉴스 클리핑(`data/clips/index.json`)·수요 신호(`data/signals.json`)·
  실측 검색량(`data/volume.json`)·데이터랩 트렌드(`data/trends.json`)·논문 아카이브(`data/papers.json`)·
  SERP 캡쳐(`serp/manifest.json`). 허용 기간=cron 주기+여유(일간 2·주간 9·월간 35일).
- `compute_health()`는 읽기 전용. `data/automation_health.json`은 만들지 않는다(저장 요약을 신뢰하지 않으므로 불필요).

## P0-2 — GitHub Actions 실행 순서·write 충돌 정리 🔶 진행(별도 PR)

> 상태: 별도 브랜치 `p0-2/actions-ordering`에서 구현. 상세는 `docs/automation-runbook.md`.

- **공유 concurrency 레인** `cm-cmo-data-writers` — 커밋 워크플로 6종 직렬화(동시 push 방지)
- **분(minute) 분리 cron** — 같은 UTC 분 겹침 제거(signals/serp, searchad/trends, news/papers)
- **안전 push** — `git pull --rebase --autostash` + 3회 재시도, 소진 시 실패(각 워크플로는 겹치지 않는 경로만 커밋)
- **실행 순서** — signals(06:00)→news(07:30)→브리프(08:00) / news(13:00)→브리프(14:00)
- **workflow_run 미사용** — 두 수집 fan-in 불가·중복 위험. P0-1 실시간 신선도 계산으로 하드 순서 불필요(늦으면 stale 표시)
- **정적 회귀 테스트** `tests/test_workflows.py` — 중복 write cron·concurrency 누락·workflow_dispatch·workflow_run 대상 검사

## P0-3 — 다음 작업, 이번 PR에서는 구현하지 않음

검색광고 파일을 내부 검토용과 네이버 업로드 흐름으로 분리한다.

- “사전점검 통과”를 “규격 점검 완료”로 변경
- 상품 근거 미확인
- 심의 검토 전
- 운영 후보
- 내부 검토용 Excel 명확화
- 사용자가 내려받은 네이버 대량등록 템플릿을 업로드해 열을 매핑
- 공식 템플릿 확인 전에는 “네이버 업로드 가능”이라고 표시하지 않음
- 상품별 50개를 전략 그룹으로 분류
- 상품별 50행, 전체 650행 다운로드 검증

## 사람 승인 없이는 하지 않는 것

- 보험 광고심의 최종 승인
- 담보·면책·감액·보험료 사실 확정
- 네이버·GitHub·공공데이터 Secret 생성 또는 저장
- 개인정보·임직원 정보·광고계정 원본 커밋
- 근거 없는 CTR·전환율·성과 수치 생성
