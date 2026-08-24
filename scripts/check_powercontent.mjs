import fs from "node:fs";
import vm from "node:vm";

const root = new URL("../", import.meta.url);
const html = fs.readFileSync(new URL("powercontent-tool.html", root), "utf8");
const materialSpecs = fs.readFileSync(new URL("shared/naver-material-specs.js", root), "utf8");
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
vm.runInContext(
  `${pureSection}
  ;globalThis.__POWER_CHECK__={
    PRODUCTS,titleCandidates,descriptionFor,extensionBrief,validateExtensions,volumeRows,inScope,clen,
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
    const description = check.descriptionFor(product, candidate);
    const descriptionLength = check.clen(description);
    if (titleLength < 7 || titleLength > 28) throw new Error(`${product.name}: 제목 ${titleLength}자`);
    if (descriptionLength < 80 || descriptionLength > 110) throw new Error(`${product.name}: 설명 ${descriptionLength}자`);
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
  const extensions = check.extensionBrief(product, candidates[0]);
  const extensionErrors = check.validateExtensions(extensions);
  if (extensionErrors.length) throw new Error(`${product.name}: ${extensionErrors.join(", ")}`);
  for (const key of context.ModooNaverMaterialSpecs.manualOnlyFields) {
    if (extensions.manual[key] !== "") throw new Error(`${product.name}: ${key} 자동 입력됨`);
  }
  console.log(`OK  ${product.name}: 제목 3안 · 설명 80~110자 · 확장소재 규격 통과`);
}

console.log("OK  파워컨텐츠 13상품 품질 가드 통과");
