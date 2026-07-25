"""Every registered admin screen passes the UI conformance suite
(#244, ADR-0055): the design system's rules run in CI, screen by
screen, instead of being re-argued in review.

Coverage is the registry itself — `snapshot_paths()` — so a new screen
joins the suite the moment it registers, plus one representative page
of each editor shape. Fixture-dependent rules (DS-19's large
collection, DS-8's language scale) have their own tests below.
"""

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

import pytest
from cms_admin import AdminSettings, create_app
from cms_admin.listing import PAGE_SIZE
from cms_admin.navigation import snapshot_paths
from cms_admin.security import hash_password
from cms_core import (
    ArticleContent,
    ContentStatus,
    Language,
    MediaAsset,
    MenuItem,
    Role,
    User,
    create_storage,
    new_article,
)
from cms_core.pages import PageContent, Section, SectionContent, new_page
from fastapi.testclient import TestClient
from ui_conformance import (
    UI_CONFORMANCE_VERSION,
    check_pagination_bounds_large_collections,
    conformance_checks,
    parse,
)

PASSWORD = "correct horse battery staple"
NOW = datetime(2026, 7, 25, tzinfo=UTC)

PROJECT_TOML = """
[site]
name = "Aurora Cartography"
base_url = "https://example.com"
languages = ["pt-pt", "es", "fr", "de"]

[storage]
url = "sqlite:///content.db"

[build]
output = "_site"
"""

ENTITY_PATHS = (
    "/articles/new",
    "/articles/tides",
    "/articles/tides/translations/pt-pt",
    "/pages/new",
    "/pages/crew",
    "/pages/crew/sections/hero",
    "/pages/crew/sections/hero/translations/pt-pt",
    "/pages/crew/translations/pt-pt",
    "/media/new",
    "/media/chart",
    "/menu?new=1",
)


def _seed(tmp_path: Path, *, articles: int = 2, toml: str = PROJECT_TOML) -> str:
    url = f"sqlite:///{tmp_path / 'content.db'}"
    (tmp_path / "sardine.toml").write_text(toml, encoding="utf-8")
    with create_storage(url) as storage:
        storage.save_user(
            User(
                username="ana",
                password_hash=hash_password(PASSWORD),
                role=Role.ADMIN,
                created_at=NOW,
            )
        )
        first = new_article(
            "tides", ArticleContent(title="Tides", summary="S", body_markdown="Body."), now=NOW
        )
        first.set_translation(Language.PT_PT, ArticleContent(title="Marés"))
        storage.save_article(first)
        for number in range(articles - 1):
            extra = new_article(
                f"entry-{number:03d}", ArticleContent(title=f"Entry {number:03d}"), now=NOW
            )
            # In review with translations missing: the publish gate has
            # something to report, so the findings table is a real
            # collection too.
            extra.status = ContentStatus.REVIEW
            storage.save_article(extra)
            storage.save_page(
                new_page(
                    f"page-{number:03d}",
                    PageContent(title=f"Page {number:03d}", slug=f"page-{number:03d}"),
                    now=NOW,
                )
            )
        page = new_page("crew", PageContent(title="The crew", slug="crew"), now=NOW)
        page.sections.append(
            Section(key="hero", kind="hero", source=SectionContent(fields={"heading": "Hi"}))
        )
        storage.save_page(page)
        storage.save_media_asset(
            MediaAsset(
                id="chart",
                path="images/chart.svg",
                mime_type="image/svg+xml",
                width=1200,
                height=800,
                alt={Language.EN: "A chart"},
            )
        )
        storage.save_menu_item(
            MenuItem(id="home", url="/", position=1, labels={Language.EN: "Home"})
        )
    return url


@contextmanager
def _client(tmp_path: Path, **seed: object) -> Iterator[TestClient]:
    """A signed-in panel over a seeded project — the suite renders real
    screens through the real app, never a fixture of HTML."""
    tmp_path.mkdir(parents=True, exist_ok=True)
    url = _seed(tmp_path, **seed)  # type: ignore[arg-type]
    app = create_app(
        AdminSettings(storage_url=url, media_dir=tmp_path / "media", project_dir=tmp_path)
    )
    with TestClient(app, base_url="https://testserver") as client:
        form = client.get("/login")
        client.post(
            "/login",
            data={
                "username": "ana",
                "password": PASSWORD,
                "login_csrf": form.cookies["__Host-sardine_login_csrf"],
            },
        )
        yield client


def test_the_conformance_version_is_one() -> None:
    assert UI_CONFORMANCE_VERSION == 1


@pytest.mark.parametrize("path", [*snapshot_paths(), *ENTITY_PATHS])
@pytest.mark.parametrize(("check_name", "check"), conformance_checks())
def test_every_screen_conforms(tmp_path: Path, path: str, check_name: str, check: object) -> None:
    with _client(tmp_path) as client:
        response = client.get(path)
        assert response.status_code == 200, f"{path}: {response.status_code}"
        check(parse(path, response.text))  # type: ignore[operator]


def test_the_suite_covers_every_registered_screen() -> None:
    """The coverage list is the registry — a new screen cannot ship
    outside the suite."""
    assert snapshot_paths(), "the screen registry is empty"


@pytest.mark.parametrize("path", ("/articles", "/pages", "/publishing"))
def test_large_collections_paginate(tmp_path: Path, path: str) -> None:
    """DS-19 with a collection larger than the page size."""
    with _client(tmp_path, articles=PAGE_SIZE + 12) as client:
        page = parse(path, client.get(path).text)
        check_pagination_bounds_large_collections(page, PAGE_SIZE)
        assert page.paginations >= 1, f"{path}: no pagination on a large collection"


def test_screens_do_not_grow_with_the_language_count(tmp_path: Path) -> None:
    """DS-8, measured the way the rule states it: the number of controls
    a user can reach without opening a disclosure is the same with two
    languages and with thirty."""
    from cms_core.language_packs import LanguagePack, register_language_pack

    many = ["pt-pt", "es", "fr", "de", "it", "id"]
    for number in range(24):
        tag = f"zz-{number:02d}"
        register_language_pack(LanguagePack(tag=tag, native_name=f"Fixture {number:02d}"))
        many.append(tag)
    assert len(many) == 30

    def controls(languages: list[str], directory: Path, path: str) -> int:
        toml = PROJECT_TOML.replace(
            'languages = ["pt-pt", "es", "fr", "de"]',
            "languages = [" + ", ".join(f'"{tag}"' for tag in languages) + "]",
        )
        with _client(directory, toml=toml) as client:
            return parse(path, client.get(path).text).visible_controls

    for path in ("/menu?item=home", "/menu?new=1"):
        few = controls(["pt-pt"], tmp_path / "few", path)
        lots = controls(many, tmp_path / "many", path)
        assert lots == few, f"{path}: {few} controls with 2 languages, {lots} with 30"


# --- The suite has teeth: each rule catches its own defect ------------

DEFECTS = (
    (
        "one-h1-carrying-only-the-title",
        "<h1>about <span class='badge'>published</span></h1>",
    ),
    ("one-h1-carrying-only-the-title", "<h1>one</h1><h1>two</h1>"),
    ("breadcrumbs", "<h1>Screen</h1><p>no breadcrumb anywhere</p>"),
    (
        "empty-states-offer-the-next-action",
        "<nav class='breadcrumb'></nav><h1>S</h1>"
        "<div class='card admin-empty-state'><p>Nothing here.</p></div>",
    ),
    (
        "at-most-one-open-disclosure",
        "<nav class='breadcrumb'></nav><h1>S</h1>"
        "<details open><summary>a</summary></details>"
        "<details open><summary>b</summary></details>",
    ),
    (
        "datatable-order",
        "<nav class='breadcrumb'></nav><h1>S</h1>"
        "<table><tbody><tr><td>row</td></tr></tbody></table>"
        "<p class='admin-summary-line'>Showing 1-1 of 1</p>",
    ),
    (
        "datatable-order",
        "<nav class='breadcrumb'></nav><h1>S</h1>"
        "<p class='admin-summary-line'>Showing 1-1 of 1</p>"
        "<form class='admin-filter-bar'></form>"
        "<table><tbody><tr><td>row</td></tr></tbody></table>",
    ),
)


@pytest.mark.parametrize(("check_name", "html"), DEFECTS)
def test_each_check_catches_its_defect(check_name: str, html: str) -> None:
    check = dict(conformance_checks())[check_name]
    with pytest.raises(AssertionError):
        check(parse("/fixture", html))


def test_pagination_check_catches_an_unbounded_collection() -> None:
    rows = "".join("<tr><td>row</td></tr>" for _ in range(40))
    page = parse("/fixture", f"<table><tbody>{rows}</tbody></table>")
    with pytest.raises(AssertionError):
        check_pagination_bounds_large_collections(page, PAGE_SIZE)


def test_the_language_scale_measure_ignores_closed_disclosures() -> None:
    """The DS-8 measure counts what a user can reach: a control behind a
    closed disclosure is not visible, one in an open section is."""
    body = "<input name='a'><details{open}><summary>s</summary><input name='b'></details>"
    closed = parse("/x", body.format(open=""))
    opened = parse("/x", body.format(open=" open"))
    assert closed.visible_controls == 1
    assert opened.visible_controls == 2
