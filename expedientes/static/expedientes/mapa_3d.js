(function () {
  "use strict";
  const root = document.getElementById("mapa-movilidad");
  if (!root) return;
  const nodes = Array.from(root.querySelectorAll("[data-estacion]"));
  const cards = Array.from(document.querySelectorAll(".mov3d-activity"));
  const title = document.getElementById("mov3d-selected");
  const empty = document.getElementById("mov3d-empty-stage");
  const all = document.getElementById("mov3d-show-all");
  const context = document.getElementById("mov3d-stage-context");
  const isCancelled = !!root.querySelector(".is-cancelled");
  const descriptions = {
    recorrida: "Etapa anterior: existe avance registrado, pero esto no acredita que todas sus actividades se completaran.",
    actual: "Esta es la etapa actual del expediente.",
    futura: "Etapa futura: las actividades registradas son informativas; no significa que el expediente haya llegado aquí.",
    cancelada: "Expediente cancelado: recorrido disponible solo para consulta."
  };
  function select(code, label, situation) {
    nodes.forEach(node => node.setAttribute("aria-pressed", String(node.dataset.estacion === code)));
    let visible = 0;
    cards.forEach(card => {
      const show = card.dataset.etapa === code;
      card.hidden = !show;
      if (show) visible++;
    });
    if (empty) empty.hidden = visible !== 0;
    if (title) title.textContent = label;
    if (context) context.textContent = isCancelled ? descriptions.cancelada : (descriptions[situation] || "Etapa consultada.");
    if (all) all.hidden = false;
  }
  nodes.forEach(node => node.addEventListener("click", () => select(node.dataset.estacion, node.dataset.nombre, node.dataset.situacion)));
  if (all) all.addEventListener("click", () => {
    nodes.forEach(node => node.setAttribute("aria-pressed", "false"));
    cards.forEach(card => { card.hidden = false; });
    if (empty) empty.hidden = true;
    if (title) title.textContent = "Todas las etapas";
    if (context) context.textContent = "Se muestran todas las actividades registradas. El estado real del expediente no cambia.";
    all.hidden = true;
  });
  // El estudiante ve inicialmente todas las actividades, preservando la
  // funcionalidad existente. Elegir una estación activa el filtro.
})();
