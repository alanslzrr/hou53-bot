# `apps/web/` — Next.js frontend

Phase 5 currently implements the server-side NLP parser route. The full
interactive frontend remains Phase 6.

Stack baseline (see [ADR-0009](../../docs/adr/0009-frontend-stack.md)):
Next.js App Router · AI SDK structured output · direct OpenAI provider · zod. shadcn/ui, Tailwind, NextAuth,
Drizzle, and Neon are added with the Phase 6 UI.

## NLP parser

`POST /api/parse` accepts:

```json
{ "description": "A 3-bedroom house in Ames, 1,800 sqft, built in 1995." }
```

and returns either parsed fields for user confirmation:

```json
{
  "ok": true,
  "parsed_fields": { "BedroomAbvGr": 3, "GrLivArea": 1800, "YearBuilt": 1995 },
  "guessed_fields": [],
  "missing_fields": [],
  "needs_confirmation": true
}
```

or a structured error with `partial_fields` for manual entry fallback.

The route uses `ai` structured output (`generateText` + `Output.object`)
with `@ai-sdk/openai` and `OPENAI_API_KEY`. Guardrails: server-only
credentials, bounded input, timeout, deterministic settings, in-memory
per-user/IP rate limiting, structured JSON logs, and zod validation
generated from the Python/Pydantic house input contract.

## Local commands

```bash
pnpm --dir apps/web install
pnpm --dir apps/web dev
pnpm --dir apps/web typecheck
pnpm --dir apps/web test
pnpm --dir apps/web build
pnpm --dir apps/web generate:contracts
```

Set `OPENAI_API_KEY` locally or in the deployment environment.
The parser default is `gpt-5.4-mini`. Temperature is intentionally omitted
because OpenAI reasoning models do not support it.
