#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
캡쳐 개인정보 자동 마스킹 (로컬 전용)

한국어 OCR로 화면 캡쳐의 텍스트와 위치를 검출하고,
주민번호·차량번호·면허번호·전화·계좌/카드·이메일·생년월일 등을 자동으로 가립니다.
'라벨 인접 마스킹'으로 이름/주소처럼 패턴이 없는 값도 라벨 옆/아래를 가립니다.

⚠️ 자동검출은 100%가 아닙니다. 실행 후 생성되는 review_report.html 로
   누락/과다 가림을 반드시 사람이 최종 확인하세요.

설치:
  pip install -r requirements-masker.txt
  # EasyOCR 사용 시 최초 1회 모델 자동 다운로드(인터넷 필요).
  # Tesseract 사용 시: 별도 tesseract 바이너리 + 한국어 데이터(kor) 설치 필요.

사용:
  python3 masker.py                      # capture/ -> capture_masked/ (기본: 예시값 치환)
  python3 masker.py --style box          # 예시 치환 대신 검정 박스
  python3 masker.py --style blur         # 모자이크
  python3 masker.py --font /path/to.ttf  # 치환 텍스트용 한국어 폰트 지정
  python3 masker.py --engine tesseract   # 가벼운 엔진
  python3 masker.py --mask-money         # 보험료/금액(계약 민감)도 처리
  python3 masker.py --no-safe            # 안전모드(여분 숫자 가림) 끄기

기본은 '예시 치환'(이름→김한화 등)으로, 실제 값 위에 가짜 예시를 그려 화면을 자연스럽게
유지합니다. 한국어 폰트가 없으면 해당 항목은 검정 박스로 자동 대체됩니다.
"""
import os, re, sys, argparse, html, glob

# ---------- 마스킹 대상 패턴 (값 자체로 식별 가능한 것) ----------
PII_PATTERNS = {
    "주민등록번호": re.compile(r"\d{6}\s*[-~]?\s*[1-4]\d{6}"),
    "주민번호(부분)": re.compile(r"\b\d{6}\s*[-~]?\s*[1-4]\b"),
    "운전면허번호": re.compile(r"\d{2}\s*[-]?\s*\d{2}\s*[-]?\s*\d{6}\s*[-]?\s*\d{2}"),
    "차량번호(신)": re.compile(r"\b\d{2,3}\s*[가-힣]\s*\d{4}\b"),
    "차량번호(구)": re.compile(r"[가-힣]{2}\s*\d{2}\s*[가-힣]\s*\d{4}"),
    "휴대폰": re.compile(r"01[016789]\s*[-.]?\s*\d{3,4}\s*[-.]?\s*\d{4}"),
    "전화번호": re.compile(r"\b0\d{1,2}\s*[-.]?\s*\d{3,4}\s*[-.]?\s*\d{4}\b"),
    "카드번호": re.compile(r"\b\d{4}\s*[- ]?\s*\d{4}\s*[- ]?\s*\d{4}\s*[- ]?\s*\d{4}\b"),
    "계좌번호": re.compile(r"\b\d{2,6}\s*-\s*\d{2,6}\s*-\s*\d{2,6}(\s*-\s*\d{1,6})?\b"),
    "이메일": re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}"),
    "생년월일": re.compile(r"\b(19|20)\d{2}\s*[./\-년]\s*\d{1,2}\s*[./\-월]\s*\d{1,2}\s*일?\b"),
}
# 금액/보험료 (옵션)
MONEY_PATTERN = re.compile(r"\d{1,3}(,\d{3})+\s*원?|\b\d+\s*만\s*원\b")

# ---------- 라벨 인접 마스킹 (값에 패턴이 없는 이름/주소 등) ----------
# 라벨 텍스트가 보이면, 같은 줄 오른쪽 또는 바로 아래 박스를 값으로 보고 가림
LABEL_KEYWORDS = [
    "이름", "성명", "가입자", "피보험자", "운전자", "계약자", "예금주",
    "주소", "거주지", "자택", "직장주소",
    "연락처", "휴대폰", "전화", "핸드폰",
    "주민", "주민등록", "생년월일", "생일",
    "면허", "면허번호", "차량번호", "차대번호",
    "계좌", "카드번호", "이메일", "메일",
]
SAFE_DIGIT = re.compile(r"\d{6,}")  # 안전모드: 6자리 이상 연속 숫자

# ---------- 예시 치환 값 (style=replace) ----------
# 실제 값 위에 가짜 예시값을 그려 화면을 자연스럽게 유지. (mask-tool.html 과 동일)
EX = {
    "이름": "김한화", "주민번호": "820101-1******",
    "주소": "서울 영등포구 여의대로 56 한화손해보험", "전화": "010-1234-5678",
    "생년월일": "1982-01-01", "차량번호": "12가3456",
    "면허번호": "12-34-567890-12", "이메일": "sample@hwgeneralins.com",
    "카드": "1234-5678-9012-3456", "계좌": "123-456-789012", "금액": "100,000원",
}
PATTERN_TO_CAT = {
    "주민등록번호": "주민번호", "주민번호(부분)": "주민번호", "운전면허번호": "면허번호",
    "차량번호(신)": "차량번호", "차량번호(구)": "차량번호", "휴대폰": "전화", "전화번호": "전화",
    "카드번호": "카드", "계좌번호": "계좌", "이메일": "이메일", "생년월일": "생년월일", "금액": "금액",
}
LABEL_TO_CAT = [
    (["이름", "성명", "가입자", "피보험자", "운전자", "계약자", "예금주"], "이름"),
    (["주소", "거주지", "자택", "직장주소"], "주소"),
    (["연락처", "휴대폰", "전화", "핸드폰"], "전화"),
    (["주민"], "주민번호"), (["생년월일", "생일"], "생년월일"), (["면허"], "면허번호"),
    (["차량번호", "차대번호"], "차량번호"), (["계좌"], "계좌"), (["카드"], "카드"),
    (["이메일", "메일"], "이메일"),
]
FONT_CANDIDATES = [
    "/System/Library/Fonts/AppleSDGothicNeo.ttc", "/Library/Fonts/AppleGothic.ttf",
    "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    "C:/Windows/Fonts/malgun.ttf",
]


def find_font(override):
    for c in ([override] if override else []) + FONT_CANDIDATES:
        if c and os.path.exists(c):
            return c
    return None


def example_value(reason):
    """검출 사유(reason) → 치환할 예시값. 모르면 None(→검정 박스 대체)."""
    if reason.startswith("라벨인접:"):
        lab = reason.split(":", 1)[1]
        for keys, cat in LABEL_TO_CAT:
            if any(k in lab for k in keys):
                return EX.get(cat)
        return None
    return EX.get(PATTERN_TO_CAT.get(reason))


def get_ocr(engine, langs):
    """엔진별 OCR 함수 반환. 결과: [(text, (x0,y0,x1,y1), conf), ...]"""
    if engine == "easyocr":
        import easyocr
        reader = easyocr.Reader([l for l in langs], gpu=False)
        def run(path):
            out = []
            for box, text, conf in reader.readtext(path):
                xs = [p[0] for p in box]; ys = [p[1] for p in box]
                out.append((text, (min(xs), min(ys), max(xs), max(ys)), float(conf)))
            return out
        return run
    elif engine == "tesseract":
        import pytesseract
        from PIL import Image
        lang = "+".join("kor" if l == "ko" else "eng" for l in langs)
        def run(path):
            img = Image.open(path)
            d = pytesseract.image_to_data(img, lang=lang, output_type=pytesseract.Output.DICT)
            out = []
            for i in range(len(d["text"])):
                t = d["text"][i].strip()
                if not t:
                    continue
                x, y, w, h = d["left"][i], d["top"][i], d["width"][i], d["height"][i]
                conf = float(d["conf"][i]) / 100.0 if d["conf"][i] not in ("-1", -1) else 0.0
                out.append((t, (x, y, x + w, y + h), conf))
            return out
        return run
    raise SystemExit(f"알 수 없는 엔진: {engine}")


def classify(text, mask_money, safe):
    """이 텍스트가 마스킹 대상이면 (사유) 반환, 아니면 None."""
    for name, pat in PII_PATTERNS.items():
        if pat.search(text):
            return name
    if mask_money and MONEY_PATTERN.search(text):
        return "금액"
    if safe and SAFE_DIGIT.search(text):
        return "숫자(안전모드)"
    return None


def is_label(text):
    return any(k in text for k in LABEL_KEYWORDS)


def neighbor_value_indices(idx, items):
    """라벨 박스(idx)의 값으로 추정되는 인접 박스 인덱스들."""
    _, (x0, y0, x1, y1), _ = items[idx]
    h = y1 - y0
    cy = (y0 + y1) / 2
    found = []
    for j, (_, (jx0, jy0, jx1, jy1), _) in enumerate(items):
        if j == idx:
            continue
        jcy = (jy0 + jy1) / 2
        # 같은 줄 오른쪽 (세로 겹침 + 오른쪽에 위치, 가까운 것)
        same_line = abs(jcy - cy) < h * 0.7
        if same_line and jx0 >= x1 - 2 and jx0 - x1 < h * 12:
            found.append(j)
        # 바로 아래 (가로 겹침 + 한 줄 아래)
        horiz_overlap = min(x1, jx1) - max(x0, jx0) > 0
        if horiz_overlap and 0 < jy0 - y1 < h * 1.8:
            found.append(j)
    return found


def _clamp_box(box, W, H):
    x0, y0, x1, y1 = box
    pad = max(2, int((y1 - y0) * 0.15))
    return (max(0, int(x0) - pad), max(0, int(y0) - pad),
            min(W, int(x1) + pad), min(H, int(y1) + pad))


def mask_image(path, out_path, items, targets, style, font_path=None):
    """targets: {박스 인덱스: 검출사유}. 스타일대로 처리해 저장."""
    if style == "replace":
        _mask_replace(path, out_path, items, targets, font_path)
        return
    import cv2
    img = cv2.imread(path)
    if img is None:
        from PIL import Image
        import numpy as np
        img = cv2.cvtColor(np.array(Image.open(path).convert("RGB")), cv2.COLOR_RGB2BGR)
    H, W = img.shape[:2]
    for j in targets:
        x0, y0, x1, y1 = _clamp_box(items[j][1], W, H)
        if x1 <= x0 or y1 <= y0:
            continue
        if style == "blur":
            roi = img[y0:y1, x0:x1]
            k = max(9, ((min(x1 - x0, y1 - y0) // 4) | 1))
            img[y0:y1, x0:x1] = cv2.GaussianBlur(roi, (k, k), 0)
        else:
            cv2.rectangle(img, (x0, y0), (x1, y1), (0, 0, 0), -1)
    cv2.imwrite(out_path, img)


def _mask_replace(path, out_path, items, targets, font_path):
    """실제 값 위에 예시값을 그려 자연스럽게 치환. 값/폰트 없으면 검정 박스."""
    from PIL import Image, ImageDraw, ImageFont
    img = Image.open(path).convert("RGB")
    draw = ImageDraw.Draw(img)
    W, H = img.size
    for j, reason in targets.items():
        x0, y0, x1, y1 = _clamp_box(items[j][1], W, H)
        if x1 <= x0 or y1 <= y0:
            continue
        val = example_value(reason)
        if not val or not font_path:
            draw.rectangle([x0, y0, x1, y1], fill=(0, 0, 0))
            continue
        bg = img.getpixel((min(W - 1, x0 + 1), min(H - 1, y0 + 1)))[:3]
        draw.rectangle([x0, y0, x1, y1], fill=bg)
        lum = 0.299 * bg[0] + 0.587 * bg[1] + 0.114 * bg[2]
        color = (26, 26, 46) if lum > 140 else (255, 255, 255)
        h = y1 - y0
        ipad = max(2, int(h * 0.18))
        fs = max(10, int(h * 0.6))
        font = ImageFont.truetype(font_path, fs)
        try:
            while fs > 8 and draw.textlength(val, font=font) > (x1 - x0 - 2 * ipad):
                fs -= 1
                font = ImageFont.truetype(font_path, fs)
        except Exception:
            pass
        cy = (y0 + y1) // 2
        try:
            draw.text((x0 + ipad, cy), val, fill=color, font=font, anchor="lm")
        except TypeError:  # 구버전 Pillow: anchor 미지원
            draw.text((x0 + ipad, cy - fs // 2), val, fill=color, font=font)
    img.save(out_path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default="capture")
    ap.add_argument("--output", default="capture_masked")
    ap.add_argument("--engine", default="easyocr", choices=["easyocr", "tesseract"])
    ap.add_argument("--lang", default="ko,en")
    ap.add_argument("--style", default="replace", choices=["replace", "box", "blur"],
                    help="replace=예시값 치환(기본), box=검정박스, blur=모자이크")
    ap.add_argument("--font", default=None, help="치환 텍스트용 한국어 ttf/ttc 경로")
    ap.add_argument("--mask-money", action="store_true", help="보험료/금액도 처리")
    ap.add_argument("--no-safe", action="store_true", help="안전모드(여분 숫자 가림) 끄기")
    ap.add_argument("--min-conf", type=float, default=0.3, help="라벨 인접 마스킹 최소 신뢰도")
    args = ap.parse_args()

    safe = not args.no_safe
    langs = [s.strip() for s in args.lang.split(",") if s.strip()]
    os.makedirs(args.output, exist_ok=True)

    font_path = find_font(args.font) if args.style == "replace" else None
    if args.style == "replace":
        if font_path:
            print(f"치환 폰트: {font_path}")
        else:
            print("⚠️ 한국어 폰트를 못 찾아 '예시 치환'이 검정 박스로 대체됩니다. "
                  "(--font 경로로 지정하거나 NanumGothic 설치)")

    exts = ("*.png", "*.jpg", "*.jpeg", "*.webp", "*.bmp")
    files = sorted(f for e in exts for f in glob.glob(os.path.join(args.input, e)))
    if not files:
        sys.exit(f"'{args.input}/' 에서 이미지를 찾지 못했습니다.")

    print(f"엔진: {args.engine} · 이미지 {len(files)}장 · 안전모드 {'ON' if safe else 'OFF'}")
    ocr = get_ocr(args.engine, langs)

    report = []  # (rel_in, rel_out, [(reason, text)])
    for path in files:
        name = os.path.basename(path)
        out = os.path.join(args.output, os.path.splitext(name)[0] + "_masked.png")
        print(f"  처리중: {name} ...", end="", flush=True)
        items = ocr(path)
        targets, reasons = {}, []
        for i, (text, _, conf) in enumerate(items):
            r = classify(text, args.mask_money, safe)
            if r and i not in targets:
                targets[i] = r; reasons.append((r, text))
            if is_label(text) and conf >= args.min_conf:
                rs = "라벨인접:" + text.strip()
                for j in neighbor_value_indices(i, items):
                    if j not in targets:
                        targets[j] = rs; reasons.append((rs, items[j][0]))
        mask_image(path, out, items, targets, args.style, font_path)
        report.append((name, os.path.basename(out), reasons))
        print(f" 가림 {len(targets)}곳")

    write_report(args.output, report)
    # 대시보드용 manifest(captures.js) 자동 생성 (실패해도 마스킹 결과엔 영향 없음)
    try:
        import make_manifest
        mpath, mn = make_manifest.build(args.output)
        print(f"manifest 생성: {mpath} ({mn}개)")
    except Exception as e:
        print(f"(manifest 생성 건너뜀: {e} — 'python3 make_manifest.py' 로 수동 생성 가능)")
    print(f"\n완료. 검수 리포트: {os.path.join(args.output, 'review_report.html')}")
    print("⚠️ 리포트를 열어 누락/과다 가림을 반드시 사람이 확인하세요.")


def write_report(out_dir, report):
    rows = []
    for src, masked, reasons in report:
        items = "".join(
            f"<li><b>{html.escape(r)}</b> — <code>{html.escape(t)}</code></li>"
            for r, t in reasons
        ) or "<li style='color:#999'>검출/가림 없음 — 직접 확인 필요</li>"
        rows.append(
            f"<div class='card'><div class='hd'>{html.escape(src)} "
            f"<span class='cnt'>가림 {len(reasons)}곳</span></div>"
            f"<img src='{html.escape(masked)}'>"
            f"<details><summary>가린 항목 보기</summary><ul>{items}</ul></details></div>"
        )
    htmlout = (
        "<!DOCTYPE html><html lang='ko'><head><meta charset='UTF-8'>"
        "<title>마스킹 검수 리포트</title><style>"
        "body{font-family:-apple-system,'Apple SD Gothic Neo',sans-serif;background:#f4f5f7;padding:16px;color:#1a1a2e}"
        ".warn{background:#fff8e6;border:1px solid #f0dca0;border-radius:10px;padding:12px;font-size:13px;color:#8a6d1a;margin-bottom:14px}"
        ".grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:14px}"
        ".card{background:#fff;border:1px solid #e8eaf0;border-radius:12px;padding:12px}"
        ".hd{font-size:13px;font-weight:600;margin-bottom:8px;display:flex;justify-content:space-between}"
        ".cnt{color:#4f7cff;font-size:11px}"
        "img{width:100%;border:1px solid #eef0f4;border-radius:8px}"
        "details{margin-top:8px;font-size:12px}code{background:#f4f5f7;padding:1px 4px;border-radius:4px}"
        "ul{margin:6px 0 0 16px}li{margin:3px 0}</style></head><body>"
        "<h2>마스킹 검수 리포트</h2>"
        "<div class='warn'>⚠️ 자동검출은 100%가 아닙니다. 각 이미지에서 <b>가려지지 않은 개인정보가 없는지</b>, "
        "그리고 <b>분석에 필요한 내용이 과하게 가려지지 않았는지</b> 직접 확인하세요. "
        "문제가 있으면 mask-tool.html(수동 도구)로 보완하세요.</div>"
        "<div class='grid'>" + "".join(rows) + "</div></body></html>"
    )
    with open(os.path.join(out_dir, "review_report.html"), "w", encoding="utf-8") as f:
        f.write(htmlout)


if __name__ == "__main__":
    main()
