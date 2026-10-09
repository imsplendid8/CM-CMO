#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""워커 자동 배포 전, 대시보드에서 만든 KV 네임스페이스를 이름으로 찾아 wrangler.toml에 바인딩을 붙인다.

wrangler deploy는 toml에 없는 바인딩을 지우므로, 대시보드에서 연결한 USAGE(필수)·GSC_TOKENS(선택)를
Cloudflare API로 조회해 같은 바인딩 이름으로 이어 붙인다. ID를 저장소에 커밋하지 않는다(실행 중에만 씀).
필수 바인딩을 못 찾으면 배포를 멈춘다 — 바인딩 없이 배포하면 검색·검색량 조회가 모두 503이 된다.

환경변수: CLOUDFLARE_API_TOKEN, CLOUDFLARE_ACCOUNT_ID
"""
import json
import os
import re
import sys
import urllib.request

# binding → (필수 여부, 네임스페이스 이름 후보) — 안내 문서에서 만들도록 한 이름과 바인딩 이름 자체
KV = {
    "USAGE": (True, ("modooflow-usage", "USAGE", "usage", "modooflow-naver-proxy-USAGE")),
    "GSC_TOKENS": (False, ("modooflow-gsc-tokens", "GSC_TOKENS", "gsc-tokens")),
}


def list_namespaces(token, account):
    out, page = [], 1
    while True:
        req = urllib.request.Request(
            f"https://api.cloudflare.com/client/v4/accounts/{account}/storage/kv/namespaces?per_page=100&page={page}",
            headers={"Authorization": f"Bearer {token}"})
        with urllib.request.urlopen(req, timeout=20) as r:
            data = json.load(r)
        rows = data.get("result") or []
        out += rows
        if len(rows) < 100:
            return out
        page += 1


def pick(namespaces, candidates):
    by_title = {str(n.get("title", "")).strip().lower(): n for n in namespaces}
    for name in candidates:
        if name.lower() in by_title:
            return by_title[name.lower()]
    return None


def attach(toml_text, namespaces):
    """toml 끝에 찾은 KV 바인딩과 keep_vars를 붙인다. (붙인 텍스트, 빠진 필수 바인딩)"""
    if re.search(r"^\s*\[\[kv_namespaces\]\]", toml_text, re.M):
        return toml_text, []   # 이미 toml에 선언돼 있으면 건드리지 않는다
    blocks, missing = [], []
    for binding, (required, candidates) in KV.items():
        ns = pick(namespaces, candidates)
        if ns:
            blocks.append(f'[[kv_namespaces]]\nbinding = "{binding}"\nid = "{ns["id"]}"\n')
        elif required:
            missing.append(binding)
    head = "" if re.search(r"^\s*keep_vars\s*=", toml_text, re.M) else "keep_vars = true\n"
    # 최상위 키는 첫 [table] 앞에 와야 하므로 keep_vars는 맨 앞에 둔다
    return head + toml_text.rstrip() + "\n\n" + "\n".join(blocks), missing


def main(path):
    # 앞뒤 공백·줄바꿈은 붙여넣기 흔적이라 덜어낸다(중간 줄바꿈은 워크플로 검사에서 막음)
    token = (os.environ.get("CLOUDFLARE_API_TOKEN") or "").strip()
    account = (os.environ.get("CLOUDFLARE_ACCOUNT_ID") or "").strip()
    if not (token and account):
        print("CLOUDFLARE_API_TOKEN/CLOUDFLARE_ACCOUNT_ID 필요", file=sys.stderr)
        return 2
    namespaces = list_namespaces(token, account)
    with open(path, encoding="utf-8") as f:
        text, missing = attach(f.read(), namespaces)
    if missing:
        titles = ", ".join(sorted(str(n.get("title")) for n in namespaces)) or "(없음)"
        print(f"::error::필수 KV 바인딩 {missing}의 네임스페이스를 못 찾음 — 계정의 KV 이름: {titles}", file=sys.stderr)
        return 1
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    print("KV 바인딩 연결:", ", ".join(b for b in KV if f'binding = "{b}"' in text) or "toml 선언 사용")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "wrangler.toml"))
