/** Utilidades de DOM sin dependencias. */

export const $ = (selector, root = document) => root.querySelector(selector);
export const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];

const HTML_ESCAPES = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };

/** Escapa un valor para insertarlo como texto o atributo en HTML. */
export const escapeHtml = (value) => String(value ?? "").replace(/[&<>"']/g, (char) => HTML_ESCAPES[char]);

export const spinnerHtml = (label) => `<span class="spinner" aria-hidden="true"></span>${label}`;
