# Reports-Connector

Regulators' reports, roadmaps and masterplans, exported as **reports** under Metamorph's market contract (`metamorph-market-contract`, kind `report`): OJK's *Laporan Perkembangan Keuangan Syariah Indonesia* (LPKSI), BI's *Kajian Ekonomi dan Keuangan Syariah Indonesia* (KEKSI), OJK's sharia banking roadmap (RP3SI) and fintech lending roadmap. It is Phase 4 of the market data layer: [Metamorph-Knowledge-Platform/docs/market-data-layer-plan.md](../Metamorph-Knowledge-Platform/docs/market-data-layer-plan.md).

**A report has no legal force.** It says what a regulator reports or plans, never a rule. Reports are kept out of the regulation layer.

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

## How a report is read

By `metamorph-pdf-text`, the extraction every connector shares: the PDF's text layer, MinerU's layout and OCR (the only OCR engine allowed), page furniture removed. Its text is written page by page with `<!-- page N -->` markers, and **the platform cuts it into passages** with their pages. The PDF and the text are both exported as blobs.
- A report is read with MinerU's lighter tier: it is no legal text.
- Every MinerU reading is kept in `data/mineru-cache/`, so a report is never sent to MinerU twice alike.
- **Without MinerU** (`METAMORPH_MINERU_URL` unset, or the service down), a report is kept unread, with the reason. `reports read` reads it once MinerU is back, from the kept PDF.

**Access rules,** as the other connectors':
- Every request names the connector in its User-Agent (`reports/<version>`, plus `REPORTS_CONTACT` if set).
- It makes one request every two seconds, and follows only the links the pages show.
- **A refusal stops the run:** an HTTP error, or a download that isn't a PDF. Nothing is worked around.

## Commands

| Command | Does |
|---|---|
| `reports sync` | Import every LPKSI edition OJK's listing has that isn't kept; read again one kept unread |
| `reports import FILE --id ID --title TITLE --edition EDITION [--published DATE] [--url URL] [--file-url URL]` | Keep and read a report downloaded by hand |
| `reports read` | Read every report kept but not read yet |
| `reports status` | Every report kept: its pages and how it was read, or why it isn't |
| `reports export --out DIR --run-id ID` | Every read report → one market bundle (a full snapshot) |
| `reports health` | Exit `0` ok, `1` warning (a report unread, or no sync in 14 days), `2` critical (nothing read) |

## Settings

| Variable | Default | Meaning |
|---|---|---|
| `REPORTS_DATA` | `data` | Where the connector keeps its state |
| `REPORTS_CONTACT` | none | Added to the User-Agent, e.g. `mailto:team@example.com` |
| `METAMORPH_MINERU_URL` | none | The MinerU service, e.g. `http://host.docker.internal:8010`. Reading a report needs it |
| `METAMORPH_MINERU_API_KEY` | none | Its key, if it was started with one |

## State

In `data/`, which Airflow bind-mounts:
- `reports.sqlite`: each report, where it came from, how it was read (or why not), and the syncs;
- `files/<sha256>`: each PDF as published, and each text as read;
- `mineru-cache/`: every MinerU reading.

## Development

```bash
uv sync
uv run pytest        # OJK's pages saved on 2026-10-28; MinerU is a fake
uv run ruff check .
docker build -f Reports-Connector/Dockerfile -t metamorph/reports:dev .   # from the workspace root
```

Layers, inner to outer: `domain` (what a report is, an LPKSI edition's title), `application` (ports and use cases), `adapters` (OJK's listing over HTTP, metamorph-pdf-text, SQLite, the market bundle), then `cli`, `wiring` and `config`. `tests/test_architecture.py` keeps dependencies pointing inward, and OCR MinerU's alone.

Airflow runs `ingest_reports` on Mondays: `reports sync`, then export, then `metamorph market load --publish`, then discard. That is in the platform's `dags/`.
