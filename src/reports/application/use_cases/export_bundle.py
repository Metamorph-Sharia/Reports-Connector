"""Export: every read report, with its PDF and its text, and every release, with its body, as one market bundle
(a full snapshot)."""

from __future__ import annotations

from pathlib import Path

from reports.application.ports import BundleExporter, Store


class ExportBundle:
    def __init__(self, store: Store, exporter: BundleExporter) -> None:
        self.store = store
        self.exporter = exporter

    def __call__(self, out: Path, run_id: str) -> int:
        read = [kept for kept in self.store.reports() if kept.reading is not None]
        releases = self.store.releases()
        shas = [sha for kept in read for sha in (kept.pdf, kept.reading.text)] + [kept.body for kept in releases]
        return self.exporter.export(read, releases, {sha: self.store.file(sha) for sha in shas}, out, run_id)
