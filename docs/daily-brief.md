# 데일리 비서 브리핑 (텔레그램) — 오늘 할 일 판단형

담당자에게 텔레그램으로 하루 **2회(오전 08:00 · 오후 14:00 KST)** 브리핑을 보냅니다.
헤드라인 나열이 아니라 **대시보드 데이터를 읽어 "오늘 할 일"을 우선순위로 판단**합니다:
- **수요 신호**(`data/signals.json` 트리거·기상특보) → 급등/상승 상품의 소재·랜딩·입찰 조정 검토 후보(최우선)
- **시즌 이슈**(`data/seasonal.json`, 이번 달→다음 달) → 월요일·구간 전환일에 시즌 소재 점검, 매월 20일 다음 달 준비(메인 ★ 우선)
- **SERP 상위노출 갭** → 월요일에 메인 상품 중 주차 순환 1건 점검
- **주목할 뉴스**는 클리핑(`data/clips/`)에서 **행동가치 키워드**(출시·개편·인상·손해율·적자·사고·호우 등)가 있는 것만 2~3건 — 경쟁사 움직임 가중, 단순 헤드라인 노이즈 제외

## 반복 억제 규칙

- 오전 08시는 계획형 브리프다. `high` 수요 신호는 매일, `medium`은 월·목에만 표시한다.
- 시즌 점검은 월요일 또는 정확한 시즌 구간의 시작·종료 전환일에만 표시한다.
- 다음 달 시즌 준비는 매월 20일 한 번, SERP 점검은 월요일 주 1회만 표시한다.
- 오후 14시는 오전 계획을 반복하지 않고 새 뉴스와 데이터 상태만 보여준다.
- 검색수요만으로 입찰 강화를 확정하지 않고 `입찰 조정 검토`로 표시한다.

이 단계는 별도 상태 저장소 없이 시간·주기 규칙으로 반복을 줄인다. 완료·보류·다시 알림 같은 사용자 상태는 인증된 저장소와 Telegram 버튼을 연결한 뒤 추가한다.

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
- 스케줄: `.github/workflows/daily-brief.yml` (cron `0 23 * * *` = 08:00 KST, `0 5 * * *` = 14:00 KST, 수동 실행도 가능)
- 미리보기: `python3 scripts/daily_brief.py --dry` (발송 없이 메시지만 출력)

## 발송 예시
```
🗓️ Modooflow · 7/27(월) 오전 — 오늘 할 일 4

✅ 오늘 할 일 (우선순위)
1. 🔥 해외여행보험 — 검색수요 급등: 근거 확인 후 소재·랜딩·입찰 조정 검토
2. ★ 주택화재보험 — 장마·집중호우·태풍(이번 달): 시즌 소재 등록·랜딩 점검
3. ★ 운전자보험 — 여름 휴가철·렌터카(이번 달): 시즌 소재 등록·랜딩 점검
4. 🔭 골프보험 — 주간 SERP 점검: 검색결과·경쟁 소구 확인

📰 주목할 뉴스
· [경쟁사·DB손보] 상반기 車보험, 6년 만에 적자···내년 자동차보험료 인상되나 (seoulfn.com)
· [경쟁사·메리츠화재] 미래에셋생명·흥국생명 보험료 인상…'계리감독 선진화' 여파 (shinailbo.co.kr)

🔭 전체 대시보드 → https://imsplendid8.github.io/CM-CMO
```
(🔥/🌡=수요 신호 · ★=메인 상품군 · 🔭=SERP 갭 · 뉴스는 클리핑에서 자동 선별)

## 설정 (1회) — 텔레그램 봇
1. 텔레그램에서 **@BotFather** → `/newbot` → 봇 이름 지정 → **봇 토큰** 받기.
2. 받을 사람은 각자 만든 봇과 대화 시작(아무 메시지 전송) 후 `chat.id` 확인 — 가장 쉬운 방법은 텔레그램 **@userinfobot** 에게 말 걸어 나오는 `Id` 숫자. (또는 브라우저에서 `https://api.telegram.org/bot<토큰>/getUpdates` 의 `chat.id`.)
3. 저장소 **Settings → Secrets and variables → Actions** 에 추가:
   - `TELEGRAM_BOT_TOKEN` = 봇 토큰
   - **`TELEGRAM_CHAT_IDS`** = 받을 사람들의 chat_id를 **콤마로 구분**(예: `123456789,987654321`). 한 명이면 그 값 하나. (하위호환: 단일 `TELEGRAM_CHAT_ID` 도 계속 지원 — `TELEGRAM_CHAT_IDS` 가 우선)
   - 뉴스는 **뉴스 클리핑(`news-clip.yml`)** 이 적립한 `data/clips/`에서 자동 선별합니다(브리핑이 직접 네이버를 호출하지 않음). 뉴스 클리핑용 `NAVER_CLIENT_ID/SECRET`만 설정돼 있으면 됩니다.
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
같은 `scripts/daily_brief.py`의 `build_message()`를 재사용하며, `--email` 모드로 SMTP 발송합니다(HTML+텍스트 멀티파트, 뉴스 '바로가기'는 링크로 렌더).

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
