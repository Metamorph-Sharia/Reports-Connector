"""Read reports → market contract `report` records, and releases → `release` records, written with the contract's
BundleWriter: a full snapshot, each PDF, each text and each release's body a blob."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path

from metamorph_market import (
    BundleWriter,
    Extraction,
    FileRef,
    FileRole,
    Release,
    ReleaseRecord,
    Report,
    ReportRecord,
    ReportText,
    SourceRef,
    TextMethod,
)

from reports.application.ports import KeptRelease, KeptReport

CONNECTOR = "reports"
PDF = "application/pdf"
HTML = "text/html; charset=utf-8"


class MarketBundleExporter:
    def __init__(self, connector_version: str) -> None:
        self.connector_version = connector_version

    def export(
        self,
        reports: Sequence[KeptReport],
        releases: Sequence[KeptRelease],
        files: Mapping[str, bytes],
        out: Path,
        run_id: str,
    ) -> int:
        with BundleWriter(out, connector=CONNECTOR, connector_version=self.connector_version, run_id=run_id) as bundle:
            for sha in sorted(files):
                bundle.put_blob(files[sha])
            for kept in reports:
                bundle.add(self._record(kept))
            for kept in releases:
                bundle.add(self._release(kept))
        return len(reports) + len(releases)

    def _release(self, kept: KeptRelease) -> ReleaseRecord:
        release = kept.release
        return ReleaseRecord(
            source=SourceRef(CONNECTOR, self.connector_version, kept.page_url.rsplit("/", 1)[-1].removesuffix(".aspx"),
                             kept.page_url, kept.fetched_at),
            release=Release(release.id, release.issuer, release.number, release.title, release.published_on,
                            release.language),
            text=kept.text,
            files=(FileRef(kept.body, FileRole.SOURCE_PAGE, HTML, kept.page_url, release.published_on),),
            source_fields={"pdf": kept.pdf_url},
        )

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
