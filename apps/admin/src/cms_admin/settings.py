"""Admin configuration.

Environment-only by design: the admin never reads config files, so secrets
cannot end up in a project directory that gets committed or exported.
"""

import os
from dataclasses import dataclass, field
from datetime import timedelta
from pathlib import Path

DEFAULT_STORAGE_URL = "sqlite:///content.db"
DEFAULT_SESSION_HOURS = 12
DEFAULT_UPLOAD_MAX_MB = 10


@dataclass(frozen=True, slots=True)
class AdminSettings:
    storage_url: str = DEFAULT_STORAGE_URL
    session_ttl: timedelta = timedelta(hours=DEFAULT_SESSION_HOURS)
    # Secure cookies are the default; set SARDINE_ADMIN_COOKIE_SECURE=0
    # only for plain-http local development.
    cookie_secure: bool = True
    # Where uploaded media files live — the project's media/ directory, the
    # same one `cms build` collects.
    media_dir: Path = field(default_factory=lambda: Path("media"))
    upload_max_bytes: int = DEFAULT_UPLOAD_MAX_MB * 1024 * 1024

    @classmethod
    def from_env(cls) -> "AdminSettings":
        return cls(
            storage_url=os.environ.get("SARDINE_STORAGE_URL", DEFAULT_STORAGE_URL),
            session_ttl=timedelta(
                hours=float(
                    os.environ.get("SARDINE_ADMIN_SESSION_HOURS", str(DEFAULT_SESSION_HOURS))
                )
            ),
            cookie_secure=os.environ.get("SARDINE_ADMIN_COOKIE_SECURE", "1") != "0",
            media_dir=Path(os.environ.get("SARDINE_MEDIA_DIR", "media")),
            upload_max_bytes=int(
                float(os.environ.get("SARDINE_ADMIN_UPLOAD_MAX_MB", str(DEFAULT_UPLOAD_MAX_MB)))
                * 1024
                * 1024
            ),
        )
