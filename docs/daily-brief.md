# 데일리 비서 브리핑 (텔레그램) — 오늘 할 일 판단형

담당자에게 텔레그램으로 하루 **2회(오전 08:00 · 오후 14:00 KST)** 브리핑을 보냅니다.
헤드라인 나열이 아니라 **대시보드 데이터를 읽어 "오늘 할 일"을 우선순위로 판단**합니다:
- **수요 신호**(`data/signals.json` 트리거·기상특보) → 급등/상승 상품 소재·입찰 강화(최우선)
- **시즌 이슈**(`data/seasonal.json`, 이번 달→다음 달) → 시즌 소재 등록·미리 준비(메인 ★ 우선)
- **SERP 상위노출 갭** → 메인 상품 중 요일 순환 1건 점검
- **주목할 뉴스**는 클리핑(`data/clips/`)에서 **행동가치 키워드**(출시·개편·인상·손해율·적자·사고·호우 등)가 있는 것만 2~3건 — 경쟁사 움직임 가중, 단순 헤드라인 노이즈 제외

## 데이터 상태(자동화 수집 점검)
브리프 하단에 **[데이터 상태]** 를 붙입니다. **저장된 요약을 신뢰하지 않고**, 브리프 생성 직전에
`scripts/check_automation_health.py`의 `compute_health()`가 각 자동화 산출물 파일의 날짜 필드로
`healthy/stale/missing/unknown` 을 매번 새로 계산합니다(읽기 전용·git 불필요·결정론적).
- 대상 6종: 뉴스 클리핑·수요 신호·실측 검색량·데이터랩 트렌드·논문 아카이브·SERP 캡쳐
- 허용 기간 = 각 cron 주기 + 여유(일간 2·주간 9·월간 35일). 시각을 읽을 수 없으면 **정상으로 단정하지 않고** stale/unknown/미상으로 표시.
- 소스를 전혀 읽을 수 없으면 "상태 확인 불가"로 표시(정상 오표시 방지).
- 단독 확인: `python3 scripts/check_automation_health.py` (또는 `--json`). 테스트: `python3 -m unittest tests.test_automation_health`.

## 구성
- 스크립트: `scripts/daily_brief.py` (표준 라이브러리만; `products.json`·`seasonal.json`·`signals.json`·`clips/` + `check_automation_health` 를 읽음)
- 스케줄: `.github/workflows/daily-brief.yml` (cron `0 23 * * *` = 08:00 KST, 수동 실행도 가능)
- 미리보기: `python3 scripts/daily_brief.py --dry` (발송 없이 메시지만 출력)

## 발송 예시
```
🗓️ Modooflow · 7/27(월) 오후 — 오늘 할 일 4

✅ 오늘 할 일 (우선순위)
1. 🔥 해외여행보험 — 검색수요 급등: 소재·입찰 강화 + 랜딩 점검
2. ★ 주택화재보험 — 장마·집중호우·태풍(이번 달): 시즌 소재 등록·랜딩 점검
3. ★ 운전자보험 — 여름 휴가철·렌터카(이번 달): 시즌 소재 등록·랜딩 점검
4. · 치아보험 — 방학 치과 성수기(이번 달): 시즌 소재 등록·랜딩 점검

📰 주목할 뉴스
· [경쟁사·DB손보] 상반기 車보험, 6년 만에 적자···내년 자동차보험료 인상되나 (seoulfn.com)
· [경쟁사·메리츠화재] 미래에셋생명·흥국생명 보험료 인상…'계리감독 선진화' 여파 (shinailbo.co.kr)

🔭 전체 대시보드 → https://imsplendid8.github.io/CM-CMO
```
(🔥/🌡=수요 신호 · ★=메인 상품군 · 🔭=SERP 갭 · 뉴스는 클리핑에서 자동 선별)

## 설정 (1회) — 텔레그램 봇
1. 텔레그램에서 **@BotFather** → `/newbot` → 봇 이름 지정 → **봇 토큰** 받기.
2. 만든 봇과 대화 시작(아무 메시지 전송) → 브라우저에서 `https://api.telegram.org/bot<토큰>/getUpdates` 열어 `chat.id` 확인.
3. 저장소 **Settings → Secrets and variables → Actions** 에 추가:
   - `TELEGRAM_BOT_TOKEN` = 봇 토큰
   - `TELEGRAM_CHAT_ID` = 내 chat id
   - 뉴스는 **뉴스 클리핑(`news-clip.yml`)** 이 적립한 `data/clips/`에서 자동 선별합니다(브리핑이 직접 네이버를 호출하지 않음). 뉴스 클리핑용 `NAVER_CLIENT_ID/SECRET`만 설정돼 있으면 됩니다.
4. **Actions 탭 → Daily Brief → Run workflow** 로 즉시 테스트. 이후 매일 08:00 KST 자동 발송.

## 시간·내용 바꾸기
- 시간: `daily-brief.yml`의 cron 수정(UTC 기준. 08:00 KST=23:00 UTC).
- 내용: `scripts/daily_brief.py`(시즌·뉴스·SERP 비중), 시즌 데이터는 `data/seasonal.json`.

## 참고 — 카카오톡 경로
초기엔 카카오 MCP로 테스트했으나(즉석 발송 확인됨), 스케줄 세션의 커넥터 제약으로 **텔레그램(봇 API)** 을 정식 자동화 경로로 채택. 카카오로 받고 싶으면 claude.ai 자동화(Routines) UI에서 카카오 커넥터를 붙인 루틴을 별도로 만들 수 있습니다.
