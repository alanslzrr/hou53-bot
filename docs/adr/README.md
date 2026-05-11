# Architecture Decision Records (ADR)

This directory contains the architecture decision records for the HOU53-bot
project. Each ADR captures **one** architecturally significant decision, the
context that drove it, the alternatives that were considered, and the
consequences of choosing it.

We use the [MADR 4.0](https://adr.github.io/madr/) template. It is short,
opinionated, and machine-readable.

## Why ADRs

- **Traceability.** Six months from now, nobody remembers why Neon was picked
  over Supabase. The ADR answers that without spelunking through Slack.
- **Review artifact.** A PR that introduces a new library, framework, or
  pattern without a linked ADR is incomplete.
- **Onboarding.** New contributors read the ADRs in order and understand
  the shape of the system before opening a single source file.

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
| [0003](./0003-database-choice.md) | Neon (serverless Postgres) for application data | proposed |
| [0004](./0004-data-versioning-dvc.md) | DVC for dataset and model artifact versioning | proposed |
| [0005](./0005-experiment-tracking-mlflow.md) | MLflow (local tracking) for experiment metadata | proposed |
| [0006](./0006-model-selection-xgboost.md) | XGBoost as the production regressor | proposed |
| [0007](./0007-evaluation-metric-rmse-log.md) | RMSE on `log1p(SalePrice)` as the primary metric | proposed |
| [0008](./0008-api-framework-fastapi.md) | FastAPI + Pydantic v2 for the inference service | proposed |
| [0009](./0009-frontend-stack.md) | Next.js 15 App Router + shadcn/ui + Tailwind v4 | proposed |
| [0010](./0010-nlp-parsing-strategy.md) | LLM with structured output for natural-language input | proposed |
