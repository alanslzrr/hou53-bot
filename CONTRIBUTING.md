# Contributing to HOU53-bot

Solo project for the challenge. Structured for additional contributors.
The rules below keep the repository readable and reproducible.

## 1. Toolchain

| Tool | Version | Why |
|---|---|---|
| Python | 3.14 (see `.python-version`) | Challenge requirement |
| `uv` | latest | Env + dependency manager |
| Node.js | 20 LTS | Next.js runtime |
| pnpm | 9.x | Frontend package manager |
| Docker | 24+ | End-to-end run |
| DVC | 3.x | Data + model versioning |
| pre-commit | 3.x | Local linting gate |

One-time setup:

```bash
# Python (installs ml + api + dev tooling + jupyter stack)
uv sync --all-groups

# Pre-commit hooks
uv run pre-commit install --install-hooks
uv run pre-commit install --hook-type commit-msg

# Register the Jupyter kernel for IDE notebook support.
uv run python -m ipykernel install --user --name hou53-bot \
    --display-name "HOU53-bot (.venv)"
```

### IDE notebook support

- **PyCharm / VSCode**: open any notebook in `ml/notebooks/`, then in
  the kernel picker select `HOU53-bot (.venv)`. The venv has `pip`
  seeded for IDE package management.
- **JupyterLab** (no IDE): `uv run jupyter lab` from the repo root.
- Headless execution (CI gate after dependency changes):
  ```bash
  uv run jupyter nbconvert --to notebook --execute --inplace \
      ml/notebooks/01_eda.ipynb
  ```

## 2. Git workflow

Full rules in [`docs/adr/0002-git-workflow.md`](./docs/adr/0002-git-workflow.md).
Short version:

- Branch off `main`. Name `feat/<slug>`, `fix/<slug>`, `docs/<slug>`, etc.
- Branches live ≤ 3 days.
- Commits follow Conventional Commits 1.0.0.
- Rebase (do not merge) from `main` while the branch is open.
- Open a PR early, mark draft until ready.
- Squash-merge to `main`. One PR → one commit on `main`.

### Commit message template

```bash
git config commit.template .gitmessage
```

### Allowed commit types

`feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`,
`chore`, `revert`, `data` (DVC data change), `model` (DVC model change).

## 3. ADRs

Every architecturally significant decision gets an ADR. Process in
[`docs/adr/README.md`](./docs/adr/README.md).

A PR that introduces a new framework, service, storage system, or
protocol/schema change without a linked ADR is incomplete.

## 4. Code quality gates

Required green before merge:

- `uv run ruff check .`
- `uv run ruff format --check .`
- `uv run mypy ml/src apps/api/src`
- `uv run pytest`
- `pnpm --filter web lint` (Phase 6+)
- `pnpm --filter web test` (Phase 6+)

Wired into pre-commit hooks and CI.

## 5. Notebooks

- Notebooks live under `ml/notebooks/`. Both the `.ipynb` and a paired
  `.py` (Jupytext, percent format) are committed. Open the `.ipynb`;
  the `.py` mirrors it for reviewable PR diffs.
- Notebooks hold exploration, not production logic. Reusable code
  moves to `ml/src/hou53_ml/` with tests.
- `nbstripout` pre-commit hook strips outputs before commit so plot
  images do not enter Git history.

## 6. Data and model artifacts

- `data/raw/` and `data/external/` — small challenge source files kept
  in Git for reproducible local runs.
- `models/` — binary artifacts tracked with DVC pointers, never
  committed to Git directly.
- After `git pull`: `dvc pull` fetches model artifacts once a DVC remote
  is configured for the environment.
- Details: [`docs/adr/0004-data-versioning-dvc.md`](./docs/adr/0004-data-versioning-dvc.md).

## 7. Secrets and environment

- `.env` files, Each app ships `.env.example`.
- Required env vars are validated at startup (Pydantic Settings in
  Python, `zod` in the web app).
- A leaked credential is an incident — rotate immediately, open an issue.

## 8. Opening an issue

Use the GitHub issue templates. Issues about design decisions go
directly to an ADR draft — issues without a concrete next step are
closed.
