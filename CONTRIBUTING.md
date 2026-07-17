# Contributing

## Workflow

1. Create a branch off `main` (`feature/...`, `fix/...`, `docs/...`).
2. Small increments, clear imperative commits (`Add page schema validation`).
3. Before opening a PR: lint, type checking and tests must pass locally.
4. `main` is fully protected, **admins included**: no direct pushes, no
   force-pushes, no deletion. Every change lands via pull request with all
   six CI checks green, linear history (squash or rebase merge) and resolved
   conversations. Branches are deleted on merge.

## Project rules

- No editorial text hardcoded in templates — all content comes from the content model.
- Language parity is mandatory: EN is the source; PT-PT, ES, FR and DE are validated.
- Deterministic build: the same input produces the same output.
- No secrets, personal data or client content.
- Architecture decisions recorded in `docs/adr/`.
- WCAG 2.2 AA accessibility as the baseline for the admin panel and reference theme.
- **Docs move with the code**: any change that affects behavior, structure or
  plans updates README/PLAN/ADRs in the same commit. `tests/test_docs.py`
  compares the docs against the code in CI, so drift fails the build — when
  adding a documented fact worth guarding, add its check there too. Keep each
  fact in one authoritative document and link to it instead of repeating it.

## Commands (target)

```bash
cms validate && pytest   # before any PR
```
