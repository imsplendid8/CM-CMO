# 수요 신호 API 설정표

GitHub Actions는 Secret 값을 코드에 넣지 않고 `scripts/fetch_signals.py`에 전달한다.
아래처럼 서비스별 URL과 키를 분리하면 운전자보험 수요와 해외여행 수요를 같은
`data/signals.json`에 기록할 수 있다.

## 자동차 신규등록정보

### data.go.kr REST URL을 발급받은 경우(권장)

Repository Settings → Secrets and variables → Actions → New repository secret에서
다음 두 값만 먼저 등록한다.

| Secret | 넣을 값 |
|---|---|
| `CAR_NEWREG_API_URL` | data.go.kr 서비스 상세 화면의 **Open API 호출 URL** 전체 |
| `CAR_NEWREG_KEY` | data.go.kr 마이페이지의 일반 인증키(Decoding 또는 Encoding 키) |

이 방식은 `form_id`와 `style_num`을 사용하지 않는다. 서비스 문서에서 시도·차종·
등록월 같은 추가 파라미터를 요구하면 다음 Secret에 JSON 객체로 넣는다.

```json
{"sido":"서울","vehicleType":"승용"}
```

```text
CAR_NEWREG_EXTRA_PARAMS={"sido":"서울","vehicleType":"승용"}
```

서비스가 요구하는 실제 필드명은 API 상세 문서의 요청 파라미터 표를 그대로 따른다.
코드는 `serviceKey`, `dataType=JSON`, `pageNo`, `numOfRows`를 기본으로 붙이고,
기간을 요구하는 서비스에는 `CAR_NEWREG_START_DT`·`CAR_NEWREG_END_DT`를 넣었을 때만
`startDt`·`endDt`를 추가한다. 그 밖의 기간 필드는 `CAR_NEWREG_EXTRA_PARAMS`로
전달한다. 응답의 `totalCount` 또는 카운트 필드를 읽는다.

### 통계누리 URL인 경우

`stat.molit.go.kr` URL은 기존 규격을 사용하므로 아래 네 값이 모두 필요하다.

```text
CAR_NEWREG_API_URL
CAR_NEWREG_KEY
CAR_NEWREG_FORM_ID
CAR_NEWREG_STYLE_NUM
```

`form_id`·`style_num`은 data.go.kr 화면의 인증키가 아니다. 통계누리 Open API
호출 화면의 요청 URL/샘플 코드에 표시되는 표·서식 식별자다. 찾을 수 없으면
data.go.kr REST URL 방식으로 전환하는 편이 안전하다.

## 해외여행 수요

```text
TOUR_API_URL=<한국문화관광연구원 출입국관광통계 서비스 URL>
TOUR_API_KEY=<승인된 인증키>
```

기간·응답 형식이 필요한 서비스는 `TOUR_API_FORMAT`, `TOUR_API_START_DT`,
`TOUR_API_END_DT`, `TOUR_API_PAGE_NO`, `TOUR_API_NUM_OF_ROWS`를 추가한다.
응답이 JSON/XML 중 어느 쪽이든 숫자 필드를 찾아 `exit_tour.outbound_count`로
정규화하지만, 실제 지표명은 첫 실행 후 `data/signals.json`의 `raw_hint`와
`period`를 확인해 상품 담당자가 검증해야 한다.

## 동작 확인

1. Secret을 저장한다. 키 자체를 채팅이나 저장소 파일에 붙여 넣지 않는다.
2. Actions → **Demand Signals** → **Run workflow**를 실행한다.
3. 로그에서 `data/signals.json` 생성 여부를 확인한다.
4. `newreg.source`, `newreg.count`, `newreg.period`, `newreg.mom`, `newreg.series`,
   `newreg.error`를 확인한다.
   `count`가 없으면 호출 실패이지 수요 0이 아니다.
5. 성공한 뒤에만 운전자보험 트리거가 `자동차 신규등록(...)` 근거를 표시한다.

키 누락·권한 오류·필드 불일치는 기존 신호를 임의로 성공 처리하지 않고 오류 상태로
남긴다. 실제 응답의 필드명이 다른 경우에는 API 키를 다시 발급할 필요 없이
`_extract_molit_count`의 응답 매핑만 서비스 문서에 맞춰 보정한다.
