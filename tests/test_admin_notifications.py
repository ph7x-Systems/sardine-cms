"""Editorial notifications (ADR-0032 phase 2): two events, fire-and-forget."""

import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from cms_admin import AdminSettings, create_app
from cms_admin.security import hash_password
from cms_core import (
    ArticleContent,
    ContentStatus,
    Language,
    Role,
    User,
    create_storage,
    new_article,
)
from fastapi import FastAPI
from fastapi.testclient import TestClient

PASSWORD = "correct horse battery staple"
NOW = datetime(2026, 7, 21, tzinfo=UTC)


class CapturingMailer:
    def __init__(self) -> None:
        self.sent: list[tuple[str, str, str]] = []

    def send(self, to: str, subject: str, body: str) -> None:
        self.sent.append((to, subject, body))


def _app(tmp_path: Path) -> FastAPI:
    """ana admin (actor), rui reviewer PT-PT with email, eva editor with
    email, leo publisher WITHOUT email — plus one draft article whose
    newest revision is authored by eva."""
    url = f"sqlite:///{tmp_path / 'content.db'}"
    with create_storage(url) as storage:
        accounts = (
            ("ana", Role.ADMIN, "ana@example.com", None),
            ("rui", Role.REVIEWER, "rui@example.com", Language.PT_PT),
            ("eva", Role.EDITOR, "eva@example.com", None),
            ("leo", Role.PUBLISHER, None, None),
        )
        for name, role, email, language in accounts:
            storage.save_user(
                User(
                    username=name,
                    password_hash=hash_password(PASSWORD),
                    role=role,
                    created_at=NOW,
                    email=email,
                    language=language,
                )
            )
        article = new_article(
            "launch-notes",
            ArticleContent(title="Launch notes", summary="S", body_markdown="B"),
            now=NOW,
        )
        storage.save_article(article)
        storage.save_revision("article", "launch-notes", "eva", article.model_dump_json(), NOW)
    app = create_app(
        AdminSettings(storage_url=url, media_dir=tmp_path / "media", publish_gate=False)
    )
    app.state.mailer = CapturingMailer()
    return app


def _sign_in(client: TestClient) -> str:
    client.get("/login")
    csrf = client.cookies["__Host-sardine_login_csrf"]
    client.post("/login", data={"username": "ana", "password": PASSWORD, "login_csrf": csrf})
    return client.get("/articles/launch-notes").text


def _csrf(page: str) -> str:
    import re

    match = re.search(r'name="csrf_token" value="([^"]+)"', page)
    assert match
    return match.group(1)


def _transition(client: TestClient, to: str) -> Any:
    page = client.get("/articles/launch-notes").text
    return client.post(
        "/articles/launch-notes/status",
        data={"to": to, "csrf_token": _csrf(page)},
        follow_redirects=False,
    )


def _wait_for_mail(app: FastAPI, count: int) -> None:
    for _ in range(200):
        if len(app.state.mailer.sent) >= count:
            return
        time.sleep(0.01)
    raise AssertionError(f"expected {count} message(s), got {app.state.mailer.sent}")


def test_review_request_mails_reviewers_and_above_with_addresses(tmp_path: Path) -> None:
    app = _app(tmp_path)
    with TestClient(app, base_url="https://testserver") as client:
        _sign_in(client)
        answer = _transition(client, "review")
        assert answer.status_code == 303
        _wait_for_mail(app, 1)
    recipients = sorted(to for to, _, _ in app.state.mailer.sent)
    # rui (reviewer, address) — yes. leo (publisher, no address) — no.
    # eva (editor) — below the ladder. ana — the actor.
    assert recipients == ["rui@example.com"]
    _, subject, body = app.state.mailer.sent[0]
    # rui's stored language is PT-PT
    assert subject == "Revisão pedida: Launch notes"
    assert "ana" in body and "/articles/launch-notes" in body


def test_publishing_mails_the_last_editing_author(tmp_path: Path) -> None:
    app = _app(tmp_path)
    with TestClient(app, base_url="https://testserver") as client:
        _sign_in(client)
        _transition(client, "review")
        _wait_for_mail(app, 1)
        app.state.mailer.sent.clear()
        answer = _transition(client, "published")
        assert answer.status_code == 303
        _wait_for_mail(app, 1)
    to, subject, _ = app.state.mailer.sent[0]
    assert to == "eva@example.com"  # newest revision author other than ana
    assert subject == "Published: Launch notes"


def test_no_mailer_means_no_notifications_and_no_errors(tmp_path: Path) -> None:
    app = _app(tmp_path)
    app.state.mailer = None
    with TestClient(app, base_url="https://testserver") as client:
        _sign_in(client)
        assert _transition(client, "review").status_code == 303
        assert _transition(client, "published").status_code == 303

    url = app.state.settings.storage_url
    with create_storage(url) as storage:
        article = storage.load_article("launch-notes")
    assert article is not None and article.status is ContentStatus.PUBLISHED
