# UI Conformance

The backoffice's design system (ADR-0055, rules DS-1…DS-19 in
[DESIGN_RULES.md](DESIGN_RULES.md)) is not a style guide anyone has to
remember. The part of it that can be measured **runs in CI over every
registered screen**, so a screen that drifts fails a check instead of a
review.

This page says exactly which rules are enforced, how they are measured,
and — just as importantly — which are not, and why.

## What runs

| Where | What it does |
| --- | --- |
| `tests/test_ui_conformance.py` | Renders every screen the admin registers (`snapshot_paths()`) plus one page of each editor shape, through the real app, and runs the structural checks in `tests/ui_conformance.py` |
| `scripts/ui_viewport_check.py` | Drives headless Chromium at 320 px over the admin snapshot and asserts the page cannot be scrolled sideways (DS-6) |
| `scripts/a11y_check.py --scheme both` | The existing axe gate — the enforcement arm of DS-14 (both color schemes) and much of DS-15 |

Coverage comes from the screen registry, never a hand-kept list: a new
screen joins the suite the moment it registers.

## Enforced invariants

| Rule | Check | How it is measured |
| --- | --- | --- |
| DS-1 | `one-h1-carrying-only-the-title` | Exactly one `<h1>`; no badge element inside it |
| DS-2 | `breadcrumbs` | A breadcrumb navigation exists on every screen inside the shell (login, reset, setup and two-factor are the declared standalone exceptions) |
| DS-7 | `empty-states-offer-the-next-action` | Every `admin-empty-state` block contains a link or button |
| DS-17 | `at-most-one-open-disclosure` | At most one `<details open>` at load |
| DS-4, #250 | `datatable-order` | Where a summary line exists, a table follows it, and any filter bar for that table precedes it |
| DS-19 | `check_pagination_bounds_large_collections` | With a collection larger than the page size: no more than one page of rows renders, and a full page carries a pagination control |
| DS-8 | `test_screens_do_not_grow_with_the_language_count` | The number of controls reachable **without opening a disclosure** is identical for a small and a large language set — the fixture registers enough extra packs that any per-language growth would show |
| DS-6 | `scripts/ui_viewport_check.py` | The browser scrolls the document right; `window.scrollX` must stay 0 |
| DS-14 | axe gate, `--scheme both` | Every audited screen passes serious/critical checks in both palettes |

Each check is proved to catch its own defect: `test_each_check_catches_its_defect`
feeds a deliberately broken fragment per rule and requires the check to
fail. A check that cannot fail is not a check.

### On measurement

DS-6 exists because of a real mistake worth recording. An early audit
compared `document.scrollWidth` against the viewport and reported
"overflow" on two list screens. It was a false positive: the content was
correctly clipped inside `overflow-x: auto`, and the page never moved.
The suite therefore measures what the user experiences — an attempted
scroll — not a derived width.

DS-8 is measured the same way, for the same reason: controls behind a
closed disclosure exist in the DOM but are not reachable, so the count
that matters excludes them. This is what makes "the screen shows the
same number of fields whatever the language count" a testable
sentence.

The rule is about **N**, not about a number. The fixture uses a large
set because a large set makes growth visible; the size is the
fixture's business, never a threshold anyone should code against. A
project with twelve languages and one with fifty are held to the same
invariant.

## Documented audits (deliberately not automated)

These rules are real and reviewers cite them, but any automatic check
would need a heuristic to guess intent — and a suite full of guesses is
worse than a smaller honest one. They stay audits until a reliable
measurement exists:

| Rule | Why it is not automated (yet) |
| --- | --- |
| DS-3 (one primary action, in the header) | "Primary action" is intent: a screen can legitimately carry a form submit and a header action. Distinguishing them mechanically needs a region contract the templates do not yet declare. |
| DS-5 (scoped search on collections) | Requires knowing which screens *are* collections, and how large they can grow — the registry does not declare that today. |
| DS-9, DS-10 (form and editor anatomy) | Section order is semantic: "summary → main → advanced → danger" is about what the fields mean, not what tag they use. |
| DS-11 (destructive actions confirm or offer undo) | Confirmation may be a form, a flash with undo, or a second step; recognizing all three without false positives is not yet reliable. |
| DS-12, DS-13 (status badges; no config internals) | Partly covered by review and by the axe gate's contrast rules; detecting "a filesystem path in chrome" reliably needs the templates to mark what is configuration. |
| DS-16, DS-18 (master-detail; one dominant work area) | Layout intent. Measurable only with visual heuristics that would flag legitimate designs. |

Promoting an audit to an enforced check is a design-system evolution:
issue first, then the check, exactly like adding a component
(DESIGN_RULES, lifecycle).

## Running it locally

```bash
pytest tests/test_ui_conformance.py                 # structural rules
python -m cms_admin.demo_export \
  --storage examples/multilingual-company-site/content.sqlite3 \
  --out demo-admin/admin \
  --media-dir examples/multilingual-company-site/media \
  --project-dir examples/multilingual-company-site
python scripts/ui_viewport_check.py demo-admin /admin/ /admin/articles/ /admin/menu/
```

The axe gate needs its pinned bundle; the CI job shows the exact
invocation.
