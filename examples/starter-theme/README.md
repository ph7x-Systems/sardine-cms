# Starter theme

A deliberately minimal Sardine CMS theme: five templates, one
stylesheet, no build step, no JavaScript. It exists to be read and
copied — the contract in [THEME_GUIDE.md](../../docs/THEME_GUIDE.md) is
what a theme must do; this is what that looks like in files.

It passes the theme conformance suite in full, so it is a legitimate
starting point rather than a sketch.

## What is deliberately absent

**Any branch on a section kind.** `_section.html.j2` renders every kind
through one loop — fields, repeatable rows and images — including kinds
it has never seen, which is what the section contract promises. A real
theme adds branches for the kinds it wants to art-direct and *keeps a
fallback like this one*; dropping the fallback is how a theme starts
losing content silently.

Also absent: fonts, motion, colour beyond four tokens, and any layout
that a reader would remember. That is the point.

## Copy it

```bash
cp -r examples/starter-theme ../my-theme
cd ../my-theme
# rename the package directory and, in pyproject.toml, the project name
# and the entry point:
#   [project.entry-points."sardine.themes"]
#   my-theme = "my_theme:MyTheme"
pip install -e .
```

Then in the project's `sardine.toml`:

```toml
[site]
theme = "my-theme"
```

Nothing registers the theme in code: the entry point is the whole
declaration, and the panel discovers it from packaging metadata without
importing anything.

## Prove it still conforms

Four lines in your own test suite, run against your theme:

```python
import pytest
from cms_build import create_theme
from cms_build.theme_conformance import conformance_checks


@pytest.mark.parametrize(("name", "check"), conformance_checks())
def test_conformance(name, check):
    check(create_theme("my-theme"))
```

The suite is versioned and public — see
[PUBLIC_CONTRACTS.md](../../docs/PUBLIC_CONTRACTS.md). Run it before you
publish, and again whenever you touch a template.

## What to change first

1. `assets/site.css` — the tokens at the top, then the type scale.
2. `templates/base.html.j2` — the shell, the navigation, the footer.
3. `templates/_section.html.j2` — add a branch for one kind, keep the
   fallback.

The `_head.html.j2` include is best left alone: the builder computes the
canonical URL, `hreflang` alternates, Open Graph and JSON-LD from the
content, and a theme that reinvents them will disagree with the sitemap.

## Declaring compatibility

This example depends on `sardine-cms-build>=0.8` so it keeps working
while you read it. A theme you publish should declare the range it
actually certified against — the panel shows that range as its
compatibility verdict, and an honest bound is more useful to an
operator than a permissive one.
