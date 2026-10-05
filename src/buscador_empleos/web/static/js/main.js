/** Punto de entrada: conecta la API, el panel de filtros y la lista. */

import { fetchJobs } from "./api.js";
import { bindDescriptions } from "./description.js";
import { $, escapeHtml, spinnerHtml } from "./dom.js";
import { countBy, filterJobs, sortJobs } from "./filters.js";
import { fillSelect, readFilters, resetFilters } from "./panel.js";
import { renderResults } from "./render.js";
import { bindSearch } from "./search.js";
import { createTechPicker } from "./techs.js";

const FILTER_FEEDBACK_MS = 500; // pausa breve para que se note que el filtro se aplicó

const boot = JSON.parse($("#boot-data").textContent);
const picker = createTechPicker($("#techs"), boot.techGroups);

let jobs = [];
let applied = null; // filtros que se aplicaron por última vez
let applyTimer = null;

function showResults() {
  const filtered = sortJobs(filterJobs(jobs, applied), $("#sort").value);
  renderResults(filtered, jobs.length, applied.techsIncluded);
}

/** Aplica los filtros con una breve animación de carga. */
function applyFilters() {
  const button = $("#apply");
  button.disabled = true;
  button.innerHTML = spinnerHtml("Filtrando...");
  $("#list").innerHTML = `<div class="loading">${spinnerHtml("Filtrando ofertas...")}</div>`;
  clearTimeout(applyTimer);
  applyTimer = setTimeout(() => {
    applied = readFilters(picker);
    showResults();
    button.disabled = false;
    button.textContent = "Aplicar filtros";
  }, FILTER_FEEDBACK_MS);
}

async function loadJobs() {
  const data = await fetchJobs();
  jobs = data.jobs;
  $("#updated").textContent = data.updated
    ? `Actualizado: ${data.updated.replace("T", " ")}`
    : "Sin datos: pulsa Actualizar";
  picker.render(countBy(jobs, "techs"));
  fillSelect($("#query"), countBy(jobs, "query"), "Todas");
  fillSelect($("#contract"), countBy(jobs, "contract"), "Todos");
  applyFilters();
}

function showLoadError(error) {
  $("#list").innerHTML = `<div class="empty">No se pudieron cargar las ofertas: ${escapeHtml(error.message)}</div>`;
}

$("#apply").addEventListener("click", applyFilters);
$("#sort").addEventListener("input", () => applied && showResults());
$("#clear").addEventListener("click", () => {
  resetFilters(picker);
  applyFilters();
});
$(".sidebar").addEventListener("keydown", (event) => {
  const field = event.target;
  if (event.key === "Enter" && field.tagName === "INPUT" && field.id !== "roles") applyFilters();
});

bindDescriptions($("#list"), () => applied?.techsIncluded ?? []);
bindSearch(() => loadJobs().catch(showLoadError));
loadJobs().catch(showLoadError);
