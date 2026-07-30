import { Outlet, Link, useNavigate, useLocation } from "react-router-dom"
import { useAuthStore } from "./store/auth"
import { api } from "./api/client"
import Logo from "./assets/logo.svg"

export default function Layout() {
  const accessToken = useAuthStore((s) => s.accessToken)
  const clearAuth = useAuthStore((s) => s.clearAuth)
  const navigate = useNavigate()
  const location = useLocation()

  async function handleLogout() {
    try {
      await api.logout()
    } finally {
      clearAuth()
      navigate("/login")
    }
  }

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100 flex">
      <aside className="w-64 min-h-screen border-r border-gray-800 p-6 flex flex-col">
        <Link to="/" className="flex items-center gap-2 mb-8">
          <Logo className="h-7 w-7" />
          <span className="text-lg font-bold">TaskForge</span>
        </Link>

        <nav className="space-y-1 flex-1">
          <Link
            to="/"
            className={`flex items-center gap-3 px-3 py-2 rounded-md text-sm ${
              location.pathname === "/" ? "bg-gray-800" : ""
            }`}
          >
            Dashboard
          </Link>
          <Link
            to="/projects"
            className={`flex items-center gap-3 px-3 py-2 rounded-md text-sm ${
              location.pathname.startsWith("/projects") ? "bg-gray-800" : ""
            }`}
          >
            Projects
          </Link>
        </nav>

        <div className="pt-4 border-t border-gray-800">
          <button onClick={handleLogout} className="text-sm text-gray-400 hover:text-white">
            Logout
          </button>
        </div>
      </aside>

      <main className="flex-1 p-6 overflow-y-auto">
        <Outlet />
      </main>
    </div>
  )
}
