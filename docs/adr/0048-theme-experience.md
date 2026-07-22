# ADR-0048 — Themes are discovered, tried and activated; never installed by the panel

- **Status:** accepted
- **Date:** 2026-07-23

## Context

Theme contracts exist (the protocol, entry-point resolution, overrides,
the section-kind gallery) but the experience does not: choosing a theme
means editing `sardine.toml` by hand. The panel needs to close that gap
without acquiring powers it should not have.

## Decision

- **The panel never installs packages.** Themes arrive in the
  environment the way everything else does — the operator's package
  manager or container image. The panel's "install experience" is
  discovery: it enumerates every installed theme through the
  `sardine.themes` entry-point group, bundled and third-party alike,
  shows which one is active, and shows each package's version. A panel
  that executes package installation would be arbitrary code execution
  behind a login form.
- **Activation is try-first, write-second.** Activating a theme
  resolves it and runs a trial build of the current published content
  in memory; only a successful build writes `theme = "…"` into
  `[site]` — a surgical rewrite that leaves the rest of the file
  exactly as the owner wrote it. A failing theme shows its error in
  the screen, the config stays untouched, and the site never becomes
  unbuildable through the panel.
- **Compatibility is proven, not declared.** The trial build against
  the project's real content is the compatibility check — themes must
  render unknown section kinds generically by contract, and the build
  exercises exactly that. A declared-metadata contract (description,
  screenshot) is a later, additive step; its absence never blocks.
- **Failure is visible and recoverable.** A theme that fails to
  resolve or render appears in the list with its error; the active
  theme failing does not take the screen down, and switching to a
  working theme remains one click. Activation lands in the audit
  trail.
- **Updates belong to the environment.** The panel displays the
  installed package version; updating is a package operation and never
  mutates project config.

## Consequences

- Choosing a theme becomes reversible and safe: the worst outcome of
  an activation attempt is an error message, never a broken site.
- Third-party themes get the same surface as bundled ones the moment
  they are installed — no registry, no marketplace, no code executed
  before the operator asks for a build.
- The extension experience (activate/deactivate, settings, health)
  will follow the same shape in its own decisions; this record covers
  themes.
