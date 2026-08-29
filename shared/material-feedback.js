(function () {
  "use strict";
  var STORAGE_KEY = "modoo_material_review_lab_v1";
  var ACTIONS = ["accepted", "edit_requested", "rejected", "compliance_review"];
  var REASONS = {
    accepted: "사용 가능",
    edit_requested: "수정 필요",
    rejected: "사용 불가",
    compliance_review: "상품·준법 검토 필요",
    ai_template_tone: "AI 템플릿 말투",
    unusable_search_ad_tone: "실제 SA 운영문구로 부자연스러움",
    product_mismatch: "보험종목/담보 정합성 오류",
    season_mismatch: "선택월 시즌 부적합",
    serp_gap: "SERP 관측과 연결 부족",
    image_product_mismatch: "이미지 상품 혼합",
    repeated_material: "같은 내용 반복",
  };
  function safeParse(value, fallback) {
    try { return JSON.parse(value); } catch (_) { return fallback; }
  }
  function load() {
    var data = safeParse(localStorage.getItem(STORAGE_KEY), null);
    if (!data || data.schema_version !== 1) data = { schema_version: 1, updated_at: "", reviews: [] };
    data.reviews = Array.isArray(data.reviews) ? data.reviews : [];
    return data;
  }
  function save(data) {
    data.updated_at = new Date().toISOString();
    localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
    return data;
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
  function addReview(input) {
    var text = normalizeText(input.text);
    var item = {
      id: input.id || "review-" + Date.now().toString(36) + "-" + Math.random().toString(36).slice(2, 7),
      occurred_at: new Date().toISOString(),
      tool: input.tool || "material-admin",
      channel: input.channel || "unknown",
      product_key: input.product_key || "",
      product_name: input.product_name || "",
      recommendation_id: input.recommendation_id || "",
      action: ACTIONS.includes(input.action) ? input.action : "edit_requested",
      reason_code: input.reason_code || "edit_requested",
      reason_label: REASONS[input.reason_code] || input.reason_code || REASONS.edit_requested,
      text_fingerprint: input.text_fingerprint || fingerprint(text),
      text_preview: text.slice(0, 120),
      asset: input.asset || "",
      note: normalizeText(input.note),
    };
    var data = load();
    data.reviews.unshift(item);
    data.reviews = data.reviews.slice(0, 500);
    save(data);
    return item;
  }
  function clear() {
    localStorage.removeItem(STORAGE_KEY);
  }
  function stats(data) {
    var rows = (data || load()).reviews || [];
    var byAction = {}, byReason = {}, byProduct = {};
    rows.forEach(function (row) {
      byAction[row.action] = (byAction[row.action] || 0) + 1;
      byReason[row.reason_code] = (byReason[row.reason_code] || 0) + 1;
      if (row.product_key) byProduct[row.product_key] = (byProduct[row.product_key] || 0) + 1;
    });
    return { total: rows.length, byAction: byAction, byReason: byReason, byProduct: byProduct };
  }
  function exportRules() {
    var data = load();
    var rejected = data.reviews.filter(function (row) { return row.action === "rejected" || row.action === "edit_requested"; });
    var phrases = rejected.filter(function (row) {
      return row.reason_code === "ai_template_tone" || row.reason_code === "unusable_search_ad_tone" || row.reason_code === "repeated_material";
    }).map(function (row) { return row.text_preview; }).filter(Boolean);
    var assets = rejected.filter(function (row) {
      return row.reason_code === "image_product_mismatch" && row.asset;
    }).map(function (row) { return { product_key: row.product_key, asset: row.asset, reason_code: row.reason_code }; });
    return {
      schema_version: 1,
      exported_at: new Date().toISOString(),
      source: "local_material_review_lab",
      blocked_phrases: Array.from(new Set(phrases)),
      rejected_assets: assets,
      reason_counts: stats(data).byReason,
    };
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
    storageKey: STORAGE_KEY, reasons: REASONS, load: load, save: save, clear: clear,
    addReview: addReview, fingerprint: fingerprint, stats: stats, exportRules: exportRules, download: download,
  });
}());
