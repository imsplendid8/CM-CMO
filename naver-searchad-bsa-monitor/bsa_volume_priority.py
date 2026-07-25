#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BSA 검색량 우선순위 시트 (검색광고 운영 자동화 3번 항목).

계약 원장(bsa_contracts.csv)의 각 계약에 대해
  1) 보종(카테고리) 월검색량을 네이버 검색광고 키워드도구 API로 조회(수요 지표)
  2) 계약종료일 D-day를 계산
  3) '만료임박/만료 + 수요 높음/낮음'을 조합해 재계약·집행 우선순위 권고를 낸다.
bsa_contract_review.py(만료임박 판정)와 bsa_keyword_suggest.py(키워드 후보)의 다음 단계로,
"어느 보종의 BSA를 우선 재계약/집행할지"를 검색량 근거로 정렬한다.

검색량 소스: 네이버 검색광고 키워드도구(`/keywordstool`) — BSA 모니터와 동일한
  NAVER_SEARCHAD_API_KEY / SECRET_KEY / CUSTOMER_ID 사용. 키 없으면 조회 불가(‑‑sample로 로직만 확인).

사용:
  python3 bsa_volume_priority.py                 # 원장(없으면 샘플) × 실검색량
  python3 bsa_volume_priority.py --warn-days 21
  python3 bsa_volume_priority.py --sample         # API 없이 가상 검색량으로 시트/정렬 확인
출력: bsa_volume_priority_YYYYMMDD.csv (사업부·보종·D-day·월검색량·수요등급·권고), 검색량 내림차순
외부 라이브러리 의존 없음(stdlib만).
"""
import argparse
import csv
import os
import sys
import zlib
from datetime import datetime

LEDGER_FILE = "bsa_contracts.csv"
SAMPLE_FILE = "bsa_contracts_sample.csv"
HIGH, MID = 10000, 1000  # 수요 등급 임계(월 PC+모바일 합)


def load_ledger(path):
    p = path if os.path.exists(path) else (SAMPLE_FILE if os.path.exists(SAMPLE_FILE) else None)
    if not p:
        sys.exit(f"{path} 도 {SAMPLE_FILE} 도 없습니다.")
    with open(p, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def _num(v):
    """'< 10' 같은 값은 5로, 숫자는 int로."""
    s = str(v)
    if "<" in s:
        return 5
    d = "".join(ch for ch in s if ch.isdigit())
    return int(d) if d else 0


def fetch_volumes(bojongs):
    """보종 카테고리 월검색량(PC+모바일 합, 경쟁도) 조회. 반환 {보종: (pc, mobile, comp)}."""
    from searchad_client import SearchAdClient, SearchAdAPIError, SearchAdAuthError
    try:
        client = SearchAdClient()
    except SearchAdAuthError as e:
        sys.exit(str(e))
    out = {}
    uniq = [b for b in dict.fromkeys(bojongs) if b]
    for i in range(0, len(uniq), 5):
        batch = uniq[i:i + 5]
        try:
            r = client.get("/keywordstool", params={"hintKeywords": ",".join(batch), "showDetail": 1})
        except SearchAdAPIError as e:
            print(f"  (검색량 조회 실패 {batch}: {e})", file=sys.stderr)
            continue
        by_kw = {}
        for it in (r.get("keywordList") or []):
            k = (it.get("relKeyword") or "").replace(" ", "")
            by_kw[k] = it
        for b in batch:
            it = by_kw.get(b.replace(" ", ""))
            if it:
                out[b] = (_num(it.get("monthlyPcQcCnt")), _num(it.get("monthlyMobileQcCnt")), it.get("compIdx") or "")
    return out


def sample_volumes(bojongs):
    """API 없이 보종명 해시로 재현 가능한 가상 검색량(로직·시트 확인용)."""
    out = {}
    for b in dict.fromkeys(bojongs):
        if not b:
            continue
        h = zlib.crc32(b.encode("utf-8"))
        pc = 300 + h % 22000
        mob = 500 + (h >> 3) % 40000
        comp = ["낮음", "중간", "높음"][h % 3]
        out[b] = (pc, mob, comp)
    return out


def d_day(end_str, today):
    try:
        return (datetime.strptime(end_str.strip(), "%Y-%m-%d").date() - today).days
    except (ValueError, AttributeError):
        return None


def tier(total):
    if total is None:
        return "미조회"
    return "높음" if total >= HIGH else "중간" if total >= MID else "낮음"


def recommend(dday, t, warn):
    by_tier = {"높음": "재계약·집행 우선", "중간": "단가 대비 효율 검토", "낮음": "취소/축소 검토", "미조회": "검색량 확인 필요"}
    if dday is None:
        return "계약종료일 확인 필요"
    if dday < 0:
        return f"만료됨 · {by_tier[t]}"
    if dday <= warn:
        return f"만료임박 D-{dday} · {by_tier[t]}"
    return f"D-{dday} · 정상(수요 {t})"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ledger", default=LEDGER_FILE)
    ap.add_argument("--warn-days", type=int, default=14)
    ap.add_argument("--sample", action="store_true", help="API 없이 가상 검색량으로 로직·시트 확인")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    rows = load_ledger(args.ledger)
    bojongs = [(r.get("보종") or "").strip() for r in rows]
    vols = sample_volumes(bojongs) if args.sample else fetch_volumes(bojongs)

    today = datetime.now().date()
    out_rows = []
    for r in rows:
        b = (r.get("보종") or "").strip()
        pc, mob, comp = vols.get(b, (None, None, ""))
        total = (pc + mob) if pc is not None else None
        t = tier(total)
        dday = d_day(r.get("계약종료일", ""), today)
        out_rows.append({
            "사업부": (r.get("사업부") or "").strip(), "보종": b,
            "계약종료일": (r.get("계약종료일") or "").strip(),
            "D-day": dday if dday is not None else "",
            "월PC검색량": pc if pc is not None else "", "월모바일검색량": mob if mob is not None else "",
            "월합계": total if total is not None else "", "경쟁도": comp,
            "수요등급": t, "권고": recommend(dday, t, args.warn_days),
        })
    # 검색량(월합계) 내림차순 — 우선순위 정렬
    out_rows.sort(key=lambda x: (x["월합계"] if isinstance(x["월합계"], int) else -1), reverse=True)

    out_path = args.out or f"bsa_volume_priority_{datetime.now():%Y%m%d}.csv"
    fields = ["사업부", "보종", "계약종료일", "D-day", "월PC검색량", "월모바일검색량", "월합계", "경쟁도", "수요등급", "권고"]
    with open(out_path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(out_rows)

    src = "가상 검색량(--sample)" if args.sample else "실검색량"
    print(f"[{datetime.now():%Y-%m-%d %H:%M}] {len(out_rows)}건 × {src} → {out_path} (검색량 내림차순)")
    urgent = [r for r in out_rows if "만료" in r["권고"]]
    if urgent:
        print(f"  만료/임박 {len(urgent)}건 (수요순):")
        for r in urgent:
            print(f"   - [{r['사업부']}] {r['보종']}: 월{r['월합계']} · {r['권고']}")


if __name__ == "__main__":
    main()
