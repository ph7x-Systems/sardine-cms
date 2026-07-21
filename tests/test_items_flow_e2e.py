"""The ADR-0037 behavioral proof (#126): an editor's complete items flow.

Every step drives the admin's real HTTP surface — no model shortcuts:
open the page, edit items past the retired cap, save, translate the
second language side by side, publish through the workflow, and read
the eighth FAQ item in the final built HTML of BOTH bundled themes.
"""

from datetime import UTC, datetime
from pathlib import Path

from cms_admin import AdminSettings, create_app
from cms_admin.security import hash_password
from cms_build import build_site, create_theme
from cms_core import (
    ContentStatus,
    Language,
    PageContent,
    Role,
    Section,
    SectionContent,
    User,
    create_storage,
    new_page,
)
from cms_validation import SiteContent
from fastapi import FastAPI
from fastapi.testclient import TestClient

PASSWORD = "correct horse battery staple"
NOW = datetime(2026, 7, 21, 9, 0, tzinfo=UTC)

QUESTIONS = [f"Question number {n}?" for n in range(1, 8)]
ANSWERS = [f"Answer number {n}." for n in range(1, 8)]


def _app(tmp_path: Path) -> "FastAPI":
    # A real project file: the publish gate and the editors follow ITS
    # language set (pt-pt as the only target), like any real site.
    (tmp_path / "sardine.toml").write_text(
        '[site]\nname = "Flow"\nbase_url = "https://flow.example"\nlanguages = ["pt-pt"]\n',
        encoding="utf-8",
    )
    url = f"sqlite:///{tmp_path / 'content.db'}"
    page = new_page("faq", PageContent(title="FAQ", slug="faq"), now=NOW)
    page.sections.append(
        Section(
            key="questions",
            kind="faq",
            source=SectionContent(
                fields={"heading": "Questions"},
                items=[
                    {"question": q, "answer": a} for q, a in zip(QUESTIONS, ANSWERS, strict=True)
                ],
            ),
        )
    )
    with create_storage(url) as storage:
        storage.save_user(
            User(
                username="ana",
                password_hash=hash_password(PASSWORD),
                role=Role.ADMIN,
                created_at=NOW,
            )
        )
        storage.save_page(page)
    return create_app(
        AdminSettings(storage_url=url, media_dir=tmp_path / "media", project_dir=tmp_path)
    )


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


def test_the_eighth_faq_item_survives_the_whole_editorial_flow(tmp_path: Path) -> None:
    app = _app(tmp_path)
    with TestClient(app, base_url="https://testserver") as client:
        csrf = _sign_in(client)

        # 1. The editor opens the page and its section editor.
        assert "questions" in client.get("/pages/faq").text
        editor = client.get("/pages/faq/sections/questions").text
        assert "Question number 7?" in editor

        # 2-3. Adds the eighth item (past the retired q6 cap) and edits
        #      the first, then saves.
        questions = ["Question number 1, sharpened?", *QUESTIONS[1:], "Question number 8?"]
        answers = [ANSWERS[0], *ANSWERS[1:], "Answer number 8."]
        saved = client.post(
            "/pages/faq/sections/questions",
            data={
                "csrf_token": csrf,
                "field_name": ["heading"],
                "field_value": ["Questions"],
                "item_question": questions,
                "item_answer": answers,
                "media": "",
            },
            follow_redirects=False,
        )
        assert saved.status_code == 303

        # 4. Translates the page and every item into the second language.
        assert (
            client.post(
                "/pages/faq/translations/pt-pt",
                data={
                    "csrf_token": csrf,
                    "title": "Perguntas",
                    "description": "",
                    "slug": "perguntas",
                    "body_markdown": "",
                },
                follow_redirects=False,
            ).status_code
            == 303
        )
        translation_editor = client.get("/pages/faq/sections/questions/translations/pt-pt").text
        assert "Question number 8?" in translation_editor  # source beside the inputs
        assert (
            client.post(
                "/pages/faq/sections/questions/translations/pt-pt",
                data={
                    "csrf_token": csrf,
                    "field__heading": "Perguntas",
                    "item_question": [f"Pergunta {n}?" for n in range(1, 9)],
                    "item_answer": [f"Resposta {n}." for n in range(1, 9)],
                    "media": "",
                },
                follow_redirects=False,
            ).status_code
            == 303
        )

        # 5. Publishes through the workflow: draft -> review -> published.
        #    The publish gate runs — parity with pt-pt must genuinely hold.
        for target in ("review", "published"):
            response = client.post(
                "/pages/faq/status",
                data={"csrf_token": csrf, "to": target},
                follow_redirects=False,
            )
            assert response.status_code == 303, (target, response.text[:300])

    # 6-7. The final built HTML carries the eighth item — in both themes,
    #      in both languages.
    with create_storage(f"sqlite:///{tmp_path / 'content.db'}") as storage:
        page = storage.load_page("faq")
    assert page is not None and page.status is ContentStatus.PUBLISHED
    from cms_build import SiteConfig

    config = SiteConfig(name="Flow", base_url="https://flow.example", languages=(Language.PT_PT,))
    for theme_name in ("default", "ph7x-reference"):
        artifact = build_site(
            config,
            SiteContent(pages=[page], articles=[], media=[]),
            theme=create_theme(theme_name),
            now=NOW,
        )
        source_html = artifact.files["faq/index.html"].decode("utf-8")
        assert "Question number 8?" in source_html, theme_name
        assert "Question number 1, sharpened?" in source_html, theme_name
        translated_html = artifact.files["pt-pt/perguntas/index.html"].decode("utf-8")
        assert "Pergunta 8?" in translated_html, theme_name
