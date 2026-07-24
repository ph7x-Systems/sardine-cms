# ADR-0055 — Backoffice design system: the interface as an executable contract

- **Status:** accepted
- **Date:** 2026-07-24

## Context

The panel grew feature by feature while the architecture matured; each
screen invented parts of its own UI. A structural audit of every
registered screen (26 route shapes, 144 rendered snapshot pages,
desktop and 320 px) found the drift is not aesthetic but structural:

- The **primary action's position varies by screen**: 13 screens put it
  inside a card body, 3 in the page header, 2 inside a table container.
- **No list owns a search control** — the only search input on most
  screens is the navbar's global one; collections rely on filter
  selects alone.
- Some **`<h1>` elements mix the title with status badges and
  metadata** (entity editors), so the accessible name of the page is
  "about published".
- The **menu screen** is the canonical non-conforming example: a 50/50
  two-column layout whose list column renders a single sentence, a
  form-first hierarchy for a manage-first task, one visible label field
  per configured language (7 today; unusable at 30), no scoped search,
  and an empty state with no next action.
- **Editors are single long columns** (the page editor stacks 7 cards
  and 37 forms) with the save button mid-page and no internal
  navigation.
- At **320 px** the article and page lists overflow the viewport
  horizontally (261 px and 272 px) instead of scrolling inside their
  table container.
- The **publishing screen prints raw configuration internals** (the
  absolute output path) in its header line, and lists every advisory
  issue in one flat unpaginated table.
- What is *right* is equally consistent: 26/26 screens have exactly one
  `<h1>`, 25/26 carry breadcrumbs and the content-header block, and the
  articles list already has the target anatomy (header action → filter
  toolbar → table → bulk bar).

The project treats themes (ADR-0053) and providers (ADR-0054) as
versioned contracts with executable conformance. This ADR applies the
same discipline to the panel's own interface.

## Decision

**Screens are designed by task, not by page.** The governing question
for any screen is "how does an editor complete the task in seconds",
not "what does the page contain". Concretely, the panel adopts:

### One component vocabulary

Screens stop inventing UI. A macro library (phase 2) defines each
pattern once — spacing, typography, responsiveness and accessibility
included: **PageHeader** (h1 + status beside it + primary action +
breadcrumbs), **ActionBar** (an editor's operations row), **DataTable**
(responsive table with scoped search, sortable columns where useful,
consistent row actions), **FilterBar**, **EmptyState** (meaning + next
action), **FormSection** (summary → fields → advanced disclosure),
**DangerZone**, **SidebarSection**, **StatusBadge** (fixed palette,
text never color alone), **Disclosure** (the #242 pattern for anything
that scales with language count).

### Two page anatomies

- **Every list screen:** title → one-line description → toolbar
  (scoped search, filters, bulk actions) → table → pagination. The
  create action lives in the page header, nowhere else.
- **Every form/editor screen:** back link → PageHeader (title, status
  beside the h1, action bar) → summary/context → main fields →
  advanced (disclosed) → danger zone last. Technical identifiers live
  under advanced. Long editors expose internal navigation.

### Objective rules

DESIGN_RULES.md gains a numbered rule set (DS-1…DS-18) precise enough
that any pull request can answer "is this screen conformant?" without
a design review. The rules are the contract; the audit inventory on
the epic issue is the evidence they were derived from.

### Conformance, executable

The epic's final phase turns the rules into a UI conformance suite run
in CI over every registered screen (the demo-snapshot walker and the
axe harness are the rails): exactly one `<h1>` containing only the
title, breadcrumbs where applicable, primary-action placement,
scoped search on collections, consistent empty states and pagination,
keyboard operability, no horizontal overflow at 320 px, correct
rendering in both color schemes, and no degradation with the
30-language fixture. The interface becomes an executable contract.

### No behavior changes in structural phases

Phases 1–3 change structure and consistency only; the existing E2E
suites must stay green **unchanged**. Behavioral polish (motion,
skeletons, shortcuts) is explicitly phase 4.

## Consequences

- #241 (the panel at 30+ languages) is absorbed: language scaling is
  one rule (DS-8) and one conformance invariant, not a separate
  effort.
- New screens start conformant by construction: composing the
  vocabulary is less work than inventing UI.
- Drift becomes a CI failure instead of a review opinion — the same
  shift ADR-0053 made for themes.
- The audit's per-screen findings live on the epic issue (#244) as the
  phase-2 work list.
