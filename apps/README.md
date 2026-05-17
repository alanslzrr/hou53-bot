# `apps/` — deployable services

Each subdirectory is a self-contained service with its own Dockerfile and
its own build/test story. This is the boundary between the monorepo and
the container runtime: `docker compose up` composes exactly the services
defined under here.

| Service | Language | Purpose | Phase |
|---|---|---|---|
| `api/` | Python (FastAPI) | Inference + SHAP explanations | 4 |
| `web/` | TypeScript (Next.js) | NLP route handler now; user-facing UI in Phase 6 | 5/6 |

The offline training code lives outside `apps/` under `ml/` precisely
because it is not a deployable service — see
[ADR-0001](../docs/adr/0001-monorepo-structure.md).
