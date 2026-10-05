/** Descripción desplegable de cada oferta: se pide al servidor solo al abrirla y se recuerda. */

import { fetchDescription } from "./api.js";
import { spinnerHtml } from "./dom.js";
import { highlight } from "./render.js";

export function bindDescriptions(list, getHighlightedTechs) {
  const cache = new Map();

  list.addEventListener("click", async (event) => {
    const button = event.target.closest(".toggle-description");
    if (!button) return;
    const card = button.closest(".job");
    const box = card.querySelector(".description");
    const id = card.dataset.id;

    if (!box.hidden) {
      box.hidden = true;
      button.textContent = "Ver descripción";
      return;
    }
    box.hidden = false;
    button.textContent = "Ocultar descripción";

    if (!cache.has(id)) {
      box.innerHTML = spinnerHtml("Cargando descripción...");
      try {
        cache.set(id, await fetchDescription(id));
      } catch {
        box.textContent = "No se pudo cargar la descripción.";
        return;
      }
    }
    box.innerHTML = highlight(cache.get(id), getHighlightedTechs()) || "Sin descripción.";
  });
}
