# 뉴스·시즌 이벤트 캘린더 추천 엔진 (P0-EVENT)

전체 뉴스·시즌 캘린더를 결합해 **상품별 문구 추천**을 산출하는 **규칙 기반** 엔진.
LLM 없이 결정론적으로 동작하고, 모든 산출물은 **사람 검토 전 운영 후보**다.

## 구성
- `scripts/event_engine.py` — 순수 함수(run/build_events/make_reco …). 실데이터로 실행 시 `data/events/recommendations.json` 생성.
- `data/events/calendar.json` — 예정 이벤트(공휴일·개학·명절·휴가·대회·지역행사·캠페인). 공개·샘플.
- `data/events/copy_history.json` — 채택 문구 이력(fingerprint+날짜) → cooldown.
- `event-calendar.html` — 뉴스 캘린더 화면(오늘/7일/30일·상태·상품·이벤트 필터·추천·근거·유효기간·검토상태·미분류 큐).
- `tests/test_event_engine.py` — fixture 회귀 테스트(unittest).

## 이벤트 소스 결합 (하드코딩 금지)
특정 이벤트(장마·폭염 등)에 하드코딩하지 않고 아래를 통합한다:
- **예정**: `calendar.json` (날짜 기반)
- **계절**: `data/seasonal.json` (월 배열)
- **기상**: `data/signals.json`의 발효 특보(active)
- **뉴스**: `data/clips/<latest>.json` (대형화재·결항·감염병 등 긴급 포함)
- **검색량**: `data/volume.json` (상품별 실측)
- **이력**: `copy_history.json` (fingerprint cooldown)

## 이벤트 상태
`upcoming → emerging → active → cooling → ended`, 그리고 근거가 이어지면 `follow_up`.
- 날짜 이벤트: 시작 −21일 전=upcoming, −21~시작=emerging, 시작~종료=active, 종료+7일=cooling, 그 뒤=ended(후속근거+follow_up_days면 follow_up).
- 계절(월) 이벤트: 이번 달=active, 다음 달=emerging, 지난 달=cooling.
- **상태가 바뀌면** 추천의 **목적(purpose)과 유효기간**이 달라진다.

## 추천 1건에 담기는 것
확인된 사실(fact) · 관련 상품 · 이벤트 상태 · 제목/설명/콘텐츠 소제목 · 추천 이유+사용 데이터 ·
유효 기간 · 피해야 할 표현 · 추천 채널 · 상품 근거(미확인) · 심의 상태(검토 전·운영 후보) · confidence · fingerprint.

## 상품 매핑 (전 상품 확장)
주택화재·운전자·골프/홀인원·해외여행/장기체류·행사배상·암/여성/치아/유병자 — `products.json`의 13종 전체.
이벤트의 `products` + 상품 `newsQuery`/`newsExtra` + 긴급 키워드 매핑으로 결합.

## 중복 방지 (fingerprint + cooldown)
`fingerprint = sha1(상품 | 이벤트 | 목적 | 문구 코어토큰)`. 문구 코어토큰은 **어미를 제거**해,
같은 뉴스의 **어미만 바꾼 반복**은 같은 fingerprint가 된다. 최근 `COOLDOWN_DAYS(14)` 내 동일
fingerprint는 추천에서 억제한다.

## 가드레일 (생성 금지)
- **공포 조장**(끔찍·참사·당신도·큰일 …), **사건 이용 가입 압박**(지금 안 하면·더 늦기 전에 가입 …),
  **담보·보험금 단정**(무조건 보상·전액 보장·100% 지급 …) → 해당 표현이 섞이면 **추천을 만들지 않는다**.
- 모든 추천: 상품 근거 **미확인**, 심의 **검토 전 · 운영 후보**. **자동으로 "심의 통과"·"등록 가능"으로 표시하지 않는다.**
- 긴급 뉴스는 **예방·점검 안내** 톤만(사건을 이용한 압박 아님).

## 미분류 검토 큐
상품·이벤트·긴급 어디에도 확실히 매핑되지 않는 뉴스는 **자동 문구를 만들지 않고** `unclassified`
큐로 보내 **사람이 분류**한다.

## 실행·검증
```bash
python3 scripts/event_engine.py                 # data/events/recommendations.json 생성
python3 -m unittest tests.test_event_engine     # 회귀 테스트
```
UI는 배포 주소 `event-calendar.html`에서 `recommendations.json`을 읽어 표시(로컬 file://은 미표시 안내).

## 다음 단계(이번 PR 범위 밖)
- 규칙 기반 추천 위에 **LLM 보조**(초안 다양화)는 사람 검토 흐름이 안정된 뒤.
- `recommendations.json` **주기 재생성 워크플로**는 P0-2 충돌 방지 규칙(런북)에 맞춰 별도 검토.
