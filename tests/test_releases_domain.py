"""What a press release is: its ID from its page's name, its date as the listing writes it, its number."""

from __future__ import annotations

from datetime import date

import pytest

from reports.domain.releases import listed_date, number, release_id


def test_an_id_is_the_issuer_the_year_and_the_page_name_in_lower_case() -> None:
    assert release_id("ojk", date(2026, 10, 8), "OJK-Cabut-Izin-Usaha-PT-Porto-Ventura-Kapital.aspx") == (
        "ojk:siaran-pers:2026:ojk-cabut-izin-usaha-pt-porto-ventura-kapital"
    )


@pytest.mark.parametrize(("page", "name"), [
    ("OJK-Gelar-Forum-Sinergi-Penguatan-Ekosistem-Tata-Kelola-(SPEKTA).aspx",
     "ojk-gelar-forum-sinergi-penguatan-ekosistem-tata-kelola-spekta"),
    ("Tingkatkan-Akses-Keuangan-Masyarakat-Desa,-OJK-Resmikan-Program.aspx",
     "tingkatkan-akses-keuangan-masyarakat-desa-ojk-resmikan-program"),
    ("Serius-dalam-Penegakan-Hukum-OJK-Jatuhkan-Total-Denda-Rp2,52-Triliun.aspx",
     "serius-dalam-penegakan-hukum-ojk-jatuhkan-total-denda-rp2-52-triliun"),
    ("Siaran-Pers-Sektor-Jasa-Keuangan-Tetap-Stabil-di-Tengah-Upaya--Pemulihan.aspx",
     "siaran-pers-sektor-jasa-keuangan-tetap-stabil-di-tengah-upaya-pemulihan"),
])
def test_a_page_name_keeps_only_letters_and_digits_between_single_hyphens(page: str, name: str) -> None:
    assert release_id("ojk", date(2026, 1, 1), page) == f"ojk:siaran-pers:2026:{name}"


@pytest.mark.parametrize(("listed", "day"), [
    ("27 Oktober 2026", date(2026, 10, 27)),
    ("4 Maret 2025", date(2025, 3, 4)),
    ("11 Nopember 2021", date(2021, 11, 11)),  # the older spelling
    (" 17 Agustus 2020 ", date(2020, 8, 17)),
])
def test_a_listed_date_is_read_in_indonesian(listed: str, day: date) -> None:
    assert listed_date(listed) == day


def test_a_listed_date_that_is_not_a_date_says_so() -> None:
    with pytest.raises(ValueError, match="not a date: '12-10-2023 15.01'"):
        listed_date("12-10-2023 15.01")


@pytest.mark.parametrize(("text", "found"), [
    ("SP 188/DKPU/OJK/X/2026\u200b\n\nSIARAN PERS\n\nOJK CABUT IZIN", "SP 188/DKPU/OJK/X/2026"),
    ("\u200b\n\nSP-157/GKPB/OJK/X/2024\n\nSIARAN PERS", "SP-157/GKPB/OJK/X/2024"),
    ("SP 60 /GKPB/OJK/V/2024\n\nSIARAN PERS", "SP 60 /GKPB/OJK/V/2024"),
    ("SIARAN PERS BERSAMA\n\nKSSK\n\nJakarta, 27 Oktober 2021. Komite (SP 1/2021 dibahas)", None),
])
def test_a_number_is_a_line_of_its_own_near_the_top(text: str, found: str | None) -> None:
    assert number(text) == found
