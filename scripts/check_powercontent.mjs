import fs from "node:fs";
import vm from "node:vm";

const root = new URL("../", import.meta.url);
const html = fs.readFileSync(new URL("powercontent-tool.html", root), "utf8");
const materialSpecs = fs.readFileSync(new URL("shared/naver-material-specs.js", root), "utf8");
const insuranceAdReview = fs.readFileSync(new URL("shared/insurance-ad-review.js", root), "utf8");
const scripts = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map((match) => match[1]);
const appScript = scripts.find((source) => source.includes("function contentBriefFor"));
if (!appScript) throw new Error("powercontent-tool.html에서 콘텐츠 브리프 생성 로직을 찾지 못했습니다.");

const pureSection = appScript.split("function renderNav")[0];
const context = {
  console,
  window: {
    ModooPlanning: { getMonth: () => 8, nextMonth: (month) => month % 12 + 1 },
    ModooHumanizeKo: { light: (value) => String(value) },
  },
};
vm.createContext(context);
vm.runInContext(materialSpecs, context, { filename: "shared/naver-material-specs.js" });
vm.runInContext(insuranceAdReview, context, { filename: "shared/insurance-ad-review.js" });
vm.runInContext(
  `${pureSection}
  ;globalThis.__POWER_CHECK__={
    PRODUCTS,titleCandidates,candidateCannibalization,sameCurrentTopic,reviewPowerMaterial,volumeRows,inScope,clen,keywordPlan,introFor,
    contentBriefFor,contentKeywordSet,visualPlanFor,
    setData:(volume,seasonal,titles,serp,history)=>{DATA={volume,seasonal,titles,serp,history};}
  };`,
  context,
  { filename: "powercontent-tool.html" },
);

const check = context.__POWER_CHECK__;
const readJson = (path) => JSON.parse(fs.readFileSync(new URL(path, root), "utf8"));
const volumeData = readJson("data/volume.json");
const seasonalData = readJson("data/seasonal.json");
const titleData = readJson("data/adcopy/powercontent-title-opportunities.json");
const serpData = readJson("data/adcopy/serp-candidates.json");
const historyData = readJson("data/adcopy/powercontent-history.json");
check.setData(
  volumeData,
  seasonalData,
  titleData,
  serpData,
  historyData,
);

if (check.PRODUCTS.length !== 12) throw new Error(`상품 수 불일치: ${check.PRODUCTS.length}개`);
const forbidden = /자동차\s*보험|공개\s*관측|한화생명|고객센터|라이나|영업배상책임|재난배상책임/;
const forbiddenKeyword = /삼성|DB|디비|동부|현대|KB|메리츠|라이나|AXA|악사|흥국|롯데|신한/;

for (const product of check.PRODUCTS) {
  const candidates = check.titleCandidates(product);
  if (candidates.length !== 3) throw new Error(`${product.name}: 콘텐츠 소재 ${candidates.length}개 (기대 3개)`);
  if (candidates.some((candidate) => check.candidateCannibalization(product, candidate))) {
    throw new Error(`${product.name}: 과거 제안과 카니벌라이제이션 발생`);
  }
  if (candidates.some((candidate, index) => candidates.slice(0, index).some((old) => check.sameCurrentTopic(old, candidate)))) {
    throw new Error(`${product.name}: 현재 콘텐츠 3안 사이 주제 중복`);
  }
  for (const candidate of candidates) {
    const titleLength = check.clen(candidate.title);
    if (titleLength < 7 || titleLength > 28) throw new Error(`${product.name}: 제목 ${titleLength}자`);
    if (!check.inScope(product, candidate.target_query || candidate.title)) {
      throw new Error(`${product.name}: 범위 밖 검색어 '${candidate.target_query}'`);
    }
    if (forbidden.test(`${candidate.title} ${candidate.target_query || ""}`)) {
      throw new Error(`${product.name}: 제외 표현 포함 '${candidate.title}'`);
    }
    const brief = check.contentBriefFor(product, candidate);
    const introLength = check.clen(brief.intro);
    if (introLength < 80 || introLength > 110) throw new Error(`${product.name}: 도입부·광고 설명 ${introLength}자`);
    if (brief.draft.length !== 5) throw new Error(`${product.name}: 본문 초안 ${brief.draft.length}개 섹션`);
    if (brief.faq.length !== 4) throw new Error(`${product.name}: FAQ ${brief.faq.length}개`);
    if (brief.article.bodyCharCount < 1500) throw new Error(`${product.name}: 발행형 본문 ${brief.article.bodyCharCount}자`);
    if (brief.article.tags.length < 2) throw new Error(`${product.name}: 발행 태그 부족`);
    if (brief.visuals.mid.length !== 3) throw new Error(`${product.name}: 중간 이미지 ${brief.visuals.mid.length}장`);
    const visualAssets = [brief.visuals.hero, ...brief.visuals.mid].map((row) => row.asset);
    if (new Set(visualAssets).size !== 4) throw new Error(`${product.name}: 대표·중간 이미지 원본 중복`);
    if (visualAssets.some((asset) => !fs.existsSync(new URL(asset, root)))) {
      throw new Error(`${product.name}: 이미지 파일 누락`);
    }
    if (!brief.visuals.rule.includes("이미지 내부 텍스트 없음") || brief.visuals.hero.textOverlay !== false) {
      throw new Error(`${product.name}: 텍스트 없는 이미지 제작 규칙 누락`);
    }
    if (!brief.article.caseExample.fields.every((value) => value.includes("입력"))) {
      throw new Error(`${product.name}: 승인 사례 자리표시자 누락`);
    }
    if (!brief.article.banner.headline || !brief.article.banner.button || !brief.article.banner.url.includes("직접 입력")) {
      throw new Error(`${product.name}: 하단 CTA 배너 구성 누락`);
    }
    if (!brief.article.reviewFooter.includes("심의필 번호 직접 입력")) {
      throw new Error(`${product.name}: 심의정보 입력란 누락`);
    }
    if (!brief.keywords.primary.kw || !brief.keywords.related.length || !brief.keywords.support.length) {
      throw new Error(`${product.name}: 키워드 전략 누락`);
    }
    if (brief.keywords.all.some((keyword) => forbiddenKeyword.test(keyword))) {
      throw new Error(`${product.name}: 경쟁사 키워드 혼입 '${brief.keywords.all.join(" · ")}'`);
    }
    const material = `${candidate.title} ${brief.intro}`.replace(/\s/g, "");
    if (!material.includes(brief.keywords.primary.kw.replace(/\s/g, ""))) {
      throw new Error(`${product.name}: 대표 키워드가 제목·설명에 없음`);
    }
    if (brief.ad.title !== candidate.title || brief.ad.description !== brief.intro) {
      throw new Error(`${product.name}: 콘텐츠와 광고 소재 연결 실패`);
    }
    const review = check.reviewPowerMaterial(product, candidate, brief.intro);
    if (review.generationBlocking) throw new Error(`${product.name}: 보험광고 사전검수 ${review.statusLabel}`);
  }
  console.log(`OK  ${product.name}: 키워드 전략 · 콘텐츠 3안 · 발행본문 1,500자+ · 대표 1/중간 3 · CTA 배너`);
}

const driver = check.PRODUCTS.find((product) => product.key === "driver");
const driverSet = check.contentKeywordSet(driver);
const driverMeasured = check.volumeRows(driver);
const driverKeys = new Set(driverSet.map((row) => row.keyword.replace(/\s/g, "").toLowerCase()));
if (driverSet.length < 50) throw new Error(`운전자보험 전체 키워드셋이 너무 적음: ${driverSet.length}개`);
if (driverKeys.size !== driverSet.length) throw new Error("운전자보험 전체 키워드셋에 중복 키워드가 있음");
if (driverMeasured.some((row) => !driverKeys.has(row.kw.replace(/\s/g, "").toLowerCase()))) {
  throw new Error("운전자보험 SearchAd 실측 활용 가능 키워드가 전체 키워드셋에서 누락됨");
}
if (driverSet.some((row) => forbiddenKeyword.test(row.keyword) || /자동차\s*보험|원데이|일일운전자|1일운전자|단기운전자|하루운전자|렌트카보험|한문철/.test(row.keyword))) {
  throw new Error("운전자보험 전체 키워드셋에 제외 키워드가 포함됨");
}
if (driverSet.some((row) => !row.priority || !row.category || !row.intent || !row.source || !row.use || !row.status)) {
  throw new Error("운전자보험 전체 키워드셋 Excel 필수 분류값 누락");
}
for (const category of ["대표", "실측 연관", "담보·상황", "의사결정", "질문형"]) {
  if (!driverSet.some((row) => row.category.includes(category))) throw new Error(`운전자보험 전체 키워드셋 ${category} 누락`);
}
console.log(`OK  운전자보험 전체 키워드셋 ${driverSet.length}개 · 중복/범위/Excel 필드 검증`);

const sample = check.titleCandidates(driver)[0];
check.setData(volumeData, seasonalData, titleData, serpData, { entries: [{
  product_key: driver.key,
  planning_month: "2026-07",
  title: sample.title,
  target_query: sample.target_query,
  angle: sample.angle || sample.pattern,
  sections: sample.sections || [],
}] });
if (!check.candidateCannibalization(driver, sample)) {
  throw new Error("운전자보험 과거 동일 제안 카니벌라이제이션을 감지하지 못함");
}
console.log("OK  과거 제목·검색의도·본문 각도 카니벌라이제이션 감지");

console.log("OK  파워콘텐츠 12상품 콘텐츠 제안 품질 가드 통과");
