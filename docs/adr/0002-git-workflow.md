# ADR-0002: Trunk-based development with Conventional Commits

- **Status:** proposed
- **Date:** 2026-04-21
- **Deciders:** Alan Salazar

## Context and Problem Statement

We need a Git workflow that keeps the main branch releasable at all times,
supports a small team, and produces a commit history that a human and a tool
(changelog generator) can both read.

## Decision Drivers

- The project is evaluated in part on how it resembles a "real production
  application" — long-lived release branches are the opposite of that.
- The solution must be delivered as a fork with a clean history — reviewers
  will read commits, not only the final code.
- We want to generate a `CHANGELOG.md` automatically rather than curating
  one by hand.
- Every ADR-worthy decision should have exactly one commit trail tying it to
  the PR and to the ADR file.

## Considered Options

1. **Gitflow** — `develop`, `release/*`, `hotfix/*`, `feature/*` long-lived
   branches.
2. **GitHub Flow** — feature branches off `main`, PR to `main`, deploy from
   `main`.
3. **Trunk-based development** — short-lived feature branches (≤ 2–3 days),
   squash-merge to `main`, deploy from `main`.

## Decision Outcome

Chosen option: **Trunk-based development** with **Conventional Commits** and
**squash-merge**, because it produces the cleanest `main` history, keeps
branches short enough that conflicts stay tractable, and plugs directly into
`git-cliff` for changelog generation.

### Positive Consequences

- `main` is always green and deployable.
- One PR → one squashed commit → one changelog entry. No noise.
- `feat:`, `fix:`, `docs:`, `chore:`, `refactor:`, `test:`, `perf:`, `ci:`,
  plus `data:` and `model:` for domain-specific changes, communicate intent
  at a glance.
- PR titles are validated by `commitlint` (via pre-commit hooks on the
  branch) before they reach CI.

### Negative Consequences / Trade-offs

- Squash-merge loses intermediate commits. Acceptable — we use draft PRs and
  checkpoint commits for WIP, and the squashed message captures the final
  story.
- Developers must learn the commit-type vocabulary. Mitigated by the
  `.gitmessage` template and commitlint running locally.

## Branch and commit rules

- **Main branch:** `main`, protected, linear history, required status checks.
- **Feature branches:** `feat/<short-slug>`, `fix/<short-slug>`,
  `docs/<short-slug>`. Maximum life: 3 days. Rebase (do not merge) from
  `main` while the branch is open.
- **Commit format:** Conventional Commits 1.0.0.
  `<type>(<scope>)!?: <summary>`. Body explains *why*, not *what*.
- **PR size:** aim for < 400 lines changed. Larger changes split into
  stacked PRs.
- **Linking ADRs:** any PR that introduces a significant decision must link
  the ADR in its description.

## Allowed commit types

| Type | Meaning |
|---|---|
| `feat` | New user-visible feature |
| `fix` | Bug fix |
| `docs` | Documentation only |
| `style` | Formatting, no logic change |
| `refactor` | Code restructure, no behavior change |
| `perf` | Performance improvement |
| `test` | Adding or fixing tests |
| `build` | Build system, dependencies |
| `ci` | CI configuration |
| `chore` | Miscellaneous (lint config, tool setup) |
| `revert` | Revert a previous commit |
| `data` | Dataset change |
| `model` | Model artifact change |

## Links

- [Conventional Commits 1.0.0](https://www.conventionalcommits.org/en/v1.0.0/)
- [Trunk-based development](https://trunkbaseddevelopment.com/)
