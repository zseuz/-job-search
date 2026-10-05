// Pruebas de la lógica pura del navegador. Se ejecutan con:  node --test tests/js/*.test.mjs
import assert from "node:assert/strict";
import { test } from "node:test";

import { countBy, filterJobs, matchesFilters, sortJobs } from "../../src/buscador_empleos/web/static/js/filters.js";

const job = (overrides = {}) => ({
  id: "A:1", source: "A", title: "Desarrollador Java", company: "ACME", query: "java",
  modality: "Remoto", roles: ["Desarrollador"], contract: "Indefinido", techs: ["Java", "SQL"],
  salary_min: 5_000_000, days_ago: 2, ...overrides,
});

const NO_FILTERS = {
  text: "", kind: "", query: "", contract: "",
  modalities: ["Remoto", "Híbrido", "Presencial", "No indicado"], sources: ["A", "B"],
  ageDays: 0, includeUndated: true, salaryMin: 0, salaryMax: 0, includeUnpaid: true,
  techsIncluded: [], techsExcluded: [], techMode: "any",
};
const only = (overrides) => ({ ...NO_FILTERS, ...overrides });

test("sin filtros pasan todas las ofertas", () => {
  assert.equal(matchesFilters(job(), NO_FILTERS), true);
});

test("modalidad y fuente", () => {
  assert.equal(matchesFilters(job(), only({ modalities: ["Presencial"] })), false);
  assert.equal(matchesFilters(job(), only({ sources: ["B"] })), false);
});

test("texto: título o empresa, sin distinguir mayúsculas", () => {
  assert.equal(matchesFilters(job(), only({ text: "acme" })), true);
  assert.equal(matchesFilters(job(), only({ text: "java" })), true);
  assert.equal(matchesFilters(job(), only({ text: "cobol" })), false);
});

test("tipo de cargo, búsqueda original y contrato", () => {
  assert.equal(matchesFilters(job(), only({ kind: "Analista de datos" })), false);
  assert.equal(matchesFilters(job(), only({ kind: "Desarrollador" })), true);
  assert.equal(matchesFilters(job(), only({ query: "python" })), false);
  assert.equal(matchesFilters(job(), only({ contract: "Fijo" })), false);
});

test("fecha: filtra por antigüedad y decide qué hacer con las ofertas sin fecha", () => {
  assert.equal(matchesFilters(job({ days_ago: 10 }), only({ ageDays: 7 })), false);
  assert.equal(matchesFilters(job({ days_ago: 7 }), only({ ageDays: 7 })), true);
  assert.equal(matchesFilters(job({ days_ago: null }), only({ ageDays: 7, includeUndated: true })), true);
  assert.equal(matchesFilters(job({ days_ago: null }), only({ ageDays: 7, includeUndated: false })), false);
  assert.equal(matchesFilters(job({ days_ago: null }), only({ ageDays: 0, includeUndated: false })), true);
});

test("salario: mínimo, máximo y ofertas sin salario", () => {
  assert.equal(matchesFilters(job({ salary_min: 3_000_000 }), only({ salaryMin: 4_000_000 })), false);
  assert.equal(matchesFilters(job({ salary_min: 6_000_000 }), only({ salaryMax: 5_000_000 })), false);
  assert.equal(matchesFilters(job({ salary_min: 5_000_000 }), only({ salaryMin: 4e6, salaryMax: 6e6 })), true);
  assert.equal(matchesFilters(job({ salary_min: null }), only({ salaryMin: 4e6, includeUnpaid: true })), true);
  assert.equal(matchesFilters(job({ salary_min: null }), only({ includeUnpaid: false })), false);
});

test("tecnologías: cualquiera, todas y exclusión", () => {
  assert.equal(matchesFilters(job(), only({ techsIncluded: ["Java", "Angular"], techMode: "any" })), true);
  assert.equal(matchesFilters(job(), only({ techsIncluded: ["Java", "Angular"], techMode: "all" })), false);
  assert.equal(matchesFilters(job(), only({ techsIncluded: ["Java", "SQL"], techMode: "all" })), true);
  assert.equal(matchesFilters(job(), only({ techsExcluded: ["SQL"] })), false);
  assert.equal(matchesFilters(job(), only({ techsIncluded: ["Java"], techsExcluded: ["SQL"] })), false);
  assert.equal(matchesFilters(job(), only({ techsExcluded: ["Angular"] })), true);
});

test("filterJobs no modifica la lista original", () => {
  const jobs = [job({ id: "1" }), job({ id: "2", source: "B" })];
  const result = filterJobs(jobs, only({ sources: ["A"] }));
  assert.deepEqual(result.map((j) => j.id), ["1"]);
  assert.equal(jobs.length, 2);
});

test("orden: más recientes (sin fecha al final), mayor salario y más tecnologías", () => {
  const jobs = [
    job({ id: "viejo", days_ago: 9, salary_min: 1, techs: ["Java"] }),
    job({ id: "sin-fecha", days_ago: null, salary_min: 3, techs: ["a", "b", "c"] }),
    job({ id: "nuevo", days_ago: 1, salary_min: 2, techs: ["a", "b"] }),
  ];
  assert.deepEqual(sortJobs(jobs).map((j) => j.id), ["nuevo", "viejo", "sin-fecha"]);
  assert.deepEqual(sortJobs(jobs, "salary").map((j) => j.id), ["sin-fecha", "nuevo", "viejo"]);
  assert.deepEqual(sortJobs(jobs, "techs").map((j) => j.id), ["sin-fecha", "nuevo", "viejo"]);
  assert.deepEqual(jobs.map((j) => j.id), ["viejo", "sin-fecha", "nuevo"]); // el original queda igual
  assert.deepEqual(sortJobs(jobs, "desconocido").map((j) => j.id), ["nuevo", "viejo", "sin-fecha"]);
});

test("countBy cuenta valores simples y listas, ignorando los vacíos", () => {
  const jobs = [job({ techs: ["Java", "SQL"], contract: "" }), job({ techs: ["Java"], contract: "Fijo" })];
  assert.deepEqual(countBy(jobs, "techs"), { Java: 2, SQL: 1 });
  assert.deepEqual(countBy(jobs, "contract"), { Fijo: 1 });
});
