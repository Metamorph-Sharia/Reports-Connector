"""Is collection working? For a scheduler: exit 0 ok, 1 warning, 2 critical."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import IntEnum

from reports.application.ports import Store
from reports.application.use_cases.status import walk

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
        walked_back = self.store.walked_back()
        message = (f"{len(kept) - unread} reports read, {unread} unread; {len(self.store.releases())} releases, "
                   f"{walk(walked_back)}; last synced {synced or 'never'}")
        if len(kept) == unread:
            return Health(Severity.CRITICAL, message)
        stale = not synced or (today - date.fromisoformat(synced)).days > SYNC_WARN_AFTER_DAYS
        return Health(Severity.WARNING if unread or stale or not walked_back else Severity.OK, message)
