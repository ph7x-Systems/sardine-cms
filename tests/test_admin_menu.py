"""The menu manager, rebuilt as the design-system golden screen
(ADR-0055): task-first master-detail, editor only on selection,
translations and technical fields behind closed disclosures, empty
state with the next action."""

from datetime import UTC, datetime
from pathlib import Path

from cms_admin import AdminSettings, create_app
from cms_admin.security import hash_password
from cms_core import Role, User, create_storage
from fastapi import FastAPI
from fastapi.testclient import TestClient

PASSWORD = "correct horse battery staple"
NOW = datetime(2026, 7, 19, tzinfo=UTC)


def _app(tmp_path: Path, role: Role = Role.PUBLISHER) -> FastAPI:
    url = f"sqlite:///{tmp_path / 'content.db'}"
    with create_storage(url) as storage:
        storage.save_user(
            User(username="ana", password_hash=hash_password(PASSWORD), role=role, created_at=NOW)
        )
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


def test_the_task_flow_open_add_select_edit(tmp_path: Path) -> None:
    with TestClient(_app(tmp_path), base_url="https://testserver") as client:
        csrf = _sign_in(client)

        # DS-7/DS-16: the empty screen is an empty state with the next
        # action — no editor form is rendered until asked for.
        empty = client.get("/menu").text
        assert "No custom items yet" in empty
        assert "Add custom item" in empty
        assert 'name="url"' not in empty

        # The editor appears on explicit intent.
        editor = client.get("/menu?new=1").text
        assert 'name="url"' in editor
        assert "New item" in editor

        # The id is technical: omitted, it derives from the label.
        saved = client.post(
            "/menu",
            data={
                "csrf_token": csrf,
                "url": "/docs/",
                "position": "1",
                "label_en": "Docs",
                "label_pt-pt": "Documentação",
            },
            follow_redirects=False,
        )
        assert saved.status_code == 303
        assert saved.headers["location"] == "/menu?item=docs"

        # The list shows the source-language label; the translation
        # lives in the item's editor, behind the disclosure.
        page = client.get("/menu").text
        assert "Docs" in page
        assert "Documentação" not in page
        detail = client.get("/menu?item=docs").text
        assert 'value="Documentação"' in detail
        assert "Translations · 1/" in detail

        # DS-17: every disclosure ships closed.
        assert "<details" in detail
        assert " open>" not in detail and " open >" not in detail

        bad = client.post(
            "/menu", data={"csrf_token": csrf, "id": "Bad Id!", "url": "/x/", "position": "1"}
        )
        assert bad.status_code == 422

        removed = client.post(
            "/menu/docs/delete", data={"csrf_token": csrf}, follow_redirects=False
        )
        assert removed.status_code == 303
        assert "No custom items yet" in client.get("/menu").text


def test_the_list_is_the_ordering_surface(tmp_path: Path) -> None:
    with TestClient(_app(tmp_path), base_url="https://testserver") as client:
        csrf = _sign_in(client)
        for position, (item_id, url) in enumerate(
            (("home", "/"), ("about", "/about/"), ("blog", "/blog/")), start=1
        ):
            client.post(
                "/menu",
                data={
                    "csrf_token": csrf,
                    "id": item_id,
                    "url": url,
                    "position": str(position),
                    "label_en": item_id.title(),
                },
            )
        page = client.get("/menu").text
        assert page.index("Home") < page.index("About") < page.index("Blog")

        moved = client.post(
            "/menu/blog/move",
            data={"csrf_token": csrf, "direction": "up"},
            follow_redirects=False,
        )
        assert moved.status_code == 303
        page = client.get("/menu").text
        assert page.index("Home") < page.index("Blog") < page.index("About")

        unknown = client.post("/menu/nowhere/move", data={"csrf_token": csrf, "direction": "up"})
        assert unknown.status_code == 404


def test_menu_writes_need_the_publisher_role(tmp_path: Path) -> None:
    with TestClient(_app(tmp_path, role=Role.EDITOR), base_url="https://testserver") as client:
        csrf = _sign_in(client)
        assert client.get("/menu").status_code == 200  # anyone signed in can look
        denied = client.post(
            "/menu", data={"csrf_token": csrf, "id": "x", "url": "/", "position": "1"}
        )
        assert denied.status_code == 403
