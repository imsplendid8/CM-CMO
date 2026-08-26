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
const RETRIES = Number(process.env.CAPTURE_RETRIES || 1); // 실패(빈 화면/오류) 시 추가 재캡쳐 횟수

async function extractDomCandidates(page) {
  return page.evaluate(() => {
    const root=document.querySelector("#main_pack")||document.querySelector("#ct")||document.body;
    const seen=new Set(),rows=[];
    for(const a of root.querySelectorAll("a[href]")){
      let block=a;
      for(let depth=0;depth<6&&block?.parentElement;depth++){
        const parent=block.parentElement,text=(parent.innerText||"").replace(/\s+/g," ").trim();
        if(text.length>700)break;
        block=parent;
        if(text.length>=40&&/(광고|파워링크|adcr|sponsored)/i.test(`${text} ${a.href} ${block.className||""}`))break;
      }
      const text=(block?.innerText||a.innerText||"").replace(/\s+/g," ").trim();
      if(text.length<20||text.length>500||seen.has(text))continue;
      const adSignal=/(광고|파워링크|adcr|sponsored)/i.test(`${text} ${a.href} ${block?.className||""}`);
      if(!adSignal)continue;
      const linkTexts=[...block.querySelectorAll("a")].map(x=>(x.innerText||"").replace(/\s+/g," ").trim()).filter(x=>x.length>=2&&x.length<=60).slice(0,12);
      const features=[];
      [["insurance_quote",/보험료|견적|계산/],["easy_join",/간편|바로|즉시|24\s*시간|온라인|다이렉트/],["coverage",/보장|특약|담보|진단비|치료비|합의금|벌금/],["promotion",/이벤트|증정|할인|페이|상품권|쿠폰/],["trust",/공식|전문가|상담|선택|1위/]].forEach(([name,pattern])=>{if(pattern.test(text))features.push(name)});
      seen.add(text);rows.push({text,linkTexts,features,hasImage:Boolean(block.querySelector("img")),confidence:"needs_review"});
      if(rows.length===10)break;
    }
    return rows;
  });
}

fs.mkdirSync(OUT, { recursive: true });

// 렌더 성공 판정 — 검색결과 본문이 실제로 채워졌는지(스켈레톤/빈 화면 감지)
async function renderedOk(page) {
  try {
    return await page.evaluate(() => {
      const mp = document.querySelector("#main_pack") || document.querySelector("#ct") || document.body;
      if (!mp) return false;
      const txt = (mp.innerText || "").replace(/\s+/g, "");
      return txt.length > 300; // 실제 결과가 채워지면 텍스트가 충분히 쌓임
    });
  } catch { return false; }
}

// 네이버 SERP 열고 캡쳐 — 빈 화면/오류면 재로드해 한 번 더 시도. 마지막 시도는 무조건 저장(캡쳐 유실 방지).
async function gotoAndShoot(page, url, shotOpts, label) {
  let r = null, lastErr = null;
  for (let attempt = 0; attempt <= RETRIES; attempt++) {
    const last = attempt === RETRIES;
    try {
      r = await page.goto(url, { waitUntil: "domcontentloaded", timeout: 45000 });
      await page.waitForTimeout(1800 + attempt * 1000); // 재시도일수록 조금 더 대기
      const ok = await renderedOk(page);
      if (ok || last) {
        await page.screenshot(shotOpts);
        return { status: r ? r.status() : null, attempt, rendered: ok };
      }
      lastErr = new Error("빈 화면/스켈레톤 — 렌더 미완");
    } catch (e) {
      lastErr = e;
      if (last) throw e;
    }
    console.warn(`  ↻ ${label} 재캡쳐 ${attempt + 1}/${RETRIES} (${lastErr.message})`);
    await page.waitForTimeout(1500);
  }
  throw lastErr;
}

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
      // 상단 통합검색 영역만 (파워링크·브랜드검색·플레이스 노출 구간) · 빈 화면이면 재캡쳐
      const res = await gotoAndShoot(
        page, naverUrl(kw),
        { path: path.join(OUT, file), clip: { x: 0, y: 0, width: 1280, height: 1600 } },
        p.key,
      );
      const domCandidates=await extractDomCandidates(page);
      results.push({ key: p.key, name: p.name, kw, file, date: today, status: res.status, domCandidates });
      console.log(`✓ ${p.key.padEnd(10)} "${kw}" → serp/${file}${res.attempt ? ` (재캡쳐 ${res.attempt}회)` : ""}${res.rendered ? "" : " ⚠ 렌더 미완"}`);
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
  const domPath=path.join(OUT,"dom_observations.json");
  let dom={source:"playwright-dom-review-queue",asof:today,observations:[]};
  try{dom=JSON.parse(fs.readFileSync(domPath,"utf-8"));}catch{}
  dom.asof=today;dom.observations=(dom.observations||[]).filter(x=>x.date!==today);
  for(const r of results)for(const c of (r.domCandidates||[]))dom.observations.push({product:r.key,keyword:r.kw,date:r.date,capture:r.file,...c});
  dom.observations=dom.observations.slice(-500);
  fs.writeFileSync(domPath,JSON.stringify(dom,null,2));
  console.log(`\nmanifest: serp/manifest.json · 이번 실행 ${ok}/${results.length}건 캡쳐`);
  if (ok === 0) process.exitCode = 1;
}

main().catch(e => { console.error(e); process.exit(1); });
