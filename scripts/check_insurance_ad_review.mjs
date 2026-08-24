import fs from "node:fs";
import vm from "node:vm";

const source = fs.readFileSync(new URL("../shared/insurance-ad-review.js", import.meta.url), "utf8");
const context = {};
vm.createContext(context);
vm.runInContext(source, context, {filename: "shared/insurance-ad-review.js"});
const review = context.ModooInsuranceAdReview;
if (!review) throw new Error("보험광고 사전검수 엔진을 불러오지 못했습니다.");

const expect = (condition, message) => { if (!condition) throw new Error(message); };
const hasRule = (result, ruleId) => result.findings.some((finding) => finding.ruleId === ruleId);

const safe = review.review("보험료와 보장 범위, 제외 조건을 상품설명서에서 확인하세요.", {channel: "test"});
expect(!safe.generationBlocking, "조건 확인형 안전 문구가 생성 차단됨");
expect(safe.status === "manual_review", "상품 표현은 사람 심의 필요로 남아야 함");

const certainty = review.review("무조건 100% 보장", {channel: "test"});
expect(certainty.status === "blocked" && hasRule(certainty, "FCPA-22-CERTAINTY"), "확정 보장 표현 미차단");

const comparison = review.review("업계 1위 운전자보험", {channel: "test"});
expect(comparison.generationBlocking && hasRule(comparison, "DECREE-20-COMPARISON"), "근거 없는 순위 표현 미탐지");

const dailyPremium = review.review("하루 300원으로 부담 없이", {channel: "test"});
expect(dailyPremium.generationBlocking && hasRule(dailyPremium, "FCPA-22-PREMIUM-BURDEN"), "일 단위 보험료 표현 미탐지");

const unlimited = review.review("횟수 제한 없이 모두 보장", {channel: "test"});
expect(hasRule(unlimited, "FCPA-22-COVERAGE-LIMIT"), "무제한 보장 오인 표현 미탐지");

const renewal = review.review("갱신형 100세 보장", {channel: "test"});
expect(hasRule(renewal, "FCPA-22-RENEWAL"), "갱신 안내 필요 표현 미탐지");

expect(review.verifiedAt === "2026-08-25", "규정 확인일 불일치");
expect(review.sources.fcpa22.url.startsWith("https://www.law.go.kr/"), "법령 원문 링크 누락");
expect(review.sources.knia.url.startsWith("https://adview.knia.or.kr/"), "손해보험협회 심의시스템 링크 누락");
expect(review.sources.kniaGuide.url.startsWith("https://www.knia.or.kr/"), "손해보험협회 가이드 링크 누락");
expect(safe.disclaimer.includes("승인 또는 심의 결과가 아닙니다"), "자동검수 한계 안내 누락");

console.log("OK  보험광고 법령 기반 사전검수 규칙 통과");
