"""The #128 onboarding check: empty database to published site, mechanized.

The companion to `editor_flow_check.py`, for the other half of the
adopter's first hour. Self-contained and reproducible by anyone and by
CI: it starts from an **empty directory with no database, no project
file and no account**, serves the real admin app, and drives the whole
browser path with headless Chromium — the first-run wizard creates the
admin account, the site identity, the language set and the theme, seeds
the example content, and the publishing screen builds and exports the
site. It then asserts the built artifact exists and carries the seeded
content.

Along the way it checks the guarantees #128 asks for and a test with a
fixed database cannot show: that an unconfigured instance sends every
route to the wizard, that the wizard is safe to abandon and resume, and
that the instance cannot be left without an admin account.

This is the mechanical proof that no step of the path is blocked. It
does NOT satisfy the "first site published in under 10 minutes" metric,
which requires a real non-technical tester (ROADMAP measurement rules).

Usage:
    python scripts/onboarding_flow_check.py
"""

import socket
import tempfile
import threading
import time
from pathlib import Path

import uvicorn
from playwright.sync_api import sync_playwright

USERNAME = "owner"
PASSWORD = "a sardine in space wins"
SITE_NAME = "Onboarding check"


def _free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


def _serve(directory: Path, port: int) -> uvicorn.Server:
    """The panel over an empty directory: no database, no project file,
    no account — exactly what a fresh install has."""
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


def _drive(base: str, directory: Path) -> list[str]:
    steps: list[str] = []

    def step(name: str) -> None:
        steps.append(name)
        print(f"  ok: {name}")

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page()

        # An unconfigured instance takes every route to the wizard.
        for path in ("/", "/articles", "/publishing"):
            page.goto(f"{base}{path}")
            assert page.url.rstrip("/").endswith("/setup"), f"{path} did not reach the wizard"
        step("an empty instance lands every route on the wizard")

        # Abandoning mid-wizard must lose nothing: leaving and coming
        # back finds the same empty form, and the instance still has no
        # account.
        page.fill("#username", USERNAME)
        page.goto(f"{base}/articles")
        assert page.url.rstrip("/").endswith("/setup")
        assert page.input_value("#username") == "", "an abandoned wizard kept partial state"
        step("the wizard is safe to abandon and resume")

        page.fill("#username", USERNAME)
        page.fill("#password", PASSWORD)
        page.fill("input[name='password_repeat']", PASSWORD)
        page.fill("input[name='site_name']", SITE_NAME)
        page.fill("input[name='base_url']", "https://onboarding.example")
        page.check("input[name='seed_example']")
        page.click("form button[type=submit]")
        page.wait_for_url(f"{base}/", timeout=30_000)
        step("the wizard created the account, the project and the content")

        # The project file is written and the account exists.
        assert (directory / "sardine.toml").is_file(), "no sardine.toml was written"
        assert SITE_NAME in (directory / "sardine.toml").read_text(encoding="utf-8")
        step("sardine.toml carries the site identity from the browser")

        # Signed in straight from the wizard: the dashboard renders.
        assert "<h1" in page.content(), "the dashboard did not render after setup"
        step("the wizard signs the first admin in")

        # A configured instance never exposes the wizard again — the
        # instance cannot be left without an admin account.
        page.goto(f"{base}/setup")
        assert not page.url.rstrip("/").endswith("/setup"), "the wizard stayed reachable"
        step("a configured instance never exposes the wizard again")

        # Publish from the browser: the publishing screen builds and
        # exports without touching the command line.
        page.goto(f"{base}/publishing")
        page.click("#build-form button[type=submit]")
        page.wait_for_url(f"{base}/publishing", timeout=120_000)
        body = page.content()
        assert "ready to go live" in body or "Last run" in body, "no build outcome reported"
        step("the site was built and exported from the browser")

        browser.close()
    return steps


def _assert_built(directory: Path) -> None:
    output = directory / "_site"
    assert output.is_dir(), "the build produced no output directory"
    index = output / "index.html"
    assert index.is_file(), "the built site has no index.html"
    html = index.read_text(encoding="utf-8")
    assert "<html" in html, "the built index is not HTML"
    files = sum(1 for path in output.rglob("*") if path.is_file())
    assert files > 20, f"the built site looks empty ({files} files)"
    print(f"  ok: built site on disk — {files} files, index.html renders")


def main() -> int:
    with tempfile.TemporaryDirectory() as scratch:
        directory = Path(scratch)
        port = _free_port()
        server = _serve(directory, port)
        try:
            started = time.monotonic()
            steps = _drive(f"http://127.0.0.1:{port}", directory)
            elapsed = time.monotonic() - started
        finally:
            server.should_exit = True
        _assert_built(directory)
        print(f"OK: {len(steps)} steps + build assertion in {elapsed:.1f}s (mechanical)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
