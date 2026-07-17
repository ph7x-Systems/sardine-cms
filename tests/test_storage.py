"""Backend conformance suite (ADR-0004): every engine must pass unchanged.

The `backend` fixture (tests/conftest.py) parameterizes these tests over all
implemented engines — SQLite always, PostgreSQL when a server is available.
"""

from cms_core import (
    ArticleContent,
    ContentStatus,
    Language,
    MediaAsset,
    PageContent,
    Section,
    SectionContent,
    new_article,
    new_page,
)
from cms_core.storage import MIGRATIONS, StorageBackend


def test_connect_applies_all_migrations(backend: StorageBackend) -> None:
    assert backend.schema_version() == len(MIGRATIONS)
    # A second migrate call is a no-op, not an error.
    assert backend.migrate() == len(MIGRATIONS)


def test_article_round_trip(backend: StorageBackend) -> None:
    article = new_article("first-post", ArticleContent(title="First", body_markdown="Hello."))
    article.set_translation(Language.PT_PT, ArticleContent(title="Primeiro", body_markdown="Olá."))
    article.status = ContentStatus.REVIEW
    article.category = "field-notes"
    article.tags = ("craft", "maps")

    backend.save_article(article)
    assert backend.load_article("first-post") == article


def test_save_is_an_upsert(backend: StorageBackend) -> None:
    article = new_article("first-post", ArticleContent(title="First"))
    backend.save_article(article)

    article.source = ArticleContent(title="First, revised")
    article.set_translation(Language.ES, ArticleContent(title="Primero"))
    backend.save_article(article)

    loaded = backend.load_article("first-post")
    assert loaded is not None
    assert loaded.source.title == "First, revised"
    assert set(loaded.translations) == {Language.ES}


def test_delete_cascades_to_translations(backend: StorageBackend) -> None:
    article = new_article("first-post", ArticleContent(title="First"))
    article.set_translation(Language.FR, ArticleContent(title="Premier"))
    backend.save_article(article)

    assert backend.delete_article("first-post")
    assert not backend.delete_article("first-post")
    assert backend.list_article_ids() == []


def test_missing_article_loads_as_none(backend: StorageBackend) -> None:
    assert backend.load_article("nope") is None


def test_page_round_trip_preserves_section_order(backend: StorageBackend) -> None:
    page = new_page("home", PageContent(title="Home", slug="home"))
    for key in ("hero", "features", "contact"):
        page.sections.append(
            Section(key=key, kind=key, source=SectionContent(fields={"heading": key.title()}))
        )
    page.sections[0].set_translation(
        Language.PT_PT, SectionContent(fields={"heading": "Bem-vindo"})
    )
    page.set_translation(Language.PT_PT, PageContent(title="Início", slug="inicio"))
    backend.save_page(page)

    loaded = backend.load_page("home")
    assert loaded is not None
    assert loaded == page
    assert [section.key for section in loaded.sections] == ["hero", "features", "contact"]


def test_page_delete_removes_page(backend: StorageBackend) -> None:
    page = new_page("home", PageContent(title="Home", slug="home"))
    hero = Section(key="hero", kind="hero", source=SectionContent(fields={"heading": "Welcome"}))
    hero.set_translation(Language.FR, SectionContent(fields={"heading": "Bienvenue"}))
    page.sections.append(hero)
    backend.save_page(page)

    assert backend.delete_page("home")
    assert backend.list_page_ids() == []
    assert backend.load_page("home") is None


def test_media_round_trip_and_delete(backend: StorageBackend) -> None:
    asset = MediaAsset(
        id="logo",
        path="images/logo.svg",
        mime_type="image/svg+xml",
        width=64,
        height=64,
        alt={Language.EN: "Company logo", Language.PT_PT: "Logótipo da empresa"},
    )
    backend.save_media_asset(asset)
    assert backend.load_media_asset("logo") == asset
    assert backend.list_media_ids() == ["logo"]

    assert backend.delete_media_asset("logo")
    assert backend.load_media_asset("logo") is None


def test_has_content_reflects_all_collections(backend: StorageBackend) -> None:
    assert not backend.has_content()
    backend.save_page(new_page("home", PageContent(title="Home", slug="home")))
    assert backend.has_content()
    backend.delete_page("home")
    assert not backend.has_content()


def test_load_all_collections(backend: StorageBackend) -> None:
    backend.save_article(new_article("b-post", ArticleContent(title="B")))
    backend.save_article(new_article("a-post", ArticleContent(title="A")))
    backend.save_page(new_page("home", PageContent(title="Home", slug="home")))

    assert [article.id for article in backend.load_all_articles()] == ["a-post", "b-post"]
    assert [page.id for page in backend.load_all_pages()] == ["home"]
    assert backend.load_all_media_assets() == []


def test_backend_is_a_context_manager(backend: StorageBackend) -> None:
    with backend as storage:
        storage.save_article(new_article("post", ArticleContent(title="Post")))
