"""A report's PDF read by metamorph-pdf-text, the extraction every connector shares: the text layer, MinerU's
layout and OCR (the only OCR engine allowed), page furniture removed. Readings are cached in data/mineru-cache.

A report is read with a role other than the regulation's, so MinerU's lighter tier reads it: a report is no legal
text, and the vision model's care with list markers buys nothing here.
"""

from __future__ import annotations

from typing import Protocol

from metamorph_contract import join_pages
from metamorph_pdf_text import ExtractedPdf, ExtractionFailed, ExtractionUnavailable

from reports.application.ports import ReadingFailed, ReadText

ROLE = "report"
NO_SERVICE = "MinerU is needed to read a report: set METAMORPH_MINERU_URL (and METAMORPH_MINERU_CACHE)"


class Extract(Protocol):
    def run(self, pdf: bytes, role: str) -> ExtractedPdf: ...


class PdfText:
    def __init__(self, extract: Extract | None) -> None:
        self.extract = extract  # None when no MinerU service is configured

    def read(self, pdf: bytes) -> ReadText:
        if self.extract is None:
            raise ReadingFailed(NO_SERVICE)
        try:
            extracted = self.extract.run(pdf, ROLE)
        except (ExtractionUnavailable, ExtractionFailed) as error:
            raise ReadingFailed(f"MinerU: {error}") from error
        read = extracted.extraction
        return ReadText(
            text=join_pages(list(extracted.pages)),
            pages=len(extracted.pages),
            method=extracted.method,
            engine=read.engine,
            engine_version=read.engine_version,
            tier=str(read.tier),
            ocr_mode=str(read.ocr_mode),
            pages_ocrd=read.pages_ocrd,
            pages_fallen_back=read.pages_fallen_back,
        )
