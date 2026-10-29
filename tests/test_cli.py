"""The commands Airflow and a curator run, and the exit codes Airflow reads. OJK and MinerU are fakes here."""

from __future__ import annotations

from pathlib import Path

import pytest
from fakes import FakeListing, FakeReader, FakeReleases, listed
from metamorph_market import Bundle

from reports import wiring
from reports.cli import main

RELEASES = [[listed("POJK-17-Tahun-2026", "15 Oktober 2026"), listed("Siaran-Pers-Akhir-Tahun", "30 Desember 2019")]]


@pytest.fixture(autouse=True)
def data(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("REPORTS_DATA", str(tmp_path / "data"))
    monkeypatch.setattr(wiring, "OjkLpksi", lambda site: FakeListing(["2024", "2025"]))
    monkeypatch.setattr(wiring, "OjkReleases", lambda site: FakeReleases(RELEASES))
    monkeypatch.setattr(wiring, "reader", lambda config: FakeReader())
    return tmp_path / "data"


def test_sync_reports_each_edition_then_each_new_release(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["sync"]) == 0
    assert capsys.readouterr().out == ("ojk:lpksi:2024: imported\nojk:lpksi:2025: imported\n"
                                       "ojk:siaran-pers:2026:pojk-17-tahun-2026: kept\n")


def test_releases_are_kept_since_the_date_set(monkeypatch: pytest.MonkeyPatch,
                                              capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setenv("RELEASES_SINCE", "2019-12-01")

    main(["sync"])

    assert capsys.readouterr().out.endswith("ojk:siaran-pers:2019:siaran-pers-akhir-tahun: kept\n")


def test_a_refusal_stops_the_sync_with_an_error(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    listing = FakeListing(["2025"], refuse=FakeListing(["2025"]).editions()[0])
    monkeypatch.setattr(wiring, "OjkLpksi", lambda site: listing)

    assert main(["sync"]) == 2
    assert "reports: stopped: " in capsys.readouterr().err


def test_import_takes_a_report_downloaded_by_hand(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    pdf = tmp_path / "RP3SI.pdf"
    pdf.write_bytes(b"%PDF-1.7 RP3SI")

    assert main(["import", str(pdf), "--id", "ojk:roadmap:2023:rp3si", "--title", "Roadmap RP3SI 2023-2027",
                 "--edition", "2023-2027", "--published", "2023-11-27"]) == 0
    assert capsys.readouterr().out == "ojk:roadmap:2023:rp3si: 2 pages, text_layer\n"


def test_import_refuses_an_id_that_breaks_the_contract(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    pdf = tmp_path / "x.pdf"
    pdf.write_bytes(b"%PDF-1.7")

    assert main(["import", str(pdf), "--id", "RP3SI", "--title", "Roadmap", "--edition", "2023"]) == 2
    assert "an ID is lowercase" in capsys.readouterr().err


def test_without_mineru_reports_are_kept_unread_then_read(monkeypatch: pytest.MonkeyPatch,
                                                          capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(wiring, "reader", lambda config: FakeReader(unavailable=True))
    main(["sync"])
    assert main(["health"]) == 2  # nothing read
    monkeypatch.setattr(wiring, "reader", lambda config: FakeReader())
    capsys.readouterr()

    assert main(["read"]) == 0
    assert capsys.readouterr().out == "ojk:lpksi:2024: 2 pages, text_layer\nojk:lpksi:2025: 2 pages, text_layer\n"


def test_status_export_and_health_after_a_sync(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    main(["sync"])
    capsys.readouterr()

    assert main(["status"]) == 0
    assert "ojk:lpksi:2025 Laporan Perkembangan Keuangan Syariah Indonesia 2025: 2 pages" in capsys.readouterr().out
    assert main(["export", "--out", str(tmp_path / "bundle"), "--run-id", "run-1"]) == 0
    assert Bundle(tmp_path / "bundle").manifest.records == 3  # two reports and a release
    assert main(["health"]) == 0
