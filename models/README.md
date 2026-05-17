# `models/` — trained artifacts

Trained production artifacts live here and are committed directly to Git.
The current model and metadata files are small enough that adding an
external artifact store would add operational overhead without improving
the clone-and-run workflow.

See [ADR-0004](../docs/adr/0004-small-artifacts-in-git.md).

## Expected contents (Phase 3)

| File | Format | Purpose |
|---|---|---|
| `hou53-pipeline.joblib` | joblib | Serialized sklearn `Pipeline` (preprocess + XGBoost + target transform) |
| `model_metadata.json` | JSON | Version, training date, dataset hash, metrics, feature schema |
| `shap_background.parquet` | parquet | Background dataset for the SHAP `TreeExplainer` (small sample of training rows) |

## Reproduce

```bash
git clone <repo>
uv sync --all-groups
uv run uvicorn app.main:app --app-dir apps/api/src --port 8000
```
