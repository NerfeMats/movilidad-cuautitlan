(function () {
  "use strict";
  const root = document.getElementById("mapa-movilidad");
  if (!root) return;
  const nodes = Array.from(root.querySelectorAll("[data-estacion]"));
  const cards = Array.from(document.querySelectorAll(".mov3d-activity"));
  const title = document.getElementById("mov3d-selected");
  const empty = document.getElementById("mov3d-empty-stage");
  const all = document.getElementById("mov3d-show-all");
  function select(code, label) {
    nodes.forEach(node => node.setAttribute("aria-pressed", String(node.dataset.estacion === code)));
    let visible = 0;
    cards.forEach(card => {
      const show = card.dataset.etapa === code;
      card.hidden = !show;
      if (show) visible++;
    });
    if (empty) empty.hidden = visible !== 0;
    if (title) title.textContent = label;
    if (all) all.hidden = false;
  }
  nodes.forEach(node => node.addEventListener("click", () => select(node.dataset.estacion, node.dataset.nombre)));
  if (all) all.addEventListener("click", () => {
    nodes.forEach(node => node.setAttribute("aria-pressed", "false"));
    cards.forEach(card => { card.hidden = false; });
    if (empty) empty.hidden = true;
    if (title) title.textContent = "Todas las etapas";
    all.hidden = true;
  });
  // El estudiante ve inicialmente todas las actividades, preservando la
  // funcionalidad existente. Elegir una estación activa el filtro.
})();
