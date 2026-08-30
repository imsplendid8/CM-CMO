const RETENTION_MONTHS = 13;
const SERVICE_RE = /해지|해약|청구|보상|환급|약관|고객\s*센터|콜센터|전화|로그인|접수|보험금/iu;
const PRODUCT_REVIEW_RE = /1일|일일|하루|원데이|단기|추가|자부상|자동차부상치료비/iu;
const COMPETITOR_RE = /캐롯|삼성(?:화재)?|현대해상|DB손해|디비손해|KB손해|케이비손해|메리츠|롯데손해|흥국화재|교보|농협손해|AXA|악사/iu;
const NAVER_SUFFIXES = ["보험료", "비교", "가격", "가입", "가입방법", "다이렉트", "계산", "견적", "추천", "후기", "약관", "청구", "해지"];
const GOOGLE_SUFFIXES = ["가입 전 확인", "필요한가요", "얼마인가요", "비교 방법", "추천 기준", "후기", "단점", "나이", "20대", "30대", "40대", "50대", "60대", "보장내용", "특약", "면책", "고지의무"];
const QUESTION_SUFFIXES = ["어떤 경우", "무엇을 확인", "가입 조건", "보험료 차이", "보장하지 않는 경우"];
const LONGTAIL_SUFFIXES = ["비교사이트", "비교견적", "가입조건", "가입전확인", "보장내용", "보장범위", "청구방법", "해지방법", "후기", "추천", "가격비교", "보험료계산", "약관", "특약", "면책", "주의사항"];
const OVERSEAS_REGIONS = ["일본", "미국", "유럽", "동남아", "베트남", "태국", "필리핀", "대만", "홍콩", "괌", "사이판", "호주", "캐나다", "뉴질랜드"];
const OVERSEAS_TARGETS = ["유학생", "워홀", "워킹홀리데이", "어학연수", "교환학생", "장기체류", "주재원", "해외출장"];

function productSignals(product = {}) {
  const text = `${product.key || ""} ${product.name || ""} ${product.serpKw || ""} ${(product.core || []).join(" ")} ${(product.special || []).join(" ")}`;
  const overseas = /해외여행|여행자보험|장기체류|유학생|워홀|워킹홀리데이|어학연수|주재원/iu.test(text) || ["overseas", "overseaslong"].includes(product.key);
  const driver = /운전자보험|교통사고|벌금|변호사선임|형사합의금|12대중과실/iu.test(text) || product.key === "driver";
  const home = /주택화재|화재보험|누수|풍수재|도난|스크린홀인원/iu.test(text) || product.key === "hrmf";
  return { overseas, driver, home };
}

export function seedQueries(product = {}) {
  const base = [...new Set([product.serpKw, ...(product.core || []), product.name].filter(Boolean))];
  const special = (product.special || []).slice(0, 6);
  const overseasSeeds = (product.key === "overseas" || product.key === "overseaslong")
    ? [
        ...OVERSEAS_REGIONS.map(region => `${region} 해외여행보험`),
        ...OVERSEAS_REGIONS.map(region => `${region} 여행자보험`),
        ...OVERSEAS_TARGETS.map(target => `${target} 해외여행보험`),
        ...OVERSEAS_TARGETS.map(target => `${target} 여행자보험`),
      ]
    : [];
  const longtail = base.slice(0, 2).flatMap(keyword => LONGTAIL_SUFFIXES.map(suffix => `${keyword}${suffix}`));
  const seeds = [
    ...base,
    ...base.slice(0, 2).flatMap(keyword => ["보험료", "비교", "가입", "추천", "후기", "약관"].map(suffix => `${keyword} ${suffix}`)),
    ...special.flatMap(term => [term, `${product.serpKw || product.name} ${term}`]),
    ...longtail,
    ...overseasSeeds,
  ];
  return [...new Set(seeds.map(value => String(value).replace(/\s+/g, " ").trim()).filter(Boolean))].slice(0, 120);
}

function expandedSuggestions(product = {}) {
  const primary = product.serpKw || product.name;
  const core = [...new Set([primary, ...(product.core || [])].filter(Boolean))].slice(0, 4);
  const special = (product.special || []).slice(0, 6);
  const signals = productSignals(product);
  const rows = [];
  const push = (keyword, seed, rank, sourcePlatform, sourceType, seedGroup) => {
    rows.push({ keyword, seed, rank, source_platform: sourcePlatform, source_type: sourceType, seed_group: seedGroup });
  };
  core.forEach((seed, seedIndex) => {
    NAVER_SUFFIXES.forEach((suffix, index) => push(`${seed} ${suffix}`, seed, 100 + seedIndex * 30 + index, "naver", "expanded_seed", "거래·서비스"));
    GOOGLE_SUFFIXES.forEach((suffix, index) => push(`${seed} ${suffix}`, seed, 300 + seedIndex * 40 + index, "google", "pattern_expand", "질문·비교"));
    LONGTAIL_SUFFIXES.forEach((suffix, index) => push(`${seed}${suffix}`, seed, 500 + seedIndex * 50 + index, "naver", "pattern_expand", "롱테일 결합"));
  });
  special.forEach((term, index) => {
    push(`${primary} ${term}`, primary, 600 + index, "naver", "expanded_seed", "담보·세부항목");
    push(`${term} 보험`, term, 650 + index, "google", "pattern_expand", "담보·정보탐색");
    QUESTION_SUFFIXES.forEach((suffix, qIndex) => push(`${term} ${suffix}`, term, 700 + index * 10 + qIndex, "google", "pattern_expand", "담보 질문"));
  });
  if (signals.overseas) {
    OVERSEAS_REGIONS.forEach((region, index) => {
      push(`${region} 해외여행보험`, primary, 900 + index, "naver", "pattern_expand", "지역·보험");
      push(`${region} 여행자보험`, primary, 960 + index, "naver", "pattern_expand", "지역·보험");
      push(`${region} 여행보험`, primary, 1020 + index, "google", "pattern_expand", "지역·보험");
    });
    OVERSEAS_TARGETS.forEach((target, index) => {
      push(`${target} 해외여행보험`, primary, 1100 + index, "naver", "pattern_expand", "타겟·보험");
      push(`${target} 여행자보험`, primary, 1160 + index, "naver", "pattern_expand", "타겟·보험");
      push(`${target} 보험`, target, 1220 + index, "google", "pattern_expand", "타겟·보험");
    });
  }
  if (signals.driver) {
    ["비교사이트", "가격비교", "보험료계산", "가입조건", "교통사고", "벌금", "변호사선임", "형사합의금"].forEach((suffix, index) => {
      push(`운전자보험${suffix}`, primary, 1300 + index, "naver", "pattern_expand", "운전자 롱테일");
      push(`다이렉트 운전자보험${suffix}`, primary, 1360 + index, "google", "pattern_expand", "운전자 롱테일");
    });
  }
  if (signals.home) {
    ["누수", "화재", "풍수재", "도난", "스크린홀인원"].forEach((suffix, index) => {
      push(`주택화재보험${suffix}`, primary, 1420 + index, "naver", "pattern_expand", "주택 롱테일");
      push(`화재보험${suffix}`, primary, 1480 + index, "google", "pattern_expand", "주택 롱테일");
    });
  }
  return rows;
}

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
    const rawRows = [
      ...(captured[product.key] || []).map(row => ({ source_platform: "naver", source_type: "visible_ui", seed_group: "실측 화면", ...row })),
      ...expandedSuggestions(product),
    ];
    for (const raw of rawRows) {
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
        keyword, seed: raw.seed, rank: raw.rank, source_platform: raw.source_platform || "naver",
        source_type: raw.source_type || "visible_ui", seed_group: raw.seed_group || "실측 화면",
        ...classifySuggestion(keyword, product), firstSeenMonth,
        isNew: Boolean(previousSnapshot && !wasPresent),
      });
    }
    const platformOrder = { naver: 0, google: 1 };
    const typeOrder = { visible_ui: 0, expanded_seed: 1, pattern_expand: 2 };
    suggestions.sort((a, b) =>
      (platformOrder[a.source_platform] ?? 9) - (platformOrder[b.source_platform] ?? 9) ||
      (typeOrder[a.source_type] ?? 9) - (typeOrder[b.source_type] ?? 9) ||
      a.rank - b.rank || a.keyword.localeCompare(b.keyword, "ko"));
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
    _comment: "네이버 공개 검색 화면 자동완성 표시어와 구글형 질문·비교 롱테일 보강 후보의 월간 스냅샷. visible_ui만 실제 화면 관측이며, expanded_seed/pattern_expand는 후보 확장값이다. 해외여행보험은 지역명·타겟 조합을, 보험 전반은 비교사이트·가격비교·가입조건 등 롱테일 결합을 보강한다.",
    source: "naver-visible-autocomplete", asof, month, previousMonth, cadence: "monthly",
    collection: { method: "playwright-visible-ui + offline-pattern-expand", login: false, seedsPerProduct: 24, platforms: ["naver", "google"] },
    products: currentProducts,
    snapshots: Object.fromEntries(keep.map(key => [key, snapshots[key]])),
  };
}
