# ADR-0056 — Deprecation policy: obligations, not calendars

- **Status:** accepted
- **Date:** 2026-07-25

## Context

Before 1.0, Sardine CMS could change anything. After 1.0 it promises
stability over the surfaces [PUBLIC_CONTRACTS.md](../PUBLIC_CONTRACTS.md)
lists, and a promise without a removal policy is not a promise — it is
an intention. Integrators need to know, before they build, what
withdrawal looks like.

The temptation is a calendar: "twelve months' notice". For a project
that may not release in that window, a time promise reads strong and
resolves ambiguously. What integrators actually plan against is
releases: *which version can still break me?*

This ADR therefore fixes obligations — announcement, replacement,
earliest removal, evidence — and ties removal to major versions rather
than to dates.

## Decision

### What this policy covers

Every surface PUBLIC_CONTRACTS lists as public: integration contracts
(translation providers, forms providers, deployment providers),
conformance suites (theme, translation, UI), the `cms` command line and
its options, `sardine.toml`, portable content and export formats, and
the panel's documented HTTP surface and behaviors. Integration points
without a contract version are covered too — their normative
specification is where a deprecation is announced.

### How a deprecation begins

A deprecation exists only when all of these are true:

1. **It is announced in the normative specification** of the surface —
   the one document PUBLIC_CONTRACTS names for it, never only in a
   changelog entry or a guide.
2. **A replacement or migration path is stated.** "Do not use this" is
   not a deprecation; it is a warning without an exit.
3. **The version it was deprecated in is recorded.**
4. **The earliest version in which removal may occur is recorded.**
5. **The runtime says so where it technically can** — a CLI notice, a
   panel hint, a `cms doctor` line, a CI warning, or the documentation
   alone when no execution path exists to carry it.

Anything short of that list is not deprecated; it is merely
discouraged, and removal timing does not start.

### When removal may happen

> **A deprecated public surface is not removed within the same major
> version.**

Within 1.x a surface may be marked deprecated, gain a replacement, and
stay working; removal waits for 2.0. This is the guarantee integrators
plan against, and it is deliberately release-based: it does not weaken
if the project releases slowly.

Two clarifications that follow from it:

- **Contracts with their own version bump independently.** Removing an
  obligation or a declared capability from an integration contract, or
  changing a suite so a previously conforming implementation is no
  longer conforming, requires a **new contract or suite version** even
  while the product stays 1.x. The old version remains documented for
  as long as the product supports it.
- **Operational aim, not a rule:** where a replacement exists, keep the
  deprecated surface through at least two minor releases before the
  next major is prepared, so adoption has room. This is a target the
  project holds itself to; it never overrides the major-version
  guarantee, and missing it is not a licence to remove early.

### What is not a deprecation

Naming these prevents the policy from being invoked where it does not
apply:

- **Internal refactoring.** Modules, symbols and implementation details
  outside the documented surfaces were never promised (see the 1.0
  scope in ROADMAP.md).
- **Harness corrections.** Fixing a check so it measures the rule it
  already published — the DS-6 gate moving from a `scrollWidth`
  comparison to a real attempted scroll, or wording that had let a
  fixture's size read as a threshold — changes no obligation and
  consumes no version.
- **Clarifications** that do not change semantics.
- **Compatible additions**: new optional capabilities, new optional or
  informative checks, additional fixtures exercising the same
  invariant.
- **Bug fixes** where the previous behavior contradicted the normative
  specification. The specification was the promise; the bug was not.

### The security exception

> Early removal is permitted only when keeping the behavior creates a
> material risk of security, privacy, data corruption or unsafe
> operation.

It is narrow on purpose, and it costs evidence. Invoking it requires: a
public issue or security advisory; the documented reason the risk
cannot be mitigated while preserving compatibility; the impact and the
migration for affected integrators; and an explicit entry in the
release notes. An exception without those artifacts is not an
exception — it is a breaking change.

### Where the policy lives

One normative source, per PUBLIC_CONTRACTS' own rule:

- **This ADR** is the policy and its reasons.
- **PUBLIC_CONTRACTS.md** summarizes it in a few lines and links here.
- **Each surface's specification** records its own concrete
  deprecations — announced in, removable from, replacement — without
  reproducing the policy.

## Consequences

- Integrators can answer "can this break me?" from a version number
  alone.
- The project keeps the freedom to refactor internals and to fix its
  own measurement mistakes, because neither was ever promised.
- A 2.0 becomes the deliberate place where accumulated deprecations are
  collected, rather than a surprise.
- Contract versions carry their own weight: a contract can evolve past
  a breaking change without waiting for the product's major.
