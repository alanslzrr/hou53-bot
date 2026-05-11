# SOLUTION.md

> This file is the single entry point for the reviewer. It describes what
> this submission is, how to run it, the decisions behind it, and what is
> not yet implemented.

## What this is

HOU53-bot is an end-to-end house-price prediction system for the Ames
Housing dataset. It consists of:

- A reproducible ML pipeline (preprocessing + XGBoost regressor) trained
  with scikit-learn and tracked with MLflow.
- A FastAPI inference service that exposes the trained pipeline behind a
  typed HTTP API and returns per-prediction SHAP explanations.
- A Next.js web application that lets a user describe a property in
  structured form **or** in natural language, see the predicted price, and
  inspect the factors that drove the prediction.
- A `docker-compose` that starts the whole system with one command.

## Repository layout

```
.
├── apps/
│   ├── api/        FastAPI inference service (Docker-deployed)
│   └── web/        Next.js frontend (Docker-deployed)
├── ml/             Offline ML code (training, features, evaluation)
│   ├── notebooks/  EDA and experiments (Jupytext-paired)
│   ├── src/hou53_ml/
│   ├── configs/
│   └── tests/
├── data/           DVC-tracked dataset (raw, interim, processed, external)
├── models/         DVC-tracked model artifacts
├── docs/
│   ├── adr/        Architecture Decision Records (MADR)
│   ├── eda/        Exported EDA report
│   ├── architecture.md
│   └── model-card.md
├── docker-compose.yml
└── SOLUTION.md     (this file)
```

## How to run it

> _To be completed in Phase 7. Target command is `docker compose up`._

```bash
# Placeholder — will be finalized once the API image is stable.
docker compose up --build
```

- Web: http://localhost:3000
- API: http://localhost:8000 (Swagger at `/docs`)
- MLflow UI (optional): http://localhost:5000

## Local development

```bash
# Python (ml + api)
uv sync
uv run pytest

# Web
cd apps/web
pnpm install
pnpm dev
```

## Technical decisions

Every non-trivial decision is captured as an ADR under
[`docs/adr/`](./docs/adr/README.md). The highlights:

| Area | Decision | ADR |
|---|---|---|
| Repo layout | `apps/` + `ml/` + `data/` + `docs/` | [0001](./docs/adr/0001-monorepo-structure.md) |
| Git | Trunk-based + Conventional Commits | [0002](./docs/adr/0002-git-workflow.md) |
| Database | Neon (serverless Postgres) | [0003](./docs/adr/0003-database-choice.md) |
| Data & model versioning | DVC | [0004](./docs/adr/0004-data-versioning-dvc.md) |
| Experiment tracking | MLflow, local file backend | [0005](./docs/adr/0005-experiment-tracking-mlflow.md) |
| Regressor | XGBoost (Ridge baseline) | [0006](./docs/adr/0006-model-selection-xgboost.md) |
| Metric | RMSE on `log1p(SalePrice)` | [0007](./docs/adr/0007-evaluation-metric-rmse-log.md) |
| API | FastAPI + Pydantic v2 | [0008](./docs/adr/0008-api-framework-fastapi.md) |
| Frontend | Next.js 15 + shadcn/ui + Tailwind v4 + NextAuth | [0009](./docs/adr/0009-frontend-stack.md) |
| NLP parsing | LLM with structured output | [0010](./docs/adr/0010-nlp-parsing-strategy.md) |

## What is not yet implemented

> _Tracked openly; will be updated as phases close._

- [ ] EDA report and notebook (Phase 1)
- [ ] Training pipeline and baseline vs. XGBoost comparison (Phase 2)
- [ ] Serialized model + model card (Phase 3)
- [ ] FastAPI service (Phase 4)
- [ ] NLP parser (Phase 5)
- [ ] Next.js frontend (Phase 6)
- [ ] docker-compose end-to-end (Phase 7)
- [ ] CI/CD, observability (Phase 8)

## Other considerations

- **Reproducibility.** Every commit on `main` pins: Python version
  (`.python-version`), Python dependencies (`uv.lock`), Node dependencies
  (committed lockfile), dataset hash (`data/raw/*.dvc`), model hash
  (`models/*.dvc`).
- **Explainability.** The API returns top-contributing features (via SHAP
  `TreeExplainer`) with every prediction. The frontend renders them as a
  waterfall chart with a natural-language summary.
- **Input resilience.** The API validates inputs against a Pydantic schema
  generated from the training `ColumnTransformer` — any field missing or
  out of domain is rejected with a specific error.
- **Privacy.** User inputs are persisted only for authenticated users and
  only to power their own history. No PII beyond the auth email.
