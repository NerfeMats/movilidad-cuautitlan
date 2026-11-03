/* Consulta de estaciones: no altera la etapa real ni realiza peticiones. */
(() => {
  "use strict";
  const root = document.getElementById("ruta-responsable");
  if (!root) return;
  const stations = [...root.querySelectorAll("[data-target]")];
  const panels = stations.map(station => document.getElementById(station.dataset.target));
  stations.forEach((station, selectedIndex) => {
    station.addEventListener("click", () => {
      stations.forEach((item, index) => {
        const selected = index === selectedIndex;
        item.setAttribute("aria-pressed", String(selected));
        if (panels[index]) panels[index].hidden = !selected;
      });
    });
  });
})();
