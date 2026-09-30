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


_BOJANG = re.compile(r" 보장(?![되하해받])")


def _scan(text, product_key, root=ROOT, bare=True):
    """담보명 표기 위치 스캔 → [(term, ok, op)]. op는 (특약)을 바른 자리에 두는 편집(시작, 끝, 대체 문자열).

    - 'X 보장' → 보장까지가 담보명: '보장' 바로 뒤. 'X(특약) 보장'은 자리가 틀린 것으로 본다.
    - 'X 특약' → 'X(특약)'.
    - 그 밖의 단독 언급은 terms만, bare=True일 때만 담보명 바로 뒤를 요구한다.
    """
    cfg = load(root)
    suffix = cfg.get("suffix", "(특약)")
    terms = set(cfg.get("terms", {}).get(product_key, []))
    phrases = set(cfg.get("phrases", {}).get(product_key, []))
    text = str(text or "")
    covered = [False] * len(text)
    for name in cfg.get("exclude_product_names", []):
        start = text.find(name)
        while start >= 0:
            for i in range(start, start + len(name)):
                covered[i] = True
            start = text.find(name, start + 1)
    hits = []
    for term in sorted(terms | phrases, key=len, reverse=True):
        start = text.find(term)
        while start >= 0:
            end = start + len(term)
            if not any(covered[start:end]):
                rest = text[end:]
                hit = None
                if _BOJANG.match(rest):
                    anchor = end + 3
                    hit = (term, text.startswith(suffix, anchor), (anchor, anchor, suffix))
                elif rest.startswith(suffix) and _BOJANG.match(rest[len(suffix):]):
                    anchor = end + len(suffix) + 3
                    fixed = "" if text.startswith(suffix, anchor) else suffix
                    hit = (term, False, (end, anchor, " 보장" + fixed))
                elif rest.startswith(" 특약"):
                    hit = (term, False, (end, end + 3, suffix))
                elif term in terms and (bare or rest.startswith(suffix)):
                    hit = (term, rest.startswith(suffix), (end, end, suffix))
                if hit:
                    for i in range(start, end):
                        covered[i] = True
                    hits.append(hit)
            start = text.find(term, start + 1)
    return hits


def missing_rider_marks(text, product_key, root=ROOT, bare=True):
    """(특약) 표기가 없거나 자리가 틀린 담보명 목록."""
    return [term for term, ok, _ in _scan(text, product_key, root, bare) if not ok]


def mark_riders(text, product_key, root=ROOT, bare=True):
    """(특약)을 담보명의 바른 자리에 둔다(자동 생성 문구용). 'X 보장' → 'X 보장(특약)', 'X 특약' → 'X(특약)'."""
    text = str(text or "")
    ops = sorted({op for _, ok, op in _scan(text, product_key, root, bare) if not ok}, reverse=True)
    for start, end, repl in ops:
        text = text[:start] + repl + text[end:]
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
