#!/usr/bin/env node
/*
 * capture_brand.mjs — 타사 브랜드검색 모니터링 (PC + 모바일 자동 캡쳐)
 *
 * 경쟁사(삼성·KB·현대·DB) 다이렉트 + 상품명 검색결과를 매주 캡쳐 → serp/brand/
 *   파일: <경쟁사>-<상품>-<pc|mo>-<YYYY-MM-DD>.png · 인덱스: serp/brand/manifest.json
 *   브랜드검색(브랜드 전용 광고 영역)·파워링크 구성·소구 문구를 PC/모바일로 비교.
 *
 * - 네이버 검색결과(공개) → PII 없음, 캡쳐 커밋 가능.
 * - GitHub Actions(serp-capture.yml)에서 실행. 로컬:  node scripts/capture_brand.mjs
 * - 옵션:  ONLY=samsung,kb  ·  HEADFUL=1
 */
import { chromium } from "playwright";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const OUT = path.join(ROOT, "serp", "brand");
const today = new Date().toISOString().slice(0, 10);
const only = (process.env.ONLY || "").split(",").map(s => s.trim()).filter(Boolean);

// 경쟁사 다이렉트 브랜드 + 감시 상품
const BRANDS = [
  { key: "samsung", name: "삼성화재 다이렉트" },
  { key: "kb", name: "KB손해보험 다이렉트" },
  { key: "hyundai", name: "현대해상 다이렉트" },
  { key: "db", name: "DB손해보험 다이렉트" },
];
const PRODUCTS = ["운전자보험", "주택화재보험", "골프보험", "암보험", "해외여행보험"];

const naverUrl = q => "https://search.naver.com/search.naver?query=" + encodeURIComponent(q);
const safe = s => String(s).replace(/[^a-zA-Z0-9_-]/g, "");
const prodKey = p => ({ "운전자보험": "driver", "주택화재보험": "hrmf", "골프보험": "golf", "암보험": "cncr", "해외여행보험": "overseas" }[p] || safe(p));

fs.mkdirSync(OUT, { recursive: true });

const DEVICES = {
  pc: { viewport: { width: 1280, height: 1500 }, ua: "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36" },
  mo: { viewport: { width: 390, height: 1600 }, ua: "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1" },
};

async function main() {
  const proxy = process.env.HTTPS_PROXY || process.env.https_proxy;
  const opts = { headless: !process.env.HEADFUL, args: ["--no-sandbox", "--disable-dev-shm-usage"] };
  if (process.env.PW_CHROMIUM) opts.executablePath = process.env.PW_CHROMIUM;
  if (proxy) opts.proxy = { server: proxy };
  const browser = await chromium.launch(opts);

  const shots = [];
  for (const b of BRANDS) {
    if (only.length && !only.includes(b.key)) continue;
    for (const prod of PRODUCTS) {
      const query = `${b.name} ${prod}`;
      const pk = prodKey(prod);
      for (const [dev, cfg] of Object.entries(DEVICES)) {
        const ctx = await browser.newContext({ viewport: cfg.viewport, deviceScaleFactor: dev === "mo" ? 2 : 1.5, locale: "ko-KR", userAgent: cfg.ua });
        const page = await ctx.newPage();
        const file = `${b.key}-${pk}-${dev}-${today}.png`;
        try {
          await page.goto(naverUrl(query), { waitUntil: "domcontentloaded", timeout: 45000 });
          await page.waitForTimeout(1800);
          await page.screenshot({ path: path.join(OUT, file), clip: { x: 0, y: 0, width: cfg.viewport.width, height: cfg.viewport.height } });
          shots.push({ co: b.key, coName: b.name, prod, prodKey: pk, dev, query, file, date: today });
          console.log(`✓ ${b.key}/${pk}/${dev} "${query}"`);
        } catch (e) {
          console.error(`✗ ${b.key}/${pk}/${dev} — ${e.message}`);
        }
        await ctx.close();
      }
    }
  }
  await browser.close();

  // manifest 병합 (경쟁사>상품>디바이스 별 dated 히스토리)
  const mfPath = path.join(OUT, "manifest.json");
  let mf = { source: "playwright-naver-brand", asof: today, brands: {} };
  try { mf = JSON.parse(fs.readFileSync(mfPath, "utf-8")); } catch {}
  mf.asof = today; mf.brands = mf.brands || {};
  for (const s of shots) {
    const co = (mf.brands[s.co] = mf.brands[s.co] || { name: s.coName, products: {} });
    const pr = (co.products[s.prodKey] = co.products[s.prodKey] || { name: s.prod, captures: [] });
    const caps = pr.captures.filter(c => c.file !== s.file);
    caps.push({ file: s.file, date: s.date, dev: s.dev });
    caps.sort((a, b) => (a.date + a.dev).localeCompare(b.date + b.dev));
    pr.captures = caps.slice(-48); // 상품×디바이스 최근 히스토리 보관
  }
  fs.writeFileSync(mfPath, JSON.stringify(mf, null, 1));
  console.log(`\nbrand manifest: serp/brand/manifest.json · 이번 실행 ${shots.length}컷`);
  if (shots.length === 0) process.exitCode = 1;
}
main().catch(e => { console.error(e); process.exit(1); });
