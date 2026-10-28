"""Status: every report kept, read or not."""

from __future__ import annotations

from reports.application.ports import Store


class Status:
    def __init__(self, store: Store) -> None:
        self.store = store

    def __call__(self) -> list[str]:
        lines = []
        for kept in self.store.reports():
            reading = kept.reading
            shown = (f"{reading.pages} pages, {reading.method}, fetched {kept.fetched_at[:10]}" if reading
                     else f"unread: {kept.note}")
            lines.append(f"{kept.report.id} {kept.report.title}: {shown}")
        return lines
