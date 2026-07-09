---
tags:
  - taskforge-ai
  - phase-1
  - checklist
  - fullstack
status: in-progress
completion_rate: 0%
---

# 🗺️ TaskForge AI - Phase 1 Implementation Progress

This is your interactive checklist for Phase 1. Open this file directly in your **Obsidian** vault to track your progress and log your learning milestones.

> [!info] **Phase 1 Goal**
> Establish secure JWT authentication with refresh token rotation, database schemas with SQLAlchemy, basic CRUD endpoints for projects/tasks, and core validation matching between Zod and Pydantic.

---

## 🛠️ Step 1: Environment & Workspace Setup
*Establish the monorepo structure and install backend/frontend dependencies.*

- [ ] **Create folder structure**
	- `backend/` for the FastAPI project
	- `frontend/` for the React/TypeScript/Vite client
- [ ] **Configure backend dependencies**
	- Create `backend/requirements.txt`
	- Create python virtual environment: `python -m venv .venv`
	- Install packages: `pip install -r requirements.txt`
- [ ] **Initialize Frontend Client**
	- Create Vite React + TS app: `npm create vite@latest frontend -- --template react-ts`
	- Install dependencies: `npm i`
	- Install packages: TailwindCSS, Zustand, `@tanstack/react-query`, `zod`

🧠 **Concept Review:** 
- *Why is a monorepo beneficial for small-to-medium full-stack projects?*
- *What is the role of virtual environments in Python development?*

---

## 🗄️ Step 2: Database Schema & Manual Migrations
*Define SQL models and generate the initial database migration manually.*

- [ ] **Define database settings in `config.py`** using Pydantic Settings
- [ ] **Set up database async connection engine in `db.py`**
- [ ] **Write SQLAlchemy models in `models.py`**
	- [ ] `User` model (UUID PK, unique email, hashed password)
	- [ ] `RefreshToken` model (UUID PK, user_id FK, token hash, expires_at, revoked_at)
	- [ ] `Project` model (UUID PK, title, status enum, soft delete `deleted_at`)
	- [ ] `Task` model (UUID PK, project_id FK, status enum, order_index, soft delete `deleted_at`)
- [ ] **Initialize Alembic**
	- Run `alembic init alembic` from the `backend/` directory
	- Configure `env.py` to point to the async DB engine and SQLAlchemy metadata
- [ ] **Write manual migration step**
	- Generate migration: `alembic revision --message="init_schema"`
	- Write the database table definition and composite indexes inside `upgrade()` and `downgrade()`

🧠 **Active Recall Checkpoint:**
- *What makes a composite index `(owner_id, status)` efficient for project filtering?*
- *Why do we write migrations manually instead of relying on `alembic --autogenerate` for production schemas?*

---

## 🔑 Step 3: Secure Auth & JWT Rotation
*Implement Argon2 password hashing and secure token rotation.*

- [ ] **Write password utilities in `security.py`** using `argon2-cffi`
- [ ] **Implement access token generation** (5-minute expiry)
- [ ] **Implement refresh token generation** (30-day expiry, stored as cryptographically secure hash in DB)
- [ ] **Write authentication endpoints in `routes/auth.py`**
	- [ ] `/auth/register` (Password validation, Argon2 hash, User insertion)
	- [ ] `/auth/login` (Verify password, generate access JWT, set HTTP-only cookie with refresh token)
	- [ ] `/auth/refresh` (Check rotation, check reuse/replay attacks, generate new access token and new rotated refresh cookie)
	- [ ] `/auth/logout` (Revoke active refresh token, clear HTTP-only cookie)

🧠 **Security Review:**
- *How does storing the hash of a refresh token in the DB protect users compared to storing raw tokens?*
- *Explain the exact sequence of events when a client triggers a refresh token rotation (RTR).*

---

## 📁 Step 4: Project & Task CRUD Endpoints
*Build paginated, soft-deleted CRUD operations in FastAPI.*

- [ ] **Create basic Project CRUD routes in `routes/projects.py`**
	- [ ] `POST /projects` (Create project)
	- [ ] `GET /projects` (Read all active, support limit/offset pagination, filter out soft-deleted)
	- [ ] `PATCH /projects/{id}` (Update details)
	- [ ] `DELETE /projects/{id}` (Soft delete by setting `deleted_at` timestamp)
- [ ] **Create Task CRUD routes in `routes/tasks.py`**
	- [ ] `POST /projects/{pid}/tasks` (Create task with order index)
	- [ ] `GET /projects/{pid}/tasks` (Read all active tasks in project, sorted by `order_index`)
	- [ ] `PATCH /projects/{pid}/tasks/{tid}` (Update task details / status)
	- [ ] `DELETE /projects/{pid}/tasks/{tid}` (Soft delete task)

🧠 **Performance Deep-Dive:**
- *What is the N+1 problem when fetching projects and their tasks? How does SQLAlchemy resolve this?*
- *Why is a soft delete useful, and how does it affect query indexing strategies?*

---

## 🔄 Step 5: Manual Schema Matching
*Create matching TypeScript/Zod schemas from backend Pydantic definitions.*

- [ ] **Define response/request Pydantic schemas in `schemas.py`**
- [ ] **Write Zod schemas manually in `frontend/src/schemas/`**
	- [ ] Match `ProjectResponse` and `ProjectCreate` to TypeScript/Zod forms
	- [ ] Match `TaskResponse` and `TaskUpdate` to TypeScript/Zod forms
	- [ ] Match `TokenResponse` validation
- [ ] **Document serialization differences** (e.g., date-time strings, UUID validators)

🧠 **Interview Question:**
- *Explain why validating JSON on both the client (Zod) and server (Pydantic) is crucial for production reliability.*

---

## 🧪 Step 6: Testing & Verification
*Write and run verification tests using Pytest.*

- [ ] **Configure testing environment**
	- Create `backend/tests/conftest.py` with async DB session fixtures
- [ ] **Write Auth Integration test** (Register -> Login -> Verify token and cookie)
- [ ] **Write CRUD operations test** (Create project -> Update -> Soft delete -> Verify absence)
- [ ] **Verify Swagger UI** at `http://localhost:8000/docs`

🧠 **Concept Review:**
- *Why do we run database tests in separate test-scoped database transactions that rollback on teardown?*
