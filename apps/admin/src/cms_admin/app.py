"""Application factory.

One FastAPI process serves the API and the server-rendered UI (ADR-0013).
Storage is opened once per process (any supported engine, via the
thread-affine ``StorageExecutor``) and closed on shutdown; handlers reach it
through ``get_db``.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from cms_core.accounts import AdminSession, User
from fastapi import Depends, FastAPI, Request
from fastapi.templating import Jinja2Templates

from cms_admin.auth import current_session, get_db
from cms_admin.auth import router as auth_router
from cms_admin.db import StorageExecutor
from cms_admin.settings import AdminSettings


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings: AdminSettings = app.state.settings
    app.state.db = StorageExecutor(settings.storage_url)
    try:
        yield
    finally:
        app.state.db.close()


def create_app(settings: AdminSettings | None = None) -> FastAPI:
    from cms_admin.auth import LoginRateLimiter

    app = FastAPI(title="Stillsite admin", lifespan=_lifespan, docs_url=None, redoc_url=None)
    app.state.settings = settings if settings is not None else AdminSettings.from_env()
    app.state.templates = Jinja2Templates(directory=Path(__file__).parent / "templates")
    app.state.login_limiter = LoginRateLimiter()
    app.include_router(auth_router)

    @app.get("/healthz")
    async def healthz(request: Request) -> dict[str, str | int]:
        version = await get_db(request).run(lambda storage: storage.schema_version())
        return {"status": "ok", "schema_version": version}

    @app.get("/")
    async def dashboard(
        request: Request,
        user_session: tuple[User, AdminSession] = Depends(current_session),
    ) -> object:
        user, session = user_session
        return request.app.state.templates.TemplateResponse(
            request, "dashboard.html.j2", {"user": user, "csrf_token": session.csrf_token}
        )

    return app
