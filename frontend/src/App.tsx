import { useEffect } from "react";
import { useAuthStore } from "./store/auth";
import { api, ApiError } from "./api/client";
import { TokenResponseSchema } from "./schemas/auth";

// ── Silent Session Restore ────────────────────────────────────────────────────
// On mount, attempt to silently restore the session by calling /auth/refresh.
// The browser automatically sends the httpOnly refresh cookie — we just need
// to receive the new access token and store it in the Zustand memory store.
// If this fails (expired or no cookie), the user stays logged out.
function useSessionRestore() {
  const setAccessToken = useAuthStore((s) => s.setAccessToken);

  useEffect(() => {
    api
      .refresh()
      .then((data) => {
        const parsed = TokenResponseSchema.safeParse(data);
        if (parsed.success) {
          setAccessToken(parsed.data.access_token);
        }
      })
      .catch((err: ApiError) => {
        // 401 = no valid session → stay logged out, that's fine
        if (err.status !== 401) {
          console.error("Session restore failed unexpectedly:", err);
        }
      });
  }, [setAccessToken]);
}

export default function App() {
  useSessionRestore();
  const accessToken = useAuthStore((s) => s.accessToken);

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100 flex items-center justify-center">
      <div className="text-center space-y-4">
        <h1 className="text-4xl font-bold tracking-tight">
          TaskForge <span className="text-indigo-400">AI</span>
        </h1>
        <p className="text-gray-400 text-lg">
          Phase 1 scaffold — backend connected
        </p>
        <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-gray-800 text-sm">
          <span
            className={`h-2 w-2 rounded-full ${
              accessToken ? "bg-green-400" : "bg-yellow-400"
            }`}
          />
          {accessToken ? "Session active" : "Not authenticated"}
        </div>
      </div>
    </div>
  );
}
