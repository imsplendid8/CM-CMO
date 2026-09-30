#!/usr/bin/env node
/*
 * check_power_content_articles.mjs — 파워콘텐츠 원고 재료(data/adcopy/power-content-articles.json) 품질 검사.
 * 공통 틀이 분량을 '확인하세요·약관 기준' 같은 안내 문장으로 채우던 문제(2026-09)를 다시 만들지 않도록,
 * 규격뿐 아니라 안내형 표현·보장 사실 문장 수·금액 표현·상품별 사용 금지 표현·보험광고 사전검수를 함께 본다.
 */
import fs from "node:fs";
import vm from "node:vm";

const read = rel => fs.readFileSync(new URL(`../${rel}`, import.meta.url), "utf8");
const data = JSON.parse(read("data/adcopy/power-content-articles.json"));
const context = JSON.parse(read("data/adcopy/material-source-context.json"));
const sandbox = {};
vm.createContext(sandbox);
vm.runInContext(read("shared/insurance-ad-review.js"), sandbox);
const review = sandbox.ModooInsuranceAdReview;

const clen = s => [...String(s ?? "").trim()].length;
// 안내형(독자에게 할 일을 떠넘기는) 표현 — 원고 본문·FAQ·CTA 어디에도 쓰지 않는다
const GUIDANCE = /확인하세요|확인해 보세요|확인합니다|살펴보세요|살펴봅니다|정리했습니다|정리합니다|정리해요|대조|상품설명서|비교 순서|적어 보세요|읽어 보세요|체크리스트/;
// 보장 사실을 전달하는 문장(무엇을 보상·보장·대비하는지)
const BENEFIT = /보상해요|보장해요|보상받(?:을 수 있어요|아요)|대비(?:할 수 있어요|해요)|준비(?:할 수 있어요|해요)|덜어 줘요|덜 수 있어요|(?:보상|보장)하는 특약/g;
// 승인 전 수치 표현(심급 1심·2심은 허용)
const AMOUNT = /\d[\d,.]*\s*(만\s*원|원|%|퍼센트|회|배)(?![가-힣]*심)/;
const errors = [];
const fail = (where, msg) => errors.push(`${where}: ${msg}`);
let count = 0;

for (const [key, articles] of Object.entries(data.articles || {})) {
  const suppressed = context.products?.[key]?.review_draft?.suppressed_claims || [];
  const topics = new Set();
  for (const a of articles) {
    count++;
    const where = `${key} · ${a.title}`;
    if (topics.has(a.target_query)) fail(where, "같은 상품에 중복 target_query");
    topics.add(a.target_query);
    if (clen(a.title) < 7 || clen(a.title) > 28) fail(where, `제목 ${clen(a.title)}자(7~28)`);
    if (clen(a.intro) < 80 || clen(a.intro) > 110) fail(where, `도입·광고 설명 ${clen(a.intro)}자(80~110)`);
    if (!`${a.title}${a.intro}`.replace(/\s/g, "").includes(a.target_query.replace(/\s/g, ""))) fail(where, "대표 키워드가 제목·도입에 없음");
    if ((a.sections || []).length !== 5) fail(where, `본문 섹션 ${(a.sections || []).length}개(5)`);
    const body = [a.intro, ...(a.sections || []).map(s => s.body)].join("\n\n");
    if (clen(body) < 1500) fail(where, `발행 본문 ${clen(body)}자(1,500 이상)`);
    if ((a.faq || []).length !== 4) fail(where, `FAQ ${(a.faq || []).length}개(4)`);
    if (new Set((a.faq || []).map(f => f.a)).size !== (a.faq || []).length) fail(where, "FAQ 답변이 서로 같음");
    const all = [a.title, body, a.cta, a.banner?.headline, a.banner?.subline, ...(a.faq || []).flatMap(f => [f.q, f.a])].join("\n");
    const g = all.match(GUIDANCE);
    if (g) fail(where, `안내형 표현 '${g[0]}'`);
    const terms = (all.match(/약관/g) || []).length;
    if (terms > 5) fail(where, `'약관' ${terms}회 — 제외 사유 안내 1~2회면 충분`);
    const benefit = (body.match(BENEFIT) || []).length;
    if (benefit < 5) fail(where, `보장 사실 문장 ${benefit}개(5개 이상)`);
    const amt = all.match(AMOUNT);
    if (amt) fail(where, `승인 전 수치 표현 '${amt[0]}'`);
    for (const word of suppressed) if (all.includes(word)) fail(where, `상품 사용 금지 표현 '${word}'`);
    for (const [field, text] of [["제목", a.title], ["도입", a.intro], ...(a.sections || []).map((s, i) => [`본문${i + 1}`, `${s.heading} ${s.body}`]), ...(a.faq || []).map((f, i) => [`FAQ${i + 1}`, `${f.q} ${f.a}`]), ["CTA", a.cta], ["배너", `${a.banner?.headline} ${a.banner?.subline}`]]) {
      const r = review.review(text, { channel: "power_content" });
      if (r.generationBlocking) fail(where, `${field} 사전검수 차단: ${r.findings.filter(f => f.generationBlocking).map(f => f.ruleId).join(",")}`);
    }
    if (a.review_status !== "사람 심의 필요") fail(where, "review_status는 '사람 심의 필요'");
  }
}
if (errors.length) {
  console.error(errors.map(e => `✗ ${e}`).join("\n"));
  process.exit(1);
}
console.log(`✔ 파워콘텐츠 원고 재료 ${count}편: 규격·안내형 표현 0·보장 사실 문장·금지 표현·사전검수 통과`);
