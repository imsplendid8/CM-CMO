# 데일리 비서 브리핑 (텔레그램) — 오늘 할 일 판단형

담당자에게 텔레그램으로 하루 **2회(오전 08:00 · 오후 14:00 KST)** 브리핑을 보냅니다.
헤드라인 나열이 아니라 **대시보드 데이터를 읽어 "오늘 할 일"을 우선순위로 판단**합니다:
- **수요 신호**(`data/signals.json` 트리거·기상특보) → 급등/상승 상품 소재·입찰 강화(최우선)
- **시즌 이슈**(`data/seasonal.json`, 이번 달→다음 달) → 시즌 소재 등록·미리 준비(메인 ★ 우선)
- **SERP 상위노출 갭** → 메인 상품 중 요일 순환 1건 점검
- **주목할 뉴스**는 공통 브리프(`data/briefing/latest.json`)의 상위 3건 — 제목·한 문단 요약·출처·원문 링크만 표시
- 변화가 없는 시즌 할 일은 하루 한 건만 순환하고, 수요 급등·기상특보처럼 새 근거가 있는 업무를 우선 표시

## 데이터 상태(자동화 수집 점검)
브리프 하단에 **[데이터 상태]** 를 붙입니다. **저장된 요약을 신뢰하지 않고**, 브리프 생성 직전에
`scripts/check_automation_health.py`의 `compute_health()`가 각 자동화 산출물 파일의 날짜 필드로
`healthy/stale/missing/unknown` 을 매번 새로 계산합니다(읽기 전용·git 불필요·결정론적).
- 대상 5종: 뉴스 클리핑·수요 신호·실측 검색량·데이터랩 트렌드·SERP 캡쳐
- 허용 기간 = 각 cron 주기 + 여유(일간 2·주간 9·월간 35일). 시각을 읽을 수 없으면 **정상으로 단정하지 않고** stale/unknown/미상으로 표시.
- 소스를 전혀 읽을 수 없으면 "상태 확인 불가"로 표시(정상 오표시 방지).
- 단독 확인: `python3 scripts/check_automation_health.py` (또는 `--json`). 테스트: `python3 -m unittest tests.test_automation_health`.

## 구성
- 스크립트: `scripts/daily_brief.py` (표준 라이브러리만; `products.json`·`seasonal.json`·`signals.json`·`clips/` + `check_automation_health` 를 읽음)
- 스케줄: `.github/workflows/daily-brief.yml` (cron `0 23 * * *` = 08:00 KST, 수동 실행도 가능)
- GitHub Actions의 `schedule`은 플랫폼 부하에 따라 늦게 시작될 수 있습니다. 워크플로 실행 요약의 **예약 표현·실제 시작 시각**으로 트리거 지연과 발송 코드 지연을 구분합니다. 10분 이내 정시성이 필요하면 런북의 외부 스케줄러(Cloudflare Worker Cron → `workflow_dispatch`) 방식을 사용합니다.
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
· [경쟁사·현대해상] 페달 오조작 안전장치 보험료 할인 특약
  안전장치 장착 차량의 할인 대상이 확대됐습니다.
  example.com · 2026-07-27 · 원문

🔭 전체 대시보드 → https://imsplendid8.github.io/CM-CMO
```
(🔥/🌡=수요 신호 · ★=오늘 순환 선정된 시즌 집중 업무 · 🔭=SERP 갭 · 뉴스는 공통 브리프에서 자동 선별)

## 설정 (1회) — 텔레그램 봇
1. 텔레그램에서 **@BotFather** → `/newbot` → 봇 이름 지정 → **봇 토큰** 받기.
2. 받을 사람은 각자 만든 봇과 대화 시작(아무 메시지 전송) 후 `chat.id` 확인 — 가장 쉬운 방법은 텔레그램 **@userinfobot** 에게 말 걸어 나오는 `Id` 숫자. (또는 브라우저에서 `https://api.telegram.org/bot<토큰>/getUpdates` 의 `chat.id`.)
3. 저장소 **Settings → Secrets and variables → Actions** 에 추가:
   - `TELEGRAM_BOT_TOKEN` = 봇 토큰
   - **`TELEGRAM_CHAT_IDS`** = 받을 사람들의 chat_id를 **콤마로 구분**(예: `123456789,987654321`). 한 명이면 그 값 하나. (하위호환: 단일 `TELEGRAM_CHAT_ID` 도 계속 지원 — `TELEGRAM_CHAT_IDS` 가 우선)
   - 뉴스는 **뉴스 클리핑(`news-clip.yml`)** 이 적립한 `data/clips/`에서 공통 브리프를 만들고 자동 선별합니다(브리핑이 직접 네이버를 호출하지 않음). 뉴스 클리핑용 `NAVER_CLIENT_ID/SECRET`만 설정돼 있으면 됩니다.
4. **Actions 탭 → Daily Brief → Run workflow** 로 즉시 테스트. 이후 매일 08:00·14:00 KST 자동 발송.

> ⚠️ **개인정보**: chat_id는 개인 식별자입니다. **공개 저장소에 커밋하지 말고 GitHub Secrets(비공개)에만** 넣으세요.

## 수신자·발송시간 관리
공개 GitHub Pages에는 수신자·이메일·API 키를 입력하는 설정 화면을 두지 않습니다.
- 수신자: 저장소 **Settings → Secrets and variables → Actions**에서 `TELEGRAM_CHAT_IDS`를 직접 관리합니다.
- 발송 시간: `.github/workflows/daily-brief.yml`의 UTC cron을 PR로 변경합니다.
- 변경 뒤 **Actions → Daily Brief → Run workflow**로 테스트하고 Run Summary를 확인합니다.

## 시간·내용 바꾸기
- 시간: `daily-brief.yml`의 cron을 PR로 수정합니다(UTC 기준. 08:00 KST=23:00 UTC, 14:00 KST=05:00 UTC).
- 수신자: GitHub Secret `TELEGRAM_CHAT_IDS`를 갱신합니다. 파싱은 `scripts/daily_brief.py`의 `recipients()`(콤마·줄바꿈·세미콜론 구분, 중복 제거).
- 내용: `scripts/daily_brief.py`(시즌·뉴스·SERP 비중), 시즌 데이터는 `data/seasonal.json`.

## 이메일로도 받기 (텔레그램과 별도) — 매일 08:30 KST
텔레그램과 **독립적으로**, 같은 브리핑 본문을 **이메일로 매일 08:30 KST**에 특정 주소로 보냅니다.
같은 공통 뉴스 브리프를 `scripts/daily_brief.py`의 `render_email()`이 모바일 대응 1열 카드로 렌더하고, `--email` 모드로 SMTP 발송합니다. HTML+텍스트 멀티파트이며 중복되는 별도 동향 영역 없이 제목·요약·출처·원문 링크만 표시합니다.

이메일은 `viewport`, 고정 레이아웃 바깥 표, 카드별 자동 줄바꿈을 적용합니다. 구분·제목·출처를 가로 3열로 배치하거나 출처를 한 줄로 고정하지 않으므로 좁은 Gmail·Outlook 모바일 화면에서도 본문이 잘리지 않습니다.

- 스크립트: `python3 scripts/daily_brief.py --email`
- 스케줄: `.github/workflows/daily-email.yml` (cron `30 23 * * *` = **08:30 KST**, 수동 실행도 가능)

### 설정 (1회) — Gmail SMTP 기준
> 수신자·발신 계정·앱 비밀번호는 공개 페이지나 브라우저 저장소가 아니라 GitHub Actions Secrets에서만 관리합니다.
1. 발송용 Gmail 계정에 **2단계 인증**을 켠 뒤 **앱 비밀번호**(16자리)를 발급: Google 계정 → 보안 → 앱 비밀번호.
2. 저장소 **Settings → Secrets and variables → Actions** 에 추가:
   - `SMTP_USER` = 발송 Gmail 주소 (예: `myaccount@gmail.com`)
   - `SMTP_PASS` = 위에서 발급한 **앱 비밀번호**(일반 로그인 비밀번호 아님)
   - **`EMAIL_TO`** = **받을 이메일 주소**(여러 명이면 콤마로 구분)
   - 선택: `SMTP_HOST`(기본 `smtp.gmail.com`) · `SMTP_PORT`(기본 `587`, STARTTLS / `465`=SSL) · `EMAIL_FROM`(기본 `SMTP_USER`)
3. **Actions 탭 → Daily Brief (Email) → Run workflow** 로 즉시 테스트. 이후 매일 08:30 KST 자동 발송.

> ⚠️ **개인정보/보안**: 수신 이메일(`EMAIL_TO`)과 앱 비밀번호(`SMTP_PASS`)는 **커밋하지 말고 GitHub Secrets(비공개)에만** 넣으세요. 발송 시간은 `daily-email.yml`의 cron(UTC)에서 조정합니다(08:30 KST=23:30 UTC 전일).
> Gmail이 아닌 다른 메일 서비스는 `SMTP_HOST`/`SMTP_PORT`만 그 서비스 값으로 바꾸면 됩니다.

## 참고 — 카카오톡 경로
초기엔 카카오 MCP로 테스트했으나(즉석 발송 확인됨), 스케줄 세션의 커넥터 제약으로 **텔레그램(봇 API)** 을 정식 자동화 경로로 채택. 카카오로 받고 싶으면 claude.ai 자동화(Routines) UI에서 카카오 커넥터를 붙인 루틴을 별도로 만들 수 있습니다.
