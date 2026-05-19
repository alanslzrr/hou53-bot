# ADR-0009: Next.js 15 App Router + shadcn/ui + Tailwind v4 + Auth.js

- **Status:** accepted
- **Date:** 2026-04-21
- **Deciders:** Alan Salazar

## Context and Problem Statement

The frontend must let a user describe a house (as structured input or free
text), see the predicted price, and inspect a human-readable explanation.
It must be responsive, authenticate users, and persist their prediction
history.

## Decision Drivers

- React-family is the challenge brief's suggestion — we stay in the family
  to keep the review frictionless.
- We want type-safety from DB schema → API → UI. That favors TS on the
  frontend and a toolchain that plays nicely with OpenAPI.
- shadcn/ui gives us accessible, copy-in primitives without committing to a
  component-library vendor.
- Auth.js supports a server-side CredentialsProvider/JWT flow without a DB
  adapter. Prediction history is a separate Neon/Drizzle concern.

## Considered Options

1. **Create React App / Vite + React + MUI**.
2. **Next.js App Router + shadcn/ui + Tailwind v4 + NextAuth**.
3. **Remix**.
4. **SvelteKit**.

## Decision Outcome

Chosen option: **Next.js 15 App Router + shadcn/ui + Tailwind v4 +
Auth.js**, because it is the lowest-friction path to a production-quality
frontend with typed data fetching, server-side auth, and a large ecosystem
of examples we can learn from.

### Positive Consequences

- Server Components let us do the FastAPI call on the server and hydrate
  the UI with a typed response — no CORS dance on the happy path.
- App Router + route handlers lets the NLP-parsing endpoint live in the
  Next.js app (calls the LLM, returns structured JSON), keeping the Python
  API focused on inference.
- shadcn/ui components are owned code (we copy them in) — no runtime
  dependency on a component vendor; we can theme them freely with Tailwind.
- Tailwind v4's zero-config engine removes the `tailwind.config.ts` tax.

### Negative Consequences / Trade-offs

- App Router has more conceptual surface (RSC, Server Actions, caching
  model) than a pure SPA. Mitigated by restricting ourselves to: RSC for
  reads, Route Handlers for mutations that call the Python API, and
  Client Components only where interactivity demands it.
- Tailwind v4 is newer — smaller Stack Overflow corpus, APIs have been
  moving. Mitigated by pinning the version in `package.json` and
  documenting any upgrade in an ADR.

## Implemented layout

```
apps/web/
├── src/
│   ├── app/                    # App Router routes
│   │   ├── api/                # parse, predict, Auth.js route handlers
│   │   ├── history/            # previous predictions
│   │   └── login/              # demo credentials login
│   ├── components/
│   │   ├── ui/                 # shadcn primitives (generated)
│   │   └── ai-elements/        # selected AI Elements
│   ├── features/estimate/      # assisted appraisal workspace
│   ├── lib/
│   │   ├── housing/            # generated housing contract + zod helpers
│   │   └── nlp/                # parser prompt/provider logic
│   └── server/
│       ├── db/                 # Drizzle schema/client
│       ├── predict/            # FastAPI BFF client
│       └── predictions/        # prediction repository
├── drizzle/                    # Neon migrations
└── package.json
```

## Accessibility baseline

- WCAG 2.1 AA minimum. shadcn/ui is built on Radix — accessible by default.
- All forms keyboard-navigable, all interactive elements reachable.

## Links

- [Next.js App Router](https://nextjs.org/docs/app)
- [shadcn/ui](https://ui.shadcn.com/)
- [Tailwind v4](https://tailwindcss.com/docs)
- [NextAuth.js](https://authjs.dev/)
- [ADR-0003 — Database (Neon)](./0003-database-choice.md)
