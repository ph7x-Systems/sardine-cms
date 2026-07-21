"""The editorial calendar (#132): the month as the panel sees time."""

from datetime import UTC, datetime
from pathlib import Path

from cms_admin import AdminSettings, create_app
from cms_admin.security import hash_password
from cms_core import ContentStatus, Role, User, create_storage
from cms_core.models import Article, ArticleContent, new_article
from fastapi import FastAPI
from fastapi.testclient import TestClient

PASSWORD = "correct horse battery staple"
NOW = datetime(2026, 7, 21, tzinfo=UTC)


def _app(tmp_path: Path) -> FastAPI:
    url = f"sqlite:///{tmp_path / 'content.db'}"
    with create_storage(url) as storage:
        storage.save_user(
            User(
                username="ana",
                password_hash=hash_password(PASSWORD),
                role=Role.EDITOR,
                created_at=NOW,
            )
        )
        published = new_article(
            "launched",
            ArticleContent(title="Launched note", summary="S", body_markdown="B"),
            now=datetime(2030, 3, 5, 9, 30, tzinfo=UTC),
        )
        published.status = ContentStatus.PUBLISHED
        storage.save_article(published)
        scheduled = new_article(
            "upcoming",
            ArticleContent(title="Upcoming note", summary="S", body_markdown="B"),
            now=NOW,
        )
        scheduled.status = ContentStatus.PUBLISHED
        scheduled.publish_at = datetime(2030, 3, 18, 14, 45, tzinfo=UTC)
        storage.save_article(scheduled)
        draft = new_article(
            "invisible",
            ArticleContent(title="Unscheduled draft", summary="S", body_markdown="B"),
            now=datetime(2030, 3, 9, tzinfo=UTC),
        )
        storage.save_article(draft)
    return create_app(AdminSettings(storage_url=url, media_dir=tmp_path / "media"))


def _sign_in(client: TestClient) -> str:
    form = client.get("/login")
    client.post(
        "/login",
        data={
            "username": "ana",
            "password": PASSWORD,
            "login_csrf": form.cookies["__Host-sardine_login_csrf"],
        },
    )
    return client.get("/").text.split('name="csrf_token" value="')[1].split('"')[0]


def test_month_view_places_entries_on_their_utc_days(tmp_path: Path) -> None:
    with TestClient(_app(tmp_path), base_url="https://testserver") as client:
        _sign_in(client)
        month = client.get("/calendar?month=2030-03").text
    assert "Launched note" in month  # published on its creation day
    assert "Upcoming note" in month and "scheduled" in month
    assert "Unscheduled draft" not in month  # drafts appear only when scheduled
    assert 'data-calendar-day="2030-03-05"' in month
    assert "2030-02" in month and "2030-04" in month  # month navigation


def test_reschedule_moves_the_day_and_keeps_the_time(tmp_path: Path) -> None:
    with TestClient(_app(tmp_path), base_url="https://testserver") as client:
        csrf = _sign_in(client)
        response = client.post(
            "/calendar/reschedule",
            data={
                "csrf_token": csrf,
                "kind": "article",
                "entity_id": "upcoming",
                "day": "2030-03-25",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303
    with create_storage(f"sqlite:///{tmp_path / 'content.db'}") as storage:
        moved = storage.load_article("upcoming")
    assert isinstance(moved, Article)
    assert moved.publish_at == datetime(2030, 3, 25, 14, 45, tzinfo=UTC)


def test_reschedule_refuses_history_and_bad_input(tmp_path: Path) -> None:
    with TestClient(_app(tmp_path), base_url="https://testserver") as client:
        csrf = _sign_in(client)
        history = client.post(
            "/calendar/reschedule",
            data={
                "csrf_token": csrf,
                "kind": "article",
                "entity_id": "launched",
                "day": "2030-03-25",
            },
        )
        assert history.status_code == 400  # published history never moves
        bad_month = client.get("/calendar?month=not-a-month")
        assert bad_month.status_code == 400


def test_scheduled_unpublish_drops_the_entry_deterministically(tmp_path: Path) -> None:
    """#133: the symmetric end of the window — a passed unpublish_at
    takes the entry out of the next build, same clock, same determinism."""
    from cms_build import SiteConfig, build_site
    from cms_validation import SiteContent

    article = new_article(
        "campaign",
        ArticleContent(title="Campaign page entry", summary="S", body_markdown="B"),
        now=datetime(2030, 1, 1, tzinfo=UTC),
    )
    article.status = ContentStatus.PUBLISHED
    article.unpublish_at = datetime(2030, 6, 1, tzinfo=UTC)
    config = SiteConfig(name="T", base_url="https://t.example", languages=())
    content = SiteContent(articles=[article], pages=[], media=[])

    during = build_site(config, content, now=datetime(2030, 5, 1, tzinfo=UTC))
    assert "blog/campaign/index.html" in during.files
    after = build_site(config, content, now=datetime(2030, 6, 2, tzinfo=UTC))
    assert "blog/campaign/index.html" not in after.files
    # deterministic: the same clock always gives the same answer
    assert (
        build_site(config, content, now=datetime(2030, 6, 2, tzinfo=UTC)).digest() == after.digest()
    )


def test_contradictory_window_is_refused(tmp_path: Path) -> None:
    import pytest as pytest_module
    from cms_core.models import Article

    article = new_article(
        "window", ArticleContent(title="W", summary="S", body_markdown="B"), now=NOW
    )
    article.publish_at = datetime(2030, 6, 1, tzinfo=UTC)
    with pytest_module.raises(ValueError, match="unpublish_at"):
        Article.model_validate(
            {**article.model_dump(), "unpublish_at": datetime(2030, 5, 1, tzinfo=UTC)}
        )


def test_unpublish_at_round_trips_storage_and_editor(tmp_path: Path) -> None:
    with TestClient(_app(tmp_path), base_url="https://testserver") as client:
        csrf = _sign_in(client)
        editor = client.get("/articles/upcoming").text
        assert 'name="unpublish_at"' in editor
        response = client.post(
            "/articles/upcoming",
            data={
                "csrf_token": csrf,
                "title": "Upcoming note",
                "summary": "S",
                "body_markdown": "B",
                "slug": "",
                "category": "",
                "cover": "",
                "tags": "",
                "publish_at": "2030-03-18T14:45",
                "unpublish_at": "2030-09-30T12:00",
                "author": "",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303, response.text[:300]
    with create_storage(f"sqlite:///{tmp_path / 'content.db'}") as storage:
        stored = storage.load_article("upcoming")
    assert stored is not None
    assert stored.unpublish_at == datetime(2030, 9, 30, 12, 0, tzinfo=UTC)
