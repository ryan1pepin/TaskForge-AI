# Codebase Documentation Index

## Projects

### 1. TaskForge AI — Full-Stack Project Management App
**Location:** `H:\projects\TaskForge AI`
**Summary:** JWT-authenticated project/task manager with FastAPI + React/TypeScript frontend.
Phase 1 scaffold: auth, CRUD, refresh token rotation, soft deletes, Zod↔Pydantic schema matching.
See: [[memory/projects/TaskForge-AI.md]]

## Quick Reference

| Project | Backend | Frontend | Status |
|---------|---------|----------|--------|
| TaskForge AI | FastAPI + SQLAlchemy 2.0 (async) + PostgreSQL | React 19 + Vite + TypeScript + Tailwind v4 + Zustand + TanStack Query v5 | Phase 1 scaffold complete |

## Technology Stack Overview

### Backend (FastAPI/Python)
- **Framework:** FastAPI 0.110+ with async support
- **ORM:** SQLAlchemy 2.0 async (asyncpg for Postgres, aiosqlite for tests)
- **Migrations:** Alembic with manual migration scripts
- **Auth:** Argon2 password hashing + JWT (HS256) with refresh token rotation
- **Validation:** Pydantic v2 (EmailStr, Field constraints)
- **Testing:** pytest + pytest-asyncio with SQLite in-memory DB

### Frontend (React/TypeScript)
- **Runtime:** React 19 with Vite 8
- **State:** Zustand (auth store), TanStack Query v5 (server state)
- **Validation:** Zod v4 (client-side schema matching)
- **Styling:** TailwindCSS v4 (via Vite plugin, `@import "tailwindcss"`)
- **Build:** TypeScript ~6.0 with strict config, oxlint for linting
