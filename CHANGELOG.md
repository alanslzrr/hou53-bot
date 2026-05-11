# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Entries are generated from [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/)
on release; until the first release, curated entries live under
`[Unreleased]`.

## [Unreleased]

### Added

- Phase 0 foundations: monorepo layout (`apps/`, `ml/`, `data/`, `models/`,
  `docs/`), 10 architecture decision records, `SOLUTION.md`, `CONTRIBUTING.md`,
  pre-commit toolchain, GitHub issue and PR templates, commit message
  template, and a standalone installable `ml/` Python package scaffold.

### Changed

- `pyproject.toml`: split runtime and development dependency groups,
  added lint/format/type/test tooling.
- `.gitignore`: added MLflow runs, DVC cache, and Node/Next.js artifacts.

### Removed

- _none_

[Unreleased]: https://github.com/Yagouus/hou53-bot/compare/main...HEAD
