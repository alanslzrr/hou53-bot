# ADR-0011: Assisted appraisal frontend workflow

- **Status:** accepted
- **Date:** 2026-05-17
- **Deciders:** Alan Salazar

## Context and Problem Statement

Phase 6 turns the existing ML/API/NLP backend into a usable product. The
critical choice is whether the web app should be a chat product or a structured
valuation workspace.

## Decision Outcome

Build HOU53 as an assisted appraisal workflow:

```text
natural description -> structured parse -> human review -> BFF predict -> SHAP result -> saved history
```

The frontend uses the existing Next.js app with shadcn/ui initialized by the
required preset `b4W5D7iSrC`. AI Elements is used only for the prompt input,
suggestions, workflow status, and loading shimmer. The core product state is not
`useChat`; it is a reducer-driven estimate workflow.

Authentication is mandatory for the web app. Auth.js uses CredentialsProvider
with JWT sessions and one demo user configured by environment variables. Auth
does not use a database adapter. Neon/Drizzle is used only for prediction
history.

The browser never calls FastAPI directly. Next.js owns the `/api/predict` BFF:
it validates payloads, reads the Auth.js session, calls FastAPI internally,
stores confirmed predictions, and returns a normalized response.

## Consequences

- The user always confirms parsed fields before prediction.
- SHAP from FastAPI remains the only price explanation.
- No chat persistence is needed; only confirmed predictions are stored.
- FastAPI stays stateless with respect to users and auth.
- Local demo auth is simple enough for the challenge while still enforcing the
  real logged-in flow.

## Rejected Options

- Full Vercel Chatbot Template as the app base.
- Chat SDK.
- `useChat` as the primary state model.
- `useObject` for the parser flow.
- LLM-generated price explanations.

## Links

- [ADR-0003 — Database choice](./0003-database-choice.md)
- [ADR-0009 — Frontend stack](./0009-frontend-stack.md)
- [ADR-0010 — NLP parsing strategy](./0010-nlp-parsing-strategy.md)
