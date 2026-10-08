#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""내 PC에서 구독(OAuth) 세션으로 대기 썸네일을 자동 생성하고 main에 올린다.

GitHub Actions에는 개인 OAuth 세션이 없으므로(토큰을 Secret에 넣지 않는다) 이 실행기는 사용자 PC에서
Windows 작업 스케줄러(scripts/register_image_autogen.ps1)로 매일 한 번 돈다. 대기 항목이 없으면 바로 끝난다.

순서: main 최신화 → ima2-gen 로컬 서버 확인(없으면 백그라운드로 켬) → 대기 항목 N건 생성(--provider ima2-oauth)
     → 큐·이미지 검증 → 생성 파일만 커밋·푸시. 실패하면 커밋하지 않고 큐에 실패 사유만 남긴다.

사용:
  py -3 scripts/local_image_autogen.py               # 기본 8건
  py -3 scripts/local_image_autogen.py --limit 4 --dry-run
"""
from __future__ import annotations

import argparse
import datetime
import json
import shutil
import socket
import subprocess
import sys
import time
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QUEUE = ROOT / "data/adcopy/image-generation-queue.json"
LOG = ROOT / ".image-autogen.log"            # .gitignore 대상 — 로컬 실행 기록
COMMIT_PATHS = ["assets/insurance/generated", "data/adcopy/image-generation-queue.json", "data/adcopy/serp-candidates.json"]
DEFAULT_LIMIT = 8


def log(msg: str) -> None:
    line = f"{datetime.datetime.now():%Y-%m-%d %H:%M:%S} {msg}"
    print(line, flush=True)
    try:
        with LOG.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError:
        pass


def run(cmd: list[str], check: bool = True, **kw) -> subprocess.CompletedProcess:
    res = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, encoding="utf-8", errors="replace", **kw)
    if check and res.returncode != 0:
        raise RuntimeError(f"{' '.join(cmd[:3])} 실패: {(res.stderr or res.stdout).strip()[-400:]}")
    return res


def pending_count(retry_failed: bool = False) -> int:
    try:
        items = json.loads(QUEUE.read_text(encoding="utf-8")).get("items", [])
    except (OSError, ValueError):
        return 0
    states = {"pending", "failed"} if retry_failed else {"pending"}
    return sum(1 for i in items if i.get("status") in states)


def ima2_url() -> str:
    """generate_image_assets와 같은 규칙: ~/.ima2/server.json의 실제 포트, 없으면 3333."""
    sys.path.insert(0, str(ROOT / "scripts"))
    import generate_image_assets as gia  # noqa: E402
    return gia.discover_ima2_url() or gia.DEFAULT_IMA2_URL


def port_open(url: str, timeout: float = 2.0) -> bool:
    parsed = urllib.parse.urlparse(url)
    try:
        with socket.create_connection((parsed.hostname or "127.0.0.1", parsed.port or 80), timeout=timeout):
            return True
    except OSError:
        return False


def ensure_ima2(wait_seconds: int = 60) -> str:
    url = ima2_url()
    if port_open(url):
        return url
    npx = shutil.which("npx") or shutil.which("npx.cmd")
    if not npx:
        raise RuntimeError("Node.js(npx)를 찾지 못함 — nodejs.org에서 LTS 설치 필요")
    log("ima2-gen 로컬 서버가 꺼져 있어 백그라운드로 켭니다")
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) | getattr(subprocess, "DETACHED_PROCESS", 0)
    subprocess.Popen([npx, "-y", "ima2-gen", "serve"], cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                     stdin=subprocess.DEVNULL, creationflags=flags, start_new_session=(flags == 0))
    for _ in range(wait_seconds // 2):
        time.sleep(2)
        url = ima2_url()
        if port_open(url):
            return url
    raise RuntimeError("ima2-gen 서버가 켜지지 않음 — 'npx -y ima2-gen setup'으로 OAuth 로그인을 먼저 확인")


def sync_main() -> None:
    dirty = run(["git", "status", "--porcelain", "--", *COMMIT_PATHS], check=False).stdout.strip()
    if dirty:
        raise RuntimeError("생성 파일 경로에 커밋 안 된 변경이 있음 — 이전 실행 결과를 먼저 정리")
    run(["git", "checkout", "main"])
    run(["git", "pull", "--ff-only", "origin", "main"])


def commit_and_push(count: int) -> bool:
    run(["git", "add", "--", *COMMIT_PATHS])
    if run(["git", "diff", "--cached", "--quiet"], check=False).returncode == 0:
        log("변경 없음 — 커밋 생략")
        return False
    run(["git", "commit", "-m", f"chore(images): 구독 OAuth로 썸네일 {count}건 생성(로컬 자동)"])
    for attempt in range(1, 4):
        if run(["git", "pull", "--rebase", "--autostash", "origin", "main"], check=False).returncode == 0 and \
                run(["git", "push", "origin", "HEAD:main"], check=False).returncode == 0:
            return True
        time.sleep(attempt * 5)
    raise RuntimeError("push 실패 — 네트워크·GitHub 로그인 확인 후 'git push' 수동 실행")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--limit", type=int, default=DEFAULT_LIMIT, help=f"한 번에 만들 최대 건수(1~20, 기본 {DEFAULT_LIMIT})")
    ap.add_argument("--retry-failed", action="store_true", help="이전 실패 항목도 다시 시도")
    ap.add_argument("--dry-run", action="store_true", help="생성·커밋 없이 대상만 확인")
    ap.add_argument("--no-push", action="store_true", help="커밋까지만(푸시 안 함)")
    args = ap.parse_args()
    if not 1 <= args.limit <= 20:
        log("[ERROR] --limit은 1~20")
        return 2
    try:
        if not args.dry_run:
            sync_main()
        todo = pending_count(args.retry_failed)
        if not todo:
            log("대기 썸네일 없음 — 종료")
            return 0
        log(f"대기 {todo}건 중 최대 {args.limit}건 생성 시작")
        gen = [sys.executable, "scripts/generate_image_assets.py", "--provider", "ima2-oauth", "--limit", str(args.limit)]
        if args.retry_failed:
            gen.append("--retry-failed")
        if args.dry_run:
            print(run(gen, check=False).stdout)
            return 0
        url = ensure_ima2()
        before = todo
        res = run([*gen, "--execute", "--ima2-url", url], check=False)
        print(res.stdout[-3000:])
        made = before - pending_count(args.retry_failed)
        run([sys.executable, "scripts/image_generation_queue.py", "--validate"])
        node = shutil.which("node") or shutil.which("node.exe")
        if node:
            run([node, "scripts/check_adcopy_images.mjs"])
        if made <= 0:
            log(f"생성 0건 — 큐의 last_error 확인(생성기 종료코드 {res.returncode})")
            return 1
        if args.no_push:
            run(["git", "add", "--", *COMMIT_PATHS])
            run(["git", "commit", "-m", f"chore(images): 구독 OAuth로 썸네일 {made}건 생성(로컬 자동)"])
            log(f"{made}건 생성·커밋(푸시 생략)")
        elif commit_and_push(made):
            log(f"{made}건 생성·검증·푸시 완료 — 남은 대기 {pending_count()}건")
        return 0 if res.returncode == 0 else 1
    except Exception as exc:  # 스케줄러 실행이라 원인을 로그에 남기고 끝낸다
        log(f"[ERROR] {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
