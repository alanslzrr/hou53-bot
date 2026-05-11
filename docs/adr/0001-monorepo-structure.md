# ADR-0001: Monorepo structure with `apps/`, `ml/`, `data/`, `docs/`

- **Status:** proposed
- **Date:** 2026-04-21
- **Deciders:** Alan Salazar

## Context and Problem Statement

HOU53-bot ships three deliverables that must coexist: a training codebase
(offline, heavy deps like pandas/xgboost/shap), an inference service (online,
lean runtime), and a web frontend. How we lay them out on disk determines
build times, image sizes, CI granularity, and how cleanly responsibilities
stay separated.

## Decision Drivers

- The inference image must not carry training-only dependencies (pandas,
  matplotlib, shap, jupyter). They would inflate the image by hundreds of MB
  and enlarge the attack surface.
- `docker compose up` must launch the full system, per the challenge brief.
- The team is small (one developer) — we want structure, not bureaucracy.
- Notebooks exist and are valuable, but must not be the source of truth for
  pipelines that get deployed.
- The frontend and backend are written in different languages and need
  independent build/test commands.

## Considered Options

1. **Flat layout** — everything under the repo root (`src/`, `api/`, `web/`).
2. **`apps/` + `packages/` monorepo** — Node-style monorepo with Turborepo.
3. **`apps/` + `ml/` + `data/` + `docs/`** — hybrid: deployable services under
   `apps/`, offline ML code under a top-level `ml/` package, data and models
   as first-class siblings.

## Decision Outcome

Chosen option: **Option 3**, because ML training is not a "deployable app" —
it is a pipeline that produces an artifact — and collapsing it into `apps/ml`
would force contributors to reason about it as a service.

### Positive Consequences

- `apps/api` and `apps/web` each have a single, obvious Dockerfile.
- `ml/` is a standalone installable Python package (`hou53-ml`) that the API
  can import for the preprocessing schema without importing training code.
- `data/` and `models/` as siblings signal that they are assets, not source —
  reinforced by DVC tracking (see ADR-0004).
- `docs/` at root is discoverable; ADRs do not get buried inside a service.

### Negative Consequences / Trade-offs

- Two `pyproject.toml` files (root + `ml/`). Mitigated by treating the root
  one as the workspace aggregator and `ml/pyproject.toml` as the library
  definition.
- Slightly non-standard for people expecting a `src/` layout. Mitigated by
  documenting the layout prominently in the root README.

## Pros and Cons of the Options

### Option 1 — Flat layout

- Good, because zero setup.
- Bad, because training and serving end up in the same Python environment,
  which is exactly the coupling we want to avoid.
- Bad, because there is no natural place for the frontend.

### Option 2 — `apps/` + `packages/` (Turborepo)

- Good, because Turborepo gives excellent caching and task orchestration.
- Bad, because Turborepo is designed around Node — Python packages live
  outside its task graph and gain little.
- Bad, because it imposes ceremony disproportionate to a one-person project.

### Option 3 — `apps/` + `ml/` + `data/` + `docs/`

- Good, because it mirrors the mental model: deployables under `apps/`,
  experimentation under `ml/`, assets at the root.
- Good, because each subtree has its own lint/test/build story.
- Bad, because we do not get Turborepo-style task caching out of the box.
  Acceptable — CI cost is not currently a bottleneck.

## Links

- [ADR-0004 — DVC](./0004-data-versioning-dvc.md)
- [ADR-0008 — FastAPI](./0008-api-framework-fastapi.md)
- [ADR-0009 — Frontend stack](./0009-frontend-stack.md)
