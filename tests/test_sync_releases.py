"""Syncing OJK's press releases: every release listed since a date, each kept once, a refusal stopping the run."""

from __future__ import annotations

from datetime import date, datetime

import pytest
from fakes import NOW, FakeReleases, MemoryStore, listed

from reports.application.ports import ReleasePage, SourceRefused
from reports.application.use_cases.sync_releases import SyncReleases

SINCE = date(2020, 1, 1)
PAGES = [
    [listed("OJK-Cabut-Izin-Usaha-PT-Porto-Ventura-Kapital", "8 Oktober 2026"),
     listed("RDKB-September-2026", "5 Oktober 2026")],
    [listed("Insentif-OJK-Kendaraan-Listrik", "4 Februari 2020"),
     listed("Siaran-Pers-Akhir-Tahun", "30 Desember 2019")],
    [listed("Never-Asked", "1 Januari 2015")],
]


def sync(store: MemoryStore, releases: FakeReleases) -> list:
    return list(SyncReleases(releases, store, since=SINCE, now=lambda: datetime.fromisoformat(NOW))())


def test_a_first_sync_keeps_every_release_since_the_date_and_stops_at_the_first_before() -> None:
    store, releases = MemoryStore(), FakeReleases(PAGES)

    synced = sync(store, releases)

    assert [(s.release_id, s.note) for s in synced] == [
        ("ojk:siaran-pers:2026:ojk-cabut-izin-usaha-pt-porto-ventura-kapital", "kept"),
        ("ojk:siaran-pers:2026:rdkb-september-2026", "kept"),
        ("ojk:siaran-pers:2020:insentif-ojk-kendaraan-listrik", "kept"),
    ]
    assert releases.pages_asked == 2
    assert store.walked_back() == "2020-01-01"
    assert store.last_synced() == NOW


def test_a_kept_release_has_its_number_title_date_body_and_pdf() -> None:
    store = MemoryStore()
    sync(store, FakeReleases(PAGES))

    kept = store.release("ojk:siaran-pers:2026:ojk-cabut-izin-usaha-pt-porto-ventura-kapital")
    assert kept.release.number == "SP 1/DKPU/OJK/X/2026"
    assert kept.release.title == "Siaran Pers: OJK-Cabut-Izin-Usaha-PT-Porto-Ventura-Kapital"
    assert (kept.release.published_on, kept.fetched_at) == ("2026-10-08", NOW)
    assert store.file(kept.body).decode().startswith('<div id="summary">')
    assert kept.text.startswith("SP 1/DKPU/OJK/X/2026\n\nSIARAN PERS")
    assert kept.pdf_url.endswith("OJK-Cabut-Izin-Usaha-PT-Porto-Ventura-Kapital.pdf")


def test_once_the_history_is_whole_a_sync_stops_at_the_first_page_with_nothing_new() -> None:
    store = MemoryStore()
    sync(store, FakeReleases(PAGES))
    releases = FakeReleases([[listed("POJK-17-Tahun-2026", "15 Oktober 2026"), *PAGES[0]], *PAGES[1:]])

    synced = sync(store, releases)

    assert [s.note for s in synced] == ["kept"]
    assert releases.pages_asked == 2  # page 1 had a new release, so page 2 is looked at, and has none
    assert releases.releases_asked == ["POJK-17-Tahun-2026"]


def test_a_backfill_stopped_by_a_refusal_goes_on_where_it_stopped() -> None:
    store = MemoryStore()
    with pytest.raises(SourceRefused):
        sync(store, FakeReleases(PAGES, refuse="Insentif-OJK-Kendaraan-Listrik"))
    assert store.walked_back() is None and store.last_synced() is None

    releases = FakeReleases(PAGES)
    synced = sync(store, releases)

    assert [s.release_id for s in synced] == ["ojk:siaran-pers:2020:insentif-ojk-kendaraan-listrik"]
    assert releases.releases_asked == ["Insentif-OJK-Kendaraan-Listrik"]
    assert store.walked_back() == "2020-01-01"


def test_a_listing_that_ends_before_the_date_is_walked_whole() -> None:
    store = MemoryStore()

    sync(store, FakeReleases(PAGES[:1]))

    assert store.walked_back() == "2020-01-01"


def test_a_date_that_cannot_be_read_is_noted_and_the_sync_goes_on() -> None:
    store = MemoryStore()

    synced = sync(store, FakeReleases([[listed("Undated", "kemarin"), *PAGES[0]]]))

    assert synced[0].note == "not a date: 'kemarin'"
    assert [s.note for s in synced[1:]] == ["kept", "kept"]


def test_a_page_without_a_release_is_noted_not_kept() -> None:
    store = MemoryStore()
    empty = {"RDKB-September-2026": ReleasePage("", "", None)}

    synced = sync(store, FakeReleases(PAGES[:1], pages=empty))

    assert synced[1].note == "no release on its page"
    assert store.release("ojk:siaran-pers:2026:rdkb-september-2026") is None


def test_two_pages_that_name_one_id_keep_the_first_and_note_the_second() -> None:
    store = MemoryStore()
    twins = [[listed("OJK-Gelar-SEPMT-(2026)", "5 Oktober 2026"), listed("OJK-Gelar-SEPMT-2026", "5 Oktober 2026")]]

    synced = sync(store, FakeReleases(twins))

    assert synced[0].note == "kept"
    assert synced[1].note.startswith("its ID is taken by https://ojk.go.id/id/berita-dan-kegiatan/siaran-pers/Pages/"
                                     "OJK-Gelar-SEPMT-(2026).aspx")
