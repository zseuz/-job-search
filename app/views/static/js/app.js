let JOBS = [], techsOn = new Set(), techsOff = new Set(), applied = null;
const $ = s => document.querySelector(s), $$ = s => [...document.querySelectorAll(s)];
const esc = s => (s||"").replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const GROUPS = {
  "Lenguajes": ["Java","Python","JavaScript","TypeScript","C#","PHP","Golang","Kotlin","Swift","Ruby","Scala","C++","R","SQL"],
  "Frameworks y plataformas": ["Angular","React","Vue","Node.js",".NET","Spring","Django","Flask","FastAPI","Laravel","Flutter","React Native","Android","iOS"],
  "Datos y BI": ["Power BI","Tableau","Excel","Looker","Qlik","Pandas","Spark","Hadoop","Airflow","dbt","ETL","Machine Learning","BigQuery","Snowflake","Databricks"],
  "Bases de datos": ["PostgreSQL","MySQL","SQL Server","Oracle","PL/SQL","MongoDB","NoSQL","MariaDB","SQLite","Redis","Elasticsearch","Cassandra","DynamoDB","Firebase","Neo4j","Teradata"],
  "Nube y DevOps": ["Docker","Kubernetes","AWS","Azure","GCP","Git","Linux"],
};

async function load() {
  const d = await (await fetch("/api/jobs")).json();
  JOBS = d.jobs;
  $("#updated").textContent = d.updated ? "Actualizado: " + d.updated.replace("T", " ") : "Sin datos: pulsa Actualizar";
  const count = (k) => { const m = {}; JOBS.forEach(j => (Array.isArray(j[k]) ? j[k] : [j[k]]).filter(Boolean).forEach(v => m[v] = (m[v]||0)+1)); return m; };
  const tc = count("techs");
  $("#techs").innerHTML = Object.entries(GROUPS).map(([g, list]) =>
    `<div class="tg">${g}</div><div class="techs">` +
    list.map(t => `<button data-t="${esc(t)}" class="${techsOn.has(t)?'on':techsOff.has(t)?'off':''}">${esc(t)} <small>${tc[t]||0}</small></button>`).join("") + "</div>").join("");
  $$("#techs button").forEach(b => {
    let timer;
    const set = (t, mode) => {  // mode: "on" | "off" | ""
      techsOn.delete(t); techsOff.delete(t);
      if (mode === "on") techsOn.add(t); if (mode === "off") techsOff.add(t);
      b.classList.toggle("on", mode === "on"); b.classList.toggle("off", mode === "off");
    };
    b.onclick = () => {  // clic simple (espera por si llega un doble clic)
      clearTimeout(timer);
      timer = setTimeout(() => set(b.dataset.t, techsOn.has(b.dataset.t) || techsOff.has(b.dataset.t) ? "" : "on"), 220);
    };
    b.ondblclick = () => { clearTimeout(timer); set(b.dataset.t, techsOff.has(b.dataset.t) ? "" : "off"); };
  });
  fill("#role", count("query")); fill("#contract", count("contract"));
  applyFilters();
}
function fill(sel, m) {
  const el = $(sel), cur = el.value;
  el.innerHTML = '<option value="">Todos</option>' + Object.keys(m).map(v => `<option>${esc(v)}</option>`).join("");
  el.value = cur;
}
let applyTimer;
function applyFilters() {
  const btn = $("#apply");
  btn.disabled = true; btn.innerHTML = '<span class="spin"></span>Filtrando...';
  $("#list").innerHTML = '<div class="loading"><span class="spin"></span>Filtrando ofertas...</div>';
  clearTimeout(applyTimer);
  applyTimer = setTimeout(() => { collect(); render(); btn.disabled = false; btn.textContent = "Aplicar filtros"; }, 500);
}
function collect() {
  applied = {
    q: $("#q").value.toLowerCase(), mods: $$(".mod:checked").map(c => c.value), role: $("#role").value, kind: $("#kind").value, age: +$("#age").value || 0, noDate: $("#noDate").checked,
    sources: $$(".fsrc:checked").map(c => c.value), contract: $("#contract").value, min: +$("#salMin").value || 0,
    max: +$("#salMax").value || 0, noSalary: $("#noSalary").checked, techs: [...techsOn], notTechs: [...techsOff],
    mode: $("input[name=mode]:checked").value,
  };
}
function render() {
  const f = applied; if (!f) return;
  let r = JOBS.filter(j => {
    if (!f.mods.includes(j.modality)) return false;
    if (f.q && !(j.title + " " + j.company).toLowerCase().includes(f.q)) return false;
    if (f.role && j.query !== f.role) return false;
    if (f.kind && !j.roles.includes(f.kind)) return false;
    if (f.age) {
      if (j.days_ago == null) { if (!f.noDate) return false; }
      else if (j.days_ago > f.age) return false;
    }
    if (!f.sources.includes(j.source)) return false;
    if (f.contract && j.contract !== f.contract) return false;
    if (j.salary_min) {
      if (f.min && j.salary_min < f.min) return false;
      if (f.max && j.salary_min > f.max) return false;
    } else if (!f.noSalary) return false;
    if (f.notTechs.some(t => j.techs.includes(t))) return false;
    if (f.techs.length) {
      const has = t => j.techs.includes(t);
      if (!(f.mode === "all" ? f.techs.every(has) : f.techs.some(has))) return false;
    }
    return true;
  });
  const s = $("#sort").value;
  if (!s) r.sort((a,b) => (a.days_ago ?? 1e9) - (b.days_ago ?? 1e9));
  if (s === "sal") r.sort((a,b) => (b.salary_min||0) - (a.salary_min||0));
  if (s === "tech") r.sort((a,b) => b.techs.length - a.techs.length);
  $("#count").textContent = `${r.length} de ${JOBS.length} ofertas`;
  $("#list").innerHTML = r.length ? r.slice(0, 300).map(j => `
    <div class="job" data-id="${esc(j.id)}">
      <h2><a href="${esc(j.url)}" target="_blank" rel="noopener noreferrer" referrerpolicy="no-referrer">${esc(j.title)}</a></h2>
      <div class="meta">${esc(j.company)} · ${esc(j.location)} · ${esc(j.posted)}</div>
      <div class="row">
        <span class="chip src">${j.source}</span>${j.roles.map(r => `<span class="chip">${r}</span>`).join("")}<span class="chip">${j.modality}</span>
        ${j.contract ? `<span class="chip">${esc(j.contract)}</span>` : ""}
        ${j.salary_text ? `<span class="chip sal">${esc(j.salary_text)}</span>` : ""}
        ${j.techs.map(t => `<span class="chip${f.techs.includes(t) ? ' sal' : ''}">${esc(t)}</span>`).join("")}
      </div>
      <div class="actions-row">
        ${j.has_description
          ? '<button class="ghost small toggle-desc">Ver descripción</button>'
          : '<button class="ghost small" disabled title="Esta fuente no entrega la descripción: abre el enlace">Sin descripción</button>'}
        <a class="open-link" href="${esc(j.url)}" target="_blank" rel="noopener noreferrer" referrerpolicy="no-referrer">Abrir oferta ↗</a>
      </div>
      <div class="desc" hidden></div>
    </div>`).join("") : '<div class="empty">No hay ofertas con esos filtros.</div>';
}
// ---- descripcion desplegable (se pide al servidor solo al abrirla)
const descCache = {};
function highlight(text, techs) {
  const html = esc(text);
  if (!techs.length) return html;
  const names = techs.map(t => esc(t).replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join("|");
  return html.replace(new RegExp("(?<![\\w+#.])(" + names + ")(?![\\w+#])", "gi"), "<mark>$1</mark>");
}
$("#list").addEventListener("click", async e => {
  const btn = e.target.closest(".toggle-desc");
  if (!btn) return;
  const card = btn.closest(".job"), box = card.querySelector(".desc"), id = card.dataset.id;
  if (!box.hidden) { box.hidden = true; btn.textContent = "Ver descripción"; return; }
  box.hidden = false; btn.textContent = "Ocultar descripción";
  if (!(id in descCache)) {
    box.innerHTML = '<span class="spin"></span>Cargando descripción...';
    try {
      const r = await fetch(`/api/jobs/${encodeURIComponent(id)}/description`);
      if (!r.ok) throw new Error(r.status);
      descCache[id] = (await r.json()).description || "";
    } catch (err) { box.textContent = "No se pudo cargar la descripción."; return; }
  }
  box.innerHTML = highlight(descCache[id], applied ? applied.techs : []) || "Sin descripción.";
});

$("#apply").onclick = applyFilters;
$("#sort").addEventListener("input", render);
$("aside").addEventListener("keydown", e => { if (e.key === "Enter" && e.target.tagName === "INPUT" && e.target.id !== "roles") applyFilters(); });
$("#clear").onclick = () => {
  techsOn.clear(); techsOff.clear(); $$("#techs button").forEach(b => b.classList.remove("on", "off"));
  ["#q","#salMin","#salMax"].forEach(s => $(s).value = ""); ["#kind","#role","#contract","#age"].forEach(s => $(s).value = ""); $$(".fsrc").forEach(c => c.checked = true);
  $$(".mod").forEach(c => c.checked = true); $("#noSalary").checked = true; $("#noDate").checked = true; applyFilters();
};

$("#refresh").onclick = async () => {
  const body = { roles: $("#roles").value.split(",").map(s => s.trim()).filter(Boolean), sources: $$(".src:checked").map(c => c.value),
                 pages: +$("#pages").value, expand: $("#expand").checked };
  if (!body.roles.length || !body.sources.length) {
    $("#log").textContent = !body.roles.length ? "Escribe al menos un cargo a buscar (ej. analista de datos)." : "Marca al menos una fuente donde buscar.";
    return;
  }
  const r = await fetch("/api/search", { method: "POST", headers: {"Content-Type":"application/json"}, body: JSON.stringify(body) });
  if (r.ok) poll();
};
async function poll() {
  const btn = $("#refresh"), prog = $("#prog");
  btn.disabled = true; btn.innerHTML = '<span class="spin"></span>Buscando...';
  prog.style.display = "block"; prog.classList.add("indet");
  const t = setInterval(async () => {
    const s = await (await fetch("/api/status")).json();
    $("#log").textContent = s.log.join("\n"); $("#log").scrollTop = 1e9;
    if (s.total) { prog.classList.remove("indet"); prog.firstElementChild.style.width = Math.round(100 * s.done / s.total) + "%"; }
    if (!s.running) {
      clearInterval(t); btn.disabled = false; btn.textContent = "Actualizar ofertas";
      setTimeout(() => prog.style.display = "none", 800); load();
    }
  }, 1200);
}
fetch("/api/status").then(r => r.json()).then(s => s.running && poll());
load();
