import axios from "axios";

const baseURL = import.meta.env.VITE_API_URL || "/api/v1";

export const api = axios.create({ baseURL });

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    const url = error.config?.url || "";
    if (error.response?.status === 401 && !url.includes("/auth/login")) {
      localStorage.removeItem("token");
      // Redirige al login si la sesión expiró o es inválida.
      if (!window.location.pathname.startsWith("/login")) {
        window.location.assign("/login");
      }
    }
    return Promise.reject(error);
  }
);

export const endpoints = {
  login: (payload) => api.post("/auth/login", payload).then((r) => r.data),
  me: () => api.get("/auth/me").then((r) => r.data),

  dashboard: () => api.get("/dashboard/summary").then((r) => r.data),

  matches: (params) => api.get("/matches", { params }).then((r) => r.data),
  match: (id) => api.get(`/matches/${id}`).then((r) => r.data),
  setResult: (id, payload) =>
    api.post(`/matches/${id}/result`, payload).then((r) => r.data),
  createMatch: (payload) => api.post("/matches", payload).then((r) => r.data),

  participants: () => api.get("/participants").then((r) => r.data),
  createParticipant: (payload) =>
    api.post("/participants", payload).then((r) => r.data),
  deleteParticipant: (id) => api.delete(`/participants/${id}`).then((r) => r.data),
  participantTop4: (id) => api.get(`/participants/${id}/top4`).then((r) => r.data),
  importParticipant: ({ nombre, email, file }) => {
    const form = new FormData();
    form.append("nombre", nombre);
    if (email) form.append("email", email);
    form.append("file", file);
    return api.post("/participants/import", form).then((r) => r.data);
  },

  bracket: (participantId) =>
    api
      .get("/tournament/bracket", {
        params: participantId ? { participant_id: participantId } : {},
      })
      .then((r) => r.data),

  predictions: (params) => api.get("/predictions", { params }).then((r) => r.data),
  createPrediction: (payload) =>
    api.post("/predictions", payload).then((r) => r.data),

  ranking: () => api.get("/ranking").then((r) => r.data),
  recalculateRanking: () => api.post("/ranking/recalculate").then((r) => r.data),

  statsHits: () => api.get("/stats/hits").then((r) => r.data),
  statsPhases: () => api.get("/stats/phases").then((r) => r.data),
  statsRace: () => api.get("/stats/race").then((r) => r.data),
  participantStats: (id) =>
    api.get(`/stats/participant/${id}`).then((r) => r.data),

  rules: () => api.get("/admin/rules").then((r) => r.data),
  updateRule: (code, payload) =>
    api.put(`/admin/rules/${code}`, payload).then((r) => r.data),
  finalPositions: () => api.get("/admin/final-positions").then((r) => r.data),
  setFinalPositions: (posiciones) =>
    api.put("/admin/final-positions", { posiciones }).then((r) => r.data),
  audit: () => api.get("/admin/audit").then((r) => r.data),
  triggerSync: () => api.post("/admin/sync").then((r) => r.data),
  syncStatus: () => api.get("/admin/sync/status").then((r) => r.data),
  importCalendar: () => api.post("/admin/import/calendar").then((r) => r.data),
  importPredictions: () => api.post("/admin/import/predictions").then((r) => r.data),
  importRules: () => api.post("/admin/import/rules").then((r) => r.data),
  resetTournament: () => api.post("/admin/reset/tournament").then((r) => r.data),

  createBackup: () => api.post("/admin/backup").then((r) => r.data),
  restoreBackup: () => api.post("/admin/backup/restore").then((r) => r.data),
  downloadBackup: () =>
    api.get("/admin/backup/download", { responseType: "blob" }).then((r) => r.data),

  users: () => api.get("/admin/users").then((r) => r.data),
  createUser: (payload) => api.post("/admin/users", payload).then((r) => r.data),
  deleteUser: (id) => api.delete(`/admin/users/${id}`).then((r) => r.data),
  resetUserPassword: (id, password) =>
    api.post(`/admin/users/${id}/reset-password`, { password }).then((r) => r.data),

  exportUrl: (kind) => `${baseURL}/export/${kind}`,
};
