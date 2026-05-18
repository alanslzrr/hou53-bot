# `apps/web/` — Next.js frontend

Phase 6 implements the assisted appraisal workspace: login, natural-language
parse, structured field review, BFF prediction, SHAP result display, and saved
prediction history.

Stack baseline (see [ADR-0009](../../docs/adr/0009-frontend-stack.md) and
[ADR-0011](../../docs/adr/0011-assisted-appraisal-frontend.md)): Next.js App
Router · shadcn/ui preset `b4W5D7iSrC` · Tailwind v4 · AI Elements · Auth.js
CredentialsProvider with JWT · Drizzle · Neon · AI SDK structured output ·
direct OpenAI provider · zod.

## Routes

| Route | Purpose |
|---|---|
| `/` | Login-required estimate workspace |
| `/login` | CredentialsProvider demo login |
| `/history` | Saved predictions for the signed-in user |
| `/history/[id]` | Prediction detail |
| `POST /api/parse` | Authenticated NLP parser route |
| `POST /api/predict` | Authenticated BFF route to FastAPI + Neon |

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
pnpm --dir apps/web db:migrate
```

Set `OPENAI_API_KEY` locally or in the deployment environment.
The parser default is `gpt-5.4-mini`. Temperature is intentionally omitted
because OpenAI reasoning models do not support it.
The default timeout is 15 seconds; local smoke tests with `gpt-5.4-mini`
completed in roughly 4-6 seconds.

## Auth and persistence

Auth.js does not use a database adapter. Configure one demo user:

```bash
node -e "const bcrypt=require('bcryptjs'); bcrypt.hash('change-me', 12).then(console.log)"
```

Then set `AUTH_SECRET`, `HOU53_AUTH_EMAIL`, and
`HOU53_AUTH_PASSWORD_HASH`. Prediction history uses `DATABASE_URL` and the
Drizzle migration in `drizzle/0000_predictions.sql`.

`POST /api/predict` calls `HOU53_API_BASE_URL` internally. The browser never
calls FastAPI directly.
