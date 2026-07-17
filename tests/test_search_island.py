"""The <site-search> island: progressive enhancement, localization, budget."""

from datetime import UTC, datetime

from cms_build import SiteConfig, build_site, create_theme
from cms_core import (
    ArticleContent,
    ContentStatus,
    Language,
    new_article,
)
from cms_validation import SiteContent

NOW = datetime(2026, 1, 15, 9, 0, tzinfo=UTC)

CONFIG = SiteConfig(
    name="Aurora",
    base_url="https://example.com",
    languages=(Language.PT_PT,),
    labels={"search": {Language.PT_PT: "Procurar nos mapas"}},
)

JS_BUDGET_BYTES = 20 * 1024  # DESIGN_RULES §5


def make_content() -> SiteContent:
    article = new_article(
        "alpha", ArticleContent(title="Alpha", summary="S", body_markdown="Body"), now=NOW
    )
    article.set_translation(Language.PT_PT, ArticleContent(title="Alfa", summary="S"))
    article.status = ContentStatus.PUBLISHED
    return SiteContent(articles=[article])


def test_listing_embeds_the_search_island_per_language() -> None:
    artifact = build_site(CONFIG, make_content())
    en = artifact.files["blog/index.html"].decode("utf-8")
    pt = artifact.files["pt-pt/blog/index.html"].decode("utf-8")
    assert '<site-search index-url="/blog/search-index.json"' in en
    assert '<site-search index-url="/pt-pt/blog/search-index.json"' in pt
    assert 'label="Search"' in en
    # Project override wins over the shipped default ("Pesquisar").
    assert 'label="Procurar nos mapas"' in pt


def test_search_script_is_hash_versioned_module() -> None:
    artifact = build_site(CONFIG, make_content())
    html = artifact.files["blog/index.html"].decode("utf-8")
    assert '<script type="module" src="/assets/search.js?v=' in html
    assert "assets/search.js" in artifact.paths()


def test_page_is_complete_without_javascript() -> None:
    """Progressive enhancement: the server-rendered entries are always there."""
    artifact = build_site(CONFIG, make_content())
    html = artifact.files["blog/index.html"].decode("utf-8")
    assert '<a href="/blog/alpha/">Alpha</a>' in html


def test_theme_javascript_stays_within_budget() -> None:
    assets = create_theme("default").assets()
    total = sum(len(data) for path, data in assets.items() if path.endswith(".js"))
    assert 0 < total <= JS_BUDGET_BYTES
