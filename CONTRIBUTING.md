# Contributing to HOU53-bot

This is a solo project for the challenge, but it is structured as
if more people might join tomorrow. These rules keep the repository
readable and reproducible.

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

Set up once:

```bash
# Python
uv sync

# Pre-commit hooks
uv run pre-commit install --install-hooks
uv run pre-commit install --hook-type commit-msg
```

## 2. Git workflow

Full rules in [`docs/adr/0002-git-workflow.md`](./docs/adr/0002-git-workflow.md).
Short version:

- Branch off `main`. Name it `feat/<slug>`, `fix/<slug>`, `docs/<slug>`, etc.
- Keep branches short-lived (≤ 3 days).
- Commits follow **Conventional Commits 1.0.0**.
- Rebase (do not merge) from `main` while the branch is open.
- Open a PR early, mark it draft until ready.
- Squash-merge to `main`. One PR → one commit on `main`.

### Commit message template

`.gitmessage` is pre-registered. To enable globally for this repo:

```bash
git config commit.template .gitmessage
```

### Allowed commit types

`feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`,
`chore`, `revert`, `data` (DVC data change), `model` (DVC model change).

## 3. ADRs

Every architecturally significant decision gets an ADR. See
[`docs/adr/README.md`](./docs/adr/README.md) for the process.

A PR that introduces a new framework, a new service, a new storage system,
or a protocol/schema change without a linked ADR is incomplete.

## 4. Code quality gates

The following must be green before merging:

- `uv run ruff check .`
- `uv run ruff format --check .`
- `uv run mypy ml/src apps/api/src`
- `uv run pytest`
- `pnpm --filter web lint` (when the web app is introduced)
- `pnpm --filter web test` (when the web app is introduced)

All of the above are wired into the pre-commit hooks and into CI.

## 5. Notebooks

- Notebooks live under `ml/notebooks/` and are **paired with Jupytext**.
  Commit the `.py` light-percent file; the `.ipynb` is regenerated.
- Notebooks are for exploration, **not** for production logic. Any function
  that matters beyond the notebook moves to `ml/src/hou53_ml/`.
- Notebook outputs are stripped by the `nbstripout` pre-commit hook.

## 6. Data and model artifacts

- Raw data: in `data/raw/`, **DVC-tracked**, never committed to Git.
- Trained models: in `models/`, **DVC-tracked**, never committed to Git.
- After `git pull`, run `dvc pull` to fetch artifacts for the current commit.
- See [`docs/adr/0004-data-versioning-dvc.md`](./docs/adr/0004-data-versioning-dvc.md).

## 7. Secrets and environment

- `.env` files are never committed. Each app ships a `.env.example`.
- Required env vars are validated at startup (Pydantic Settings in Python,
  `zod` in the web app).
- No credentials in commits, ever. A leaked key is an incident — rotate
  immediately and open an issue.

## 8. Opening an issue

Use the GitHub issue templates. If the issue is about a design decision,
open an **ADR draft** directly — issues without a concrete next step get
closed.
