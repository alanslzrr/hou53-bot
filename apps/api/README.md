# `apps/api/` — FastAPI inference service

Serves the trained pipeline (`models/hou53-pipeline.joblib`) over HTTP.
Loads the model once at startup, validates inputs against a Pydantic
schema generated from `hou53_ml.io.Schema`, runs prediction + SHAP
attribution per request, and returns a structured explanation.

See [ADR-0008](../../docs/adr/0008-api-framework-fastapi.md) for the
design rationale.

## Layout (Clean Architecture, applied minimally)

```
apps/api/
├── src/app/
│   ├── api/
│   │   ├── routers/        HTTP routers (health, predict, model_info)
│   │   ├── dtos/           Pydantic request / response models
│   │   └── dependencies.py FastAPI dependency providers
│   ├── domain/             Pure dataclasses + protocols (no FastAPI)
│   ├── services/           Orchestration (predictor + explainer)
│   ├── infra/              Side-effects (model loader, settings, logging)
│   ├── config.py           Typed settings (env vars)
│   └── main.py             ASGI app factory + lifespan
├── tests/                  pytest + httpx TestClient
├── Dockerfile              Multi-stage uv build
└── .env.example
```

Layering rule: `api → services → domain` and `services → infra`.
`domain` does not import FastAPI or scikit-learn. `infra` is hidden
behind `Protocol`s so tests can swap in fakes without spinning up the
real model.

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/healthz` | Liveness — process up |
| `GET` | `/readyz` | Readiness — model loaded |
| `GET` | `/v1/model/info` | Artifact metadata (version, hash, metrics) |
| `POST` | `/v1/predict` | Single prediction with SHAP top-K |

OpenAPI is auto-generated at `/openapi.json` and Swagger UI at `/docs`.

## Run locally

```bash
# From repo root
uv sync --all-groups

# Make sure the artifact exists (train if missing)
uv run python -m hou53_ml.training.train

# Start the API
uv run --package hou53-api uvicorn app.main:app --reload --port 8000

# Sample request
curl -X POST http://localhost:8000/v1/predict \
  -H "Content-Type: application/json" \
  -d '{"OverallQual": 7, "GrLivArea": 1800, "GarageCars": 2}'
```

## Configuration

All settings come from env vars with the prefix `HOU53_API_`. See
`.env.example` for the full list. None are required; defaults work
for local development against the artifact under `models/`.
