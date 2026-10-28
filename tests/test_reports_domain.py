"""What a report is, and how an LPKSI edition's page names it."""

from __future__ import annotations

import pytest

from reports.domain.reports import InvalidReport, Report, lpksi


def test_an_lpksi_page_title_names_the_edition() -> None:
    report = lpksi("Laporan Perkembangan Keuangan Syariah Indonesia 2025")

    assert report == Report(
        id="ojk:lpksi:2025",
        issuer="ojk",
        family="lpksi",
        edition="2025",
        title="Laporan Perkembangan Keuangan Syariah Indonesia 2025",
        published_on=None,
        language="id",
    )


def test_invisible_characters_and_spacing_in_a_title_are_ignored() -> None:
    report = lpksi("\u200bLaporan  Perkembangan Keuangan Syariah Indonesia 2019 ")

    assert (report.id, report.title) == ("ojk:lpksi:2019", "Laporan Perkembangan Keuangan Syariah Indonesia 2019")


def test_a_page_whose_title_names_no_year_is_no_edition() -> None:
    assert lpksi("Laporan Perkembangan Keuangan Syariah Indonesia") is None
    assert lpksi("Pengukuhan KPKS dan Peluncuran LPKSI 2024") is None  # a news page, not an edition


def test_a_report_named_by_hand_is_checked() -> None:
    report = Report.named("ojk:roadmap:2023:rp3si", title="Roadmap RP3SI 2023-2027", edition="2023-2027")

    assert (report.issuer, report.family, report.edition) == ("ojk", "roadmap", "2023-2027")
    with pytest.raises(InvalidReport, match="issuer:family"):
        Report.named("rp3si", title="Roadmap RP3SI", edition="2023-2027")
    with pytest.raises(InvalidReport, match="lowercase"):
        Report.named("OJK:Roadmap:2023", title="Roadmap", edition="2023")
