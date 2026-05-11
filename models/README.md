# `models/` — trained artifacts (DVC-tracked)

Trained pipeline artifacts live here. **Never committed to Git directly** —
tracked with DVC (see [ADR-0004](../docs/adr/0004-data-versioning-dvc.md)).
The `.dvc` files (text, ~200 bytes each) live in Git; the binary
`*.joblib` files live on the DVC remote and are fetched with `dvc pull`.

## Expected contents (Phase 3)

| File | Format | Purpose |
|---|---|---|
| `hou53-pipeline.joblib` | joblib | Serialized sklearn `Pipeline` (preprocess + XGBoost + target transform) |
| `model_metadata.json` | JSON | Version, training date, dataset hash, metrics, feature schema |
| `shap_background.parquet` | parquet | Background dataset for the SHAP `TreeExplainer` (small sample of training rows) |

## Reproduce

```bash
git clone <repo>
dvc pull          # fetches whatever this commit's .dvc files point to
```
