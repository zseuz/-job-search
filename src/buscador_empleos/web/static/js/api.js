/** Cliente de la API del servidor. Es lo único que hace peticiones HTTP. */

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function request(url, options) {
  const response = await fetch(url, options);
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new ApiError(data.error || response.statusText, response.status);
  return data;
}

export const fetchJobs = () => request("/api/jobs");

export const fetchStatus = () => request("/api/status");

export const fetchDescription = async (jobId) =>
  (await request(`/api/jobs/${encodeURIComponent(jobId)}/description`)).description || "";

export const startSearch = (body) =>
  request("/api/search", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
