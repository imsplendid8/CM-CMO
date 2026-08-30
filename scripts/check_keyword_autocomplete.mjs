import fs from "node:fs";
import { buildDataset, classifySuggestion } from "./keyword_autocomplete_core.mjs";

const products = [{ key: "driver", name: "운전자보험" }];
const previous = {
  snapshots: {
    "2026-07": { products: { driver: ["운전자보험 비교", "운전자보험 해지"] } },
  },
};
const captured = {
  driver: [
    { keyword: "운전자보험 비교", seed: "운전자보험", rank: 1 },
    { keyword: "운전자보험 저렴한곳", seed: "운전자보험", rank: 2 },
    { keyword: "운전자보험 청구", seed: "운전자보험", rank: 3 },
  ],
};
const data = buildDataset({ previous, products, captured, asof: "2026-08-27" });
const rows = data.products.driver.suggestions;
const byKeyword = new Map(rows.map(row => [row.keyword, row]));

if (data.previousMonth !== "2026-07") throw new Error("직전 월 선택 실패");
if (byKeyword.get("운전자보험 비교")?.isNew) throw new Error("기존 키워드를 신규로 판정");
if (!byKeyword.get("운전자보험 저렴한곳")?.isNew) throw new Error("신규 자동완성 판정 실패");
if (byKeyword.get("운전자보험 저렴한곳")?.registration !== "recommended") throw new Error("가입 의도 추천 실패");
if (byKeyword.get("운전자보험 청구")?.registration !== "exclude") throw new Error("기존고객 의도 제외 실패");
if (classifySuggestion("캐롯 운전자보험").registration !== "review") throw new Error("경쟁브랜드 검토 분류 실패");
if (classifySuggestion("한화손보 다이렉트 자동차", { excluded: ["자동차보험"] }).registration !== "exclude") throw new Error("상품 제외어 차단 실패");
if (!rows.some(row => row.keyword === "운전자보험비교사이트")) throw new Error("운전자보험 롱테일 확장 실패");
if (!rows.some(row => row.keyword === "다이렉트 운전자보험비교사이트")) throw new Error("운전자보험 보조 롱테일 확장 실패");

const html = fs.readFileSync(new URL("../keyword-tool.html", import.meta.url), "utf8");
for (const marker of ["data/keyword-autocomplete.json", "네이버 자동완성", "선택 키워드 등록 CSV", "isNew"]) {
  if (!html.includes(marker)) throw new Error(`키워드 UI 계약 누락: ${marker}`);
}
console.log("OK  월간 자동완성 신규 판정·등록 안전 분류·UI 계약");
