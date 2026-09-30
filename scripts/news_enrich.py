#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""뉴스 원문 보강 — 네이버 검색 API의 잘린 제목·설명문을 기사 원문으로 바로잡는다.

네이버 뉴스 검색 API는 제목·설명문을 중간에서 잘라 '...'를 붙여 준다. 그 설명문을 그대로
요약으로 쓰면 문장이 끊기고(말줄임표), 핵심이 뒤쪽에 있는 기사는 요약이 틀린다.
clip_news.py(GitHub Actions)가 기사 페이지를 열어
  - 전체 제목(og:title)으로 잘린 제목을 교체하고
  - 본문에서 제목 핵심어와 맞는 '완결 문장' 1~2개(220자 이내)를 골라 summary로 저장한다.
기사 본문 전체는 저장하지 않는다(공개 기사 1~2문장 인용 요약만). 표준 라이브러리만 사용.
순수 함수(extract_article·summarize·sentences_from_snippet)는 테스트가 HTML fixture를 주입한다.
"""
import re
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from html import unescape
from html.parser import HTMLParser

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
MAX_BYTES = 1_500_000
SUMMARY_MAX = 220
# 기사 본문 컨테이너(네이버 뉴스·주요 언론사 공통 id/class)
BODY_IDS = {"dic_area", "newsct_article", "articlebodycontents", "articlebody", "article_body",
            "article-view-content-div", "news_body_area", "articeBody".lower(), "newsview", "article_txt"}
SKIP_TAGS = {"script", "style", "noscript", "nav", "header", "footer", "aside", "form", "button", "figcaption", "select"}
VOID_TAGS = {"br", "img", "hr", "input", "meta", "link", "source", "wbr", "area", "base", "col", "embed", "param", "track"}
BLOCK_TAGS = {"p", "div", "br", "li", "section", "article", "h1", "h2", "h3", "h4", "tr", "td", "table", "ul", "ol", "blockquote"}
NOISE_LINE = re.compile(r"기자\s*[=\]]|기자$|@[\w.-]+\.\w+|무단\s*전재|재배포\s*금지|copyright|ⓒ|©|사진\s*=|\[사진|▶|☞|구독|좋아요|댓글|관련\s*기사", re.I)
STOPWORDS = {"보험", "관련", "위해", "대한", "통해", "이번", "지난", "올해", "오늘", "기자", "뉴스", "단독", "속보", "종합"}
ELLIPSIS = re.compile(r"(\.\.\.|…)\s*$")


class _ArticleParser(HTMLParser):
    """og 메타·본문 컨테이너 텍스트·일반 텍스트 줄을 한 번에 모은다."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.meta = {}
        self.title = ""
        self._in_title = False
        self._skip = 0
        self._stack = []          # (tag, is_body)
        self._body_depth = 0
        self._link_depth = 0      # <a> 안 텍스트 — 링크 밀도로 메뉴·관련기사 목록을 거른다(Readability·trafilatura 방식)
        self.body_parts = []
        self.all_parts = []

    def handle_starttag(self, tag, attrs):
        a = {k.lower(): (v or "") for k, v in attrs}
        if tag == "meta":
            key = (a.get("property") or a.get("name") or "").lower()
            if key in ("og:title", "og:description", "description", "twitter:title"):
                self.meta.setdefault(key, unescape(a.get("content", "")).strip())
            return
        if tag == "title":
            self._in_title = True
        if tag in VOID_TAGS:
            if tag == "br":
                self._newline()
            return
        is_body = (a.get("id", "").lower() in BODY_IDS or a.get("itemprop", "").lower() == "articlebody"
                   or any(c.lower() in BODY_IDS for c in a.get("class", "").split()))
        self._stack.append((tag, is_body, tag in SKIP_TAGS))
        if tag == "a":
            self._link_depth += 1
        if tag in SKIP_TAGS:
            self._skip += 1
        if is_body:
            self._body_depth += 1
        if tag in BLOCK_TAGS:
            self._newline()

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        if tag in VOID_TAGS:
            return
        # 닫는 태그와 짝이 맞는 가장 가까운 여는 태그까지 되감는다(비정형 HTML 대응)
        for i in range(len(self._stack) - 1, -1, -1):
            if self._stack[i][0] == tag:
                for opened, is_body, skip in self._stack[i:]:
                    if opened == "a":
                        self._link_depth -= 1
                    if skip:
                        self._skip -= 1
                    if is_body:
                        self._body_depth -= 1
                del self._stack[i:]
                break
        if tag in BLOCK_TAGS:
            self._newline()

    def handle_data(self, data):
        if self._in_title:
            self.title += data
            return
        if self._skip:
            return
        chunk = (data, self._link_depth > 0)
        self.all_parts.append(chunk)
        if self._body_depth:
            self.body_parts.append(chunk)

    def _newline(self):
        self.all_parts.append(("\n", False))
        if self._body_depth:
            self.body_parts.append(("\n", False))


# 줄 맨 앞 기자·매체 표기 — 리드 문장이 이 표기와 한 줄에 붙어 오므로 줄을 버리지 말고 표기만 뗀다
BYLINE_PREFIX = re.compile(r"^\s*(?:[\[(【<][^\])】>]{0,40}(?:기자|특파원|=)[^\])】>]{0,20}[\])】>]\s*"
                           r"|[가-힣]{2,4}\s*(?:기자|특파원)\s*=\s*)+")


LINK_DENSITY_MAX = 0.5   # 줄 글자의 절반 이상이 링크면 본문이 아니라 메뉴·관련기사 목록으로 본다


def _lines(parts):
    """(텍스트, 링크 여부) 조각 → 본문 줄. 링크 밀도가 높은 줄(메뉴·관련기사)과 잡음 줄은 버린다."""
    rows, text, linked = [], [], 0
    for chunk, in_link in list(parts) + [("\n", False)]:
        if isinstance(chunk, str) and chunk == "\n" and not in_link:
            rows.append(("".join(text), linked))
            text, linked = [], 0
            continue
        value = str(chunk)
        text.append(value)
        if in_link:
            linked += len(value.strip())
    out = []
    for raw, linked_chars in rows:
        compact = re.sub(r"\s+", " ", raw).strip()
        if not compact or linked_chars / max(1, len(compact.replace(" ", ""))) > LINK_DENSITY_MAX:
            continue
        line = BYLINE_PREFIX.sub("", compact).strip()
        if line and not NOISE_LINE.search(line):
            out.append(line)
    return out


def _clean_title(title, site_hint=""):
    t = re.sub(r"\s+", " ", unescape(title or "")).strip()
    # "제목 - 매체명", "제목 | 매체명", "제목 :: 매체명" 꼬리 제거(꼬리가 짧을 때만)
    m = re.match(r"^(.*\S)\s+(?:-|\||::|:|–)\s+([^-|:]{1,20})$", t)
    if m and len(m.group(1)) >= 8:
        t = m.group(1)
    return t


def extract_article(html_text):
    """기사 HTML → {title, description, text}. text는 본문 컨테이너 우선, 없으면 문장형 줄."""
    parser = _ArticleParser()
    try:
        parser.feed(html_text or "")
        parser.close()
    except Exception:
        pass
    body = _lines(parser.body_parts)
    if len(" ".join(body)) < 80:
        # 본문 컨테이너를 못 찾은 사이트 — 문장으로 끝나는 긴 줄만 모은다(메뉴·버튼 텍스트 제외)
        body = [ln for ln in _lines(parser.all_parts) if len(ln) >= 25 and re.search(r"(다|요)\s*[.!?\"”']?$|[.!?]$", ln)]
    title = parser.meta.get("og:title") or parser.meta.get("twitter:title") or parser.title
    return {
        "title": _clean_title(title),
        "description": parser.meta.get("og:description") or parser.meta.get("description") or "",
        "text": "\n".join(body),
    }


def split_sentences(text):
    text = re.sub(r"\s+", " ", str(text or "")).strip()
    if not text:
        return []
    # 한국어 기사 문장은 대부분 '다.'로 끝난다. 숫자 속 마침표(3.5%)는 자르지 않는다.
    parts = re.split(r"(?<=[다요]\.)\s+|(?<=[!?])\s+|(?<=[다요]\.)(?=[\"“‘'\[(가-힣A-Z])", text)
    return [p.strip() for p in parts if p and p.strip()]


def _complete(sentence):
    s = sentence.strip()
    return bool(re.search(r"(?:[다요]\.|[!?])[\"”’')\]]*$", s)) and not ELLIPSIS.search(s)


def _tokens(title):
    words = re.findall(r"[가-힣A-Za-z0-9]{2,}", re.sub(r"\[[^\]]*\]", " ", title or ""))
    out = []
    for w in words:
        if w in STOPWORDS or w.isdigit():
            continue
        # 조사를 대충 떼어 비교(보험료를→보험료, 손해율이→손해율)
        stem = re.sub(r"(으로|에서|에게|까지|부터|이다|했다|한다|은|는|이|가|을|를|에|의|도|로|과|와)$", "", w)
        if len(stem) >= 2 and stem not in out:
            out.append(stem)
    return out


def summarize(title, text, description="", limit=SUMMARY_MAX):
    """본문에서 제목 핵심어와 맞는 완결 문장 1~2개(기사 순서 유지)를 고른다. 말줄임표를 붙이지 않는다."""
    sentences = [s for s in split_sentences(text) if 20 <= len(s) <= 180 and _complete(s) and not NOISE_LINE.search(s)]
    if not sentences and description:
        sentences = [s for s in split_sentences(description) if len(s) >= 20 and _complete(s)]
    if not sentences:
        return ""
    toks = _tokens(title)
    scored = []
    for i, s in enumerate(sentences[:40]):
        # 어미·조사가 붙은 핵심어(범퍼인데·올린다)도 맞도록 끝 1~2글자를 덜어낸 형태까지 비교
        hit = sum(1 for t in toks if any(t[:k] in s for k in (len(t), len(t) - 1, len(t) - 2) if k >= 2))
        score = hit * 2 + (1.5 if i == 0 else 0.6 if i == 1 else 0) + (0.3 if re.search(r"\d", s) else 0)
        scored.append((score, i, s))
    best = sorted(scored, key=lambda x: (-x[0], x[1]))
    picked = [best[0]]
    for cand in best[1:]:
        if cand[0] < 2:     # 제목과 거의 무관한 문장은 덧붙이지 않는다
            break
        if len(picked[0][2]) + 1 + len(cand[2]) <= limit:
            picked.append(cand)
            break
    picked.sort(key=lambda x: x[1])
    out = " ".join(p[2] for p in picked)
    return out if len(out) <= limit else picked[0][2][:limit]


def sentences_from_snippet(snippet, limit=190):
    """원문을 못 읽었을 때: 검색 설명문에서 잘린 마지막 문장은 버리고 완결 문장만 남긴다."""
    raw = re.sub(r"<[^>]*>", "", unescape(str(snippet or ""))).strip()
    truncated = bool(ELLIPSIS.search(raw))
    raw = ELLIPSIS.sub("", raw).strip()
    # "사진=○○ | 매체= 홍길동 기자 | 본문…" 처럼 앞에 붙은 사진·기자 표기 조각을 뗀다
    segs = [x.strip() for x in raw.split("|")]
    while len(segs) > 1 and (NOISE_LINE.search(segs[0]) or len(segs[0]) < 15):
        segs.pop(0)
    raw = BYLINE_PREFIX.sub("", " | ".join(segs)).strip()
    parts = split_sentences(raw)
    if truncated and parts:
        parts = parts[:-1]
    keep, total = [], 0
    for p in parts:
        if not _complete(p):
            break
        if total + len(p) + (1 if keep else 0) > limit:
            break
        keep.append(p)
        total += len(p) + (1 if len(keep) > 1 else 0)
    return " ".join(keep)


def tidy_title(title):
    """원문 제목을 못 받았을 때: 끝의 '...'과 그 앞의 잘린 단어('보험사기 대...')를 뗀다."""
    t = re.sub(r"\s+", " ", str(title or "")).strip()
    if not ELLIPSIS.search(t):
        return t
    t = ELLIPSIS.sub("", t).rstrip()
    cut = max(t.rfind(" "), t.rfind("…"), t.rfind("·"))
    return t[:cut].rstrip(" …·,") if cut >= len(t) * 0.5 else t


def _decode(raw, content_type):
    m = re.search(r"charset=([\w-]+)", content_type or "", re.I) or re.search(rb"<meta[^>]+charset=[\"']?([\w-]+)", raw[:4096], re.I)
    enc = m.group(1) if m else "utf-8"
    enc = enc.decode("ascii", "ignore") if isinstance(enc, bytes) else enc
    if enc.lower() in ("euc-kr", "ks_c_5601-1987", "ksc5601"):
        enc = "cp949"
    for candidate in (enc, "utf-8", "cp949"):
        try:
            return raw.decode(candidate)
        except (LookupError, UnicodeDecodeError):
            continue
    return raw.decode("utf-8", "replace")


def fetch(url, timeout=8):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "ko-KR,ko;q=0.9"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return _decode(r.read(MAX_BYTES), r.headers.get("Content-Type", ""))


def _prefix(title):
    return re.sub(r"\s+", "", ELLIPSIS.sub("", title or ""))[:12]


def enrich_item(item, fetcher=fetch):
    """기사 1건 보강 결과(바꿀 필드)를 돌려준다 — 원본 item은 건드리지 않는다. 실패해도 예외를 올리지 않는다."""
    api_title = item.get("t", "")
    try:
        art = extract_article(fetcher(item["url"]))
    except Exception:
        art = {"title": "", "description": "", "text": ""}
    title = api_title
    full = art.get("title", "")
    if full and ELLIPSIS.search(api_title) and _prefix(api_title) and _prefix(api_title) in re.sub(r"\s+", "", full):
        title = full
    title = tidy_title(title)
    summary = summarize(title, art.get("text", ""), art.get("description", ""))
    return {"t": title, "summary": summary or sentences_from_snippet(item.get("gist")),
            "summary_source": "article" if summary else "snippet"}


def _snippet_fallback(item):
    return {"t": tidy_title(item.get("t", "")), "summary": sentences_from_snippet(item.get("gist")),
            "summary_source": "snippet"}


def enrich_items(items, fetcher=fetch, workers=8, budget_sec=150):
    """summary가 없는 기사만 병렬 보강(결과 반영은 호출 스레드에서만). 시간 예산을 넘기면 남은 기사는 설명문 기반."""
    todo = [it for it in items if not it.get("summary") and it.get("url")]
    results = {}
    ex = ThreadPoolExecutor(max_workers=workers)
    futures = {ex.submit(enrich_item, dict(it), fetcher): i for i, it in enumerate(todo)}
    try:
        for fut in as_completed(futures, timeout=budget_sec):
            try:
                results[futures[fut]] = fut.result()
            except Exception:
                pass
    except Exception:   # 시간 예산 초과(TimeoutError) — 남은 기사는 설명문으로
        pass
    finally:
        ex.shutdown(wait=False, cancel_futures=True)
    for i, it in enumerate(todo):
        it.update(results.get(i) or _snippet_fallback(it))
    return sum(1 for it in todo if it.get("summary_source") == "article"), len(todo)
