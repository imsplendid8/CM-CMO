#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BSA 계약기간 검수현황 시트 생성기.

네이버 검색광고 API는 브랜드검색광고(BSA)의 계약 시작/종료일을 제공하지 않는다
(정액제 사전계약 상품이라 /ncc 계열 응답에 계약기간 필드가 없음, 2026-07 기준).
그래서 계약기간은 사람이 bsa_contracts.csv(원장)에 직접 기록하고, 이 스크립트가
  1) 원장의 계약종료일 기준 D-day를 계산하고
  2) bsa_onoff_monitor.py가 만든 최신 스냅샷(bsa_onoff_snapshot.json)과
     캠페인/광고그룹명으로 매칭해 "계약중인데 꺼져있음" / "계약 끝났는데 켜져있음" 같은
     불일치를 잡아낸다.

원장 CSV 컬럼(첫 실행 시 bsa_contracts_sample.csv를 bsa_contracts.csv로 복사해 채울 것):
  사업부,보종,캠페인명,광고그룹명,키워드,계약시작일,계약종료일,계약개월수,월광고비(만원),담당자,비고

사용:
  cp bsa_contracts_sample.csv bsa_contracts.csv   # 최초 1회, 이후 직접 값 채워넣기
  python3 bsa_contract_review.py                  # 검수 시트 생성
  python3 bsa_contract_review.py --warn-days 21   # 만료 임박 기준일 조정(기본 14일)
"""
import argparse
import csv
import json
import os
import sys
from datetime import datetime

LEDGER_FILE = "bsa_contracts.csv"
SNAPSHOT_FILE = "bsa_onoff_snapshot.json"


def load_ledger(path):
    if not os.path.exists(path):
        sys.exit(
            f"{path} 가 없습니다. 최초 1회 다음을 실행하세요:\n"
            f"  cp bsa_contracts_sample.csv {path}\n"
            f"그 다음 실제 계약 정보로 값을 채워넣으세요."
        )
    with open(path, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def load_onoff_snapshot():
    try:
        with open(SNAPSHOT_FILE, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def match_onoff(row, snapshot):
    """원장의 캠페인명/광고그룹명이 스냅샷 항목 이름에 포함되는지로 매칭(느슨한 매칭)."""
    camp_name = row.get("캠페인명", "").strip()
    ag_name = row.get("광고그룹명", "").strip()
    for it in snapshot:
        if camp_name and camp_name in it.get("campaign_name", ""):
            return it["state"]
        if ag_name and ag_name in it.get("adgroup_name", ""):
            return it["state"]
    return "(미매칭 - bsa_onoff_monitor.py 먼저 실행 또는 이름 확인 필요)"


def d_day(end_date_str, today):
    try:
        end = datetime.strptime(end_date_str.strip(), "%Y-%m-%d").date()
    except ValueError:
        return None
    return (end - today).days


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ledger", default=LEDGER_FILE)
    ap.add_argument("--warn-days", type=int, default=14, help="이 일수 이내 만료면 '만료임박'으로 표시(기본 14일)")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    rows = load_ledger(args.ledger)
    snapshot = load_onoff_snapshot()
    today = datetime.now().date()

    out_rows = []
    for row in rows:
        dday = d_day(row.get("계약종료일", ""), today)
        onoff = match_onoff(row, snapshot)
        is_on = onoff.startswith("ON")

        if dday is None:
            action = "계약종료일 형식 오류(YYYY-MM-DD로 입력)"
        elif dday < 0:
            action = ("계약종료 후에도 노출중 - 즉시 확인 필요" if is_on
                      else "계약 만료됨 - 재계약/취소 여부 판단 필요")
        elif dday <= args.warn_days:
            action = f"만료임박(D-{dday}) - 3개월 재계약 vs 취소 후 재계약 판단 필요"
        elif not is_on and "미매칭" not in onoff:
            action = "계약기간 중인데 꺼져있음 - 노출 손실 우려, 확인 필요"
        else:
            action = "정상"

        out_rows.append({**row, "D-day": dday if dday is not None else "", "현재상태(API)": onoff, "액션": action})

    out_path = args.out or f"bsa_contract_review_{datetime.now():%Y%m%d}.csv"
    fieldnames = list(rows[0].keys()) + ["D-day", "현재상태(API)", "액션"]
    with open(out_path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(out_rows)

    urgent = [r for r in out_rows if r["액션"] != "정상" and "오류" not in r["액션"]]
    print(f"[{datetime.now():%Y-%m-%d %H:%M}] 계약 {len(out_rows)}건 검수 → {out_path}")
    if urgent:
        print(f"  액션 필요 {len(urgent)}건:")
        for r in urgent:
            print(f"   - [{r.get('사업부')}] {r.get('캠페인명')}: {r['액션']}")
    else:
        print("  액션 필요 항목 없음")


if __name__ == "__main__":
    main()
