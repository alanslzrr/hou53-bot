# ADR-0004: Keep small challenge data and model artifacts in Git

- **Status:** proposed
- **Date:** 2026-04-21
- **Deciders:** Alan Salazar

## Context and Problem Statement

HOU53-bot needs a reproducible handoff between training and serving:
the FastAPI service must load the exact model artifact produced by the
training pipeline, and reviewers must be able to clone the repository
and run the project without provisioning external storage.

The current artifacts are small:

- `data/raw/house_prices.csv` is about 452 KB.
- `data/external/data_description.txt` is a small text reference.
- `models/hou53-pipeline.joblib` is about 1.6 MB.
- `models/model_metadata.json` is about 8 KB.

The question is whether these files need a separate artifact store, or
whether plain Git is the simplest reproducible option.

## Decision Drivers

- A fresh clone should contain the runnable challenge artifact.
- No external credentials or storage service should be required for local
  development, review, or `docker compose` later.
- The repository should stay easy to understand and operate.
- Binary size is far below GitHub's practical limits for this project.

## Considered Options

1. **Commit the challenge dataset and production model artifact to Git.**
2. **Use Git LFS for binary artifacts.**
3. **Use an external artifact/versioning tool.**
4. **Rely on MLflow artifacts only.**

## Decision Outcome

Chosen option: **commit the current challenge data and production model
artifact directly to Git**, because the files are small and this gives the
cleanest clone-and-run workflow.

An external artifact/versioning tool could be used here, but at the current
file sizes it does not solve an actual problem. It would add setup,
credentials, and operational failure modes without improving the reviewer
or developer experience.

### Positive Consequences

- `git clone` contains the raw dataset, model artifact, and metadata.
- The API can run locally without a separate artifact-fetch step.
- Docker composition can mount or copy `models/` directly.
- Fewer moving parts in local setup and CI.

### Negative Consequences / Trade-offs

- Model binaries are not human-reviewable in Git diffs.
- Re-training the model changes a binary file in the commit.
- The project must avoid committing exploratory run directories; those
  stay under ignored paths such as `mlruns/` and `mlartifacts/`.

## Pros and Cons of the Options

### Commit files to Git

- Good, because it is the simplest reproducible workflow.
- Good, because current file sizes are tiny for Git.
- Bad, because binary diffs are opaque.

### Git LFS

- Good, because it keeps binary storage outside normal Git objects.
- Bad, because it adds another install/runtime expectation.
- Bad, because it is unnecessary at the current artifact sizes.

### External artifact/versioning tool

- Good, because it can provide external storage and content-addressed
  references for artifacts.
- Bad, because it adds storage configuration, credentials, and another
  command to the clone/run path.
- Bad, because this project's current artifacts are too small to justify it.

### MLflow artifacts only

- Good, because training runs already log metrics and artifacts locally.
- Bad, because `mlruns/` is intentionally ignored and not the serving
  contract.
- Bad, because reviewers should not need to inspect MLflow runs to find the
  production artifact.

## Links

- [ADR-0005 — MLflow](./0005-experiment-tracking-mlflow.md)
