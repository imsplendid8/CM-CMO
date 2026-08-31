# 자동화 실행 런북 (GitHub Actions)

CM-CMO의 데이터 수집·브리프 워크플로 **실행 순서와 충돌 방지** 규칙. (P0-2)

## 스케줄 (UTC ↔ KST)

| 워크플로 | name | 트리거 | cron(UTC) | KST | 쓰는 파일 | push | concurrency |
|---|---|---|---|---|---|---|---|
| signals.yml | Demand Signals | schedule·dispatch | `30 21 * * *` | 매일 06:30 | `data/signals.json` | ✅ | `cm-cmo-data-writers` |
| news-clip.yml | News Clip | schedule·dispatch | `20 22 * * *` / `20 4 * * *` | 매일 07:20 / 13:20 | `data/clips/`(최신 30일 보관) | ✅ | `cm-cmo-data-writers` |
| event-reco.yml | Event Recommendations | schedule·dispatch | `45 22 * * *` / `45 4 * * *` | 매일 07:45 / 13:45 | `data/events/recommendations.json`·`state_history.json` | ✅ | `cm-cmo-data-writers` |
| automation-status.yml | Automation Health | schedule·dispatch | `40 22 * * *` / `40 4 * * *` | 매일 07:40 / 13:40 | (없음·상태 점검) | ✖(read) | `cm-cmo-automation-status` |
| daily-brief.yml | Daily Brief (Telegram) | schedule·dispatch | `0 23 * * *` / `0 5 * * *` | 매일 08:00 / 14:00 | (없음·텔레그램) | ✖(read) | `cm-cmo-brief-telegram` |
| daily-email.yml | Daily Brief (Email) | schedule·dispatch | `30 23 * * *` | 매일 08:30 | (없음·이메일 SMTP) | ✖(read) | `cm-cmo-brief-email` |
| searchad.yml | Naver SearchAd Volume | schedule·dispatch | `0 20 * * 0` | 일 05:00 | `data/volume.json`·`data/volume-history.json` | ✅ | `cm-cmo-data-writers` |
| serp-capture.yml | SERP Capture | schedule·dispatch | `20 21 * * 0` | 월 06:20 | `serp/` | ✅ | `cm-cmo-data-writers` |
| content-intelligence.yml | Content Intelligence Agents | schedule·dispatch | `10 22 * * 0` | 월 07:10 | `serp/ad_analysis.json`·`data/adcopy/serp-candidates.json`·`data/seo/faq-opportunities.json` | ✅ | `cm-cmo-data-writers` |
| trends.yml | Naver Trends (DataLab) | schedule·dispatch | `10 20 1 * *` | 1일 05:10 | `data/trends.json` | ✅ | `cm-cmo-data-writers` |
| technical-seo.yml | Technical SEO Audit | schedule·dispatch | `0 0 1 * *` | 1일 09:00 | (없음·unlighthouse) | ✖ | — |
| ci.yml | CI | push·PR·dispatch | — | — | ✖ | — |
| pages.yml | Deploy to GitHub Pages | push·**workflow_run**·dispatch | — | (배포) | ✖ | `pages` |

> **자동화 상태**: `automation-status.yml`(07:40·13:40, 수집 뒤·브리프 전)이 `scripts/check_automation_health.py`를 실행해 **Run 요약에 표시**한다(커밋 없음·읽기 전용). 브리프(텔레그램/이메일)도 발송 직전 `check_automation_health`로 **원천 파일 신선도를 실시간 재계산**한다(P0-1, healthy/stale/missing/unknown 분리). 저장 스냅샷(`data/automation_health.json`)은 만들지 않는다(저장 요약 미신뢰).

Content Intelligence의 Search Console 입력은 `GSC_SITE_URL`, `GSC_CLIENT_ID`, `GSC_CLIENT_SECRET`, `GSC_REFRESH_TOKEN` Secret이 모두 있을 때만 수집한다. 원본 `data/search-console.json`은 커밋하지 않는다. SERP DOM 추출값은 구조 변경 가능성이 있으므로 `serp/dom_observations.json`에 `needs_review`로 저장하고 승인된 `ad_observations.json`과 자동 병합하지 않는다.

## 실행 순서 (수집 → 브리프)

```
오전:  signals(06:30) → news-clip(07:20) → automation-status(07:40) → event-reco(07:45) → daily-brief(08:00) → daily-email(08:30)
오후:  news-clip(13:20) → automation-status(13:40) → event-reco(13:45) → daily-brief(14:00)
```
- 브리프는 **원천 파일 상태를 직접 확인**해 stale/unknown을 표시하므로(P0-1), 수집이 늦거나 실패해도 "정상"으로 오표시하지 않는다.
- 그래서 workflow_run 하드 체이닝 없이 **cron 간격 + 실시간 상태 계산**으로 순서를 보장한다.

## 충돌 방지

1. **커밋 워크플로 공유 concurrency 레인** `cm-cmo-data-writers` — 커밋/푸시하는 7개 워크플로(signals·news-clip·event-reco·searchad·serp-capture·content-intelligence·trends)만 같은 그룹을 사용한다. `cancel-in-progress: false`로 커밋 작업을 버리지 않고 main push 충돌을 직렬화한다.
2. **읽기 전용 레인 분리** — `automation-status`, `daily-brief`, `daily-email`은 각각 독립 그룹을 사용한다. 읽기 작업이 길어진 수집 작업 뒤에서 대기하지 않으며, 각 실행은 `ref: main`으로 시작 시점의 최신 커밋을 읽는다. 브리프 본문에는 원천 파일이 아직 늦었는지 상태가 표시된다.
3. **분(minute) 분리 cron** — 같은 UTC 분에 두 커밋 워크플로가 겹치지 않게 stagger:
   - signals `30 21` vs serp `20 21`(일) vs content-intelligence `10 22`(일) → 분 분리
   - searchad `0 20`(일) vs trends `10 20`(1일) → 분 분리
   - news-clip `20 22`/`20 4`, automation-status `40 22`/`40 4`, event-reco `45 22`/`45 4` → 서로·브리프와 분 분리
   - event-reco `45 22`/`45 4` → news-clip(`30 22`/`0 4`)·브리프와 분 분리(수집 뒤·브리프 전)
4. **안전 push** — 각 커밋 스텝은 `git pull --rebase --autostash origin main` 후 push, 최대 3회 재시도, 소진 시 명확히 실패(exit 1). 각 워크플로는 **서로 겹치지 않는 경로만** 커밋하므로 rebase가 내용 충돌을 일으키지 않는다.

### 예약 시각의 한계와 확인 방법

GitHub Actions의 `schedule` 이벤트는 플랫폼 부하에 따라 예약 시각보다 늦게 생성될 수 있고, 정시 발송 SLA를 보장하지 않는다. 실제 지연이 코드 내부가 아닌 트리거 단계인지 구분할 수 있도록 텔레그램·이메일 실행 요약에 예약 표현과 실제 시작 시각(UTC/KST)을 기록한다. 10분 이내 정시성이 업무 요건이면 GitHub cron 대신 외부 스케줄러(예: Cloudflare Worker Cron)가 GitHub `workflow_dispatch`를 호출하는 구조가 필요하다. 수동 실행은 기존처럼 유지한다.

## workflow_run — 수집 순서엔 미사용 · 배포엔 사용

- **수집 순서**엔 `workflow_run`을 쓰지 않는다. 오전 브리프는 **두 수집(signals + news)** 이 모두 끝나야 이상적이나, `workflow_run` 하나로는 두 upstream의 **fan-in**이 되지 않고(단일 워크플로 완료만 트리거) 중복·경합이 생긴다. P0-1이 브리프에서 신선도를 실시간 계산하므로 하드 순서는 **정확성**엔 불필요(늦으면 stale 표시). → **cron 간격 + 공유 레인 + 안전 push** 조합.
- **배포**엔 `workflow_run`을 쓴다(불가피). 봇 데이터 커밋은 `GITHUB_TOKEN`으로 push하는데, GitHub는 이 토큰의 push로 **다른 워크플로(pages.yml `on: push`)를 트리거하지 않는다**(재귀 방지). 그래서 커밋 워크플로 7종이 완료되면 `pages.yml`이 `workflow_run`으로 재배포해 사이트를 신선하게 유지한다. `workflow_run` 실행은 커밋 워크플로가 **성공**한 경우에만 배포(`if` 가드). fan-in 문제는 배포엔 무해(누가 트리거하든 결과는 "최신 main 배포" 하나).

## 유지보수 주의

- **`concurrency.group` 이름을 바꾸면** 의도한 충돌 방지가 깨진다. 커밋 7종은 `cm-cmo-data-writers`, 텔레그램·이메일·상태점검은 각각 `cm-cmo-brief-telegram`, `cm-cmo-brief-email`, `cm-cmo-automation-status`를 유지한다.
- cron을 조정할 때 **같은 UTC 분에 두 커밋 워크플로가 겹치지 않게** 할 것(정적 테스트 `tests/test_workflows.py`가 검사).
- `workflow_dispatch`는 모든 워크플로에 남겨 **수동 복구**가 가능하게 유지.
- 이 규칙은 정적 회귀 테스트로 강제: `python3 -m unittest tests.test_workflows`.
