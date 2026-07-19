import { z } from "zod";

// ── Token ────────────────────────────────────────────────────────────────────
// Maps to backend: TokenResponse (schemas.py)
// Note: token_type is always "bearer" — we validate it here to detect
//       unexpected backend changes early (contract drift protection).
export const TokenResponseSchema = z.object({
  access_token: z.string().min(1),
  token_type: z.literal("bearer"),
});

export type TokenResponse = z.infer<typeof TokenResponseSchema>;

// ── Register / Login request ─────────────────────────────────────────────────
// Maps to backend: UserRegister / UserLogin (schemas.py)
// password min_length mirrors the backend Pydantic min_length=8 constraint.
export const AuthCredentialsSchema = z.object({
  email: z.string().email("Please enter a valid email address"),
  password: z.string().min(8, "Password must be at least 8 characters"),
});

export type AuthCredentials = z.infer<typeof AuthCredentialsSchema>;
