#!/usr/bin/env node
/*
 * capture_docimg.mjs — 발표 문서 보강용 스크린샷(http 렌더)
 *   브랜드검색 갤러리 등 fetch 기반 화면은 file:// 로는 안 뜨므로 로컬 http 서버 경유.
 *   사용: (python3 -m http.server 8123 &) 후  node scripts/capture_docimg.mjs
 */
import { chromium } from "playwright";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const OUT = path.join(ROOT, "docs", "img");
const BASE = process.env.BASE || "http://localhost:8123";
const EXE = process.env.PW_CHROMIUM || "/opt/pw-browsers/chromium-1194/chrome-linux/chrome";
fs.mkdirSync(OUT, { recursive: true });

async function main() {
  const browser = await chromium.launch({ headless: true, executablePath: EXE, args: ["--no-sandbox", "--disable-dev-shm-usage"] });

  const shot = async (url, out, { w = 1280, h = 1400, wait = 1400, click } = {}) => {
    const ctx = await browser.newContext({ viewport: { width: w, height: h }, deviceScaleFactor: 1.5, locale: "ko-KR" });
    const page = await ctx.newPage();
    try {
      await page.goto(url, { waitUntil: "networkidle", timeout: 15000 }).catch(() => {});
      await page.waitForTimeout(wait);
      if (click) { await page.click(click, { timeout: 5000 }).catch(() => {}); await page.waitForTimeout(1000); }
      await page.screenshot({ path: path.join(OUT, out), clip: { x: 0, y: 0, width: w, height: h } });
      console.log(`✓ ${out}`);
    } catch (e) { console.error(`✗ ${out} — ${e.message}`); }
    await ctx.close();
  };

  await shot(`${BASE}/index.html`, "hub.png", { w: 1280, h: 900, wait: 1200 });
  await shot(`${BASE}/serp-tool.html`, "skill-serp-brand.png", { w: 1280, h: 1200, wait: 1600, click: '[data-key="__brand"]' });
  await shot(`${BASE}/keyword-tool.html`, "skill-keyword.png", { w: 1280, h: 1200, wait: 1400 });

  await browser.close();
}
main().catch(e => { console.error(e); process.exit(1); });
