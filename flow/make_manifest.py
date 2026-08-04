#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
capture_masked/ 폴더를 스캔해 대시보드가 읽을 manifest(captures.js)를 생성합니다.
(브라우저는 폴더 목록을 직접 읽지 못하므로, 이 목록 파일이 필요합니다.)

파일명 규칙:  회사_케이스_STEP번호화면명_세부[_masked].png
  예) 삼성_신규_STEP3담보선택_업셀링팝업.png
      KB_갱신_STEP5본인인증_3.png
  - 회사   = 첫 토큰 (삼성/현대/DB/KB/당사 → 익명화 S사/H사/D사/K사/당사)
  - 케이스 = 둘째 토큰 (신규/갱신/만기도래/만기미도래)
  - STEP   = 셋째 토큰 "STEP<번호><화면명>" → 번호(n)·화면명(step) 분리
  - 세부   = 넷째 이후 토큰 (본인인증 하위화면·팝업·분기 등) → detail

이렇게 만들어진 captures.js를 두면 대시보드(프로토타입 As-Is·용어 캡쳐별 보기)가
회사_케이스_STEP 기준으로 캡쳐를 화면에 '자동 매핑'합니다.

사용:
  python3 make_manifest.py
  # 마스킹(수동/자동) 후 한 번 실행 → capture_masked/captures.js 갱신 → 대시보드 새로고침
"""
import os, re, sys, json, glob

MASKED_DIR = sys.argv[1] if len(sys.argv) > 1 else "capture_masked"
EXTS = ("*.png", "*.jpg", "*.jpeg", "*.webp")

# 외부 제출물 익명화 — 실제 회사명 → 익명 라벨 (거버넌스: 외부엔 익명만)
CO_MAP = {
    "삼성": "S사", "현대": "H사", "DB": "D사", "KB": "K사",
    "메리츠": "M사", "한화": "W사", "당사": "당사",
}
STEP_RE = re.compile(r"^STEP\s*(\d+)\s*(.*)$", re.IGNORECASE)


def parse(stem):
    if stem.endswith("_masked"):
        stem = stem[: -len("_masked")]
    parts = stem.split("_")
    co_raw = parts[0] if len(parts) > 0 else "기타"
    co = CO_MAP.get(co_raw, co_raw)
    case = parts[1] if len(parts) > 1 else ""
    n, step = "", ""
    if len(parts) > 2:
        m = STEP_RE.match(parts[2])
        if m:
            n, step = m.group(1), m.group(2).strip()
        else:
            step = parts[2]
    detail = "_".join(parts[3:]) if len(parts) > 3 else ""
    return {"co": co, "case": case, "n": n, "step": step, "detail": detail}


def build(masked_dir=MASKED_DIR):
    files = sorted(
        os.path.basename(f)
        for e in EXTS
        for f in glob.glob(os.path.join(masked_dir, e))
    )
    caps = []
    for fn in files:
        info = parse(os.path.splitext(fn)[0])
        info["file"] = fn
        caps.append(info)
    os.makedirs(masked_dir, exist_ok=True)
    out = os.path.join(masked_dir, "captures.js")
    with open(out, "w", encoding="utf-8") as f:
        f.write("window.CAPTURES = " + json.dumps(caps, ensure_ascii=False, indent=1) + ";\n")
    return out, len(caps)


if __name__ == "__main__":
    path, n = build()
    print(f"manifest 생성: {path} ({n}개 캡쳐)")
    if n == 0:
        print("⚠️ capture_masked/ 에 이미지가 없습니다. 마스킹 후 다시 실행하세요.")
