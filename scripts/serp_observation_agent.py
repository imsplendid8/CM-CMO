#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SERP 관측 소재 자동 정규화 — serp/dom_observations.json → serp/ad_observations.json.

주간 자동 캡쳐(scripts/capture_serp.mjs)가 네이버 PC 파워링크 광고를 1건씩 구조화해
dom_observations.json에 남기면, 이 스크립트가 경쟁사 광고만 골라
serp_analysis.py가 읽는 관측 스키마(product·brand·keyword·date·rank·title·desc·promo·covers·price·cta·landing)로 바꾼다.

- 자사(한화·캐롯) 광고는 경쟁사 관측에서 제외한다.
- 같은 (상품, 날짜)의 자동 관측은 재실행 시 교체하고, 다른 출처(초기 샘플 등)의 행은 보존한다.
- 경쟁사 공개 광고 문구만 다룬다(PII·영업비밀 없음). 문구는 패턴 분석 근거로만 쓰고 복제하지 않는다.
표준 라이브러리만 사용. 순수 함수(normalize_rows)는 테스트가 fixture를 주입할 수 있다.
"""
import argparse
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOM_SRC = "serp/dom_observations.json"
OUT = "serp/ad_observations.json"
PRODUCTS = "data/products.json"
AUTO_SOURCE = "auto-dom"
MAX_ROWS = 1500

OWN_BRAND = re.compile(r"한화|캐롯|hanwha|carrot", re.I)
DOMAIN_TOKEN = re.compile(r"(?:https?://)?(?:[a-z0-9-]+\.)+(?:co\.kr|or\.kr|ne\.kr|kr|com|net|co|biz|io)\b", re.I)
PROMO_WORDS = re.compile(r"할인|증정|포인트|상품권|이벤트|캐시백|쿠폰|적립|사은품|기프티콘")
PRICE = re.compile(r"\d+(?:\.\d+)?\s*%\s*할인|최대\s*[\d,.]+\s*만?\s*원|월\s*[\d,]+\s*원|[\d,]+\s*원대")
NOISE_LINE = re.compile(r"^(광고|도움말|이미지|신고하기|n ?pay|네이버페이|등록 안내|.*관련 광고)$", re.I)
COMMON_COVERS = [
    "형사합의금", "변호사선임", "벌금", "교통사고처리지원금", "진단비", "유사암", "표적항암", "수술비", "입원비",
    "임플란트", "크라운", "보철", "스케일링", "홀인원", "배상책임", "풍수재", "누수", "임시거주비", "도난",
    "실손", "휴대품", "항공기지연", "태아", "선천이상", "간편심사", "12대중과실",
]
# 네이버페이·로그인 배지 안내문 — 링크라서 제목으로 잘못 잡히던 문구
BADGE_TEXT = re.compile(r"네이버 아이디|naver ?pay|npay 서비스|서비스 (보기|자세히)|네이버 로그인", re.I)
CTA_MAP = [("가입", "가입"), ("계산", "견적"), ("견적", "견적"), ("보험료", "견적"), ("비교", "비교"), ("상담", "상담")]


def _load(root, rel, default):
    try:
        with open(os.path.join(root, rel), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def _clean(text):
    return re.sub(r"\s+", " ", str(text or "")).strip()


def split_raw_lines(lines):
    """도메인이 광고주명과 한 줄에 붙은 영역 원문을 광고 단위로 나눈다."""
    ads, current = [], None
    for line in (_clean(x) for x in lines or []):
        if not line or NOISE_LINE.match(line):
            continue
        match = DOMAIN_TOKEN.search(line)
        if match:
            if current:
                ads.append(current)
            brand = _clean(line[:match.start()]).strip("·").strip()
            current = {"brand": brand, "domain": match.group(0).split("//")[-1].lower(), "body": []}
        elif current is not None:
            current["body"].append(line)
    if current:
        ads.append(current)
    out = []
    for i, ad in enumerate(ads, 1):
        body = ad["body"]
        title = next((t for t in body if len(t) >= 8), "")
        rest = [t for t in body if t != title]
        desc = max((t for t in rest if len(t) >= 20), key=len, default="")
        ext = [t for t in rest if t != desc and 2 <= len(t) <= 40]
        out.append({"kind": "powerlink", "rank": i, "brand": ad["brand"], "domain": ad["domain"],
                    "title": title, "desc": desc, "extensions": ext})
    return out


def _covers(text, special):
    found = []
    for term in list(special) + COMMON_COVERS:
        key = term.replace(" ", "")
        if key and key in text.replace(" ", "") and key not in found:
            found.append(key)
    return found[:6]


def _promo(text):
    # 숫자 속 쉼표·마침표(9,000원 · 3.5.5)에서는 자르지 않는다
    for part in re.split(r"(?<!\d)[.,](?!\d)|[!?·|\n]", text):
        part = _clean(part)
        if part and PROMO_WORDS.search(part):
            return part[:40]
    return ""


def _cta(text):
    out = []
    for word, label in CTA_MAP:
        if word in text and label not in out:
            out.append(label)
    return "/".join(out)


def _undouble(text):
    """'제목 제목'처럼 같은 문구가 두 번 붙은 경우 한 번만."""
    half = len(text) // 2
    if len(text) > 8 and text[:half].strip() == text[half:].strip():
        return text[:half].strip()
    return text


def _from_lines(lines, domain):
    """광고 원문 줄은 [광고주] → [도메인] → [제목] → [설명] 순서 — 도메인 줄 기준으로 광고주·제목을 읽는다."""
    lines = [_clean(x) for x in lines or [] if _clean(x) and not BADGE_TEXT.search(_clean(x))]
    idx = next((i for i, t in enumerate(lines) if domain and domain in t.lower()), -1)
    if idx < 0:
        return "", ""
    brand = lines[idx - 1] if idx > 0 else ""
    title = lines[idx + 1] if idx + 1 < len(lines) and len(lines[idx + 1]) >= 5 else ""
    return brand, title


def normalize_ad(row, product, date, keyword, special):
    domain = _clean(row.get("domain")).lower().rstrip("/")
    line_brand, line_title = _from_lines(row.get("lines"), domain)
    brand = _clean(row.get("brand")) or line_brand
    title = _clean(row.get("title"))
    if line_title and (not title or BADGE_TEXT.search(title)):
        title = line_title
    if BADGE_TEXT.search(title):
        title = ""
    title = _undouble(title)
    desc = _clean(row.get("desc"))
    ext = [_clean(x) for x in row.get("extensions") or []
           if _clean(x) and _clean(x) != title and not BADGE_TEXT.search(_clean(x))]
    if not (title or desc) or OWN_BRAND.search(f"{brand} {domain}"):
        return None
    text = " ".join([title, desc] + ext)
    price = PRICE.search(text)
    return {
        "product": product,
        "brand": brand or domain,
        "keyword": keyword,
        "date": date,
        "device": "pc",
        "rank": int(row.get("rank") or 0),
        "title": title,
        "desc": desc,
        "promo": _promo(" · ".join([desc] + ext + [title])),
        "covers": _covers(text, special),
        "price": _clean(price.group(0)) if price else "",
        "cta": _cta(text),
        "landing": f"{brand} 공식" if brand and "공식" in text else domain,
        "domain": domain,
        "extensions": {
            "sitelinks": [x for x in ext if not PROMO_WORDS.search(x)],
            "promotions": [x for x in ext if PROMO_WORDS.search(x)],
        },
        "source": AUTO_SOURCE,
    }


def normalize_rows(dom_rows, products):
    """dom_observations 행 → 경쟁사 관측 행. (상품, 날짜) 안에서 같은 광고(광고주·제목·설명)는 1건만."""
    special = {p.get("key"): list(p.get("special") or []) for p in products}  # 상품명(core)은 소구가 아님
    out, seen = [], set()
    for row in dom_rows or []:
        if row.get("kind") != "powerlink":
            continue
        product, date, keyword = row.get("product"), str(row.get("date") or "")[:10], _clean(row.get("keyword"))
        if not product or not date:
            continue
        ads = split_raw_lines(row.get("lines")) if row.get("raw") else [row]
        for ad in ads:
            obs = normalize_ad(ad, product, date, keyword, special.get(product, []))
            if not obs:
                continue
            key = (product, date, obs["brand"], obs["title"], obs["desc"])
            if key in seen:
                continue
            seen.add(key)
            out.append(obs)
    # 상품·날짜별 노출 순서대로 순위를 다시 매긴다(자사 제외 후 경쟁사 기준 순위).
    counters = {}
    for obs in out:
        k = (obs["product"], obs["date"])
        counters[k] = counters.get(k, 0) + 1
        obs["rank"] = counters[k]
    return out


def merge(existing, auto_rows):
    """새 자동 관측이 있는 (상품, 날짜)의 기존 자동 행만 교체. 초기 샘플 등 다른 출처는 보존."""
    refreshed = {(o["product"], o["date"]) for o in auto_rows}
    kept = [o for o in existing or []
            if not (o.get("source") == AUTO_SOURCE and (o.get("product"), o.get("date")) in refreshed)]
    rows = kept + auto_rows
    rows.sort(key=lambda o: (str(o.get("date") or ""), str(o.get("product") or ""), int(o.get("rank") or 0)))
    return rows[-MAX_ROWS:]


def build(root=ROOT):
    dom = _load(root, DOM_SRC, {})
    products = _load(root, PRODUCTS, {}).get("products", [])
    current = _load(root, OUT, {})
    auto_rows = normalize_rows(dom.get("observations"), products)
    observations = merge(current.get("observations"), auto_rows)
    dates = [str(o.get("date") or "") for o in observations if o.get("date")]
    return {
        "_comment": "경쟁사 SERP(네이버 PC 파워링크) 관측 소재 — 주간 자동 캡쳐(capture_serp.mjs)의 광고 DOM을 "
                    "serp_observation_agent.py가 정규화(source=auto-dom). 자사 광고 제외. 경쟁사 공개 광고 문구만 담으며 "
                    "PII·영업비밀 없음. 문구는 패턴 분석 근거로만 쓰고 복제하지 않는다. serp_analysis.py의 입력.",
        "asof": max(dates) if dates else current.get("asof", ""),
        "schema": "product·brand·keyword·date·device·rank·title·desc·promo·covers[]·price·cta·landing·domain·extensions·source",
        "observations": observations,
    }, len(auto_rows)


def main(argv=None, root=ROOT):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--validate", action="store_true", help="파일을 쓰지 않고 결과만 출력")
    args = parser.parse_args(argv)
    result, n_auto = build(root)
    if not args.validate:
        with open(os.path.join(root, OUT), "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=1)
            f.write("\n")
    by_date = {}
    for o in result["observations"]:
        by_date[o["date"]] = by_date.get(o["date"], 0) + 1
    recent = ", ".join(f"{d} {n}건" for d, n in sorted(by_date.items())[-3:])
    print(f"✔ {OUT} · asof {result['asof']} · 자동 관측 {n_auto}건 · 최근 {recent}")
    if n_auto == 0:
        print("⚠ 파워링크 자동 관측 0건 — capture_serp.mjs 추출 결과(serp/dom_observations.json) 확인 필요")
    return result


if __name__ == "__main__":
    main()
