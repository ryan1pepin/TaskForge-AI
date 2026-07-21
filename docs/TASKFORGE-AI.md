# TaskForge AI — Full Codebase Documentation

## Overview

Full-stack project management application with secure JWT authentication, PostgreSQL backend, and React/TypeScript frontend. Built as a learning exercise for interview-level fullstack skills (Phase 1 complete, Phase 2 TBD).

**Stack:** FastAPI + SQLAlchemy 2.0 (async) + Argon2 + PyJWT ↔ React 19 + Vite 8 + TypeScript + Zustand + TanStack Query v5 + Zod v4 + TailwindCSS v4

---

## Directory Structure

```
TaskForge AI/
├── docker-compose.yml          # PostgreSQL 15 container
├── TaskForge_Phase1_Checklist.md  # Phase goals and concept checkpoints
│
├── backend/
│   ├── requirements.txt        # Python dependencies
│   ├── alembic.ini             # Alembic config
│   ├── alembic/
│   │   ├── env.py              # Async migration runner (auto-generated)
│   │   └── versions/
│   │       └── e728181a0c91_init_schema.py  # Manual initial migration
│   ├── app/
│   │   ├── main.py             # FastAPI app factory + CORS + route registration
│   │   ├── config.py           # Pydantic Settings (DB URL, JWT, CORS)
│   │   ├── db.py               # Async engine, session factory, DeclarativeBase
│   │   ├── models.py           # SQLAlchemy 2.0 ORM models (User, RefreshToken, Project, Task)
│   │   ├── schemas.py          # Pydantic v2 request/response schemas
│   │   ├── security.py         # Argon2 hashing + JWT encode/decode
│   │   ├── dependencies.py     # FastAPI DI: get_current_user from Bearer token
│   │   └── routes/
│   │       ├── auth.py         # /auth/register, login, refresh, logout
│   │       ├── projects.py     # /projects CRUD (soft delete + pagination)
│   │       └── tasks.py        # /projects/{id}/tasks CRUD (ordered by order_index)
│   └── tests/
│       ├── conftest.py         # Pytest fixtures: in-memory SQLite, ASGITransport client
│       ├── test_auth.py        # Register, login, refresh token rotation, replay detection
│       └── test_crud.py        # Project/task CRUD lifecycle, pagination, cascade soft delete
│
├── frontend/
│   ├── package.json            # React 19, TanStack Query v5, Zustand, Zod v4, Tailwind v4
│   ├── vite.config.ts          # Vite + React + Tailwind plugin + /api proxy → :8000
│   ├── tsconfig.json           # TypeScript ~6.0 strict config
│   └── src/
│       ├── main.tsx            # Entry: QueryClient setup, StrictMode render
│       ├── App.tsx             # Session restore hook + auth status UI (scaffold)
│       ├── index.css           # @import "tailwindcss"
│       ├── api/
│       │   └── client.ts       # Thin fetch-based API client with ApiError class
│       ├── store/
│       │   └── auth.ts         # Zustand memory-only access token store (XSS-safe)
│       └── schemas/
│           ├── auth.ts         # Zod: TokenResponseSchema, AuthCredentialsSchema
│           ├── project.ts      # Zod: ProjectResponse/Create/Update + status enum
│           └── task.ts         # Zod: TaskResponse/Create/Update + status/priority enums
```

---

## Architecture & Design Decisions

### Authentication Pattern (Interview-Worthy)

**Access Token:** Short-lived JWT (5 min), stored in **Zustand memory store only** (never localStorage → XSS protection). Contains `sub` (user UUID) and `type: "access"`.

**Refresh Token:** Long-lived (30 days), stored as **httpOnly cookie** by the backend. The raw token is never returned to JS; instead its SHA256 hash is persisted in PostgreSQL (`refresh_tokens.token_hash`).

### Refresh Token Rotation (RTR)

On every `/auth/refresh` call:
1. Look up submitted refresh token's hash in DB
2. If `revoked_at` is already set → **replay attack detected** → revoke ALL active tokens for that user, return 401 with "Session compromised"
3. Otherwise: set `revoked_at` on current token, generate fresh access JWT + new refresh token, set new httpOnly cookie

### Session Restore Flow

On app mount (`App.tsx`), `useSessionRestore()` calls `/auth/refresh`. The browser automatically includes the httpOnly cookie. On success, the new access token is stored in Zustand memory. On 401 (no valid session), the user stays logged out — no UI flash.

### Soft Delete Pattern

All projects and tasks use `deleted_at TIMESTAMP WITH TIME ZONE` instead of hard deletes. Benefits:
- Audit trail preserved
- Foreign key integrity maintained (tasks cascade-deleted when project is soft-deleted via manual loop)
- Queries filter on `deleted_at IS NULL`
- Composite indexes include `deleted_at` for efficient filtering

### Security Choices

| Choice | Rationale |
|--------|-----------|
| Argon2 over bcrypt | Memory-hard, GPU-resistance, future-proof against ASIC attacks |
| UUID primary keys | Prevent enumeration attacks (sequential IDs leak data) |
| httpOnly cookies for refresh tokens | Immune to XSS theft |
| Memory-only access token | Lost on page refresh; forces re-auth from cookie rather than localStorage which any JS can read |
| SHA256 hash of refresh tokens in DB | Database breach doesn't give usable session tokens |
| SameSite=Lax | CSRF protection for cross-site requests |

### API Client Design

The frontend deliberately **avoids Axios** to reduce bundle size and prevent interceptor conflicts with TanStack Query's own retry/rollback lifecycle. Uses a thin fetch wrapper that:
- Attaches Bearer token from Zustand store
- Sets `credentials: "include"` for httpOnly cookie transport
- Returns structured `ApiError` with status code + detail message

---

## Database Schema (PostgreSQL)

### users
| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK, default uuid_generate |
| email | VARCHAR(255) | UNIQUE, NOT NULL, indexed |
| password_hash | VARCHAR(255) | NOT NULL (Argon2) |
| created_at | TIMESTAMPTZ | NOT NULL, server_default now() |
| updated_at | TIMESTAMPTZ | NOT NULL, auto-updated |

### refresh_tokens
| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| user_id | UUID | FK → users.id ON DELETE CASCADE |
| token_hash | VARCHAR(255) | UNIQUE, NOT NULL, indexed (SHA256 of raw token) |
| expires_at | TIMESTAMPTZ | NOT NULL |
| revoked_at | TIMESTAMPTZ | nullable |
| **Index** | `idx_rt_user_expires(user_id, expires_at)` | Composite for active session queries |

### projects
| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| owner_id | UUID | FK → users.id ON DELETE CASCADE |
| title | VARCHAR(255) | NOT NULL |
| description | VARCHAR(1000) | nullable |
| status | VARCHAR(50) | NOT NULL, default 'draft' (enum: draft/active/archived) |
| created_at | TIMESTAMPTZ | NOT NULL |
| updated_at | TIMESTAMPTZ | NOT NULL |
| deleted_at | TIMESTAMPTZ | nullable (soft delete marker) |
| **Index** | `idx_proj_owner_status_deleted(owner_id, status, deleted_at)` | Composite for paginated list queries |

### tasks
| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| project_id | UUID | FK → projects.id ON DELETE CASCADE |
| title | VARCHAR(255) | NOT NULL |
| description | VARCHAR(1000) | nullable |
| status | VARCHAR(50) | NOT NULL, default 'todo' (enum: todo/in_progress/done) |
| priority | SMALLINT | NOT NULL, 0-3, CHECK constraint |
| order_index | INTEGER | NOT NULL, for drag-and-drop ordering |
| due_date | TIMESTAMPTZ | nullable |
| created_at | TIMESTAMPTZ | NOT NULL |
| updated_at | TIMESTAMPTZ | NOT NULL |
| deleted_at | TIMESTAMPTZ | nullable (soft delete marker) |
| **Index** | `idx_task_proj_order_deleted(project_id, order_index, deleted_at)` | Composite for ordered task queries |

---

## API Endpoints (all under `/api/v1`)

### Auth (`/auth/*`)
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/auth/register` | Public | Create user, issue access token + refresh cookie |
| POST | `/auth/login` | Public | Verify credentials, issue tokens |
| POST | `/auth/refresh` | Cookie | Rotate refresh token, issue new access token |
| POST | `/auth/logout` | Cookie | Revoke refresh token, clear cookie |

### Projects (`/projects/*`)
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/projects` | Bearer | Create project (owned by current user) |
| GET | `/projects` | Bearer | List active projects (limit/offset pagination, optional status filter) |
| GET | `/projects/{id}` | Bearer | Get single project detail |
| PATCH | `/projects/{id}` | Bearer | Partial update |
| DELETE | `/projects/{id}` | Bearer | Soft delete (cascades to tasks) |

### Tasks (`/projects/{pid}/tasks/*`)
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `.../tasks` | Bearer | Create task in owned project |
| GET | `.../tasks` | Bearer | List active tasks (sorted by order_index, optional status filter) |
| PATCH | `.../tasks/{tid}` | Bearer | Partial update |
| DELETE | `.../tasks/{tid}` | Bearer | Soft delete |

### Health
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/health` | Public | Returns `{"status": "ok"}` |

---

## Schema Matching (Pydantic ↔ Zod)

The frontend Zod schemas in `src/schemas/` are **manually written mirrors** of the backend Pydantic schemas in `app/schemas.py`:

| Backend (Pydantic) | Frontend (Zod) | Notes |
|--------------------|----------------|-------|
| `UUID` | `z.string().uuid()` | FastAPI serializes UUIDs to ISO-8601 strings |
| `datetime` | `z.string().datetime()` | FastAPI outputs ISO-8601 format |
| `Optional[str]` | `.nullable().optional()` | Python None → JSON null |
| `Field(min_length=8)` | `.min(8, "message")` | Equivalent constraint |
| Enum classes | `z.enum([...])` | Case-sensitive value match |

**Why validate on both sides?** Client validation (Zod) catches user input errors before network call. Server validation (Pydantic) is the security boundary — never trust client data. The dual-layer approach protects against malicious clients and contract drift between deployments.

---

## Testing Strategy

### Test Database
Uses **SQLite in-memory** via `aiosqlite` for offline testing without Docker/Postgres. Override `settings.DATABASE_URL` to `sqlite+aiosqlite:///:memory:` in `conftest.py`. Tables are created/dropped at session scope; each test runs in a rolled-back transaction.

### Test Client
Uses `httpx.AsyncClient` with `ASGITransport` for in-process request testing (no real HTTP server). The DB dependency is overridden to use the fixture-managed session.

### Coverage Areas
- **Auth tests:** Register success, duplicate email rejection, login success/failure, refresh token rotation, replay attack detection, logout revocation
- **CRUD tests:** Full project lifecycle (create→read→list→update→soft delete), pagination, task ordering, cascade soft delete verification

---

## Running the Project

### Prerequisites
- Python 3.14+ (based on pycache extensions showing cpython-314)
- Node.js (vite client)
- Docker (for PostgreSQL) or local Postgres 15

### Backend Setup
```bash
cd "H:\projects\TaskForge AI\backend"
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
# Run migrations
alembic upgrade head
# Start server
uvicorn app.main:app --reload --port 8000
```

### Frontend Setup
```bash
cd "H:\projects\TaskForge AI\frontend"
npm install
npm run dev
# Dev server on :5173, proxies /api → localhost:8000
```

### Running Tests
```bash
cd "H:\projects\TaskForge AI\backend"
pytest
```

---

## Docker (Production-Ready Database)

The `docker-compose.yml` runs PostgreSQL 15 Alpine with persistent volume. The backend connects via `postgresql+asyncpg://postgres:postgres@localhost:5432/taskforge`.

---

## Phase 2 (TBD / Roadmap)

Phase 1 establishes the foundation. Likely next phases:
- **UI components:** Login/register forms, project list/detail views, task boards, drag-and-drop reordering
- **AI features:** Task suggestion, auto-prioritization, deadline prediction (the "AI" in TaskForge AI)
- **Collaboration:** Shared projects, role-based access control, comments/activity feeds
- **Real-time:** WebSockets for live task updates across clients
- **Deployment:** Docker Compose for full stack, CI/CD pipeline

---

## Key Interview Talking Points

1. **Why Argon2 over bcrypt?** Memory-hardness provides GPU-resistance; bcrypt is vulnerable to GPU parallelism. Argon2id (default) resists both side-channel and GPU attacks.

2. **Why httpOnly cookies + memory tokens instead of localStorage?** localStorage is readable by any injected script (XSS). httpOnly cookies are immune. The short-lived access token in memory is lost on refresh, forcing a secure cookie-based restore — no persistent XSS target.

3. **Why refresh token rotation over simple expiry?** Without rotation, a stolen refresh token works for 30 days. With rotation, each use revokes the previous token — detection of replay within seconds of theft. If a stolen token is replayed before the legitimate client rotates it, ALL sessions are killed (compromised session).

4. **Why soft deletes?** Audit trail preservation, soft-delete recovery workflows, and cascade-safe foreign keys. Real-world apps rarely do hard deletes on business entities.

5. **Why composite indexes?** Single-column indexes don't help multi-column WHERE clauses. `(owner_id, status, deleted_at)` exactly matches our most common query pattern: "find owner's non-deleted active projects."

6. **Why manual migrations over autogenerate?** Autogenerate can miss subtle changes (column type narrowing, index order, check constraints). Manual migrations are auditable, reviewable in PRs, and production-safe.

7. **Why avoid Axios?** Bundle size (~30KB gzip), interceptor conflicts with TanStack Query's own retry/rollback, and the native fetch API is sufficient for most needs when wrapped properly.
