"""Telegram HTML 메시지를 태그를 깨뜨리지 않고 나누는 유틸리티."""
from __future__ import annotations

import html
import re

TAG_RE = re.compile(r"<[^>]*>")


def _plain_chunks(line: str, maximum: int) -> list[str]:
    plain = html.unescape(TAG_RE.sub("", line))
    # escape 후 길이가 늘어날 수 있으므로 충분한 여유를 둔다.
    width = max(1, maximum // 6)
    return [html.escape(plain[i:i + width]) for i in range(0, len(plain), width)] or [""]


def split_html_message(text: str, maximum: int = 3900) -> list[str]:
    """완결된 줄 단위로 나누고, 비정상적으로 긴 한 줄은 안전한 평문으로 전환한다."""
    lines = str(text).splitlines()
    chunks: list[str] = []
    current = ""
    for line in lines:
        parts = [line] if len(line) <= maximum else _plain_chunks(line, maximum)
        for part in parts:
            candidate = f"{current}\n{part}" if current else part
            if current and len(candidate) > maximum:
                chunks.append(current)
                current = part
            else:
                current = candidate
    if current or not chunks:
        chunks.append(current)
    return chunks
