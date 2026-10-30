# Reports-Connector

Regulators' reports, roadmaps and masterplans, and OJK's press releases, exported under Metamorph's market contract (`metamorph-market-contract`):
- **reports** (kind `report`): OJK's *Laporan Perkembangan Keuangan Syariah Indonesia* (LPKSI), BI's *Kajian Ekonomi dan Keuangan Syariah Indonesia* (KEKSI), OJK's sharia banking roadmap (RP3SI) and fintech lending roadmap. Phase 4 of the market data layer;
- **releases** (kind `release`): OJK's press releases (*Siaran Pers*) since 2020, every sector. Phase 5.

The plan is [Metamorph-Knowledge-Platform/docs/market-data-layer-plan.md](../Metamorph-Knowledge-Platform/docs/market-data-layer-plan.md).

**Neither has legal force.** A report says what a regulator reports or plans; a release says what it announced. One announcing a regulation is not the regulation. Both are kept out of the regulation layer.

## How reports arrive

- **`reports sync`** reads [OJK's LPKSI listing](https://ojk.go.id/id/kanal/syariah/data-dan-statistik/laporan-perkembangan-keuangan-syariah-indonesia/Default.aspx): one page per edition (2016–2025 on 2026-10-28), each linking its PDF.
  - The edition comes from the page's title (`Laporan Perkembangan Keuangan Syariah Indonesia 2025` → `ojk:lpksi:2025`), invisible characters aside.
  - An edition kept already costs its page only. A page that names no edition, or links no single PDF, is noted for a person.
- **`reports import FILE --id … --title … --edition …`** keeps a report downloaded by hand: KEKSI, since bi.go.id refuses connectors, and the roadmaps, which come once per period. For example:

  ```bash
  uv run reports import ~/Downloads/RP3SI.pdf --id ojk:roadmap:2023:rp3si \
    --title "Roadmap Pengembangan dan Penguatan Perbankan Syariah Indonesia 2023-2027" --edition 2023-2027 \
    --url "https://ojk.go.id/id/Publikasi/Roadmap-dan-Pedoman/Syariah/Perbankan-Syariah-Indonesia/Pages/Roadmap-Pengembangan-dan-Penguatan-Perbankan-Syariah-Indonesia-2023-2027.aspx"
  ```

**IDs:** `{issuer}:{family}:{edition}` for a yearly report (`ojk:lpksi:2025`, `bi:keksi:2024`), or `{issuer}:{family}:{year}:{name}` for one among others (`ojk:roadmap:2023:rp3si`, `ojk:roadmap:2023:lpbbti`).

## How releases arrive

`reports sync` also walks [OJK's press release listing](https://ojk.go.id/id/berita-dan-kegiatan/siaran-pers/Default.aspx), ten releases a page, newest first:
- **Older pages come through the pager's own postback:** the page's form, with its state, posted back naming the pager link, as the page's scripts do when a person clicks it. A pager that doesn't move forward stops the run.
- **Each release not kept** costs its page. Its body (`<div id="summary">`) is kept as published, and its words are taken from it by one general rule (`adapters/web/release_html.py`):
  - blocks end paragraphs;
  - line breaks, table rows and list items end lines;
  - cells are joined by ` | `;
  - what the page hides, and images, are dropped.
- **Its date** is the listing's (`8 Oktober 2026`). Its own date line is a day earlier in about one in seven, an evening release, so it isn't checked.
- **Its number** (`SP 188/DKPU/OJK/X/2026`) is the line that opens it, when there is one: a few have none, and numbers repeat each year.
- **The walk stops at the first release before `RELEASES_SINCE`** (2020-01-01, about 1,180 releases), and the history is then whole. After that, a sync stops at the first listing page with nothing new: a week costs a page or two and a handful of releases.
- **A walk a refusal stopped goes on where it stopped:** kept releases cost only their listing page.

**IDs:** `{issuer}:siaran-pers:{year}:{name}`, the name being the release's page name in lower case, letters and digits only (`OJK-Cabut-Izin-Usaha-PT-Porto-Ventura-Kapital.aspx` of 8 October 2026 → `ojk:siaran-pers:2026:ojk-cabut-izin-usaha-pt-porto-ventura-kapital`). Two pages that would share an ID keep the first, and the second is noted.

### The first collection of releases

About 1,300 requests, roughly an hour or two at one every two seconds. It runs in a Docker container, outside any terminal session:

```bash
scripts/backfill start    # start it, or resume it where it stopped
scripts/backfill status   # releases kept, how far back, the pace, and the last lines
scripts/backfill log      # follow it (Ctrl-C leaves it running)
scripts/backfill stop     # stop it; start resumes it
```

Keep Airflow's `ingest_reports` paused while it runs: both would sync into the same `data/`.

## How a report is read

By `metamorph-pdf-text`, the extraction every connector shares: the PDF's text layer, MinerU's layout and OCR (the only OCR engine allowed), page furniture removed. Its text is written page by page with `<!-- page N -->` markers, and **the platform cuts it into passages** with their pages. The PDF and the text are both exported as blobs.
- A report is read with MinerU's lighter tier: it is no legal text.
- Every MinerU reading is kept in `data/mineru-cache/`, so a report is never sent to MinerU twice alike.
- **Without MinerU** (`METAMORPH_MINERU_URL` unset, or the service down), a report is kept unread, with the reason. `reports read` reads it once MinerU is back, from the kept PDF.

**Access rules,** as the other connectors':
- Every request names the connector in its User-Agent (`reports/<version>`, plus `REPORTS_CONTACT` if set).
- It makes one request every two seconds, across LPKSI and releases alike, and follows only the links the pages show (and the release listing's pager, as the page posts it).
- **A refusal stops the run:** an HTTP error, or a download that isn't a PDF. Nothing is worked around.

## Commands

| Command | Does |
|---|---|
| `reports sync` | Import every LPKSI edition OJK's listing has that isn't kept, and read again one kept unread; then keep every press release not kept, since `RELEASES_SINCE` |
| `reports import FILE --id ID --title TITLE --edition EDITION [--published DATE] [--url URL] [--file-url URL]` | Keep and read a report downloaded by hand |
| `reports read` | Read every report kept but not read yet |
| `reports status` | Every report kept: its pages and how it was read, or why it isn't; then the releases in one line |
| `reports export --out DIR --run-id ID` | Every read report and every release → one market bundle (a full snapshot) |
| `reports health` | Exit `0` ok, `1` warning (a report unread, the release history not whole yet, or no sync in 14 days), `2` critical (no report read) |

## Settings

| Variable | Default | Meaning |
|---|---|---|
| `REPORTS_DATA` | `data` | Where the connector keeps its state |
| `REPORTS_CONTACT` | none | Added to the User-Agent, e.g. `mailto:team@example.com` |
| `METAMORPH_MINERU_URL` | none | The MinerU service, e.g. `http://host.docker.internal:8010`. Reading a report needs it |
| `METAMORPH_MINERU_API_KEY` | none | Its key, if it was started with one |
| `RELEASES_SINCE` | `2020-01-01` | The oldest press release kept (the project owner's choice, 2026-10-28) |

## State

In `data/`, which Airflow bind-mounts:
- `reports.sqlite`: each report, where it came from, how it was read (or why not); each release with its words; the syncs, and how far back the release listing was walked whole;
- `files/<sha256>`: each PDF as published, each text as read, and each release's body as published;
- `mineru-cache/`: every MinerU reading.

## Development

```bash
uv sync
uv run pytest        # OJK's pages saved on 2026-10-28 (LPKSI, the release listing and its pager, releases); MinerU is a fake
uv run ruff check .
docker build -f Reports-Connector/Dockerfile -t metamorph/reports:dev .   # from the workspace root
```

Layers, inner to outer: `domain` (what a report is, an LPKSI edition's title; a release's ID, date and number), `application` (ports and use cases), `adapters` (ojk.go.id over one HTTP client: LPKSI's listing, the release listing and its pager, a release's HTML; metamorph-pdf-text, SQLite, the market bundle), then `cli`, `wiring` and `config`. `tests/test_architecture.py` keeps dependencies pointing inward, and OCR MinerU's alone.

Airflow runs `ingest_reports` on Mondays: `reports sync` (LPKSI, then releases), then export, then `metamorph market load`, then discard; the load triggers the platform's `market_publish`, which publishes it. That is in the platform's `dags/`.
