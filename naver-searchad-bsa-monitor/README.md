# 네이버 검색광고 BSA 모니터링

CM장기/CM자동차/TM 사업부 검색광고 운영 자동화의 1번 항목:
**BSA(브랜드검색광고) 및 광고그룹 on/off 모니터링 + 계약기간 검수현황 시트.**

Modooflow 대시보드(정적 웹 도구 모음, `index.html` 등)와는 목적이 다른 **별도 CLI 도구**라 이 폴더에
독립적으로 구성했습니다. 대시보드 쪽 코드(HTML/JS/data)는 건드리지 않습니다.

## 왜 두 개로 나눠져 있나 (중요)

네이버 검색광고 Open API(`/ncc/campaigns`, `/ncc/adgroups`)로는 **on/off 상태(살아있는지 꺼져있는지)**
는 조회되지만, **BSA 계약 시작일/종료일은 조회되지 않습니다.** 브랜드검색광고는 정액제로
사전계약하는 상품이라 계약기간이 API 응답에 없습니다(2026-07 기준 확인).

그래서:
- `bsa_onoff_monitor.py` → API로 on/off만 자동 모니터링
- `bsa_contracts.csv` → 계약기간은 **직접 입력해 관리**하는 원장
- `bsa_contract_review.py` → 원장의 계약종료일 + API의 on/off를 교차 검증해서
  "만료임박", "계약중인데 꺼져있음", "계약 끝났는데 켜져있음" 같은 걸 자동으로 잡아줌

## 준비물

1. [네이버 검색광고](https://searchad.naver.com) → 도구 → API 사용 관리에서 발급:
   - API License(Access License) → `NAVER_SEARCHAD_API_KEY`
   - Secret Key → `NAVER_SEARCHAD_SECRET_KEY`
   - 광고주 CUSTOMER ID → `NAVER_SEARCHAD_CUSTOMER_ID`
2. 환경변수로 설정 (키/시크릿은 **절대 코드나 커밋에 넣지 않기**):
   ```bash
   export NAVER_SEARCHAD_API_KEY="..."
   export NAVER_SEARCHAD_SECRET_KEY="..."
   export NAVER_SEARCHAD_CUSTOMER_ID="..."
   ```
3. (선택) 변경 감지 시 카카오 알림을 받으려면 `KAKAO_ACCESS_TOKEN` 설정 —
   발급 방법은 카카오 개발자센터의 '나에게 보내기(memo)' 토큰 방식 참고 (텔레그램 데일리 브리핑 `scripts/daily_brief.py`와 병행 가능).

외부 라이브러리 설치 불필요 (Python 표준 라이브러리만 사용).

## 처음 실행할 때 — 반드시 원본 필드부터 확인

계정마다 캠페인 타입/이름 규칙이 다를 수 있어서, 자동 BSA 판별을 맹신하지 말고
먼저 원본 JSON을 눈으로 확인하세요.

```bash
python3 searchad_client.py
# 또는
python3 bsa_onoff_monitor.py --dump-raw   # bsa_raw_dump.json 생성
```

`campaignTp`/`name` 필드를 보고 실제 BSA 캠페인·광고그룹이 어떻게 표기되는지 확인한 뒤,
필요하면 이름 매칭 키워드를 추가하세요:

```bash
python3 bsa_onoff_monitor.py --keyword "실제캠페인명일부"
```

## 일상 운용

```bash
# 1) on/off 모니터링 (매일 cron 등록 권장)
python3 bsa_onoff_monitor.py --notify
#  → bsa_onoff_YYYYMMDD.csv (현재 전체 현황)
#  → bsa_onoff_changelog.csv (상태 바뀐 이력만 누적)
#  → bsa_onoff_snapshot.json (다음 실행과 비교하기 위한 최신 상태, 커밋 안 함)

# 2) 계약기간 원장 준비 (최초 1회, 이후 계약 갱신/신규 시마다 직접 수정)
cp bsa_contracts_sample.csv bsa_contracts.csv
# → 실제 계약 정보로 값 채워넣기 (사업부/보종/캠페인명/계약시작일/계약종료일/월광고비 등)

# 3) 계약기간 검수 시트 생성
python3 bsa_contract_review.py
#  → bsa_contract_review_YYYYMMDD.csv
#     - D-day, on/off 매칭 상태, 액션(만료임박/불일치/정상) 자동 표기
python3 bsa_contract_review.py --warn-days 21   # 만료임박 기준일 조정
```

`bsa_contract_review.py`의 "액션" 컬럼이 3개월 재계약 vs 취소 후 재계약 판단의
출발점입니다 — 만료임박 항목을 검색량 추이(2번 항목 예정)와 같이 보고 결정하세요.

## 커밋되는 것 / 안 되는 것

- 커밋: 스크립트, `bsa_contracts_sample.csv`(가상 예시 데이터)
- 커밋 안 함(`.gitignore`): 실제 계약 원장(`bsa_contracts.csv`), 스냅샷/CSV 산출물,
  원본 API 덤프 — 전부 실행 결과물이거나 실제 영업 데이터가 들어갈 수 있는 파일

## 파일 구성

| 파일 | 역할 |
|---|---|
| `searchad_client.py` | 네이버 검색광고 API 인증(HMAC-SHA256) + GET 요청 헬퍼 |
| `bsa_onoff_monitor.py` | BSA 캠페인/광고그룹 on/off 자동 모니터링 · 변경 감지 · 카카오 알림 |
| `bsa_contracts_sample.csv` | 계약 원장 템플릿(가상 예시 데이터) |
| `bsa_contract_review.py` | 계약기간 D-day 계산 + on/off 교차검증 → 검수 시트 |

## 다음 항목과의 연결

- 2번(BSA 키워드 제안 시트): 이 원장의 사업부(TM/CM장기/CM자동차)·보종 구조를 그대로 재사용 예정
- 3번(검색량 모니터링): 여기서 나온 "만료임박" 리스트에 검색량 추이를 붙여 재계약 판단 근거로 사용 예정
