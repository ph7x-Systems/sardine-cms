"""On-publish webhooks (ADR-0036): signed, retried, optional."""

import http.server
import json
import re
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, ClassVar

import pytest
from cms_admin import AdminSettings, create_app
from cms_admin.security import hash_password
from cms_admin.webhooks import signature, validate_webhook_settings
from cms_core import ArticleContent, Role, User, create_storage, new_article
from fastapi import FastAPI
from fastapi.testclient import TestClient

PASSWORD = "correct horse battery staple"
NOW = datetime(2026, 7, 21, tzinfo=UTC)
SECRET = "hook-secret"


class _Receiver(http.server.BaseHTTPRequestHandler):
    fail_first: ClassVar[int] = 0
    received: ClassVar[list[tuple[dict[str, str], bytes]]] = []

    def do_POST(self) -> None:
        body = self.rfile.read(int(self.headers["Content-Length"]))
        if _Receiver.fail_first > 0:
            _Receiver.fail_first -= 1
            self.send_response(500)
            self.end_headers()
            return
        _Receiver.received.append((dict(self.headers), body))
        self.send_response(204)
        self.end_headers()

    def log_message(self, *args: object) -> None:
        pass


@pytest.fixture()
def receiver() -> Any:
    _Receiver.received = []
    _Receiver.fail_first = 0
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _Receiver)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_address[1]}/hook"
    server.shutdown()


def _app(tmp_path: Path, url: str | None) -> FastAPI:
    storage_url = f"sqlite:///{tmp_path / 'content.db'}"
    with create_storage(storage_url) as storage:
        storage.save_user(
            User(
                username="ana",
                password_hash=hash_password(PASSWORD),
                role=Role.ADMIN,
                created_at=NOW,
            )
        )
        article = new_article(
            "launch-notes",
            ArticleContent(title="Launch notes", summary="S", body_markdown="B"),
            now=NOW,
        )
        storage.save_article(article)
    return create_app(
        AdminSettings(
            storage_url=storage_url,
            media_dir=tmp_path / "media",
            publish_gate=False,
            webhook_url=url,
            webhook_secret=SECRET if url else None,
        )
    )


def _transition(client: TestClient, to: str) -> None:
    page = client.get("/articles/launch-notes").text
    csrf = re.search(r'name="csrf_token" value="([^"]+)"', page).group(1)  # type: ignore[union-attr]
    answer = client.post(
        "/articles/launch-notes/status",
        data={"to": to, "csrf_token": csrf},
        follow_redirects=False,
    )
    assert answer.status_code == 303


def _sign_in(client: TestClient) -> None:
    client.get("/login")
    csrf = client.cookies["__Host-sardine_login_csrf"]
    client.post("/login", data={"username": "ana", "password": PASSWORD, "login_csrf": csrf})


def _wait_for(count: int) -> None:
    import time

    for _ in range(400):
        if len(_Receiver.received) >= count:
            return
        time.sleep(0.01)
    raise AssertionError(f"expected {count} delivery(ies), got {len(_Receiver.received)}")


def test_publish_and_unpublish_ring_the_doorbell_signed(tmp_path: Path, receiver: str) -> None:
    app = _app(tmp_path, receiver)
    with TestClient(app, base_url="https://testserver") as client:
        _sign_in(client)
        _transition(client, "review")  # not a public change: no delivery
        _transition(client, "published")
        _wait_for(1)
        _transition(client, "draft")  # unpublish
        _wait_for(2)
    events = []
    for headers, body in _Receiver.received:
        assert headers["X-Sardine-Signature"] == signature(SECRET, body)
        payload = json.loads(body)
        assert payload["entity"] == {"kind": "article", "id": "launch-notes"}
        events.append(payload["event"])
    assert events == ["published", "unpublished"]


def test_failed_deliveries_retry_with_backoff(
    tmp_path: Path, receiver: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    import cms_admin.webhooks as hooks

    monkeypatch.setattr(hooks, "BACKOFF_SECONDS", (0.01, 0.02, 0.03))
    _Receiver.fail_first = 2
    app = _app(tmp_path, receiver)
    with TestClient(app, base_url="https://testserver") as client:
        _sign_in(client)
        _transition(client, "review")
        _transition(client, "published")
        _wait_for(1)  # third attempt landed
    assert len(_Receiver.received) == 1


def test_without_configuration_nothing_is_sent(tmp_path: Path) -> None:
    _Receiver.received = []
    app = _app(tmp_path, None)
    with TestClient(app, base_url="https://testserver") as client:
        _sign_in(client)
        _transition(client, "review")
        _transition(client, "published")
    assert _Receiver.received == []


def test_unsigned_or_plain_http_configuration_fails_startup() -> None:
    try:
        validate_webhook_settings("https://ci.example/hook", None)
        raise AssertionError("expected ValueError")
    except ValueError as error:
        assert "SECRET" in str(error)
    try:
        validate_webhook_settings("http://ci.example/hook", "s")
        raise AssertionError("expected ValueError")
    except ValueError as error:
        assert "https" in str(error)
    validate_webhook_settings("http://127.0.0.1:9/hook", "s")  # loopback dev is fine
    validate_webhook_settings(None, None)  # off is fine
