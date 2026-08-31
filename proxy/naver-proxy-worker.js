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
 *   ④ KV 'USAGE' 기반 경로별 IP·일 요청 상한 — 바인딩이 없으면 API 요청을 거부한다.
 *
 * 라우트:
 *   GET  /naver/v1/search/*                → openapi.naver.com (검색: 뉴스 등)
 *   POST /naver/v1/datalab/*               → openapi.naver.com (데이터랩 트렌드)
 *   GET  /searchad/keywordstool            → api.searchad.naver.com (검색량 조회 전용, HMAC 자동 서명)
 *   POST /v1/feedback                      → 비공개 D1 검수 이벤트(Cloudflare Access 필요)
 *   GET  /usage                            → 사용량(대시보드 위젯, 허용 출처만)
 *   GET  /  ·  /health                     → 상태(공개)
 *
 * 배포: docs/api-from-url.md 참고 (wrangler deploy 한 줄).
 */

// 허용 출처(팀 Pages 도메인). 로컬 디버그가 필요하면 잠시 "http://localhost:8787" 등을 추가.
const ALLOW_ORIGINS = [
  "https://imsplendid8.github.io",
];
const ROUTE_DAILY_MAX = { search: 500, datalab: 100, searchad: 100, feedback: 200 };
const MAX_QUERY_LENGTH = 4096;
const MAX_BODY_BYTES = 64 * 1024;
const MAX_FEEDBACK_META_BYTES = 8 * 1024;
const FEEDBACK_ACTIONS = new Set(["copied", "accepted", "edit_requested", "rejected"]);
const SHA256_HEX = /^[0-9a-f]{64}$/i;

const matchOrigin = (v) => {
  if (!v) return null;
  for (const o of ALLOW_ORIGINS) if (v === o || v.startsWith(o + "/")) return o;
  return null;
};
// 요청 출처 판정: Origin(브라우저가 CORS로 부착) 우선, 없으면 Referer 접두로 확인.
const allowedOrigin = (req) => matchOrigin(req.headers.get("Origin")) || matchOrigin(req.headers.get("Referer"));

const corsFor = (origin, extra = {}) => ({
  "Access-Control-Allow-Origin": origin || ALLOW_ORIGINS[0],
  "Access-Control-Allow-Credentials": "true",
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
  if (p === "/v1/feedback") return method === "POST";
  return false;
}

async function hmacSha256B64(secret, msg) {
  const key = await crypto.subtle.importKey("raw", new TextEncoder().encode(secret), { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
  const sig = await crypto.subtle.sign("HMAC", key, new TextEncoder().encode(msg));
  return btoa(String.fromCharCode(...new Uint8Array(sig)));
}

// ── 사용량/레이트리밋 ──
const today = () => new Date().toISOString().slice(0, 10); // UTC 기준일
const DAILY_LIMIT = { search: 25000, datalab: 1000, searchad: null, feedback: 5000 };
async function bump(env, cat) {
  try {
    const k = `u:${cat}:${today()}`;
    const n = parseInt((await env.USAGE.get(k)) || "0", 10) + 1;
    await env.USAGE.put(k, String(n), { expirationTtl: 172800 });
  } catch (e) {}
}
async function rateOk(env, req, cat) {
  if (!env || !env.USAGE) return false;
  try {
    const ip = req.headers.get("CF-Connecting-IP") || "0";
    const k = `rl:${cat}:${ip}:${today()}`;
    const n = parseInt((await env.USAGE.get(k)) || "0", 10) + 1;
    await env.USAGE.put(k, String(n), { expirationTtl: 172800 });
    return n <= ROUTE_DAILY_MAX[cat];
  } catch (e) { return false; }
}
const routeCategory = (p) => p.startsWith("/naver/v1/datalab/") ? "datalab"
  : p.startsWith("/naver/v1/search/") ? "search"
  : p === "/searchad/keywordstool" ? "searchad" : "feedback";
async function usageReport(env) {
  const date = today();
  const out = { date, tracked: !!(env && env.USAGE), limits: DAILY_LIMIT, usage: { search: 0, datalab: 0, searchad: 0, feedback: 0 } };
  if (env && env.USAGE) {
    for (const cat of ["search", "datalab", "searchad", "feedback"]) {
      out.usage[cat] = parseInt((await env.USAGE.get(`u:${cat}:${date}`)) || "0", 10);
    }
  }
  return out;
}

// ── 비공개 피드백 저장 ──
// Access가 붙은 경로에서만 전달되는 두 헤더를 모두 요구한다. 이메일 원문은
// 저장하지 않고, ACTOR_HASH_SALT와 결합한 SHA-256 지문만 D1에 기록한다.
function accessIdentity(req) {
  const email = (req.headers.get("Cf-Access-Authenticated-User-Email")
    || req.headers.get("CF-Access-Authenticated-User-Email") || "").trim().toLowerCase();
  const jwt = (req.headers.get("Cf-Access-Jwt-Assertion")
    || req.headers.get("CF-Access-Jwt-Assertion") || "").trim();
  return email && jwt ? email : "";
}
async function sha256Hex(value) {
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(value));
  return Array.from(new Uint8Array(digest), (n) => n.toString(16).padStart(2, "0")).join("");
}
function limitedString(value, max) {
  if (value == null || typeof value === "object") return null;
  const text = String(value ?? "").trim();
  return text ? text.slice(0, max) : null;
}
async function saveFeedback(req, env, origin) {
  if (!env || !env.FEEDBACK_DB) return jsonFor(origin, { error: "feedback storage not configured: FEEDBACK_DB" }, 503);
  const email = accessIdentity(req);
  if (!email) return jsonFor(origin, { error: "feedback authentication required" }, 401);
  if (!env.ACTOR_HASH_SALT) return jsonFor(origin, { error: "feedback storage not configured: ACTOR_HASH_SALT" }, 503);
  let payload, raw;
  try { raw = await req.text(); } catch (e) { return jsonFor(origin, { error: "invalid body" }, 400); }
  if (new TextEncoder().encode(raw).byteLength > MAX_BODY_BYTES) return jsonFor(origin, { error: "request body too large" }, 413);
  try { payload = JSON.parse(raw); } catch (e) { return jsonFor(origin, { error: "invalid JSON" }, 400); }
  if (!payload || typeof payload !== "object" || Array.isArray(payload)) return jsonFor(origin, { error: "feedback payload must be an object" }, 400);
  // 원문 카피는 어떤 형태로도 저장하지 않는다. 클라이언트는 textFingerprint만 보낸다.
  if (Object.prototype.hasOwnProperty.call(payload, "text")) return jsonFor(origin, { error: "raw text is not accepted" }, 400);
  const action = limitedString(payload.action, 32);
  const tool = limitedString(payload.tool, 80);
  if (!action || !FEEDBACK_ACTIONS.has(action)) return jsonFor(origin, { error: "invalid feedback action" }, 400);
  if (!tool) return jsonFor(origin, { error: "tool is required" }, 400);
  const textFingerprint = limitedString(payload.textFingerprint || payload.text_fingerprint, 64);
  if (textFingerprint && !SHA256_HEX.test(textFingerprint)) return jsonFor(origin, { error: "textFingerprint must be sha256 hex" }, 400);
  if (payload.metadata != null && (typeof payload.metadata !== "object" || Array.isArray(payload.metadata))) return jsonFor(origin, { error: "metadata must be an object" }, 400);
  const metadata = payload.metadata && typeof payload.metadata === "object" && !Array.isArray(payload.metadata) ? payload.metadata : {};
  if (Object.prototype.hasOwnProperty.call(metadata, "text")) return jsonFor(origin, { error: "raw text is not accepted" }, 400);
  const metadataJson = JSON.stringify(metadata);
  if (new TextEncoder().encode(metadataJson).byteLength > MAX_FEEDBACK_META_BYTES) return jsonFor(origin, { error: "metadata too large" }, 413);
  const editDistance = payload.editDistance == null || payload.edit_distance == null ? null : Number(payload.editDistance ?? payload.edit_distance);
  if (editDistance != null && (!Number.isFinite(editDistance) || editDistance < 0 || editDistance > 1e6)) return jsonFor(origin, { error: "invalid editDistance" }, 400);
  const occurredAt = limitedString(payload.occurredAt || payload.occurred_at, 40) || new Date().toISOString();
  if (Number.isNaN(Date.parse(occurredAt))) return jsonFor(origin, { error: "invalid occurredAt" }, 400);
  const actorHash = await sha256Hex(`${env.ACTOR_HASH_SALT}:${email}`);
  try {
    const result = await env.FEEDBACK_DB.prepare(`INSERT INTO copy_feedback
      (occurred_at, tool, product_key, recommendation_id, action, source_version,
       text_fingerprint, edit_distance, review_status, actor_hash, metadata_json)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`)
      .bind(
        occurredAt,
        tool,
        limitedString(payload.productKey || payload.product_key, 80),
        limitedString(payload.recommendationId || payload.recommendation_id, 160),
        action,
        limitedString(payload.sourceVersion || payload.source_version, 80),
        textFingerprint,
        editDistance,
        limitedString(payload.reviewStatus || payload.review_status, 80),
        actorHash,
        metadataJson,
      ).run();
    await bump(env, "feedback");
    return jsonFor(origin, { ok: true, id: result?.meta?.last_row_id ?? null });
  } catch (e) {
    return jsonFor(origin, { error: "feedback storage failed" }, 502);
  }
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

    // ④ 비용이 발생하는 API는 레이트리밋 저장소가 없으면 운영하지 않는다.
    if (!env || !env.USAGE) return jsonFor(origin, { error: "server not configured: USAGE rate limit binding" }, 503);
    const category = routeCategory(p);
    if (!(await rateOk(env, req, category))) return jsonFor(origin, { error: "rate limit exceeded" }, 429);

    try {
      // ── 비공개 검수 피드백 ──
      // Access + D1이 구성된 경우에만 저장한다. 원문 카피는 받지 않는다.
      if (p === "/v1/feedback") return saveFeedback(req, env, origin);

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
