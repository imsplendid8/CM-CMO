import fs from "node:fs";
import vm from "node:vm";

const root = new URL("../", import.meta.url);
const html = fs.readFileSync(new URL("powercontent-tool.html", root), "utf8");
const materialSpecs = fs.readFileSync(new URL("shared/naver-material-specs.js", root), "utf8");
const insuranceAdReview = fs.readFileSync(new URL("shared/insurance-ad-review.js", root), "utf8");
const scripts = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map((match) => match[1]);
const appScript = scripts.find((source) => source.includes("function titleCandidates"));
if (!appScript) throw new Error("powercontent-tool.html에서 후보 생성 로직을 찾지 못했습니다.");

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
    PRODUCTS,REFERENCE_PATTERNS,titleCandidates,adDraftFor,reviewPowerMaterial,volumeRows,inScope,clen,
    referencePatternFor,normalizePostText,descriptionCandidatesFrom,seoAlignment,
    setData:(volume,seasonal,titles)=>{DATA={volume,seasonal,titles};}
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
);

if (check.PRODUCTS.length !== 13) throw new Error(`상품 수 불일치: ${check.PRODUCTS.length}개`);
const forbidden = /자동차\s*보험|공개\s*관측|한화생명|고객센터|라이나|영업배상책임|재난배상책임/;

for (const product of check.PRODUCTS) {
  const candidates = check.titleCandidates(product);
  if (candidates.length !== 3) throw new Error(`${product.name}: 제목 후보 ${candidates.length}개 (기대 3개)`);
  for (const candidate of candidates) {
    const titleLength = check.clen(candidate.title);
    if (titleLength < 7 || titleLength > 28) throw new Error(`${product.name}: 제목 ${titleLength}자`);
    if (!check.inScope(product, candidate.target_query || candidate.title)) {
      throw new Error(`${product.name}: 범위 밖 검색어 '${candidate.target_query}'`);
    }
    if (forbidden.test(`${candidate.title} ${candidate.target_query || ""}`)) {
      throw new Error(`${product.name}: 제외 표현 포함 '${candidate.title}'`);
    }
    if (/비교\s+비교할 때|보험비교할 때|(?:기준과|주의사항과|그리고|및)$/.test(candidate.title)) {
      throw new Error(`${product.name}: 어색한 제목 '${candidate.title}'`);
    }
  }
  const representative = check.volumeRows(product)[0]?.kw || product.serpKw;
  if (forbidden.test(representative)) throw new Error(`${product.name}: 대표 검색어 범위 오류 '${representative}'`);
  const ad = check.adDraftFor(candidates[0]);
  if (ad.description || ad.landingUrl || ad.image || ad.publishedAt) {
    throw new Error(`${product.name}: 발행 전 등록 자산이 자동 입력됨`);
  }
  const compliance = check.reviewPowerMaterial(product, candidates[0]);
  if (compliance.generationBlocking) throw new Error(`${product.name}: 보험광고 사전검수 ${compliance.statusLabel}`);
  console.log(`OK  ${product.name}: 포스팅 소재 3안 · 광고 등록 초안 분리`);
}

const groundedCases = [
  {
    key: "driver",
    post: {
      url: "https://blog.naver.com/hanwha-direct/example-driver",
      publishedAt: "2026-08-25",
      title: "운전자보험 가입 방법과 확인 순서",
      body: "운전자보험 가입 방법을 확인할 때는 가입 대상과 운전 용도를 먼저 정하고, 필요한 보장 항목과 제외 조건을 상품설명서에서 살펴본 뒤 본인 정보와 계약 내용을 순서대로 확인해야 합니다. 가입 전에는 약관을 읽고 보장하지 않는 사항도 함께 확인하세요.",
    },
  },
  {
    key: "hrmf",
    post: {
      url: "https://blog.naver.com/hanwha-direct/example-fire",
      publishedAt: "2026-08-25",
      title: "주택화재보험 누수 대비 체크포인트",
      body: "주택화재보험을 살펴볼 때는 우리 집 누수 피해와 아랫집 등 타인의 재산에 생긴 피해를 구분하고, 각 상황에 적용되는 특약의 보장 조건과 제외 사항을 상품설명서에서 확인해야 합니다. 실제 가입 전에는 약관과 상품설명서를 읽어 주세요.",
    },
  },
];

for (const { key, post } of groundedCases) {
  const product = check.PRODUCTS.find((row) => row.key === key);
  const candidate = check.titleCandidates(product)[0];
  const excerpts = check.descriptionCandidatesFrom(post.body, product, candidate);
  if (!check.referencePatternFor(product)) throw new Error(`${product.name}: 경쟁사 구조 참고 누락`);
  if (!excerpts.length) throw new Error(`${product.name}: 원문 연속 발췌 후보 없음`);
  const excerpt = excerpts[0];
  if (excerpt.length < 80 || excerpt.length > 110) throw new Error(`${product.name}: 설명 ${excerpt.length}자`);
  if (!check.normalizePostText(post.body).includes(excerpt.text)) throw new Error(`${product.name}: 원문에 없는 설명 생성`);
  if (check.seoAlignment(product, candidate, post).score < 80) throw new Error(`${product.name}: SEO 정합성 점수 미달`);
  const ad = check.adDraftFor(candidate, post, excerpt.text);
  if (ad.description !== excerpt.text || ad.landingUrl !== post.url || ad.publishedAt !== post.publishedAt) {
    throw new Error(`${product.name}: 원문 기반 등록 초안 연결 실패`);
  }
  console.log(`OK  ${product.name}: 네이버 규격 · SEO 정합성 · 타사 구조 참고 가드 통과`);
}

console.log("OK  파워컨텐츠 13상품 품질 가드 통과");
