"""Telegram HTML 메시지를 태그를 깨뜨리지 않고 나누는 유틸리티."""
from __future__ import annotations

import html
import re

TAG_RE = re.compile(r"<[^>]*>")


def _text_length(s: str) -> int:
    """HTML 태그를 제외한 실제 텍스트 길이 계산."""
    return len(TAG_RE.sub("", s))


def _smart_break(text: str, maximum: int) -> tuple[str, str]:
    """
    최대 길이 내에서 줄바꿈, 문장 끝(마침표·느낌표·물음표), 또는 문단 끝을 기준으로 자르기.
    (text: 남은 부분, 자른 부분)의 튜플 반환.
    """
    current_length = 0
    last_break = 0
    last_sentence_end = 0

    i = 0
    while i < len(text):
        if text[i:i+4] == '\n\n':  # 문단 구분
            if i <= maximum:
                last_break = i + 2
            else:
                break
            i += 2
        elif text[i] in '\n':  # 줄바꿈
            if current_length <= maximum:
                last_break = i + 1
            i += 1
        elif text[i:i+1].startswith('<'):  # HTML 태그 시작
            end = text.find('>', i)
            if end != -1:
                i = end + 1
            else:
                i += 1
        else:
            current_length += 1
            if text[i] in '.!?':  # 문장 끝
                if current_length <= maximum:
                    last_sentence_end = i + 1
            elif current_length > maximum:
                break
            i += 1

    if current_length <= maximum:
        return "", text

    if last_sentence_end > 0:
        break_at = last_sentence_end
    elif last_break > 0:
        break_at = last_break
    else:
        break_at = minimum_safe_break(text, maximum)

    return text[break_at:].lstrip('\n'), text[:break_at]


def minimum_safe_break(text: str, maximum: int) -> int:
    """태그를 깨뜨리지 않으면서 최대한 앞에서 자르기."""
    current_length = 0
    i = 0

    while i < len(text) and current_length <= maximum:
        if text[i:i+1].startswith('<'):
            end = text.find('>', i)
            if end != -1:
                i = end + 1
            else:
                i += 1
        else:
            current_length += 1
            i += 1

    return max(1, i)


def split_html_message(text: str, maximum: int = 3800) -> list[str]:
    """
    HTML 태그를 보존하면서 긴 메시지를 청크로 나누기.
    줄바꿈, 문장 끝, 문단 끝을 기준으로 자르되, 태그는 깨뜨리지 않음.
    """
    chunks: list[str] = []
    remaining = str(text).strip()

    while remaining:
        if _text_length(remaining) <= maximum:
            chunks.append(remaining)
            break

        rest, chunk = _smart_break(remaining, maximum)
        if chunk:
            chunks.append(chunk.rstrip('\n'))
        remaining = rest.lstrip('\n')

        if not chunk:  # 무한루프 방지
            break

    return chunks if chunks else [""]
