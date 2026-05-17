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
# One-time system dep for XGBoost on macOS
brew install libomp

# Python (ml + api + dev tooling + jupyter stack)
uv sync --all-groups

# Register the Jupyter kernel for IDE notebook support (one-time).
uv run python -m ipykernel install --user --name hou53-bot \
    --display-name "HOU53-bot (.venv)"

# Verify everything runs.
uv run pytest                                          # 108 tests, ~3s
uv run jupyter nbconvert --to notebook --execute \
    --inplace ml/notebooks/01_eda.ipynb                # exec notebook headless
uv run python -m hou53_ml.training.train               # XGBoost + Ridge baseline
uv run uvicorn app.main:app --reload --port 8000       # API at :8000, /docs

# Optional
uv run mlflow ui --backend-store-uri ./mlruns          # browse experiment runs
uv run jupyter lab                                     # JupyterLab on :8888

# Try the API
curl http://localhost:8000/healthz
curl -X POST http://localhost:8000/v1/predict \
  -H "Content-Type: application/json" \
  -d '{"OverallQual":7,"GrLivArea":1800,"GarageCars":2,"YearBuilt":2000}'

# Web (Phase 6)
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

## What is implemented (so far)

- [x] **Phase 0** — monorepo skeleton, 10 ADRs, pre-commit, GitHub
      templates, workspace `pyproject.toml`, installable `hou53-ml`
      package.
- [x] **Phase 1 — EDA**
  - Tested helpers in `hou53_ml.eda.summary`
    (missing summary, target distribution, skew, correlations,
    cardinality, outlier mask).
  - Jupytext-paired notebook
    [`ml/notebooks/01_eda.py`](./ml/notebooks/01_eda.py).
  - Findings consolidated in
    [`docs/eda/report.md`](./docs/eda/report.md) — drives every
    Phase-2 preprocessing decision.
- [x] **Phase 2 — ML pipeline** (XGBoost artifact persisted)
  - `hou53_ml.features` — feature-aware imputation, structural derived
    features, fold-safe target encoding, ordinal encoders, and composable
    `ColumnTransformer`.
  - `hou53_ml.models` — Ridge baseline + XGBoost factory (lazy import).
  - `hou53_ml.pipelines` — full `TransformedTargetRegressor` pipeline.
  - `hou53_ml.evaluation` — RMSE-log / MAE / R² / median-APE +
    K-fold CV report.
  - `hou53_ml.serialization` — `ModelArtifact` (joblib +
    JSON metadata sidecar with dataset hash, library versions,
    metrics, schema fingerprint).
  - `hou53_ml.training` — stratified train/test split with outlier
    filtering + CLI entry point with MLflow logging.
  - `hou53_ml.explainability` — SHAP `TreeExplainer` wrapper that
    produces structured contributions + a plain-English sentence.

  Headline metrics (current XGBoost artifact, with Ridge as baseline):

  |  | Ridge (baseline) | **XGBoost (production)** |
  |---|---:|---:|
  | CV RMSE-log | 0.1203 ± 0.0091 | **0.1167 ± 0.0074** |
  | Test RMSE-log | **0.1243** | 0.1249 |
  | Test MAE | $13,432 | **$12,791** |
  | Test R² (USD) | 0.920 | **0.927** |
  | Test median APE | **5.63 %** | 5.79 % |

  Full discussion in [`docs/model-card.md`](./docs/model-card.md).
  SHAP explanations verified end-to-end on the saved artifact.

- [x] **Phase 4 — FastAPI inference service** (`apps/api/`)
  - Clean Architecture layout: `api → services → domain` + `infra`
    behind protocols.
  - 4 endpoints: `GET /healthz`, `GET /readyz`,
    `GET /v1/model/info`, `POST /v1/predict`.
  - Pydantic v2 input model **generated dynamically from
    `hou53_ml.io.Schema`** — single source of truth for the 79
    feature contract; aliases for columns starting with digits
    (`1stFlrSF`, `2ndFlrSF`, `3SsnPorch`).
  - Range / literal validation (years 1800–2100, OverallQual 1–10,
    quality scale `Ex/Gd/TA/Fa/Po/NA`) with structured 422 responses.
  - Model + SHAP explainer loaded once in the FastAPI lifespan;
    every request is sub-100 ms on the persisted XGBoost.
  - `structlog` JSON logs with per-request `x-request-id`
    propagation; CORS middleware preconfigured.
  - Multi-stage `uv`-based Dockerfile (Debian slim, libgomp1 for
    XGBoost), non-root user, healthcheck wired.
  - 14 API tests (stub model + real-artifact end-to-end), all green.
    **Combined repo test count: 108 tests in 3.4 s.**

  Live smoke against the persisted artifact:

  ```http
  POST /v1/predict
  → prediction: $114,903  (baseline $160,495)
    SHAP top: QualTotalSF −$22,260, Functional −$12,526,
              TotalSF −$10,980, QualArea +$8,998, OverallQual +$4,744
  ```

## What is not yet implemented

- [ ] **NLP parser** (Phase 5)
- [ ] **Next.js frontend** (Phase 6)
- [ ] **docker-compose end-to-end** (Phase 7)
- [ ] **CI/CD, observability** (Phase 8)

## Other considerations

- **Reproducibility.** Every commit on `main` pins: Python version
  (`.python-version`), Python dependencies (`uv.lock`), Node dependencies
  (committed lockfile), source dataset in Git, and model hashes
  (`models/*.dvc`). Fetching model binaries from another clone requires
  configuring the DVC remote.
- **Explainability.** The API returns top-contributing features (via SHAP
  `TreeExplainer`) with every prediction. The frontend renders them as a
  waterfall chart with a natural-language summary.
- **Input resilience.** The API validates inputs against a Pydantic schema
  generated from the training `ColumnTransformer` — any field missing or
  out of domain is rejected with a specific error.
- **Privacy.** User inputs are persisted only for authenticated users and
  only to power their own history. No PII beyond the auth email.
