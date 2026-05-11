# Notebooks

Exploration and experiments. **Not production code.** Anything that matters
beyond a single notebook is promoted into `ml/src/hou53_ml/` with tests.

## Rules

- **Paired with Jupytext** in light-percent format. Commit the `.py`
  version; the `.ipynb` is regenerated.
- Outputs are stripped by the `nbstripout` pre-commit hook.
- Each notebook ends with a markdown cell summarizing findings and linking
  to any code that was promoted to the package.

## Creating one

```bash
uv run jupytext --set-formats ipynb,py:light ml/notebooks/<NN>_<slug>.ipynb
```

Naming: `01_eda.ipynb`, `02_feature_engineering.ipynb`, `03_baseline.ipynb`, etc.
