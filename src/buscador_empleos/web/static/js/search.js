/** «Actualizar ofertas»: lanza la búsqueda en el servidor y muestra su progreso. */

import { ApiError, fetchStatus, startSearch } from "./api.js";
import { $, $$, spinnerHtml } from "./dom.js";

const POLL_INTERVAL_MS = 1200;
const HIDE_PROGRESS_AFTER_MS = 800;

function readSearchForm() {
  return {
    roles: $("#roles")
      .value.split(",")
      .map((role) => role.trim())
      .filter(Boolean),
    sources: $$(".search-source:checked").map((box) => box.value),
    pages: Number($("#pages").value),
    expand: $("#expand").checked,
  };
}

function showProgress(status) {
  const bar = $("#progress");
  const log = $("#log");
  log.textContent = status.log.join("\n");
  log.scrollTop = log.scrollHeight;
  if (status.total) {
    bar.classList.remove("is-indeterminate");
    bar.firstElementChild.style.width = `${Math.round((100 * status.done) / status.total)}%`;
  }
}

export function bindSearch(onFinished) {
  const button = $("#refresh");
  const bar = $("#progress");
  let polling = false;

  function setBusy(busy) {
    button.disabled = busy;
    if (busy) button.innerHTML = spinnerHtml("Buscando...");
    else button.textContent = "Actualizar ofertas";
  }

  /** Consulta el progreso hasta que termina; después recarga las ofertas. */
  function follow() {
    if (polling) return;
    polling = true;
    setBusy(true);
    bar.hidden = false;
    bar.classList.add("is-indeterminate");
    const timer = setInterval(async () => {
      try {
        const status = await fetchStatus();
        showProgress(status);
        if (status.running) return;
      } catch (error) {
        $("#log").textContent = `No se pudo consultar el progreso: ${error.message}`;
      }
      clearInterval(timer);
      polling = false;
      setBusy(false);
      setTimeout(() => {
        bar.hidden = true;
      }, HIDE_PROGRESS_AFTER_MS);
      onFinished();
    }, POLL_INTERVAL_MS);
  }

  button.addEventListener("click", async () => {
    const form = readSearchForm();
    if (!form.roles.length || !form.sources.length) {
      $("#log").textContent = form.roles.length
        ? "Marca al menos una fuente donde buscar."
        : "Escribe al menos un cargo a buscar (ej. analista de datos).";
      return;
    }
    try {
      await startSearch(form);
    } catch (error) {
      $("#log").textContent = error.message;
      if (!(error instanceof ApiError && error.status === 409)) return; // 409: ya había una, se sigue esa
    }
    follow();
  });

  // Si se recargó la página con una búsqueda en curso, se retoma el seguimiento.
  fetchStatus()
    .then((status) => status.running && follow())
    .catch(() => {});
}
