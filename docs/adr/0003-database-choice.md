# ADR-0003: Neon (serverless Postgres) for application data

- **Status:** proposed
- **Date:** 2026-04-21
- **Deciders:** Alan Salazar

## Context and Problem Statement

The application stores users, prediction history, feedback, and model-version
metadata. The frontend is Next.js + NextAuth; the backend is Python + FastAPI.
We need a database that both stacks can reach without glue code and that does
not force us to adopt an auth or ORM layer we have already replaced.

## Decision Drivers

- The entities are inherently relational (users ↔ predictions ↔ model versions
  ↔ feedback). SQL models this cleanly; documents do not.
- We already chose NextAuth (ADR-0009) — any database with a proprietary auth
  layer is money spent on a feature we will not use.
- FastAPI must write to the DB directly from Python. A mature driver
  (`asyncpg`) is non-negotiable.
- The challenge is evaluated on how it resembles production. Per-PR database
  branching is a meaningful step up in DX.
- We may later add a vector column for embedding the natural-language input
  (ADR-0010) — `pgvector` should be one SQL statement away.

## Considered Options

1. **Neon** — serverless Postgres with DB branching, pgvector, native Vercel
   integration, NextAuth Postgres adapter.
2. **Supabase** — Postgres + Auth + Storage + Realtime as a bundled BaaS.
3. **Convex** — TS-native reactive document database.

## Decision Outcome

Chosen option: **Neon**, because it aligns with every decision driver without
forcing us to adopt or pay for features we have already solved elsewhere.

### Positive Consequences

- NextAuth's `@auth/pg-adapter` works out of the box — zero glue code for
  session persistence.
- FastAPI talks to the DB via `asyncpg` / SQLAlchemy 2.0 — the most mature,
  best-documented Python ↔ Postgres combination.
- Per-PR database branching enables meaningful preview environments.
- `pgvector` available as `CREATE EXTENSION` for the NLP feature.
- Standard Postgres — zero vendor lock-in; a `pg_dump` gets us off Neon in
  an afternoon if we ever need to.

### Negative Consequences / Trade-offs

- Cold starts on free tier (~1–3 s). Mitigated by the fact that the first
  query on a user session is not latency-critical; hot path is the model
  inference.
- Connection pooling for serverless requires the pooled endpoint, not the
  direct one. Documented in the API's README and enforced via env var
  validation.

## Pros and Cons of the Options

### Neon

- Good, because it is plain Postgres — every Python and TS library "just
  works".
- Good, because of DB branching per PR.
- Good, because of native Vercel integration.
- Bad, because of cold starts on the free tier.

### Supabase

- Good, because it is also Postgres underneath.
- Good, because of generous free tier.
- Bad, because its Auth product duplicates NextAuth — we would be paying
  (in complexity, not dollars) for unused features.
- Bad, because Supabase-flavored tooling (Edge Functions, Supabase CLI)
  accretes vendor lock-in if used; ignoring it wastes the product.

### Convex

- Good, because the TS DX is excellent for reactive UIs.
- Bad, because there is no first-class Python driver — FastAPI would have to
  talk to Convex over HTTP, which defeats the purpose.
- Bad, because it pushes domain logic into Convex functions (TS), splitting
  the business logic across two languages for no gain.
- Bad, because the data model is document-oriented; our schema is relational.

## Links

- [Neon docs](https://neon.com/docs/introduction)
- [NextAuth.js Postgres adapter](https://authjs.dev/reference/adapter/pg)
- [ADR-0009 — Frontend stack](./0009-frontend-stack.md)
- [ADR-0010 — NLP parsing strategy](./0010-nlp-parsing-strategy.md)
