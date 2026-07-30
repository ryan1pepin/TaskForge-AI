import { useState, FormEvent } from "react"
import { Link, useNavigate } from "react-router-dom"
import { api } from "../api/client"
import { useAuthStore } from "../store/auth"

export default function Register() {
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [confirm, setConfirm] = useState("")
  const [error, setError] = useState("")
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()
  const setAccessToken = useAuthStore(s => s.setAccessToken)

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setError("")
    if (password !== confirm) { setError("Passwords do not match"); return }
    if (password.length < 8)   { setError("Password must be at least 8 characters"); return }
    setLoading(true)
    try {
      const data = await api.register(email, password)
      if (data && data.access_token) {
        setAccessToken(data.access_token)
        navigate("/projects")
      } else {
        setError("Registration failed")
      }
    } catch (err: unknown) {
      setError((err as { detail?: string })?.detail ?? "Something went wrong")
    } finally { setLoading(false) }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 p-4">
      <form onSubmit={onSubmit} className="w-full max-w-sm rounded-lg bg-white p-8 shadow">
        <h1 className="mb-6 text-center text-2xl font-bold">Create account</h1>
        {error && <p className="mb-4 text-sm text-red-600">{error}</p>}
        <label className="mb-4 block">
          <span className="text-sm font-medium">Email</span>
          <input value={email} onChange={e => setEmail(e.target.value)} type="email" required
                 className="mt-1 w-full rounded border p-2" />
        </label>
        <label className="mb-4 block">
          <span className="text-sm font-medium">Password</span>
          <input value={password} onChange={e => setPassword(e.target.value)} type="password" minLength={8} required
                 className="mt-1 w-full rounded border p-2" />
        </label>
        <label className="mb-6 block">
          <span className="text-sm font-medium">Confirm</span>
          <input value={confirm} onChange={e => setConfirm(e.target.value)} type="password" required
                 className="mt-1 w-full rounded border p-2" />
        </label>
        <button disabled={loading} type="submit"
                className="w-full rounded bg-blue-600 py-2 font-semibold text-white hover:bg-blue-700">
          {loading ? "Creating..." : "Register"}
        </button>
        <p className="mt-4 text-center text-sm">
          Already have an account? <Link to="/login" className="text-blue-600 underline">Log in</Link>
        </p>
      </form />
    </div>
  )
}
