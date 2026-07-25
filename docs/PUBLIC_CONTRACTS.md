# Public Contracts

The map of what Sardine CMS promises publicly: every surface a third
party may build against, where its specification lives, how it is
versioned, and how conformance is verified.

**This page is an index, not a specification.** It answers four
questions per surface and points at the document that owns the detail.
Nothing here restates a contract — follow the reference.

Scope note (see [ROADMAP.md](ROADMAP.md), the frozen 1.0 scope): the
stability promise covers these surfaces, not every module or symbol in
the repository. Including a capability in a release does not make its
internals public API.

## Versioned contracts and suites

Two kinds of artifact carry a version, and they are not the same
promise. An **integration contract** is what third-party code
implements; its version is a promise to implementers. A **conformance
suite** is an executable definition of what conforming means; its
version tracks the rules it verifies.

| Surface | What it is | Normative specification | Versioning | Verified by |
| --- | --- | --- | --- | --- |
| Theme conformance | Conformance suite (theme authors) | [ADR-0053](adr/0053-theme-conformance-contract.md); the checks in `cms_build.theme_conformance` | `CONFORMANCE_VERSION`, additive within a version | A parametrized test over `conformance_checks()`; both bundled themes are certified in CI |
| Translation provider contract | Integration contract (provider authors) | [ADR-0054](adr/0054-translation-providers.md); authoring guide: [WRITING_A_TRANSLATION_PROVIDER.md](WRITING_A_TRANSLATION_PROVIDER.md) | `TRANSLATION_CONTRACT_VERSION`, additive within a version | Validated at selection time (version and protocol) before anything runs |
| Translation conformance | Conformance suite (provider authors) | `cms_core.translation_conformance` — the named checks are the definition | `TRANSLATION_CONFORMANCE_VERSION`, tracks the contract | A four-line parametrized test in the author's own suite; fixture providers certified in CI |
| Forms provider contract | Integration contract (extension authors) | [ADR-0040](adr/0040-forms-provider-contract.md); authoring guide: [WRITING_A_FORMS_PROVIDER.md](WRITING_A_FORMS_PROVIDER.md) | `FORMS_CONTRACT_VERSION`, additive within a version | Validated at selection time; repo conformance suite over an extension-registered provider |
| Deployment provider contract | Integration contract (extension authors) | [WRITING_A_DEPLOYMENT_PROVIDER.md](WRITING_A_DEPLOYMENT_PROVIDER.md); operator semantics in [DEPLOYMENT_PROVIDERS.md](DEPLOYMENT_PROVIDERS.md) | `DEPLOY_CONTRACT_VERSION`, additive within a version | Validated at selection time; deployment conformance suite over the bundled providers |
| UI conformance | Conformance suite (core and contributors) | The rules in [DESIGN_RULES.md](DESIGN_RULES.md) (DS-1…DS-19), decided by [ADR-0055](adr/0055-backoffice-design-system.md); what is enforced: [UI_CONFORMANCE.md](UI_CONFORMANCE.md) | `UI_CONFORMANCE_VERSION`, tracks the rules it verifies | CI: the suite over every registered screen, the viewport gate, the axe gate |

The UI conformance suite is public as an **architecture and
contribution contract for the panel**. It is not an external
integration promise like the translation contract, and it is not
presented as one.

## Integration surfaces without a contract version

Real extension points, deliberately listed with the same columns so
their status is visible rather than assumed. Giving any of them a
version follows the ordinary process — ADR, implementation,
documentation, version policy — and is never done for symmetry.

| Surface | What it is | Normative specification | Versioning | Verified by |
| --- | --- | --- | --- | --- |
| Storage backends | Integration surface (backend authors) | [ADR-0004](adr/0004-storage-backend-factory.md) | Not applicable — no contract version; the conformance suite is the definition | The backend conformance suite, run unchanged against every engine (a required CI check for PostgreSQL) |
| Comments providers | Integration surface (extension authors) | [ADR-0031](adr/0031-comments-integration.md) | Not applicable — a data shape selected by name, with no version validated at selection | Consent and vendoring rules checked by the build's output-integrity tests |
| Language packs | Integration surface (pack authors) | [ADR-0034](adr/0034-language-packs.md); authoring guide: [LANGUAGE_PACK_GUIDE.md](LANGUAGE_PACK_GUIDE.md) | Not applicable — packs are data registered at load | An end-to-end build with the pack's tag; RTL packs ride the CI accessibility gate |
| Section kinds | Integration surface (theme and extension authors) | [THEME_GUIDE.md](THEME_GUIDE.md) — the kind gallery and its field contract | Not applicable — unknown kinds degrade to generic rendering by design | Theme conformance (`gallery-kinds-render`, `unknown-kinds-degrade`) |

## Surfaces versioned with the product

These carry no independent version: they change with the release and
under the deprecation policy.

| Surface | Normative specification | Verified by |
| --- | --- | --- |
| The `cms` command line | [wiki: CLI Reference](https://github.com/ph7x-Systems/sardine-cms/wiki/CLI-Reference) | End-to-end CLI tests over a real project |
| `sardine.toml` | [wiki: Configuration](https://github.com/ph7x-Systems/sardine-cms/wiki/Configuration) | Project-loading tests; `cms doctor` |
| Portable content (JSON/Markdown export and import) | [ADR-0003](adr/0003-sqlite-poc-persistence.md) and the export format tests | Round-trip tests: export → import → identical content |
| Content API (built JSON) | [CONTENT_API.md](CONTENT_API.md) | Output-integrity tests over the built artifact |
| The panel's HTTP surface | [ADMIN_GUIDE.md](ADMIN_GUIDE.md) | The admin end-to-end suites |

## One normative specification per surface

> **Every public surface has exactly one normative specification. Every
> other document is informative and must reference it rather than
> reproduce it.**

This is the rule that keeps the map true. When something changes, the
question is not "how many places must I edit?" but "which document is
normative for this surface?" — edit that one, and let the rest point
at it. A guide that restates a contract will drift from it; a guide
that links to it cannot.

## Changing a contract

The version policy — what may change inside a version, what requires a
new one, and how long a superseded version stays supported — lives in
the deprecation policy (ADR, in preparation for 1.0). Until it lands,
the working rule is the one every contract here already follows:
additive changes inside a version, a new version for anything that
could make a conforming implementation non-conforming.
