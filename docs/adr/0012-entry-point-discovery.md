# ADR-0012 — Extension discovery via Python entry points, loaded lazily

- **Status:** accepted
- **Date:** 2026-07-17

> Identifiers in this record predate the Stillsite → Sardine CMS rename
> ([ADR-0016](0016-rename-sardine-cms.md)): read `stillsite*` names as their
> `sardine*` successors.


## Context

The extensibility contracts left the plugin mechanism open ("entry points vs.
explicit registry"). The first installable extension — the reference theme —
forces the decision: a project setting `theme = "ph7x-reference"` must work
after `pip install cms-theme-ph7x-reference` with zero further configuration,
and the CLI cannot import arbitrary modules on faith.

## Decision

Both, layered — the explicit registry stays the API, entry points feed it:

- Packages declare extensions in standard entry-point groups —
  `stillsite.themes` now; `stillsite.targets`, `stillsite.backends`,
  `stillsite.plugins` follow the same pattern when needed.
- `create_theme(name)` resolves from the in-process registry first; on a
  miss it loads the matching entry point (by name), registers it, and
  retries. **Lazy by name**: nothing is imported unless the project asked
  for it, so startup cost and import side effects stay zero for unused
  extensions.
- `register_theme` remains public: tests, scripts and applications can
  register programmatically without packaging.

## Consequences

- Installing a theme package is the whole integration ("pip install, set the
  name, build").
- Unknown names still fail loudly, now with entry points consulted before
  the error — the no-silent-fallback rule holds.
- The pending plugin-mechanism question is settled as policy for every
  extension kind; remaining kinds adopt it on first need.
