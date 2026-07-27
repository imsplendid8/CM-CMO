# NEXT — CM-CMO 다음 구현

## P0-1 — 브리프 자동화 상태 오표시 수정

> 상태(2026-07-27): **이 PR에서 구현 완료** — `scripts/check_automation_health.py`(순수 함수) +
> `scripts/daily_brief.py` 연동 + `tests/test_automation_health.py`. 원천 파일이 main에 없어
> "수정"이 아니라 신규 구현했다(아래 구현 요구사항 충족). 다음 항목은 P0-2.

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

## P0-2 — 다음 작업, 이번 PR에서는 구현하지 않음

뉴스 수집과 automation-health가 같은 시각에 실행되는 충돌을 제거한다.

- 수집 완료 후 상태 점검이 실행되도록 workflow_run 또는 명시적인 의존관계 사용
- write workflow concurrency group 통일
- 자동 커밋 전에 pull --rebase 적용
- 같은 시각 cron 제거
- 오전 브리프 전에 상태 점검 완료

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
