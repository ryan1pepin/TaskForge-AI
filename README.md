# TaskForge AI

Full-stack project management application with AI-powered task insights. JWT-authenticated, async backend, React/TypeScript frontend.

## Features

- **Authentication** — Register/login with Argon2 password hashing, JWT access + refresh token rotation, logout flow
- **Project CRUD** — Create, read, update, and soft-delete projects owned by the current user
- **Task Management** — Kanban-style board with status transitions (todo → in progress → done), priority levels, due dates
- **AI Integration** — Smart task prioritization, deadline suggestions, description generation, and project health scoring via OpenAI

## Tech Stack

| Layer | Tech |
|---|---|
| Backend | FastAPI, SQLAlchemy 2.0 (async), PostgreSQL, Alembic |
| Frontend | React 19, Vite, TypeScript, TailwindCSS v4 |
| State | Zustand (client auth), TanStack Query v5 (server state) |
| Validation | Pydantic v2 ↔ Zod v4 (shared schema contracts) |
| AI | OpenAI API (GPT-4o-mini) for task insights |

## Quick Start

```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate  # or .\.venv\Scripts\activate on Windows
pip install -r requirements.txt
cp .env.example .env  # configure DB and OpenAI key
alembic upgrade head
uvicorn app.main:app --reload

# Frontend
cd frontend
npm install && npm run dev
```

## Architecture

- **Backend:** `backend/app/` — FastAPI with async sessions, dependency injection, Pydantic schemas, and route modules for auth/projects/tasks/AI endpoints
- **Frontend:** `frontend/src/` — Vite + React SPA with Zustand auth store, TanStack Query data fetching, Zod form validation, and a protected routing setup
- **Database:** PostgreSQL via asyncpg (SQLite in-test). Migrations managed by Alembic

## Project Structure

```
TaskForge AI/
├── backend/
│   └── app/
│       ├── main.py              # FastAPI entry point + CORS
│       ├── config.py            # Settings & environment variables
│       ├── routes/              # auth, projects, tasks, AI endpoints
│       ├── ai/                  # OpenAI client wrapper & prompts
│       └── models / schemas     # SQLAlchemy ORM + Pydantic validation
├── frontend/
│   └── src/
│       ├── pages/               # route components (Login, Register, Kanban)
│       ├── api/                 # Axios client with interceptors
│       └── store/               # Zustand auth + Query hooks
└── docker-compose.yml           # PostgreSQL + Redis services
```


