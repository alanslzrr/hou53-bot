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
| `POST /api/estimate/readiness` | Authenticated input-signal assessment + helper questions |
| `POST /api/predict` | Authenticated BFF route to FastAPI + Neon |

## NLP parser

`POST /api/parse` accepts:

```json
{ "description": "A 3-bedroom house in Ames, 1,800 sqft, built in 1995." }
```

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

## Runtime configuration

Auth.js uses one environment-backed CredentialsProvider user and JWT sessions;
it has no database adapter or auth tables. Neon stores confirmed predictions
only, through the Drizzle `predictions` table. Required runtime variables are
listed in [.env.example](./.env.example).

`POST /api/predict` calls `HOU53_API_BASE_URL` internally. The browser never
calls FastAPI directly. `HOU53_API_AUTH_MODE=auto` keeps local/docker HTTP
targets unauthenticated and adds a Google ID token only for Cloud Run
`*.run.app` targets. Use `google` to force ID-token auth for a custom Cloud Run
domain, or `none` to disable it explicitly.

## Readiness assistant

`POST /api/estimate/readiness` computes a deterministic `readiness_score`
from structured fields and returns up to five helper questions for sparse
inputs. The LLM may improve question wording, but it never predicts price or
changes the score. Users can still run `Predict with sparse input`; FastAPI
continues to accept partial payloads.

Set `HOU53_READINESS_LLM_ENABLED=false` to force rule-based helper questions.
