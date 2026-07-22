# 데일리 비서 브리핑 (텔레그램)

매일 아침 **08:00 KST**에 담당자에게 텔레그램으로 하루 브리핑을 보냅니다 —
`오늘의 시즌 이슈(data/seasonal.json) + 주요 뉴스(선택) + SERP 할일`.

## 구성
- 스크립트: `scripts/daily_brief.py` (표준 라이브러리만, `data/products.json`·`data/seasonal.json`를 읽음)
- 스케줄: `.github/workflows/daily-brief.yml` (cron `0 23 * * *` = 08:00 KST, 수동 실행도 가능)
- 미리보기: `python3 scripts/daily_brief.py --dry` (발송 없이 메시지만 출력)

## 발송 예시
```
🗓️ Modooflow 데일리 비서 · 7/22(수)

☔ 오늘의 시즌 이슈
★ 주택화재보험 — 장마·집중호우·태풍 (누수, 침수, 풍수재)
★ 운전자보험 — 여름 휴가철·렌터카 (휴가철 운전자보험, 렌터카 운전자보험)
· 치아보험 — 방학 치과 성수기 (치아보험, 임플란트, 치아교정)

🔭 SERP 할일 · 한화 상위노출 갭 점검: 주택화재보험 · 골프보험 · 해외여행보험
→ https://imsplendid8.github.io/CM-CMO
```
(★ = 메인 상품군 · 뉴스는 네이버 키 설정 시 자동 포함)

## 설정 (1회) — 텔레그램 봇
1. 텔레그램에서 **@BotFather** → `/newbot` → 봇 이름 지정 → **봇 토큰** 받기.
2. 만든 봇과 대화 시작(아무 메시지 전송) → 브라우저에서 `https://api.telegram.org/bot<토큰>/getUpdates` 열어 `chat.id` 확인.
3. 저장소 **Settings → Secrets and variables → Actions** 에 추가:
   - `TELEGRAM_BOT_TOKEN` = 봇 토큰
   - `TELEGRAM_CHAT_ID` = 내 chat id
   - (선택) `NAVER_CLIENT_ID`, `NAVER_CLIENT_SECRET` = 네이버 개발자센터 검색 API 키(뉴스 포함용)
4. **Actions 탭 → Daily Brief → Run workflow** 로 즉시 테스트. 이후 매일 08:00 KST 자동 발송.

## 시간·내용 바꾸기
- 시간: `daily-brief.yml`의 cron 수정(UTC 기준. 08:00 KST=23:00 UTC).
- 내용: `scripts/daily_brief.py`(시즌·뉴스·SERP 비중), 시즌 데이터는 `data/seasonal.json`.

## 참고 — 카카오톡 경로
초기엔 카카오 MCP로 테스트했으나(즉석 발송 확인됨), 스케줄 세션의 커넥터 제약으로 **텔레그램(봇 API)** 을 정식 자동화 경로로 채택. 카카오로 받고 싶으면 claude.ai 자동화(Routines) UI에서 카카오 커넥터를 붙인 루틴을 별도로 만들 수 있습니다.
