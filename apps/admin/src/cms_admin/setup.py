"""First-run setup (#128): from an empty instance to a working site.

While the instance has no accounts, every request lands on ``/setup`` —
one page, three sections: the first admin account, the site's identity
(name, address, languages from the registered packs, theme) and optional
example content. Submitting creates the admin, writes ``sardine.toml``
when the project has none (an existing file is never rewritten — its
values show read-only), optionally seeds the example site, signs the
new admin in and lands on the dashboard's first-steps checklist.

The instance can never be left without an admin: the wizard's account
is always ``admin`` role, and ``/setup`` disappears the moment any
account exists.
"""

import asyncio
import secrets
from datetime import UTC, datetime
from pathlib import Path

from cms_core import Language, Role, User
from cms_core.language_packs import registered_language_packs
from fastapi import APIRouter, Request, status
from fastapi.responses import RedirectResponse
from pydantic import ValidationError

from cms_admin.auth import get_db, login_csrf_cookie_name, session_cookie_name
from cms_admin.i18n import translate
from cms_admin.security import hash_password, new_token, token_digest

router = APIRouter()

PASSWORD_MIN = 12


async def setup_pending(request: Request) -> bool:
    """True while the instance has no accounts. Cached once done: the
    wizard can never reappear on a configured instance."""
    if getattr(request.app.state, "setup_done", False):
        return False
    usernames = await get_db(request).run(lambda storage: storage.list_usernames())
    if usernames:
        request.app.state.setup_done = True
        return False
    return True


def _language_choices() -> list[tuple[str, str]]:
    return [(pack.tag, pack.native_name or pack.tag) for pack in registered_language_packs()]


def _project_file(request: Request) -> Path:
    return Path(request.app.state.settings.project_dir) / "sardine.toml"


def _render(request: Request, form: dict[str, object], errors: list[str]) -> object:
    csrf = new_token()
    response = request.app.state.templates.TemplateResponse(
        request,
        "setup.html.j2",
        {
            "errors": errors,
            "form": form,
            "setup_csrf": csrf,
            "language_choices": _language_choices(),
            "existing_project": _project_file(request).is_file(),
            "themes": ("default", "ph7x-reference"),
        },
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT if errors else 200,
    )
    response.set_cookie(
        login_csrf_cookie_name(request),
        csrf,
        httponly=True,
        samesite="strict",
        secure=request.app.state.settings.cookie_secure,
        path="/",
    )
    return response


_DEFAULT_FORM: dict[str, object] = {
    "username": "",
    "site_name": "",
    "base_url": "https://",
    "source_language": "en",
    "languages": [],
    "theme": "default",
    "seed_example": False,
}


@router.get("/setup")
async def setup_form(request: Request) -> object:
    if not await setup_pending(request):
        return RedirectResponse("/login", status_code=status.HTTP_303_SEE_OTHER)
    return _render(request, dict(_DEFAULT_FORM), [])


@router.post("/setup")
async def setup_submit(request: Request) -> object:
    if not await setup_pending(request):
        return RedirectResponse("/login", status_code=status.HTTP_303_SEE_OTHER)
    form_data = await request.form()
    csrf_cookie = request.cookies.get(login_csrf_cookie_name(request))
    submitted = str(form_data.get("setup_csrf", ""))
    if not csrf_cookie or not secrets.compare_digest(csrf_cookie, submitted):
        return _render(request, dict(_DEFAULT_FORM), ["The form expired — try again."])

    username = str(form_data.get("username", "")).strip().lower()
    password = str(form_data.get("password", ""))
    password_repeat = str(form_data.get("password_repeat", ""))
    site_name = str(form_data.get("site_name", "")).strip()
    base_url = str(form_data.get("base_url", "")).strip()
    source_language = str(form_data.get("source_language", "en"))
    languages = [str(value) for value in form_data.getlist("languages")]
    theme = str(form_data.get("theme", "default"))
    seed_example = form_data.get("seed_example") is not None

    form: dict[str, object] = {
        "username": username,
        "site_name": site_name,
        "base_url": base_url,
        "source_language": source_language,
        "languages": languages,
        "theme": theme,
        "seed_example": seed_example,
    }
    errors: list[str] = []
    if not username or not username.replace("-", "").isalnum():
        errors.append(translate(request, "username: lowercase letters, digits and dashes only"))
    if len(password) < PASSWORD_MIN:
        errors.append(translate(request, "The password needs at least 12 characters."))
    if password != password_repeat:
        errors.append(translate(request, "The two passwords do not match."))

    project_exists = _project_file(request).is_file()
    if not project_exists:
        try:
            from cms_build import SiteConfig

            known = {tag for tag, _name in _language_choices()}
            chosen = [tag for tag in languages if tag in known and tag != source_language]
            SiteConfig(
                name=site_name,
                base_url=base_url,
                source_language=Language(source_language),
                languages=tuple(Language(tag) for tag in chosen),
                theme=theme if theme in ("default", "ph7x-reference") else "default",
            )
        except (ValidationError, ValueError):
            errors.append(translate(request, "Check the site name and address."))
    if errors:
        return _render(request, form, errors)

    password_hash = await asyncio.to_thread(hash_password, password)
    user = User(
        username=username,
        password_hash=password_hash,
        role=Role.ADMIN,
        created_at=datetime.now(tz=UTC),
    )
    db = get_db(request)
    await db.run(lambda storage: storage.save_user(user))
    request.app.state.setup_done = True
    from cms_admin.audit import record as audit_record

    await audit_record(request, username, "user-created", "user", username, "setup")

    if not project_exists:
        chosen = [
            tag
            for tag in languages
            if tag in {t for t, _n in _language_choices()} and tag != source_language
        ]
        listed = ", ".join(f'"{tag}"' for tag in chosen)
        _project_file(request).write_text(
            "[site]\n"
            f'name = "{site_name}"\n'
            f'base_url = "{base_url}"\n'
            f'source_language = "{source_language}"\n'
            f"languages = [{listed}]\n"
            f'theme = "{theme}"\n'
            "\n[storage]\n"
            f'url = "{request.app.state.settings.storage_url}"\n',
            encoding="utf-8",
        )

    if seed_example:
        from cms_cli.seed import seed

        project_dir = Path(request.app.state.settings.project_dir)
        await db.run(lambda storage: seed(storage, project_dir))

    # Sign the new admin straight in — the wizard ends on the dashboard.
    token = new_token()
    now = datetime.now(tz=UTC)
    ttl = request.app.state.settings.session_ttl
    from cms_core import AdminSession

    session = AdminSession(
        token_hash=token_digest(token),
        username=username,
        csrf_token=new_token(),
        expires_at=now + ttl,
    )
    await db.run(lambda storage: storage.save_session(session))
    response = RedirectResponse("/", status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(
        session_cookie_name(request),
        token,
        httponly=True,
        samesite="strict",
        secure=request.app.state.settings.cookie_secure,
        max_age=int(ttl.total_seconds()),
        path="/",
    )
    return response
