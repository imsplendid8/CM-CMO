#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""여러 volume JSON을 하나로 병합. 네이버(pc/mobile 분리) 우선, 구글로 빈 값 보강.
사용: python3 scripts/merge_volume.py volume_naver.json volume_google.json > volume.json
"""
import sys, json

def load(f):
    try:
        d = json.load(open(f, encoding="utf-8"))
        return d.get("keywords") or d
    except Exception as e:
        print(f"[skip] {f}: {e}", file=sys.stderr)
        return {}

def main(files):
    out = {}
    for f in files:
        for k, v in load(f).items():
            cur = out.setdefault(k, {})
            for kk, vv in (v or {}).items():
                if kk in ("pc", "mobile"):
                    if not cur.get(kk):
                        cur[kk] = vv
                else:
                    cur.setdefault(kk, vv)
            cur.setdefault("pc", 0); cur.setdefault("mobile", 0)
    json.dump({"keywords": out}, sys.stdout, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main(sys.argv[1:] or ["volume_naver.json"])
