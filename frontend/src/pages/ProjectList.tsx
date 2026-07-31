import { useQuery } from "@tanstack/react-query"
import { useNavigate } from "react-router-dom"
import { api } from "../api/client"
import type { ProjectResponse } from "../schemas/project"

export default function ProjectList() {
  const navigate = useNavigate()

  const { data, isLoading } = useQuery<ProjectResponse[]>({
    queryKey: ["projects"],
    queryFn: () => api.getProjects(),
  })

  if (isLoading) return <p className="p-6 text-gray-300">Loading projects...</p>

  return (
    <div className="w-full p-6">
      <h1 className="mb-8 text-2xl font-bold text-gray-100 tracking-tight">My Projects</h1>

      <button
        onClick={() => navigate("/projects/new")}
        className="mb-8 inline-flex items-center gap-2 rounded-lg bg-violet-600 px-5 py-2.5 text-sm font-semibold text-white shadow-lg shadow-violet-900/40 transition-all hover:bg-violet-500 hover:shadow-violet-600/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-violet-400"
      >
        <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
        </svg>
        New Project
      </button>

      {data?.length === 0 && (
        <div className="mt-12 flex items-center justify-center rounded-xl border border-dashed border-gray-700 bg-gray-900/50 py-24 text-center">
          <div>
            <svg xmlns="http://www.w3.org/2000/svg" className="mx-auto mb-4 h-12 w-12 text-gray-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 12.75V12A2.25 2.25 0 0 1 4.5 9.75h15a2.25 2.25 0 0 1 2.25 2.25v.75m-8.69-6.44-1.25-1.25a2.25 2.25 0 0 1-1.59-.65L6.75 2.25M3.75 13.5h16.5" />
            </svg>
            <p className="text-gray-400">No projects yet</p>
            <button
              onClick={() => navigate("/projects/new")}
              className="mt-3 text-violet-400 underline hover:text-violet-300"
            >
              Create one to get started
            </button>
          </div>
        </div>
      )}

      <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
        {data?.map((p) => (
          <button
            key={p.id}
            onClick={() => navigate("/projects/" + p.id)}
            className="group relative flex flex-col rounded-xl border border-gray-700/60 bg-gradient-to-b from-gray-800 to-gray-900 p-6 text-left shadow-[0_4px_12px_rgba(0,0,0,.35)] transition-all duration-200 hover:-translate-y-1 hover:border-violet-500/40 hover:shadow-[0_8px_24px_rgba(124,58,237,.25)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-violet-400 before:absolute before:-inset-px before:rounded-xl before:border before:border-transparent before:transition-colors before:hover:border-violet-500/20"
          >
            {/* Top accent line */}
            <div className="absolute inset-x-6 -top-px h-px bg-gradient-to-r from-transparent via-violet-500/40 to-transparent opacity-0 transition-opacity group-hover:opacity-100" />

            <span className="-mb-2 text-sm font-medium uppercase tracking-widest text-violet-400">
              {p.status}
            </span>

            <h2 className="mt-1 line-clamp-2 text-lg font-bold text-gray-50 transition-colors group-hover:text-white">
              {p.title}
            </h2>

            {p.description && (
              <p className="mt-2 line-clamp-3 flex-1 text-sm leading-relaxed text-gray-400">{p.description}</p>
            )}

            {/* Bottom status bar indicator */}
            <div className="mt-5 flex items-center justify-between">
              <span className={`inline-h-block h-2 w-2 rounded-full ${statusDot(p.status)}`} />
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" className="mt-1 text-gray-500 transition-transform group-hover:translate-x-1" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
              </svg>
            </div>
          </button>
        ))}
      </div>
    </div>
  )
}

function statusDot(status: string): string {
  switch (status.toLowerCase()) {
    case "active": return "bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,.6)]"
    case "completed": return "bg-blue-400 shadow-[0_0_8px_rgba(96,165,250,.6)]"
    case "on-hold": return "bg-amber-400 shadow-[0_0_8px_rgba(251,191,36,.6)]"
    default: return "bg-gray-500"
  }
}
