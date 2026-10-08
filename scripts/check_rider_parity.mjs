#!/usr/bin/env node
/*
 * check_rider_parity.mjs — (특약) 표기 규칙의 세 구현이 같은 답을 내는지 검사.
 *   ① scripts/coverage_terms.py (SA 에이전트·이벤트 추천) — 기준 예문 tests/fixtures/rider_cases.json 생성 원본
 *   ② adcopy-tool.html riderScan/markRiders/riderMissing (SA 도구, bare=true)
 *   ③ scripts/check_power_content_articles.mjs missingRider (파워콘텐츠 검사, bare=false)
 * 한 곳만 고치면 SA와 파워콘텐츠 판정이 갈라지므로 CI에서 막는다.
 */
import fs from "node:fs";
import vm from "node:vm";

const read = (rel) => fs.readFileSync(new URL(`../${rel}`, import.meta.url), "utf8");
const coverage = read("data/adcopy/coverage-terms.json");
const { cases } = JSON.parse(read("tests/fixtures/rider_cases.json"));
const fnSource = (src, name) => {
  const start = src.indexOf(`function ${name}(`);
  if (start < 0) throw new Error(`${name} 함수를 찾지 못함`);
  let depth = 0;
  for (let i = src.indexOf("{", start); i < src.length; i++) {
    if (src[i] === "{") depth++;
    else if (src[i] === "}" && --depth === 0) return src.slice(start, i + 1);
  }
  throw new Error(`${name} 함수 끝을 찾지 못함`);
};

const html = read("adcopy-tool.html");
const sa = {};
vm.createContext(sa);
vm.runInContext(`var COVERAGE=${coverage};${["riderScan", "riderMissing", "markRiders"].map((n) => fnSource(html, n)).join("\n")};globalThis.api={riderMissing,markRiders};`, sa);

const pc = {};
vm.createContext(pc);
vm.runInContext(`var coverage=${coverage};${fnSource(read("scripts/check_power_content_articles.mjs"), "missingRider")};globalThis.api={missingRider};`, pc);

const errors = [];
const same = (a, b) => JSON.stringify([...a].sort()) === JSON.stringify([...b].sort());
for (const c of cases) {
  const tag = `[${c.key}${c.bare ? "" : " · 파워콘텐츠"}] ${c.text}`;
  if (c.bare) {
    const marked = sa.api.markRiders(c.text, c.key);
    const missing = [...sa.api.riderMissing(c.text, c.key)];
    if (marked !== c.marked) errors.push(`${tag}\n   SA 도구 표기 '${marked}' ≠ 기준 '${c.marked}'`);
    if (!same(missing, c.missing)) errors.push(`${tag}\n   SA 도구 누락 ${JSON.stringify(missing)} ≠ 기준 ${JSON.stringify(c.missing)}`);
  } else {
    const missing = [...pc.api.missingRider(c.text, c.key)];
    if (!same(missing, c.missing)) errors.push(`${tag}\n   파워콘텐츠 검사 누락 ${JSON.stringify(missing)} ≠ 기준 ${JSON.stringify(c.missing)}`);
    const after = [...pc.api.missingRider(c.marked, c.key)];
    if (after.length) errors.push(`${tag}\n   기준 표기 '${c.marked}'를 파워콘텐츠 검사가 다시 누락으로 봄: ${after}`);
  }
}
if (errors.length) {
  console.error(`✗ (특약) 규칙 구현 불일치 ${errors.length}건\n${errors.join("\n")}`);
  process.exit(1);
}
console.log(`✔ (특약) 규칙 3개 구현 일치 — 기준 예문 ${cases.length}건`);
