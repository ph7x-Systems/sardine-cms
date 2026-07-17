"""SQLite round-trip and migration behavior."""

from pathlib import Path

from cms_core import ArticleContent, ContentStatus, Language, new_article
from cms_core.storage import (
    MIGRATIONS,
    connect,
    delete_article,
    list_article_ids,
    load_article,
    migrate,
    save_article,
    schema_version,
)


def test_connect_applies_all_migrations(tmp_path: Path) -> None:
    connection = connect(tmp_path / "cms.sqlite3")
    assert schema_version(connection) == len(MIGRATIONS)
    # A second migrate call is a no-op, not an error.
    assert migrate(connection) == len(MIGRATIONS)


def test_article_round_trip(tmp_path: Path) -> None:
    connection = connect(tmp_path / "cms.sqlite3")
    article = new_article("first-post", ArticleContent(title="First", body_markdown="Hello."))
    article.set_translation(Language.PT_PT, ArticleContent(title="Primeiro", body_markdown="Olá."))
    article.status = ContentStatus.REVIEW

    save_article(connection, article)
    loaded = load_article(connection, "first-post")

    assert loaded == article


def test_save_is_an_upsert(tmp_path: Path) -> None:
    connection = connect(tmp_path / "cms.sqlite3")
    article = new_article("first-post", ArticleContent(title="First"))
    save_article(connection, article)

    article.source = ArticleContent(title="First, revised")
    article.set_translation(Language.ES, ArticleContent(title="Primero"))
    save_article(connection, article)

    loaded = load_article(connection, "first-post")
    assert loaded is not None
    assert loaded.source.title == "First, revised"
    assert set(loaded.translations) == {Language.ES}


def test_delete_cascades_to_translations(tmp_path: Path) -> None:
    connection = connect(tmp_path / "cms.sqlite3")
    article = new_article("first-post", ArticleContent(title="First"))
    article.set_translation(Language.FR, ArticleContent(title="Premier"))
    save_article(connection, article)

    assert delete_article(connection, "first-post")
    assert not delete_article(connection, "first-post")
    assert list_article_ids(connection) == []
    remaining = connection.execute("SELECT COUNT(*) FROM translations").fetchone()[0]
    assert remaining == 0


def test_missing_article_loads_as_none(tmp_path: Path) -> None:
    connection = connect(tmp_path / "cms.sqlite3")
    assert load_article(connection, "nope") is None


def test_page_round_trip_preserves_section_order(tmp_path: Path) -> None:
    from cms_core import MediaAsset, PageContent, Section, SectionContent, new_page
    from cms_core.storage import load_page, save_media_asset, save_page

    connection = connect(tmp_path / "cms.sqlite3")
    page = new_page("home", PageContent(title="Home", slug="home"))
    for key in ("hero", "features", "contact"):
        page.sections.append(
            Section(key=key, kind=key, source=SectionContent(fields={"heading": key.title()}))
        )
    page.sections[0].set_translation(
        Language.PT_PT, SectionContent(fields={"heading": "Bem-vindo"})
    )
    page.set_translation(Language.PT_PT, PageContent(title="Início", slug="inicio"))
    save_page(connection, page)

    asset = MediaAsset(
        id="hero-image",
        path="images/hero.webp",
        mime_type="image/webp",
        width=1600,
        height=900,
        alt={Language.EN: "A sunrise", Language.PT_PT: "Um nascer do sol"},
    )
    save_media_asset(connection, asset)

    loaded = load_page(connection, "home")
    assert loaded is not None
    assert loaded == page
    assert [section.key for section in loaded.sections] == ["hero", "features", "contact"]


def test_media_round_trip_and_delete(tmp_path: Path) -> None:
    from cms_core import MediaAsset
    from cms_core.storage import (
        delete_media_asset,
        list_media_ids,
        load_media_asset,
        save_media_asset,
    )

    connection = connect(tmp_path / "cms.sqlite3")
    asset = MediaAsset(
        id="logo",
        path="images/logo.svg",
        mime_type="image/svg+xml",
        width=64,
        height=64,
        alt={Language.EN: "Company logo"},
    )
    save_media_asset(connection, asset)
    assert load_media_asset(connection, "logo") == asset
    assert list_media_ids(connection) == ["logo"]

    assert delete_media_asset(connection, "logo")
    assert load_media_asset(connection, "logo") is None
    orphan_alts = connection.execute("SELECT COUNT(*) FROM media_alt_texts").fetchone()[0]
    assert orphan_alts == 0


def test_page_delete_cascades(tmp_path: Path) -> None:
    from cms_core import PageContent, Section, SectionContent, new_page
    from cms_core.storage import delete_page, list_page_ids, save_page

    connection = connect(tmp_path / "cms.sqlite3")
    page = new_page("home", PageContent(title="Home", slug="home"))
    hero = Section(key="hero", kind="hero", source=SectionContent(fields={"heading": "Welcome"}))
    hero.set_translation(Language.FR, SectionContent(fields={"heading": "Bienvenue"}))
    page.sections.append(hero)
    save_page(connection, page)

    assert delete_page(connection, "home")
    assert list_page_ids(connection) == []
    for table in ("sections", "section_translations", "page_translations"):
        count = connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        assert count == 0
