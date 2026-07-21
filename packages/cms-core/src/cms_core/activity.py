"""Activity records (#134): who did what, when — append-only.

An audit record is operational history, deliberately decoupled from
content: it survives the deletion of what it describes, is never
exported with content, and never blocks the action it records."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class ActivityRecord:
    at: datetime
    actor: str
    """Username, or ``system`` for scheduled/automated operations."""
    action: str
    """A stable verb: ``published``, ``trashed``, ``signed-in``, …"""
    subject_kind: str
    """``article`` | ``page`` | ``media`` | ``user`` | ``session`` | …"""
    subject_id: str
    detail: str = ""
