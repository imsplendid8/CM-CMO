(function () {
  "use strict";
  function endpoint() {
    var meta = document.querySelector('meta[name="modoo-feedback-endpoint"]');
    return ((meta && meta.content) || "").trim().replace(/\/+$/, "");
  }
  function hex(bytes) {
    return Array.prototype.map.call(new Uint8Array(bytes), function (value) {
      return value.toString(16).padStart(2, "0");
    }).join("");
  }
  function hash(value) {
    return crypto.subtle.digest("SHA-256", new TextEncoder().encode(String(value))).then(hex);
  }

  function record(event) {
    var base = endpoint();
    if (!base) return Promise.resolve({ sent: false, reason: "feedback endpoint not configured" });
    var payload = Object.assign({}, event);
    var prepared = payload.text ? hash(payload.text).then(function (fingerprint) {
      payload.textFingerprint = fingerprint;
      delete payload.text;
    }) : Promise.resolve();
    return prepared.then(function () {
      payload.schemaVersion = 1;
      payload.occurredAt = new Date().toISOString();
      payload.sourcePage = location.pathname.split("/").pop() || "index.html";
      return fetch(base + "/v1/feedback", {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
    }).then(function (response) {
      if (!response.ok) throw new Error("feedback " + response.status);
      return { sent: true };
    });
  }

  window.ModooFeedback = Object.freeze({ configured: function () { return !!endpoint(); }, record: record });
}());
