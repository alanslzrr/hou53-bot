# EDA reports

Exported EDA findings live here as markdown. The notebook is the scratchpad
(`ml/notebooks/01_eda.ipynb`); the markdown in this directory is the
**artifact** — the thing reviewers read and PRs cite.

Workflow:

1. Explore in the notebook.
2. Once findings stabilize, run `jupytext --to md:myst ...` or copy the
   conclusions + plots into `report.md`.
3. Any finding that drives a pipeline decision is linked from the relevant
   ADR.

Filled in Phase 1.
