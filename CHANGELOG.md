# Changelog

Per-version changes in Added / Changed / Fixed / Removed form. The
project follows semantic versioning from `0.1.0`; the six packages
release in lockstep under one `vX.Y.Z` tag. Narrative release notes —
features with their PRs, breaking changes and migrations — live in
[RELEASE_NOTES.md](RELEASE_NOTES.md).

## Unreleased

### Changed

- The dashboard answers "is anything wrong?" instead of listing
  everything that is: the advisory findings become a bounded tally per
  rule with a link to the publishing screen, which owns the filters and
  the pagination for them. The seeded project's dashboard goes from
  6169 px to 1845 px — it had been roughly five thousand pixels of
  wrapped advisory rows in a narrow column, on the first screen anyone
  sees.
- The status tiles no longer read as if pages did not exist. The counts
  always covered articles and pages alike, but every tile's footer said
  "Articles" and linked only there; each now links to both. The totals
  line becomes three of the theme's own info-boxes, one per kind,
  linking to its list.
- An editor's auxiliary panels (editorial notes, revisions, external
  preview links) arrive **collapsed**, with a one-line summary of what
  they hold — "3 notes", "none yet". Four cards of emptiness had been
  taking about five hundred pixels in the middle of the work area. They
  use the vendored theme's own collapsible card (`card-tools` with
  `data-lte-toggle="card-collapse"`) rather than a hand-rolled
  disclosure.

### Fixed

- The project file the first-run wizard writes is parseable on Windows.
  Values were embedded unescaped, so a Windows storage path — with its
  backslashes, which TOML reads as escape sequences — produced a
  `sardine.toml` that could no longer be read; a site name containing a
  quotation mark broke it on every platform. Both writers now share one
  escaping helper.
- Deployment activation works on Windows. Activating a release renames
  the pointer over `current`, which Windows refuses when the name
  already exists (`WinError 5`); the old pointer is now removed first
  there, inside the deployment lock, leaving the release directories
  untouched.
- Importing a portable export no longer loses the Markdown tree on
  Windows. The importer keyed the files with the operating system's
  separator while the format — and every consumer — uses a forward
  slash, so on Windows no key matched: translations came from
  `content.json` alone and their states were wrong after a round trip.
- Text artifacts are byte-identical on every platform. The portable
  export, `release.json`, the seeded media and every project-file write
  used the platform's native line endings, so on Windows the same
  content produced different bytes — which contradicts the deterministic
  build promise and broke the portable round trip. All of them now pin
  `\n`.
- A configured **absolute** SQLite path is honoured as written. The
  project loader stripped every leading slash before deciding whether a
  path was absolute, so `sqlite:////var/lib/site/content.db` resolved
  *inside* the project directory and the database was silently created
  somewhere else. The URL form is now parsed by the same function the
  storage backend uses; relative paths still resolve against the project
  directory and `:memory:` passes through.

### Added

- A **starter theme** (`examples/starter-theme/`): a deliberately
  minimal theme — five templates, one stylesheet, no JavaScript — that
  passes the theme conformance suite in full, so it is a starting point
  rather than a sketch. It carries no branch on a section kind: one
  generic renderer covers fields, repeatable rows and images for every
  kind, including kinds an extension invents, which is what the section
  contract promises. Certified in CI beside the bundled themes, with a
  test that keeps it small.

- Onboarding-flow check (`scripts/onboarding_flow_check.py`) in CI
  (#128): the browser path from an **empty database** — no project
  file, no account — through the first-run wizard to a site built and
  exported from the panel, driven with headless Chromium against the
  real app. It also asserts what a fixed-database test cannot: an
  unconfigured instance routes everything to the wizard, the wizard is
  safe to abandon and resume without keeping partial state, and a
  configured instance never exposes it again. Mechanical proof that no
  step of the path is blocked; the "under ten minutes" metric still
  requires a real tester.

- The UI conformance suite (#244, ADR-0055): the backoffice design
  system becomes an executable contract. Every screen the admin
  registers is rendered and checked in CI — one `h1` carrying only the
  title, breadcrumbs, empty states that offer the next action, at most
  one open disclosure, the DataTable order, pagination bounding large
  collections, and the language-scale invariant (the controls reachable
  without opening a disclosure are the same with 2 languages and with
  30). A viewport gate drives Chromium at 320 px and asserts the page
  cannot be scrolled sideways — measured as an attempted scroll, not a
  derived width. Each check is proved to catch its own defect, and
  UI_CONFORMANCE.md records which rules stay documented audits rather
  than becoming fragile heuristics.

### Changed

- The publishing screen is rebuilt task-first (#244, #250, ADR-0055):
  summary before anything else (site identity — without the raw output
  path —, the gate verdict and the bounded rules table), then
  **Findings** as a real data table — severity/rule filters, scoped
  search, a summary line and pagination instead of one flat unbounded
  list — and the run area (deployment state, target choice, last run)
  last. Understanding the publication state no longer requires
  scrolling past hundreds of advisory rows.

- The settings screens adopt the design system (#244, ADR-0055):
  themes, extensions and migration take the shared page header;
  extension settings becomes an editor (back link, the extension's
  name as the title) built on the new `form_section` component; and
  the themes grid stays symmetric — a theme without a bundled
  screenshot shows a neutral placeholder in the same slot instead of
  collapsing the card.

- The editors adopt the design system (#244, ADR-0055): every editor
  header becomes back link → an `h1` carrying only the identity → the
  status badge beside it (articles, pages, sections, media and the
  three translation editors); the operations merge into one action
  bar; long editors (article, page) gain "On this page" internal
  navigation; and Move to trash leaves the header area for a bordered
  **Danger zone** that closes the page — destructive actions live
  there and nowhere else.

- The content lists (articles, pages, media) adopt the design system
  (#244, ADR-0055): one anatomy — header with the create action,
  toolbar with scoped search and filters, bulk actions, a summary line
  ("Showing 1–25 of 30"), the table, pagination (DS-19: a collection
  larger than 25 never renders in full; paging keeps the active
  filters). Articles and pages gain scoped search; empty states carry
  the next action. The media table's select/preview columns are
  realigned with their headers.

- The Menu screen is rebuilt as the design system's golden screen
  (#244, ADR-0055): open it and you see the navigation — master-detail
  with list-order reordering and scoped search — instead of a form.
  The editor appears on selection or Add; translations and technical
  fields (id, position) live behind closed disclosures, so the screen
  shows the same number of fields with 2 or 30 languages; the id is
  optional and derives from the label; the empty state explains the
  automatic menu and carries the add action. A first component
  vocabulary (`page_header`, `empty_state`, `disclosure`) is born on
  this screen and will spread from it.

### Added

- Translation providers (#228): a `TranslationProvider` contract in
  `cms_core.translations` following the established provider pattern
  (ADR-0054), contributed by @MasRama — contract, registry and both
  faces. Providers produce suggestions that land as draft content
  in the existing state machine; nothing is published by the provider.
  `cms translate --language <tag> --missing` batch-suggests from the
  CLI; a Suggest-translation action joins the side-by-side article
  translation editor. Both faces are invisible without `[translations]
  provider` configured. Declared capabilities, structured
  `ProviderError`, secrets via environment only, audit records without
  prompts or tokens.
- Translation-provider conformance as a public contract (#228): being
  a Sardine translation provider is now an executable specification —
  `cms_core.translation_conformance` ships versioned named checks
  (batch order, placeholder and Markdown preservation, empty-source
  and empty-target semantics, declared-language honesty, structured
  failure, glossary); third-party providers certify in a four-line
  parametrized test. `TranslationFailed` becomes the classified
  failure channel carrying `ProviderError`, and
  `[translations.glossary.<target>]` supplies required target terms to
  providers declaring `supports_glossary` — on both faces. New
  developer guide: WRITING_A_TRANSLATION_PROVIDER.md.

## 0.8.0 — 2026-07-23

Being a Sardine theme is now an executable specification: themes
become verifiable contracts, extensions gain operational tooling, and
Astro joins as a first-class deployment target.

### Added

- Theme conformance as a public contract (#141): the suite moves to
  `cms_build.theme_conformance` — versioned, self-contained, fifteen
  named checks any theme package imports and runs against itself. Both
  bundled themes are certified by the full contract in CI, and "passes
  the conformance suite" becomes the objective acceptance rule for
  community themes (ADR-0053).

- Extension settings (#141): extensions declare a versioned settings
  schema — plain data, defaults included — and the panel renders it
  with explicit provenance per value; validation precedes persistence,
  values persist per project, optional migrations bridge schema
  versions, and resolved settings reach the extension at load time.
  Secret fields name an environment variable: the panel shows presence
  or absence only. `cms doctor` reports settings validity and each
  required variable (ADR-0052).

- Extension health (#141): extensions may declare a health check —
  their own answer to "is my integration alive". Results surface on
  demand on the extension's card and in `cms doctor`, one line per
  check; a raising check is a contained failed check, and health never
  gates builds, publishing or activation (ADR-0051).

- Astro deployment target ([#191](https://github.com/ph7x-Systems/sardine-cms/issues/191)): `cms export --target astro` emits an Astro project scaffold alongside the static site — `astro.config.mjs`, content collection schemas (`src/content/config.ts`), `package.json` and `tsconfig.json` — that consumes Sardine's Content API JSON. Teams already deploying Astro get a type-safe starting point with zero core changes; the target registers like the others and the panel picks it up automatically.

## 0.7.0 — 2026-07-23

Theme and extension management, phase 1 (#141): choosing and
activating themes and extensions no longer means editing files.
Extension health and settings surfaces, the official theme set and the
theme conformance suite follow in the next phase.

### Added

- Extensions screen (#141): activate and deactivate without editing
  files — discovery from packaging metadata with nothing imported for
  the listing, compatibility from the declared core range,
  transactional activation (isolated load, trial build, only then the
  config write), capabilities shown from the loaded object only, and
  containment: a broken active extension shows its error instead of
  taking the panel down, and deactivation rewrites configuration
  without importing it. Any extension load failure is now a typed
  ExtensionError, so tolerant call sites contain module-level crashes
  too (ADR-0050).

- Theme cards from the manifest (#141): the Themes screen renders
  description, author, license, website, screenshot and a
  compatibility verdict entirely from each package's own metadata —
  no theme code runs for the listing, and the compatibility shown is
  the same version range the installer enforces. The reference theme
  ships its screenshot (ADR-0049).

- Themes screen (#141): the panel lists every theme the environment
  can activate — bundled and installed packages with their versions,
  discovered through the entry-point group without loading code — and
  activates one without editing files. Activation tries a full build
  first; a failing theme shows its error and the configuration stays
  untouched. The panel never installs packages (ADR-0048).

## 0.6.0 — 2026-07-23

The migration release: the WXR flow (#140) is complete end to end,
from the CLI to the panel, on one shared pipeline.

### Added

- WXR migration flow, final part (#140): the Migration screen brings
  the whole flow to the panel — upload with the inspection report
  rendered before anything is written, mapping forms, optional
  source-wins updates and media download with per-URL outcomes, and
  automatic redirects; the panel and the CLI call the same shared
  pipeline (`cms_core.migration`, `cms_build.redirects`), so behavior
  parity is structural. Admin-only, audited, localized in all six
  panel languages (ADR-0047).

- WXR migration flow, fourth part (#140): imported posts keep their
  source URLs alive — each post's original permalink path is recorded
  in the project's `[redirects]` table when it differs from the new
  address, deterministically, without chains or collisions, and
  idempotently across re-runs; an upstream rename with `--update`
  flattens every old address to the newest one (ADR-0046).

- WXR migration flow, third part (#140): `--fetch-media` downloads the
  images imported posts reference into the media library and rewrites
  bodies to `/media/…` paths — explicit opt-in, public hosts only,
  size/time caps with three attempts, duplicate bytes reuse the
  existing asset, and every URL is reported as fetched, reused or
  failed with its reason (ADR-0045).

- Indonesian language pack (`id`): site labels, month names, date
  pattern and a full admin catalog so the panel itself speaks Bahasa
  Indonesia. Seventh bundled language; contributed by @MasRama (#216).

## 0.5.0 — 2026-07-22

The WXR migration flow (#140) ships partially in this release: the
inspection report, idempotent re-imports and mappings are in; media
fetch, redirects for changed URLs and the admin migration flow remain
pending.

### Added

- WXR migration flow, first part (#140): `cms import --format wxr
  --dry-run` reports what an export contains before anything is written
  — importable posts, author/category/tag inventories, referenced
  media, comment count, a note per left-behind item with its reason and
  an explicit fidelity percentage; nothing is silently dropped. Imports
  are idempotent by source id: re-running with a newer export never
  duplicates a post (even after an upstream slug change), leaves
  already-migrated posts untouched by default and overwrites them only
  with `--update`, keeping the entity id (ADR-0043).

- WXR migration flow, second part (#140): authors, categories and tags
  map at import — `--map-author`, `--map-category` and `--map-tag`
  take repeatable `"source=target"` renames, an empty target drops the
  value, unmatched sources warn and proceed, and `--dry-run` previews
  the post-mapping inventories (ADR-0044).

- **Docker quickstart** ([#192](https://github.com/ph7x-Systems/sardine-cms/issues/192)): `docker compose up` brings up the admin panel with a seeded example site — no Python environment needed. A random admin password is generated on first run and printed in the container log. Site content and the SQLite database persist in named volumes.
- Italian language pack (`it`): site labels, month names and date
  pattern, following the LANGUAGE_PACK_GUIDE format. Includes the admin
  catalog so the panel itself speaks Italian (#203, contributed by
  @MasRama; admin catalog follow-up).

### Changed

- Contributor flow: the contributing guide covers the first-PR path
  (repository language, changelog placement, the first-contribution CI
  approval wait, how to branch), the README links it, and changelog
  entries credit external contributors.

- CI enforces commit message hygiene: a required check rejects
  attribution trailers in branch commits.

### Fixed

- Fork pull requests run the full backend conformance job: the MSSQL
  service container starts with a fallback throwaway password when
  repository secrets are absent, so external contributions no longer
  fail a required check they cannot influence.

## 0.4.0 — 2026-07-22

### Added

- `cms demo`: from nothing to a browsable five-language site in one
  command — scaffold, seed, build and serve, with printed next steps;
  the directory persists for exploring afterwards.

- `cms init --theme`: choose the theme when the project is created.
  Installing a theme package no longer requires hand-editing
  `sardine.toml` before the first build.

### Fixed

- The README taught `cms demo`, which no release contained: a clean
  `pip install` failed on the very first instruction. Its quickstart is
  now one uninterrupted sequence, guarded by tests that check every
  documented command exists and that the flow selects a theme.

- `ADMIN_GUIDE` showed a dump/restore pair whose restore failed on any
  project that already had content, which is every project being
  restored. It now passes `--replace`.

## 0.3.0 — 2026-07-22

### Added

- External preview links: signed (HMAC, per-instance stored key),
  always expiring, revocable from the entry's editor card,
  unauthenticated but minimal in scope — one entry through the real
  theme with a localized draft banner; publication state untouched;
  creation and revocation audited (migration 26).

- Advisory SEO hints in the validation report (title/description
  length; warnings only, `[validation] disabled` opts out — the new
  per-project rule switch) and automatic redirects when a published
  entry's slug changes: per language, chains flattened, loops
  impossible, stale redirects dropped when an address returns to life;
  every recorded redirect audited (#138).

- Package metadata declares the project URLs (homepage, repository,
  wiki, changelog) — published releases show them as verified links.

- SEO editor card: a collapsed Search-and-social card on article and
  page editors (title, description, noindex, canonical, social image)
  with a static preview; per language, localized (#138).

- Per-entry SEO overrides: articles and pages carry an optional `seo`
  payload per language (title, description, `noindex`, canonical
  override, social-card image from the media library) that flows
  through the single head derivation — each tag emitted exactly once;
  empty values keep today's derived output. Content API surfaces the
  payload additively (migration 25).

- Forms provider contract: `[forms] provider` selects who handles
  accepted submissions; extensions register destinations via
  `Extension.forms_providers` (contract version validated at
  selection, failures contained and audited, never visitor-facing);
  the reference behaviour is the default and a conformance suite
  covers any provider (ADR-0040).

- Optional form-submission storage: `[forms] store` persists accepted
  submissions (decoupled from notification — either leg failing never
  affects the other or the visitor), with an admin-only Submissions
  screen (filter by form and date, definitive delete) and
  `retention_days` pruning at startup (#137; migration 24).

- Official forms endpoint (`POST /forms/submit` on the panel):
  server-side validation against the declared inputs, layered spam
  protection (honeypot, elapsed-time, per-address rate limiting,
  origin allowlist), deterministic status codes, localized accessible
  responses, and contained mail notification via `[forms] notify`;
  the example site ships a working contact form (#137).

- Form section kind: both bundled themes render visitor forms declared
  as section items (text, email, textarea, checkbox), with accessible
  labels, a honeypot, an enhancement-filled elapsed-time field and an
  optional required consent checkbox; the form renders only when
  `[forms] endpoint` is configured (#137).

- In-editor media picker: covers and section media are chosen from a
  visual library grid (thumbnails, dimensions, undersized-image flag)
  with no script required; the ID inputs remain the precise path
  (#136).

- Media replace-file flow: swap the file behind an asset while the ID
  and every reference stay valid; alt texts, collection and focal
  carry over, an out-of-bounds crop is cleared, and duplicate bytes
  are refused naming their owner (#136).

- Modern image formats by default: every raster image ships WebP/AVIF
  variants (of the base size and of each configured responsive width)
  whenever the environment can encode them; both bundled themes render
  them as picture sources and the Content API lists them in a new
  additive `sources` field. `[build] modern_image_formats = false`
  turns it off (#136).

- Media crop and focal point: an optional crop stored as data and
  applied at build — the published image, its dimensions and every
  derivative descend from the cropped area while the original stays
  untouched — and a focal point carried in image metadata (themes and
  the Content API) (#136; migration 23).

- Media collections, usage counts and duplicate prevention: assets
  carry an optional collection (filterable in the library) and the
  SHA-256 of their bytes — identical uploads are refused naming the
  existing asset; the list shows how many entries use each asset
  (#136; migration 22).

- Deployment provider framework: a versioned `DeployProvider` contract
  with a registry (`register_deploy_provider`), per-provider settings
  from the raw `[deploy]` table, capability declaration the panel
  adapts to, selection-time validation, a conformance suite any
  provider can run, and extension registration
  (`Extension.deploy_providers`) — a third destination needs zero core
  changes (#156).

- Azure Static Web Apps deployment provider behind the same contract:
  authenticated upload of immutable releases, deployment tracking with
  transient panel phases, health verification, rollback by re-sending
  a kept release — with the token read from the environment at deploy
  time and never stored, logged, audited or echoed (#156).

- Automated deployment, filesystem/Nginx reference provider: publish
  and unpublish end on the public site through immutable releases,
  atomic symlink activation, health checks with automatic rollback,
  panel-side manual rollback without rebuild, concurrency locking, a
  scheduled-window watcher and full audit-trail coverage (#156).

- Needs-attention dashboard: review queue, pending translations,
  scheduled changes within 7 days and stale drafts — each card linking
  to its work, with a real all-clear state (#135).

- Audit trail: append-only activity records for sign-ins, transitions,
  trash/purge, media, user/role/2FA changes and builds, with an
  admin-only Activity screen and startup retention pruning (#134;
  migration 21).

- Configurable source language (`[site] source_language`, ADR-0034).
- Language packs carry everything: site labels, dates, admin catalogs,
  `native_name`; data-only packs; authoring guide and `sardine-lang-<tag>`
  naming; CI drives an RTL build through the accessibility gate.
- Repeating `items` in sections, kind-declared Markdown fields and
  long-form page bodies (`body_markdown`) — model, storage, both
  themes, editors, portable format (ADR-0037; migrations 18–19).
- Page editor UX: block gallery with auto-derived keys, duplicate,
  hide/show, delete with undo, drag reorder (#127).
- Browser onboarding: first-run setup wizard and guided deployment
  choice with persisted target and go-live feedback (#128).
- Global admin search over articles, pages, sections and media in
  every language (#129, ADR-0038).
- Bulk actions with per-entry rules and outcome report (#130).
- Translation queue and "missing «tag»" list filters (#131).
- Editorial calendar with drag-to-reschedule (#132).
- Scheduled unpublish: `unpublish_at` publication windows (#133;
  migration 20).
- Editorial-flow check (`scripts/editor_flow_check.py`) in CI.
- Operational model documentation (DEPLOYMENT.md, #152).
- Internal dependency bounds (`>=0.2.0,<0.3`) and OIDC-first/token-
  fallback publishing.

### Changed

- The admin sidebar, section labels and demo-snapshot capture list all
  derive from one navigation registry — each screen registers once in
  its module (key, path, label, icon, order, minimum role, optional
  group), and extensions can register screens through the same call
  (#177).

- Deployment documentation split by audience: a short Deployment Guide
  for operators (operating models, configuration reference, complete
  examples, one consolidated troubleshooting table), a Deployment
  Providers overview, and a Writing a Deployment Provider developer
  guide (contract, registration, example, conformance rules, store
  layout). Public pages no longer reference issues or decision
  records.

- The Content API documentation is written for the API consumer:
  endpoints, response contract, guarantees and a short example;
  verification detail moved to the test plan (#165).

- Flow-relative CSS only in themes and panel (RTL end to end),
  conformance-enforced.
- Media alt text requires *some* language, not a hardcoded one.
- Content lists show constant-width translation coverage, never a
  column per language.
- The roadmap became a product plan with an issue-tracked queue and an
  explicit definition of done; documentation split by concern (#155).
- The comments capability is recorded as partial (contract without an
  official provider).

### Fixed

- The builder no longer skips pages of a non-default source language.
- The publishing flow's editor check types through the Markdown
  widget's real surface (silent-loss case caught by the in-repo check).

## 0.2.0 — 2026-07-21

Editorial completeness (M5), extensibility and adoption (M6) and
operations (M7) in one release — see
[RELEASE_NOTES.md](RELEASE_NOTES.md) for the full account.

### Added

- Scheduling, revisions with restore, trash, duplicates, previews with
  autosave and live refresh, quick actions, featured, authorship,
  editorial notes, users screen (M5).
- Extension contract (ADR-0028), menu manager, image derivatives,
  redirects, portable round-trip, external blog import, section-kind
  gallery, comments contract (ADR-0031), versioned JSON content API
  (M6).
- Pluggable email with enumeration-safe password reset and editorial
  notifications (ADR-0032), TOTP two-factor with per-role enforcement
  (ADR-0035), signed on-publish webhooks (ADR-0036), `cms doctor`
  (M7).
- Admin panel localization (ADR-0022); storage migrations up to 17.

## 0.1.x — 2026-07

First public releases: content core with checksum translation states,
four storage engines behind one conformance-tested contract,
validation engine, deterministic builder with SEO head contract,
themes with overrides, deployment targets, the `cms` CLI and the full
browser admin (WCAG 2.2 AA gated in CI).
