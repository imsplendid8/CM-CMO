import fs from "node:fs";
import vm from "node:vm";

const html = fs.readFileSync(new URL("../adcopy-tool.html", import.meta.url), "utf8");
const scripts = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map((m) => m[1]);
const appScript = scripts.find((source) => source.includes("function buildNaverRows"));

if (!appScript) {
  throw new Error("adcopy-tool.html에서 소재 생성 스크립트를 찾지 못했습니다.");
}

const pureSection = appScript.split("/* ── 날씨 대응")[0];
const context = { console };
vm.createContext(context);
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
    const signature = [
      row.campaignName,
      row.adGroupName,
      row.title,
      row.description,
      row.extraTitle,
      row.promo,
      row.sublink1,
      row.sublink2,
      row.sublink3,
      row.sublink4,
    ].join("|");
    if (signatures.has(signature)) throw new Error(`${product.name}: 중복 소재 조합 발견`);
    signatures.add(signature);
  }
  total += rows.length;
  console.log(`OK  ${product.name}: 50행`);
}

if (total !== 650) throw new Error(`전체 행 수 불일치: ${total}행 (기대 650행)`);
console.log(`OK  전체 ${PRODUCTS.length}상품 × 50행 = ${total}행`);
console.log("OK  선택월·익월 밖 시즌 소재 제외 (8월→9월, 신년 문구 없음)");
