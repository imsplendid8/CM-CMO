(() => {
  "use strict";
  const init = () => {
    const sidebar = document.querySelector(".sidebar");
    if (!sidebar || document.querySelector(".mobile-sidebar-toggle")) return;
    if (!sidebar.id) sidebar.id = "toolSidebar";

    const button = document.createElement("button");
    button.type = "button";
    button.className = "mobile-sidebar-toggle";
    button.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="M4 7h16M4 12h16M4 17h16"/></svg><span>상품·보기</span>';
    button.setAttribute("aria-label", "상품과 화면 메뉴 열기");
    button.setAttribute("aria-controls", sidebar.id);
    button.setAttribute("aria-expanded", "false");

    const mask = document.createElement("div");
    mask.className = "mobile-sidebar-mask";
    mask.setAttribute("aria-hidden", "true");
    document.body.append(mask, button);

    const setOpen = (open) => {
      sidebar.classList.toggle("mobile-open", open);
      mask.classList.toggle("on", open);
      document.body.classList.toggle("mobile-sidebar-open", open);
      button.setAttribute("aria-expanded", open ? "true" : "false");
      button.setAttribute("aria-label", open ? "상품과 화면 메뉴 닫기" : "상품과 화면 메뉴 열기");
    };

    button.addEventListener("click", () => setOpen(!sidebar.classList.contains("mobile-open")));
    mask.addEventListener("click", () => setOpen(false));
    sidebar.addEventListener("click", (event) => {
      if (matchMedia("(max-width:820px)").matches && event.target.closest("a,button,[data-key]")) setOpen(false);
    });
    addEventListener("keydown", (event) => { if (event.key === "Escape") setOpen(false); });
    matchMedia("(min-width:821px)").addEventListener?.("change", (event) => { if (event.matches) setOpen(false); });
  };
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init, { once: true });
  else init();
})();
