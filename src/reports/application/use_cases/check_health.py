"""Is collection working? For a scheduler: exit 0 ok, 1 warning, 2 critical."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import IntEnum

from reports.application.ports import Store

SYNC_WARN_AFTER_DAYS = 14  # the listing is synced weekly


class Severity(IntEnum):
    OK = 0
    WARNING = 1
    CRITICAL = 2


@dataclass(frozen=True)
class Health:
    severity: Severity
    message: str


class CheckHealth:
    def __init__(self, store: Store) -> None:
        self.store = store

    def __call__(self, today: date) -> Health:
        kept = self.store.reports()
        unread = sum(1 for report in kept if report.reading is None)
        synced = (self.store.last_synced() or "")[:10]
        message = f"{len(kept) - unread} reports read, {unread} unread; last synced {synced or 'never'}"
        if len(kept) == unread:
            return Health(Severity.CRITICAL, message)
        stale = not synced or (today - date.fromisoformat(synced)).days > SYNC_WARN_AFTER_DAYS
        return Health(Severity.WARNING if unread or stale else Severity.OK, message)
