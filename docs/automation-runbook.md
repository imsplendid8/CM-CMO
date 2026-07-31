# 자동화 실행 런북 (GitHub Actions)

CM-CMO의 데이터 수집·브리프 워크플로 **실행 순서와 충돌 방지** 규칙. (P0-2)

## 스케줄 (UTC ↔ KST)

| 워크플로 | name | 트리거 | cron(UTC) | KST | 쓰는 파일 | push | concurrency |
|---|---|---|---|---|---|---|---|
| signals.yml | Demand Signals | schedule·dispatch | `0 21 * * *` | 매일 06:00 | `data/signals.json` | ✅ | `cm-cmo-data-writers` |
| news-clip.yml | News Clip | schedule·dispatch | `30 22 * * *` / `0 4 * * *` | 매일 07:30 / 13:00 | `data/clips/` | ✅ | `cm-cmo-data-writers` |
| event-reco.yml | Event Recommendations | schedule·dispatch | `45 22 * * *` / `45 4 * * *` | 매일 07:45 / 13:45 | `data/events/recommendations.json`·`state_history.json` | ✅ | `cm-cmo-data-writers` |
| daily-brief.yml | Daily Brief (Telegram) | schedule·dispatch | `0 23 * * *` / `0 5 * * *` | 매일 08:00 / 14:00 | (없음·텔레그램) | ✖ | — (read 전용) |
| searchad.yml | Naver SearchAd Volume | schedule·dispatch | `0 20 * * 0` | 일 05:00 | `data/volume.json` | ✅ | `cm-cmo-data-writers` |
| serp-capture.yml | SERP Capture | schedule·dispatch | `20 21 * * 0` | 월 06:20 | `serp/` | ✅ | `cm-cmo-data-writers` |
| trends.yml | Naver Trends (DataLab) | schedule·dispatch | `10 20 1 * *` | 1일 05:10 | `data/trends.json` | ✅ | `cm-cmo-data-writers` |
| papers.yml | Papers Archive | schedule·dispatch | `0 0 1 * *` | 1일 09:00 | `docs/논문-아카이브.md`·`data/papers.json` | ✅ | `cm-cmo-data-writers` |
| technical-seo.yml | Technical SEO Audit | schedule·dispatch | `0 0 1 * *` | 1일 09:00 | (없음·unlighthouse) | ✖ | — |
| ci.yml | CI | push·PR·dispatch | — | — | ✖ | — |
| pages.yml | Deploy to GitHub Pages | push·**workflow_run**·dispatch | — | (배포) | ✖ | `pages` |

> **automation-health 전용 워크플로는 없음.** 자동화 상태는 브리프 실행 시 `scripts/check_automation_health.py`가 **원천 파일 신선도로 실시간 계산**한다(P0-1). 별도 스냅샷/커밋 워크플로를 만들지 않는다.

## 실행 순서 (수집 → 브리프)

```
오전:  signals(06:00) → news-clip(07:30) → event-reco(07:45) → daily-brief(08:00)
오후:  news-clip(13:00) → event-reco(13:45) → daily-brief(14:00)
```
- 브리프는 **원천 파일 상태를 직접 확인**해 stale/unknown을 표시하므로(P0-1), 수집이 늦거나 실패해도 "정상"으로 오표시하지 않는다.
- 그래서 workflow_run 하드 체이닝 없이 **cron 간격 + 실시간 상태 계산**으로 순서를 보장한다.

## 충돌 방지

1. **공유 concurrency 레인** `cm-cmo-data-writers` — 커밋/푸시하는 7개 워크플로가 같은 그룹을 사용해 GitHub가 **직렬화**(동시에 하나만 실행). `cancel-in-progress: false`로 어떤 실행도 버리지 않는다.
2. **분(minute) 분리 cron** — 같은 UTC 분에 두 커밋 워크플로가 겹치지 않게 stagger:
   - signals `0 21` vs serp `20 21`(일) → 분 분리
   - searchad `0 20`(일) vs trends `10 20`(1일) → 분 분리
   - news-clip 오전을 `30 22`로 이동 → papers `0 0 1`(1일)과의 09:00 겹침 제거
   - event-reco `45 22`/`45 4` → news-clip(`30 22`/`0 4`)·브리프와 분 분리(수집 뒤·브리프 전)
3. **안전 push** — 각 커밋 스텝은 `git pull --rebase --autostash origin main` 후 push, 최대 3회 재시도, 소진 시 명확히 실패(exit 1). 각 워크플로는 **서로 겹치지 않는 경로만** 커밋하므로 rebase가 내용 충돌을 일으키지 않는다.

## workflow_run — 수집 순서엔 미사용 · 배포엔 사용

- **수집 순서**엔 `workflow_run`을 쓰지 않는다. 오전 브리프는 **두 수집(signals + news)** 이 모두 끝나야 이상적이나, `workflow_run` 하나로는 두 upstream의 **fan-in**이 되지 않고(단일 워크플로 완료만 트리거) 중복·경합이 생긴다. P0-1이 브리프에서 신선도를 실시간 계산하므로 하드 순서는 **정확성**엔 불필요(늦으면 stale 표시). → **cron 간격 + 공유 레인 + 안전 push** 조합.
- **배포**엔 `workflow_run`을 쓴다(불가피). 봇 데이터 커밋은 `GITHUB_TOKEN`으로 push하는데, GitHub는 이 토큰의 push로 **다른 워크플로(pages.yml `on: push`)를 트리거하지 않는다**(재귀 방지). 그래서 커밋 워크플로 7종이 완료되면 `pages.yml`이 `workflow_run`으로 재배포해 사이트를 신선하게 유지한다. `workflow_run` 실행은 커밋 워크플로가 **성공**한 경우에만 배포(`if` 가드). fan-in 문제는 배포엔 무해(누가 트리거하든 결과는 "최신 main 배포" 하나).

## 유지보수 주의

- **`concurrency.group` 이름을 바꾸면** 직렬화가 깨진다. 7개 커밋 워크플로는 반드시 동일 그룹(`cm-cmo-data-writers`)을 유지할 것.
- cron을 조정할 때 **같은 UTC 분에 두 커밋 워크플로가 겹치지 않게** 할 것(정적 테스트 `tests/test_workflows.py`가 검사).
- `workflow_dispatch`는 모든 워크플로에 남겨 **수동 복구**가 가능하게 유지.
- 이 규칙은 정적 회귀 테스트로 강제: `python3 -m unittest tests.test_workflows`.
