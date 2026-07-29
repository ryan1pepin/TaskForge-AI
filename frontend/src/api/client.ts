// Thin fetch-based API client with Zustand-sourced access token.
// Deliberately avoids Axios → less bundle bloat, no interceptor race vs TanStack Query retry/rollback.

import { useAuthStore } from "../store/auth";

const BASE_URL = "/api/v1";

export class ApiError extends Error {
  constructor(public status: number, public detail: string) {
    super(detail);
    this.name = "ApiError";
  }
}

export type ProjectParams = { limit?: number; offset?: number; status?: string };
export type TaskParams = { status?: string };

// ── Core request helper with 401 auto-refresh ────────────────────────────────
async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const token = useAuthStore.getState().accessToken ?? null;
  let attempt = 0;

  while (attempt <= 1) {
    const res = await fetch(`${BASE_URL}${path}`, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...(options?.headers as Record<string, string>),
      },
      credentials: "include", // httpOnly refresh cookie travels cross-origin
    });

    if (res.status === 401 && attempt === 0) {
      try {
        const refreshed = await fetch(`${BASE_URL}/auth/refresh`, {
          method: "POST", credentials: "include" as RequestCredentials,
        });
        if (refreshed.ok) {
          const j = await refreshed.json();
          useAuthStore.getState().setAccessToken(j.access_token);
        } else {
          useAuthStore.getState().clearToken();
          throw new ApiError(401, "Session expired");
        }
      } catch (_recovered: unknown) {
        if ((_recovered as ApiError).status === 401) throw _recovered as Error;
        /* network blip — try one original retry */
      }
      attempt++;
      continue; // retry with fresh token in next loop iteration
    }

    if (res.status === 204) return undefined as T;

    const body = await res.json().catch(() => ({ detail: res.statusText }));
    if (!res.ok) throw new ApiError(res.status, body.detail ?? "Unknown error");

    return body as T;
  }

  /* unreachable guard */
  return Promise.reject(new Error("Unreachable"));
}

// ── Public API surface (consumed by TanStack Query hooks / mutations) ────────

export const api = {
  // ─ Auth ─
  login: (email: string, pw: string) =>
    request("/auth/login", { method: "POST", body: JSON.stringify({ email, password: pw }) }),

  register: (email: string, pw: string) =>
    request("/auth/register", { method: "POST", body: JSON.stringify({ email, password: pw }) }),

  refresh: () => request("/auth/refresh", { method: "POST" }),

  logout: () => request("/auth/logout", { method: "POST" }),

  // ─ Projects ─
  getProjects(opts?: ProjectParams) {
    const q = new URLSearchParams();
    if (opts?.limit)  q.set("limit", String(opts.limit));
    if (opts?.offset) q.set("offset", String(opts.offset));
    if (opts?.status) q.set("status", opts.status);
    return request(`/projects${q.size ? "?" + q : ""}`);
  },

  createProject(body: object) =>
    request("/projects", { method: "POST", body: JSON.stringify(body) }),

  updateProject(id: string, body: object) =>
    request(`/projects/${id}`, { method: "PATCH", body: JSON.stringify(body) }),

  deleteProject(id: string) =>
    request(`/projects/${id}`, { method: "DELETE" }),

  // ─ Tasks ─
  getTasks(projectId: string, opts?: TaskParams) {
    const q = new URLSearchParams();
    if (opts?.status) q.set("status", opts.status);
    return request(`/projects/${projectId}/tasks${q.size ? "?" + q : ""}`);
  },

  createTask(projectId: string, body: object) =>
    request(`/projects/${projectId}/tasks`, { method: "POST", body: JSON.stringify(body) }),

  updateTask(projectId: string, taskId: string, body: object) =>
    request(`/projects/${projectId}/tasks/${taskId}`, { method: "PATCH", body: JSON.stringify(body) }),

  deleteTask(projectId: string, taskId: string) =>
    request(`/projects/${projectId}/tasks/${taskId}`, { method: "DELETE" }),

  // ─ AI endpoints ─
  suggestPriority: (pid: string, tid: string) =>
    request(`/projects/${pid}/tasks/${tid}/suggest-priority`, { method: "POST" }),

  suggestDeadline: (pid: string, tid: string) =>
    request(`/projects/${pid}/tasks/${tid}/suggest-deadline`, { method: "POST" }),

  generateDescription: (pid: string, tid: string) =>
    request(`/projects/${pid}/tasks/${tid}/generate-description`, { method: "POST" }),

  suggestTasks: (pid: string) =>
    request(`/projects/${pid}/suggest-tasks`, { method: "POST" }),

  projectHealth: (pid: string) =>
    request(`/projects/${pid}/health`, { method: "GET" }),
};
