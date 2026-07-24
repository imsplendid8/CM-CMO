#!/usr/bin/env node
/*
 * capture_skilldoc.mjs — 발표 문서용 스킬 적용 예시 스크린샷(로컬 렌더)
 *   클로드 스킬이 데이터/포맷으로 반영된 실제 툴 화면을 캡쳐 → docs/img/
 *   - terms-tool.html : insurance-terms 스킬 산출물(약관 용어→소비자 표현)
 *   - news-tool.html  : cm-news-analysis 스킬 포맷(요약→상세·이슈/영향/참고)
 * 외부망 불필요(정적 렌더). 로컬:  node scripts/capture_skilldoc.mjs
 */
import { chromium } from "playwright";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const OUT = path.join(ROOT, "docs", "img");
fs.mkdirSync(OUT, { recursive: true });

const SHOTS = [
  { file: "terms-tool.html", out: "skill-terms.png", w: 1280, h: 1400, wait: 1200 },
  { file: "news-tool.html",  out: "skill-news.png",  w: 1280, h: 1500, wait: 1400 },
];

async function main() {
  const exe = process.env.PW_CHROMIUM || "/opt/pw-browsers/chromium-1194/chrome-linux/chrome";
  const browser = await chromium.launch({ headless: true, executablePath: exe, args: ["--no-sandbox", "--disable-dev-shm-usage"] });
  for (const s of SHOTS) {
    const ctx = await browser.newContext({ viewport: { width: s.w, height: s.h }, deviceScaleFactor: 1.5, locale: "ko-KR" });
    const page = await ctx.newPage();
    const url = "file://" + path.join(ROOT, s.file);
    try {
      await page.goto(url, { waitUntil: "networkidle", timeout: 15000 }).catch(() => {});
      await page.waitForTimeout(s.wait);
      await page.screenshot({ path: path.join(OUT, s.out), clip: { x: 0, y: 0, width: s.w, height: s.h } });
      console.log(`✓ ${s.out}`);
    } catch (e) {
      console.error(`✗ ${s.file} — ${e.message}`);
    }
    await ctx.close();
  }
  await browser.close();
}
main().catch(e => { console.error(e); process.exit(1); });
