# Design Rules

The rules every theme — the built-in one, the reference theme, and any
third-party theme — must satisfy. They come from a decade of lessons on the
production site this framework was extracted from (docs/POC_PLAN.md records
their origin); the mechanical ones are enforced by the theme conformance
suite (TEST_PLAN.md §1.5), not by review alone.

## 1. Tokens, not values

- All colors, spacing, type scale and breakpoints live in **CSS custom
  properties** (design tokens) in the theme's base stylesheet. Components
  consume tokens; they never hardcode values.
- A project rebrands by overriding the token file (`theme/assets/…`,
  ADR-0007) — never by editing templates.

## 2. The non-negotiables (conformance-tested)

| Rule | Why |
| --- | --- |
| `[hidden]{display:none!important}` is the **first rule** of the base stylesheet | The browser's `[hidden]` rule has zero specificity; any `display:` utility silently defeats it. This killed a privacy notice and a consent-gated form once. |
| **Zero inline styles** | CSP-compatible output; styling stays overridable by token/asset shadowing. |
| **Local assets only** — fonts, scripts, styles ship in the theme; no CDNs | Privacy (no third-party requests), determinism, offline builds. |
| **Images always carry `width` and `height`** | No layout shift; the builder provides dimensions from the media model. |
| **No horizontal scroll at any width** | Checked at 360/820/1280px. |
| `prefers-reduced-motion` honored — effects opt out cleanly | Accessibility; effects are decoration, never information. |
| **Single-source assets** — a behavior/effect lives in exactly one file, referenced everywhere | Copy-pasting a script into two shells once produced three divergent sites. |
| **Flow-relative CSS only** — logical properties (`margin-inline-start`, `padding-inline`, `text-align: start/end`, `inset-inline-*`), never `-left`/`-right` or asymmetric four-value shorthands | Any language pack may declare `rtl` (ADR-0034); a physical property silently breaks every RTL site. The one exception: overriding a vendored bundle's physical property, which must name what upstream names. |

## 3. Layout and type

- Main breakpoint at **820px**; progressive `max-width` steps below it.
- One content measure (`--maxw`) shared by header, main and footer.
- Typography pairs a sans for UI (reference theme: Inter) with a serif for
  editorial voice (Newsreader), subset to latin + latin-ext, `woff2`,
  preloaded, local.

## 4. Semantics and accessibility

- Semantic landmarks (`header/nav/main/footer`), one `h1` per page, skip
  clutter. WCAG **2.2 AA** is the baseline; automated axe checks join CI with
  the reference theme (TEST_PLAN §2).
- Language switcher marks the active language (`aria-current`); every page
  declares `lang`.
- Interactive states (focus, hover) visible; contrast from tokens that pass
  AA in both light and dark schemes.

## 5. Modern web platform, no frameworks

Themes target the **web platform as it is today** — and stay static-first:

- **Progressive enhancement**: every page is complete HTML without
  JavaScript; scripts only enhance (search filtering, effects, menus).
- **Web Components (native custom elements)** are the unit of interactivity —
  small self-registering islands (`<site-search>`, `<site-nav>`) shipped as
  **ES modules** from the theme's assets. No framework runtime, no build
  step, no hydration: the HTML is already there.
- **Modern CSS over JS**: container queries, `:has()`, nesting and custom
  properties before reaching for script; view transitions welcome where they
  degrade gracefully.
- Budget: a theme's total JS stays small (the reference target is under
  20 KB, uncompressed, all-in) — if a feature needs more, it belongs in the
  admin, not the public site.

## 6. What themes never do

- Assemble `<head>` content, feeds or indexes — the builder generates them
  (head contract, JSON-LD, RSS, search index); templates only render what
  they receive.
- Embed editorial text — every user-facing string comes from the content
  model or site config.
- Reference assets by literal URL — always through `asset_urls` (hash-versioned
  by the builder; cache busting is automatic).

## Language scale: disclosure, never unbounded repetition

Language sets are data and unbounded (ADR-0034). Every surface —
lists, forms, editors, switchers — must therefore scale by
*disclosure*: aggregate first, then search, filter or expand into the
language being edited. No screen renders an unbounded run of
per-language controls; content lists keep constant-width aggregate
coverage, and editing surfaces open one language at a time past a
small threshold. A 30-language fixture in the test suite enforces
this for every future screen (#241).

## Backoffice design system (ADR-0055)

Screens are designed by task, not by page: the governing question is
"how does an editor complete the task in seconds". These rules are
objective on purpose — any pull request must be able to answer "is
this screen conformant?" without a design review. The epic's final
phase turns them into a CI conformance suite over every registered
screen.

- **DS-1** Exactly one `<h1>` per screen, containing only the screen
  or entity title. Status badges and metadata render *beside* the h1,
  never inside it.
- **DS-2** Every screen inside the shell carries breadcrumbs
  (`Home / …`). Standalone flows (login, reset, setup) are the only
  exceptions.
- **DS-3** A screen's primary action is one `btn-primary` in the page
  header, aligned with the h1. A form's submit is that form's only
  primary button and sits at the form's end. No screen shows two
  primary buttons for different tasks in the same region.
- **DS-4** List anatomy, always in this order: title → one-line
  description → toolbar (search, filters, bulk actions) → table →
  pagination. The create action lives in the header (DS-3).
- **DS-5** Every collection that can exceed one screen has a search or
  filter scoped to itself — the navbar's global search never counts.
- **DS-6** Wide content scrolls inside its own container; at 320 px
  the page never scrolls horizontally.
- **DS-7** Empty states say what the emptiness means *and* offer the
  next action (a link or button). A bare sentence is non-conforming.
- **DS-8** Nothing repeats per language (see the section above): one
  source control plus a translations disclosure or aggregate; the
  number of visible controls is constant regardless of the language
  count.
- **DS-9** Form anatomy: summary/context → main fields → advanced
  (disclosed, holding technical identifiers) → danger zone last.
- **DS-10** Editors share one header: back link → h1 with status
  beside it → action bar. Long editors (more than four cards) expose
  internal navigation.
- **DS-11** Destructive actions use outline-danger styling, live in
  the danger zone or row menus, and always confirm or offer undo.
- **DS-12** Status is a `StatusBadge`: fixed palette, text plus
  `title`, never color alone.
- **DS-13** Raw configuration internals — filesystem paths,
  connection strings, environment values — never render in page
  chrome.
- **DS-14** Every screen renders correctly in both color schemes (the
  axe gate runs both).
- **DS-15** Every interactive control is reachable and operable by
  keyboard; the skip link always works.
- **DS-16** Screens scale by *selection*, never by rendering every
  editable item at once: a collection's editor is master-detail — one
  detail editor exists regardless of whether the collection holds 5
  items or 500.
- **DS-17** Forms scale by *depth*: at most one disclosed section is
  open by default (basic visible, translations/advanced/SEO closed);
  never four sections expanded on load.
- **DS-18** Every screen has one clearly dominant work area. Title and
  primary action orient it (DS-1, DS-3); no secondary panel competes
  visually with the task — an empty panel given half the screen is the
  canonical violation.

These rules are executable on purpose: DS-8 compares the visible
control count between the 2-language and 30-language fixtures; DS-16
compares it between small and large collections; DS-17 counts open
disclosures at load. A screen fails the suite, not a design review.

Screens compose the component vocabulary (PageHeader, ActionBar,
DataTable, FilterBar, EmptyState, FormSection, DangerZone,
SidebarSection, StatusBadge, Disclosure — ADR-0055) instead of
open-coding these patterns; a covered pattern outside the vocabulary
is itself a non-conformance.

**The golden screen.** The menu screen is the design system's
reference implementation: it concentrates every pattern at once —
list, form, languages, reordering, empty state, responsiveness — so
phase 2 rebuilds it first, and a change to the system is judged by
whether the menu screen still conforms. When the golden screen
conforms, most screens align by construction.

**The interaction budget.** Beyond the testable rules, every screen
carries a budget — the UX counterpart of a performance budget: at
most **one** primary action, **one** active editor, **one** open
disclosure (DS-17), **one** decision per step (select, *then* edit —
never both at once), and **zero** growth of visible elements with
data size (DS-8, DS-16). Not every line is machine-checkable; the
budget's job is to reframe review. The question for any panel PR is
"does this increase the screen's interaction budget?" — and a yes
requires the author to justify it in the PR, the same way a
performance regression would.

### The component inventory (v1 — closed)

Screens build from this list and nothing else. A component outside it
does not enter through a pull request; it enters through an ADR or a
design-system evolution issue.

| Component | Status in v1 |
| --- | --- |
| PageLayout, Sidebar, Breadcrumbs, SearchBox (global) | provided by the shell (`shell.html.j2` / `base` chrome) — screens never rebuild them |
| PageHeader | `page_header` macro (`_components.html.j2`) |
| EmptyState | `empty_state` macro |
| Disclosure | `disclosure` macro (native `details`, closed by default) |
| ActionBar, DataTable, FilterBar, FormSection, DangerZone, StatusBadge | defined by v1, extracted as macros as each screen adopts the system (the patterns exist today as open-coded Bootstrap; extraction changes markup, never behavior) |
| Modal, Drawer, Toast | **reserved** — they imply client-side behavior in a JS-minimal panel; introducing any of them requires its own ADR |

### Page anatomies (v1)

Exactly six anatomies are supported; every screen declares one, and
"which anatomy is this screen?" never has two answers:

| Anatomy | Shape | Screens |
| --- | --- | --- |
| List | title → description → toolbar (search, filters, bulk) → table → pagination | articles, pages, media, translations, trash, activity, submissions, users, calendar |
| Master-detail | list column (add, scoped search, ordering) → detail editor on selection | **menu** (the golden screen) |
| Form | back link → header (status beside title) → main fields → disclosed advanced → danger zone | article/page/section editors and their translations, media detail, new-entry forms |
| Dashboard | stat tiles → attention queue → report cards | dashboard |
| Settings | card grid or card list with per-card actions | themes, extensions, extension settings, migration, publishing |
| Standalone | single centered card, no shell | login, reset, setup, two-factor |

### Tokens

The panel's tokens are AdminLTE/Bootstrap's own custom properties —
spacing scale, radii, typography, color modes, input heights.
`admin.css` only adds accessibility fixes, no-JS fallbacks and the
font faces; it never restyles the theme and never introduces new
hardcoded values. A design-system component consumes Bootstrap
utilities and variables exclusively — the same "tokens, not values"
rule themes live under (§1).

### Lifecycle — v1 is frozen

This section, the rule set (DS-1…DS-18), the component inventory and
the anatomies together are **Design System v1**, frozen as of
ADR-0055. From here, any change — a new component, a new anatomy, a
rule change, a variant of an existing pattern — happens through an
ADR or a design-system evolution issue, never inside a feature PR.
Contributors build against a stable specification, exactly as they do
against theme and translation-provider conformance; review cites DS
numbers, not taste.
