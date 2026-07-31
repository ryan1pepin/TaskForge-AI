import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { useState, useEffect, FormEvent } from "react"
import { useParams, useNavigate } from "react-router-dom"
import { api } from "../api/client"
import type { TaskResponse } from "../schemas/task"

type Column = "todo" | "in_progress" | "done"

const COLUMNS: { key: Column; label: string }[] = [
  { key: "todo", label: "To Do" },
  { key: "in_progress", label: "In Progress" },
  { key: "done", label: "Done" },
]

/* ── Priority helpers ── */
const PRI_LABELS = ["Low", "Medium", "High", "Critical"] as const
const priClass = (n: number) => n === 3 ? "bg-red-900/60 text-red-300" : n === 2 ? "bg-orange-900/60 text-orange-300" : n === 1 ? "bg-yellow-900/60 text-yellow-300" : "bg-gray-700 text-gray-400"

/* ── Main page ── */
export default function ProjectDetail() {
  const { projectId } = useParams<{ projectId: string }>()
  const navigate = useNavigate()
  const qc = useQueryClient()

  /* Queries & mutations */
  const { data: tasks, isLoading: loadingTasks } = useQuery<TaskResponse[]>({
    queryKey: ["tasks", projectId],
    queryFn: () => api.getTasks(projectId!),
  })

  const todo = tasks?.filter(t => t.status === "todo") ?? []
  const inProgress = tasks?.filter(t => t.status === "in_progress") ?? []
  const done = tasks?.filter(t => t.status === "done") ?? []
  const colMap: Record<Column, TaskResponse[]> = { todo, in_progress: inProgress, done }

  const update = useMutation({
    mutationFn: ({ taskId, ...body }: { taskId: string; [key: string]: any }) =>
      api.updateTask(projectId!, taskId, body),
    onSettled: () => qc.invalidateQueries({ queryKey: ["tasks"] }),
  })

  const remove = useMutation({
    mutationFn: (taskId: string) => api.deleteTask(projectId!, taskId),
    onSettled: () => qc.invalidateQueries({ queryKey: ["tasks"] }),
  })

  /* Add task */
  const [newTitle, setNewTitle] = useState("")
  const handleAdd = async (e: FormEvent) => {
    e.preventDefault()
    if (!newTitle.trim()) return
    await api.createTask(projectId!, { title: newTitle })
    setNewTitle("")
    qc.invalidateQueries({ queryKey: ["tasks"] })
  }

  /* AI toast */
  const [aiMsg, setAiMsg] = useState("")

  /* ── Render ── */
  if (loadingTasks) return <p className="p-6 text-gray-300">Loading project...</p>

  function onDropCol(e, colKey) {
    try {
      const tid = JSON.parse(e.dataTransfer.getData("text/plain")).id;
      update.mutate({ taskId: tid, status: colKey });
    } catch {} // ignore bad drops
  }

  return (
    <div className="space-y-8 p-6">
      <div className="flex items-center justify-between">
        <button onClick={() => navigate("/")} className="text-sm text-violet-400 hover:underline">← Projects</button>
      </div>

      {/* Add task */}
      <form onSubmit={handleAdd} className="flex gap-2">
        <input value={newTitle} onChange={e => setNewTitle(e.target.value)} placeholder="Add a task..."
          className="flex-1 rounded-lg border border-gray-700 bg-gray-900 px-4 py-2 text-sm text-gray-100 placeholder-gray-500 focus:border-violet-500 focus:outline-none" />
        <button type="submit" className="rounded-lg bg-violet-600 px-5 py-2 text-sm font-semibold text-white hover:bg-violet-500">Add Task</button>
      </form>

      {/* AI toast */}
      {aiMsg && (
        <div onClick={() => setAiMsg("")} className="cursor-pointer rounded-lg border border-gray-700 bg-gray-800/90 p-4 backdrop-blur">
          <p className="text-sm text-gray-300">{aiMsg}</p>
        </div>
      )}

      {/* Kanban board */}
      <div className="grid gap-4 md:grid-cols-3">
        {COLUMNS.map(col => (
          <section key={col.key} className="rounded-xl bg-gray-900/50 p-4"
            onDragOver={(e) => e.preventDefault()}
            onDrop={(e) => onDropCol(e, col.key)}
          >
            <div className="mb-4 flex items-center justify-between border-b border-gray-800 pb-2">
              <h2 className="text-sm font-semibold uppercase tracking-widest text-gray-400">{col.label}</h2>
              <span className="rounded-full bg-gray-800 px-2 py-0.5 text-xs text-gray-400">{colMap[col.key].length}</span>
            </div>
            <div className="space-y-3" style={{ minHeight: 100 }}>
              {colMap[col.key]?.map(task => (
                <TaskCard key={task.id} task={task} colKey={col.key}
                  onUpdate={(values) => update.mutate({ taskId: task.id, ...values })}
                  onDelete={() => remove.mutate(task.id)}
                  onAI={(type) => handleAI(task.id, type)} />
              ))}
            </div>
          </section>
        ))}
      </div>

      {/* Health */}
      <ProjectHealth projectId={projectId!} />
    </div>
  )

  /* ── AI actions (auto-apply) ── */
  async function handleAI(taskId: string, type: "priority" | "deadline" | "description") {
    try {
      if (type === "priority") {
        const r = await api.suggestPriority(projectId!, taskId)
        await api.updateTask(projectId!, taskId, { priority: Math.max(0, r.suggested_priority ?? 0) })
        setAiMsg(`Priority → ${PRI_LABELS[r.suggested_priority] || "unchanged"}`)
      } else if (type === "deadline") {
        const r = await api.suggestDeadline(projectId!, taskId)
        await api.updateTask(projectId!, taskId, { due_date: r.suggested_due_date ?? null })
        setAiMsg(`Due date → ${r.suggested_due_date?.slice(0, 10) || "none"}`)
      } else {
        const r = await api.generateDescription(projectId!, taskId)
        await api.updateTask(projectId!, taskId, { description: r.description })
        setAiMsg("Description updated")
      }
    } catch { setAiMsg("AI unavailable") }
  }
}

/* ── Task Card (standalone component for edit state) ── */
function TaskCard({ task, colKey, onDelete, onAI, onUpdate }: {
  task: TaskResponse; colKey: Column
  onUpdate?: (values: Record<string, any>) => void; onDelete: any
  onAI: (t: "priority" | "deadline" | "description") => void
}) {
  const [editing, setEditing] = useState(false)
  const qc = useQueryClient()
  const [d, setD] = useState({ title: task.title, desc: task.description ?? "", pri: task.priority, due: task.due_date ? task.due_date.slice(0, 10) : "" })

  // Sync if task changes externally (after parent refreshes)
  useEffect(() => {
    setD({ title: task.title, desc: task.description ?? "", pri: task.priority, due: task.due_date ? task.due_date.slice(0, 10) : "" })
  }, [task.id, task.title, task.description, task.priority, task.due_date])

  async function save() {
    await api.updateTask(task.project_id, task.id, {
      title: d.title, description: d.desc || undefined, priority: d.pri, due_date: d.due ? new Date(d.due).toISOString() : null,
    })
    setEditing(false)
    qc.invalidateQueries({ queryKey: ["tasks", task.project_id] })
  }

  const pri = PRI_LABELS[task.priority] ?? "?"
  const due = task.due_date ? new Date(task.due_date).toLocaleDateString() : null

  return (
    <div className="overflow-hidden rounded-lg border border-gray-700/60 bg-gradient-to-b from-gray-800 to-gray-900 shadow-md transition-all hover:border-violet-500/30 hover:shadow-violet-500/10 cursor-grab active:cursor-grabbing"
      draggable
      onDragStart={(e) => {
        e.dataTransfer.setData("text/plain", JSON.stringify({ id: task.id }));
        e.dataTransfer.effectAllowed = "move";
      }}
    >
      {editing ? (
        /* ── Edit form ── */
        <div className="p-4 space-y-2">
          <input value={d.title} onChange={e => setD({ ...d, title: e.target.value })}
            className="w-full rounded border border-violet-500/50 bg-gray-900 px-3 py-1.5 text-sm text-white focus:outline-none" />
          <textarea value={d.desc} onChange={e => setD({ ...d, desc: e.target.value })} rows={2} placeholder="Description..."
            className="w-full resize-none rounded border border-gray-600 bg-gray-900 px-3 py-1.5 text-xs text-gray-300 focus:border-violet-500/50 focus:outline-none" />
          <div className="flex items-center gap-2">
            <select value={d.pri} onChange={e => setD({ ...d, pri: +e.target.value })}
              className="rounded border border-gray-600 bg-gray-900 px-2 py-1 text-xs text-gray-300 focus:outline-none">
              <option value={0}>Low</option><option value={1}>Medium</option><option value={2}>High</option><option value={3}>Critical</option>
            </select>
            <input type="date" value={d.due} onChange={e => setD({ ...d, due: e.target.value })}
              className="rounded border border-gray-600 bg-gray-900 px-2 py-1 text-xs text-gray-300 focus:outline-none" />
          </div>
          <div className="flex gap-2">
            <button onClick={save} className="rounded bg-violet-600 px-3 py-1 text-xs font-semibold text-white hover:bg-violet-500">Save</button>
            <button onClick={() => setEditing(false)} className="rounded border border-gray-600 px-3 py-1 text-xs text-gray-400 hover:bg-gray-700">Cancel</button>
          </div>
        </div>
      ) : (
        /* ── Read-only card ── */
        <div className="p-4 relative">
          {/* Title + edit trigger */}
          <div className="flex items-start justify-between gap-2">
            <p className={`flex-1 text-sm font-semibold ${task.status === "done" ? "line-through text-gray-500" : "text-gray-100"}`}>
              {task.title}
            </p>
            <button onClick={() => setEditing(true)} title="Edit"
              className="shrink-0 rounded p-1 text-gray-500 hover:bg-gray-700 opacity-60 hover:opacity-100 transition-opacity">
              <svg width="14" height="14" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" d="M16.862 3.487a2.05 2.05 0 012.914 2.914l-9.36 9.36-4 1.24L7.138 14.9zM14.056 7.311l-2.828 2.828" />
              </svg>
            </button>
          </div>

          {/* Meta: priority badge + due date */}
          <div className="mt-2 flex items-center gap-2">
            <span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${priClass(task.priority)}`}>
              {pri}
            </span>
            {due && <span className="text-[10px] text-yellow-400/80">📅 {due}</span>}
          </div>

          {/* Description preview */}
          {task.description && (
            <p className="mt-2 line-clamp-2 text-xs text-gray-400 leading-relaxed">
              {task.description.length > 100 ? task.description.slice(0, 100) + "…" : task.description}
            </p>
          )}

          {/* Action buttons */}
          <div className="mt-3 flex flex-wrap items-center gap-1.5 border-t border-gray-800 pt-2">
            {/* Move arrows */}
            {colKey !== "todo" && (
              (() => {
                const prev = colKey === "in_progress" ? "todo" : "in_progress";
                return <button onClick={() => onUpdate?.({ status: prev })} title={`Move to ${COLUMNS.find(c => c.key === prev)?.label}`} className="text-xs rounded-full border border-gray-600 px-2 py-0.5 text-gray-400 hover:bg-gray-700">←</button>;
              })()
            )}
            {colKey !== "done" && (
              (() => {
                const next = colKey === "todo" ? "in_progress" : "done";
                return <button onClick={() => onUpdate?.({ status: next })} title={`Move to ${COLUMNS.find(c => c.key === next)?.label}`} className="text-xs rounded-full border border-gray-600 px-2 py-0.5 text-gray-400 hover:bg-gray-700">→</button>;
              })()
            )}
            <div className="h-4 w-px border-l border-gray-700" />
            <button onClick={() => onAI("priority")} title="AI suggest & apply priority"
              className="text-[10px] rounded-full border border-purple-500/30 px-2 py-0.5 text-purple-400 hover:bg-purple-500/10 transition">
              ⚡ Priority
            </button>
            <button onClick={() => onAI("deadline")} title="AI suggest & apply deadline"
              className="text-[10px] rounded-full border border-purple-500/30 px-2 py-0.5 text-purple-400 hover:bg-purple-500/10 transition">
              ⚡ Deadline
            </button>
            <button onClick={() => onAI("description")} title="AI expand & apply description"
              className="text-[10px] rounded-full border border-purple-500/30 px-2 py-0.5 text-purple-400 hover:bg-purple-500/10 transition">
              ⚡ Description
            </button>
            <div className="flex-grow" />
            <button onClick={onDelete} title="Delete"
              className="text-[10px] rounded-full border border-red-500/30 px-2 py-0.5 text-red-400 hover:bg-red-500/10 transition">
              ×
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

/* ── Project health ── */
function ProjectHealth({ projectId }: { projectId: string }) {
  const { data } = useQuery({ queryKey: ["health", projectId], queryFn: () => api.projectHealth(projectId) })
  if (!data) return null
  const color = data.score >= 7 ? "text-green-400" : data.score >= 4 ? "text-yellow-400" : "text-red-400"
  return (
    <div className="rounded-xl border border-gray-800 bg-gradient-to-br from-gray-900 to-gray-950 p-5">
      <h3 className={`text-lg font-bold ${color}`}>Health: {data.score}/10</h3>
      <p className="mt-1 text-sm text-gray-400">{data.progress_pct}% complete — {data.completed}/{data.total} tasks done</p>
      {data.flag && <p className="mt-2 text-sm text-red-400">{data.flag}</p>}
    </div>
  )
}
