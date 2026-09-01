#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""대기 중인 월간 썸네일을 이미지 생성 API로 만들고 안전하게 승격한다.

기본 동작은 **미리보기만** 한다. 비용이 발생하는 API 호출은 ``--execute``를
명시했을 때만 허용한다. 기본 provider는 OpenAI Images API이며, ``ima2-oauth``를
선택하면 로컬 ima2-gen 서버가 보유한 OAuth 세션을 사용한다. OAuth 토큰은
이 저장소·GitHub Actions·Pages로 전달하지 않는다. 생성된 PNG는 상품별 경로와
PNG 헤더를 검증한 뒤 queue/계획에 반영한다.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
QUEUE_PATH = ROOT / "data/adcopy/image-generation-queue.json"
DEFAULT_API_URL = "https://api.openai.com/v1/images/generations"
DEFAULT_MODEL = "gpt-image-1"
DEFAULT_IMA2_URL = "http://127.0.0.1:3333"
DEFAULT_IMA2_MODEL = "gpt-5.6-luna"
MAX_ERROR_LENGTH = 240
MAX_PNG_BYTES = 5 * 1024 * 1024
MAX_BATCH = 20
LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1"}


def read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(path)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def compact_error(value: Any) -> str:
    text = str(value or "").replace("\r", " ").replace("\n", " ").strip()
    return text[:MAX_ERROR_LENGTH] or "알 수 없는 이미지 생성 오류"


def pending_items(queue: dict[str, Any], product: str = "", retry_failed: bool = False) -> list[dict[str, Any]]:
    statuses = {"pending", "failed"} if retry_failed else {"pending"}
    return [
        item for item in queue.get("items") or []
        if item.get("status") in statuses and (not product or item.get("product_key") == product)
    ]


def asset_target(relative: str, product_key: str) -> Path:
    """생성 파일이 assets/insurance/generated/<상품키>-*.png인지 확인한다."""
    normalized = str(relative or "").replace("\\", "/")
    prefix = f"assets/insurance/generated/{product_key}-"
    if not normalized.startswith(prefix) or not normalized.lower().endswith(".png"):
        raise ValueError("상품별 generated PNG 경로가 아님")
    target = (ROOT / normalized).resolve()
    generated_root = (ROOT / "assets/insurance/generated").resolve()
    try:
        target.relative_to(generated_root)
    except ValueError as exc:
        raise ValueError("생성 파일 경로가 허용된 폴더 밖임") from exc
    return target


def png_dimensions(data: bytes) -> tuple[int, int]:
    if len(data) < 24 or data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("PNG 헤더가 아님")
    return int.from_bytes(data[16:20], "big"), int.from_bytes(data[20:24], "big")


def validate_png(data: bytes, spec: dict[str, Any] | None = None) -> tuple[int, int]:
    max_bytes = min(MAX_PNG_BYTES, int((spec or {}).get("max_bytes") or MAX_PNG_BYTES))
    if len(data) > max_bytes:
        raise ValueError(f"PNG가 {max_bytes // (1024 * 1024)}MB를 초과함")
    width, height = png_dimensions(data)
    minimum = int((spec or {}).get("width") or 214)
    if width != height or width < minimum:
        raise ValueError(f"정사각형 {minimum}px 이상 PNG가 아님: {width}x{height}")
    return width, height


def response_image_bytes(payload: dict[str, Any], opener=urllib.request.urlopen) -> bytes:
    """Images API의 b64_json 응답을 우선 사용하고, URL 응답도 제한적으로 지원한다."""
    rows = payload.get("data") if isinstance(payload, dict) else None
    first = rows[0] if isinstance(rows, list) and rows else {}
    if not isinstance(first, dict):
        raise ValueError("이미지 응답 data가 없음")
    encoded = first.get("b64_json")
    if encoded:
        try:
            return base64.b64decode(str(encoded), validate=True)
        except (ValueError, TypeError) as exc:
            raise ValueError("b64_json 디코딩 실패") from exc
    url = str(first.get("url") or "")
    if url.startswith("https://"):
        with opener(url, timeout=30) as response:
            data = response.read(MAX_PNG_BYTES + 1)
        return data
    raise ValueError("이미지 응답에 b64_json/url이 없음")


def validate_ima2_url(value: str) -> str:
    """OAuth 토큰이 있는 ima2 서버는 로컬 루프백 주소만 허용한다."""
    raw = str(value or DEFAULT_IMA2_URL).strip().rstrip("/")
    parsed = urllib.parse.urlparse(raw)
    host = (parsed.hostname or "").lower()
    if parsed.scheme != "http" or host not in LOOPBACK_HOSTS or not parsed.netloc:
        raise ValueError("ima2 OAuth URL은 http://127.0.0.1(또는 localhost)만 허용")
    return raw


def discover_ima2_url() -> str:
    """ima2가 포트 충돌로 3333 외 포트를 택한 경우 광고 파일에서 찾는다."""
    info_path = Path.home() / ".ima2" / "server.json"
    payload = read_json(info_path, {})
    if not isinstance(payload, dict):
        return ""
    backend = payload.get("backend") if isinstance(payload.get("backend"), dict) else {}
    for candidate in (backend.get("url"), payload.get("url")):
        try:
            return validate_ima2_url(str(candidate or ""))
        except ValueError:
            continue
    return ""


def ima2_image_bytes(payload: dict[str, Any]) -> bytes:
    """ima2 `/api/generate`의 단일 이미지 data URL을 PNG 바이트로 변환한다."""
    rows = payload.get("images") if isinstance(payload, dict) else None
    candidate = payload.get("image") if isinstance(payload, dict) else None
    if not candidate and isinstance(rows, list) and rows and isinstance(rows[0], dict):
        candidate = rows[0].get("image")
    value = str(candidate or "")
    match = re.match(r"^data:image/[^;]+;base64,(.+)$", value, re.S)
    if not match:
        raise ValueError("ima2 응답에 이미지 data URL이 없음")
    try:
        return base64.b64decode(match.group(1), validate=True)
    except (ValueError, TypeError) as exc:
        raise ValueError("ima2 이미지 data URL 디코딩 실패") from exc


def ima2_generate(item: dict[str, Any], server_url: str = DEFAULT_IMA2_URL,
                  model: str = DEFAULT_IMA2_MODEL, size: str = "1024x1024",
                  quality: str = "medium", opener=urllib.request.urlopen) -> bytes:
    """로컬 ima2-gen의 GPT OAuth lane으로 이미지를 생성한다.

    이 함수는 외부 URL이나 Authorization 헤더를 사용하지 않는다. OAuth 토큰은
    사용자의 로컬 ima2 프로세스가 보유하고, 이 저장소에는 토큰이 남지 않는다.
    """
    base = validate_ima2_url(server_url)
    prompt = str(item.get("prompt") or item.get("scene") or "").strip()
    if not prompt:
        raise ValueError("이미지 prompt가 없음")
    prompt = (prompt + "\n보험 광고용 텍스트 없는 프리미엄 3D 애니메이션. "
              "이미지 안에 글자·숫자·로고·워터마크·다른 보험종목을 넣지 않는다.").strip()
    # ima2 CLI는 `oauth/gpt-...` 표기도 허용하지만 API body는 provider와
    # model을 분리해 받으므로, 실수로 lane 접두어가 넘어와도 정규화한다.
    model_name = str(model or DEFAULT_IMA2_MODEL).strip()
    if model_name.startswith("oauth/"):
        model_name = model_name.split("/", 1)[1]
    if not model_name:
        raise ValueError("ima2 모델명이 없음")
    body = json.dumps({
        "prompt": prompt,
        "provider": "oauth",
        "model": model_name,
        "quality": quality,
        "size": size,
        "format": "png",
        "moderation": "low",
        "requestId": f"cm-cmo-{item.get('queue_id') or item.get('proposal_id') or 'image'}",
    }, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        f"{base}/api/generate",
        data=body,
        method="POST",
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            "X-Ima2-Client": "cm-cmo-material-admin",
        },
    )
    with opener(request, timeout=240) as response:
        raw = response.read(MAX_PNG_BYTES * 2)
        status = getattr(response, "status", 200)
    if status < 200 or status >= 300:
        try:
            error_payload = json.loads(raw.decode("utf-8", errors="ignore"))
            error = error_payload.get("error") if isinstance(error_payload, dict) else ""
            message = error.get("message") if isinstance(error, dict) else error
        except (ValueError, AttributeError):
            message = raw.decode("utf-8", errors="ignore")
        raise RuntimeError(f"ima2 OAuth HTTP {status}: {compact_error(message)}")
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError) as exc:
        raise ValueError("ima2 응답 JSON 파싱 실패") from exc
    return ima2_image_bytes(payload)


def openai_generate(item: dict[str, Any], api_key: str, api_url: str = DEFAULT_API_URL,
                    model: str = DEFAULT_MODEL, size: str = "1024x1024",
                    quality: str = "medium", opener=urllib.request.urlopen) -> bytes:
    parsed_url = urllib.parse.urlparse(api_url)
    if parsed_url.scheme != "https" or not parsed_url.netloc:
        raise ValueError("이미지 API URL은 HTTPS 주소여야 함")
    prompt = str(item.get("prompt") or item.get("scene") or "").strip()
    if not prompt:
        raise ValueError("이미지 prompt가 없음")
    # 보험종목별 장면과 무문자 정책은 queue prompt를 보존하면서 한 번 더 고정한다.
    prompt = (prompt + "\n보험 광고용 텍스트 없는 프리미엄 3D 애니메이션. "
              "이미지 안에 글자·숫자·로고·워터마크·다른 보험종목을 넣지 않는다.").strip()
    body = json.dumps({
        "model": model,
        "prompt": prompt,
        "n": 1,
        "size": size,
        "quality": quality,
    }, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        api_url,
        data=body,
        method="POST",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
    )
    with opener(request, timeout=180) as response:
        raw = response.read(MAX_PNG_BYTES * 2)
        status = getattr(response, "status", 200)
    if status < 200 or status >= 300:
        try:
            message = json.loads(raw.decode("utf-8", errors="ignore")).get("error", {}).get("message", "")
        except (ValueError, AttributeError):
            message = raw.decode("utf-8", errors="ignore")
        raise RuntimeError(f"OpenAI Images API HTTP {status}: {compact_error(message)}")
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError) as exc:
        raise ValueError("이미지 API JSON 응답 파싱 실패") from exc
    return response_image_bytes(payload, opener=opener)


def summary(queue: dict[str, Any]) -> dict[str, int]:
    return {status: sum(item.get("status") == status for item in queue.get("items") or [])
            for status in ("pending", "generated", "ready", "failed")}


def save_queue(queue: dict[str, Any]) -> None:
    queue["generated_at"] = utc_now()
    queue["summary"] = summary(queue)
    write_json(QUEUE_PATH, queue)


def sync_plan() -> int:
    # 기존 동기화 함수를 재사용해 실제 파일이 있는 항목만 계획의 asset으로 승격한다.
    try:
        from scripts.image_generation_queue import sync_generated_assets  # type: ignore
    except ModuleNotFoundError:
        from image_generation_queue import sync_generated_assets  # type: ignore
    return sync_generated_assets()


def run(args: argparse.Namespace) -> int:
    if args.limit < 1 or args.limit > MAX_BATCH:
        print(f"[ERROR] --limit은 1~{MAX_BATCH} 사이여야 합니다.", flush=True)
        return 2
    queue = read_json(QUEUE_PATH, {})
    if not isinstance(queue, dict) or not isinstance(queue.get("items"), list):
        print("[ERROR] 이미지 생성 큐를 읽지 못했습니다", flush=True)
        return 2
    items = pending_items(queue, args.product, args.retry_failed)
    if args.limit > 0:
        items = items[:args.limit]
    provider_name = str(getattr(args, "provider", os.environ.get("IMAGE_PROVIDER", "openai")) or "openai").strip().lower()
    if provider_name not in {"openai", "ima2-oauth"}:
        print("[ERROR] --provider는 openai 또는 ima2-oauth만 지원합니다.", flush=True)
        return 2
    retry_note = " · 실패 재시도 포함" if args.retry_failed else ""
    print(f"[INFO] 대상 {len(items)}건 · 상품 필터 {args.product or '전체'}{retry_note} · provider {provider_name}", flush=True)
    if not args.execute:
        requirement = "OPENAI_API_KEY" if provider_name == "openai" else "ima2 setup 후 ima2 serve(로컬 OAuth)"
        print(f"[DRY-RUN] 비용이 발생하는 호출은 하지 않았습니다. 실행하려면 --execute와 {requirement}가 필요합니다.", flush=True)
        for item in items:
            print(f"  - {item.get('product_name', item.get('product_key'))} · {item.get('role')} · {item.get('asset_path')}", flush=True)
        return 0
    if not items:
        print("[OK] 처리할 pending 항목이 없습니다.", flush=True)
        return 0
    api_key = ""
    api_url = ""
    model = ""
    ima2_url = ""
    if provider_name == "openai":
        api_key = os.environ.get("OPENAI_API_KEY", "").strip()
        if not api_key:
            print("[ERROR] OPENAI_API_KEY Secret이 없습니다. API를 호출하지 않았습니다.", flush=True)
            return 2
        api_url = os.environ.get("OPENAI_IMAGE_API_URL", DEFAULT_API_URL).strip() or DEFAULT_API_URL
        parsed_api_url = urllib.parse.urlparse(api_url)
        if parsed_api_url.scheme != "https" or not parsed_api_url.netloc:
            print("[ERROR] OPENAI_IMAGE_API_URL은 HTTPS 주소여야 합니다. API 키 전송을 중단했습니다.", flush=True)
            return 2
        model = os.environ.get("OPENAI_IMAGE_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL
    else:
        try:
            requested_ima2_url = (getattr(args, "ima2_url", "") or os.environ.get("IMA2_SERVER_URL", "")).strip()
            if not requested_ima2_url:
                requested_ima2_url = discover_ima2_url() or DEFAULT_IMA2_URL
            ima2_url = validate_ima2_url(requested_ima2_url)
        except ValueError as exc:
            print(f"[ERROR] {exc}", flush=True)
            return 2
        model = str(getattr(args, "ima2_model", "") or os.environ.get("IMA2_IMAGE_MODEL", DEFAULT_IMA2_MODEL)).strip()
        if not model:
            print("[ERROR] IMA2_IMAGE_MODEL이 비어 있습니다.", flush=True)
            return 2
    size = os.environ.get("IMAGE_SIZE", os.environ.get("OPENAI_IMAGE_SIZE", "1024x1024")).strip() or "1024x1024"
    quality = os.environ.get("IMAGE_QUALITY", os.environ.get("OPENAI_IMAGE_QUALITY", "medium")).strip() or "medium"
    queue["provider"] = provider_name
    queue["provider_model"] = model
    queue["provider_configured_at"] = utc_now()
    run_failures = 0
    for item in items:
        queue_id = str(item.get("queue_id") or "")
        item["attempts"] = int(item.get("attempts") or 0) + 1
        try:
            target = asset_target(str(item.get("asset_path") or ""), str(item.get("product_key") or ""))
            target.parent.mkdir(parents=True, exist_ok=True)
            last_error = ""
            data = b""
            for attempt in range(3):
                try:
                    if provider_name == "ima2-oauth":
                        data = ima2_generate(item, server_url=ima2_url, model=model, size=size, quality=quality)
                    else:
                        data = openai_generate(item, api_key, api_url=api_url, model=model, size=size, quality=quality)
                    break
                except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, RuntimeError, ValueError) as exc:
                    last_error = compact_error(exc)
                    if attempt < 2:
                        time.sleep(2 ** attempt)
            if not data:
                raise RuntimeError(last_error or "이미지 API 응답 없음")
            validate_png(data, item.get("spec") or {})
            temp = target.with_suffix(target.suffix + ".tmp")
            temp.write_bytes(data)
            temp.replace(target)
            item["status"] = "generated"
            item["reference_only"] = False
            item["last_error"] = ""
            item["reason"] = ("ima2-gen GPT OAuth 생성 파일 확인"
                               if provider_name == "ima2-oauth" else "OpenAI Images API 생성 파일 확인")
            item["provider"] = provider_name
            item["generated_at"] = utc_now()
            print(f"[OK] {queue_id} → {target.relative_to(ROOT)}", flush=True)
        except Exception as exc:  # 항목별 실패를 기록하고 다음 항목은 계속한다.
            run_failures += 1
            item["status"] = "failed"
            item["last_error"] = compact_error(exc)
            item["reason"] = "이미지 생성 실패 · 재시도 필요"
            print(f"[ERROR] {queue_id} · {item['last_error']}", flush=True)
        save_queue(queue)

    synced = sync_plan()
    if synced:
        print(f"[OK] 계획 asset 반영 {synced}건", flush=True)
    save_queue(queue)
    # 이전 실행의 failed 항목은 이번 실행 결과가 아니다. 그래야 pending 배치를
    # 계속 생성할 수 있고, 실패 재시도는 --retry-failed로 별도 선택할 수 있다.
    return 1 if run_failures else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true", help="실제 API 호출 및 PNG 저장(기본은 dry-run)")
    parser.add_argument("--limit", type=int, default=4, help="이번 실행에서 처리할 최대 건수(기본 4)")
    parser.add_argument("--product", default="", help="상품 키로 제한(예: driver)")
    parser.add_argument("--retry-failed", action="store_true", help="이전 실행에서 실패한 항목도 재시도")
    parser.add_argument("--provider", choices=("openai", "ima2-oauth"),
                        default=os.environ.get("IMAGE_PROVIDER", "openai").strip().lower() or "openai",
                        help="이미지 생성 provider (기본 openai, 로컬 OAuth는 ima2-oauth)")
    parser.add_argument("--ima2-url", default=os.environ.get("IMA2_SERVER_URL", ""),
                        help="ima2-gen 로컬 서버 주소(비우면 ~/.ima2/server.json 자동 탐색)")
    parser.add_argument("--ima2-model", default=os.environ.get("IMA2_IMAGE_MODEL", DEFAULT_IMA2_MODEL),
                        help="ima2 API에 전달할 모델명(예: gpt-5.6-luna)")
    return run(parser.parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
