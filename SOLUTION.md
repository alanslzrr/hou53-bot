# SOLUTION.md

This is the submission for the NTT Data Ames Housing challenge. I built
it as an end-to-end product: a scikit-learn pipeline serialised into a
single XGBoost artifact, a FastAPI service that loads it with SHAP
attribution wired in, and a Next.js app where the user describes a
property in natural language, reviews the parsed fields, confirms, and
gets a price plus an explanation. Both services run on Google Cloud
Run. Confirmed predictions live per-user in Neon Postgres.

## Build and run

### Local development

```bash
brew install libomp                                    # macOS only, for XGBoost
uv sync --all-groups                                   # ml + api + tooling
pnpm install                                           # apps/web
cp apps/web/.env.example apps/web/.env                 # fill values

uv run pytest                                          # backend test suite
pnpm --dir apps/web test                               # frontend test suite

uv run uvicorn app.main:app --reload --port 8000       # FastAPI on :8000
pnpm --dir apps/web dev                                # Next.js on :3000
```

The full dev workflow (pre-commit, Jupyter kernel registration, the
EDA notebook) is documented in [`CONTRIBUTING.md`](./CONTRIBUTING.md).

### Production (Google Cloud Run)

```bash
gcloud builds submit \
  --config=.gcp/cloudbuild-api.yaml \
  --substitutions=_IMAGE=<region>-docker.pkg.dev/<project>/hou53/api:latest

gcloud builds submit \
  --config=.gcp/cloudbuild-web.yaml \
  --substitutions=_IMAGE=<region>-docker.pkg.dev/<project>/hou53/web:latest

gcloud run deploy hou53-api --image=<...> --region=<...>
gcloud run deploy hou53-web --image=<...> --region=<...>
```

Image details: [`apps/api/Dockerfile.gcp`](./apps/api/Dockerfile.gcp)
(model artifact and dataset baked in) and
[`apps/web/Dockerfile.gcp`](./apps/web/Dockerfile.gcp). Required env
vars: [`apps/web/.env.example`](./apps/web/.env.example). The web
service mints Google ID tokens to call the API, so reviewers don't
need an API key to hit the deployed stack — only valid demo
credentials.

## Technical decisions

Decisions live as ADRs under [`docs/adr/`](./docs/adr/README.md). Each
one has the context, the alternatives I considered, and the trade-offs.

| Area | Summary | ADR |
|---|---|---|
| Monorepo layout | Offline ML separate from deployable services | [0001](./docs/adr/0001-monorepo-structure.md) |
| Git workflow | Squash-merge to `main`; Conventional Commits | [0002](./docs/adr/0002-git-workflow.md) |
| Database (Neon, predictions only) | JWT auth means no Auth.js adapter tables | [0003](./docs/adr/0003-database-choice.md) |
| Artifact versioning (in Git, no DVC) | 2 MB of binaries; DVC overkill | [0004](./docs/adr/0004-small-artifacts-in-git.md) |
| Experiment tracking (MLflow) | Local file backend; offline-reproducible | [0005](./docs/adr/0005-experiment-tracking-mlflow.md) |
| Regressor (XGBoost + Ridge baseline) | Ridge as sanity floor; XGBoost ships | [0006](./docs/adr/0006-model-selection-xgboost.md) |
| Primary metric (RMSE on `log1p`) | Matches Kaggle leaderboard; `TransformedTargetRegressor` wrap | [0007](./docs/adr/0007-evaluation-metric-rmse-log.md) |
| API (FastAPI + Pydantic v2) | Clean Architecture; schema generated from Python | [0008](./docs/adr/0008-api-framework-fastapi.md) |
| Frontend stack (Next.js + shadcn + Auth.js) | App Router, Tailwind v4, JWT sessions | [0009](./docs/adr/0009-frontend-stack.md) |
| NLP parsing (structured-output LLM) | Single-shot; user confirms before predict | [0010](./docs/adr/0010-nlp-parsing-strategy.md) |
| Assisted appraisal workflow (not chat) | Reducer-driven; readiness assistant for sparse input | [0011](./docs/adr/0011-assisted-appraisal-frontend.md) |
| Deployment on Google Cloud Run | Two services; Google ID-token service auth | [0012](./docs/adr/0012-deployment-on-google-cloud-run.md) |

Context that doesn't fit a single ADR:

- [`docs/architecture.md`](./docs/architecture.md) — runtime diagram,
  sequence diagram, ER schema, ownership boundaries.
- [`docs/model-card.md`](./docs/model-card.md) — model details,
  metrics, ethical notes.
- [`docs/eda/report.md`](./docs/eda/report.md) — EDA findings driving
  preprocessing.
- [`CHANGELOG.md`](./CHANGELOG.md) — per-phase change history.

## Aspects not implemented

- **NLP parser accuracy measured against the live OpenAI API.** The
  harness and dataset are in
  [`ml/src/hou53_ml/evaluation/nlp_parser.py`](./ml/src/hou53_ml/evaluation/nlp_parser.py)
  and [`ml/evals/nlp_parser/`](./ml/evals/nlp_parser/); no number
  produced.
- **GitHub Actions.** None configured.
- **Sentry, distributed tracing, and alerts.** Cloud Logging is the
  only observability layer.
- **Multi-model blending and Optuna hyperparameter search.** Single
  XGBoost artifact only. See
  [`docs/model-card.md`](./docs/model-card.md) for the rationale and
  the explicit future-improvements list.
- **Retrieval-augmented few-shot for the NLP parser.** Option 6 in
  [ADR-0010](./docs/adr/0010-nlp-parsing-strategy.md).
- **Multi-turn agent for the NLP parser.** Option 5 in
  [ADR-0010](./docs/adr/0010-nlp-parsing-strategy.md).

## Other considerations

- **Reproducibility from any commit.** Python (`uv.lock`), Node
  (`pnpm-lock.yaml`), the source CSV, and the production artifact are
  all in Git. `git clone` + `uv sync --all-groups` + `pnpm install`
  lands a reviewer on the exact bytes that produced the deployed
  model.
- **One schema, three consumers.** The 79-field house contract is
  defined once in `hou53_ml.io.Schema` and generates the FastAPI
  Pydantic input, the web's zod schema, and the NLP parser's
  structured-output schema. Drift breaks `pnpm build`, not
  production.
- **Determinism boundary.** The model and SHAP attribution are
  deterministic. The NLP parser is the only non-deterministic piece
  in the system, and it always hands control back to the form for
  human confirmation before any prediction is requested. Guardrails
  are in [ADR-0010](./docs/adr/0010-nlp-parsing-strategy.md).
- **Idempotency.** The BFF requires an `idempotency_key` per
  prediction; a retry returns the original row instead of burning a
  new model call. Enforced at the database with
  `UNIQUE(user_id, idempotency_key)` + `ON CONFLICT DO NOTHING`.
- **Sparse-input handling.** The readiness assistant scores the input
  deterministically and surfaces up to five targeted follow-up
  questions (rule-based, optionally LLM-rewritten) instead of
  blocking the prediction. The user always gets to proceed.
- **Privacy posture.** Auth via Auth.js Credentials/JWT (demo user
  via env). Predictions are filtered by `user_id`; nothing is shared
  across users. The browser never reaches FastAPI directly.
