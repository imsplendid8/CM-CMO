(() => {
  "use strict";

  const svg = (paths, className = "ui-icon") => `<svg class="${className}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${paths}</svg>`;
  const ICONS = {
    home: svg('<path d="M3.5 10.5 12 3.8l8.5 6.7"/><path d="M5.5 9v11h13V9"/><path d="M9.5 20v-5.5h5V20"/>'),
    seo: svg('<path d="M4 7h16M4 17h16"/><circle cx="9" cy="7" r="2.2"/><circle cx="15" cy="17" r="2.2"/>'),
    keyword: svg('<circle cx="10.8" cy="10.8" r="6.6"/><path d="m16 16 4.5 4.5"/><path d="M8 11h5.5M10.8 8.2v5.6"/>'),
    news: svg('<path d="M4.5 4.5h13v15h-11a2 2 0 0 1-2-2z"/><path d="M17.5 8.5H20v9a2 2 0 0 1-2 2"/><path d="M8 9h6M8 12.5h6M8 16h4"/>'),
    serp: svg('<rect x="3" y="4" width="18" height="13" rx="2.5"/><path d="M8 21h8M12 17v4"/><path d="m8 11 2.4 2.2L16 8"/>'),
    calendar: svg('<rect x="3.5" y="5" width="17" height="15.5" rx="2.5"/><path d="M3.5 9.5h17M8 3.5v3M16 3.5v3"/><path d="M8 13h3M13 13h3M8 16.5h3"/>'),
    adcopy: svg('<path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4z"/>'),
    power: svg('<path d="M5 3.5h10l4 4V20.5H5z"/><path d="M15 3.5v4h4M8.5 12h7M8.5 15.5h5"/><path d="m17.5 14.5 1 2 2 .8-2 1-1 2-1-2-2-1 2-.8z"/>'),
    overview: svg('<rect x="3.5" y="3.5" width="17" height="17" rx="2.5"/><path d="M3.5 9h17M9 9v11.5"/>'),
    search: svg('<circle cx="10.8" cy="10.8" r="6.6"/><path d="m16 16 4.5 4.5"/>'),
    menu: svg('<path d="M4 7h16M4 12h16M4 17h16"/>'),
    tag: svg('<path d="M20 13 13 20l-9-9V4h7z"/><circle cx="8.5" cy="8.5" r="1.2"/>'),
    archive: svg('<path d="M3.5 7.5h17v12h-17zM2.5 4h19v3.5h-19zM9 12h6"/>'),
    signal: svg('<path d="M3 12h3l2.2-6 4.2 12 2.4-6H21"/>'),
    camera: svg('<rect x="3" y="6.5" width="18" height="13" rx="2.5"/><path d="m8 6.5 1.2-2h5.6l1.2 2"/><circle cx="12" cy="13" r="3.2"/>'),
    lock: svg('<rect x="4.5" y="10" width="15" height="10.5" rx="2.5"/><path d="M8 10V7a4 4 0 0 1 8 0v3M12 14v2.5"/>'),
    architecture: svg('<rect x="9" y="3" width="6" height="5" rx="1"/><rect x="3" y="16" width="6" height="5" rx="1"/><rect x="15" y="16" width="6" height="5" rx="1"/><path d="M12 8v4M6 16v-4h12v4"/>'),
    compass: svg('<circle cx="12" cy="12" r="9"/><path d="m15.5 8.5-2 5-5 2 2-5z"/>'),
    plug: svg('<path d="m8 3 1.5 4M16 3l-1.5 4M7 7h10v2a5 5 0 0 1-5 5v0a5 5 0 0 1-5-5zM12 14v7"/>'),
    package: svg('<path d="m12 3 8.5 4.5v9L12 21l-8.5-4.5v-9zM3.5 7.5 12 12l8.5-4.5M12 12v9M8 5l8.5 4.5"/>'),
    list: svg('<path d="M9 6h11M9 12h11M9 18h11"/><path d="m4 6 .8.8L6.5 5M4 12l.8.8L6.5 11M4 18l.8.8 1.7-1.8"/>'),
    bot: svg('<rect x="4" y="7" width="16" height="12" rx="3"/><path d="M12 3v4M9 12h.01M15 12h.01M8 16h8"/>'),
    code: svg('<path d="m8.5 8-4 4 4 4M15.5 8l4 4-4 4M14 5l-4 14"/>'),
    globe: svg('<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c2.3 2.5 3.5 5.5 3.5 9S14.3 18.5 12 21M12 3c-2.3 2.5-3.5 5.5-3.5 9S9.7 18.5 12 21"/>'),
    settings: svg('<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.9l.1.1-2.8 2.8-.1-.1a1.7 1.7 0 0 0-1.9-.3 1.7 1.7 0 0 0-1 1.6v.2h-4V21a1.7 1.7 0 0 0-1-1.6 1.7 1.7 0 0 0-1.9.3l-.1.1L4.2 17l.1-.1a1.7 1.7 0 0 0 .3-1.9A1.7 1.7 0 0 0 3 14H2.8v-4H3a1.7 1.7 0 0 0 1.6-1 1.7 1.7 0 0 0-.3-1.9L4.2 7 7 4.2l.1.1A1.7 1.7 0 0 0 9 4.6a1.7 1.7 0 0 0 1-1.6v-.2h4V3a1.7 1.7 0 0 0 1 1.6 1.7 1.7 0 0 0 1.9-.3l.1-.1L19.8 7l-.1.1a1.7 1.7 0 0 0-.3 1.9 1.7 1.7 0 0 0 1.6 1h.2v4H21a1.7 1.7 0 0 0-1.6 1z"/>'),
    sun: svg('<circle cx="12" cy="12" r="3.5"/><path d="M12 2.5v2M12 19.5v2M2.5 12h2M19.5 12h2M5.3 5.3l1.4 1.4M17.3 17.3l1.4 1.4M18.7 5.3l-1.4 1.4M6.7 17.3l-1.4 1.4"/>'),
    moon: svg('<path d="M20.5 15.2A8.2 8.2 0 0 1 8.8 3.5 8.5 8.5 0 1 0 20.5 15.2z"/>'),
  };
  const PAGE_ICON = {
    "seo-audit.html": "seo",
    "keyword-tool.html": "keyword",
    "news-tool.html": "news",
    "serp-tool.html": "serp",
    "seasonal-tool.html": "calendar",
    "adcopy-tool.html": "adcopy",
    "powercontent-tool.html": "power",
    "overview.html": "overview",
  };
  const page = location.pathname.split("/").pop() || "index.html";

  function setIcon(element, name) {
    if (!element || !ICONS[name]) return;
    element.innerHTML = ICONS[name];
    element.dataset.uiIconReady = name;
  }

  function updateThemeIcon() {
    const dark = document.documentElement.getAttribute("data-theme") === "dark" ||
      (!document.documentElement.hasAttribute("data-theme") && matchMedia("(prefers-color-scheme:dark)").matches);
    document.querySelectorAll("#themeBtn").forEach((button) => {
      setIcon(button, dark ? "sun" : "moon");
      const label = dark ? "라이트 모드로 전환" : "다크 모드로 전환";
      button.setAttribute("aria-label", label);
      button.title = label;
    });
  }

  function enhanceChrome() {
    const pageIcon = PAGE_ICON[page];
    if (pageIcon) document.querySelectorAll(".brand-logo").forEach((element) => setIcon(element, pageIcon));

    document.querySelectorAll(".crumb[href*='index.html']").forEach((link) => {
      link.innerHTML = `<span class="ui-inline-icon">${ICONS.home}</span><span>콘솔</span>`;
      link.setAttribute("aria-label", "Modoo 통합 콘솔로 이동");
    });

    document.querySelectorAll(".search").forEach((box) => {
      [...box.childNodes].filter((node) => node.nodeType === Node.TEXT_NODE && node.textContent.trim()).forEach((node) => node.remove());
      if (!box.querySelector(".ui-search-icon")) {
        const icon = document.createElement("span");
        icon.className = "ui-search-icon";
        icon.innerHTML = ICONS.search;
        box.prepend(icon);
      }
    });

    if (page === "overview.html") {
      const routeIcons = {
        "seo-audit.html": "seo", "keyword-tool.html": "keyword", "news-tool.html": "news", "serp-tool.html": "serp",
        "seasonal-tool.html": "calendar", "adcopy-tool.html": "adcopy", "powercontent-tool.html": "power",
      };
      const titleIcons = [
        [/브랜드검색/, "tag"], [/클리핑/, "archive"], [/수요 신호/, "signal"], [/SERP 캡쳐/, "camera"], [/보안 설정/, "lock"],
        [/아키텍처/, "architecture"], [/로드맵/, "compass"], [/API/, "plug"], [/OSS/, "package"], [/상태/, "list"],
        [/프로젝트 가이드/, "bot"], [/GitHub 저장소/, "code"], [/배포 대시보드/, "globe"], [/Actions/, "settings"], [/위키/, "overview"],
      ];
      document.querySelectorAll("a.card").forEach((card) => {
        const href = (card.getAttribute("href") || "").split("#")[0];
        const title = card.querySelector(".t")?.textContent || "";
        const name = routeIcons[href] || titleIcons.find(([pattern]) => pattern.test(title))?.[1] || "overview";
        setIcon(card.querySelector(".ic"), name);
      });
      const homeLink = document.querySelector('.hb[href="index.html"]');
      if (homeLink) homeLink.innerHTML = `<span class="ui-inline-icon">${ICONS.home}</span><span>통합 콘솔</span>`;
    }

    const target = document.querySelector(".content,#home,.wrap,main");
    if (target && !document.querySelector(".ui-skip")) {
      if (!target.id) target.id = "main-content";
      const skip = document.createElement("a");
      skip.className = "ui-skip";
      skip.href = `#${target.id}`;
      skip.textContent = "본문으로 건너뛰기";
      document.body.prepend(skip);
    }
    updateThemeIcon();
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", enhanceChrome, { once: true });
  else enhanceChrome();

  new MutationObserver(updateThemeIcon).observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
  window.ModooIcons = { icon: (name) => ICONS[name] || "", setIcon };
})();
