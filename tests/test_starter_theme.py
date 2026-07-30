"""The starter theme is certified by the public contract (#193).

The example under `examples/starter-theme/` is the answer to "show me a
theme": minimal enough to read in one sitting, and conforming enough to
build on. This test runs the same suite a third-party author runs —
`cms_build.theme_conformance` — so the example can never drift into
being aspirational documentation.

It is not installed as a package: the path is added here so the example
stays a directory to copy rather than a distribution to release.
"""

import sys
from pathlib import Path

import pytest
from cms_build.theme_conformance import conformance_checks
from cms_build.themes import Theme

STARTER_SRC = Path(__file__).resolve().parents[1] / "examples" / "starter-theme" / "src"
if str(STARTER_SRC) not in sys.path:
    sys.path.insert(0, str(STARTER_SRC))


def _starter() -> Theme:
    from sardine_theme_starter import StarterTheme

    return StarterTheme()


@pytest.mark.parametrize(("check_name", "check"), conformance_checks())
def test_the_starter_theme_is_certified(check_name: str, check: object) -> None:
    check(_starter())  # type: ignore[operator]


def test_the_starter_theme_stays_minimal() -> None:
    """Its value is being small. If it grows into a design, it stops
    being the thing a newcomer reads first."""
    package = STARTER_SRC / "sardine_theme_starter"
    css = sum(
        len(path.read_text(encoding="utf-8").splitlines())
        for path in (package / "assets").glob("*.css")
    )
    templates = sorted(path.name for path in (package / "templates").glob("*.j2"))
    assert css <= 70, f"{css} lines of CSS"
    assert templates == [
        "_head.html.j2",
        "_section.html.j2",
        "article.html.j2",
        "base.html.j2",
        "listing.html.j2",
        "not_found.html.j2",
        "page.html.j2",
    ]


def test_the_generic_renderer_covers_kinds_it_has_never_seen() -> None:
    """The fallback is the feature: a kind an extension invents still
    renders its fields instead of vanishing."""
    from cms_build import build_site
    from cms_build.theme_conformance import sample_config
    from cms_core import ContentStatus
    from cms_core.pages import PageContent, Section, SectionContent, new_page
    from cms_validation import SiteContent

    page = new_page("odd", PageContent(title="Odd", description="D", slug="odd"))
    page.sections.append(
        Section(
            key="invented",
            kind="kind-from-an-extension",
            source=SectionContent(fields={"note": "STARTERSENTINEL"}),
        )
    )
    page.status = ContentStatus.PUBLISHED
    artifact = build_site(sample_config(), SiteContent(pages=[page]), theme=_starter())
    html = artifact.files["odd/index.html"].decode("utf-8")
    assert "STARTERSENTINEL" in html
    assert 'class="section section-kind-from-an-extension"' in html
