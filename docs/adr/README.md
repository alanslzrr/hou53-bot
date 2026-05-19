# Architecture Decision Records (ADR)

This directory contains the architecture decision records for the HOU53-bot
project. Each ADR captures **one** architecturally significant decision, the
context that drove it, the alternatives that were considered, and the
consequences of choosing it.

Format: [MADR 4.0](https://adr.github.io/madr/).

## Lifecycle

An ADR moves through these statuses:

- `proposed` — opened in a PR, under discussion.
- `accepted` — merged; the decision is active.
- `deprecated` — still historically true but no longer the current approach.
- `superseded by ADR-XXXX` — explicitly replaced. Never delete a superseded
  ADR; link it forward.

## How to add one

1. Copy [`0000-template.md`](./0000-template.md).
2. Rename it `NNNN-kebab-case-title.md` using the next unused number.
3. Fill in every section. "N/A" is acceptable; empty is not.
4. Add an entry to the index below.
5. Open a PR. Prefix the title with `docs(adr):` per our commit convention.

## Index

| # | Title | Status |
|---|---|---|
| [0001](./0001-monorepo-structure.md) | Monorepo structure with `apps/`, `ml/`, `data/`, `docs/` | proposed |
| [0002](./0002-git-workflow.md) | Trunk-based development with Conventional Commits | proposed |
| [0003](./0003-database-choice.md) | Neon (serverless Postgres) for prediction history | accepted |
| [0004](./0004-small-artifacts-in-git.md) | Keep small challenge data and model artifacts in Git | proposed |
| [0005](./0005-experiment-tracking-mlflow.md) | MLflow (local tracking) for experiment metadata | proposed |
| [0006](./0006-model-selection-xgboost.md) | XGBoost as the production regressor | proposed |
| [0007](./0007-evaluation-metric-rmse-log.md) | RMSE on `log1p(SalePrice)` as the primary metric | proposed |
| [0008](./0008-api-framework-fastapi.md) | FastAPI + Pydantic v2 for the inference service | proposed |
| [0009](./0009-frontend-stack.md) | Next.js 15 App Router + shadcn/ui + Tailwind v4 + Auth.js | accepted |
| [0010](./0010-nlp-parsing-strategy.md) | LLM with structured output for natural-language input | proposed |
| [0011](./0011-assisted-appraisal-frontend.md) | Assisted appraisal frontend workflow | accepted |
| [0012](./0012-deployment-on-google-cloud-run.md) | Deployment on Google Cloud Run | accepted |
