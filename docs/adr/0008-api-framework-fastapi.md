# ADR-0008: FastAPI + Pydantic v2 for the inference service

- **Status:** proposed
- **Date:** 2026-04-21
- **Deciders:** Alan Salazar

## Context and Problem Statement

The inference service must accept HTTP requests carrying (possibly partial)
house features, validate them, run the serialized pipeline, compute SHAP
attributions, and return a structured response. It must be containerizable,
document itself, and gracefully reject malformed input.

## Decision Drivers

- Challenge brief explicitly suggests FastAPI + Pydantic; choosing otherwise
  requires strong justification.
- Type-safe request/response schemas are the cheapest way to keep frontend
  and backend in sync — we want the frontend's zod schema to be generated
  from the backend's OpenAPI, not hand-written.
- The service must run in Docker with a small image.
- 79 possible input fields, most of them optional in the user-facing form.
  We need a validation layer that handles this without 79 manual checks.

## Considered Options

1. **Flask + marshmallow**.
2. **Django REST Framework**.
3. **FastAPI + Pydantic v2**.
4. **BentoML**.
5. **LitServe / Ray Serve**.

## Decision Outcome

Chosen option: **FastAPI + Pydantic v2**, because it is the stack suggested
by the brief and it gives us input validation, OpenAPI docs, and async I/O
for the price of declaring Pydantic models — no extra libraries.

### Positive Consequences

- Free OpenAPI 3.1 schema at `/openapi.json` → frontend types generated via
  `openapi-typescript` / `openapi-zod-client`.
- Pydantic v2 is fast (Rust core) — not a bottleneck even under load.
- Async handlers give us room to add timeouts/retries when we later call the
  LLM for NLP parsing.
- ASGI lifespan context makes "load model once at startup" a one-liner.

### Negative Consequences / Trade-offs

- FastAPI is less opinionated about project structure than DRF. Mitigated
  by our own layering (see "Layering" below).

## Layering (Clean Architecture, applied minimally)

The API is split into four layers, each with one reason to change:

```
apps/api/src/app/
├── api/            # HTTP adapters (routers, request/response DTOs)
├── domain/         # pure business logic (no FastAPI, no sklearn imports)
├── services/       # orchestration (load model, call domain, build response)
├── infra/          # I/O (model loader, DB client, logging, metrics)
└── main.py         # FastAPI app factory + lifespan
```

Rules:

- `api/` depends on `services/`. `services/` depends on `domain/` and
  `infra/`. `domain/` depends on nothing in the app.
- Routers do not touch the model or the DB directly — they call a service.
- Services do not import FastAPI.
- Infra hides external systems (filesystem, network, DB) behind protocols
  (PEP 544) so that domain and services can be tested with in-memory fakes.

This is the **S** and **D** of SOLID applied to a small codebase — single
responsibility per module, and inversion of the model-loading dependency so
tests do not need a real `joblib` file on disk.

## Endpoints (initial surface)

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/v1/predict` | Single prediction with SHAP explanation |
| `POST` | `/v1/predict/batch` | Batch predictions |
| `GET` | `/v1/model/info` | Version, training date, metrics |
| `GET` | `/healthz` | Liveness probe |
| `GET` | `/readyz` | Readiness probe (model loaded?) |

All `/v1/*` routes are versioned so that breaking changes do not break the
frontend mid-flight.

## Links

- [FastAPI docs](https://fastapi.tiangolo.com/)
- [Pydantic v2 docs](https://docs.pydantic.dev/latest/)
- [ADR-0009 — Frontend stack](./0009-frontend-stack.md)
