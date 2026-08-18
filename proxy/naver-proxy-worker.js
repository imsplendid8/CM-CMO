/*
 * naver-proxy-worker.js — Cloudflare Worker (무료) CORS 프록시
 *
 * 목적: 브라우저에서 직접 못 부르는 네이버 API(CORS 차단 + 검색광고 HMAC 서명)를
 *       팀 소유 워커가 대신 호출 → 툴이 "URL에서 바로" 실시간 데이터를 받음.
 *
 * 요청 허용 정책(중요):
 *   ① 출처 화이트리스트 — 브라우저 CORS 정책용이다. Origin/Referer는 인증 수단이 아니다.
 *   ② 키는 '워커 시크릿만' 사용 — 브라우저 헤더로 키를 받지 않음(x-mf-* override 폐지) → 브라우저 키 노출 0.
 *        wrangler secret put NAVER_ID / NAVER_SECRET            (검색·데이터랩)
 *        wrangler secret put AD_KEY / AD_SECRET / AD_CUSTOMER    (검색광고)
 *   ③ 라우트·메서드 화이트리스트 — 정의된 엔드포인트/메서드만 통과(그 외 404).
 *   ④ (KV 'USAGE' 있을 때) IP·일 단위 요청 상한 — 남용/과용 차단(초과 429).
 *
 * 라우트:
 *   GET  /naver/v1/search/*                → openapi.naver.com (검색: 뉴스 등)
 *   POST /naver/v1/datalab/*               → openapi.naver.com (데이터랩 트렌드)
 *   GET  /searchad/keywordstool            → api.searchad.naver.com (검색량 조회 전용, HMAC 자동 서명)
 *   GET  /usage                            → 사용량(대시보드 위젯, 허용 출처만)
 *   GET  /  ·  /health                     → 상태(공개)
 *
 * 배포: docs/api-from-url.md 참고 (wrangler deploy 한 줄).
 */

// 허용 출처(팀 Pages 도메인). 로컬 디버그가 필요하면 잠시 "http://localhost:8787" 등을 추가.
const ALLOW_ORIGINS = [
  "https://imsplendid8.github.io",
];
const IP_DAILY_MAX = 3000; // KV 있을 때 IP별 하루 요청 상한(초과 시 429). null 이면 무제한.
const MAX_QUERY_LENGTH = 4096;
const MAX_BODY_BYTES = 64 * 1024;

const matchOrigin = (v) => {
  if (!v) return null;
  for (const o of ALLOW_ORIGINS) if (v === o || v.startsWith(o + "/")) return o;
  return null;
};
// 요청 출처 판정: Origin(브라우저가 CORS로 부착) 우선, 없으면 Referer 접두로 확인.
const allowedOrigin = (req) => matchOrigin(req.headers.get("Origin")) || matchOrigin(req.headers.get("Referer"));

const corsFor = (origin, extra = {}) => ({
  "Access-Control-Allow-Origin": origin || ALLOW_ORIGINS[0],
  "Vary": "Origin",
  "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
  "Access-Control-Allow-Headers": "content-type",
  "Access-Control-Max-Age": "86400",
  "Cache-Control": "no-store",
  "X-Content-Type-Options": "nosniff",
  ...extra,
});
const jsonFor = (origin, obj, status = 200) =>
  new Response(JSON.stringify(obj), { status, headers: corsFor(origin, { "content-type": "application/json; charset=utf-8" }) });

// 라우트·메서드 화이트리스트
function routeAllowed(method, p) {
  if (p.startsWith("/naver/v1/search/")) return method === "GET";
  if (p.startsWith("/naver/v1/datalab/")) return method === "POST";
  // 공개 브라우저 경로는 검색량 조회만 허용한다. /ncc/* 등 광고 관리 API는 절대 전달하지 않는다.
  if (p === "/searchad/keywordstool") return method === "GET";
  return false;
}

async function hmacSha256B64(secret, msg) {
  const key = await crypto.subtle.importKey("raw", new TextEncoder().encode(secret), { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
  const sig = await crypto.subtle.sign("HMAC", key, new TextEncoder().encode(msg));
  return btoa(String.fromCharCode(...new Uint8Array(sig)));
}

// ── 사용량/레이트리밋 (KV 'USAGE' 바인딩 있을 때만 · 없으면 조용히 생략) ──
const today = () => new Date().toISOString().slice(0, 10); // UTC 기준일
const DAILY_LIMIT = { search: 25000, datalab: 1000, searchad: null };
async function bump(env, cat) {
  if (!env || !env.USAGE) return;
  try {
    const k = `u:${cat}:${today()}`;
    const n = parseInt((await env.USAGE.get(k)) || "0", 10) + 1;
    await env.USAGE.put(k, String(n), { expirationTtl: 172800 });
  } catch (e) {}
}
async function rateOk(env, req) {
  if (!env || !env.USAGE || IP_DAILY_MAX == null) return true;
  try {
    const ip = req.headers.get("CF-Connecting-IP") || "0";
    const k = `rl:${ip}:${today()}`;
    const n = parseInt((await env.USAGE.get(k)) || "0", 10) + 1;
    await env.USAGE.put(k, String(n), { expirationTtl: 172800 });
    return n <= IP_DAILY_MAX;
  } catch (e) { return false; }
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
    const url = new URL(req.url);
    const p = url.pathname;
    const origin = allowedOrigin(req);

    // 프리플라이트 — 허용 출처에만 CORS 부여, 그 외 403
    if (req.method === "OPTIONS") {
      return origin ? new Response(null, { headers: corsFor(origin) }) : new Response(null, { status: 403 });
    }

    // 상태 확인은 공개(모니터링용)
    if (p === "/" || p === "/health") return jsonFor(origin, { ok: true, service: "modooflow-naver-proxy" });

    // ① 출처 화이트리스트 — 그 외 전부 차단
    if (!origin) return jsonFor(null, { error: "forbidden: origin not allowed" }, 403);

    // 사용량 위젯(허용 출처만)
    if (p === "/usage") return jsonFor(origin, await usageReport(env));

    // ③ 라우트·메서드 화이트리스트
    if (!routeAllowed(req.method, p)) return jsonFor(origin, { error: "route/method not allowed" }, 404);

    // 비정상적으로 큰 쿼리·본문은 외부 API와 Worker 자원을 사용하기 전에 거부한다.
    if (url.search.length > MAX_QUERY_LENGTH) return jsonFor(origin, { error: "query too large" }, 414);
    const contentLength = Number(req.headers.get("content-length") || 0);
    if (Number.isFinite(contentLength) && contentLength > MAX_BODY_BYTES) {
      return jsonFor(origin, { error: "request body too large" }, 413);
    }

    // ④ IP·일 요청 상한
    if (!(await rateOk(env, req))) return jsonFor(origin, { error: "rate limit exceeded" }, 429);

    try {
      // ── 네이버 검색·데이터랩 (키=워커 시크릿만) ──
      if (p.startsWith("/naver/")) {
        const id = env.NAVER_ID, secret = env.NAVER_SECRET;
        if (!id || !secret) return jsonFor(origin, { error: "server not configured: NAVER_ID/SECRET" }, 500);
        const target = "https://openapi.naver.com" + p.replace(/^\/naver/, "") + url.search;
        const init = { method: req.method, headers: { "X-Naver-Client-Id": id, "X-Naver-Client-Secret": secret } };
        if (req.method === "POST") { init.headers["Content-Type"] = "application/json"; init.body = await req.text(); }
        const r = await fetch(target, init);
        const body = await r.text();
        await bump(env, p.includes("/datalab") ? "datalab" : "search");
        return new Response(body, { status: r.status, headers: corsFor(origin, { "content-type": "application/json; charset=utf-8" }) });
      }

      // ── 네이버 검색광고 (HMAC-SHA256 서명, 키=워커 시크릿만) ──
      if (p === "/searchad/keywordstool") {
        const key = env.AD_KEY, secret = env.AD_SECRET, customer = env.AD_CUSTOMER;
        if (!key || !secret || !customer) return jsonFor(origin, { error: "server not configured: AD_KEY/AD_SECRET/AD_CUSTOMER" }, 500);
        const apiPath = p.replace(/^\/searchad/, "");
        const method = "GET";
        const ts = Date.now().toString();
        const sign = await hmacSha256B64(secret, `${ts}.${method}.${apiPath}`);
        const target = "https://api.searchad.naver.com" + apiPath + url.search;
        const init = {
          method,
          headers: {
            "X-Timestamp": ts, "X-API-KEY": key, "X-Customer": customer, "X-Signature": sign,
            "Content-Type": "application/json; charset=UTF-8",
          },
        };
        const r = await fetch(target, init);
        const body = await r.text();
        await bump(env, "searchad");
        return new Response(body, { status: r.status, headers: corsFor(origin, { "content-type": "application/json; charset=utf-8" }) });
      }

      return jsonFor(origin, { error: "unknown route" }, 404);
    } catch (e) {
      return jsonFor(origin, { error: String((e && e.message) || e) }, 502);
    }
  },
};
