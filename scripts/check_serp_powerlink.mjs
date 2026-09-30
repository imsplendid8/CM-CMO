#!/usr/bin/env node
/*
 * check_serp_powerlink.mjs — 파워링크 추출기(serp_powerlink_extract.mjs) 회귀 검사.
 * 가상 픽스처(tests/fixtures/naver_powerlink*.html)에서 광고 1건씩 구조화되는지 확인한다.
 * serp-capture.yml이 실제 캡쳐 전에 실행(Chromium 필요). 로컬: PW_CHROMIUM=<경로> node scripts/check_serp_powerlink.mjs
 */
import { chromium } from "playwright";
import assert from "node:assert/strict";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { extractPowerLinks } from "./serp_powerlink_extract.mjs";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const fixture = name => pathToFileURL(path.join(ROOT, "tests/fixtures", name)).href;
const opts = { args: ["--no-sandbox"] };
if (process.env.PW_CHROMIUM) opts.executablePath = process.env.PW_CHROMIUM;

const browser = await chromium.launch(opts);
try {
  const page = await browser.newPage();

  await page.goto(fixture("naver_powerlink.html"));
  const ads = await extractPowerLinks(page);
  assert.equal(ads.length, 3, "광고 3건(자사 포함)이 각각 분리돼야 함");
  assert.deepEqual(ads.map(a => a.brand), ["가상손해보험다이렉트", "샘플화재다이렉트", "한화손보다이렉트"]);
  assert.equal(ads[0].domain, "direct.example-ins.co.kr");
  assert.equal(ads[0].title, "가상다이렉트 공식 운전자보험 · 450만의 선택");
  assert.match(ads[0].desc, /^형사합의금·변호사선임비용 보장/);
  assert.deepEqual(ads[0].extensions, ["변호사선임비용 심급별 보장", "24시간가입", "보험료계산"]);
  assert.ok(!ads.some(a => /관련 광고|이 광고가 표시된 이유/.test(a.title + a.desc)), "영역 머리글이 광고로 잡히면 안 됨");

  await page.goto(fixture("naver_powerlink_inline.html"));
  const raw = await extractPowerLinks(page);
  assert.equal(raw.length, 1);
  assert.equal(raw[0].raw, true, "도메인이 붙은 마크업은 원문 줄 폴백");
  assert.ok(raw[0].lines.includes("가상생명 · virtual-life.co.kr 광고"));

  console.log(`✔ 파워링크 추출기: 구조화 ${ads.length}건 · 원문 폴백 ${raw[0].lines.length}줄`);
} finally {
  await browser.close();
}
