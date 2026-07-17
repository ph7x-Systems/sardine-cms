"""SQLite persistence (development backend).

The database is a working store only — the portable source of truth is always
the JSON/Markdown export (see :mod:`cms_core.export`). Schema migrations are
ordered scripts applied once each, tracked via SQLite's ``user_version``.
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path

from cms_core.languages import Language
from cms_core.media import MediaAsset
from cms_core.models import Article, ArticleContent
from cms_core.pages import Page, PageContent, Section, SectionContent
from cms_core.states import ContentStatus
from cms_core.translatable import Translation

MIGRATIONS: tuple[str, ...] = (
    """
    CREATE TABLE articles (
        id TEXT PRIMARY KEY,
        status TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        title TEXT NOT NULL,
        summary TEXT NOT NULL,
        body_markdown TEXT NOT NULL
    );
    CREATE TABLE translations (
        article_id TEXT NOT NULL REFERENCES articles(id) ON DELETE CASCADE,
        language TEXT NOT NULL,
        title TEXT NOT NULL,
        summary TEXT NOT NULL,
        body_markdown TEXT NOT NULL,
        source_checksum TEXT NOT NULL,
        PRIMARY KEY (article_id, language)
    );
    """,
    """
    CREATE TABLE pages (
        id TEXT PRIMARY KEY,
        status TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        title TEXT NOT NULL,
        description TEXT NOT NULL,
        slug TEXT NOT NULL
    );
    CREATE TABLE page_translations (
        page_id TEXT NOT NULL REFERENCES pages(id) ON DELETE CASCADE,
        language TEXT NOT NULL,
        title TEXT NOT NULL,
        description TEXT NOT NULL,
        slug TEXT NOT NULL,
        source_checksum TEXT NOT NULL,
        PRIMARY KEY (page_id, language)
    );
    CREATE TABLE sections (
        page_id TEXT NOT NULL REFERENCES pages(id) ON DELETE CASCADE,
        key TEXT NOT NULL,
        position INTEGER NOT NULL,
        kind TEXT NOT NULL,
        fields_json TEXT NOT NULL,
        media_json TEXT NOT NULL,
        PRIMARY KEY (page_id, key)
    );
    CREATE TABLE section_translations (
        page_id TEXT NOT NULL,
        section_key TEXT NOT NULL,
        language TEXT NOT NULL,
        fields_json TEXT NOT NULL,
        media_json TEXT NOT NULL,
        source_checksum TEXT NOT NULL,
        PRIMARY KEY (page_id, section_key, language),
        FOREIGN KEY (page_id, section_key)
            REFERENCES sections(page_id, key) ON DELETE CASCADE
    );
    CREATE TABLE media_assets (
        id TEXT PRIMARY KEY,
        path TEXT NOT NULL,
        mime_type TEXT NOT NULL,
        width INTEGER,
        height INTEGER
    );
    CREATE TABLE media_alt_texts (
        media_id TEXT NOT NULL REFERENCES media_assets(id) ON DELETE CASCADE,
        language TEXT NOT NULL,
        alt TEXT NOT NULL,
        PRIMARY KEY (media_id, language)
    );
    """,
)


def connect(path: Path | str) -> sqlite3.Connection:
    connection = sqlite3.connect(path)
    connection.execute("PRAGMA foreign_keys = ON")
    migrate(connection)
    return connection


def schema_version(connection: sqlite3.Connection) -> int:
    row = connection.execute("PRAGMA user_version").fetchone()
    return int(row[0])


def migrate(connection: sqlite3.Connection) -> int:
    current = schema_version(connection)
    for number, script in enumerate(MIGRATIONS[current:], start=current + 1):
        connection.executescript(script)
        connection.execute(f"PRAGMA user_version = {number}")
        connection.commit()
    return schema_version(connection)


def save_article(connection: sqlite3.Connection, article: Article) -> None:
    with connection:
        connection.execute(
            "INSERT INTO articles"
            " (id, status, created_at, updated_at, title, summary, body_markdown)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)"
            " ON CONFLICT(id) DO UPDATE SET"
            " status = excluded.status, updated_at = excluded.updated_at,"
            " title = excluded.title, summary = excluded.summary,"
            " body_markdown = excluded.body_markdown",
            (
                article.id,
                article.status.value,
                article.created_at.isoformat(),
                article.updated_at.isoformat(),
                article.source.title,
                article.source.summary,
                article.source.body_markdown,
            ),
        )
        connection.execute("DELETE FROM translations WHERE article_id = ?", (article.id,))
        connection.executemany(
            "INSERT INTO translations"
            " (article_id, language, title, summary, body_markdown, source_checksum)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            [
                (
                    article.id,
                    language.value,
                    translation.content.title,
                    translation.content.summary,
                    translation.content.body_markdown,
                    translation.source_checksum,
                )
                for language, translation in sorted(
                    article.translations.items(), key=lambda item: item[0].value
                )
            ],
        )


def load_article(connection: sqlite3.Connection, article_id: str) -> Article | None:
    row = connection.execute(
        "SELECT id, status, created_at, updated_at, title, summary, body_markdown"
        " FROM articles WHERE id = ?",
        (article_id,),
    ).fetchone()
    if row is None:
        return None
    translations: dict[Language, Translation[ArticleContent]] = {}
    for t_row in connection.execute(
        "SELECT language, title, summary, body_markdown, source_checksum"
        " FROM translations WHERE article_id = ? ORDER BY language",
        (article_id,),
    ):
        translations[Language(t_row[0])] = Translation[ArticleContent](
            content=ArticleContent(title=t_row[1], summary=t_row[2], body_markdown=t_row[3]),
            source_checksum=t_row[4],
        )
    return Article(
        id=row[0],
        status=ContentStatus(row[1]),
        created_at=datetime.fromisoformat(row[2]),
        updated_at=datetime.fromisoformat(row[3]),
        source=ArticleContent(title=row[4], summary=row[5], body_markdown=row[6]),
        translations=translations,
    )


def delete_article(connection: sqlite3.Connection, article_id: str) -> bool:
    with connection:
        cursor = connection.execute("DELETE FROM articles WHERE id = ?", (article_id,))
    return cursor.rowcount > 0


def list_article_ids(connection: sqlite3.Connection) -> list[str]:
    rows = connection.execute("SELECT id FROM articles ORDER BY id").fetchall()
    return [str(row[0]) for row in rows]


def load_all_articles(connection: sqlite3.Connection) -> list[Article]:
    articles: list[Article] = []
    for article_id in list_article_ids(connection):
        article = load_article(connection, article_id)
        if article is not None:
            articles.append(article)
    return articles


def save_page(connection: sqlite3.Connection, page: Page) -> None:
    with connection:
        connection.execute(
            "INSERT INTO pages (id, status, created_at, updated_at, title, description, slug)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)"
            " ON CONFLICT(id) DO UPDATE SET"
            " status = excluded.status, updated_at = excluded.updated_at,"
            " title = excluded.title, description = excluded.description,"
            " slug = excluded.slug",
            (
                page.id,
                page.status.value,
                page.created_at.isoformat(),
                page.updated_at.isoformat(),
                page.source.title,
                page.source.description,
                page.source.slug,
            ),
        )
        connection.execute("DELETE FROM page_translations WHERE page_id = ?", (page.id,))
        connection.executemany(
            "INSERT INTO page_translations"
            " (page_id, language, title, description, slug, source_checksum)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            [
                (
                    page.id,
                    language.value,
                    translation.content.title,
                    translation.content.description,
                    translation.content.slug,
                    translation.source_checksum,
                )
                for language, translation in sorted(
                    page.translations.items(), key=lambda item: item[0].value
                )
            ],
        )
        connection.execute("DELETE FROM sections WHERE page_id = ?", (page.id,))
        for position, section in enumerate(page.sections):
            connection.execute(
                "INSERT INTO sections (page_id, key, position, kind, fields_json, media_json)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                (
                    page.id,
                    section.key,
                    position,
                    section.kind,
                    json.dumps(section.source.fields, sort_keys=True),
                    json.dumps(section.source.media),
                ),
            )
            connection.executemany(
                "INSERT INTO section_translations"
                " (page_id, section_key, language, fields_json, media_json, source_checksum)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                [
                    (
                        page.id,
                        section.key,
                        language.value,
                        json.dumps(translation.content.fields, sort_keys=True),
                        json.dumps(translation.content.media),
                        translation.source_checksum,
                    )
                    for language, translation in sorted(
                        section.translations.items(), key=lambda item: item[0].value
                    )
                ],
            )


def _load_sections(connection: sqlite3.Connection, page_id: str) -> list[Section]:
    sections: list[Section] = []
    for row in connection.execute(
        "SELECT key, kind, fields_json, media_json FROM sections"
        " WHERE page_id = ? ORDER BY position",
        (page_id,),
    ):
        translations: dict[Language, Translation[SectionContent]] = {}
        for t_row in connection.execute(
            "SELECT language, fields_json, media_json, source_checksum"
            " FROM section_translations WHERE page_id = ? AND section_key = ?"
            " ORDER BY language",
            (page_id, row[0]),
        ):
            translations[Language(t_row[0])] = Translation[SectionContent](
                content=SectionContent(fields=json.loads(t_row[1]), media=json.loads(t_row[2])),
                source_checksum=t_row[3],
            )
        sections.append(
            Section(
                key=row[0],
                kind=row[1],
                source=SectionContent(fields=json.loads(row[2]), media=json.loads(row[3])),
                translations=translations,
            )
        )
    return sections


def load_page(connection: sqlite3.Connection, page_id: str) -> Page | None:
    row = connection.execute(
        "SELECT id, status, created_at, updated_at, title, description, slug"
        " FROM pages WHERE id = ?",
        (page_id,),
    ).fetchone()
    if row is None:
        return None
    translations: dict[Language, Translation[PageContent]] = {}
    for t_row in connection.execute(
        "SELECT language, title, description, slug, source_checksum"
        " FROM page_translations WHERE page_id = ? ORDER BY language",
        (page_id,),
    ):
        translations[Language(t_row[0])] = Translation[PageContent](
            content=PageContent(title=t_row[1], description=t_row[2], slug=t_row[3]),
            source_checksum=t_row[4],
        )
    return Page(
        id=row[0],
        status=ContentStatus(row[1]),
        created_at=datetime.fromisoformat(row[2]),
        updated_at=datetime.fromisoformat(row[3]),
        source=PageContent(title=row[4], description=row[5], slug=row[6]),
        translations=translations,
        sections=_load_sections(connection, page_id),
    )


def delete_page(connection: sqlite3.Connection, page_id: str) -> bool:
    with connection:
        cursor = connection.execute("DELETE FROM pages WHERE id = ?", (page_id,))
    return cursor.rowcount > 0


def list_page_ids(connection: sqlite3.Connection) -> list[str]:
    rows = connection.execute("SELECT id FROM pages ORDER BY id").fetchall()
    return [str(row[0]) for row in rows]


def load_all_pages(connection: sqlite3.Connection) -> list[Page]:
    pages: list[Page] = []
    for page_id in list_page_ids(connection):
        page = load_page(connection, page_id)
        if page is not None:
            pages.append(page)
    return pages


def save_media_asset(connection: sqlite3.Connection, asset: MediaAsset) -> None:
    with connection:
        connection.execute(
            "INSERT INTO media_assets (id, path, mime_type, width, height)"
            " VALUES (?, ?, ?, ?, ?)"
            " ON CONFLICT(id) DO UPDATE SET"
            " path = excluded.path, mime_type = excluded.mime_type,"
            " width = excluded.width, height = excluded.height",
            (asset.id, asset.path, asset.mime_type, asset.width, asset.height),
        )
        connection.execute("DELETE FROM media_alt_texts WHERE media_id = ?", (asset.id,))
        connection.executemany(
            "INSERT INTO media_alt_texts (media_id, language, alt) VALUES (?, ?, ?)",
            [
                (asset.id, language.value, alt)
                for language, alt in sorted(asset.alt.items(), key=lambda item: item[0].value)
            ],
        )


def load_media_asset(connection: sqlite3.Connection, asset_id: str) -> MediaAsset | None:
    row = connection.execute(
        "SELECT id, path, mime_type, width, height FROM media_assets WHERE id = ?",
        (asset_id,),
    ).fetchone()
    if row is None:
        return None
    alt = {
        Language(alt_row[0]): str(alt_row[1])
        for alt_row in connection.execute(
            "SELECT language, alt FROM media_alt_texts WHERE media_id = ? ORDER BY language",
            (asset_id,),
        )
    }
    return MediaAsset(
        id=row[0], path=row[1], mime_type=row[2], width=row[3], height=row[4], alt=alt
    )


def delete_media_asset(connection: sqlite3.Connection, asset_id: str) -> bool:
    with connection:
        cursor = connection.execute("DELETE FROM media_assets WHERE id = ?", (asset_id,))
    return cursor.rowcount > 0


def list_media_ids(connection: sqlite3.Connection) -> list[str]:
    rows = connection.execute("SELECT id FROM media_assets ORDER BY id").fetchall()
    return [str(row[0]) for row in rows]


def load_all_media_assets(connection: sqlite3.Connection) -> list[MediaAsset]:
    assets: list[MediaAsset] = []
    for asset_id in list_media_ids(connection):
        asset = load_media_asset(connection, asset_id)
        if asset is not None:
            assets.append(asset)
    return assets
