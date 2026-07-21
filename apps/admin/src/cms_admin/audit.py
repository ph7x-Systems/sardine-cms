"""The audit trail (#134): who did what, when — and it never blocks.

Every security- and content-relevant panel action appends one
``ActivityRecord``. Recording failures are logged and swallowed: the
audit trail observes operations, it never becomes their point of
failure. Records survive the deletion of what they describe and are
pruned only by the retention policy."""

import logging
from datetime import UTC, datetime, timedelta

from cms_core.activity import ActivityRecord
from fastapi import Request

from cms_admin.auth import get_db
from cms_admin.db import StorageExecutor

logger = logging.getLogger("cms_admin.audit")


async def record(
    request: Request,
    actor: str,
    action: str,
    subject_kind: str,
    subject_id: str,
    detail: str = "",
) -> None:
    entry = ActivityRecord(
        at=datetime.now(tz=UTC),
        actor=actor,
        action=action,
        subject_kind=subject_kind,
        subject_id=subject_id,
        detail=detail,
    )
    try:
        await get_db(request).run(lambda storage: storage.record_activity(entry))
    except Exception:  # pragma: no cover - the trail never blocks the action
        logger.exception("activity record failed: %s %s", action, subject_id)


async def prune_on_startup(db: "StorageExecutor", retention_days: int) -> None:
    """Apply the retention policy once per process start; 0 keeps all."""
    if retention_days <= 0:
        return
    cutoff = datetime.now(tz=UTC) - timedelta(days=retention_days)
    try:
        await db.run(lambda storage: storage.prune_activity(cutoff))
    except Exception:  # pragma: no cover
        logger.exception("activity pruning failed")
