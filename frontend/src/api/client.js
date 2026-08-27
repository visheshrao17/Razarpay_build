import axios from "axios";

const api = axios.create({
  baseURL: `${process.env.REACT_APP_BACKEND_URL}/api`,
  withCredentials: true,
});

export function formatApiError(err) {
  const detail = err?.response?.data?.detail ?? err?.response?.data?.error?.message;
  if (detail == null) return err?.message || "Something went wrong";
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail))
    return detail.map((e) => (e && typeof e.msg === "string" ? e.msg : JSON.stringify(e))).join(" ");
  if (typeof detail === "object") return detail.message || JSON.stringify(detail);
  return String(detail);
}

export const auth = {
  login: (email, password) => api.post("/auth/login", { email, password }),
  logout: () => api.post("/auth/logout"),
  me: () => api.get("/auth/me"),
};

export const runs = {
  list: () => api.get("/runs"),
  create: (body) => api.post("/runs", body),
  get: (runId) => api.get(`/runs/${runId}`),
  loadFixtures: (runId) => api.post(`/runs/${runId}/sources/fixture`),
  uploadSource: (runId, sourceType, file) => {
    const fd = new FormData();
    fd.append("source_type", sourceType);
    fd.append("file", file);
    return api.post(`/runs/${runId}/sources`, fd);
  },
  execute: (runId, force = false) => api.post(`/runs/${runId}/execute?force=${force}`),
  summary: (runId) => api.get(`/runs/${runId}/summary`),
  matches: (runId, params) => api.get(`/runs/${runId}/matches`, { params }),
  matchDetail: (runId, matchId) => api.get(`/runs/${runId}/matches/${matchId}`),
  exceptions: (runId, params) => api.get(`/runs/${runId}/exceptions`, { params }),
  audit: (runId, params) => api.get(`/runs/${runId}/audit`, { params }),
  evaluation: (runId) => api.get(`/runs/${runId}/evaluation`),
  report: (runId, format) =>
    api.get(`/runs/${runId}/report`, {
      params: { format },
      responseType: format === "json" ? "json" : "text",
      transformResponse: format === "json" ? undefined : [(d) => d],
    }),
};

export const exceptions = {
  detail: (exceptionId) => api.get(`/exceptions/${exceptionId}`),
  resolve: (exceptionId, body) => api.post(`/exceptions/${exceptionId}/resolve`, body),
  explain: (exceptionId, model) => api.post(`/exceptions/${exceptionId}/explain`, { model }),
};

export const razorpay = {
  status: () => api.get("/razorpay/status"),
};

export default api;
