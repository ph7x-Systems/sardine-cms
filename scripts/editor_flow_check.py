"""The #127 editorial-flow check: the landing-page scenario, mechanized.

Self-contained and reproducible by anyone and by CI: it creates a fresh
monolingual project and admin account in a temporary directory, serves
the real admin app, drives the complete scenario through the real UI
with headless Chromium — sign in, create a page, add hero/story/FAQ/CTA
from the block gallery, fill fields, Markdown body and three FAQ items,
publish through the workflow — then builds the site and asserts the
content reached the final HTML. Exit 1 on any failed step.

This is the mechanical proof that no step of the scenario is blocked.
It does NOT satisfy the 15-minute usability metric, which requires a
real non-technical tester (ROADMAP measurement rules).

Usage:
    python scripts/editor_flow_check.py
"""

import socket
import tempfile
import threading
import time
from datetime import UTC, datetime
from pathlib import Path

import uvicorn
from playwright.sync_api import sync_playwright

USERNAME = "owner"
PASSWORD = "a sardine in space wins"


def _free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


def _prepare_project(directory: Path) -> None:
    (directory / "sardine.toml").write_text(
        '[site]\nname = "Flow check"\nbase_url = "https://flow.example"\nlanguages = []\n',
        encoding="utf-8",
    )
    from cms_admin.security import hash_password
    from cms_core import Role, User, create_storage

    with create_storage(f"sqlite:///{directory / 'content.sqlite3'}") as storage:
        storage.save_user(
            User(
                username=USERNAME,
                password_hash=hash_password(PASSWORD),
                role=Role.ADMIN,
                created_at=datetime.now(tz=UTC),
            )
        )


def _serve(directory: Path, port: int) -> uvicorn.Server:
    from cms_admin import AdminSettings, create_app

    app = create_app(
        AdminSettings(
            storage_url=f"sqlite:///{directory / 'content.sqlite3'}",
            media_dir=directory / "media",
            project_dir=directory,
            cookie_secure=False,
        )
    )
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
    threading.Thread(target=server.run, daemon=True).start()
    deadline = time.monotonic() + 15
    while not server.started:
        if time.monotonic() > deadline:
            raise RuntimeError("admin server did not start")
        time.sleep(0.05)
    return server


def _drive(base: str) -> list[str]:
    steps: list[str] = []

    def step(name: str) -> None:
        steps.append(name)
        print(f"  ok: {name}")

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page()

        page.goto(f"{base}/login")
        page.fill("#username", USERNAME)
        page.fill("#password", PASSWORD)
        page.click("button[type=submit]")
        page.wait_for_url(f"{base}/")
        step("signed in")

        page.goto(f"{base}/pages/new")
        page.fill("#id", "landing")
        page.fill("#title", "A nossa empresa")
        page.fill("#slug", "landing")
        page.click("form.admin-form button[type=submit]")
        page.wait_for_url(f"{base}/pages/landing")
        step("page created")

        for kind in ("hero", "story", "faq", "cta"):
            page.goto(f"{base}/pages/landing")
            page.click(f".admin-block-gallery form:has(input[value='{kind}']) button")
            page.wait_for_url(f"{base}/pages/landing/sections/{kind}")
            step(f"block added from the gallery: {kind}")

        page.goto(f"{base}/pages/landing/sections/hero")
        page.fill("input[name='field_value'] >> nth=0", "Fazemos sites que ficam")
        page.click("form.admin-form button[type=submit]")
        step("hero filled")

        # The Markdown widget (EasyMDE over CodeMirror) owns the
        # textarea; typing goes through its editor surface.
        page.goto(f"{base}/pages/landing/sections/story")
        page.evaluate(
            "document.querySelector('.EasyMDEContainer .CodeMirror')"
            ".CodeMirror.setValue('Uma equipa pequena, um **compromisso** grande.')"
        )
        page.fill("input[name='field_value'] >> nth=0", "Quem somos")
        page.click("form.admin-form button[type=submit]")
        step("story filled through the Markdown widget")

        page.goto(f"{base}/pages/landing/sections/faq")
        page.locator("input[name='item_question']").nth(0).fill("Quanto custa?")
        page.locator("input[name='item_answer']").nth(0).fill("Depende do site.")
        page.locator("input[name='item_question']").nth(1).fill("Quanto tempo demora?")
        page.locator("input[name='item_answer']").nth(1).fill("Duas a quatro semanas.")
        page.click("form.admin-form button[type=submit]")
        page.goto(f"{base}/pages/landing/sections/faq")
        page.locator("input[name='item_question']").nth(2).fill("Fazem manutencao?")
        page.locator("input[name='item_answer']").nth(2).fill("Sim, com plano mensal.")
        page.click("form.admin-form button[type=submit]")
        step("faq: three items")

        page.goto(f"{base}/pages/landing/sections/cta")
        names = page.locator("input[name='field_name']")
        values = page.locator("input[name='field_value']")
        wanted = {"heading": "Vamos falar?", "button": "Contactar", "url": "/contacto/"}
        for index in range(names.count()):
            value = wanted.get(names.nth(index).input_value())
            if value:
                values.nth(index).fill(value)
        page.click("form.admin-form button[type=submit]")
        step("cta filled")

        for target in ("review", "published"):
            page.goto(f"{base}/pages/landing")
            selector = (
                f"form[action='/pages/landing/status']"
                f":has(input[name='to'][value='{target}']) button"
            )
            page.click(selector)
            page.wait_for_load_state()
            step(f"workflow -> {target}")

        browser.close()
    return steps


def _assert_built(directory: Path) -> None:
    from cms_build import build_site
    from cms_cli.project import load_project
    from cms_core import create_storage
    from cms_validation import SiteContent

    project = load_project(directory)
    with create_storage(f"sqlite:///{directory / 'content.sqlite3'}") as storage:
        page = storage.load_page("landing")
    assert page is not None, "the landing page was not stored"
    artifact = build_site(project.site, SiteContent(pages=[page], articles=[], media=[]))
    html = artifact.files["landing/index.html"].decode("utf-8")
    for expected in (
        "Fazemos sites que ficam",
        "<strong>compromisso</strong>",
        "Quanto custa?",
        "Fazem manutencao?",
        "Vamos falar?",
    ):
        assert expected in html, f"missing from the built page: {expected!r}"
    print("  ok: built HTML carries every block, Markdown rendered")


def main() -> int:
    with tempfile.TemporaryDirectory() as scratch:
        directory = Path(scratch)
        _prepare_project(directory)
        port = _free_port()
        server = _serve(directory, port)
        try:
            started = time.monotonic()
            steps = _drive(f"http://127.0.0.1:{port}")
            elapsed = time.monotonic() - started
        finally:
            server.should_exit = True
        _assert_built(directory)
        print(f"OK: {len(steps)} steps + build assertion in {elapsed:.1f}s (mechanical)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
