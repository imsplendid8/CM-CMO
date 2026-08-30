(function () {
  "use strict";
  var STORAGE_KEY = "modoo_material_review_lab_v1";
  var SCHEMA_VERSION = 2;
  var ACTIONS = ["accepted", "edit_requested", "rejected", "compliance_review"];
  var ACTION_LABELS = {
    accepted: "사용 가능",
    edit_requested: "수정 필요",
    rejected: "사용 불가",
    compliance_review: "상품·준법 검토 필요",
  };
  var REASONS = {
    ai_template_tone: "AI 템플릿 말투",
    unusable_search_ad_tone: "실제 SA 운영문구로 부자연스러움",
    product_mismatch: "보험종목/담보 정합성 오류",
    season_mismatch: "선택월 시즌 부적합",
    serp_gap: "SERP 관측과 연결 부족",
    image_product_mismatch: "이미지 상품 혼합",
    repeated_material: "같은 내용 반복",
    unsupported_claim: "근거 없는 단정·혜택 표현",
    naver_limit_violation: "네이버 소재 제한 위반",
    thin_editorial_value: "발행 콘텐츠로 정보 가치 부족",
    image_missing: "검수할 이미지 파일 없음",
    style_drift: "이미지 스타일 불일치",
    compliance_review: "상품·준법 검토 필요",
  };

  function safeParse(value, fallback) {
    try { return JSON.parse(value); } catch (_) { return fallback; }
  }
  function normalizeText(value) {
    return String(value || "").replace(/\s+/g, " ").trim();
  }
  function fingerprint(value) {
    var text = normalizeText(value);
    var hash = 2166136261;
    for (var i = 0; i < text.length; i += 1) {
      hash ^= text.charCodeAt(i);
      hash = Math.imul(hash, 16777619);
    }
    return (hash >>> 0).toString(16).padStart(8, "0");
  }
  function uid(prefix) {
    return (prefix || "item") + "-" + Date.now().toString(36) + "-" + Math.random().toString(36).slice(2, 8);
  }
  function normalizeFields(fields) {
    var result = {};
    if (!fields || typeof fields !== "object" || Array.isArray(fields)) return result;
    Object.keys(fields).forEach(function (key) {
      var value = fields[key];
      if (Array.isArray(value)) result[key] = value.map(normalizeText).filter(Boolean).slice(0, 20);
      else result[key] = String(value || "").trim().slice(0, 12000);
    });
    return result;
  }
  function materialText(row) {
    var fields = normalizeFields(row.fields);
    var values = [row.title, row.text];
    Object.keys(fields).forEach(function (key) {
      values.push(Array.isArray(fields[key]) ? fields[key].join(" · ") : fields[key]);
    });
    return values.filter(Boolean).join("\n").trim();
  }
  function normalizeMaterial(row) {
    if (!row || typeof row !== "object") return null;
    var fields = normalizeFields(row.fields);
    var title = String(row.title || fields.title || fields.headline || "제목 없는 소재").trim().slice(0, 300);
    var item = {
      id: row.id || uid("material"),
      created_at: row.created_at || new Date().toISOString(),
      updated_at: row.updated_at || row.created_at || new Date().toISOString(),
      source: row.source || "operator_upload",
      channel: ["search_ad", "power_content", "thumbnail"].includes(row.channel) ? row.channel : "search_ad",
      product_key: normalizeText(row.product_key),
      product_name: normalizeText(row.product_name),
      planning_month: /^\d{4}-\d{2}$/.test(String(row.planning_month || "")) ? row.planning_month : "",
      title: title,
      text: String(row.text || "").trim().slice(0, 20000),
      fields: fields,
      asset: String(row.asset || "").trim().slice(0, 1800000),
      asset_name: normalizeText(row.asset_name),
      asset_type: normalizeText(row.asset_type),
      note: String(row.note || "").trim().slice(0, 4000),
      status: row.status || "pending",
    };
    item.text_fingerprint = row.text_fingerprint || fingerprint(materialText(item));
    return item;
  }
  function normalizeReview(row) {
    if (!row || typeof row !== "object") return null;
    var action = ACTIONS.includes(row.action) ? row.action : "edit_requested";
    var reason = row.reason_code || (action === "compliance_review" ? "compliance_review" : "ai_template_tone");
    return {
      id: row.id || uid("review"),
      item_id: row.item_id || row.recommendation_id || "",
      occurred_at: row.occurred_at || new Date().toISOString(),
      tool: row.tool || "material-admin",
      channel: row.channel || "unknown",
      product_key: row.product_key || "",
      product_name: row.product_name || "",
      recommendation_id: row.recommendation_id || row.item_id || "",
      action: action,
      action_label: row.action_label || ACTION_LABELS[action] || action,
      reason_code: reason,
      reason_label: row.reason_label || REASONS[reason] || reason,
      text_fingerprint: row.text_fingerprint || fingerprint(row.focus_text || row.text_preview || row.text || ""),
      text_preview: normalizeText(row.focus_text || row.text_preview || row.text || "").slice(0, 240),
      asset: row.asset || "",
      note: normalizeText(row.note).slice(0, 1200),
      replacement_direction: normalizeText(row.replacement_direction || row.note).slice(0, 1200),
    };
  }
  function emptyState() {
    return { schema_version: SCHEMA_VERSION, updated_at: "", reviews: [], materials: [], agent_requests: [] };
  }
  function load() {
    var raw = safeParse(localStorage.getItem(STORAGE_KEY), null);
    var data = raw && typeof raw === "object" ? raw : emptyState();
    data.schema_version = SCHEMA_VERSION;
    data.reviews = (Array.isArray(data.reviews) ? data.reviews : []).map(normalizeReview).filter(Boolean);
    data.materials = (Array.isArray(data.materials) ? data.materials : []).map(normalizeMaterial).filter(Boolean);
    data.agent_requests = Array.isArray(data.agent_requests) ? data.agent_requests.slice(0, 100) : [];
    return data;
  }
  function save(data) {
    data.schema_version = SCHEMA_VERSION;
    data.updated_at = new Date().toISOString();
    localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
    return data;
  }
  function addMaterial(input) {
    var item = normalizeMaterial(input);
    if (!item) throw new Error("invalid material");
    var data = load();
    var index = data.materials.findIndex(function (row) { return row.id === item.id; });
    if (index >= 0) data.materials[index] = item;
    else data.materials.unshift(item);
    data.materials = data.materials.slice(0, 200);
    save(data);
    return item;
  }
  function removeMaterial(id) {
    var data = load();
    var before = data.materials.length;
    data.materials = data.materials.filter(function (row) { return row.id !== id; });
    data.reviews = data.reviews.filter(function (row) { return row.item_id !== id; });
    save(data);
    return before !== data.materials.length;
  }
  function addReview(input) {
    var text = normalizeText(input.focus_text || input.text);
    var item = normalizeReview({
      id: input.id,
      item_id: input.item_id,
      occurred_at: input.occurred_at,
      tool: input.tool,
      channel: input.channel,
      product_key: input.product_key,
      product_name: input.product_name,
      recommendation_id: input.recommendation_id,
      action: input.action,
      reason_code: input.reason_code,
      reason_label: input.reason_label,
      text_fingerprint: input.text_fingerprint || fingerprint(text),
      focus_text: text.slice(0, 240),
      asset: input.asset || "",
      note: input.note,
      replacement_direction: input.replacement_direction,
    });
    var data = load();
    data.reviews.unshift(item);
    data.reviews = data.reviews.slice(0, 500);
    save(data);
    return item;
  }
  function mergeById(currentRows, incomingRows, normalizer, limit) {
    var map = {};
    currentRows.forEach(function (row) { if (row && row.id) map[row.id] = row; });
    var imported = 0, merged = 0;
    incomingRows.forEach(function (row) {
      var item = normalizer(row);
      if (!item) return;
      imported += 1;
      if (map[item.id]) merged += 1;
      map[item.id] = item;
    });
    return {
      rows: Object.keys(map).map(function (key) { return map[key]; })
        .sort(function (a, b) { return String(b.occurred_at || b.updated_at || b.created_at || "").localeCompare(String(a.occurred_at || a.updated_at || a.created_at || "")); })
        .slice(0, limit),
      imported: imported,
      merged: merged,
    };
  }
  function importBackup(payload) {
    var incoming = payload && typeof payload === "object" ? payload : null;
    if (!incoming) return { imported: 0, merged: 0, reason: "invalid_payload" };
    var current = load();
    var reviewResult = mergeById(current.reviews, Array.isArray(incoming.reviews) ? incoming.reviews : [], normalizeReview, 500);
    var materialRows = Array.isArray(incoming.materials) ? incoming.materials : (Array.isArray(incoming) ? incoming : []);
    var materialResult = mergeById(current.materials, materialRows, normalizeMaterial, 200);
    current.reviews = reviewResult.rows;
    current.materials = materialResult.rows;
    save(current);
    return {
      imported: reviewResult.imported + materialResult.imported,
      merged: reviewResult.merged + materialResult.merged,
      reviews: current.reviews.length,
      materials: current.materials.length,
    };
  }
  function clear() {
    localStorage.removeItem(STORAGE_KEY);
  }
  function stats(data) {
    var state = data || load();
    var rows = state.reviews || [];
    var byAction = {}, byReason = {}, byProduct = {}, failedByProduct = {};
    rows.forEach(function (row) {
      byAction[row.action] = (byAction[row.action] || 0) + 1;
      byReason[row.reason_code] = (byReason[row.reason_code] || 0) + 1;
      if (row.product_key) byProduct[row.product_key] = (byProduct[row.product_key] || 0) + 1;
      if (row.product_key && (row.action === "rejected" || row.action === "edit_requested")) {
        failedByProduct[row.product_key] = (failedByProduct[row.product_key] || 0) + 1;
      }
    });
    return { total: rows.length, materials: (state.materials || []).length, byAction: byAction, byReason: byReason, byProduct: byProduct, failedByProduct: failedByProduct };
  }
  function feedbackPhrases(rows) {
    return rows.map(function (row) { return normalizeText(row.text_preview); }).filter(function (text) { return text.length >= 2 && text.length <= 240; });
  }
  function exportRules(baseRules) {
    var data = load();
    var rejected = data.reviews.filter(function (row) { return row.action === "rejected" || row.action === "edit_requested"; });
    var phraseRows = rejected.filter(function (row) {
      return ["ai_template_tone", "unusable_search_ad_tone", "repeated_material", "thin_editorial_value"].includes(row.reason_code);
    });
    var assets = rejected.filter(function (row) {
      return ["image_product_mismatch", "style_drift", "repeated_material"].includes(row.reason_code) && row.asset && !String(row.asset).startsWith("data:");
    }).map(function (row) { return { product_key: row.product_key, asset: row.asset, reason_code: row.reason_code }; });
    var byChannel = {}, byProductChannel = {}, repeated = {};
    rejected.forEach(function (row) {
      if (!row.channel || !row.text_preview) return;
      if (!byChannel[row.channel]) byChannel[row.channel] = [];
      byChannel[row.channel].push(row.text_preview);
      var productKey = (row.product_key || "all") + ":" + row.channel;
      if (!byProductChannel[productKey]) byProductChannel[productKey] = [];
      byProductChannel[productKey].push(row.text_preview);
      if (row.reason_code === "repeated_material") repeated[row.text_preview] = (repeated[row.text_preview] || 0) + 1;
    });
    function uniqueMap(source) {
      var result = {};
      Object.keys(source).forEach(function (key) { result[key] = Array.from(new Set(source[key])).slice(0, 30); });
      return result;
    }
    var base = baseRules && typeof baseRules === "object" ? baseRules : {};
    return {
      schema_version: 2,
      exported_at: new Date().toISOString(),
      source: "local_material_review_lab",
      copy_replacements: Array.isArray(base.copy_replacements) ? base.copy_replacements : [],
      blocked_phrases: Array.from(new Set([].concat(base.blocked_phrases || [], feedbackPhrases(phraseRows)))),
      blocked_phrases_by_channel: uniqueMap(byChannel),
      blocked_phrases_by_product_channel: uniqueMap(byProductChannel),
      rejected_assets: assets,
      reason_counts: stats(data).byReason,
      repeated_material_top: Object.keys(repeated).sort(function (a, b) { return repeated[b] - repeated[a] || a.localeCompare(b); }).slice(0, 20).map(function (text) { return { text: text, count: repeated[text] }; }),
      channel_reason_counts: Object.entries(rejected.reduce(function (acc, row) {
        var key = (row.channel || "unknown") + ":" + (row.reason_code || "unknown");
        acc[key] = (acc[key] || 0) + 1;
        return acc;
      }, {})).map(function (pair) { return { key: pair[0], count: pair[1] }; }).sort(function (a, b) { return b.count - a.count || a.key.localeCompare(b.key); }).slice(0, 40),
    };
  }
  function exportAgentRequest(baseRules, filters) {
    var data = load();
    var selected = data.materials.filter(function (row) {
      return (!filters || !filters.product_key || row.product_key === filters.product_key) &&
        (!filters || !filters.channel || row.channel === filters.channel);
    });
    var relevantIds = new Set(selected.map(function (row) { return row.id; }));
    var reviews = data.reviews.filter(function (row) {
      return relevantIds.has(row.item_id) ||
        ((!filters || !filters.product_key || row.product_key === filters.product_key) && (!filters || !filters.channel || row.channel === filters.channel));
    });
    var request = {
      schema_version: 1,
      requested_at: new Date().toISOString(),
      source: "material_review_lab",
      task: "regenerate_materials_from_operator_feedback",
      filters: filters || {},
      generation_rules: exportRules(baseRules),
      operator_materials: selected.map(function (row) {
        return { id: row.id, channel: row.channel, product_key: row.product_key, product_name: row.product_name, planning_month: row.planning_month, title: row.title, fields: row.fields, text: row.text, note: row.note, asset_name: row.asset_name };
      }),
      review_decisions: reviews,
      instructions: [
        "구조화된 SERP 텍스트를 우선 근거로 사용한다.",
        "반려 문구를 동의어만 바꿔 반복하지 않는다.",
        "상품·시즌·채널이 일치하는 대안을 만들고 기존 채택 소재와 중복을 검사한다.",
        "자동 검사는 심의 통과로 표현하지 않고 사람 심의 필요 항목을 분리한다.",
      ],
    };
    data.agent_requests.unshift({ id: uid("agent"), created_at: request.requested_at, filters: request.filters, material_count: selected.length, review_count: reviews.length });
    data.agent_requests = data.agent_requests.slice(0, 100);
    save(data);
    return request;
  }
  function download(data, filename) {
    var blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json;charset=utf-8" });
    var url = URL.createObjectURL(blob);
    var link = document.createElement("a");
    link.href = url;
    link.download = filename || "material-review.json";
    document.body.appendChild(link);
    link.click();
    link.remove();
    setTimeout(function () { URL.revokeObjectURL(url); }, 500);
  }

  window.ModooMaterialFeedback = Object.freeze({
    storageKey: STORAGE_KEY,
    schemaVersion: SCHEMA_VERSION,
    reasons: REASONS,
    actions: ACTION_LABELS,
    load: load,
    save: save,
    clear: clear,
    addReview: addReview,
    addMaterial: addMaterial,
    removeMaterial: removeMaterial,
    fingerprint: fingerprint,
    stats: stats,
    exportRules: exportRules,
    exportAgentRequest: exportAgentRequest,
    download: download,
    importBackup: importBackup,
    normalizeReview: normalizeReview,
    normalizeMaterial: normalizeMaterial,
    materialText: materialText,
  });
}());
