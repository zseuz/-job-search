/** Panel de filtros: lee los controles del formulario y los restablece. */

import { $, $$, escapeHtml } from "./dom.js";

const checkedValues = (selector) => $$(selector + ":checked").map((input) => input.value);

/** Convierte el estado del formulario en el objeto de filtros que entiende `filters.js`. */
export function readFilters(picker) {
  const techs = picker.selection();
  return {
    text: $("#text").value.trim().toLowerCase(),
    modalities: checkedValues(".filter-modality"),
    kind: $("#kind").value,
    query: $("#query").value,
    sources: checkedValues(".filter-source"),
    ageDays: Number($("#age").value) || 0,
    includeUndated: $("#include-undated").checked,
    salaryMin: Number($("#salary-min").value) || 0,
    salaryMax: Number($("#salary-max").value) || 0,
    includeUnpaid: $("#include-unpaid").checked,
    contract: $("#contract").value,
    techsIncluded: techs.included,
    techsExcluded: techs.excluded,
    techMode: $("input[name=tech-mode]:checked").value,
  };
}

/** Rellena un <select> con las opciones disponibles sin perder la que estaba elegida. */
export function fillSelect(select, counts, allLabel) {
  const current = select.value;
  select.innerHTML =
    `<option value="">${escapeHtml(allLabel)}</option>` +
    Object.keys(counts)
      .map((value) => `<option>${escapeHtml(value)}</option>`)
      .join("");
  select.value = current;
}

/** Deja todos los filtros como al abrir la página. */
export function resetFilters(picker) {
  picker.clear();
  ["#text", "#salary-min", "#salary-max", "#kind", "#query", "#contract", "#age"].forEach((id) => {
    $(id).value = "";
  });
  $$(".filter-source, .filter-modality").forEach((box) => {
    box.checked = true;
  });
  $("#include-unpaid").checked = true;
  $("#include-undated").checked = true;
  $("input[name=tech-mode][value=any]").checked = true;
}
