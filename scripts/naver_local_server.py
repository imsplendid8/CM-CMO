#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
네이버 검색광고 '로컬 연동 서버' — 이거 하나면 대시보드에서 바로 연동됩니다.

실행:
    python3 scripts/naver_local_server.py
그다음 브라우저에서:
    http://localhost:8787/keyword-tool.html
페이지의 '🔌 네이버 실시간 연동'에 키 3개 입력 → 버튼 클릭 → 검색량이 표에 채워집니다.

두 가지 연동을 제공합니다:
  • POST /naver  검색광고 키워드도구(검색량·경쟁도) — API_KEY·SECRET·CUSTOMER (검색광고 API)
  • POST /news   뉴스 검색(카테고리 뉴스 실시간 갱신) — Client ID/Secret (개발자센터 검색 API)

동작: 브라우저(localhost) → 이 서버(내 PC) → 네이버 API(HTTPS).
키는 내 PC 밖으로 나가지 않습니다. (표준 라이브러리만 사용 · pip 불필요)
"""
import http.server, socketserver, json, os, time, hmac, hashlib, base64, re, urllib.parse, urllib.request
from datetime import datetime

PORT = 8787
BASE = "https://api.searchad.naver.com"
NEWS_BASE = "https://openapi.naver.com/v1/search/news.json"   # 네이버 개발자센터 검색 API(뉴스)

def _sign(secret, ts, method, path):
    msg = f"{ts}.{method}.{path}"
    return base64.b64encode(hmac.new(secret.encode(), msg.encode(), hashlib.sha256).digest()).decode()

def _num(v):
    if isinstance(v, str):
        return 0 if "<" in v else int(v.replace(",", "") or 0)
    return int(v or 0)

def keywordstool(api, secret, cust, hints):
    path = "/keywordstool"
    ts = str(int(time.time() * 1000))
    q = urllib.parse.urlencode({"hintKeywords": ",".join(hints), "showDetail": "1"})
    req = urllib.request.Request(f"{BASE}{path}?{q}", headers={
        "X-Timestamp": ts, "X-API-KEY": api, "X-Customer": str(cust),
        "X-Signature": _sign(secret, ts, "GET", path),
    })
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.load(r)

def _clean(s):   # <b> 태그·HTML 엔티티 제거
    s = re.sub(r"<[^>]+>", "", s or "")
    for a, b in (("&amp;", "&"), ("&lt;", "<"), ("&gt;", ">"), ("&quot;", '"'), ("&#39;", "'"), ("&apos;", "'")):
        s = s.replace(a, b)
    return s.strip()

def _src(url):   # 링크 도메인 → 출처 표기
    try:
        return urllib.parse.urlparse(url).netloc.replace("www.", "").split(".")[0]
    except Exception:
        return ""

def _date(pub):  # 'Wed, 22 Jul 2026 17:56:00 +0900' → '2026-07-22'
    try:
        return datetime.strptime(pub[:25].strip(), "%a, %d %b %Y %H:%M:%S").strftime("%Y-%m-%d")
    except Exception:
        return (pub or "")[:16]

def news_search(cid, csec, query, display=8):
    q = urllib.parse.urlencode({"query": query, "display": max(1, min(int(display or 8), 20)), "sort": "date"})
    req = urllib.request.Request(f"{NEWS_BASE}?{q}", headers={
        "X-Naver-Client-Id": cid, "X-Naver-Client-Secret": csec,
    })
    with urllib.request.urlopen(req, timeout=15) as r:
        data = json.load(r)
    out = []
    for it in data.get("items", []):
        url = it.get("originallink") or it.get("link") or ""
        out.append({"t": _clean(it.get("title")), "gist": _clean(it.get("description"))[:120],
                    "src": _src(url), "date": _date(it.get("pubDate")), "url": url})
    return out

class Handler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def _json(self, obj):
        payload = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(payload)

    def do_POST(self):
        route = self.path.split("?")[0]
        if route not in ("/naver", "/news"):
            self.send_error(404); return
        try:
            ln = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(ln) or b"{}")
        except Exception:
            body = {}
        if route == "/news":
            cid = (body.get("clientId") or "").strip()
            csec = (body.get("clientSecret") or "").strip()
            query = (body.get("query") or "").strip()
            items, err = [], None
            if not (cid and csec):
                err = "네이버 개발자센터 검색 API의 Client ID/Secret을 입력하세요 (검색광고 키와 다름)"
            elif not query:
                err = "검색어(상품 시드)가 없습니다"
            else:
                try:
                    items = news_search(cid, csec, query, body.get("display", 8))
                except urllib.error.HTTPError as e:
                    err = f"네이버 응답 {e.code} — Client ID/Secret 또는 검색 API 사용 설정을 확인하세요"
                except Exception as e:
                    err = str(e)
            self._json({"items": items, "error": err}); return
        api = (body.get("apiKey") or "").strip()
        secret = (body.get("secret") or "").strip()
        cust = str(body.get("customer") or "").strip()
        seeds = [s for s in (body.get("seeds") or []) if s][:20]
        out, err = {}, None
        if not (api and secret and cust):
            err = "키 3개(API_KEY·SECRET·CUSTOMER)를 모두 입력하세요"
        else:
            try:
                for i in range(0, len(seeds), 5):                 # keywordstool: 시드 5개/호출
                    data = keywordstool(api, secret, cust, seeds[i:i+5])
                    for row in data.get("keywordList", []):
                        out[row["relKeyword"]] = {
                            "pc": _num(row.get("monthlyPcQcCnt")),
                            "mobile": _num(row.get("monthlyMobileQcCnt")),
                            "comp": row.get("compIdx", ""),
                        }
                    time.sleep(0.25)
            except urllib.error.HTTPError as e:
                err = f"네이버 응답 {e.code} — 키/CUSTOMER ID를 확인하세요"
            except Exception as e:
                err = str(e)
        payload = json.dumps({"keywords": out, "error": err}, ensure_ascii=False).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *a):   # 키가 URL에 없으니 조용히
        pass

if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # 레포 루트에서 파일 서빙
    print(f"▶ 연동 서버 실행 중.  브라우저에서 열기:  http://localhost:{PORT}/keyword-tool.html")
    print("   (종료: Ctrl+C)")
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("127.0.0.1", PORT), Handler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n종료")
