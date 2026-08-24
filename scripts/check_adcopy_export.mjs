import fs from "node:fs";
import vm from "node:vm";

const html = fs.readFileSync(new URL("../adcopy-tool.html", import.meta.url), "utf8");
const materialSpecs = fs.readFileSync(new URL("../shared/naver-material-specs.js", import.meta.url), "utf8");
const scripts = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map((m) => m[1]);
const appScript = scripts.find((source) => source.includes("function buildNaverRows"));

if (!appScript) {
  throw new Error("adcopy-tool.html에서 소재 생성 스크립트를 찾지 못했습니다.");
}

const pureSection = appScript.split("/* ── 날씨 대응")[0];
const context = { console };
vm.createContext(context);
vm.runInContext(materialSpecs, context, { filename: "shared/naver-material-specs.js" });
vm.runInContext(
  `${pureSection}\n;globalThis.__AD_CHECK__={PRODUCTS,buildSheet,buildNaverRows,validateNaverRow,setPlanMonth:(month)=>{PLANM=month;}};`,
  context,
  { filename: "adcopy-tool.html" },
);

const { PRODUCTS, buildSheet, buildNaverRows, validateNaverRow, setPlanMonth } = context.__AD_CHECK__;
if (PRODUCTS.length !== 13) {
  throw new Error(`상품 수 불일치: ${PRODUCTS.length}개 (기대 13개)`);
}

setPlanMonth(8);
for (const product of PRODUCTS) {
  const sheet = buildSheet(product);
  if (sheet.subt.length > 15 || sheet.additionalDesc.length !== 4 || sheet.promo.length !== 2 || sheet.sub.length !== 4) {
    throw new Error(`${product.name}: 확장소재 후보 개수 불일치 (추가제목 ${sheet.subt.length}, 추가설명 ${sheet.additionalDesc.length}, 홍보 ${sheet.promo.length}, 서브링크 ${sheet.sub.length})`);
  }
  if (sheet.issues.some((issue) => !issue.m.includes(8) && !issue.m.includes(9))) {
    throw new Error(`${product.name}: 선택월(8월)·익월(9월) 밖 시즌 소재가 포함됨`);
  }
}
const cancerSheet = buildSheet(PRODUCTS.find((product) => product.key === "cncr"));
if ([...cancerSheet.subt, ...cancerSheet.desc].some((row) => row.tx.includes("신년"))) {
  throw new Error("8월 암보험 소재에 신년 문구가 포함됨");
}

let total = 0;
for (const product of PRODUCTS) {
  const rows = buildNaverRows(product, 50);
  if (rows.length !== 50) {
    throw new Error(`${product.name}: ${rows.length}행 (기대 50행)`);
  }
  const signatures = new Set();
  for (const row of rows) {
    const errors = validateNaverRow(row);
    if (errors.length) throw new Error(`${product.name}: ${errors.join(", ")}`);
    const generatedCopy = [row.title, row.description, row.extraTitle, row.additionalDescription, row.promo].join(" ");
    if (/24시간|3분|바로 가입|최저|저렴|무료|무조건/.test(generatedCopy)) {
      throw new Error(`${product.name}: 근거 확인 전 사용할 수 없는 표현 '${generatedCopy}'`);
    }
    const signature = [
      row.campaignName,
      row.adGroupName,
      row.title,
      row.description,
      row.extraTitle,
      row.additionalDescription,
      row.promo,
      row.sublink1,
      row.sublink2,
      row.sublink3,
      row.sublink4,
    ].join("|");
    for (const key of context.ModooNaverMaterialSpecs.manualOnlyFields) {
      if (row[key] !== "") throw new Error(`${product.name}: ${key} 자동 입력됨`);
    }
    if (signatures.has(signature)) throw new Error(`${product.name}: 중복 소재 조합 발견`);
    signatures.add(signature);
  }
  total += rows.length;
  console.log(`OK  ${product.name}: 50행`);
}

if (total !== 650) throw new Error(`전체 행 수 불일치: ${total}행 (기대 650행)`);
console.log(`OK  전체 ${PRODUCTS.length}상품 × 50행 = ${total}행`);
console.log("OK  선택월·익월 밖 시즌 소재 제외 (8월→9월, 신년 문구 없음)");
