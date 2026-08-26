const RETENTION_MONTHS = 13;
const SERVICE_RE = /해지|해약|청구|보상|환급|약관|고객\s*센터|콜센터|전화|로그인|접수|보험금/iu;
const PRODUCT_REVIEW_RE = /1일|일일|하루|원데이|단기|추가|자부상|자동차부상치료비/iu;
const COMPETITOR_RE = /캐롯|삼성(?:화재)?|현대해상|DB손해|디비손해|KB손해|케이비손해|메리츠|롯데손해|흥국화재|교보|농협손해|AXA|악사/iu;

export const normalizeKeyword = value => String(value || "").replace(/\s+/g, "").toLowerCase();

export function classifySuggestion(keyword, product = {}) {
  const normal = normalizeKeyword(keyword);
  const excluded = (product.excluded || []).some(term => {
    const exact = normalizeKeyword(term), stem = exact.replace(/보험$/u, "");
    return normal.includes(exact) || (stem.length >= 3 && normal.includes(stem));
  });
  if (excluded) {
    return { intent: "상품제외", registration: "exclude", reason: "상품 마스터 제외어와 일치" };
  }
  if (SERVICE_RE.test(keyword)) {
    return { intent: "기존고객", registration: "exclude", reason: "해지·청구 등 기존고객 업무 의도" };
  }
  if (COMPETITOR_RE.test(keyword)) {
    return { intent: "경쟁브랜드", registration: "review", reason: "상표·랜딩 관련성 확인 필요" };
  }
  if (PRODUCT_REVIEW_RE.test(keyword)) {
    return { intent: "상품확인", registration: "review", reason: "실제 판매 상품·담보와 일치 여부 확인" };
  }
  if (/보험료|가격|비교|추천|견적|가입|다이렉트|저렴|계산/iu.test(keyword)) {
    return { intent: "가입검토", registration: "recommended", reason: "가입 탐색 의도" };
  }
  return { intent: "정보탐색", registration: "review", reason: "랜딩 콘텐츠 관련성 확인" };
}

export function buildDataset({ previous = {}, products, captured, asof }) {
  const month = asof.slice(0, 7);
  const snapshots = { ...(previous.snapshots || {}) };
  const previousMonths = Object.keys(snapshots).filter(key => key < month).sort();
  const previousMonth = previousMonths.at(-1) || null;
  const previousSnapshot = previousMonth ? snapshots[previousMonth] : null;
  const currentProducts = {};

  for (const product of products) {
    const seen = new Set();
    const suggestions = [];
    for (const raw of (captured[product.key] || [])) {
      const keyword = String(raw.keyword || "").replace(/\s+/g, " ").trim();
      const normal = normalizeKeyword(keyword);
      if (!keyword || seen.has(normal)) continue;
      seen.add(normal);
      const firstSeenMonth = Object.keys(snapshots).sort().find(period =>
        (((snapshots[period] || {}).products || {})[product.key] || []).some(item => normalizeKeyword(item) === normal)
      ) || month;
      const wasPresent = previousSnapshot
        ? ((((previousSnapshot.products || {})[product.key]) || []).some(item => normalizeKeyword(item) === normal))
        : false;
      suggestions.push({
        keyword, seed: raw.seed, rank: raw.rank, ...classifySuggestion(keyword, product), firstSeenMonth,
        isNew: Boolean(previousSnapshot && !wasPresent),
      });
    }
    suggestions.sort((a, b) => a.rank - b.rank || a.keyword.localeCompare(b.keyword, "ko"));
    currentProducts[product.key] = { name: product.name, suggestions };
  }

  snapshots[month] = {
    asof,
    products: Object.fromEntries(products.map(product => [
      product.key,
      (currentProducts[product.key]?.suggestions || []).map(item => item.keyword),
    ])),
  };
  const keep = Object.keys(snapshots).sort().slice(-RETENTION_MONTHS);
  return {
    _comment: "네이버 공개 검색 화면의 자동완성 표시어 월간 스냅샷. 신규는 직전 수집월 대비 새로 등장한 검색어이며, 등록 추천은 검색량·상품 관련성을 별도 확인해야 한다.",
    source: "naver-visible-autocomplete", asof, month, previousMonth, cadence: "monthly",
    collection: { method: "playwright-visible-ui", login: false, seedsPerProduct: 3 },
    products: currentProducts,
    snapshots: Object.fromEntries(keep.map(key => [key, snapshots[key]])),
  };
}
