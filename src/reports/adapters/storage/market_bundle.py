"""Read reports → market contract `report` records, written with the contract's BundleWriter: a full snapshot,
each PDF and each text a blob."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path

from metamorph_market import (
    BundleWriter,
    Extraction,
    FileRef,
    FileRole,
    Report,
    ReportRecord,
    ReportText,
    SourceRef,
    TextMethod,
)

from reports.application.ports import KeptReport

CONNECTOR = "reports"
PDF = "application/pdf"


class MarketBundleExporter:
    def __init__(self, connector_version: str) -> None:
        self.connector_version = connector_version

    def export(self, reports: Sequence[KeptReport], files: Mapping[str, bytes], out: Path, run_id: str) -> int:
        with BundleWriter(out, connector=CONNECTOR, connector_version=self.connector_version, run_id=run_id) as bundle:
            for sha in sorted(files):
                bundle.put_blob(files[sha])
            for kept in reports:
                bundle.add(self._record(kept))
        return len(reports)

    def _record(self, kept: KeptReport) -> ReportRecord:
        report, reading = kept.report, kept.reading
        if reading is None:
            raise ValueError(f"{report.id} isn't read yet: only read reports are exported")
        return ReportRecord(
            source=SourceRef(CONNECTOR, self.connector_version, report.id, kept.page_url, kept.fetched_at),
            report=Report(report.id, report.issuer, report.family, report.edition, report.title, report.published_on,
                          report.language),
            text=ReportText(
                file=reading.text,
                pages=reading.pages,
                method=TextMethod(reading.method),
                extraction=Extraction(reading.engine, reading.engine_version, reading.tier, reading.ocr_mode,
                                      reading.pages_ocrd, reading.pages_fallen_back),
            ),
            files=(FileRef(kept.pdf, FileRole.SOURCE_REPORT, PDF, kept.file_url,
                           report.published_on or kept.fetched_at[:10]),),
            source_fields={"page_url": kept.page_url, "file_url": kept.file_url},
        )
