#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""워커 설정 누락·정시 호출 실패 감시(헬스 체크 워크플로에서 6시간마다).

워커 /health는 값 없이 '빠진 설정 이름'과 최근 정시 호출 결과만 돌려준다.
문제가 있으면 같은 제목의 열린 이슈가 없을 때만 이슈를 만들고 텔레그램으로 한 번 알린다(사건당 1회).
문제가 사라지면 그 이슈를 닫는다.

환경변수: WORKER_URL(기본 DEFAULT_PROXY), GITHUB_TOKEN·GITHUB_REPOSITORY(이슈), TELEGRAM_BOT_TOKEN·TELEGRAM_CHAT_IDS(선택)
"""
import json
import os
import sys
import urllib.parse
import urllib.request

DEFAULT_WORKER = "https://modooflow-naver-proxy.angle0102.workers.dev"
ISSUE_TITLE = "⚠️ 워커 설정 누락·정시 호출 실패"
HOW_TO = {
    "USAGE": "Settings → Bindings → KV namespace, Variable name `USAGE`",
    "NAVER_ID": "Settings → Variables and Secrets → Secret `NAVER_ID`(네이버 개발자센터 Client ID)",
    "NAVER_SECRET": "Secret `NAVER_SECRET`(네이버 개발자센터 Client Secret)",
    "AD_KEY": "Secret `AD_KEY`(검색광고 액세스라이선스)",
    "AD_SECRET": "Secret `AD_SECRET`(검색광고 비밀키)",
    "AD_CUSTOMER": "Secret `AD_CUSTOMER`(검색광고 CUSTOMER_ID)",
    "GH_DISPATCH_TOKEN": "Secret `GH_DISPATCH_TOKEN`(GitHub fine-grained 토큰 · CM-CMO · Actions Read and write)",
}


def problems(health):
    """/health 응답 → 사람이 읽을 문제 목록(빈 목록이면 정상)."""
    if not isinstance(health, dict):
        return ["워커 /health 응답을 읽지 못함"]
    if "missing" not in health:
        return ["워커 코드가 최신이 아님 — proxy/naver-proxy-worker.js를 Cloudflare 편집기에 다시 붙여 넣고 Deploy(설정 점검 기능 포함)"]
    out = [f"설정 누락 `{k}` — {HOW_TO.get(k, '워커 설정 확인')}" for k in health.get("missing") or []]
    sched = health.get("scheduler") or {}
    for r in sched.get("results") or []:
        if r.get("ok"):
            continue
        if r.get("reason") == "no_token":
            why = "토큰 없음"
        elif r.get("status") in (401, 403):
            why = f"HTTP {r.get('status')} — 토큰 만료·권한 부족 가능(새 토큰 발급)"
        else:
            why = f"HTTP {r.get('status')}"
        out.append(f"정시 호출 실패 {sched.get('slot')} UTC `{r.get('workflow')}` — {why} → GitHub 예비 실행으로 늦게 발송")
    return out


def _api(method, url, token, body=None):
    req = urllib.request.Request(url, method=method, data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json",
                                          "Content-Type": "application/json", "User-Agent": "modooflow-health"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r) if r.status != 204 else None


def notify_telegram(text):
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chats = [c.strip() for c in (os.environ.get("TELEGRAM_CHAT_IDS") or os.environ.get("TELEGRAM_CHAT_ID") or "").replace("\n", ",").split(",") if c.strip()]
    for chat in chats if token else []:
        data = urllib.parse.urlencode({"chat_id": chat, "text": text, "disable_web_page_preview": "true"}).encode()
        try:
            urllib.request.urlopen(urllib.request.Request(f"https://api.telegram.org/bot{token}/sendMessage", data=data), timeout=15)
        except Exception as e:
            print(f"텔레그램 알림 실패: {type(e).__name__}", file=sys.stderr)


def main():
    url = (os.environ.get("WORKER_URL") or DEFAULT_WORKER).rstrip("/") + "/health"
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "modooflow-health"}), timeout=20) as r:
            health = json.load(r)
    except Exception as e:
        health = None
        print(f"/health 요청 실패: {type(e).__name__}", file=sys.stderr)
    found = problems(health)
    print(json.dumps(health, ensure_ascii=False) if health else "(응답 없음)")
    print("\n".join(found) or "✔ 워커 설정·정시 호출 정상")

    token, repo = os.environ.get("GITHUB_TOKEN"), os.environ.get("GITHUB_REPOSITORY")
    if not (token and repo):
        return 1 if found else 0
    base = f"https://api.github.com/repos/{repo}/issues"
    opened = [i for i in _api("GET", base + "?state=open&per_page=100", token) if i.get("title") == ISSUE_TITLE and "pull_request" not in i]
    if found and not opened:
        body = "워커 `/health` 점검에서 문제가 발견됐습니다(값은 노출되지 않음).\n\n" + "\n".join(f"- {p}" for p in found) + \
               "\n\n위치: Cloudflare → Workers & Pages → `modooflow-naver-proxy` → Settings. 해결되면 다음 점검에서 이 이슈가 자동으로 닫힙니다."
        _api("POST", base, token, {"title": ISSUE_TITLE, "body": body})
        notify_telegram("⚠️ Modooflow 워커 점검\n" + "\n".join(f"· {p}" for p in found))
    elif not found:
        for issue in opened:
            _api("POST", f"{base}/{issue['number']}/comments", token, {"body": "✔ 워커 설정·정시 호출 정상 확인 — 자동으로 닫습니다."})
            _api("PATCH", f"{base}/{issue['number']}", token, {"state": "closed", "state_reason": "completed"})
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
