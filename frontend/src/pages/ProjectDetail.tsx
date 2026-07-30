import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { useState, FormEvent } from "react"
import { useParams, useNavigate } from "react-router-dom"
import { api } from "../api/client"
import type { TaskResponse } from "../schemas/task"

type Column = "todo" | "in_progress" | "done"

const COLUMNS: { key: Column; label: string }[] = [
  { key: "todo", label: "To Do" },
  { key: "in_progress", label: "In Progress" },
  { key: "done", label: "Done" },
]

export default function ProjectDetail() {
  const { projectId } = useParams<{ projectId: string }>()
  const navigate = useNavigate()
  const qc = useQueryClient()

  const { data: tasks, isLoading: loadingTasks } = useQuery<TaskResponse[]>({
    queryKey: ["tasks", projectId],
    queryFn: () => api.getTasks(projectId!),
  })

  // Group tasks by status
  const todo      = tasks?.filter(t => t.status === "todo") ?? []
  const inProgress = tasks?.filter(t => t.status === "in_progress") ?? []
  const done       = tasks?.filter(t => t.status === "done") ?? []

  // Update mutation
  const update = useMutation({
    mutationFn: ({ taskId, status }: { taskId: string; status: Column }) =>
      api.updateTask(projectId!, taskId, { status }),
    onSettled: () => qc.invalidateQueries({ queryKey: ["tasks"] }),
  })

  // Delete mutation
  const remove = useMutation({
    mutationFn: (taskId: string) => api.deleteTask(projectId!, taskId),
    onSettled: () => qc.invalidateQueries({ queryKey: ["tasks"] }),
  })

  // Inline add form
  const [newTitle, setNewTitle] = useState("")
  const handleAdd = async (e: FormEvent) => {
    e.preventDefault()
    if (!newTitle.trim()) return
    await api.createTask(projectId!, { title: newTitle })
    setNewTitle("")
    qc.invalidateQueries({ queryKey: ["tasks"] })
  }

  // AI actions
  const [aiMsg, setAiMsg] = useState("")
  const aiPriority = async (taskId: string) => {
    try {
      const r = await api.suggestPriority(projectId!, taskId)
      setAiMsg(`Suggested priority: ${r.suggested_priority} — ${r.reasoning}`)
    } catch { setAiMsg("AI unavailable") }
  }
  const aiDeadline = async (taskId: string) => {
    try {
      const r = await api.suggestDeadline(projectId!, taskId)
      setAiMsg(`Suggested deadline: ${r.suggested_due_date ?? "none"} — ${r.reasoning}`)
    } catch { setAiMsg("AI unavailable") }
  }
  const aiDesc = async (taskId: string) => {
    try {
      const r = await api.generateDescription(projectId!, taskId)
      setAiMsg(`Expanded:\n${r.description}`)
      // Optionally apply to task
      await api.updateTask(projectId!, taskId, { description: r.description })
      qc.invalidateQueries({ queryKey: ["tasks"] })
    } catch { setAiMsg("AI unavailable") }
  }

  if (loadingTasks) return <p className="p-6">Loading tasks...</p>

  const colMap: Record<Column, TaskResponse[]> = { todo, in_progress: inProgress, done }

  return (
    <div className="p-6">
      <div className="mb-4 flex items-center justify-between">
        <button onClick={() => navigate("/projects")} className="text-sm text-blue-500 hover:underline">
          ← Projects
        </button>
      </div>

      {/* Quick add */}
      <form onSubmit={handleAdd} className="mb-6 flex gap-2">
        <input value={newTitle} onChange={e => setNewTitle(e.target.value)} placeholder="Add a task..."
               className="flex-1 rounded border p-2" />
        <button type="submit" className="rounded bg-blue-600 px-4 py-2 text-white hover:bg-blue-700">Add</button>
      </form>

      {/* AI message toast */}
      {aiMsg && (
        <div onClick={() => setAiMsg("")} className="mb-4 cursor-pointer rounded bg-gray-800 p-3">
          <pre className="whitespace-pre-wrap text-sm">{aiMsg}</pre>
          <span className="text-xs text-gray-400">Click to dismiss</span>
        </div>
      )}

      {/* Kanban columns */}
      <div className="grid gap-4 md:grid-cols-3">
        {COLUMNS.map(col => (
          <div key={col.key} className="rounded bg-gray-800 p-3">
            <h2 className="mb-3 font-semibold capitalize">{col.label}</h2>
            <div className="space-y-2">
              {(colMap[col.key] ?? []).map(task => (
                <div key={task.id} className="rounded border bg-gray-900 p-3">
                  <p className="font-medium text-sm">{task.title}</p>
                  {task.description && <p className="mt-1 text-xs text-gray-400 line-clamp-2">{task.description.slice(0, 80)}</p>}
                  {task.due_date && <p className="mt-1 text-xs text-yellow-400">Due: {new Date(task.due_date).toLocaleDateString()}</p>}

                  <div className="mt-2 flex gap-1 flex-wrap">
                    {/* Move buttons */}
                    {col.key !== "todo" && (
                      <button onClick={() => {
                        const prev = col.key === "in_progress" ? "todo" : "in_progress"
                        update.mutate({ taskId: task.id, status: prev })
                      }} className="text-xs rounded border px-2 py-0.5 hover:bg-gray-700">←</button>
                    )}
                    {col.key !== "done" && (
                      <button onClick={() => {
                        const next = col.key === "todo" ? "in_progress" : "done"
                        update.mutate({ taskId: task.id, status: next })
                      }} className="text-xs rounded border px-2 py-0.5 hover:bg-gray-700">→</button>
                    )}

                    {/* AI buttons */}
                    <button onClick={() => aiPriority(task.id)} title="AI suggest priority"
                            className="text-xs rounded border px-2 py-0.5 text-purple-400 hover:bg-gray-700">AI-Pri</button>
                    <button onClick={() => aiDeadline(task.id)} title="AI suggest deadline"
                            className="text-xs rounded border px-2 py-0.5 text-purple-400 hover:bg-gray-700">AI-Due</button>
                    <button onClick={() => aiDesc(task.id)} title="AI expand description"
                            className="text-xs rounded border px-2 py-0.5 text-purple-400 hover:bg-gray-700">AI-Desc</button>

                    {/* Delete */}
                    <button onClick={() => remove.mutate(task.id)} title="Delete"
                            className="text-xs rounded border px-2 py-0.5 text-red-400 hover:bg-gray-700">×</button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>

      {/* Project health score */}
      <ProjectHealth projectTitle={projectId} />
    </div>
  )
}

function ProjectHealth({ projectTitle }: { projectTitle?: string }) {
  const { projectId } = useParams<{ projectId: string }>()
  const { data } = useQuery({ queryKey: ["health", projectId], queryFn: () => api.projectHealth(projectId!) })
  if (!data) return null
  const color = data.score >= 7 ? "text-green-400" : data.score >= 4 ? "text-yellow-400" : "text-red-400"
  return (
    <div className="mt-6 rounded bg-gray-900 p-4">
      <h3 className={`text-lg font-bold ${color}`}>Health: {data.score}/10</h3>
      <p className="text-sm text-gray-400">{data.progress_pct}% complete — {data.completed}/{data.total} tasks done</p>
      {data.flag && <p className="mt-1 text-sm text-red-400">{data.flag}</p>}
    </div>
  )
}
