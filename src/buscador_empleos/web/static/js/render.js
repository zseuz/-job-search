/** Dibujo de la lista de ofertas. */

import { $, escapeHtml as esc } from "./dom.js";
import { MAX_RESULTS } from "./filters.js";

const LINK_ATTRS = 'rel="noopener noreferrer" referrerpolicy="no-referrer"';

/** Resalta (con <mark>) las tecnologías indicadas dentro de un texto, escapándolo antes. */
export function highlight(text, techs) {
  const html = esc(text);
  if (!techs.length) return html;
  const names = techs.map((tech) => esc(tech).replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join("|");
  return html.replace(new RegExp(`(?<![\\w+#.])(${names})(?![\\w+#])`, "gi"), "<mark>$1</mark>");
}

function chipsHtml(job, highlighted) {
  const chip = (text, extra = "") => `<span class="chip${extra}">${esc(text)}</span>`;
  return [
    chip(job.source, " chip-source"),
    ...job.roles.map((role) => chip(role)),
    chip(job.modality),
    job.contract ? chip(job.contract) : "",
    job.salary_text ? chip(job.salary_text, " chip-highlight") : "",
    ...job.techs.map((tech) => chip(tech, highlighted.includes(tech) ? " chip-highlight" : "")),
  ].join("");
}

export function jobCardHtml(job, highlighted = []) {
  const descriptionButton = job.has_description
    ? '<button type="button" class="btn btn-ghost btn-small toggle-description">Ver descripción</button>'
    : '<button type="button" class="btn btn-ghost btn-small" disabled ' +
      'title="Esta fuente no entrega la descripción: abre el enlace">Sin descripción</button>';
  return `
    <article class="job" data-id="${esc(job.id)}">
      <h2><a href="${esc(job.url)}" target="_blank" ${LINK_ATTRS}>${esc(job.title)}</a></h2>
      <div class="meta">${esc(job.company)} · ${esc(job.location)} · ${esc(job.posted)}</div>
      <div class="chips">${chipsHtml(job, highlighted)}</div>
      <div class="job-actions">
        ${descriptionButton}
        <a class="open-link" href="${esc(job.url)}" target="_blank" ${LINK_ATTRS}>Abrir oferta ↗</a>
      </div>
      <div class="description" hidden></div>
    </article>`;
}

/** Dibuja el resultado de aplicar los filtros: el contador y las primeras ofertas. */
export function renderResults(jobs, total, highlighted) {
  $("#count").textContent = `${jobs.length} de ${total} ofertas`;
  $("#list").innerHTML = jobs.length
    ? jobs
        .slice(0, MAX_RESULTS)
        .map((job) => jobCardHtml(job, highlighted))
        .join("")
    : '<div class="empty">No hay ofertas con esos filtros.</div>';
}
