import fs from "node:fs";
import vm from "node:vm";

const html = fs.readFileSync(new URL("../keyword-tool.html", import.meta.url), "utf8");
const scripts = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map((match) => match[1]);
const appScript = scripts.find((source) => source.includes("function monthlyMovers"));

if (!appScript) throw new Error("keyword-tool.html에서 월간 키워드 로직을 찾지 못했습니다.");

const pureSection = appScript.split("function importKeywords")[0];
const context = { console };
vm.createContext(context);
vm.runInContext(
  `${pureSection}\n;globalThis.__KW_CHECK__={monthlyMovers,setHistory:(history)=>{VOL_HISTORY=history;}};`,
  context,
  { filename: "keyword-tool.html" },
);

const { monthlyMovers, setHistory } = context.__KW_CHECK__;
setHistory({
  source: "searchad",
  snapshots: {
    "2026-07": { products: { cncr: { keywords: {
      "암보험": { total: 100, comp: "높음" },
      "신규 암 키워드": { total: 0, comp: "중간" },
      "소폭 상승": { total: 100, comp: "낮음" },
      "기준 미달 신규": { total: 0, comp: "낮음" },
    } } } },
    "2026-08": { products: { cncr: { keywords: {
      "암보험": { total: 170, comp: "높음" },
      "신규 암 키워드": { total: 150, comp: "중간" },
      "소폭 상승": { total: 140, comp: "낮음" },
      "기준 미달 신규": { total: 99, comp: "낮음" },
    } } } },
  },
});

const report = monthlyMovers("cncr");
if (report.previous !== "2026-07" || report.current !== "2026-08") throw new Error("비교 월 선택 오류");
if (report.rows.length !== 2) throw new Error(`후보 수 불일치: ${report.rows.length}개 (기대 2개)`);
const byKeyword = new Map(report.rows.map((row) => [row.keyword, row]));
if (byKeyword.get("암보험")?.kind !== "rising") throw new Error("급상승 판정 실패");
if (byKeyword.get("신규 암 키워드")?.kind !== "new") throw new Error("신규 판정 실패");
if (byKeyword.has("소폭 상승") || byKeyword.has("기준 미달 신규")) throw new Error("기준 미달 키워드가 후보에 포함됨");

console.log("OK  신규: 전월 0·당월 100회 이상");
console.log("OK  급상승: 전월 10회 이상·+50회·+50% 이상");
