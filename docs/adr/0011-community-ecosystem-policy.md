# ADR-0011 — Community ecosystem: free licenses, naming grant, listed by conformance

- **Status:** accepted
- **Date:** 2026-07-17

## Context

The framework's extension seams are code (`register_theme`, `register_target`,
`register_backend`, validation rules), but sharing needs rules before the
first third-party package exists: what license community packages must carry,
how they may use the Stillsite name (the trademark is excluded from the
Apache-2.0 grant, Section 6), and how users discover trustworthy packages.
Deciding this after an ecosystem forms is how projects end up with license
chaos and name squatting.

## Decision

1. **Free licenses only, verified at listing.** The framework stays
   **Apache-2.0** (ADR-0002 reaffirmed; the fair-code route was analyzed and
   rejected for the core — it would forbid the primary audience, agencies
   building client sites commercially). Community packages may choose any
   **OSI-approved free license** (MIT or Apache-2.0 recommended); a free
   license is a hard requirement for being listed in the official registry.
2. **Naming grant (nominative use).** Package names following the patterns
   `stillsite-theme-<name>`, `stillsite-target-<name>`,
   `stillsite-backend-<engine>` and `stillsite-plugin-<name>` are expressly
   permitted — this is a limited trademark grant for identification only.
   Not permitted: claiming official status, using the logos, or naming a
   package in a way that implies pH7x Systems authorship. Official packages
   live under the `ph7x-Systems` GitHub org; everything else is community.
3. **Listed by conformance, not by opinion.** The registry is a table in
   [ECOSYSTEM.md](../ECOSYSTEM.md), amended by pull request. Listing
   requirements are objective: free license, the relevant conformance suite
   passing in the package's own CI (storage suite for backends, theme
   checklist for themes, output-integrity for targets), and a README with a
   quickstart. Delisting happens the same way (PR with the failing evidence).
4. **Discovery**: GitHub topics (`stillsite`, `stillsite-theme`, …) plus the
   registry. No separate infrastructure until scale demands it — the
   registry is versioned, reviewed and anti-drift-checkable like everything
   else in the repo.

## Consequences

- A contributor can build, license and announce a package without asking
  permission — the policy is self-service.
- Users get one vetted list where "listed" means "conformant and free", not
  "endorsed".
- The trademark stays protected while the name remains usable where it must
  be: in package identifiers.
- The plugin-mechanism ADR (entry points vs. explicit registry) remains a
  separate, future decision; this policy already covers whatever mechanism
  lands.
