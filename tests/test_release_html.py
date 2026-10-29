"""A release's page → its body as published, and its words: one general rule on the HTML, never one per release."""

from __future__ import annotations

from pathlib import Path

from reports.adapters.web.release_html import body, pdf, text

FIXTURES = Path(__file__).parent / "fixtures"
PORTO = (FIXTURES / "release-porto-ventura.html").read_text(encoding="utf-8")
RDK = (FIXTURES / "release-rdkb-september-2026.html").read_text(encoding="utf-8")
KSSK = (FIXTURES / "release-kssk-2021.html").read_text(encoding="utf-8")


def paragraphs(html: str) -> list[str]:
    return text(body(html)).split("\n\n")


def test_the_body_is_the_release_alone_without_the_sites_menus_or_other_articles() -> None:
    found = body(PORTO)

    assert found.startswith('<div id="summary">') and found.endswith("</div>")
    assert "Porto Ventura" in found
    assert "Artikel Lain" not in found and "Tentang OJK" not in found


def test_the_words_come_in_paragraphs_with_the_number_first() -> None:
    found = paragraphs(PORTO)

    assert found[0] == "SP 188/DKPU/OJK/X/2026"
    assert found[3].startswith("Jakarta, 8 Oktober 2026. Otoritas Jasa Keuangan (OJK) sesuai dengan Surat Keputusan")
    assert "humas@ojk.go.id" in found[-1]  # the press contact closes every release


def test_hidden_labels_are_not_words_of_the_release() -> None:
    assert "Page Content" not in text(body(PORTO))


def test_list_items_are_lines_of_one_paragraph() -> None:
    (items,) = [paragraph for paragraph in paragraphs(PORTO) if paragraph.startswith("Menyelesaikan hak")]

    assert items.splitlines()[1].startswith("Menyelenggarakan rapat umum pemegang saham")


def test_inline_words_stay_in_their_sentence() -> None:
    assert any("serta very strong El Nino yang berpotensi" in paragraph for paragraph in paragraphs(RDK))


def test_a_table_is_one_paragraph_of_rows_with_their_cells() -> None:
    tables = [paragraph for paragraph in paragraphs(RDK) if " | " in paragraph]

    assert tables
    assert all(len(table.splitlines()) > 1 for table in tables)


def test_a_paragraph_has_no_empty_lines_or_runs_of_spaces() -> None:
    for paragraph in paragraphs(RDK) + paragraphs(KSSK):
        assert paragraph.strip() and "  " not in paragraph and "\n\n" not in paragraph
        assert all(line.strip() == line and line for line in paragraph.splitlines())


def test_a_release_without_a_number_starts_with_its_heading() -> None:
    assert paragraphs(KSSK)[0].upper().startswith("SIARAN PERS")


def test_the_page_links_the_release_as_a_pdf() -> None:
    assert pdf(PORTO, "https://ojk.go.id/x") == (
        "https://ojk.go.id/id/berita-dan-kegiatan/siaran-pers/Documents/Pages/"
        "OJK-Cabut-Izin-Usaha-PT-Porto-Ventura-Kapital/SP%20188%20OJK%20Cabut%20Izin%20Usaha%20PT%20Porto%20Ventura"
        "%20Kapital.pdf"
    )
