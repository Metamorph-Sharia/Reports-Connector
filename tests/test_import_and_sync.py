"""Importing a report downloaded by hand, and syncing OJK's LPKSI listing."""

from __future__ import annotations

from datetime import datetime

import pytest
from fakes import NOW, FakeListing, FakeReader, MemoryStore, edition_page, pdf_of, pdf_url

from reports.application.ports import ReportPage, SourceRefused
from reports.application.use_cases.import_report import ImportReport
from reports.application.use_cases.sync_lpksi import SyncLpksi
from reports.domain.reports import Report

RP3SI = Report.named("ojk:roadmap:2023:rp3si", title="Roadmap RP3SI 2023-2027", edition="2023-2027")


def importer(store: MemoryStore, reader: FakeReader | None = None) -> ImportReport:
    return ImportReport(store, reader or FakeReader(), now=lambda: datetime.fromisoformat(NOW))


def test_an_import_keeps_the_pdf_and_its_text() -> None:
    store = MemoryStore()

    imported = importer(store)(b"%PDF-1.7 RP3SI", RP3SI, page_url=None, file_url=None)

    kept = store.report("ojk:roadmap:2023:rp3si")
    assert imported == kept
    assert store.file(kept.pdf) == b"%PDF-1.7 RP3SI"
    assert store.file(kept.reading.text).decode().startswith("<!-- page 1 -->\nRP3SI")
    assert (kept.reading.pages, kept.reading.tier, kept.fetched_at) == (2, "basic", NOW)


def test_a_report_mineru_cannot_read_now_is_kept_unread_with_the_reason() -> None:
    store = MemoryStore()

    kept = importer(store, FakeReader(unavailable=True))(b"%PDF-1.7 RP3SI", RP3SI, page_url=None, file_url=None)

    assert kept.reading is None
    assert kept.note == "MinerU is unavailable: METAMORPH_MINERU_URL is not set"
    assert store.file(kept.pdf) == b"%PDF-1.7 RP3SI"


def sync(listing: FakeListing, store: MemoryStore, reader: FakeReader | None = None) -> list:
    return list(SyncLpksi(listing, store, importer(store, reader), now=lambda: datetime.fromisoformat(NOW))())


def test_a_sync_imports_every_edition_not_kept() -> None:
    store = MemoryStore()

    found = sync(FakeListing(["2024", "2025"]), store)

    assert [synced.report_id for synced in found] == ["ojk:lpksi:2024", "ojk:lpksi:2025"]
    assert store.file(store.report("ojk:lpksi:2025").pdf) == pdf_of("2025")
    assert store.report("ojk:lpksi:2025").page_url == edition_page("2025")
    assert store.report("ojk:lpksi:2025").file_url == pdf_url("2025")
    assert store.last_synced() == NOW


def test_an_edition_kept_already_costs_its_page_only() -> None:
    store = MemoryStore()
    sync(FakeListing(["2025"]), store)
    listing = FakeListing(["2025"])

    (again,) = sync(listing, store)

    assert again.note == "kept already"
    assert listing.asked == [edition_page("2025")]


def test_an_edition_kept_unread_is_read_from_its_kept_pdf() -> None:
    store = MemoryStore()
    sync(FakeListing(["2025"]), store, FakeReader(unavailable=True))
    listing = FakeListing(["2025"])

    (again,) = sync(listing, store)

    assert store.report("ojk:lpksi:2025").reading is not None
    assert (again.note, listing.asked) == ("read", [edition_page("2025")])


def test_a_page_that_names_no_edition_or_links_no_single_pdf_is_noted() -> None:
    store = MemoryStore()
    pages = {
        edition_page("2023"): ReportPage("Pengukuhan KPKS", (pdf_url("2023"),)),
        edition_page("2024"): ReportPage("Laporan Perkembangan Keuangan Syariah Indonesia 2024", ()),
        edition_page("2025"): ReportPage("Laporan Perkembangan Keuangan Syariah Indonesia 2025",
                                         (pdf_url("2025"), pdf_url("2025-en"))),
    }

    found = sync(FakeListing(["2023", "2024", "2025"], pages=pages), store)

    assert [synced.note for synced in found] == [
        "not an edition: Pengukuhan KPKS",
        "no PDF on its page",
        "2 PDFs on its page: import the edition by hand",
    ]
    assert store.reports() == []


def test_a_refusal_stops_the_sync_and_records_no_sync() -> None:
    store = MemoryStore()

    with pytest.raises(SourceRefused):
        sync(FakeListing(["2024", "2025"], refuse=pdf_url("2025")), store)

    assert store.report("ojk:lpksi:2024") is not None
    assert store.last_synced() is None


def test_reports_kept_unread_are_read_once_mineru_is_back() -> None:
    from reports.application.use_cases.read_unread import ReadUnread

    store = MemoryStore()
    importer(store, FakeReader(unavailable=True))(b"%PDF-1.7 RP3SI", RP3SI, page_url=None, file_url=None)

    read = list(ReadUnread(store, importer(store))())

    assert [kept.report.id for kept in read] == ["ojk:roadmap:2023:rp3si"]
    assert store.report("ojk:roadmap:2023:rp3si").reading is not None
    assert list(ReadUnread(store, importer(store))()) == []
