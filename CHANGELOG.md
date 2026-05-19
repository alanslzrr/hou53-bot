# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Entries are generated from [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/)
on release; until the first release, curated entries live under
`[Unreleased]`.

## [Unreleased]

### Added

- **Phase 7 — Deployment on Google Cloud Run.**
  - `.gcp/cloudbuild-api.yaml`, `.gcp/cloudbuild-web.yaml`,
    `.gcloudignore`.
  - `apps/api/Dockerfile.gcp` — runtime image with the model artifact
    and dataset baked in.
  - `apps/web/Dockerfile.gcp` — multi-stage `pnpm` build.
  - `apps/web/src/server/gcp/authenticated-cloud-run-fetch.ts` —
    Google ID-token signing for service-to-service calls.
  - Rationale and trade-offs:
    [ADR-0012](./docs/adr/0012-deployment-on-google-cloud-run.md).

- **Phase 6 — Assisted appraisal frontend (`apps/web/`).**
  - Next.js 15 App Router, shadcn/ui, Tailwind v4, Drizzle, Neon.
  - Reducer-driven estimate workspace with twelve states (idle →
    parsing → parsed → editing → assessing → needs_more_signal →
    applying_answers → predicting → predicted, plus per-step error
    states).
  - Auth.js CredentialsProvider with JWT sessions, demo user via env,
    no DB adapter.
  - BFF route `POST /api/predict` (session check, idempotency lookup,
    FastAPI call, persistence, normalized response). Idempotency
    enforced at the database with `UNIQUE(user_id, idempotency_key)`
    and `ON CONFLICT DO NOTHING`.
  - Drizzle schema for the `predictions` table; migration applied
    against the configured Neon database.
  - History views (`/history`, `/history/[id]`).
  - Readiness assistant: deterministic 0-100 input score over six
    signal groups, up to five follow-up questions (rule-based,
    optionally LLM-rewritten). Documented as the readiness extension
    in [ADR-0010](./docs/adr/0010-nlp-parsing-strategy.md).
  - 51 Vitest tests.
  - Workflow decision: [ADR-0011](./docs/adr/0011-assisted-appraisal-frontend.md).

- **Phase 5 — NLP parser (`POST /api/parse`).**
  - Next.js route using AI SDK `generateText` + `Output.object`
    against the Pydantic-derived house input schema.
  - Eight operational guardrails (bounded input, content-length
    precheck, timeout, deterministic settings, errors-as-data, rate
    limit, structured logs, schema validation).
  - Generated TS contract under `apps/web/src/lib/housing/` keeps the
    79-field schema in sync with the Python `Schema`.
  - Eval harness in `ml/src/hou53_ml/evaluation/nlp_parser.py`
    plus 120 synthetic descriptions in `ml/evals/nlp_parser/`. CLI
    gate `--min-accuracy` returns non-zero exit code below threshold.
  - Strategy and trade-offs: [ADR-0010](./docs/adr/0010-nlp-parsing-strategy.md).

- **Phase 4 — FastAPI inference service (`apps/api/`).**
  - Clean Architecture layout (`api`, `services`, `domain`, `infra`).
  - Endpoints `GET /healthz`, `GET /readyz`, `GET /v1/model/info`,
    `POST /v1/predict`. OpenAPI at `/openapi.json`, Swagger at `/docs`.
  - Input Pydantic model generated dynamically from
    `hou53_ml.io.Schema` with field-level validators.
  - Lifespan loads artifact and SHAP explainer once.
  - Multi-stage `uv` Dockerfile (Debian slim, `libgomp1`, non-root).
  - 14 API tests.
  - Framework decision: [ADR-0008](./docs/adr/0008-api-framework-fastapi.md).

- **Phase 2 — ML pipeline (`ml/`).**
  - `hou53_ml.features` — neighborhood-aware imputation, fold-safe
    target encoding, structural derived features, ordinal encoders,
    composable preprocessor.
  - `hou53_ml.models` — Ridge baseline and XGBoost factory.
  - `hou53_ml.pipelines` — `TransformedTargetRegressor(log1p)`
    wrapping derived features + preprocessor + estimator.
  - `hou53_ml.evaluation` — metrics + K-fold cross-validation report.
  - `hou53_ml.serialization` — `ModelArtifact` (joblib + sidecar
    metadata JSON).
  - `hou53_ml.training` — stratified split with documented outlier
    filter, MLflow logging, CLI entry point.
  - `hou53_ml.explainability` — SHAP `TreeExplainer` wrapper with
    structured contributions and natural-language summary.
  - Production training run completed; numbers in
    [`docs/model-card.md`](./docs/model-card.md).
  - Decisions: [ADR-0006](./docs/adr/0006-model-selection-xgboost.md),
    [ADR-0007](./docs/adr/0007-evaluation-metric-rmse-log.md).

- **Phase 1 — EDA.**
  - Stateless helpers in `hou53_ml.eda.summary`.
  - Jupytext-paired notebook (`ml/notebooks/01_eda.{py,ipynb}`).
  - Findings consolidated in
    [`docs/eda/report.md`](./docs/eda/report.md) — drives every
    Phase-2 preprocessing choice.

- **Phase 0 — Foundations.** Monorepo layout, twelve ADRs,
  `SOLUTION.md`, `CONTRIBUTING.md`, pre-commit toolchain, GitHub
  issue / PR templates, commit message template, installable
  `hou53-ml` package scaffold.

### Changed

- Two test stacks: `uv run pytest` (Python) and
  `pnpm --dir apps/web test` (web).
- `apps/api/Dockerfile.gcp` differs from the local `Dockerfile`:
  Cloud Run image bakes the artifact and dataset; the local image
  expects mounts.
- ADRs [0003](./docs/adr/0003-database-choice.md) and
  [0009](./docs/adr/0009-frontend-stack.md) rewritten to match the
  implemented stack (Auth.js without DB adapter; Neon scoped to
  prediction history only).
- Root `pyproject.toml`: `apps/api` workspace member, `httpx` in dev
  group, pytest `--import-mode=importlib`.
- `ml/pyproject.toml`: added `seaborn`, `missingno`, `matplotlib`.
- `apps/web/package.json`: shadcn, Drizzle, AI SDK, Auth.js,
  `google-auth-library`.
- `.gitignore`: MLflow runs, generated data, Node / Next.js artifacts.

### Removed

- DVC scaffolding (`.dvc/`, `.dvcignore`, `models/*.dvc`, the
  superseded DVC ADR). Rationale in
  [ADR-0004](./docs/adr/0004-small-artifacts-in-git.md).

[Unreleased]: https://github.com/Yagouus/hou53-bot/compare/main...HEAD
