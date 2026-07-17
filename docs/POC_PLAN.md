# PoC Plan — Reproduce the ph7x.com architecture end-to-end

The proof of concept for the whole framework is: **rebuild the architecture of
the live ph7x.com site with the framework** — same URL tree, same head
contract, same design system — driven by the content model, the validator and
the deterministic builder. The original lives at `~/dev/Ph7x.Site.Corporate`
(its `swa/` output is the reference) and is **strictly read-only**: we copy
patterns, never files, and the example content stays fictional (the real
site's business identity, contacts and JSON-LD data are never imported).

## 1. Idea inventory (extracted from the live site's output)

### 1.1 Site & URL structure

- EN at the root; other languages under `/pt /es /fr /de`; `x-default` = root.
- **Localized slugs everywhere**: `/contact/` ↔ `/pt/contacto/` ↔
  `/de/kontakt/`; every blog article has a per-language slug
  (`three-decisions-before-moving-to-azure` ↔
  `tres-decisoes-antes-de-ir-para-o-azure`).
- One-page home with anchored sections (`#about #expertise #work #certs`) +
  standalone contact page.
- Blog per language: listing, pagination (`/blog/page/2/`), categories
  (`/blog/category/<slug>/`), RSS (`/blog/rss.xml`) and a client-side search
  index (`/blog/search-index.json`).
- Legal pages as flat files (`privacy.html`, `terms.html`, `cookies.html`),
  per language.
- `404.html`, `robots.txt`, one `sitemap.xml` covering all languages.

### 1.2 Head contract (every page)

- `title` + `meta description`; robots `index, follow, max-image-preview:large`.
- Full Open Graph set: `og:type` (website/article), `site_name`, `url`,
  `image` (1200×630 with explicit dimensions), `og:locale` + one
  `og:locale:alternate` per language; Twitter `summary_large_image`.
- Complete hreflang cluster (all languages + `x-default`) and `canonical` on
  every page — including deep blog pages, each pointing at its localized
  siblings.
- JSON-LD: organization node with a stable `@id` (`…#organization`) on the
  home page (ProfessionalService pattern: founder, knowsAbout, serviceType,
  areaServed, availableLanguage); `og:type=article` +
  `article:published_time` on posts.
- Favicon + `preload` of the critical fonts (`crossorigin`).

### 1.3 Assets & design system

- **CSS split per shell**: a tiny shared `site.css` plus `home.css`,
  `blog.css`, `legal.css` — pages load only what they use.
- **Cache-busting by content hash**: `home.css?v=c430b85a` — hashes change
  only when content changes (pairs with deterministic builds).
- Design tokens (CSS custom properties): `--bg --ink --muted --head --accent
  --navy --green --panel --line --line-2 --faint --maxw --sans --serif --fxh`.
- Fonts local only: Inter (sans) + Newsreader (serif + italic), woff2, latin
  and latin-ext subsets, preloaded.
- Responsive: progressive `max-width` steps with **820px as the main
  breakpoint**; `prefers-reduced-motion: reduce` honored.
- `[hidden]{display:none!important}` as the first rule — kills the
  specificity-zero bug class (documented lesson in the source CSS).
- Editorial dark theme with signature effects: grain overlay, aurora,
  canvas node-network background, reveal animations (`.rev`, `.d1–.d3`),
  masked headline, magnetic buttons (`data-mag`).
- Images always carry explicit `width`/`height` (no layout shift).

### 1.4 JavaScript (three small files, ~18 KB total)

- `fx.js` — background/effects, **single source** (the site's own comments
  record the drift bug caused when it was copy-pasted into two shells: one
  source of truth per behavior).
- `blog.js` — client-side search over `search-index.json`.
- `consent.js` — self-hosted cookie consent, zero third-party trackers.

### 1.5 Search index shape (per language)

Array of `{t: title, e: excerpt, u: url, c: category label, d: ISO date,
dh: human date in that language, m: minutes-to-read, s: lowercased searchable
text}` — small, static, language-scoped.

### 1.6 SWA configuration ideas (feeds ADR-0005's `swa` adapter)

- `responseOverrides`: 404 → `/404.html`; **403 masked as 404**; 401 →
  provider login with `post_login_redirect_uri`.
- Security headers globally: `X-Content-Type-Options: nosniff`,
  `X-Frame-Options: SAMEORIGIN`, `Referrer-Policy:
  strict-origin-when-cross-origin`, `Permissions-Policy` denying
  geolocation/microphone/camera.
- Cache policy: HTML `no-cache, must-revalidate`; `/assets/*`, sitemap and
  robots cached 24h.
- **Legacy redirect map** (301s from an older site's URLs to the new anchors,
  per language) — redirects are content, so they belong in the content model.
- Role-protected route (`allowedRoles`) and disabled unused auth providers
  (unwanted login route → 404).
- Explicit `mimeTypes` for `.json`, `.xml`, `.webmanifest`.

## 2. What the framework must generalize

| ph7x.com hardcodes | The framework provides |
| --- | --- |
| Hand-written head block per template | Head contract generated from page/article models (hreflang from translations, OG from content + media, JSON-LD from site config) |
| Localized slugs maintained by hand | Per-language `slug` on `PageContent`/article translations (already in the model) with parity validation |
| Sections fixed in HTML | `Section.kind` → theme template (hero, about, expertise-grid, work, certs, contact) |
| One-off search index script | `search-index.json` emitted by the builder per language |
| Manual redirect list | Redirect entries in the content model, emitted by each deployment adapter |
| CSS/JS copied between shells | Theme package with tokens + per-shell bundles, single-source assets |

## 3. Execution phases

### Phase A — generator parity (Milestone 2)

1. Model the site as content: home page (kick/hero/about/expertise/work/
   certs sections), contact page, legal pages, ~7 articles with categories —
   **fictional company, fictional posts**, same shapes.
2. `cms-build` renders through the theme interface and reproduces: the URL
   tree of §1.1, the head contract of §1.2, sitemap, per-language RSS,
   pagination, category pages, search indexes, hashed asset URLs.
3. `cms-validation` gates: language parity (a missing translation blocks that
   page), slug uniqueness per language, alt text, head-contract completeness.
4. `cms export --target swa` emits §1.6 as `staticwebapp.config.json`;
   `--target nginx` emits the same policy as `nginx.conf`.
5. **Acceptance**: structural-parity test suite — same URL set shape, every
   page passes a head-contract checker, builds are byte-deterministic.

### Phase B — reference theme (Milestone 4)

1. `cms-theme-ph7x-reference` implements §1.3: tokens, local fonts, 820px
   breakpoint, `[hidden]` rule, reduced-motion, dark editorial look, effects
   (grain/aurora/network/reveals) as theme assets — single-source.
2. `examples/multilingual-company-site` = the fictional content of Phase A
   rendered with this theme in 5 languages; becomes the Copier template for
   `cms init` (ADR-0006-to-be) and the CI-built example.
3. **Acceptance**: example builds in CI on every push; link check, WCAG 2.2 AA
   checks, no horizontal scroll at any breakpoint, zero inline styles.

## 4. Bug classes the framework kills by design

The live site's source comments record real bugs it hit. We inherit the
lessons, not the bugs — each one becomes a structural guarantee:

| Bug the site hit | How the framework makes it impossible |
| --- | --- |
| `[hidden]` elements reappearing (browser rule has zero specificity; any `display:` rule silently defeats it — bit the privacy notice and the contact form) | `[hidden]{display:none!important}` ships as the first rule of the theme **base layer**, non-optional; a theme conformance test asserts it |
| Effects script copy-pasted into two shells, missing from a third — divergence from duplicated sources | Assets belong to the theme package and are referenced, never inlined per template; a build check fails on duplicated asset content |
| Pages missing shared behavior because each shell hand-assembles its `<head>`/scripts | The head contract and asset includes are **generated** from one place; templates receive them, they don't write them |
| Redirect map maintained by hand in platform config, drifting from real URLs | Redirects live in the content model; adapters emit them; the validator cross-checks targets against generated URLs |
| Stale search index / RSS after content edits | Indexes and feeds are build outputs, regenerated on every build — never edited artifacts |
| Cache-busting hashes bumped manually or forgotten | Asset URLs get content hashes computed by the builder; deterministic builds mean hashes change exactly when content does |

## 5. Hard constraints

- `Ph7x.Site.Corporate` is never modified and never imported verbatim.
- No real business/personal data (names, addresses, phone numbers, VAT,
  emails) in this repository — the JSON-LD structures are reproduced with
  fictional data only.
- Everything lands behind the existing gates: mypy strict, ruff, tests, docs
  anti-drift, secret scan.
