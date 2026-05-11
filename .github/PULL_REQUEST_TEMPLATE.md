<!--
Thank you for the PR. Please fill in every section. Omit a section only if
you have replaced it with "N/A — <reason>".
-->

## Summary

<!-- One or two sentences on what this PR does and why. "Why" first. -->

## Type of change

<!-- Pick one — must match the commit type prefix. -->

- [ ] feat — new user-visible feature
- [ ] fix — bug fix
- [ ] docs — documentation only
- [ ] refactor — no behavior change
- [ ] perf — performance improvement
- [ ] test — adding or fixing tests
- [ ] chore / build / ci — tooling
- [ ] data — DVC-tracked dataset change
- [ ] model — DVC-tracked model change

## Linked ADR

<!--
If this PR introduces or changes an architecturally significant decision,
link the ADR. If not, write "N/A — not an architectural change".
-->

ADR: `docs/adr/NNNN-...md`

## How I tested it

<!--
Commands run, screenshots if UI, metrics if model. Enough that a reviewer
could reproduce without asking follow-up questions.
-->

## Checklist

- [ ] Conventional-commit title
- [ ] Tests added or updated (or marked N/A with reason)
- [ ] Docs / ADR updated (or marked N/A with reason)
- [ ] `uv run pre-commit run --all-files` passes locally
- [ ] No secrets or credentials in the diff
- [ ] If data or model changed: `dvc status` is clean and the `.dvc` files are in the diff
