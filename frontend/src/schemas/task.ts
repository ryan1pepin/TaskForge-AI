import { z } from "zod";

// ── Enums ────────────────────────────────────────────────────────────────────
// Must exactly match backend TaskStatus enum values.
// Python enum: todo | in_progress | done
export const TaskStatusSchema = z.enum(["todo", "in_progress", "done"]);
export type TaskStatus = z.infer<typeof TaskStatusSchema>;

// ── Task Response ─────────────────────────────────────────────────────────────
// Maps to backend: TaskResponse (schemas.py)
// priority: Python SmallInteger (0-3) → z.number().int().min(0).max(3)
// due_date: Python Optional[datetime] → nullable ISO-8601 string
export const TaskResponseSchema = z.object({
  id: z.string().uuid(),
  project_id: z.string().uuid(),
  title: z.string().min(1).max(255),
  description: z.string().max(1000).nullable().optional(),
  status: TaskStatusSchema,
  priority: z.number().int().min(0).max(3),
  order_index: z.number().int().min(0),
  due_date: z.string().datetime().nullable().optional(),
  created_at: z.string().datetime(),
  updated_at: z.string().datetime(),
});

export type TaskResponse = z.infer<typeof TaskResponseSchema>;

// ── Task Create ───────────────────────────────────────────────────────────────
// Maps to backend: TaskCreate (schemas.py)
export const TaskCreateSchema = z.object({
  title: z.string().min(1, "Title is required").max(255),
  description: z.string().max(1000).optional(),
  status: TaskStatusSchema.optional().default("todo"),
  priority: z.number().int().min(0).max(3).optional().default(0),
  order_index: z.number().int().min(0).optional().default(0),
  due_date: z.string().datetime().optional(),
});

export type TaskCreate = z.infer<typeof TaskCreateSchema>;

// ── Task Update ───────────────────────────────────────────────────────────────
// Maps to backend: TaskUpdate (schemas.py) — all fields optional (PATCH)
export const TaskUpdateSchema = z.object({
  title: z.string().min(1).max(255).optional(),
  description: z.string().max(1000).optional(),
  status: TaskStatusSchema.optional(),
  priority: z.number().int().min(0).max(3).optional(),
  order_index: z.number().int().min(0).optional(),
  due_date: z.string().datetime().nullable().optional(),
});

export type TaskUpdate = z.infer<typeof TaskUpdateSchema>;
