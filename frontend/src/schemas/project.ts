import { z } from "zod";

// ── Enums ────────────────────────────────────────────────────────────────────
// Must exactly match backend ProjectStatus enum values (case-sensitive).
// Python enum: draft | active | archived
export const ProjectStatusSchema = z.enum(["draft", "active", "archived"]);
export type ProjectStatus = z.infer<typeof ProjectStatusSchema>;

// ── Project Response ──────────────────────────────────────────────────────────
// Maps to backend: ProjectResponse (schemas.py)
// Key type mappings:
//   Python UUID  → z.string().uuid()   (FastAPI serialises UUIDs to strings)
//   Python datetime → z.string().datetime() (FastAPI serialises to ISO-8601 strings)
export const ProjectResponseSchema = z.object({
  id: z.string().uuid(),
  owner_id: z.string().uuid(),
  title: z.string().min(1).max(255),
  description: z.string().max(1000).nullable().optional(),
  status: ProjectStatusSchema,
  created_at: z.string().datetime(),
  updated_at: z.string().datetime(),
});

export type ProjectResponse = z.infer<typeof ProjectResponseSchema>;

// ── Project Create ────────────────────────────────────────────────────────────
// Maps to backend: ProjectCreate (schemas.py)
export const ProjectCreateSchema = z.object({
  title: z.string().min(1, "Title is required").max(255),
  description: z.string().max(1000).optional(),
  status: ProjectStatusSchema.optional().default("draft"),
});

export type ProjectCreate = z.infer<typeof ProjectCreateSchema>;

// ── Project Update ────────────────────────────────────────────────────────────
// Maps to backend: ProjectUpdate (schemas.py) — all fields optional (PATCH)
export const ProjectUpdateSchema = z.object({
  title: z.string().min(1).max(255).optional(),
  description: z.string().max(1000).optional(),
  status: ProjectStatusSchema.optional(),
});

export type ProjectUpdate = z.infer<typeof ProjectUpdateSchema>;
