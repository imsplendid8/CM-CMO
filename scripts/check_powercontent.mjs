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
    PRODUCTS,titleCandidates,reviewPowerMaterial,volumeRows,inScope,clen,keywordPlan,introFor,
    contentBriefFor,approvedClaimsFor,
    setData:(volume,seasonal,titles,claims)=>{DATA={volume,seasonal,titles,claims};}
  };`,
  context,
  { filename: "powercontent-tool.html" },
);

const check = context.__POWER_CHECK__;
const readJson = (path) => JSON.parse(fs.readFileSync(new URL(path, root), "utf8"));
check.setData(
  readJson("data/volume.json"),
  readJson("data/seasonal.json"),
  readJson("data/adcopy/powercontent-title-opportunities.json"),
  readJson("data/evidence/claims.json"),
);

if (check.PRODUCTS.length !== 13) throw new Error(`상품 수 불일치: ${check.PRODUCTS.length}개`);
const forbidden = /자동차\s*보험|공개\s*관측|한화생명|고객센터|라이나|영업배상책임|재난배상책임/;
const forbiddenKeyword = /삼성|DB|디비|동부|현대|KB|메리츠|라이나|AXA|악사|흥국|롯데|신한/;

for (const product of check.PRODUCTS) {
  const candidates = check.titleCandidates(product);
  if (candidates.length !== 3) throw new Error(`${product.name}: 콘텐츠 소재 ${candidates.length}개 (기대 3개)`);
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
  console.log(`OK  ${product.name}: 키워드 전략 · 콘텐츠 3안 · 본문 5섹션 · FAQ 4개`);
}

if (check.PRODUCTS.some((product) => check.approvedClaimsFor(product).length)) {
  throw new Error("현재 원장에는 승인된 power_content claim이 없어야 합니다.");
}

console.log("OK  파워콘텐츠 13상품 콘텐츠 제안 품질 가드 통과");
