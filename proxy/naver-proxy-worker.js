/*
 * naver-proxy-worker.js — Cloudflare Worker (무료) CORS 프록시
 *
 * 목적: 브라우저에서 직접 못 부르는 네이버 API(CORS 차단 + 검색광고 HMAC 서명)를
 *       사용자 소유 워커가 대신 호출 → 툴이 "URL에서 바로" 실시간 데이터를 받음.
 *
 * 키 전달 두 방식 (둘 중 아무거나):
 *   (A) 요청 헤더로 전달  — 허브 ⚙설정창(localStorage)에 넣은 키를 브라우저가 헤더로 보냄
 *         x-mf-naver-id / x-mf-naver-secret               (검색·데이터랩)
 *         x-mf-ad-key / x-mf-ad-secret / x-mf-ad-customer (검색광고)
 *   (B) 워커 시크릿으로 전달 — `wrangler secret put NAVER_ID` 등으로 1회 등록(브라우저에 키 노출 0, 더 안전)
 *
 * 라우트:
 *   GET  /naver/v1/search/news.json?query=...           → openapi.naver.com (뉴스)
 *   POST /naver/v1/datalab/search                        → openapi.naver.com (데이터랩 트렌드)
 *   POST /searchad/keywordstool?...                      → api.searchad.naver.com (검색량, HMAC 자동 서명)
 *
 * 배포: 아래 docs/api-from-url.md 참고 (wrangler deploy 한 줄).
 * 보안: ALLOW_ORIGIN 을 본인 Pages 도메인으로 좁히세요(기본은 * — 데모용).
 */

const ALLOW_ORIGIN = "https://imsplendid8.github.io"; // 팀 Pages 도메인만 허용(남이 내 워커 못 씀). 로컬 테스트 땐 잠시 "*"

const cors = (extra = {}) => ({
  "Access-Control-Allow-Origin": ALLOW_ORIGIN,
  "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
  "Access-Control-Allow-Headers": "content-type,x-mf-naver-id,x-mf-naver-secret,x-mf-ad-key,x-mf-ad-secret,x-mf-ad-customer",
  "Access-Control-Max-Age": "86400",
  ...extra,
});
const json = (obj, status = 200) =>
  new Response(JSON.stringify(obj), { status, headers: cors({ "content-type": "application/json; charset=utf-8" }) });

async function hmacSha256B64(secret, msg) {
  const key = await crypto.subtle.importKey("raw", new TextEncoder().encode(secret), { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
  const sig = await crypto.subtle.sign("HMAC", key, new TextEncoder().encode(msg));
  return btoa(String.fromCharCode(...new Uint8Array(sig)));
}

// ── 사용량 카운트 (KV 'USAGE' 바인딩 있을 때만 · 없으면 조용히 생략) ──
const today = () => new Date().toISOString().slice(0, 10);            // UTC 기준일
const DAILY_LIMIT = { search: 25000, datalab: 1000, searchad: null }; // 네이버 공개 일한도
async function bump(env, cat) {
  if (!env || !env.USAGE) return;
  try {
    const k = `u:${cat}:${today()}`;
    const n = parseInt((await env.USAGE.get(k)) || "0", 10) + 1;
    await env.USAGE.put(k, String(n), { expirationTtl: 172800 }); // 2일 후 자동 만료
  } catch (e) {}
}
async function usageReport(env) {
  const date = today();
  const out = { date, tracked: !!(env && env.USAGE), limits: DAILY_LIMIT, usage: { search: 0, datalab: 0, searchad: 0 } };
  if (env && env.USAGE) {
    for (const cat of ["search", "datalab", "searchad"]) {
      out.usage[cat] = parseInt((await env.USAGE.get(`u:${cat}:${date}`)) || "0", 10);
    }
  }
  return out;
}

export default {
  async fetch(req, env) {
    if (req.method === "OPTIONS") return new Response(null, { headers: cors() });
    const url = new URL(req.url);
    const h = req.headers;
    const p = url.pathname;

    try {
      // ── 네이버 검색·데이터랩 ──────────────────────────────
      if (p.startsWith("/naver/")) {
        const id = h.get("x-mf-naver-id") || env.NAVER_ID;
        const secret = h.get("x-mf-naver-secret") || env.NAVER_SECRET;
        if (!id || !secret) return json({ error: "네이버 Client ID/Secret 없음 (설정창 또는 워커 시크릿)" }, 400);
        const target = "https://openapi.naver.com" + p.replace(/^\/naver/, "") + url.search;
        const init = {
          method: req.method,
          headers: { "X-Naver-Client-Id": id, "X-Naver-Client-Secret": secret },
        };
        if (req.method === "POST") { init.headers["Content-Type"] = "application/json"; init.body = await req.text(); }
        const r = await fetch(target, init);
        const body = await r.text();
        await bump(env, p.includes("/datalab") ? "datalab" : "search");
        return new Response(body, { status: r.status, headers: cors({ "content-type": "application/json; charset=utf-8" }) });
      }

      // ── 네이버 검색광고 (HMAC-SHA256 서명) ───────────────
      if (p.startsWith("/searchad/")) {
        const key = h.get("x-mf-ad-key") || env.AD_KEY;
        const secret = h.get("x-mf-ad-secret") || env.AD_SECRET;
        const customer = h.get("x-mf-ad-customer") || env.AD_CUSTOMER;
        if (!key || !secret || !customer) return json({ error: "검색광고 키/시크릿/Customer 없음" }, 400);
        const apiPath = p.replace(/^\/searchad/, "");
        const method = req.method;
        const ts = Date.now().toString();
        const sign = await hmacSha256B64(secret, `${ts}.${method}.${apiPath}`);
        const target = "https://api.searchad.naver.com" + apiPath + url.search;
        const init = {
          method,
          headers: {
            "X-Timestamp": ts,
            "X-API-KEY": key,
            "X-Customer": customer,
            "X-Signature": sign,
            "Content-Type": "application/json; charset=UTF-8",
          },
        };
        if (method === "POST") init.body = await req.text();
        const r = await fetch(target, init);
        const body = await r.text();
        await bump(env, "searchad");
        return new Response(body, { status: r.status, headers: cors({ "content-type": "application/json; charset=utf-8" }) });
      }

      // ── 사용량 조회 (대시보드 위젯) ───────────────────────
      if (p === "/usage") return json(await usageReport(env));

      if (p === "/" || p === "/health") return json({ ok: true, service: "modooflow-naver-proxy" });
      return json({ error: "unknown route" }, 404);
    } catch (e) {
      return json({ error: String(e && e.message || e) }, 502);
    }
  },
};
