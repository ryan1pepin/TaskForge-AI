import { useState, FormEvent } from "react"
import { useNavigate } from "react-router-dom"
import { api } from "../api/client"

export default function NewProject() {
  const navigate = useNavigate()
  const [title, setTitle] = useState("")
  const [description, setDescription] = useState("")
  const [error, setError] = useState("")
  const [loading, setLoading] = useState(false)

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setError("")
    if (!title.trim()) { setError("Title is required"); return }
    setLoading(true)
    try {
      await api.createProject({ title, description: description || undefined })
      navigate("/")
    } catch (err: unknown) {
      setError((err as { detail?: string })?.detail ?? "Failed to create project")
    } finally { setLoading(false) }
  }

  return (
    <div className="mx-auto max-w-lg p-8">
      <button onClick={() => navigate(-1)} className="mb-4 text-sm text-blue-500 hover:underline">
        ← Back to projects
      </button>
      <h1 className="mb-6 text-xl font-bold">New Project</h1>

      <form onSubmit={onSubmit} className="space-y-4">
        {error && <p className="text-sm text-red-400">{error}</p>}

        <div>
          <label className="mb-1 block text-sm font-medium" htmlFor="title">Title</label>
          <input id="title" value={title} onChange={e => setTitle(e.target.value)} required
                 className="w-full rounded border bg-gray-900 p-2 text-white focus:outline-none focus:ring-2 focus:ring-blue-500" />
        </div>

        <div>
          <label className="mb-1 block text-sm font-medium" htmlFor="description">Description</label>
          <textarea id="description" value={description} onChange={e => setDescription(e.target.value)} rows={4}
                    className="w-full rounded border bg-gray-900 p-2 text-white focus:outline-none focus:ring-2 focus:ring-blue-500" />
        </div>

        <button type="submit" disabled={loading}
                className="rounded bg-blue-600 px-4 py-2 font-medium text-white hover:bg-blue-700 disabled:opacity-50">
          {loading ? "Creating..." : "Create Project"}
        </button>
      </form>
    </div>
  )
}
