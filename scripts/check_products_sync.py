#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""상품 마스터 드리프트 검사 — data/products.json 이 단일 소스.

각 도구 HTML의 인라인 `PRODUCTS`에 캐노니컬 10개 상품이 모두 있고
key별 name·cat 이 data/products.json 과 일치하는지 확인한다(자체완결 HTML 원칙상
런타임 공유 대신 이 검사로 동기화를 강제). CI(.github/workflows/ci.yml)에서 실행.

사용: python3 scripts/check_products_sync.py   (불일치 시 exit 1)
"""
import json, re, sys, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FILES = ["seo-audit.html", "keyword-tool.html", "news-tool.html", "serp-tool.html", "seasonal-tool.html"]
ALLOWED_EXTRA = {"pro", "__pro", "__all"}   # 범용 생성기 등 도구별 허용 키

def canonical():
    d = json.load(open(os.path.join(ROOT, "data/products.json"), encoding="utf-8"))
    return {p["key"]: {"name": p["name"], "cat": p["cat"]} for p in d["products"]}

def parse_products(html):
    # `const PRODUCTS=[ ... ];` 블록에서 key별 name·cat 추출.
    # 중첩 중괄호에 견고하도록 key:"..." 위치를 기준으로 다음 key 전까지 슬라이스해서 필드 검색.
    m = re.search(r"const PRODUCTS\s*=\s*\[(.*?)\n\s*\]\s*;", html, re.S)
    if not m:
        m = re.search(r"const PRODUCTS\s*=\s*\[(.*?)\]\s*;", html, re.S)
    if not m:
        return None
    block = m.group(1)
    anchors = [(mm.start(), mm.group(1)) for mm in re.finditer(r'key:"([^"]*)"', block)]
    out = {}
    for i, (pos, key) in enumerate(anchors):
        end = anchors[i + 1][0] if i + 1 < len(anchors) else len(block)
        seg = block[pos:end]
        n = re.search(r'name:"([^"]*)"', seg)
        c = re.search(r'cat:"([^"]*)"', seg)
        out[key] = {"name": n.group(1) if n else None, "cat": c.group(1) if c else None}
    return out

def main():
    canon = canonical()
    canon_cats = {v["cat"] for v in canon.values()}
    errors = []
    for f in FILES:
        path = os.path.join(ROOT, f)
        if not os.path.exists(path):
            errors.append(f"[{f}] 파일 없음"); continue
        prods = parse_products(open(path, encoding="utf-8").read())
        if not prods:
            errors.append(f"[{f}] PRODUCTS 배열을 찾지 못함"); continue
        # 표준 cat 체계(사이트/장기/일반)를 쓰는 도구만 name·cat 까지 강제, 그 외(seo-audit)는 키 집합만
        standardized = {v["cat"] for v in prods.values() if v["cat"]} <= canon_cats
        for key, cv in canon.items():
            if key not in prods:
                errors.append(f"[{f}] 상품 '{key}' 누락"); continue
            if standardized:
                pv = prods[key]
                if pv["name"] != cv["name"]:
                    errors.append(f"[{f}] '{key}' name 불일치: '{pv['name']}' ≠ '{cv['name']}'")
                if pv["cat"] and pv["cat"] != cv["cat"]:
                    errors.append(f"[{f}] '{key}' cat 불일치: '{pv['cat']}' ≠ '{cv['cat']}'")
        for key in prods:
            if key not in canon and key not in ALLOWED_EXTRA:
                errors.append(f"[{f}] 알 수 없는 상품 키 '{key}' (data/products.json 에 없음)")
    if errors:
        print("✖ 상품 마스터 드리프트 발견:", file=sys.stderr)
        for e in errors:
            print("  - " + e, file=sys.stderr)
        sys.exit(1)
    print(f"✔ 상품 마스터 동기화 OK — {len(FILES)}개 도구 × {len(canon)}개 상품 일치")

if __name__ == "__main__":
    main()
