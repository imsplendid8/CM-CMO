(function (root) {
  "use strict";

  const freeze = (value) => Object.freeze(value);
  const SOURCES = freeze({
    verifiedAt: "2026-08-25",
    fcpa22: freeze({label: "금융소비자보호법 제22조", url: "https://www.law.go.kr/lsLinkCommonInfo.do?chrClsCd=010202&lsJoLnkSeq=1031294935"}),
    decree18to19: freeze({label: "금융소비자보호법 시행령 제18조~제19조", url: "https://law.go.kr/lsLinkCommonInfo.do?chrClsCd=010202&lspttninfSeq=166871"}),
    decree20: freeze({label: "금융소비자보호법 시행령 제20조", url: "https://law.go.kr/LSW/lumLsLinkPop.do?chrClsCd=010202&lspttninfSeq=166867"}),
    supervision17to19: freeze({label: "금융소비자 보호에 관한 감독규정 제17조~제19조", url: "https://www.law.go.kr/LSW/admRulLsInfoP.do?admRulSeq=2100000276850"}),
    knia: freeze({label: "손해보험협회 광고심의 관리시스템", url: "https://adview.knia.or.kr/bizApp/authenticate/addeUserLogin.do"}),
    kniaGuide: freeze({label: "손해보험협회 광고심의 가이드라인 (I)", url: "https://www.knia.or.kr/file-manager/103316"}),
  });
  const LABELS = freeze({blocked: "자동 차단", needs_evidence: "근거 필요", needs_disclosure: "필수 고지 필요", manual_review: "사람 심의 필요", auto_clear: "자동 위험표현 없음"});
  const PRIORITY = freeze({auto_clear: 0, manual_review: 1, needs_disclosure: 2, needs_evidence: 3, blocked: 4});

  /* 법령 자체의 금칙어 목록이 아니라, 해당 법령 위반 가능성을 찾기 위한 보수적 1차 탐지어다. */
  const RULES = freeze([
    freeze({
      id: "FCPA-22-CERTAINTY", source: "fcpa22", status: "blocked",
      terms: freeze(["무조건", "100%", "완벽", "절대", "확정", "보장 확정", "원금보장", "평생보장", "누구나", "전원", "무심사"]),
      message: "불확실한 보험금 지급·가입 결과를 확정적으로 오인시킬 수 있습니다.",
      action: "확정 표현을 삭제하고 실제 가입·지급 요건을 상품자료와 약관 기준으로 적으세요.",
    }),
    freeze({
      id: "DECREE-20-COMPARISON", source: "decree20", status: "needs_evidence",
      terms: freeze(["최고", "최상", "최대", "최저가", "최저", "제일", "1위", "일등", "넘버원", "넘버1", "유일", "단독", "최초", "제1위", "가장", "업계 최초", "국내 최초", "저렴", "더 유리", "더 우수"]),
      message: "비교 대상·기준이 분명하지 않거나 객관적 근거가 없는 우월 표현일 수 있습니다.",
      action: "표현을 삭제하거나 비교 대상·기준일·산출 기준·객관적 증빙을 같은 광고에서 확인 가능하게 하세요.",
    }),
    freeze({
      id: "DECREE-20-STATISTICS", source: "decree20", status: "needs_evidence",
      patterns: freeze([/\d+(?:\.\d+)?\s*%/g, /\d+\s*년\s*연속/g, /\d+\s*명\s*중\s*\d+\s*명/g]),
      message: "수치·통계 표현은 산출 기준과 객관적 증빙을 확인해야 합니다.",
      action: "출처, 기준시점, 조사대상과 산출 기준을 확인하고 광고 안에서 식별할 수 있게 표시하세요.",
    }),
    freeze({
      id: "FCPA-22-COVERAGE-LIMIT", source: "fcpa22", status: "needs_disclosure",
      terms: freeze(["제한 없이", "제한없이", "횟수 제한 없이", "횟수제한없이", "전부 보장", "전액 보장", "모두 보장", "다 보장"]),
      message: "보험금 지급한도·제외사유가 없는 것처럼 오인시킬 수 있습니다.",
      action: "면책·감액·횟수·금액 한도 등 실제 지급제한을 혜택과 균형 있게 표시하세요.",
    }),
    freeze({
      id: "FCPA-22-PREMIUM-BURDEN", source: "fcpa22", status: "needs_evidence",
      terms: freeze(["부담 없이", "부담없는", "커피 한 잔", "커피한잔", "소액으로", "공짜", "완전무료", "무료", "할인"]),
      patterns: freeze([/(?:하루|일일)\s*[0-9,]+\s*원/g]),
      message: "보험료나 경제적 부담이 실제보다 작다고 오인시킬 수 있습니다.",
      action: "산출 조건이 확인된 실제 보험료만 사용하고 가입 조건·납입기간 등 판단 기준을 함께 표시하세요.",
    }),
    freeze({
      id: "DECREE-20-SPEED", source: "decree20", status: "needs_evidence",
      terms: freeze(["바로 가입", "즉시 가입", "당일 가입", "전날 가입", "24시간", "3분 가입", "1분 가입"]),
      message: "가입 가능 시점·처리 속도를 단정하는 표현은 실제 절차 근거가 필요합니다.",
      action: "채널 운영시간, 인수심사와 가입 제한을 확인한 뒤 입증 가능한 범위로 수정하세요.",
    }),
    freeze({
      id: "FCPA-22-RENEWAL", source: "fcpa22", status: "needs_disclosure",
      terms: freeze(["갱신형", "자동갱신", "자동 갱신", "100세 보장"]),
      message: "갱신 주기와 갱신 시 보험료 변동 가능성 안내가 필요할 수 있습니다.",
      action: "상품자료를 확인해 갱신 주기와 갱신 시 보험료가 인상될 수 있음을 함께 표시하세요.",
    }),
    freeze({
      id: "FCPA-22-REFUND", source: "fcpa22", status: "needs_disclosure",
      terms: freeze(["만기환급", "만기 환급", "환급률", "해약환급금", "해지환급금"]),
      message: "환급금이 확정되거나 납입보험료 전액이 반환되는 것처럼 오인시킬 수 있습니다.",
      action: "환급금 변동·미지급 가능성과 산출 기준을 상품자료에 맞춰 표시하세요.",
    }),
    freeze({
      id: "SUPERVISION-19-PROMOTION", source: "supervision17to19", status: "needs_evidence",
      terms: freeze(["증정", "경품", "사은품", "기프티콘", "상품권"]),
      message: "판매촉진 혜택은 제공 조건·가액과 허용 범위를 확인해야 합니다.",
      action: "제공 대상, 기간, 조건, 가액과 보험업법령상 허용 범위를 준법 담당자가 확인하게 하세요.",
    }),
    freeze({
      id: "FCPA-22-PRODUCT-CLAIM", source: "fcpa22", status: "manual_review",
      patterns: freeze([/(?:보장|보험금|진단비|치료비|의료비|배상책임|면책|감액|한도|보험료)/g]),
      message: "상품의 권리·의무에 관한 표현은 최신 상품자료·약관과 일치하는지 사람 확인이 필요합니다.",
      action: "상품명, 가입 조건, 지급사유, 지급제한과 랜딩 내용을 최신 승인 자료에 대조하세요.",
    }),
    freeze({
      id: "KNIA-CHANNEL-MATCH", source: "knia", status: "manual_review",
      terms: freeze(["다이렉트", "온라인보험", "인터넷보험"]),
      message: "판매채널 표현과 실제 가입 경로·상품 기초서류의 일치 여부를 확인해야 합니다.",
      action: "광고주체, 상품명, 판매채널과 랜딩의 가입 경로를 협회 제출 전 대조하세요.",
    }),
  ]);

  const compact = (value) => String(value == null ? "" : value).replace(/\s+/g, "").toLowerCase();
  const uniq = (values) => [...new Set(values)];
  function matchedValues(rule, text) {
    const flat = compact(text);
    const terms = (rule.terms || []).filter((term) => flat.includes(compact(term)));
    const patterns = (rule.patterns || []).flatMap((pattern) => {
      const flags = pattern.flags.includes("g") ? pattern.flags : `${pattern.flags}g`;
      return [...String(text).matchAll(new RegExp(pattern.source, flags))].map((match) => match[0]);
    });
    return uniq([...terms, ...patterns]);
  }
  function review(text, context) {
    const value = String(text == null ? "" : text);
    const findings = [];
    for (const rule of RULES) {
      const matches = matchedValues(rule, value);
      if (!matches.length) continue;
      findings.push(freeze({
        ruleId: rule.id, source: rule.source, sourceLabel: SOURCES[rule.source].label, sourceUrl: SOURCES[rule.source].url,
        status: rule.status, statusLabel: LABELS[rule.status], matches: freeze(matches), message: rule.message, action: rule.action,
        generationBlocking: PRIORITY[rule.status] >= PRIORITY.needs_disclosure,
      }));
    }
    const status = findings.reduce((current, finding) => PRIORITY[finding.status] > PRIORITY[current] ? finding.status : current, "auto_clear");
    return freeze({text: value, channel: String(context?.channel || "unspecified"), status, statusLabel: LABELS[status], findings: freeze(findings), generationBlocking: findings.some((finding) => finding.generationBlocking), disclaimer: "자동 사전검수 결과이며 손해보험협회·준법감시인의 승인 또는 심의 결과가 아닙니다."});
  }
  function reviewFields(fields, context) {
    const findings = [];
    for (const [field, value] of Object.entries(fields || {})) {
      for (const finding of review(value, context).findings) findings.push(freeze({...finding, field}));
    }
    const status = findings.reduce((current, finding) => PRIORITY[finding.status] > PRIORITY[current] ? finding.status : current, "auto_clear");
    return freeze({status, statusLabel: LABELS[status], findings: freeze(findings), generationBlocking: findings.some((finding) => finding.generationBlocking), disclaimer: "자동 사전검수 결과이며 손해보험협회·준법감시인의 승인 또는 심의 결과가 아닙니다."});
  }

  root.ModooInsuranceAdReview = freeze({verifiedAt: SOURCES.verifiedAt, sources: SOURCES, labels: LABELS, rules: RULES, review, reviewFields});
})(globalThis);
