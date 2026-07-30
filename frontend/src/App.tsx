import { useEffect, useState } from "react"
import { createBrowserRouter, RouterProvider, Navigate, Outlet } from "react-router-dom"
import Layout from "./Layout"
import Login from "./pages/Login"
import Register from "./pages/Register"
import ProjectList from "./pages/ProjectList"
import ProjectDetail from "./pages/ProjectDetail"
import NewProject from "./pages/NewProject"
import { useAuthStore } from "./store/auth"
import { api } from "./api/client"

function ProtectedRoute() {
  const accessToken = useAuthStore(state => state.accessToken)
  
  if (!accessToken) {
    return <Navigate to="/login" replace />
  }
  
  return <Outlet />
}

function SessionRestore({ children }: { children: React.ReactNode }) {
  const [isRestoring, setIsRestoring] = useState(true)
  const setAccessToken = useAuthStore(state => state.setAccessToken)

  useEffect(() => {
    async function restoreSession() {
      try {
        const data = await api.refresh()
        // Ensure data is typed or at least check for access_token
        if (data && (data as any).access_token) {
          setAccessToken((data as any).access_token)
        }
      } catch (err) {
        // silently fail, user must log in
      } finally {
        setIsRestoring(false)
      }
    }
    restoreSession()
  }, [setAccessToken])

  if (isRestoring) return <div className="flex h-screen items-center justify-center">Loading session...</div>

  return <>{children}</>
}

const router = createBrowserRouter([
  {
    path: "/",
    element: (
      <SessionRestore>
        <Layout />
      </SessionRestore>
    ),
    children: [
      {
        element: <ProtectedRoute />,
        children: [
          { index: true, element: <ProjectList /> },
          { path: "projects/new", element: <NewProject /> },
          { path: "projects/:projectId", element: <ProjectDetail /> },
        ]
      }
    ],
  },
  { path: "/login", element: <SessionRestore><Login /></SessionRestore> },
  { path: "/register", element: <SessionRestore><Register /></SessionRestore> },
])

export default function App() {
  return <RouterProvider router={router} />
}

