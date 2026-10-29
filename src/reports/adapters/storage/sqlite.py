"""The connector's state in data/: reports.sqlite (each report and how it was read, each release, the syncs and how
far the release listing was walked) and files/<sha256> (each PDF as published, each text as read, each release's
body as published)."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import asdict
from pathlib import Path

from reports.application.ports import KeptRelease, KeptReport, Reading
from reports.domain.releases import Release
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
CREATE TABLE IF NOT EXISTS release (
    id           TEXT PRIMARY KEY,
    release      TEXT NOT NULL,  -- the Release, as JSON
    published_on TEXT NOT NULL,
    body         TEXT NOT NULL,  -- sha256 in files/
    text         TEXT NOT NULL,
    page_url     TEXT NOT NULL,
    pdf_url      TEXT,
    fetched_at   TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS walk (since TEXT NOT NULL);  -- the release listing, walked whole back to this date
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

    def keep_release(self, kept: KeptRelease) -> None:
        release = kept.release
        with self.db:
            self.db.execute(
                "INSERT OR REPLACE INTO release (id, release, published_on, body, text, page_url, pdf_url, fetched_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (release.id, json.dumps(asdict(release), ensure_ascii=False), release.published_on, kept.body,
                 kept.text, kept.page_url, kept.pdf_url, kept.fetched_at),
            )

    def release(self, release_id: str) -> KeptRelease | None:
        row = self.db.execute(f"SELECT {_RELEASE_COLUMNS} FROM release WHERE id = ?", (release_id,)).fetchone()
        return _kept_release(row) if row else None

    def releases(self) -> list[KeptRelease]:
        query = f"SELECT {_RELEASE_COLUMNS} FROM release ORDER BY published_on DESC, id DESC"
        return [_kept_release(row) for row in self.db.execute(query)]

    def walked_back_to(self, since: str) -> None:
        with self.db:
            self.db.execute("INSERT INTO walk (since) VALUES (?)", (since,))

    def walked_back(self) -> str | None:
        return self.db.execute("SELECT min(since) FROM walk").fetchone()[0]


_COLUMNS = "report, pdf, page_url, file_url, fetched_at, reading, note"


def _kept(row: tuple) -> KeptReport:
    report, pdf, page_url, file_url, fetched_at, reading, note = row
    return KeptReport(Report(**json.loads(report)), pdf, page_url, file_url, fetched_at,
                      Reading(**json.loads(reading)) if reading else None, note)


_RELEASE_COLUMNS = "release, body, text, page_url, pdf_url, fetched_at"


def _kept_release(row: tuple) -> KeptRelease:
    release, body, text, page_url, pdf_url, fetched_at = row
    return KeptRelease(Release(**json.loads(release)), body, text, page_url, pdf_url, fetched_at)
