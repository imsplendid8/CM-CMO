#!/usr/bin/env node
/*
 * capture_serp.mjs — 상품별 네이버 PC 검색결과(SERP) 자동 스크린샷 아카이브
 *
 * data/products.json 의 serpKw 로 네이버 통합검색(PC)을 열어 상단 화면을 캡쳐하고
 * serp/<key>-<YYYY-MM-DD>.png 로 저장 + serp/manifest.json 갱신.
 *
 *  - SERP 는 공개 검색결과 → PII 없음 → 캡쳐본 커밋 가능(원본 캡쳐 금지 원칙 위배 아님)
 *  - 이 환경(샌드박스)은 외부망이 막혀 있어 동작 안 함 → GitHub Actions(serp-capture.yml)
 *    또는 로컬에서 실행:  node scripts/capture_serp.mjs
 *  - 옵션:  ONLY=hrmf,golf  (일부 상품만)  ·  HEADFUL=1 (창 표시, 로컬 디버그)
 */
import { chromium } from "playwright";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const OUT = path.join(ROOT, "serp");
const products = JSON.parse(fs.readFileSync(path.join(ROOT, "data/products.json"), "utf-8"));
const list = Array.isArray(products) ? products : (products.products || []);
const only = (process.env.ONLY || "").split(",").map(s => s.trim()).filter(Boolean);
const today = new Date().toISOString().slice(0, 10);

const naverUrl = kw => "https://search.naver.com/search.naver?query=" + encodeURIComponent(kw);
const safe = s => String(s).replace(/[^a-zA-Z0-9_-]/g, "");

fs.mkdirSync(OUT, { recursive: true });

async function main() {
  const proxy = process.env.HTTPS_PROXY || process.env.https_proxy;
  const opts = { headless: !process.env.HEADFUL, args: ["--no-sandbox", "--disable-dev-shm-usage"] };
  if (process.env.PW_CHROMIUM) opts.executablePath = process.env.PW_CHROMIUM;
  if (proxy) opts.proxy = { server: proxy };

  const browser = await chromium.launch(opts);
  const ctx = await browser.newContext({
    viewport: { width: 1280, height: 1600 },
    deviceScaleFactor: 1.5,
    locale: "ko-KR",
    userAgent: "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
  });

  const results = [];
  for (const p of list) {
    const kw = p.serpKw || p.name;
    if (!kw) continue;
    if (only.length && !only.includes(p.key)) continue;
    const file = `${safe(p.key)}-${today}.png`;
    const page = await ctx.newPage();
    try {
      const r = await page.goto(naverUrl(kw), { waitUntil: "domcontentloaded", timeout: 45000 });
      await page.waitForTimeout(1800);
      // 상단 통합검색 영역만 (파워링크·브랜드검색·플레이스 노출 구간)
      await page.screenshot({ path: path.join(OUT, file), clip: { x: 0, y: 0, width: 1280, height: 1600 } });
      results.push({ key: p.key, name: p.name, kw, file, date: today, status: r ? r.status() : null });
      console.log(`✓ ${p.key.padEnd(10)} "${kw}" → serp/${file}`);
    } catch (e) {
      console.error(`✗ ${p.key} "${kw}" — ${e.message}`);
      results.push({ key: p.key, name: p.name, kw, file: null, date: today, error: e.message });
    } finally {
      await page.close();
    }
  }
  await browser.close();

  // manifest 병합 — 상품별 dated 캡쳐 히스토리 누적(전/후 diff 용)
  const mfPath = path.join(OUT, "manifest.json");
  let prev = { shots: {} };
  try { prev = JSON.parse(fs.readFileSync(mfPath, "utf-8")); } catch {}
  const shots = prev.shots || {};
  for (const r of results) {
    if (!r.file) continue;
    shots[r.key] = shots[r.key] || { name: r.name, kw: r.kw, captures: [] };
    shots[r.key].name = r.name; shots[r.key].kw = r.kw;
    const caps = shots[r.key].captures.filter(c => c.file !== r.file); // 같은 날 재실행 시 덮어쓰기
    caps.push({ file: r.file, date: r.date });
    caps.sort((a, b) => a.date.localeCompare(b.date));
    shots[r.key].captures = caps.slice(-24); // 상품별 최근 24회(약 반년) 보관
  }
  const ok = results.filter(r => r.file).length;
  fs.writeFileSync(mfPath, JSON.stringify({ source: "playwright-naver", asof: today, updated: ok, shots }, null, 2));
  console.log(`\nmanifest: serp/manifest.json · 이번 실행 ${ok}/${results.length}건 캡쳐`);
  if (ok === 0) process.exitCode = 1;
}

main().catch(e => { console.error(e); process.exit(1); });
