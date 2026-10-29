"""What is exported, shown and checked: read reports and every release; unread reports, a release history not
whole yet and a stale sync warn."""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

from fakes import NOW, FakeListing, FakeReader, FakeReleases, MemoryStore, listed

from reports.application.use_cases.check_health import CheckHealth, Severity
from reports.application.use_cases.export_bundle import ExportBundle
from reports.application.use_cases.import_report import ImportReport
from reports.application.use_cases.status import Status
from reports.application.use_cases.sync_lpksi import SyncLpksi
from reports.application.use_cases.sync_releases import SyncReleases

TODAY = date(2026, 10, 28)


class CapturingExporter:
    def __init__(self) -> None:
        self.exported: tuple = ()

    def export(self, reports, releases, files, out: Path, run_id: str) -> int:  # noqa: ANN001
        self.exported = (tuple(reports), tuple(releases), dict(files))
        return len(reports) + len(releases)


RELEASES = [[listed("POJK-17-Tahun-2026", "15 Oktober 2026"), listed("Insentif-OJK", "4 Februari 2020")],
            [listed("Siaran-Pers-Akhir-Tahun", "30 Desember 2019")]]


def synced_store(*years: str, unread: str | None = None, releases: list | None = RELEASES) -> MemoryStore:
    store = MemoryStore()
    importer = ImportReport(store, FakeReader(), now=lambda: datetime.fromisoformat(NOW))
    list(SyncLpksi(FakeListing(list(years)), store, importer, now=lambda: datetime.fromisoformat(NOW))())
    if releases is not None:
        sync = SyncReleases(FakeReleases(releases), store, since=date(2020, 1, 1),
                            now=lambda: datetime.fromisoformat(NOW))
        list(sync())
    if unread:
        store.unread(unread)
    return store


def test_only_read_reports_are_exported_with_their_pdf_and_text() -> None:
    store, exporter = synced_store("2024", "2025", unread="ojk:lpksi:2024"), CapturingExporter()

    count = ExportBundle(store, exporter)(Path("out"), "run-1")

    reports, releases, files = exporter.exported
    (kept,) = reports
    assert (count, kept.report.id) == (3, "ojk:lpksi:2025")
    assert [release.release.published_on for release in releases] == ["2026-10-15", "2020-02-04"]
    assert set(files) == {kept.pdf, kept.reading.text, *(release.body for release in releases)}


def test_status_shows_each_report_and_why_one_is_unread() -> None:
    lines = Status(synced_store("2024", "2025", unread="ojk:lpksi:2024"))()

    assert lines == [
        "ojk:lpksi:2024 Laporan Perkembangan Keuangan Syariah Indonesia 2024: unread: MinerU is unavailable",
        "ojk:lpksi:2025 Laporan Perkembangan Keuangan Syariah Indonesia 2025: 2 pages, text_layer, fetched 2026-10-28",
        "releases: 2 kept, 2020-02-04 to 2026-10-15; the listing walked whole back to 2020-01-01",
    ]


def test_status_says_when_the_release_history_is_not_whole_yet() -> None:
    store = synced_store("2025", releases=None)

    assert Status(store)()[-1] == "releases: none kept; the listing not walked whole yet"


def test_health_is_ok_when_every_report_is_read_and_the_sync_recent() -> None:
    assert CheckHealth(synced_store("2025"))(TODAY).severity is Severity.OK


def test_health_warns_on_an_unread_report_or_an_old_sync() -> None:
    unread = CheckHealth(synced_store("2024", "2025", unread="ojk:lpksi:2024"))(TODAY)
    stale = CheckHealth(synced_store("2025"))(date(2026, 11, 28))

    assert unread.severity is stale.severity is Severity.WARNING
    assert "1 unread" in unread.message
    assert "last synced 2026-10-28" in stale.message


def test_health_warns_while_the_release_history_is_not_whole() -> None:
    health = CheckHealth(synced_store("2025", releases=None))(TODAY)

    assert health.severity is Severity.WARNING
    assert "0 releases, the listing not walked whole yet" in health.message


def test_health_is_critical_with_nothing_read() -> None:
    assert CheckHealth(MemoryStore())(TODAY).severity is Severity.CRITICAL
