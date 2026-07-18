// Thin fetch-based API client.
// Deliberately avoids Axios to reduce bundle size and prevent interceptor
// conflicts with TanStack Query's own lifecycle (refetch, retry, rollback).
//
// Auth pattern:
//   - Access token lives in Zustand memory store (never localStorage → XSS safe)
//   - Refresh token lives in httpOnly cookie (set by backend → CSRF protected via SameSite=Lax)
//   - On 401, we call /auth/refresh once (with credentials), get a new access token,
//     and retry the original request — TanStack Query handles re-queuing.

const BASE_URL = "/api/v1";

export class ApiError extends Error {
  constructor(
    public status: number,
    public detail: string,
  ) {
    super(detail);
    this.name = "ApiError";
  }
}

// ── Core request helper ───────────────────────────────────────────────────────
async function request<T>(
  path: string,
  options: RequestInit = {},
  accessToken?: string | null,
): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };

  if (accessToken) {
    headers["Authorization"] = `Bearer ${accessToken}`;
  }

  const response = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers,
    // credentials: "include" sends the httpOnly refresh cookie on every request
    credentials: "include",
  });

  // 204 No Content — return empty without trying to parse JSON
  if (response.status === 204) {
    return undefined as T;
  }

  const data = await response.json().catch(() => ({ detail: response.statusText }));

  if (!response.ok) {
    throw new ApiError(response.status, data.detail ?? "Unknown error");
  }

  return data as T;
}

// ── Public API ────────────────────────────────────────────────────────────────
// These are the raw fetch functions consumed by TanStack Query hooks.
// TanStack Query owns retry logic, caching, and stale-time — we don't duplicate that here.

export const api = {
  // Auth
  register: (email: string, password: string) =>
    request("/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),

  login: (email: string, password: string) =>
    request("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),

  refresh: () =>
    request("/auth/refresh", { method: "POST" }),

  logout: (accessToken: string) =>
    request("/auth/logout", { method: "POST" }, accessToken),

  // Projects
  getProjects: (accessToken: string, params?: { limit?: number; offset?: number; status?: string }) => {
    const qs = new URLSearchParams();
    if (params?.limit)  qs.set("limit",  String(params.limit));
    if (params?.offset) qs.set("offset", String(params.offset));
    if (params?.status) qs.set("status", params.status);
    return request(`/projects${qs.size ? `?${qs}` : ""}`, {}, accessToken);
  },

  createProject: (accessToken: string, body: object) =>
    request("/projects", { method: "POST", body: JSON.stringify(body) }, accessToken),

  updateProject: (accessToken: string, id: string, body: object) =>
    request(`/projects/${id}`, { method: "PATCH", body: JSON.stringify(body) }, accessToken),

  deleteProject: (accessToken: string, id: string) =>
    request(`/projects/${id}`, { method: "DELETE" }, accessToken),

  // Tasks
  getTasks: (accessToken: string, projectId: string, params?: { status?: string }) => {
    const qs = new URLSearchParams();
    if (params?.status) qs.set("status", params.status);
    return request(`/projects/${projectId}/tasks${qs.size ? `?${qs}` : ""}`, {}, accessToken);
  },

  createTask: (accessToken: string, projectId: string, body: object) =>
    request(`/projects/${projectId}/tasks`, { method: "POST", body: JSON.stringify(body) }, accessToken),

  updateTask: (accessToken: string, projectId: string, taskId: string, body: object) =>
    request(`/projects/${projectId}/tasks/${taskId}`, { method: "PATCH", body: JSON.stringify(body) }, accessToken),

  deleteTask: (accessToken: string, projectId: string, taskId: string) =>
    request(`/projects/${projectId}/tasks/${taskId}`, { method: "DELETE" }, accessToken),
};
