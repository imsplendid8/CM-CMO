#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""담보명 뒤 '(특약)' 표기 검사 공용 함수 — data/adcopy/coverage-terms.json 기준."""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_CACHE = {}


def load(root=ROOT):
    if root not in _CACHE:
        with open(os.path.join(root, "data", "adcopy", "coverage-terms.json"), encoding="utf-8") as f:
            _CACHE[root] = json.load(f)
    return _CACHE[root]


def missing_rider_marks(text, product_key, root=ROOT):
    """(특약) 표기 없이 쓰인 담보명 목록. 긴 이름부터 맞추고, 이미 맞춘 구간과 상품명 안의 단어는 건너뛴다."""
    cfg = load(root)
    suffix = cfg.get("suffix", "(특약)")
    terms = sorted(cfg.get("terms", {}).get(product_key, []), key=len, reverse=True)
    text = str(text or "")
    covered = [False] * len(text)
    for name in cfg.get("exclude_product_names", []):
        start = text.find(name)
        while start >= 0:
            for i in range(start, start + len(name)):
                covered[i] = True
            start = text.find(name, start + 1)
    missing = []
    for term in terms:
        start = text.find(term)
        while start >= 0:
            end = start + len(term)
            if not any(covered[start:end]):
                for i in range(start, end):
                    covered[i] = True
                if not text.startswith(suffix, end):
                    missing.append(term)
            start = text.find(term, start + 1)
    return missing


def mark_riders(text, product_key, root=ROOT):
    """(특약) 표기가 빠진 담보명 바로 뒤에 '(특약)'을 붙인다(자동 생성 문구용)."""
    cfg = load(root)
    suffix = cfg.get("suffix", "(특약)")
    terms = sorted(cfg.get("terms", {}).get(product_key, []), key=len, reverse=True)
    text = str(text or "")
    covered = [False] * len(text)
    for name in cfg.get("exclude_product_names", []):
        start = text.find(name)
        while start >= 0:
            for i in range(start, start + len(name)):
                covered[i] = True
            start = text.find(name, start + 1)
    inserts = []
    for term in terms:
        start = text.find(term)
        while start >= 0:
            end = start + len(term)
            if not any(covered[start:end]):
                for i in range(start, end):
                    covered[i] = True
                if not text.startswith(suffix, end):
                    inserts.append(end)
            start = text.find(term, start + 1)
    for pos in sorted(inserts, reverse=True):
        text = text[:pos] + suffix + text[pos:]
    return text
