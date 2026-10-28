"""The SQLite store and the market bundle, on disk: what a sync keeps is what an export sends, and it is valid."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from fakes import NOW, FakeListing, FakeReader
from metamorph_market import Bundle, ReportRecord, TextMethod

from reports.adapters.storage.market_bundle import MarketBundleExporter
from reports.adapters.storage.sqlite import SqliteStore
from reports.application.use_cases.export_bundle import ExportBundle
from reports.application.use_cases.import_report import ImportReport
from reports.application.use_cases.sync_lpksi import SyncLpksi


def synced(data: Path, reader: FakeReader | None = None) -> SqliteStore:
    store = SqliteStore(data)
    importer = ImportReport(store, reader or FakeReader(), now=lambda: datetime.fromisoformat(NOW))
    list(SyncLpksi(FakeListing(["2024", "2025"]), store, importer, now=lambda: datetime.fromisoformat(NOW))())
    return store


def test_a_report_is_kept_whole_across_connections(tmp_path: Path) -> None:
    kept = synced(tmp_path).report("ojk:lpksi:2025")

    again = SqliteStore(tmp_path)

    assert again.report("ojk:lpksi:2025") == kept
    assert [report.report.id for report in again.reports()] == ["ojk:lpksi:2024", "ojk:lpksi:2025"]
    assert again.file(kept.reading.text).startswith(b"<!-- page 1 -->")
    assert again.last_synced() == NOW


def test_an_unread_report_is_kept_with_its_note(tmp_path: Path) -> None:
    kept = synced(tmp_path, FakeReader(unavailable=True)).report("ojk:lpksi:2025")

    assert kept.reading is None
    assert "METAMORPH_MINERU_URL" in SqliteStore(tmp_path).report("ojk:lpksi:2025").note


def test_an_export_is_a_valid_bundle_of_report_records(tmp_path: Path) -> None:
    store = synced(tmp_path / "data")

    count = ExportBundle(store, MarketBundleExporter("0.1.0"))(tmp_path / "bundle", "run-1")

    entries = list(Bundle(tmp_path / "bundle").entries())
    assert count == len(entries) == 2
    assert all(entry.is_valid for entry in entries)
    record = entries[1].record
    assert isinstance(record, ReportRecord)
    assert (record.report.id, record.text.method, record.source.connector) == (
        "ojk:lpksi:2025", TextMethod.TEXT_LAYER, "reports"
    )
    assert Bundle(tmp_path / "bundle").blob_path(record.text.file).read_bytes().startswith(b"<!-- page 1 -->")
