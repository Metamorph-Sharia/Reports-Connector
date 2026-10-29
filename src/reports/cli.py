"""`reports`: sync OJK's LPKSI listing and press releases or import a report, read, show, export, check health
(README.md)."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

from reports.application.ports import KeptReport, SourceRefused
from reports.config import Config
from reports.domain.reports import InvalidReport, Report
from reports.wiring import Application, build

EXIT_OK, EXIT_ERROR = 0, 2


def main(argv: Sequence[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    try:
        return arguments.run(build(Config.from_environment()), arguments)
    except (SourceRefused, InvalidReport) as error:
        print(f"reports: stopped: {error}", file=sys.stderr)
        return EXIT_ERROR


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="reports", description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(required=True, metavar="COMMAND")
    commands.add_parser(
        "sync", help="import every LPKSI edition OJK's listing has that isn't kept, then keep every new press release"
    ).set_defaults(run=_sync)
    imported = commands.add_parser("import", help="keep and read a report's PDF, downloaded by a person")
    imported.add_argument("file", type=Path, help="the report's PDF, as published")
    imported.add_argument("--id", required=True, help="issuer:family:edition, or issuer:family:year:name")
    imported.add_argument("--title", required=True, help="as published")
    imported.add_argument("--edition", required=True, help="as titled, e.g. 2024 or 2023-2027")
    imported.add_argument("--published", help="the date it was published (YYYY-MM-DD)")
    imported.add_argument("--url", help="the page that lists it")
    imported.add_argument("--file-url", help="the PDF's address")
    imported.add_argument("--language", default="id")
    imported.set_defaults(run=_import)
    commands.add_parser("read", help="read every report kept but not read yet").set_defaults(run=_read)
    commands.add_parser("status", help="every report kept: pages, how it was read, or why not").set_defaults(
        run=_status
    )
    export = commands.add_parser("export", help="every read report → one market bundle")
    export.add_argument("--out", type=Path, required=True, help="an empty directory for the bundle")
    export.add_argument("--run-id", default=datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ"))
    export.set_defaults(run=_export)
    commands.add_parser("health", help="exit 0 ok / 1 warning / 2 critical").set_defaults(run=_health)
    return parser


def _sync(app: Application, _: argparse.Namespace) -> int:
    for synced in app.sync():
        print(f"{synced.report_id or synced.url}: {synced.note}", flush=True)
    for release in app.sync_releases():
        print(f"{release.release_id or release.url}: {release.note}", flush=True)
    return EXIT_OK


def _import(app: Application, arguments: argparse.Namespace) -> int:
    report = Report.named(arguments.id, title=arguments.title, edition=arguments.edition,
                          published_on=arguments.published, language=arguments.language)
    _print(app.import_report(arguments.file.read_bytes(), report, page_url=arguments.url, file_url=arguments.file_url))
    return EXIT_OK


def _read(app: Application, _: argparse.Namespace) -> int:
    for kept in app.read_unread():
        _print(kept)
    return EXIT_OK


def _print(kept: KeptReport) -> None:
    reading = kept.reading
    shown = f"{reading.pages} pages, {reading.method}" if reading else f"unread: {kept.note}"
    print(f"{kept.report.id}: {shown}", flush=True)


def _status(app: Application, _: argparse.Namespace) -> int:
    for line in app.status():
        print(line)
    return EXIT_OK


def _export(app: Application, arguments: argparse.Namespace) -> int:
    count = app.export_bundle(arguments.out, arguments.run_id)
    print(f"{count} records → {arguments.out}")
    return EXIT_OK


def _health(app: Application, _: argparse.Namespace) -> int:
    health = app.check_health(today=datetime.now(UTC).date())
    print(f"{health.severity.name.lower()}: {health.message}")
    return int(health.severity)
