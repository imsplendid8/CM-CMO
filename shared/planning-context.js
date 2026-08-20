(function () {
  "use strict";

  const STORAGE_KEY = "cm_cmo_plan_month";

  function parseMonth(value) {
    const match = String(value == null ? "" : value).match(/(?:^|-)\s*(\d{1,2})$/);
    const month = match ? Number(match[1]) : Number(value);
    return Number.isInteger(month) && month >= 1 && month <= 12 ? month : null;
  }

  function queryMonth() {
    try {
      return parseMonth(new URLSearchParams(location.search).get("month"));
    } catch (_) {
      return null;
    }
  }

  function storedMonth() {
    try {
      return parseMonth(localStorage.getItem(STORAGE_KEY));
    } catch (_) {
      return null;
    }
  }

  function getMonth() {
    return queryMonth() || storedMonth() || new Date().getMonth() + 1;
  }

  function setMonth(value, syncUrl) {
    const month = parseMonth(value);
    if (!month) return getMonth();
    try {
      localStorage.setItem(STORAGE_KEY, String(month));
    } catch (_) {}
    if (syncUrl !== false) {
      try {
        const url = new URL(location.href);
        url.searchParams.set("month", String(month));
        history.replaceState(null, "", url.pathname + url.search + url.hash);
      } catch (_) {}
    }
    return month;
  }

  function nextMonth(month) {
    const parsed = parseMonth(month) || getMonth();
    return parsed % 12 + 1;
  }

  function optionMarkup(selected) {
    const month = parseMonth(selected) || getMonth();
    return Array.from({ length: 12 }, (_, index) => {
      const value = index + 1;
      return `<option value="${value}"${value === month ? " selected" : ""}>${value}월</option>`;
    }).join("");
  }

  window.ModooPlanning = { STORAGE_KEY, parseMonth, getMonth, setMonth, nextMonth, optionMarkup };
})();
