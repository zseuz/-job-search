// Pruebas del HTML que se genera para cada oferta. Se ejecutan con:  node --test tests/js/*.test.mjs
import assert from "node:assert/strict";
import { test } from "node:test";

import { escapeHtml } from "../../src/buscador_empleos/web/static/js/dom.js";
import { highlight, jobCardHtml } from "../../src/buscador_empleos/web/static/js/render.js";

const job = (overrides = {}) => ({
  id: "A:1", source: "A", title: "Dev", company: "ACME", location: "Bogotá", posted: "Hace 1 día",
  url: "https://example.test/1", modality: "Remoto", roles: ["Desarrollador"], contract: "",
  salary_text: "", techs: ["Java"], has_description: true, ...overrides,
});

test("escapeHtml neutraliza los caracteres peligrosos", () => {
  assert.equal(escapeHtml(`<img src=x onerror="a()"> & 'x'`), "&lt;img src=x onerror=&quot;a()&quot;&gt; &amp; &#39;x&#39;");
  assert.equal(escapeHtml(null), "");
  assert.equal(escapeHtml(5), "5");
});

test("highlight resalta solo palabras completas y escapa antes de resaltar", () => {
  assert.equal(highlight("Java y JavaScript", ["Java"]), "<mark>Java</mark> y JavaScript");
  assert.equal(highlight("usa C# y .NET", ["C#", ".NET"]), "usa <mark>C#</mark> y <mark>.NET</mark>");
  assert.equal(highlight("<b>Java</b>", ["Java"]), "&lt;b&gt;<mark>Java</mark>&lt;/b&gt;");
  assert.equal(highlight("texto", []), "texto");
});

test("la tarjeta escapa todos los datos de la oferta", () => {
  const html = jobCardHtml(job({ title: "<script>alert(1)</script>", source: "<b>x</b>", company: '"&"' }));
  assert.ok(!html.includes("<script>"));
  assert.ok(!html.includes("<b>x</b>"));
  assert.ok(html.includes("&lt;script&gt;"));
});

test("el botón de descripción depende de si la oferta la tiene", () => {
  assert.ok(jobCardHtml(job()).includes("toggle-description"));
  const without = jobCardHtml(job({ has_description: false }));
  assert.ok(!without.includes("toggle-description"));
  assert.ok(without.includes("Sin descripción"));
});

test("los enlaces externos no filtran el origen ni dan acceso a la ventana", () => {
  const html = jobCardHtml(job());
  assert.equal((html.match(/rel="noopener noreferrer" referrerpolicy="no-referrer"/g) || []).length, 2);
});

test("las tecnologías filtradas se marcan en la tarjeta", () => {
  assert.ok(jobCardHtml(job(), ["Java"]).includes('class="chip chip-highlight">Java'));
  assert.ok(jobCardHtml(job(), []).includes('class="chip">Java'));
});
