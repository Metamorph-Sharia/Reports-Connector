"""The connector's state in data/: reports.sqlite (each report, how it was read, the syncs) and files/<sha256>
(each PDF as published and each text as read)."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import asdict
from pathlib import Path

from reports.application.ports import KeptReport, Reading
from reports.domain.reports import Report

SCHEMA = """
CREATE TABLE IF NOT EXISTS report (
    id         TEXT PRIMARY KEY,
    report     TEXT NOT NULL,  -- the Report, as JSON
    pdf        TEXT NOT NULL,  -- sha256 in files/
    page_url   TEXT,
    file_url   TEXT,
    fetched_at TEXT NOT NULL,
    reading    TEXT,           -- the Reading, as JSON; NULL until read
    note       TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS sync (at TEXT NOT NULL);
"""


class SqliteStore:
    def __init__(self, data: Path) -> None:
        self.files = data / "files"
        self.files.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(data / "reports.sqlite")
        self.db.executescript(SCHEMA)

    def keep_file(self, data: bytes) -> str:
        sha = hashlib.sha256(data).hexdigest()
        path = self.files / sha
        if not path.exists():
            partial = path.with_suffix(".partial")
            partial.write_bytes(data)
            partial.rename(path)  # never a half-written file under its sha
        return sha

    def file(self, sha: str) -> bytes:
        return (self.files / sha).read_bytes()

    def keep_report(self, kept: KeptReport) -> None:
        with self.db:
            self.db.execute(
                "INSERT OR REPLACE INTO report (id, report, pdf, page_url, file_url, fetched_at, reading, note) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (kept.report.id, json.dumps(asdict(kept.report), ensure_ascii=False), kept.pdf, kept.page_url,
                 kept.file_url, kept.fetched_at, json.dumps(asdict(kept.reading)) if kept.reading else None,
                 kept.note),
            )

    def report(self, report_id: str) -> KeptReport | None:
        row = self.db.execute(f"SELECT {_COLUMNS} FROM report WHERE id = ?", (report_id,)).fetchone()
        return _kept(row) if row else None

    def reports(self) -> list[KeptReport]:
        return [_kept(row) for row in self.db.execute(f"SELECT {_COLUMNS} FROM report ORDER BY id")]

    def synced(self, at: str) -> None:
        with self.db:
            self.db.execute("INSERT INTO sync (at) VALUES (?)", (at,))

    def last_synced(self) -> str | None:
        return self.db.execute("SELECT max(at) FROM sync").fetchone()[0]


_COLUMNS = "report, pdf, page_url, file_url, fetched_at, reading, note"


def _kept(row: tuple) -> KeptReport:
    report, pdf, page_url, file_url, fetched_at, reading, note = row
    return KeptReport(Report(**json.loads(report)), pdf, page_url, file_url, fetched_at,
                      Reading(**json.loads(reading)) if reading else None, note)
