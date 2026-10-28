"""A report's PDF read by metamorph-pdf-text: its pages joined with markers, how it was read kept beside them."""

from __future__ import annotations

import pytest
from metamorph_pdf_text import (
    TEXT_LAYER,
    ExtractedPdf,
    Extraction,
    ExtractionFailed,
    ExtractionUnavailable,
    OcrMode,
    Tier,
)

from reports.adapters.pdf.pdf_text import ROLE, PdfText
from reports.application.ports import ReadingFailed


class StubExtract:
    def __init__(self, error: Exception | None = None) -> None:
        self.error = error
        self.roles: list[str] = []

    def run(self, pdf: bytes, role: str) -> ExtractedPdf:
        self.roles.append(role)
        if self.error:
            raise self.error
        extraction = Extraction("mineru", "4.0.12+t1", Tier.BASIC, OcrMode.AUTO, pages_ocrd=1, pages_fallen_back=0)
        return ExtractedPdf(("Keuangan Syariah", "Perbankan Syariah"), TEXT_LAYER, extraction, ())


def test_pages_are_joined_with_their_markers_and_the_reading_kept() -> None:
    extract = StubExtract()

    read = PdfText(extract).read(b"%PDF")

    assert read.text == "<!-- page 1 -->\nKeuangan Syariah\n\n<!-- page 2 -->\nPerbankan Syariah"
    assert (read.pages, read.method, read.tier, read.ocr_mode, read.pages_ocrd) == (2, "text_layer", "basic", "auto", 1)
    assert extract.roles == [ROLE]  # not the regulation's role: a report is read with the lighter tier


@pytest.mark.parametrize("error", [ExtractionUnavailable("busy"), ExtractionFailed("bad file")])
def test_mineru_unavailable_or_failing_is_a_reading_failed(error: Exception) -> None:
    with pytest.raises(ReadingFailed, match="MinerU"):
        PdfText(StubExtract(error)).read(b"%PDF")


def test_without_mineru_a_report_cannot_be_read() -> None:
    with pytest.raises(ReadingFailed, match="METAMORPH_MINERU_URL"):
        PdfText(None).read(b"%PDF")
