/* UI-only tab selection. Does not change any expediente data. */
(function () {
  "use strict";
  const links = Array.from(document.querySelectorAll("[data-cg-tab]"));
  if (!links.length) return;
  const valid = new Set(["resumen", "ruta", "actividades", "documentos", "instituciones", "historial"]);
  function activate(name) {
    if (!valid.has(name)) name = "resumen";
    document.querySelectorAll(".cg-tab-panel").forEach(el => { el.hidden = el.id !== "cg-tab-" + name; });
    document.querySelectorAll(".cg-tabs [data-cg-tab]").forEach(el => {
      const selected = el.dataset.cgTab === name;
      el.classList.toggle("active", selected);
      if (selected) el.setAttribute("aria-current", "page");
      else el.removeAttribute("aria-current");
    });
  }
  links.forEach(el => el.addEventListener("click", function () {
    const name = el.dataset.cgTab;
    if (valid.has(name)) activate(name);
  }));
  function sync() { activate(location.hash.slice(1)); }
  window.addEventListener("hashchange", sync);
  sync();
})();
