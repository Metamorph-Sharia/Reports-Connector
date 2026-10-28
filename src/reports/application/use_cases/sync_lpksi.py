"""Sync OJK's LPKSI listing: every edition page it links, each edition imported once.

An edition kept already costs its page only. One kept but not read yet (MinerU was unavailable) is read again from
its kept PDF. A page that names no edition, or links no single PDF, is noted and left for a person. A refusal
stops the sync, which then isn't recorded as one that went through.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from dataclasses import dataclass
from datetime import datetime

from reports.application.ports import KeptReport, LpksiListing, Store
from reports.application.use_cases.import_report import ImportReport
from reports.domain.reports import lpksi


@dataclass(frozen=True)
class Synced:
    url: str  # the edition's page
    report_id: str | None
    note: str  # imported, read, kept already, or why not
    kept: KeptReport | None = None


class SyncLpksi:
    def __init__(
        self, listing: LpksiListing, store: Store, import_report: ImportReport, now: Callable[[], datetime]
    ) -> None:
        self.listing = listing
        self.store = store
        self.import_report = import_report
        self.now = now

    def __call__(self) -> Iterator[Synced]:
        for url in self.listing.editions():
            yield self._edition(url)
        self.store.synced(self.now().isoformat(timespec="seconds"))

    def _edition(self, url: str) -> Synced:
        page = self.listing.page(url)
        report = lpksi(page.title)
        if report is None:
            return Synced(url, None, f"not an edition: {page.title}")
        kept = self.store.report(report.id)
        if kept is not None and kept.reading is not None:
            return Synced(url, report.id, "kept already", kept)
        if kept is not None:
            kept = self.import_report.read(kept)
            return Synced(url, report.id, kept.note or "read", kept)
        if not page.pdfs:
            return Synced(url, report.id, "no PDF on its page")
        if len(page.pdfs) > 1:
            return Synced(url, report.id, f"{len(page.pdfs)} PDFs on its page: import the edition by hand")
        (file_url,) = page.pdfs
        kept = self.import_report(self.listing.download(file_url), report, page_url=url, file_url=file_url)
        return Synced(url, report.id, kept.note or "imported", kept)
