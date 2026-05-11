# `data/`

Four subdirectories, each with a specific role:

| Dir | Purpose | Tracked by |
|---|---|---|
| `raw/` | The original Kaggle/Inria CSV, verbatim. Never edit in place. | DVC |
| `external/` | Third-party references (e.g., `data_description.txt`). | Git (small, rarely changes) |
| `interim/` | Intermediate artifacts of preprocessing. Safe to delete anytime. | gitignored |
| `processed/` | Final model-ready matrices (train/test splits). | gitignored |

See [ADR-0004](../docs/adr/0004-data-versioning-dvc.md) for the DVC story.

## Reproduce

```bash
dvc pull          # pulls `data/raw/*` for the current commit
```

The training pipeline (Phase 2 onwards) reads from `raw/` + `external/`
and materializes `interim/` and `processed/` — those are derivable and do
not need to be versioned.
