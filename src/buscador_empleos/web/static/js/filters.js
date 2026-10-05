/**
 * Lógica pura de filtrado y orden de ofertas. No toca el DOM: se prueba con `node --test`.
 *
 * Forma del objeto de filtros:
 *   text, kind, query, contract      texto ('' = sin filtro)
 *   modalities, sources              listas de valores permitidos
 *   ageDays                          0 = cualquier fecha
 *   includeUndated, includeUnpaid    qué hacer con ofertas sin fecha / sin salario
 *   salaryMin, salaryMax             0 = sin límite
 *   techsIncluded, techsExcluded     tecnologías a exigir / a descartar
 *   techMode                         'any' | 'all'
 */

export const MAX_RESULTS = 300;

export function matchesFilters(job, f) {
  if (!f.modalities.includes(job.modality)) return false;
  if (f.text && !`${job.title} ${job.company}`.toLowerCase().includes(f.text)) return false;
  if (f.query && job.query !== f.query) return false;
  if (f.kind && !job.roles.includes(f.kind)) return false;
  if (f.ageDays) {
    if (job.days_ago == null) {
      if (!f.includeUndated) return false;
    } else if (job.days_ago > f.ageDays) {
      return false;
    }
  }
  if (!f.sources.includes(job.source)) return false;
  if (f.contract && job.contract !== f.contract) return false;
  if (job.salary_min) {
    if (f.salaryMin && job.salary_min < f.salaryMin) return false;
    if (f.salaryMax && job.salary_min > f.salaryMax) return false;
  } else if (!f.includeUnpaid) {
    return false;
  }
  if (f.techsExcluded.some((tech) => job.techs.includes(tech))) return false;
  if (f.techsIncluded.length) {
    const has = (tech) => job.techs.includes(tech);
    const ok = f.techMode === "all" ? f.techsIncluded.every(has) : f.techsIncluded.some(has);
    if (!ok) return false;
  }
  return true;
}

export const filterJobs = (jobs, filters) => jobs.filter((job) => matchesFilters(job, filters));

const byRecency = (a, b) => (a.days_ago ?? 1e9) - (b.days_ago ?? 1e9);
const bySalary = (a, b) => (b.salary_min || 0) - (a.salary_min || 0);
const byTechCount = (a, b) => b.techs.length - a.techs.length;
const COMPARATORS = { "": byRecency, salary: bySalary, techs: byTechCount };

/** Devuelve una copia ordenada ('' = más recientes, 'salary', 'techs'). */
export const sortJobs = (jobs, mode = "") => [...jobs].sort(COMPARATORS[mode] ?? byRecency);

/** Cuenta cuántas ofertas tienen cada valor de `key` (un valor o una lista). */
export function countBy(jobs, key) {
  const counts = {};
  for (const job of jobs) {
    for (const value of [].concat(job[key])) {
      if (value) counts[value] = (counts[value] || 0) + 1;
    }
  }
  return counts;
}
