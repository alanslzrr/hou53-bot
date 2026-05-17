# Notebooks

Exploration and experiments. Not production code. Anything reusable
beyond a single notebook moves to `ml/src/hou53_ml/` with tests.

## Files per notebook

Each notebook is committed as two paired files:

- `<NN>_<slug>.ipynb` — opened in Jupyter / VSCode / PyCharm.
- `<NN>_<slug>.py` — Jupytext mirror in percent format. Edits to
  either side propagate to the other when Jupytext is installed.

Reason for the pair: `git diff` on `.ipynb` JSON is unreadable; the
`.py` produces reviewable diffs. The `nbstripout` pre-commit hook
clears `.ipynb` outputs before commit so plot images do not enter Git
history.

## Create a new notebook

```bash
uv run jupytext --set-formats "ipynb,py:percent" ml/notebooks/<NN>_<slug>.ipynb
```

Naming: `01_eda.ipynb`, `02_feature_engineering.ipynb`, etc.

## Conventions

- Each notebook ends with a markdown cell summarising findings and
  linking to any code promoted into `hou53_ml`.
- Long-lived findings move to `docs/eda/report.md` (or equivalent
  markdown). The notebook is the scratch pad; the markdown is the
  authority.
