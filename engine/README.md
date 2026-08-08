# THE VIEWER — Indexing Engine

The ingestion + OCR indexing pipeline that builds the searchable index for THE VIEWER.
Offline, Windows-friendly, backwards-compatible, and resumable.

## What it does

1. **Crawls** `E:\ALL MILITARY TMS` (read-only — your files are never modified).
2. **Text-first**: pulls embedded text from every readable PDF page and indexes it
   immediately into a SQLite **FTS5** full-text index (`index\viewer.db`).
3. **Queues** scanned/image-only pages as `pending_ocr`.
4. **OCR worker** rasterizes those pages (`pdftoppm`) and reads them with `tesseract`,
   writing the recovered text into the same index — so search keeps getting better.

It is **idempotent** (re-running skips unchanged files) and **resumable** (state lives in
the database; stop anytime and re-run).

## Prerequisites (install once, add each to your PATH)

- **Python 3** — https://www.python.org/downloads/  (check "Add Python to PATH")
- **Poppler for Windows** (provides `pdftotext`, `pdfinfo`, `pdftoppm`)
  — e.g. the `poppler-windows` release; add its `bin` folder to PATH.
- **Tesseract-OCR** (provides `tesseract`) — e.g. the UB-Mannheim installer; add to PATH.

No internet is needed once these are installed.

## Easiest way to run

Double-click **`run_indexing.bat`**. It checks prerequisites, runs the fast text-first
crawl, then loops the OCR worker until every scanned page is done. You can close it and
re-run later; it resumes.

## Manual commands

```
python viewer_ingest.py crawl  --root "E:\ALL MILITARY TMS"      # text-first index
python viewer_ingest.py ocr    --limit 500 --workers 4           # OCR a batch (repeat)
python viewer_ingest.py run    --root "E:\ALL MILITARY TMS" --workers 4   # crawl then OCR all
python viewer_ingest.py status                                   # progress counts
python viewer_ingest.py search "dual voltage alternator"         # quick search test
```

- `--workers` = number of OCR processes. A good value is your CPU core count.
- The index is written to `..\index\viewer.db` by default (override with `--db`).

## Scale expectations

The corpus is ~7,300 PDFs / ~85 GB. The **text-first** pass is fast and makes most of the
library searchable quickly. **OCR is the long pole** — it processes scanned pages one at a
time (a few per second across several cores), so the full pass runs for hours and is meant
to grind in the background. Because it is resumable, you never lose progress.

## Backwards compatibility (standing rule R1)

- The source corpus is opened **read-only**; it is never changed.
- The index schema is **versioned** (`schema_meta`) and upgraded only by numbered,
  additive migrations in `migrations\` — old data stays readable, changes are rollbackable.
- The index is always **rebuildable from scratch** from the read-only corpus — the ultimate
  rollback.

## Files

```
engine\
  viewer_ingest.py        the pipeline (crawl / ocr / run / status / search)
  run_indexing.bat        one-click Windows launcher
  migrations\0001_init.sql  initial schema (FTS5 + jobs queue + versioning)
  README.md               this file
..\index\viewer.db        the search index (created by the pipeline)
..\docs\                   architecture + data-flow diagrams
```

A sample index built from a representative subset (HMMWV, Buffalo MRAP, M113, Cummins,
generators) ships as `..\index\viewer_index.db` so you can see real results immediately.
