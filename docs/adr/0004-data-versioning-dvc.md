# ADR-0004: DVC for dataset and model artifact versioning

- **Status:** proposed
- **Date:** 2026-04-21
- **Deciders:** Alan Salazar

## Context and Problem Statement

The raw Ames Housing CSV is ~500 KB — small enough to commit. The trained
XGBoost pipeline (joblib) plus its metadata will be a few MB. Neither is huge,
but both are binary assets whose history we want to track without polluting
Git diffs, and both must be reproducible end-to-end ("which dataset trained
which model?").

## Decision Drivers

- Model artifacts are binary — committing them to Git makes blame useless and
  the repo heavy over time.
- The evaluation criteria include reproducibility of training.
- A CI job (or a new contributor) must be able to fetch the exact dataset +
  model version associated with a commit, without manual steps.
- We want an audit trail: given a model in production, find the data that
  produced it.

## Considered Options

1. **Commit everything to Git** (CSV small, model small enough).
2. **Git LFS** for binary artifacts.
3. **DVC** with a remote (S3, R2, or GDrive for the challenge).
4. **MLflow Model Registry** as the only artifact store.

## Decision Outcome

Chosen option: **DVC with a Google Drive remote for the challenge (upgradable
to S3 later)**, because it gives us content-hashed versioning for data *and*
models with a CLI that feels Git-native, while staying free-tier friendly.

### Positive Consequences

- `dvc pull` after `git clone` fetches the exact dataset + model for that
  commit. One command, no Slack DMs.
- The `.dvc` files in Git are tiny — reviewable diffs on a text file with a
  content hash, instead of binary churn.
- DVC pipelines (`dvc.yaml`) let us declare "raw data → preprocess →
  train → evaluate" as a DAG; the DAG becomes the canonical training
  entry point, not a notebook.
- Works orthogonally with MLflow — DVC tracks the *what* (files and hashes),
  MLflow tracks the *how* (params, metrics, runs).

### Negative Consequences / Trade-offs

- Extra tool in the toolbox. Mitigated by the fact that for a newcomer,
  `dvc pull` is the only command they need.
- Google Drive remote is rate-limited and ugly for teams. Acceptable for the
  challenge deliverable; upgrade to S3-compatible (Cloudflare R2) is a
  config change.

## Pros and Cons of the Options

### Commit everything to Git

- Good, because no extra tool.
- Bad, because every retrain bloats the repo with an unreviewable binary.
- Bad, because no way to recover "data as of last Tuesday" without tagging.

### Git LFS

- Good, because transparent — `git checkout` just works.
- Bad, because GitHub LFS has a 1 GB free quota that fills up fast.
- Bad, because no pipeline concept — files are tracked, computation is not.

### DVC

- Good, because file versioning + pipeline DAG in one tool.
- Good, because remote-agnostic (S3, GCS, Azure, SSH, GDrive).
- Bad, because it is one more thing to learn.

### MLflow Model Registry

- Good, because model artifacts get a registry with stages
  (staging/production).
- Bad, because it only handles *model* artifacts — we still need a home for
  the dataset.
- Bad, because a registry server is infra we would have to run or pay for.

We will use MLflow for experiment tracking (ADR-0005) but not for artifact
storage — that is DVC's job.

## Links

- [DVC docs](https://dvc.org/doc)
- [ADR-0005 — MLflow](./0005-experiment-tracking-mlflow.md)
