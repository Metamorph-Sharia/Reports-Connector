"""Import a report: keep its PDF as published, then read its text. A PDF that can't be read now is kept unread,
with the reason, and read again later from the kept PDF."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from datetime import datetime

from reports.application.ports import KeptReport, Reader, Reading, ReadingFailed, ReadText, Store
from reports.domain.reports import Report


class ImportReport:
    def __init__(self, store: Store, reader: Reader, now: Callable[[], datetime]) -> None:
        self.store = store
        self.reader = reader
        self.now = now

    def __call__(self, pdf: bytes, report: Report, *, page_url: str | None, file_url: str | None) -> KeptReport:
        kept = KeptReport(
            report=report,
            pdf=self.store.keep_file(pdf),
            page_url=page_url,
            file_url=file_url,
            fetched_at=self.now().isoformat(timespec="seconds"),
            reading=None,
        )
        return self.read(kept)

    def read(self, kept: KeptReport) -> KeptReport:
        """Reads a kept report's PDF and keeps what was read, or why it couldn't be."""
        try:
            read = self.reader.read(self.store.file(kept.pdf))
        except ReadingFailed as failed:
            kept = replace(kept, reading=None, note=str(failed))
        else:
            kept = replace(kept, reading=self._kept_text(read), note="")
        self.store.keep_report(kept)
        return kept

    def _kept_text(self, read: ReadText) -> Reading:
        return Reading(
            text=self.store.keep_file(read.text.encode("utf-8")),
            pages=read.pages,
            method=read.method,
            engine=read.engine,
            engine_version=read.engine_version,
            tier=read.tier,
            ocr_mode=read.ocr_mode,
            pages_ocrd=read.pages_ocrd,
            pages_fallen_back=read.pages_fallen_back,
        )
