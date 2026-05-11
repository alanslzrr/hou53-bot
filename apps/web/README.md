# `apps/web/` — Next.js frontend

Placeholder; implemented in **Phase 6**.

Planned stack (see [ADR-0009](../../docs/adr/0009-frontend-stack.md)):
Next.js 15 App Router · shadcn/ui · Tailwind v4 · NextAuth · Drizzle ORM
against Neon (ADR-0003).

The NLP route handler (ADR-0010) lives here, not in the Python API, so
that the LLM provider key never leaves the server-side of the web app.
