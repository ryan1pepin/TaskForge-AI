import { create } from "zustand";

// ── Auth Store ────────────────────────────────────────────────────────────────
// Access token lives only in memory (Zustand), never in localStorage.
// Rationale: localStorage is readable by any JS on the page (XSS risk).
// The refresh token lives in an httpOnly cookie managed entirely by the browser —
// we never touch it directly from JS.
//
// Interview talking point:
//   "Memory storage means the token is lost on page refresh — that's intentional.
//    We call /auth/refresh on mount to silently restore the session from the
//    httpOnly cookie. This gives XSS protection without requiring the user to
//    log in again on every page load."

interface AuthState {
  accessToken: string | null;
  setAccessToken: (token: string | null) => void;
  clearAuth: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  accessToken: null,

  setAccessToken: (token) => set({ accessToken: token }),

  clearAuth: () => set({ accessToken: null }),
}));
