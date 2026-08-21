#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""뉴스 클리핑을 채널 공통의 의사결정형 브리프로 변환한다.

원문 전체를 읽었다고 주장하지 않는다. 공개 검색 결과의 제목·설명문만 사용하며,
대시보드·텔레그램·이메일은 이 모듈이 만든 같은 요약을 길이만 달리해 표시한다.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import datetime, timezone, timedelta

KST = timezone(timedelta(hours=9))

ACTION_TERMS = {
    "출시", "개편", "리뉴얼", "신상품", "인상", "인하", "할인", "이벤트", "다이렉트",
    "제재", "과징금", "심의", "광고", "손해율", "보험료", "사고", "화재", "폭우", "호우",
    "침수", "폭염", "한파", "급증", "지원", "보장", "가입", "규제", "제도",
}
NOISE_TERMS = {
    "목표주가", "투자의견", "배당", "증권", "주가", "코스피", "코스닥", "채용", "인사",
    "봉사활동", "사회공헌", "기부", "수상", "골프대회 성적", "프로야구", "폭스바겐", "VW ",
    "제약사", "약국", "CSM", "보험계약마진", "순이익", "계리적 가정", "목표주가",
}

CATEGORY_TERMS = {
    "home": ("한화손해보험", "한화손보", "캐롯", "다이렉트보험"),
    "hrmf": ("주택화재", "화재보험", "아파트 화재", "누수", "침수", "풍수재"),
    "golf": ("골프보험", "홀인원", "라운딩", "골프장", "KPGA", "골퍼"),
    "cncr": ("암보험", "암 진단", "진단비", "유사암"),
    "dntl": ("치아보험", "임플란트", "치과", "보철", "크라운"),
    "driver": ("운전자보험", "자동차보험", "교통사고", "운전자", "스쿨존", "페달 오조작"),
    "woman": ("여성보험", "여성건강", "유방", "자궁", "난소"),
    "birth": ("태아보험", "자녀보험", "임신", "출산", "태아", "임산부"),
    "overseas": ("여행보험", "여행자보험", "항공지연", "해외여행", "휴대품"),
    "overseaslong": ("장기체류보험", "유학생보험", "유학", "워킹홀리데이", "워홀", "주재원"),
    "holeinone": ("홀인원보험", "홀인원", "라운딩"),
    "event": ("행사보험", "행사배상", "배상책임", "지역행사", "축제"),
    "chronic": ("유병자보험", "간편보험", "간편심사", "유병력자", "고령자보험"),
}
DOMAIN_TERMS = {
    "보험", "손보", "손해보험", "다이렉트", "가입", "보장", "보험료", "담보", "광고",
    "심의", "제재", "청구", "사고", "화재", "침수", "여행", "운전자", "골프",
}

WHY_RULES = [
    (("광고", "심의", "제재", "과징금"),
     "광고 운영 기준과 심의 리스크가 바뀔 수 있어 집행 중인 소재 점검이 필요합니다.",
     "검색광고·파워콘텐츠·DA 소재의 필수 안내와 과장 표현을 확인하세요."),
    (("출시", "신상품", "개편", "리뉴얼"),
     "경쟁 상품과 고객 선택 기준이 달라질 수 있는 변화입니다.",
     "경쟁사 혜택·담보·가입 동선을 비교해 자사 차별 소구를 정리하세요."),
    (("보험료", "인상", "인하", "할인"),
     "가격 민감도와 비교 검색량에 직접 영향을 줄 가능성이 있습니다.",
     "가격 단독 경쟁보다 보장·편의 차이를 함께 보여주는 소재를 준비하세요."),
    (("화재", "폭우", "호우", "침수", "한파", "폭염"),
     "사고·기상 이슈는 단기간에 관련 보험의 정보 탐색을 키울 수 있습니다.",
     "예방 정보와 실제 보장 범위를 구분해 관련 상품 랜딩과 콘텐츠를 점검하세요."),
    (("사기", "사고", "과실", "판결"),
     "고객의 위험 인식과 보장 필요성을 환기할 수 있는 이슈입니다.",
     "불안을 과장하지 말고 사고 대응 절차와 보장 범위를 설명하는 콘텐츠로 연결하세요."),
    (("지원", "정책", "제도", "규제"),
     "정책 변화가 가입 조건·고객 문의·콘텐츠 수요에 영향을 줄 수 있습니다.",
     "적용 대상과 시행 시점을 확인한 뒤 FAQ와 랜딩 안내를 갱신하세요."),
]

PRODUCT_ACTIONS = {
    "home": "브랜드검색과 통합 랜딩의 최신 메시지를 점검하세요.",
    "hrmf": "주택화재보험의 화재·누수·풍수재 보장 안내를 점검하세요.",
    "golf": "골프보험의 상해·배상과 라운딩 시즌 소재를 점검하세요.",
    "cncr": "암보험의 진단비·갱신 조건을 쉬운 언어로 비교해 설명하세요.",
    "dntl": "치아보험의 보철·임플란트 보장 조건을 명확히 안내하세요.",
    "driver": "운전자보험의 사고 대응·형사합의 관련 안내를 점검하세요.",
    "woman": "여성건강보험은 질환 예방 정보와 보장 안내를 구분하세요.",
    "birth": "태아·자녀보험의 가입 시기와 필요 서류 FAQ를 점검하세요.",
    "overseas": "여행보험의 항공지연·휴대품·의료비 보장 안내를 점검하세요.",
    "overseaslong": "장기체류보험의 체류기간·현지 의료 관련 안내를 점검하세요.",
    "holeinone": "홀인원보험의 가입 단위·보장 조건·청구 방법을 점검하세요.",
    "event": "행사배상책임보험의 가입 대상·행사 유형·가입 시점을 확인하세요.",
    "chronic": "간편보험의 고지 항목과 가입 가능 조건을 쉽게 설명하세요.",
}


def clean_text(value):
    text = re.sub(r"<[^>]*>", "", str(value or ""))
    text = text.replace("&quot;", '"').replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    return re.sub(r"\s+", " ", text).strip(" .…")


def concise(value, limit=180):
    """검색 설명문을 단어 중간에서 자르지 않는 짧은 문장으로 정리한다."""
    text = clean_text(value)
    if not text:
        return "공개 검색 결과에는 별도 설명이 없어 원문 확인이 필요합니다."
    text = re.sub(r"\.{2,}", ". ", text)
    sentences = re.split(r"(?<=[.!?다요])\s+", text)
    picked = ""
    for sentence in sentences:
        candidate = (picked + " " + sentence).strip()
        if len(candidate) > limit:
            break
        picked = candidate
        if len(picked) >= 70:
            break
    if not picked:
        picked = text[:limit].rsplit(" ", 1)[0] or text[:limit]
    picked = picked.rstrip(" ,;:")
    if picked and picked[-1] not in ".!?다요":
        picked += "…"
    return picked


def _fingerprint(title):
    norm = re.sub(r"[^0-9a-z가-힣]", "", clean_text(title).lower())
    return hashlib.sha1(norm.encode("utf-8")).hexdigest()[:12]


def _topic_tokens(title):
    stop = {"보험", "손해보험", "관련", "확대", "추진", "출시", "뉴스", "단독"}
    return {token for token in re.findall(r"[0-9a-z가-힣]{2,}", clean_text(title).lower()) if token not in stop}


def _similar_title(left, right):
    a = re.sub(r"[^0-9a-z가-힣]", "", clean_text(left).lower())
    b = re.sub(r"[^0-9a-z가-힣]", "", clean_text(right).lower())
    if not a or not b:
        return False
    grams_a = {a[i:i + 3] for i in range(max(1, len(a) - 2))}
    grams_b = {b[i:i + 3] for i in range(max(1, len(b) - 2))}
    return len(grams_a & grams_b) / max(1, len(grams_a | grams_b)) >= .2


def _score(key, category, item, main):
    title = clean_text(item.get("t"))
    gist = clean_text(item.get("gist"))
    text = f"{title} {gist}"
    if key in CATEGORY_TERMS and not any(term.lower() in text.lower() for term in CATEGORY_TERMS[key]):
        return -99
    if key.startswith("ind_"):
        query = clean_text(category.get("q", ""))
        haystack = title
        if key == "ind_biz" and not any(term in title for term in ("보험", "손보", "보험사")):
            return -99
        if key != "ind_biz" and query and query.lower() not in haystack.lower():
            return -99
    score = 0
    score += min(4, sum(1 for term in ACTION_TERMS if term in text))
    score += 2 if any(term in text for term in DOMAIN_TERMS) else -2
    score += 1 if key in main else 0
    score += 2 if key.startswith("ind_") and any(term in text for term in ("보험", "다이렉트", "광고", "상품")) else 0
    score -= 5 if any(term in text for term in NOISE_TERMS) else 0
    score -= 3 if "브리핑" in title and (" 외" in title or title.endswith("외")) else 0
    if category.get("q") and clean_text(category["q"]).split()[0] in text:
        score += 1
    return score


def _why_action(key, title, gist):
    text = f"{title} {gist}"
    for terms, why, action in WHY_RULES:
        if any(term in text for term in terms):
            return why, action
    if key.startswith("ind_"):
        return ("경쟁사의 움직임은 검색광고 소구와 상품 비교 기준에 영향을 줄 수 있습니다.",
                "상품·가격·프로모션의 실제 변경 여부를 확인하고 대응 필요성을 판단하세요.")
    return ("관련 상품의 고객 관심과 정보 탐색에 영향을 줄 수 있는 뉴스입니다.",
            PRODUCT_ACTIONS.get(key, "원문 근거를 확인한 뒤 소재·FAQ·랜딩 반영 여부를 판단하세요."))


def build_digest(clip, products, main, limit=8):
    """clips 하루치에서 채널 공통 브리프를 만든다."""
    products = products or {}
    main = set(main or [])
    candidates = []
    for key, category in (clip or {}).get("categories", {}).items():
        tag = products.get(key, {}).get("name") or category.get("name") or key
        if key == "ind_biz":
            tag = f"업계·{tag}"
        elif key.startswith("ind_"):
            tag = f"경쟁사·{tag}"
        for item in category.get("items", [])[:10]:
            title = clean_text(item.get("t"))
            if not title or not item.get("url"):
                continue
            score = _score(key, category, item, main)
            if score < 2:
                continue
            candidates.append((score, item.get("date", ""), key, tag, item))
    candidates.sort(key=lambda row: (row[0], row[1]), reverse=True)

    def as_story(score, date, key, tag, item):
        what = concise(item.get("gist"), 190)
        why, action = _why_action(key, item.get("t", ""), item.get("gist", ""))
        return {
            "id": _fingerprint(item.get("t")), "category": key, "tag": tag,
            "title": clean_text(item.get("t")), "source": item.get("src", ""),
            "date": date, "url": item.get("url", ""), "what": what,
            "why": why, "action": action, "score": score,
            "evidence_scope": "네이버 검색 결과 제목·설명문",
            "confidence": "중간" if len(clean_text(item.get("gist"))) >= 70 else "낮음",
        }

    stories, seen, per_key, topic_sets, selected_titles = [], set(), {}, [], []

    def add_candidate(row):
        score, date, key, tag, item = row
        fp = _fingerprint(item.get("t"))
        url_key = re.sub(r"[?#].*$", "", item.get("url", ""))
        if fp in seen or url_key in seen or per_key.get(key, 0) >= 2:
            return False
        tokens = _topic_tokens(item.get("t"))
        if tokens and any(len(tokens & old) / max(1, len(tokens | old)) >= .25 for old in topic_sets):
            return False
        if any(_similar_title(item.get("t"), old) for old in selected_titles):
            return False
        seen.update((fp, url_key))
        topic_sets.append(tokens)
        selected_titles.append(item.get("t", ""))
        per_key[key] = per_key.get(key, 0) + 1
        stories.append(as_story(score, date, key, tag, item))
        return True

    # 1차는 카테고리당 1건으로 다양성을 확보하고, 자리가 남을 때만 2차 기사를 채운다.
    for row in candidates:
        if row[2] in per_key:
            continue
        add_candidate(row)
        if len(stories) >= limit:
            break
    if len(stories) < limit:
        for row in candidates:
            add_candidate(row)
            if len(stories) >= limit:
                break

    # 전체 상위 기사와 별개로 각 카테고리의 최신 유효 기사도 최대 2건 유지한다.
    # 그래야 대시보드 일부 카테고리만 최신 요약되고 나머지는 정적 문구에 머무는 현상을 막을 수 있다.
    categories, category_seen = {}, {}
    for score, date, key, tag, item in candidates:
        group = categories.setdefault(key, {"name": tag, "stories": []})
        fp = _fingerprint(item.get("t"))
        seen_for_key = category_seen.setdefault(key, set())
        if fp in seen_for_key or len(group["stories"]) >= 2:
            continue
        seen_for_key.add(fp)
        group["stories"].append(as_story(score, date, key, tag, item))
    for group in categories.values():
        group["summary"] = " ".join(story["what"] for story in group["stories"][:2])
        group["insight"] = group["stories"][0]["action"]

    return {
        "schema_version": 1,
        "date": (clip or {}).get("date") or datetime.now(KST).strftime("%Y-%m-%d"),
        "asof": (clip or {}).get("asof") or datetime.now(KST).strftime("%Y-%m-%d %H:%M"),
        "source_scope": "공개 뉴스 검색의 제목·설명문 기반 요약이며 기사 원문 전체 요약이 아님",
        "stories": stories, "categories": categories,
        "quality": {"selected": len(stories), "candidate_count": len(candidates), "noise_rule": "주가·인사·수상 등 비마케팅 기사 감점"},
    }


def write_latest(root):
    """저장소의 최신 클리핑으로 배포용 공통 브리프 파일을 재생성한다."""
    with open(os.path.join(root, "data", "clips", "index.json"), encoding="utf-8") as f:
        index = json.load(f)
    latest = index["dates"][0]["date"]
    with open(os.path.join(root, "data", "clips", f"{latest}.json"), encoding="utf-8") as f:
        clip = json.load(f)
    with open(os.path.join(root, "data", "products.json"), encoding="utf-8") as f:
        pdata = json.load(f)
    plist = pdata if isinstance(pdata, list) else pdata.get("products", [])
    digest = build_digest(clip, {p["key"]: p for p in plist}, [] if isinstance(pdata, list) else pdata.get("main", []))
    out_dir = os.path.join(root, "data", "briefing")
    os.makedirs(out_dir, exist_ok=True)
    for name in (f"{latest}.json", "latest.json"):
        with open(os.path.join(out_dir, name), "w", encoding="utf-8") as f:
            json.dump(digest, f, ensure_ascii=False, indent=1)
    return digest


if __name__ == "__main__":
    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    result = write_latest(repo)
    print(f"✔ data/briefing/latest.json · {result['date']} · 주요 뉴스 {len(result['stories'])}건 · 카테고리 {len(result['categories'])}개")
