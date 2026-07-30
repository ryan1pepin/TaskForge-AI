import { useQuery, useMutation } from "@tanstack/react-query"
import { useNavigate } from "react-router-dom"
import { api } from "../api/client"
import type { ProjectResponse } from "../schemas/project"

export default function ProjectList() {
  const navigate = useNavigate()

  const { data, isLoading } = useQuery<ProjectResponse[]>({
    queryKey: ["projects"],
    queryFn: () => api.getProjects(),
  })

  const createMutation = useMutation({
    mutationFn: (body: { title: string; description?: string }) => api.createProject(body),
    onSuccess: () => navigate("/projects"),
  })

  if (isLoading) return <p className="p-6">Loading projects...</p>

  return (
    <div className="w-full p-6">
      <h1 className="mb-6 text-xl font-bold">My Projects</h1>

      <button onClick={() => navigate("/projects/new")}
              className="mb-4 rounded bg-blue-600 px-4 py-2 text-white hover:bg-blue-700">
        + New Project
      </button>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {data?.map((p: ProjectResponse) => (
          <div key={p.id} onClick={() => navigate("/projects/" + p.id)}
               className="cursor-pointer rounded border bg-white p-5 shadow hover:border-blue-400">
            <h2 className="font-semibold">{p.title}</h2>
            {p.description && <p className="mt-1 text-sm text-gray-600">{p.description.slice(0, 120)}</p>}
            <span className="inline-block mt-3 rounded bg-gray-100 px-2 py-0.5 text-xs capitalize">
              {p.status}
            </span>
          </div>
        ))}
      </div>

      {data?.length === 0 && (
        <p className="mt-8 text-center text-gray-500">No projects yet. Create one to get started.</p>
      )}
    </div>
  )
}
