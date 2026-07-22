# ADR-0044 — Migration mapping is explicit, previewable and forgiving

- **Status:** accepted
- **Date:** 2026-07-22

## Context

ADR-0043 made the WXR inspection report the contract of the migration
flow; its author, category and tag inventories exist to be acted on.
Source sites arrive with bylines and taxonomies the target site does
not want verbatim: authors change names, categories merge, tags get
retired. The importer needs a way to express that — without editing the
export file and without a separate configuration format.

## Decision

- **Mapping is a set of explicit renames.** `--map-author`,
  `--map-category` and `--map-tag` each take `"source=target"` and
  repeat. Keys match exactly: authors by their source byline string,
  categories and tags by the slug the report shows.
- **An empty target drops the value.** `--map-tag "old-news="` removes
  the tag; `--map-author "Ghost="` clears the byline. Dropping is a
  mapping, not a separate switch.
- **Unmatched sources warn, never fail.** A mapping kept from a
  previous run may reference a term this incremental export does not
  contain; that is normal operation, so it produces a warning line and
  the import proceeds. Malformed specs (no `=`, empty source, a
  category or tag target that is not a slug) are errors.
- **The dry run previews the mapping.** `--dry-run` with mappings
  reports the post-mapping inventories — the operator sees the result
  before anything is written, from the same artifact the import uses.
- Mapping applies identically to fresh imports and `--update` runs.

## Consequences

- A migration keeps one growing set of mapping flags (or a shell
  script holding them) that stays valid across incremental re-runs.
- The admin flow inherits a ready contract: its mapping UI writes the
  same renames the CLI takes, and its preview renders the same
  post-mapping report.
- No new file format enters the project; mappings live in the command
  line that ran, which the operator already records.
