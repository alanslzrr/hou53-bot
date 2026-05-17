# ADR-0005: MLflow (local tracking) for experiment metadata

- **Status:** proposed
- **Date:** 2026-04-21
- **Deciders:** Alan Salazar

## Context and Problem Statement

During training we will run dozens to hundreds of experiments (hyperparameter
trials, feature ablations, different CV seeds). Each one has params, metrics,
and artifacts (the fitted pipeline, SHAP plots). We need a way to recover
"which combination of inputs produced the best model, and where is that
model?" without relying on filenames or memory.

## Decision Drivers

- The canonical model lineage must be queryable (params → metrics → artifact
  path).
- The tool must work fully offline — no account, no cloud egress required for
  a challenge grader to reproduce results.
- Must integrate cleanly with scikit-learn pipelines and Optuna.
- Must not impose a server to run for the challenge deliverable (grader runs
  `docker compose up` and everything works).

## Considered Options

1. **Print statements + CSVs** — log manually.
2. **MLflow** with the file-based tracking backend.
3. **Weights & Biases**.
4. **Comet ML** / **Neptune**.

## Decision Outcome

Chosen option: **MLflow with `file:./mlruns` backend**, because it meets every
driver without requiring network access or an account, and it is the de-facto
standard the evaluators will recognize.

### Positive Consequences

- `mlflow.autolog()` plus a handful of explicit `log_param`/`log_metric` calls
  capture everything we care about.
- `mlflow ui` is a single command to browse runs locally.
- MLflow's `pyfunc` model flavor gives us a uniform `predict()` signature
  independent of which scikit-learn/XGBoost API we use.
- Runs are content-addressable on disk — reproducible across machines once
  the `mlruns/` directory is archived.

### Negative Consequences / Trade-offs

- `mlruns/` can grow large. Mitigated by `.gitignore` (it is never
  committed); the production artifact is exported explicitly to `models/`.
- No team features (sharing, permissions). Out of scope for the challenge.

## Division of labor between MLflow and committed artifacts

| Concern | Tool |
|---|---|
| Challenge dataset and production model file storage | Git |
| Training DAG (load data → features → train → export artifact) | Python entry point |
| Run metadata (params, metrics, tags) | MLflow |
| Intra-run artifacts (plots, feature importances) | MLflow |
| "This commit used this dataset and produced this model" | Git + model metadata JSON |
| "Which hyperparameters won CV?" | MLflow |

## Pros and Cons of the Options

### Print + CSVs

- Good, because zero setup.
- Bad, because nothing is queryable.
- Bad, because nobody ever actually does this rigorously.

### MLflow (file backend)

- Good, because open source, offline, industry standard.
- Good, because the `pyfunc` abstraction is useful for the API handoff.
- Bad, because the UI is serviceable but dated.

### Weights & Biases

- Good, because the UI and collaboration features are excellent.
- Bad, because it requires a cloud account — the grader cannot reproduce
  without credentials.
- Bad, because it is overkill for a single-developer challenge.

### Comet / Neptune

- Same trade-offs as W&B — SaaS-first.

## Links

- [MLflow docs](https://mlflow.org/docs/latest/index.html)
- [ADR-0004 — small artifacts in Git](./0004-small-artifacts-in-git.md)
