"""Export: every read report, with its PDF and its text, as one market bundle (a full snapshot)."""

from __future__ import annotations

from pathlib import Path

from reports.application.ports import BundleExporter, Store


class ExportBundle:
    def __init__(self, store: Store, exporter: BundleExporter) -> None:
        self.store = store
        self.exporter = exporter

    def __call__(self, out: Path, run_id: str) -> int:
        read = [kept for kept in self.store.reports() if kept.reading is not None]
        files = {sha: self.store.file(sha) for kept in read for sha in (kept.pdf, kept.reading.text)}
        return self.exporter.export(read, files, out, run_id)
