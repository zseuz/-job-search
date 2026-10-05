/**
 * Selector de tecnologías con tres estados:
 *   clic        -> incluir (azul)
 *   doble clic  -> excluir (rojo y tachado)
 *   otro clic   -> quitar
 */

import { escapeHtml } from "./dom.js";

const CLICK_DELAY_MS = 220; // se espera por si el clic es en realidad el primero de un doble clic

export function createTechPicker(container, groups) {
  const included = new Set();
  const excluded = new Set();
  const chips = new Map(); // tecnología -> botón
  let pendingClick = null;

  function paint(tech) {
    const chip = chips.get(tech);
    if (!chip) return;
    chip.classList.toggle("is-included", included.has(tech));
    chip.classList.toggle("is-excluded", excluded.has(tech));
  }

  function setState(tech, state) {
    included.delete(tech);
    excluded.delete(tech);
    if (state === "included") included.add(tech);
    if (state === "excluded") excluded.add(tech);
    paint(tech);
  }

  function render(counts = {}) {
    container.innerHTML = Object.entries(groups)
      .map(
        ([group, techs]) =>
          `<div class="tech-group-title">${escapeHtml(group)}</div><div class="tech-list">` +
          techs
            .map(
              (tech) =>
                `<button type="button" class="tech-chip" data-tech="${escapeHtml(tech)}">` +
                `${escapeHtml(tech)} <small>${counts[tech] || 0}</small></button>`,
            )
            .join("") +
          "</div>",
      )
      .join("");
    chips.clear();
    container.querySelectorAll(".tech-chip").forEach((chip) => chips.set(chip.dataset.tech, chip));
    [...included, ...excluded].forEach(paint);
  }

  container.addEventListener("click", (event) => {
    const chip = event.target.closest(".tech-chip");
    if (!chip) return;
    const tech = chip.dataset.tech;
    clearTimeout(pendingClick);
    pendingClick = setTimeout(
      () => setState(tech, included.has(tech) || excluded.has(tech) ? "none" : "included"),
      CLICK_DELAY_MS,
    );
  });

  container.addEventListener("dblclick", (event) => {
    const chip = event.target.closest(".tech-chip");
    if (!chip) return;
    clearTimeout(pendingClick);
    setState(chip.dataset.tech, excluded.has(chip.dataset.tech) ? "none" : "excluded");
  });

  return {
    render,
    selection: () => ({ included: [...included], excluded: [...excluded] }),
    clear() {
      const all = [...included, ...excluded];
      included.clear();
      excluded.clear();
      all.forEach(paint);
    },
  };
}
