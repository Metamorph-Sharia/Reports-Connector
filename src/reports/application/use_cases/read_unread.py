"""Read every report kept but not read yet, from its kept PDF: once MinerU is available again."""

from __future__ import annotations

from collections.abc import Iterator

from reports.application.ports import KeptReport, Store
from reports.application.use_cases.import_report import ImportReport


class ReadUnread:
    def __init__(self, store: Store, import_report: ImportReport) -> None:
        self.store = store
        self.import_report = import_report

    def __call__(self) -> Iterator[KeptReport]:
        for kept in self.store.reports():
            if kept.reading is None:
                yield self.import_report.read(kept)
