#!/usr/bin/env node
/*
 * 네이버 통합검색 입력창에 실제로 노출되는 자동완성어를 월 1회 수집한다.
 * 비공개 API·로그인·사내망을 사용하지 않고 공개 화면의 표시 텍스트만 읽는다.
 */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { buildDataset } from "./keyword_autocomplete_core.mjs";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const OUTPUT = path.join(ROOT, "data", "keyword-autocomplete.json");
async function extractSuggestions(page, seed) {
  const input = page.locator('input[name="query"], #query, input[title*="검색"]').first();
  await input.waitFor({ state: "visible", timeout: 15000 });
  await input.click();
  await input.press("ControlOrMeta+A");
  await input.pressSequentially(seed, { delay: 65 });
  await page.waitForTimeout(1200);
  return page.evaluate(rawSeed => {
    const normal = value => String(value || "").replace(/\s+/g, "").toLowerCase();
    const wanted = normal(rawSeed);
    const inputEl = document.querySelector('input[name="query"], #query, input[title*="검색"]');
    const inputRect = inputEl?.getBoundingClientRect();
    const nodes = document.querySelectorAll('[role="option"], [role="listbox"] li, .api_atcmp_wrap li, .autocomplete li, li');
    const rows = [];
    for (const node of nodes) {
      const rect = node.getBoundingClientRect();
      const style = getComputedStyle(node);
      if (!rect.width || !rect.height || style.display === "none" || style.visibility === "hidden") continue;
      if (inputRect && (rect.top < inputRect.bottom - 8 || rect.top > inputRect.bottom + 720)) continue;
      let text = (node.innerText || "").replace(/\s+/g, " ").trim();
      text = text.split(/\n|신고|삭제/)[0].trim().replace(/\s+추가$/u, "").trim();
      const candidate = normal(text);
      if (!text || text.length > 60 || candidate === wanted || !candidate.startsWith(wanted)) continue;
      rows.push({ keyword: text, top: rect.top });
    }
    const unique = new Map();
    rows.sort((a, b) => a.top - b.top).forEach(row => {
      const key = normal(row.keyword);
      if (!unique.has(key)) unique.set(key, row.keyword);
    });
    return [...unique.values()].slice(0, 20);
  }, seed);
}

async function main() {
  const master = JSON.parse(fs.readFileSync(path.join(ROOT, "data", "products.json"), "utf-8"));
  const products = master.products || master;
  let previous = {};
  try { previous = JSON.parse(fs.readFileSync(OUTPUT, "utf-8")); } catch {}
  const asof = new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Seoul" }).format(new Date());
  if (process.argv.includes("--reclassify")) {
    const captured = Object.fromEntries(products.map(product => [
      product.key,
      ((previous.products || {})[product.key]?.suggestions || []).map(({ keyword, seed, rank }) => ({ keyword, seed, rank })),
    ]));
    const data = buildDataset({ previous, products, captured, asof: previous.asof || asof });
    fs.writeFileSync(OUTPUT, JSON.stringify(data, null, 2) + "\n");
    console.log(`재분류 완료: ${products.length}개 상품 · ${data.asof}`);
    return;
  }
  const { chromium } = await import("playwright");
  const browser = await chromium.launch({ headless: true, args: ["--no-sandbox", "--disable-dev-shm-usage"] });
  const context = await browser.newContext({
    viewport: { width: 1280, height: 1000 }, locale: "ko-KR",
    userAgent: "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
  });
  const page = await context.newPage();
  const captured = {};
  try {
    await page.goto("https://search.naver.com/search.naver?query=%EB%B3%B4%ED%97%98", { waitUntil: "domcontentloaded", timeout: 45000 });
    for (const product of products) {
      const rows = [];
      const seeds = [...new Set([product.serpKw, ...(product.core || [])].filter(Boolean))].slice(0, 3);
      for (const seed of seeds) {
        try {
          const suggestions = await extractSuggestions(page, seed);
          suggestions.forEach((keyword, index) => rows.push({ keyword, seed, rank: index + 1 }));
          console.log(`✓ ${product.key.padEnd(12)} ${seed} · ${suggestions.length}개`);
        } catch (error) {
          console.warn(`⚠ ${product.key} ${seed} · ${error.message}`);
        }
        await page.waitForTimeout(350);
      }
      captured[product.key] = rows;
    }
  } finally {
    await browser.close();
  }
  const total = Object.values(captured).reduce((sum, rows) => sum + rows.length, 0);
  if (!total) throw new Error("네이버 자동완성 표시어를 한 건도 수집하지 못해 기존 정상본을 유지합니다.");
  const data = buildDataset({ previous, products, captured, asof });
  fs.writeFileSync(OUTPUT, JSON.stringify(data, null, 2) + "\n");
  console.log(`완료: ${products.length}개 상품 · 중복 전 ${total}건 · ${data.month} 스냅샷`);
}

if (process.argv[1] && import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href) {
  main().catch(error => { console.error(error); process.exit(1); });
}
