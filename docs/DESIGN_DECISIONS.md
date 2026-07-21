# TaskForge AI — Design Decisions & Implementation Rationale

## Table of Contents

1. [Why Document](#why-document)
2. [Project Foundations](#project-foundations)
3. [Backend Decisions](#backend-decisions)
4. [Frontend Decisions](#frontend-decisions)
5. [Cross-Cutting Decisions](#cross-cutting-decisions)

---

## Why Document

This file explains the **"why" behind every significant decision** in the TaskForge AI codebase. It is not a README (the project doesn't need installation instructions for itself) — it is an **interview-ready rationale guide**. Each section presents:

- The decision made
- The alternatives considered
- Why this option was chosen
- What tradeoffs were accepted

---

## Project Foundations

### 1. Why Monorepo (Co-Located Backend + Frontend)?

**Decision:** Single repository with `backend/` and `frontend/` as top-level directories.

**Alternatives:**
- **Git Submodules:** Each layer in its own repo, frontend references backend via submodule
- **Two Separate Repos:** Independent lifecycle, separate CI/CD
- **True Monorepo (Nx/Turborepo):** Heavy tooling with task orchestration, caching, shared libraries

**Why Co-Located Simple Monorepo:**

| Factor | Monorepo Advantage |
|--------|-------------------|
| Atomic changes | Auth contract change (backend) + Zod schema update (frontend) in one commit |
| Shared context | One PR review covers both sides of an API endpoint change |
| Simpler tooling | No Nx/Turborepo config overhead for a ~20-file project |
| Easier onboarding | New contributor clones one repo, reads one docs folder |

**Tradeoff:** If this grows beyond ~5 services, a true monorepo tool (Nx) or polyrepo strategy would be cleaner. For Phase 1–3 scale, the overhead isn't worth it.

### 2. Why Python for Backend?

**Decision:** FastAPI on Python rather than Node.js/Express, Go/Gin, or Rust/Axum.

**Rationale:**
- **Type safety at runtime:** Pydantic v2 validates every request body, query param, and response model — not just at compile time but at the network boundary
- **SQLAlchemy 2.0:** The most mature async ORM in any language. First-class support for both PostgreSQL (production) and SQLite (tests) via dialect switching
- **Developer velocity:** FastAPI auto-generates OpenAPI/Swagger docs from type annotations — zero extra config for API documentation
- **Rich ecosystem:** Argon2, JWT, Alembic all have battle-tested Python packages

**What we'd lose with Go/Rust:** Compile-time safety. But Python's Pydantic + SQLAlchemy 2.0 mapped columns catch most data errors at request time. For this project size, the tradeoff is acceptable.

### 3. Why React for Frontend?

**Decision:** React 19 with Vite rather than Vue, Svelte, or Solid.js.

**Rationale:**
- **Market demand:** Most full-stack interviews expect React competency
- **Ecosystem maturity:** TanStack Query v5 is the gold standard for server-state management in any framework; it's React-first
- **Vite:** The fastest dev server for any JS framework (HMR, no build on start)
- **TypeScript integration:** First-class `tsx` support with strict compiler options

**Tradeoff:** React's virtual DOM reconciliation overhead vs. Svelte/Solid's fine-grained reactivity. For a project management app where DOM complexity is moderate, React's overhead is negligible and the ecosystem benefit outweighs it.

---

## Backend Decisions

### 4. Why FastAPI Over Django/Flask?

**Decision:** FastAPI as the web framework.

**Alternatives:**
| Framework | Strength | Why Not Chosen |
|-----------|----------|----------------|
| **Django** | Batteries-included (admin, ORM, auth) | Heavyweight; ORM isn't async-first; admin panel adds surface area we don't need yet |
| **Flask + extensions** | Minimalist, flexible | Requires manual assembly of async support, validation, OpenAPI docs |
| **Starlette** | Raw ASGI speed | FastAPI is Starlette with added Pydantic validation and OpenAPI generation — strictly superset |

**Why FastAPI:** It gives us:
- Dependency injection system (used for `get_db_session`, `get_current_user`)
- Automatic request/response validation via Pydantic models
- Auto-generated Swagger UI at `/docs`
- Native async/await throughout
- Type hints that double as API documentation

### 5. Why Async SQLAlchemy Over Sync?

**Decision:** `sqlalchemy.ext.asyncio` with `AsyncSession` and `asyncpg`.

**Why:** FastAPI is an ASGI framework — using sync DB drivers would require running queries in thread pools (`run_in_executor`), adding latency and complexity. Async throughout means:
- A single event loop handles I/O for HTTP + DB simultaneously
- `asyncpg` is the fastest PostgreSQL driver available (native prepared statements, server-side cursors)
- Connection pooling is built into `async_sessionmaker`

**Tradeoff:** SQLite in tests must use `aiosqlite` (the async SQLite wrapper), which has slightly different behavior (no connection pooling, thread-safety quirks). This is handled via `check_same_thread=False` in the test engine config.

### 6. Why PostgreSQL Over Other Databases?

**Decision:** PostgreSQL 15 as production database; SQLite in-memory for tests.

**Alternatives considered:**
| DB | Why Not |
|----|---------|
| **MySQL/MariaDB** | Weaker JSON support, no native UUID type (stored as binary/blob), less mature async driver ecosystem |
| **MongoDB** | No relational constraints (FK cascades gone), soft-delete patterns awkward, not ideal for structured project/task data with joins |
| **SQLite (production)** | Fine for hobby projects but no concurrent write support, no row-level security, file locking issues at scale |

**Why PostgreSQL:**
- Native `UUID` type (no string→binary conversion overhead)
- Native `JSONB` if we add metadata fields later
- Best-in-class indexing (BRIN, GIN, partial indexes)
- `asyncpg` is the fastest async Postgres driver in any language
- Free, mature, well-documented

**Why SQLite for tests:** Zero infrastructure. No Docker needed to run pytest. The dialect difference is handled by SQLAlchemy's abstraction layer — our model code never changes between backends.

### 7. Why Alembic with Manual Migrations?

**Decision:** Write `upgrade()`/`downgrade()` SQL in migration files manually instead of using `alembic revision --autogenerate`.

**Why Autogenerate is Tempting But Dangerous:**
- It compares the live DB against model classes — but **models can lie** (a column added to a model that was already migrated on production but not yet tested locally)
- It misses subtle changes: index column order, check constraints, default value changes from function-based (`func.now()`) to literal (`'now()'::text`)
- It cannot reliably detect enum changes, collation changes, or server-side default modifications

**Why Manual Migrations:**
1. **Auditability:** Every `op.create_table()` and `op.create_index()` is visible in the diff
2. **Reviewability:** PR reviewers can verify index strategy, constraint names, cascade behavior
3. **Determinism:** The migration produces identical results on every host regardless of what's in local model files
4. **Interview talking point:** "I write migrations manually because production databases aren't a snapshot of your current code — they're a historical record of every change you've ever made"

### 8. Why UUID Primary Keys Over Auto-Incrementing Integers?

**Decision:** All tables use `UUID` as primary key type.

**Alternatives:**
| Approach | Problem |
|----------|---------|
| **SERIAL / BIGSERIAL (PostgreSQL)** | Sequential IDs leak enumeration information (`/projects/1`, `/projects/2`...) — attackers can scrape your entire dataset by incrementing |
| **Random UUID v4** | Slightly larger indexes (~16 bytes vs 8 for bigint), not pre-sorted (causes B-tree page fragmentation) |
| **UUID v7 (time-ordered)** | Would be ideal but requires a library; standard library `uuid.uuid4()` is sufficient for our scale |

**Why UUID v4:**
- Prevents ID enumeration attacks
- Works identically in SQLite and PostgreSQL (both have UUID support)
- At ~10K rows, the 8-byte overhead over bigint is negligible (<0.1% of table size)
- If this grows to millions of rows, we'd switch to UUIDv7 or ULIDs

### 9. Why Argon2id for Password Hashing?

**Decision:** `argon2-cffi` with default parameters (Argon2id variant).

**Alternatives:**
| Algorithm | Status | Issue |
|-----------|--------|-------|
| **MD5/SHA1** | Broken | Designed for speed — GPU can crack billions of hashes/sec |
| **BCrypt** | Good but aging | Maximum 72-byte password (we support up to 100), not memory-hard, vulnerable to GPU parallelism at scale |
| **SCrypt** | Good | Less widely adopted, harder to tune parameters correctly |
| **Argon2id** | ✅ Winner | Won the 2015 Password Hashing Competition; memory-hard (requires RAM, not just compute); resists both side-channel and GPU attacks |

**Why Argon2id specifically (not Argon2i or Argon2d):** The `id` variant blends both resistance profiles — `Argon2i` defends against side-channel timing attacks, `Argon2d` defends against GPU rainbow table attacks. The hybrid gives the best of both.

### 10. Why JWT for Access Tokens Over Server-Side Sessions?

**Decision:** Stateless JWT access tokens (5-minute expiry) rather than server-side session IDs stored in Redis/DB.

**Alternatives:**
| Approach | Tradeoff |
|----------|----------|
| **Server-side sessions (Redis)** | Requires external state; scaling means managing Redis cluster; but easier token revocation |
| **JWT** | Stateless (no external dependency); self-contained payload; but revocation requires a blocklist or short expiry |

**Why JWT with Short Expiry:**
- No Redis dependency reduces infrastructure complexity for Phase 1
- 5-minute expiry means a stolen access token has minimal window of usefulness
- The real session lifecycle is managed by the **refresh token in the httpOnly cookie** — that's where revocation happens
- `sub` field contains the user UUID; no DB lookup needed to identify the bearer (though we do look up the User row for full object access)

**The hybrid pattern:** JWT access tokens are short-lived and stateless. Refresh tokens are long-lived but DB-tracked with rotation. This gives us:
- Stateless scale on the access path (no Redis, no session table lookup per request)
- Full revocation control on the refresh path (DB query + rotation detection)

### 11. Why SHA256 Hash of Refresh Tokens in Database?

**Decision:** Store `SHA256(raw_refresh_token)` in the DB, never store the raw token.

**Why Not Store Raw Tokens:**
If the database is breached and refresh tokens are stored plaintext (or even bcrypt-hashed with a weak salt), an attacker could use them to hijack user sessions for 30 days. SHA256-hashed tokens cannot be reverse-engineered — the DB breach gives you hashes, not usable session credentials.

**Why Not BCrypt for Refresh Tokens:**
BCrypt is designed for passwords where verification speed should be slow (throttling brute force). Refresh token lookup happens once per rotation cycle — we need **fast verification**, not slow verification. SHA256 is instant to compute and impossible to reverse.

### 12. Why Soft Deletes Over Hard Deletes?

**Decision:** `deleted_at TIMESTAMPTZ` column instead of `DELETE FROM table WHERE id = ...`.

**Alternatives considered:**
| Approach | Issue |
|----------|-------|
| **Hard delete** | Data permanently lost; breaks audit trail; cascading FK deletes can orphan related data (comments, activity logs) |
| **Boolean `is_deleted` flag** | Wastes storage for a single boolean; cannot distinguish "never deleted" from "deleted at unknown time"; loses temporal information |
| **Timestamp `deleted_at`** | ✅ Preserves when deletion happened; easy to query "all soft-deleted rows in last 30 days"; NULL means "active" (no extra column scan for the common case) |

**Additional benefits:**
- Composite indexes include `deleted_at` so queries like `WHERE deleted_at IS NULL` are index-satisfied (PostgreSQL can use a partial B-tree index on nullable columns)
- Cascade soft-delete: when a project is deleted, we manually set `deleted_at` on all child tasks — preserving referential integrity without DB-level cascade fires
- Recovery path: if someone accidentally deletes, setting `deleted_at = NULL` restores the row

### 13. Why Composite Indexes Instead of Single-Column Indexes?

**Decision:** Three composite indexes designed to match exact query patterns.

| Index | Columns | Query Pattern Served |
|-------|---------|---------------------|
| `idx_proj_owner_status_deleted` | `(owner_id, status, deleted_at)` | `SELECT * FROM projects WHERE owner_id = ? AND status = 'active' AND deleted_at IS NULL LIMIT 20 OFFSET 0` |
| `idx_task_proj_order_deleted` | `(project_id, order_index, deleted_at)` | `SELECT * FROM tasks WHERE project_id = ? AND deleted_at IS NULL ORDER BY order_index ASC` |
| `idx_rt_user_expires` | `(user_id, expires_at)` | `SELECT * FROM refresh_tokens WHERE user_id = ? AND expires_at > now()` |

**Why not just index each column separately?** PostgreSQL's query planner can only use **one** B-tree index per table scan (without index merge scans which are rare and limited). A composite index with columns in the right order lets the DB satisfy the entire WHERE + ORDER BY from a single index traversal.

**Column ordering matters:** The most selective / equality-filtered column goes first (`owner_id`), then range-filtered (`status`), then the nullable filter (`deleted_at`). Reversing this order would result in full-table scans.

### 14. Why `order_index` Integer for Task Ordering?

**Decision:** Simple integer column (`INTEGER NOT NULL DEFAULT 0`) for task position.

**Alternatives:**
| Approach | Issue |
|----------|-------|
| **Array of task IDs on Project model** | Requires full array update on every reorder; not indexable; race-prone under concurrent edits |
| **Floating-point fractional indexing** | Elegant (insert between 2.0 and 3.0 as 2.5), but precision runs out after ~1000 reorders; requires periodic re-numbering anyway |
| **Linked-list (prev_id, next_id)** | O(n) traversal to list all tasks; awkward ordering queries; not suited for SQL which is set-based |

**Why Integer:**
- `ORDER BY order_index ASC` is trivial and index-covered
- Frontend can send full re-order batches on drag-and-drop end (PATCH each task's `order_index`)
- At Phase 1 scale (<100 tasks per project), integer collisions are easily resolved by auto-incrementing from `MAX(order_index) + 1`

### 15. Why Priority as SmallInteger 0–3?

**Decision:** Four-level priority encoded as a signed small integer with a `CHECK (priority >= 0 AND priority <= 3)` constraint.

**Why Not an Enum String:**
- Integers sort naturally (`ORDER BY priority DESC` works without casting)
- Smaller storage (1 byte vs variable-length VARCHAR)
- Less chance of typos in the API contract (`"hight"` instead of `"high"`)
- Frontend Zod schema mirrors the constraint: `z.number().int().min(0).max(3)`

**Levels:** 0 = Low, 1 = Medium, 2 = High, 3 = Critical. Expandable to 5 levels without migration if needed (just widen the check constraint).

### 16. Why Pydantic v2 Settings for Configuration?

**Decision:** `pydantic_settings.BaseSettings` with `.env` file loading, rather than `os.environ.get()` calls scattered through modules.

**Alternatives:**
| Approach | Issue |
|----------|-------|
| **Bare `os.environ.get("KEY", "default")`** | No type coercion (everything is string); no validation at startup; defaults scattered across files |
| **YAML/TOML config file** | File I/O required; harder to override per-environment; more moving parts |
| **Pydantic Settings** | ✅ Typed fields validated on import; `.env` auto-loaded; `validation_alias` for renaming; `model_config` for per-setting behavior |

**Key benefit:** If a required env var is missing or wrong type, the app fails fast at startup with a clear error message rather than crashing mid-request.

### 17. Why Dependency Injection for Auth?

**Decision:** FastAPI's `Depends(get_current_user)` injected into every protected route.

**Why Not Middleware?**
Middleware runs on **every** request — including `/health`, static files, and future public endpoints. A DI dependency only runs on routes that explicitly declare it, giving us:
- Selective auth (public vs private endpoints are explicit)
- Clean separation: the auth logic lives in `dependencies.py`, route handlers focus on business logic
- Easy to swap per-route (e.g., an admin-only dependency that checks a role column later)

### 18. Why Explicit `model_dump(exclude_unset=True)` for PATCH?

**Decision:** In update endpoints, only serialize fields that were actually sent in the request body.

**Why Not Full Replace:**
PATCH semantics mean "change what's given, leave the rest." Without `exclude_unset=True`, a client sending `{"title": "new"}` would also send `{"description": null, "status": null}` (default values), overwriting existing data with nulls.

This is subtle but critical: it means our API supports true partial updates rather than disguised PUT requests in disguise.

### 19. Why Test Against SQLite Instead of Docker Postgres?

**Decision:** Tests use `sqlite+aiosqlite:///:memory:` with tables created/teared down per session.

**Alternatives:**
| Approach | Tradeoff |
|----------|----------|
| **Real Postgres in Docker** | Most accurate; but every test run needs Docker running; slow startup (~5s container warmup); harder CI setup |
| **SQLite in-memory** | Zero infrastructure; instant; SQLAlchemy's abstraction handles dialect differences; `check_same_thread=False` works around SQLite's thread safety limits |

**Caveat:** Some PostgreSQL-specific features (e.g., JSONB operators, `RETURNING` clause variations) won't exercise the exact same code path. For Phase 1 CRUD though, the query patterns are simple enough that SQLite is a faithful stand-in. If we add complex queries later, we'd spin up a test Postgres container for integration tests.

---

## Frontend Decisions

### 20. Why Zustand Over Redux/Context?

**Decision:** Zustand for client-side state (auth token only). TanStack Query for server state.

**Alternatives:**
| Approach | Issue |
|----------|-------|
| **Redux Toolkit** | Heavy boilerplate (store, slices, reducers, selectors); overkill for a single auth token; ~10x bundle size of Zustand |
| **React Context + useState** | Causes unnecessary re-renders (every subscriber rerenders on any state change); no batching; poor performance at scale |
| **Jotai** | Great library but less ecosystem adoption; fewer learning resources |
| **Zustand** | ✅ Minimal API (~1KB), no providers needed, direct hook access, perfect for small client state |

**Why the split:** Server state (projects, tasks, lists) belongs in TanStack Query which handles caching, stale time, refetch, and background sync. Client state (auth token presence) is a simple flag that Zustand manages perfectly. Don't put server state in global stores — that's the #1 React anti-pattern.

### 21. Why TanStack Query v5 Over SWR/RTK-Query?

**Decision:** `@tanstack/react-query` for all server-state management.

**Alternatives:**
| Library | Issue |
|---------|-------|
| **SWR** | Vercel-owned; React-only (not framework-agnostic); smaller ecosystem than TanStack |
| **RTK-Query** | Tied to Redux; heavy dependency chain for a query client |
| **Urql / Apollo Client** | GraphQL-first; overkill for REST APIs; large bundle |
| **TanStack Query v5** | ✅ Framework-agnostic (React, Vue, Svelte); best-in-class caching/invalidation; supports mutations with optimistic updates; per-query retry control |

**Key configuration rationale:**
```ts
staleTime: 30_000        // Data stays fresh for 30s before background refetch
refetchOnWindowFocus: true // Re-sync when user returns to tab (catches backend changes)
retry: 1                // Retry once on failure (handles transient network blips)
```
- `staleTime: 30s` balances freshness vs. request volume. Too low = excessive polling. Too high = stale data. 30s is the sweet spot for a project management app where real-time isn't critical.
- `refetchOnWindowFocus` silently updates the view when you switch tabs (e.g., another browser tab just created a task). No user action needed.

### 22. Why Thin Fetch Wrapper Over Axios?

**Decision:** Hand-written fetch-based API client in `api/client.ts`.

**Alternatives:**
| Approach | Issue |
|----------|-------|
| **Axios** | ~30KB gzip; interceptor model conflicts with TanStack Query's own retry/rollback lifecycle; unnecessary abstraction for a ~50-line wrapper |
| **ofetch (UnJS)** | Tiny but less known; adds ecosystem lock-in to the Nuxt/Vinxi universe |
| **Raw fetch** | Works but needs ~10 lines of boilerplate per call (headers, JSON parsing, error handling) |
| **Thin wrapper** | ✅ Full control; zero dependencies; `ApiError` class provides structured status + detail; TanStack Query wraps our functions so retry logic lives in one place |

**Why the wrapper is thin on purpose:** We don't implement retry, timeout, or caching here because **TanStack Query owns those concerns**. The client's only job is: attach auth header, set `credentials: "include"`, throw structured errors. Single responsibility.

### 23. Why httpOnly Cookie for Refresh Token Transport?

**Decision:** The browser sends the refresh cookie automatically on every request (`credentials: "include"`); JS never touches it.

**Alternatives:**
| Approach | Security Issue |
|----------|----------------|
| **localStorage + manual attach** | Readable by any injected script (XSS) — attacker can steal and use immediately |
| **sessionStorage** | Same XSS vulnerability; lost on tab close (forces re-login) |
| **Memory variable (no cookie)** | Lost on page refresh; user must log in every time — terrible UX |
| **httpOnly cookie** | ✅ Immune to JS reading; browser handles attachment automatically; survives page refresh; `SameSite=Lax` prevents CSRF |

**The flow:** Backend sets `Set-Cookie: refresh_token=...; HttpOnly; SameSite=Lax` on login/register/refresh. The browser stores it and sends it with every request to the same origin. Our `/auth/refresh` endpoint reads it via FastAPI's `Cookie()` dependency. JavaScript never sees it.

### 24. Why Memory-Only Access Token (Not localStorage)?

**Decision:** Access token lives in Zustand store (RAM only). Lost on page refresh. Session restored from httpOnly cookie.

**Alternatives:**
| Approach | Issue |
|----------|-------|
| **localStorage** | XSS-exposed; any script can read and exfiltrate the token |
| **Memory only + re-login on refresh** | Terrible UX — users hate logging in every page load |
| **Memory only + cookie restore** | ✅ XSS-safe (token in RAM, invisible to injected scripts); survives refresh via /auth/refresh call that reads the httpOnly cookie |

**The `useSessionRestore()` hook:** Fires on mount, calls `/auth/refresh`. The browser includes the httpOnly cookie automatically. On success → store the new access token in Zustand. On 401 → stay logged out (no valid session exists). Silent, invisible to the user.

### 25. Why Zod v4 for Client-Side Validation?

**Decision:** Manually written Zod schemas mirror every backend Pydantic schema.

**Alternatives:**
| Approach | Issue |
|----------|-------|
| **No client validation** | Bad UX — users submit forms, wait for network round-trip, then get server error messages |
| **Auto-generate from OpenAPI** | Fragile — requires build-step tooling; breaks when API changes between deploys; hides the schema-matching exercise which is the learning point |
| **Manual Zod schemas** | ✅ Explicit contract mirroring catches drift early (if backend changes a field but frontend Zod doesn't, type errors surface immediately) |

**Why manual is intentional:** The Phase 1 checklist explicitly lists "manual schema matching" as a learning objective. Writing both sides by hand teaches you to think about the contract boundary — what types serialize across JSON, how enums map, how Optionals translate.

### 26. Why TailwindCSS v4 Over CSS-in-JS or Sass?

**Decision:** `@tailwindcss/vite` plugin with `@import "tailwindcss"` in CSS entry point (v4 syntax).

**Alternatives:**
| Approach | Issue |
|----------|-------|
| **Emotion/Styled-Components** | Runtime cost (styles computed on render); bundle bloat; server-side rendering complexity |
| **Sass/LESS** | Preprocessor step adds build time; doesn't solve the "utility class" problem; still need naming conventions |
| **Vanilla CSS Modules** | Scoped styles but no utility system; verbose for layout/styling patterns we repeat (flex, gap, padding) |
| **Tailwind v4** | ✅ Zero-configuration via Vite plugin; CSS-first config (no `tailwind.config.js` needed); JIT compilation means only used classes ship; ~10KB gzip total |

**Why v4 specifically:** Tailwind v4 eliminates the JavaScript config file (`tailwind.config.js`) by reading CSS directly. This is simpler, faster, and removes a common source of misconfiguration.

### 27. Why TypeScript Strict Mode?

**Decision:** Full strict config including `verbatimModuleSyntax`, `noUnusedLocals`, `noUnusedParameters`.

**Alternatives:**
| Setting | Tradeoff |
|---------|----------|
| **`"strict": false`** | Faster onboarding but defeats the purpose of TypeScript — implicit anys everywhere, silent bugs |
| **Default strict + custom overrides** | Good balance for most projects; we've added `erasableSyntaxOnly` for modern TS-only syntax that doesn't emit |
| **Our config (full strict + bundler mode)** | ✅ Catches: unused variables (code rot), parameter shadowing, implicit returns, untyped imports. The upfront friction pays off in fewer runtime surprises. |

### 28. Why Vite Over CRA/Next.js?

**Decision:** Vite as the build tool for a plain SPA.

**Alternatives:**
| Approach | Issue |
|----------|-------|
| **Create React App (Webpack)** | Dead project; deprecated; massive config locked behind `react-scripts`; ~60s dev server startup |
| **Next.js** | SSR/SSG framework — adds routing, API routes, server components. Overkill for a client-side SPA talking to a separate FastAPI backend |
| **Vite** | ✅ Near-instant HMR; esbuild-based pre-bundling; 2s dev startup; works with React, Preact, Lit — not just one framework |

**The `/api` proxy:** Vite's dev server proxies `/api/*` requests to `http://localhost:8000`. This means:
- Frontend code uses relative URLs (`/api/v1/projects`) everywhere
- No CORS issues in development (same-origin from the browser's perspective)
- No need for environment variables or config switches between dev/prod

### 29. Why React Query DevTools Included?

**Decision:** `<ReactQueryDevtools initialIsOpen={false} />` in the component tree.

**Why:** Debugging server state is notoriously difficult without visibility into cache state, query keys, mutation status, and error details. The devtools let you:
- See which queries are stale/active/loading
- Manually invalidate caches (simulate "pull to refresh")
- Inspect mutation results and retry counts
- Understand why a component re-rendered (which query changed?)

`initialIsOpen={false}` keeps the dev experience clean by default; press `Ctrl+Shift+Q` to open when needed.

---

## Cross-Cutting Decisions

### 30. Why CORS Allowlist Instead of Wildcard?

**Decision:** Explicit origin list in `config.py`: `CORS_ORIGINS = ["http://localhost:5173"]`.

**Why Not `allow_origins=["*"]`:**
Wildcard origins with `allow_credentials=True` is a **security contradiction** — the browser rejects it. If you allow all origins, you must drop credentials (cookies won't send). By explicitly listing `localhost:5173`, we:
- Allow the dev server origin for cookie transport
- Block unknown origins from accessing our API in production
- Make CORS policy explicit and auditable

### 31. Why `pool_pre_ping=True` on the DB Engine?

**Decision:** Enable connection health checks before each query.

**Why:** Database connections can die unexpectedly (network blip, server restart, idle timeout). Without pre-ping, a stale connection throws a cryptic error mid-request. With pre-ping, the pool verifies the connection is alive before handing it to SQLAlchemy — dead connections are silently replaced. The cost is one extra round-trip per query, which is negligible compared to the actual query time.

### 32. Why `expire_on_commit=False` on Sessions?

**Decision:** Don't expire ORM attributes after commit.

**Why:** The default (`True`) makes every attribute access re-query the DB after a commit — even if you just set and committed the value yourself. Setting it to `False` means:
- `project.title` returns the in-memory value immediately after commit (no extra SELECT)
- If another process modifies the row concurrently, you'd get stale data — but our app doesn't have high-concurrency multi-writer patterns yet
- Reduces unnecessary database round-trips

### 33. Why `async with test_engine.connect()` Instead of Direct Queries in Tests?

**Decision:** Test DB sessions bind to a connection that begins a transaction, which rolls back at teardown.

**Why:** This gives us **per-test isolation**. Each test runs inside its own transaction block that never commits. When the test fixture tears down, `await transaction.rollback()` undoes every INSERT/UPDATE/DELETE — the DB returns to a clean state for the next test. No "polluted database" bugs where Test B's data leaks into Test C.

### 34. Why `httpx.AsyncClient` with `ASGITransport` Over Mocking?

**Decision:** Use real ASGI transport (calls actual FastAPI route handlers) instead of mocking every function.

**Alternatives:**
| Approach | Issue |
|----------|-------|
| **unittest.mock / pytest-mock** | Fragile — mock the wrong thing and tests pass but production breaks; doesn't test request parsing, response serialization, or middleware |
| **Integration test against real server** | Requires starting uvicorn in a subprocess; slow; port conflicts; harder to control DB state |
| **httpx + ASGITransport** | ✅ Calls real route handlers with real Pydantic validation and real dependency injection; but the DB session is overridden to use our test fixture — best of both worlds |

---

## Decisions Deferred / Not Yet Made

These areas are intentionally left open for Phase 2+:

| Decision Area | Open Question |
|---------------|---------------|
| **Deployment** | Docker Compose vs Kubernetes? Single server or cloud-native? |
| **CI/CD** | GitHub Actions? Self-hosted runner? What should the pipeline test? |
| **Real-time** | WebSockets for live task updates? Server-Sent Events as lighter alternative? |
| **File uploads** | Task attachments → where to store (S3, local disk, database BLOB)? |
| **Multi-tenancy** | Shared projects between users? Row-level security or app-level filtering? |
| **AI features** | LLM integration for task suggestion/auto-prioritization? Local Ollama or cloud API? |
| **Search** | Full-text search across tasks/projects → PostgreSQL `tsvector` or Elasticsearch? |
| **Monitoring** | Structured logging? OpenTelemetry traces? Health check endpoints? |

Each of these will get its own "why" section when the time comes to decide.

---

*Last updated: 2026-07-22*
*Author: Ryan (with OpenClaw assistance)*
