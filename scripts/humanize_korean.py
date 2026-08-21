#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""한국어 문장 보수 윤문기.

epoko77-ai/im-not-ai(MIT)의 humanize-korean light 원칙을 CM-CMO 자동화에 맞게
결정론적으로 축약했다. LLM이나 외부 API 없이 S1 패턴만 국소 수정하며, 수치·날짜·
고유 형식·인용을 보존한다. 변경률이 30%를 넘거나 보호 토큰이 달라지면 원문을 반환한다.

이 모듈의 목적은 AI 탐지 우회가 아니라 소재·뉴스·브리프의 한국어 품질 통일이다.
Upstream: https://github.com/epoko77-ai/im-not-ai
"""
import difflib
import re

MAX_CHANGE_RATE = 0.30

# 원문과 윤문본에서 반드시 동일해야 하는 구간. 변경 규칙 적용 전후 순서까지 대조한다.
PROTECTED = re.compile(
    r'"[^"\n]*"|“[^”\n]*”|‘[^’\n]*’|'
    r'\b[A-Z][A-Z0-9_-]{1,}\b|'
    r'\d+(?:[.,]\d+)*(?:%|원|만원|억원|명|건|회|일|월|년|시|분|자|위)?'
)


def _protected(text):
    return PROTECTED.findall(str(text or ""))


def change_rate(before, after):
    """SequenceMatcher 기반 변경률(0~1). 삽입·삭제·치환을 모두 반영한다."""
    return 1.0 - difflib.SequenceMatcher(None, before, after).ratio()


def humanize(text, max_change=MAX_CHANGE_RATE):
    """의미에 손대지 않는 light 윤문. 안전조건 실패 시 원문을 그대로 반환한다."""
    src = str(text or "").strip()
    if not src:
        return src
    out = src

    # A-8 이중 피동·번역투 중 형태가 명백한 경우만 수정한다.
    replacements = (
        ("도출되어진", "도출된"), ("판단되어진", "판단된"),
        ("결정되어진", "결정된"), ("작성되어진", "작성된"),
        ("생성되어진", "생성된"), ("사용되어진", "사용된"),
        ("보여질 수", "보일 수"), ("되어져", "돼"),
    )
    for before, after in replacements:
        out = out.replace(before, after)

    # C-11 연결어미 뒤 기계적 쉼표. 문장부호·숫자 목록은 건드리지 않는다.
    out = re.sub(r"([가-힣]{2,}(?:지만|면서|아서|어서|으며|이고|하고)),\s+", r"\1 ", out)

    # H-1/D-1은 같은 문단에서 반복될 때만 뒤쪽을 덜어낸다.
    for word in ("또한", "따라서", "아울러", "나아가", "결론적으로"):
        matches = list(re.finditer(rf"(?:(?<=^)|(?<=[.!?]\s)){word}[,\s]+", out))
        if len(matches) > 2:
            keep = 2
            seen = 0
            def trim_connector(m):
                nonlocal seen
                seen += 1
                return m.group(0) if seen <= keep else ""
            out = re.sub(rf"(?:(?<=^)|(?<=[.!?]\s)){word}[,\s]+", trim_connector, out)

    out = re.sub(r"[ \t]{2,}", " ", out).strip()
    if _protected(src) != _protected(out) or change_rate(src, out) > max_change:
        return src
    return out


def excerpt(text, limit):
    """문장·어절 중간 절단을 피하는 축약. limit 이하면 humanize 결과를 그대로 반환한다."""
    value = humanize(text)
    floor = int(limit * 0.50)
    if len(value) <= limit and (len(value) < floor or re.search(r"[.!?。]$", value)):
        return value
    # 과거 수집분처럼 이미 중간에서 잘린 문자열도 마지막 완결 문장/절까지만 노출한다.
    if len(value) <= limit:
        sentence = max(value.rfind(mark) for mark in (".", "!", "?", "。"))
        if sentence >= min(20, floor):
            return value[:sentence + 1]
        clause = max(value.rfind(mark) for mark in (",", "·", ";", "→"))
        if clause >= floor:
            return value[:clause].rstrip() + "…"
        clipped = re.sub(r"\s+\d[\d.,]*$", "", value.rstrip(" ,·"))
        return clipped + "…"
    window = value[:limit + 1]
    # 제한의 60% 이후에 있는 마지막 문장부호/공백을 선택한다.
    sentence = max(window.rfind(mark, floor, limit + 1) for mark in (".", "!", "?"))
    if sentence >= floor:
        return value[:sentence + 1]
    cut = window.rfind(" ", floor, limit + 1)
    if cut < floor:
        cut = limit
    clipped = value[:cut].rstrip(" ,·")
    # 원문 스니펫이 숫자 중간에서 끝난 경우 불완전한 수치를 노출하지 않는다.
    clipped = re.sub(r"\s+\d[\d.,]*$", "", clipped)
    return clipped + "…"
