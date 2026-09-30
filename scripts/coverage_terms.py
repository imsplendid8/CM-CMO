#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""담보명 뒤 '(특약)' 표기 검사 공용 함수 — data/adcopy/coverage-terms.json 기준."""
import json
import os
import re

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


# SA 설명·추가설명 운영 기준(42~45자). 짧으면 {pad} 자리에 자연스러운 부사를 넣어 맞춘다.
SA_TEXT_MIN, SA_TEXT_MAX = 42, 45
SA_PADS = ("", "미리 ", "지금 바로 ", "꼭 ", "함께 ", "한 번에 ", "미리 꼭 ", "지금 미리 ")


def fit_sa(options, product_key, minimum=SA_TEXT_MIN, maximum=SA_TEXT_MAX, root=ROOT):
    """후보 문장에서 42~45자를 우선 고르고 담보명 뒤에 (특약)을 붙인다. 문장을 중간에서 자르지 않는다."""
    tried = []
    for option in options:
        if not option:
            continue
        for pad in (SA_PADS if "{pad}" in option else ("",)):
            value = re.sub(r"\s+", " ", option.replace("{pad}", pad)).strip(" ·,:")
            value = mark_riders(value, product_key, root)
            if minimum <= len(value) <= maximum:
                return value
            tried.append(value)
    fitting = [value for value in tried if len(value) <= maximum]
    if fitting:
        return max(fitting, key=len)
    if not tried:
        return ""
    # 모든 후보가 한도를 넘으면 가장 짧은 후보의 상품명·수식어를 덜어낸다
    shortest = min(tried, key=len)
    for drop in (r"\S+보험(?:으로|을|를|의|에)?\s", r"(?:미리|꼭|지금 바로|한 번에|함께)\s"):
        slim = re.sub(drop, "", shortest, count=1)
        if len(slim) <= maximum:
            return slim
    return shortest[:maximum]
