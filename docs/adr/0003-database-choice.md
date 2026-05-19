# ADR-0003: Neon (serverless Postgres) for prediction history

- **Status:** accepted
- **Date:** 2026-04-21
- **Deciders:** Alan Salazar

## Context and Problem Statement

Phase 6 stores confirmed predictions so authenticated users can inspect their
valuation history. Auth.js uses CredentialsProvider with JWT sessions, so the
database is not responsible for users, accounts, or sessions.

The implemented database scope is intentionally small: one Neon Postgres table,
`predictions`, accessed by the Next.js BFF through Drizzle. FastAPI remains
stateless and does not write user data.

## Decision Drivers

- Prediction history needs durable relational storage with simple indexing by
  `user_id` and `created_at`.
- The app already runs mutations through Next.js route handlers, so Drizzle can
  own persistence without coupling FastAPI to auth.
- We do not need a managed auth product or Auth.js database adapter in v1.
- Neon gives serverless Postgres, a good Vercel fit, and a low-friction free
  development setup.

## Considered Options

1. **Neon**: serverless Postgres with DB branching, native Vercel integration,
   and Drizzle support.
2. **Supabase**: Postgres plus Auth, Storage, and Realtime as a bundled BaaS.
3. **Convex**: TS-native reactive document database.

## Decision Outcome

Chosen option: **Neon**.

Configured schema:

```text
predictions
  id
  user_id
  input_jsonb
  input_source
  parse_metadata_jsonb
  predicted_price_usd_cents
  model_version
  api_request_id
  result_jsonb
  shap_jsonb
  idempotency_key
  created_at
```

Indexes:

```text
predictions_user_created_idx       (user_id, created_at desc)
predictions_user_idempotency_idx   unique (user_id, idempotency_key)
```

The Drizzle migration has been applied successfully against the configured
Neon database.

## Consequences

- Prediction history survives restarts and is filtered by authenticated user.
- Auth remains simple: JWT sessions, no auth tables, no adapter migrations.
- FastAPI stays focused on model inference and SHAP.
- Standard Postgres keeps the persistence layer portable.
- Serverless database access requires `DATABASE_URL` in `apps/web/.env`.

## Links

- [ADR-0009 - Frontend stack](./0009-frontend-stack.md)
- [ADR-0011 - Assisted appraisal frontend workflow](./0011-assisted-appraisal-frontend.md)
