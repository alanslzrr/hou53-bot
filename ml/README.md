# `ml/` — offline ML package

Everything that runs **offline** — data loading, feature engineering, model
training, evaluation, explainability helpers — lives here. The FastAPI
service (`apps/api/`) imports from this package for the shared feature
schema, so that training-time and serving-time are literally the same code.

This package is **not** deployed. What gets deployed is the serialized
pipeline artifact (`models/*.joblib`) plus the API image.

## Layout

```
ml/
├── src/hou53_ml/
│   ├── config.py         # typed runtime settings (pydantic-settings)
│   ├── constants.py      # domain constants (fields that legitimately use
│   │                     # "NA" as a category, not a missing value, etc.)
│   ├── io/               # load/save CSV, DVC-tracked paths
│   ├── features/         # ColumnTransformer builders (one module per block)
│   ├── pipelines/        # compose features + regressor into a Pipeline
│   ├── models/           # baseline + XGBoost wrappers
│   ├── training/         # CV, hyperparameter search, training entry points
│   ├── evaluation/       # metrics (RMSE log, MAE dollars, R²), reports
│   ├── explainability/   # SHAP wrappers + natural-language summaries
│   └── serialization/    # joblib save/load + metadata envelope
├── notebooks/            # EDA + experiments (Jupytext-paired)
├── configs/              # YAML configs for training runs
└── tests/                # unit + model invariance tests
```

Each subpackage has a **single** public surface — imports traverse
`hou53_ml.features.builders` → `hou53_ml.pipelines.training`, never the
other direction. This is the dependency-inversion rule of SOLID applied
minimally: upstream modules do not know about downstream ones.

## Commands

```bash
# From repo root
uv sync

# Run tests
uv run pytest ml/tests

# Train (added in Phase 2)
uv run python -m hou53_ml.training.train --config ml/configs/default.yaml

# Launch MLflow UI (from repo root)
uv run mlflow ui --backend-store-uri ./mlruns
```

## Notebooks

Notebooks are **paired with Jupytext** in light-percent format. Commit the
`.py` file; the `.ipynb` is generated locally and ignored by Git.

```bash
# Create a new notebook paired with a .py file
uv run jupytext --set-formats ipynb,py:light ml/notebooks/<name>.ipynb
```

Outputs are stripped automatically by the `nbstripout` pre-commit hook.
