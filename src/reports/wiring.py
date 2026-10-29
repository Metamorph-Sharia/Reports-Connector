"""Composition root: the only module that knows every concrete class. Builds adapters, hands them to use cases.

A report is read by metamorph-pdf-text with MinerU, the only OCR engine allowed, when METAMORPH_MINERU_URL is set.
Without it, reports are kept unread, and `reports read` reads them once it is.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from metamorph_pdf_text import ExtractPdf
from metamorph_pdf_text.adapters.file_cache import FileResultCache
from metamorph_pdf_text.adapters.mineru_reader import MinerUReader
from metamorph_pdf_text.adapters.pymupdf_reader import PyMuPdfReader
from metamorph_pdf_text.adapters.vocabulary import load_vocabulary

from reports import __version__
from reports.adapters.pdf.pdf_text import PdfText
from reports.adapters.storage.market_bundle import MarketBundleExporter
from reports.adapters.storage.sqlite import SqliteStore
from reports.adapters.web.ojk_lpksi import OjkLpksi
from reports.adapters.web.ojk_releases import OjkReleases
from reports.adapters.web.ojk_site import OjkSite
from reports.application.ports import Reader
from reports.application.use_cases.check_health import CheckHealth
from reports.application.use_cases.export_bundle import ExportBundle
from reports.application.use_cases.import_report import ImportReport
from reports.application.use_cases.read_unread import ReadUnread
from reports.application.use_cases.status import Status
from reports.application.use_cases.sync_lpksi import SyncLpksi
from reports.application.use_cases.sync_releases import SyncReleases
from reports.config import Config


@dataclass(frozen=True)
class Application:
    sync: SyncLpksi
    sync_releases: SyncReleases
    import_report: ImportReport
    read_unread: ReadUnread
    export_bundle: ExportBundle
    check_health: CheckHealth
    status: Status


def reader(config: Config) -> Reader:
    if not config.mineru_url:
        return PdfText(None)
    service = MinerUReader(config.mineru_url, config.mineru_api_key)
    return PdfText(ExtractPdf(service, PyMuPdfReader(), FileResultCache(config.mineru_cache), load_vocabulary()))


def build(config: Config) -> Application:
    store = SqliteStore(config.data)
    site = OjkSite(user_agent=config.user_agent)  # one client, so both sources share one pace
    import_report = ImportReport(store, reader(config), now=lambda: datetime.now(UTC))
    return Application(
        sync=SyncLpksi(OjkLpksi(site), store, import_report, now=lambda: datetime.now(UTC)),
        sync_releases=SyncReleases(OjkReleases(site), store, since=config.releases_since,
                                   now=lambda: datetime.now(UTC)),
        import_report=import_report,
        read_unread=ReadUnread(store, import_report),
        export_bundle=ExportBundle(store, MarketBundleExporter(connector_version=__version__)),
        check_health=CheckHealth(store),
        status=Status(store),
    )
