#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BSA 사용 키워드 제안 시트 (검색광고 운영 자동화 2번 항목).

계약 원장(bsa_contracts.csv)의 **사업부·보종 구조를 그대로 재사용**해, 브랜드검색(BSA)에
등록할 후보 키워드를 생성한다. 브랜드검색은 자사 브랜드명이 포함된 검색어만 집행되므로
'브랜드명 + 보종(+수식어)' 조합으로 제안한다.

우선순위(어느 보종을 재계약/신규할지)는 검색량 추이(3번 항목)와 함께 판단한다 —
이 스크립트는 후보 목록만 만들고, 검색량은 붙이지 않는다.

사용:
  python3 bsa_keyword_suggest.py                         # bsa_contracts.csv(없으면 샘플)로 제안
  python3 bsa_keyword_suggest.py --brand "한화손보 다이렉트"
  python3 bsa_keyword_suggest.py --out bsa_kw.csv

출력: bsa_keyword_suggest_YYYYMMDD.csv (사업부·보종·제안키워드·유형·현재계약키워드)
외부 라이브러리 의존 없음(stdlib만).
"""
import argparse
import csv
import os
import sys
from datetime import datetime

LEDGER_FILE = "bsa_contracts.csv"
SAMPLE_FILE = "bsa_contracts_sample.csv"
DEFAULT_BRAND = os.environ.get("BSA_BRAND", "한화손보 다이렉트")
# 브랜드검색 소구 수식어 (빈 문자열 = 브랜드+보종 기본형). 필요 시 조정.
SUFFIXES = ["", "다이렉트", "보험료", "비교", "가입"]


def load_ledger(path):
    p = path if os.path.exists(path) else (SAMPLE_FILE if os.path.exists(SAMPLE_FILE) else None)
    if not p:
        sys.exit(f"{path} 도 {SAMPLE_FILE} 도 없습니다. 계약 원장 또는 샘플이 필요합니다.")
    with open(p, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f)), (os.path.basename(p) == SAMPLE_FILE)


def suggest(brand, bojong):
    """브랜드명 필수 조건에서 브랜드+보종(+수식어) 후보 생성(중복 제거)."""
    out, seen = [], set()
    for suf in SUFFIXES:
        if not suf:
            parts, typ = [brand, bojong], "브랜드+보종"
        elif suf == "다이렉트":
            if "다이렉트" in brand:   # 브랜드에 이미 있으면 중복 방지
                continue
            parts, typ = [brand, suf, bojong], "브랜드+다이렉트+보종"
        else:
            parts, typ = [brand, bojong, suf], f"브랜드+보종+{suf}"
        kw = " ".join(p for p in parts if p).strip()
        if kw and kw not in seen:
            seen.add(kw)
            out.append((kw, typ))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ledger", default=LEDGER_FILE)
    ap.add_argument("--brand", default=DEFAULT_BRAND, help=f"브랜드명(기본: {DEFAULT_BRAND}, 환경변수 BSA_BRAND로도 지정)")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    rows, is_sample = load_ledger(args.ledger)

    # 사업부·보종 유니크 (원장 구조 재사용)
    seen, groups = set(), []
    for r in rows:
        div = (r.get("사업부") or "").strip()
        bojong = (r.get("보종") or "").strip()
        if bojong and (div, bojong) not in seen:
            seen.add((div, bojong))
            groups.append((div, bojong, (r.get("키워드") or "").strip()))

    out_rows = []
    for div, bojong, cur_kw in groups:
        for kw, typ in suggest(args.brand, bojong):
            out_rows.append({"사업부": div, "보종": bojong, "제안 키워드": kw,
                             "유형": typ, "현재 계약 키워드": cur_kw, "비고": ""})

    out_path = args.out or f"bsa_keyword_suggest_{datetime.now():%Y%m%d}.csv"
    fields = ["사업부", "보종", "제안 키워드", "유형", "현재 계약 키워드", "비고"]
    with open(out_path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(out_rows)

    src = "샘플 원장" if is_sample else "계약 원장"
    print(f"[{datetime.now():%Y-%m-%d %H:%M}] {src} {len(groups)}개 보종 → 제안 키워드 {len(out_rows)}개 → {out_path}")
    print(f"  브랜드: {args.brand} · 브랜드검색은 브랜드명 포함 필수")
    print("  ※ 어느 보종을 우선 집행/재계약할지는 검색량 추이(3번 항목)와 함께 판단하세요.")


if __name__ == "__main__":
    main()
