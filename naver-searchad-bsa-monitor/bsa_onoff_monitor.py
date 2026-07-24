#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
네이버 검색광고 - 브랜드검색광고(BSA) 및 광고그룹 on/off 모니터링.

무엇을 하는가:
  1) /ncc/campaigns 전체 조회 → /ncc/adgroups로 캠페인별 광고그룹 조회
  2) BSA로 추정되는 캠페인·광고그룹만 골라낸다 (판별 방법은 아래 "BSA 판별 한계" 참고)
  3) 현재 on/off 상태를 스냅샷(JSON)으로 저장하고, 직전 스냅샷과 비교해 바뀐 항목만 뽑는다
  4) 이번 회차 전체 현황을 CSV로, 변경 이력을 changelog CSV에 누적한다

BSA 판별 한계 (중요, 반드시 1회 확인 필요):
  네이버 검색광고 공개 API 문서상 캠페인 타입 필드(campaignTp)에 브랜드검색이
  별도 값으로 노출되는지는 계정/상품 버전에 따라 다를 수 있다. 이 스크립트는
    (a) campaignTp/adgroup 쪽 타입 필드에 "BRAND_SEARCH"가 있으면 그것으로,
    (b) 없으면 캠페인·광고그룹 이름에 --keyword 로 지정한 문자열(기본: 브랜드검색, BSA)이
        포함되는지로 판별한다.
  처음 쓸 때는 반드시 `python3 searchad_client.py` 또는 `--dump-raw` 옵션으로
  실제 계정의 원본 JSON을 눈으로 확인하고, 이름 매칭 키워드가 실제 캠페인명과
  맞는지 검수할 것. (자동 판별을 100% 신뢰하지 말 것)

계약기간(시작일/종료일)은 이 API로 조회되지 않는다:
  브랜드검색광고는 정액제 사전계약 상품이라 계약 시작/종료일이 /ncc 계열
  API 응답에 포함되지 않는다(2026-07 기준 확인). 계약기간 검수는
  bsa_contracts.csv(수동 관리 원장)와 bsa_contract_review.py를 사용할 것.

환경변수:
  NAVER_SEARCHAD_API_KEY / NAVER_SEARCHAD_SECRET_KEY / NAVER_SEARCHAD_CUSTOMER_ID (필수)
  KAKAO_ACCESS_TOKEN (선택: --notify 사용 시, news_watch.py와 동일한 카카오 '나에게 보내기')

사용:
  python3 bsa_onoff_monitor.py                      # 1회 실행, CSV 출력
  python3 bsa_onoff_monitor.py --dump-raw            # 원본 캠페인/광고그룹 JSON도 함께 저장(필드 검수용)
  python3 bsa_onoff_monitor.py --keyword 브랜드검색 --keyword BSA
  python3 bsa_onoff_monitor.py --notify              # 변경 감지 시 카카오 알림
"""
import argparse
import csv
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime

from searchad_client import SearchAdAPIError, SearchAdAuthError, SearchAdClient

SNAPSHOT_FILE = "bsa_onoff_snapshot.json"
CHANGELOG_FILE = "bsa_onoff_changelog.csv"
RAW_DUMP_FILE = "bsa_raw_dump.json"
DEFAULT_KEYWORDS = ["브랜드검색", "BSA", "브랜드 검색"]

KAKAO_SEND_URL = "https://kapi.kakao.com/v2/api/talk/memo/default/send"


def is_bsa(kind, obj, keywords):
    """kind: 'campaign' | 'adgroup'. campaignTp 필드가 BRAND_SEARCH면 우선 채택,
    아니면 name에 키워드가 포함되는지로 판별."""
    tp = obj.get("campaignTp") or obj.get("adgroupTp") or obj.get("type") or ""
    if "BRAND_SEARCH" in str(tp).upper():
        return True
    name = obj.get("name", "")
    return any(kw in name for kw in keywords)


def effective_state(obj):
    """status/userLock을 사람이 읽을 수 있는 on/off로 정리.
    status='ELIGIBLE'이고 userLock이 아니면 ON, userLock이거나 PAUSED류면 OFF,
    그 외(DELETED, UNDER_REVIEW 등)는 상태값 그대로 노출."""
    status = obj.get("status", "")
    user_lock = bool(obj.get("userLock"))
    if user_lock:
        return "OFF(수동중지)"
    if status == "ELIGIBLE":
        return "ON"
    if status in ("PAUSED",):
        return "OFF"
    return f"기타({status or '?'})"


def fetch_bsa_items(client, keywords, dump_raw=False):
    campaigns = client.list_campaigns()
    raw = {"campaigns": campaigns, "adgroups": {}}
    items = []
    for camp in campaigns:
        camp_id = camp.get("nccCampaignId")
        camp_is_bsa = is_bsa("campaign", camp, keywords)
        try:
            adgroups = client.list_adgroups(camp_id)
        except SearchAdAPIError as e:
            print(f"  (광고그룹 조회 실패 campaign={camp_id}: {e})", file=sys.stderr)
            adgroups = []
        if dump_raw:
            raw["adgroups"][camp_id] = adgroups
        for ag in adgroups:
            if not (camp_is_bsa or is_bsa("adgroup", ag, keywords)):
                continue
            items.append({
                "id": ag.get("nccAdgroupId"),
                "campaign_id": camp_id,
                "campaign_name": camp.get("name", ""),
                "adgroup_name": ag.get("name", ""),
                "state": effective_state(ag),
                "status_raw": ag.get("status", ""),
                "user_lock": bool(ag.get("userLock")),
                "reg_tm": ag.get("regTm", ""),
                "edit_tm": ag.get("editTm", ""),
            })
        # 캠페인 자체가 BSA로 잡혔는데 광고그룹이 하나도 안 걸린 경우도 캠페인 단위로 기록
        if camp_is_bsa and not any(it["campaign_id"] == camp_id for it in items):
            items.append({
                "id": camp_id,
                "campaign_id": camp_id,
                "campaign_name": camp.get("name", ""),
                "adgroup_name": "(캠페인 단위)",
                "state": effective_state(camp),
                "status_raw": camp.get("status", ""),
                "user_lock": bool(camp.get("userLock")),
                "reg_tm": camp.get("regTm", ""),
                "edit_tm": camp.get("editTm", ""),
            })
    if dump_raw:
        with open(RAW_DUMP_FILE, "w", encoding="utf-8") as f:
            json.dump(raw, f, ensure_ascii=False, indent=2)
        print(f"  (원본 JSON 저장: {RAW_DUMP_FILE} — BSA 판별 필드가 맞는지 이걸로 검수)")
    return items


def load_snapshot():
    try:
        with open(SNAPSHOT_FILE, encoding="utf-8") as f:
            return {row["id"]: row for row in json.load(f)}
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_snapshot(items):
    with open(SNAPSHOT_FILE, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=1)


def diff_items(prev, items):
    changes = []
    for it in items:
        before = prev.get(it["id"])
        if before is None:
            changes.append({"id": it["id"], "campaign_name": it["campaign_name"],
                             "adgroup_name": it["adgroup_name"],
                             "before": "(신규발견)", "after": it["state"]})
        elif before.get("state") != it["state"]:
            changes.append({"id": it["id"], "campaign_name": it["campaign_name"],
                             "adgroup_name": it["adgroup_name"],
                             "before": before.get("state"), "after": it["state"]})
    return changes


def write_status_csv(items, path):
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["캠페인명", "광고그룹명", "상태", "status(raw)", "수동중지", "등록일", "수정일", "nccAdgroupId/campaignId"])
        for it in items:
            w.writerow([it["campaign_name"], it["adgroup_name"], it["state"], it["status_raw"],
                        "Y" if it["user_lock"] else "N", it["reg_tm"], it["edit_tm"], it["id"]])


def append_changelog(changes):
    is_new = not os.path.exists(CHANGELOG_FILE)
    with open(CHANGELOG_FILE, "a", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        if is_new:
            w.writerow(["감지시각", "캠페인명", "광고그룹명", "이전상태", "변경후상태", "id"])
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        for c in changes:
            w.writerow([now, c["campaign_name"], c["adgroup_name"], c["before"], c["after"], c["id"]])


def kakao_notify(changes):
    token = os.environ.get("KAKAO_ACCESS_TOKEN")
    if not token:
        print("  (KAKAO_ACCESS_TOKEN 없음 — 알림 생략)", file=sys.stderr)
        return
    lines = [f"- {c['campaign_name']}/{c['adgroup_name']}: {c['before']} → {c['after']}" for c in changes[:10]]
    text = "[BSA on/off 변경 감지]\n" + "\n".join(lines)
    if len(changes) > 10:
        text += f"\n... 외 {len(changes) - 10}건"
    template = {"object_type": "text", "text": text}
    data = urllib.parse.urlencode({"template_object": json.dumps(template, ensure_ascii=False)}).encode()
    req = urllib.request.Request(
        KAKAO_SEND_URL, data=data,
        headers={"Authorization": "Bearer " + token,
                 "Content-Type": "application/x-www-form-urlencoded"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            out = json.load(r)
        if out.get("result_code") != 0:
            print(f"  (카카오 응답 이상: {out})", file=sys.stderr)
    except urllib.error.URLError as e:
        print(f"  (카카오 전송 실패: {e})", file=sys.stderr)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--keyword", action="append", default=[],
                     help="BSA 판별용 이름 키워드 추가 (기본: 브랜드검색, BSA, 브랜드 검색)")
    ap.add_argument("--dump-raw", action="store_true", help="원본 캠페인/광고그룹 JSON도 저장(필드 검수용)")
    ap.add_argument("--notify", action="store_true", help="변경 감지 시 카카오 '나에게' 알림")
    ap.add_argument("--out", default=None, help="상태 CSV 경로 (기본: bsa_onoff_YYYYMMDD.csv)")
    args = ap.parse_args()

    keywords = DEFAULT_KEYWORDS + args.keyword

    try:
        client = SearchAdClient()
    except SearchAdAuthError as e:
        sys.exit(str(e))

    try:
        items = fetch_bsa_items(client, keywords, dump_raw=args.dump_raw)
    except SearchAdAPIError as e:
        sys.exit(f"API 오류: {e}")

    if not items:
        print("BSA로 판별된 캠페인/광고그룹이 없습니다. --dump-raw로 원본을 확인하고 --keyword를 조정하세요.")

    prev = load_snapshot()
    changes = diff_items(prev, items)

    out_path = args.out or f"bsa_onoff_{datetime.now():%Y%m%d}.csv"
    write_status_csv(items, out_path)
    save_snapshot(items)
    if changes:
        append_changelog(changes)
        if args.notify:
            kakao_notify(changes)

    print(f"[{datetime.now():%Y-%m-%d %H:%M}] BSA 항목 {len(items)}건 → {out_path}")
    if changes:
        print(f"  변경 {len(changes)}건 감지 → {CHANGELOG_FILE}")
        for c in changes:
            print(f"   - {c['campaign_name']}/{c['adgroup_name']}: {c['before']} → {c['after']}")
    else:
        print("  변경 없음")


if __name__ == "__main__":
    main()
