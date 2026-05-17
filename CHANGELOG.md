# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Entries are generated from [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/)
on release; until the first release, curated entries live under
`[Unreleased]`.

## [Unreleased]

### Added

- **Phase 4 — FastAPI inference service** (`apps/api/`).
  -  Architecture layout (`api/`, `services/`, `domain/`,
    `infra/`); domain has zero FastAPI / sklearn imports.
  - Endpoints: `GET /healthz`, `GET /readyz`,
    `GET /v1/model/info`, `POST /v1/predict`. OpenAPI at
    `/openapi.json`, Swagger at `/docs`.
  - Input Pydantic model generated dynamically from
    `hou53_ml.io.Schema` with aliases for columns starting with
    digits and field-level validators (years, quality scale,
    OverallQual range).
  - Lifespan loads the artifact + fits the SHAP explainer once.
    Per-request handler reuses both — sub-100 ms predictions.
  - `structlog` JSON logs with `x-request-id` middleware; CORS
    preconfigured for the future Next.js frontend.
  - Multi-stage `uv`-based Dockerfile (Debian slim + libgomp1),
    non-root user, healthcheck.
  - 14 API tests (stub-backed router tests + 2 end-to-end against the
    real artifact). Combined repo suite: **108 tests in ~3.4 s.**
- **Phase 2 — ML pipeline** (XGBoost artifact persisted, Ridge baseline
  logged for comparison).
  - `hou53_ml.features` — neighborhood-aware `LotFrontage` imputation,
    structural derived features, fold-safe `NeighborhoodPriceLog`
    target encoding, ordinal encoders, and composable
    `build_preprocessor`.
  - `hou53_ml.models` — Ridge baseline factory and XGBoost factory
    (lazy `xgboost` import so the package loads without `libomp`).
  - `hou53_ml.pipelines` — full `TransformedTargetRegressor`
    (`log1p` target wrap) composing derived features + preprocessor +
    estimator into a single deployable artifact.
  - `hou53_ml.evaluation` — RMSE-log, MAE-dollars, R², median APE +
    K-fold cross-validation report dataclass.
  - `hou53_ml.serialization` — `ModelArtifact` (joblib pipeline +
    sidecar JSON with dataset SHA-256, library versions, schema
    fingerprint, headline metrics).
  - `hou53_ml.training` — stratified train/test split with
    outlier filtering, MLflow logging, and a CLI entry point
    (`python -m hou53_ml.training.train`).
  - `hou53_ml.explainability` — SHAP `TreeExplainer` wrapper that
    returns structured per-feature contributions plus a one-sentence
    plain-English summary.
  - 94 ML tests covering loaders, schema, EDA helpers, feature-aware
    imputation, derived features, target encoding, ordinal encoders,
    preprocessor, metrics, splits, serialization, SHAP, and an
    end-to-end Ridge pipeline test.
  - Production training run (XGBoost): CV RMSE-log **0.1167 ± 0.0074**,
    test RMSE-log **0.1249**, test MAE **$12,791**, test median APE
    **5.79 %**, test R² (USD) **0.927**. Ridge baseline CV RMSE-log
    is 0.1203 for comparison. SHAP explanations verified end-to-end
    on the persisted artifact (`models/hou53-pipeline.joblib`).
- **Phase 1 — EDA**.
  - Stateless EDA helpers in `hou53_ml.eda.summary` (missing summary,
    target distribution, skew, correlations, cardinality, outlier
    mask).
  - Jupytext-paired notebook `ml/notebooks/01_eda.py`.
  - Findings consolidated in `docs/eda/report.md` — single source of
    truth driving every Phase-2 preprocessing decision.
- **Phase 0 — Foundations.** Monorepo layout (`apps/`, `ml/`, `data/`,
  `models/`, `docs/`), 10 architecture decision records, `SOLUTION.md`,
  `CONTRIBUTING.md`, pre-commit toolchain, GitHub issue / PR templates,
  commit message template, installable `hou53-ml` package scaffold.

### Changed

- Root `pyproject.toml`: added `apps/api` as a uv workspace member,
  added `httpx` to the dev group (FastAPI's TestClient dep), enabled
  pytest's `--import-mode=importlib` so per-app `conftest.py` files
  do not collide.
- `hou53_ml.constants`: added `NUMERIC_ORDINAL_FEATURES`
  (`OverallQual`, `OverallCond`) so the API DTO can range-validate
  them as integers instead of strings.
- `ml/pyproject.toml`: added `seaborn`, `missingno`, `matplotlib`
  (explicit) for EDA plots.
- `hou53_ml.constants`: added `SKEWED_NUMERIC_FEATURES`,
  `DERIVED_NUMERIC_FEATURES`, `DERIVED_BINARY_FEATURES`,
  `ACTUAL_MISSING_NUMERIC`, `ACTUAL_MISSING_CATEGORICAL` derived from
  the EDA findings.
- `pyproject.toml`: split runtime and development dependency groups,
  added lint/format/type/test tooling.
- `.gitignore`: added MLflow runs, DVC cache, Node/Next.js artifacts.

### Removed

- _none_

[Unreleased]: https://github.com/Yagouus/hou53-bot/compare/main...HEAD
