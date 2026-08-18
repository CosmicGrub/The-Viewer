# THE VIEWER — Master Architecture

**An offline search engine with a dynamic GUI for military Technical Manuals.**
Modeled on EMS-NG, taking cues from IADS and Adobe — the best of all worlds.

- **Document status:** Draft v0.1 (architecture & design only — no application code yet)
- **Date:** 2026-06-01
- **Owner:** Chris
- **Platform:** Windows (offline / air-gap capable)

---

## 0. Standing rules (apply to every future change)

These two rules govern all work on THE VIEWER, forever, unless you explicitly retire them.

1. **Backwards compatibility is mandatory.** Every change must preserve backwards compatibility for future reference, continuity, and rollbacks. No breaking changes to data formats, schemas, file layouts, or APIs without a versioned migration path and a way to roll back. Old data and old versions stay readable.
2. **A diagram accompanies every addition.** Whenever anything is added to THE VIEWER, you get a diagram showing how the new piece works and how data is queued/flows through the app — presented before or alongside the change.

See `DECISIONS.md` for the running decision log and version history.

---

## 1. What we are building (and why)

A Windows program that lets a mechanic — junior or expert — find any answer buried in a pile of ~7,300 PDFs, 13,700 images, and thousands of legacy IETM files, in seconds, with no internet.

The current reality of the dataset (folder: `E:\ALL MILITARY TMS`):

| Measure | Value |
|---|---|
| Total files | ~39,700 |
| Total size | ~85 GB |
| Top-level categories | ~70 (MRAPs, Abrams, Bradley, HEMTT, HMMWV, 5-ton, dozers, cranes, generators, engines, etc.) |
| PDFs | 7,315 |
| JPG images | 13,695 |
| Legacy EMS/IETM graphics (`.svgz`) | 6,320 |
| XFDL forms | 1,877 |
| Word `.doc` / PowerPoint `.ppt` | 880 / 442 |

The legacy `ALL EMS VEIWER FILES` folder contains the original EMS-NG / IETM **installers** (MSI + CAB) and their extracted image sets. THE VIEWER does **not** depend on that old viewer — it indexes the raw source content directly, so we own the whole pipeline and surpass EMS-NG instead of being limited by it.

### Goals (from the project brief)

- **A — Find anything.** Locate any information inside the TMs/PDFs/other files to solve mechanical problems faster.
- **B — Search every way.** Classic `Ctrl+F` find-in-document **plus** offline Google-style predictive, typo-tolerant search (faster than online because it is local).
- **C — Complete procedures.** Once a part/answer is found, show the full rundown: disassembly, assembly/install, required tools, and the clearly-stated differences between parts that look identical but are functionally different.
- **D — Dynamic graphics.** Go beyond the photos inside the PDFs — add dynamic diagrams, both simple and advanced, for young mechanics and subject-matter experts alike.
- **E — Effortless ingestion.** Add any new PDF/file to the system without a sweat.

---

## 2. Decisions locked for this build

| Area | Decision | Why |
|---|---|---|
| App shell | **Local web app** — a small Windows background service serving a browser UI | Easiest path to rich IADS/Adobe-style dynamic graphics, predictive search and `Ctrl+F`; fully offline; easiest to extend |
| Search core | **SQLite + FTS5** (full-text search 5) | Zero-install, single portable file, extremely backwards-compatible and rollback-friendly; fast full-text + prefix/predictive search |
| Indexing strategy | **Text-first, OCR queued for later** | Get a working search engine fast over already-readable text; OCR the scanned/image PDFs as a background job afterward |
| First milestone | **Full architecture + diagrams only** (this document) | Approve the blueprint before any code is written |

---

## 3. System architecture (high level)

THE VIEWER is four cooperating parts plus the data:

1. **The Corpus** — your existing `E:\ALL MILITARY TMS` folder, left exactly as-is. THE VIEWER only ever *reads* it. It is never moved or modified. (Backwards-compatibility rule: the source of truth is untouched.)
2. **The Ingestion Pipeline** — a background worker that crawls the corpus, extracts text + metadata + images, and writes them into the index. Runs incrementally and can be re-run safely at any time.
3. **The Index Store** — a versioned SQLite database (`viewer.db`) holding the full-text search index, document/part metadata, extracted graphics references, and procedure links. This is the brain.
4. **The Application Service** — a small local web server (the "engine") that answers searches from the Index Store and serves the UI and the original documents.
5. **The GUI** — the browser-based front end: search bar with live predictive results, document viewer with in-page `Ctrl+F`, procedure panels, and the dynamic graphics layer.

```
  [ E:\ALL MILITARY TMS ]      <- read-only source of truth, never modified
            |
            v
  [ Ingestion Pipeline ]       <- crawl, extract, queue, OCR-later
            |
            v
  [ Index Store: viewer.db ]   <- SQLite + FTS5, versioned
            ^
            |
  [ Application Service ]       <- local web engine (offline)
            ^
            |
  [ GUI in browser ]           <- search, view, procedures, dynamic graphics
```

The rendered, detailed versions of this live in `docs/diagrams/` (see Section 9).

---

## 4. The ingestion pipeline & data queue (how data flows in)

This is the heart of "extract all the information" and "add new files without a sweat." It is built as a **queue of jobs** so it can run for hours, be paused, resumed, and re-run without ever corrupting the index.

### 4.1 Stages

1. **Crawl / Watch.** Walk every folder and subfolder of the corpus. For each file, compute a content fingerprint (hash) + size + modified-time. New or changed files become jobs; unchanged files are skipped. A folder watcher later makes this automatic when you drop in a new file (Goal E).
2. **Classify.** Decide what each file is and how to handle it: text-PDF, scanned/image-PDF, image, Office doc, legacy IETM asset, CAD/drawing, video, etc.
3. **Extract — text first.** For text-based PDFs and Office docs, pull the text, page by page, with page numbers preserved. Capture metadata (TM number, NSN, title, vehicle, document type) where detectable.
4. **Queue for OCR (deferred).** Scanned/image-only PDFs and standalone images are recorded now but their text-extraction job is parked in an **OCR queue** with status `pending_ocr`. The document is already searchable by filename/metadata immediately; its body text fills in when OCR runs later.
5. **Extract graphics.** Pull embedded images/figures and references to the legacy `.svgz`/`.svg` graphics so the dynamic-graphics layer (Goal D) has source material.
6. **Index.** Write text into FTS5, write metadata into the relational tables, link figures and procedures.
7. **Report.** Every run records counts (files seen / new / changed / indexed / queued / failed) so you can see progress on 85 GB over time.

### 4.2 Job states (the queue)

```
discovered -> classified -> extracting -> indexed
                   \-> pending_ocr -> ocr_running -> indexed
   any stage -> failed (with reason, retryable)
```

Each job row carries its state, attempt count, and last error. Because state lives in the database, a crash or shutdown loses nothing — re-running resumes exactly where it left off. **This is the queue mechanism the standing diagram rule refers to**, and it is drawn explicitly in `docs/diagrams/02-ingestion-data-flow.mmd`.

### 4.3 Re-runs and safety

- The pipeline is **idempotent**: running it twice produces the same index, no duplicates (fingerprints dedupe).
- It only ever reads the corpus; all writes go to `viewer.db` and a separate derived-assets folder.
- A run can be stopped at any time; partial progress is durable.

---

## 5. Data model & backwards-compatibility strategy

The index is a single SQLite file, `viewer.db`. SQLite is chosen partly *because* it is the most backwards-compatible store available — the file format has been forward/backward compatible since 2004 and is explicitly committed to staying that way.

### 5.1 Versioning (the backbone of the standing compatibility rule)

- A `schema_meta` table records `schema_version` and a full migration history (when, from, to, notes).
- All schema changes are **additive and migrated**: new columns are added as nullable/defaulted; old columns are never repurposed or dropped destructively. Old readers keep working.
- Each migration is a numbered, additive-only script (`migrations/0001_init.sql`, `0002_*.sql`, …) — `ADD COLUMN`/`CREATE TABLE IF NOT EXISTS`, never a destructive `ALTER`/`DROP`. SQLite has no clean per-migration undo for that shape of change, so the practical rollback mechanism is the whole-DB snapshot below, not a per-file down-script.
- Before applying any *pending* migration, `viewer_ingest.py migrate()` backs up `viewer.db` via `safeguard.backupdb()` (a consistent `VACUUM INTO` copy, integrity-checked, written to `backups/db/viewer-YYYYMMDD-HHMM.db`) — so a rollback is always one file-copy away. Gated on there actually being pending migrations, so the common case (nothing to migrate) doesn't pay a multi-GB backup cost on every CLI invocation; a backup failure aborts the migration rather than proceeding with no rollback path.
- The corpus itself is never written to, so the original documents are an untouchable backstop.

### 5.2 Core tables (conceptual)

| Table | Holds |
|---|---|
| `documents` | One row per source file: path, fingerprint, type, TM number, NSN(s), title, vehicle/system, page count, status |
| `pages` | One row per page: document, page number, extracted text, OCR status |
| `pages_fts` | FTS5 virtual table mirroring page text for fast full-text + predictive search |
| `parts` | Recognized parts: name, part/NSN number, the document/pages that describe it |
| `part_variants` | Look-alike parts and the **clearly-stated differences** between them (Goal C) |
| `procedures` | Disassembly / assembly / install procedures: steps, required tools, linked parts |
| `figures` | Extracted images & graphics references, linked to documents/pages/parts |
| `jobs` | The ingestion queue: file, stage, state, attempts, last error |
| `schema_meta` | Schema version + migration history |
| `runs` | Ingestion run log: timestamps and counts for progress tracking |

`parts`, `part_variants`, and `procedures` are populated progressively — early runs fill `documents`/`pages`/`pages_fts` (making everything findable), and richer structure is layered on without breaking what already exists.

---

## 6. Search (Goal A & B)

Three search modes share one index:

1. **Predictive / instant search** — as you type, FTS5 prefix queries (`term*`) return suggestions and live results, Google-style but local-fast. Ranked by BM25 relevance with boosts for title/TM-number/NSN hits.
2. **Typo tolerance** — a lightweight fuzzy layer (trigram matching over a vocabulary table) catches misspellings and OCR noise, so "alternator" still finds "alternator." (FTS5 stays the speed core; the fuzzy layer only kicks in to widen recall.)
3. **In-document `Ctrl+F`** — once a document is open, classic find-in-page highlights and jumps between every match, independent of the global index.

Results show the vehicle, TM number, page, and a snippet with the hit highlighted, then deep-link straight to that page in the viewer.

---

## 7. Procedures & part disambiguation (Goal C)

When a part or answer is found, the procedure panel assembles, from the indexed content:

- **Disassembly** steps for removing the part/material from the vehicle.
- **Assembly / install** steps for putting it on.
- **Required tools** for each procedure.
- **Look-alike differences** — the `part_variants` table surfaces parts that look identical but are functionally different, with the distinguishing features called out plainly and, where possible, a side-by-side visual.

This structure is defined now; it is filled in over successive ingestion passes and curation, additively, so no later enrichment breaks earlier data.

---

## 8. Dynamic graphics layer (Goal D)

Beyond the static photos inside the PDFs, the GUI renders an interactive graphics layer driven by web tech (SVG/Canvas/WebGL in the browser):

- **Simple mode** for junior mechanics — clean callouts, highlighted parts, step-by-step visual sequences.
- **Advanced mode** for SMEs — detailed schematics, exploded/zoomable views, layered diagrams.
- The legacy `.svgz`/`.svg` IETM graphics (6,000+ of them) are a ready source to clean up, vectorize, and make interactive rather than starting from scratch.
- This layer is also where the Adobe-class tooling (available in this environment) can generate/clean diagrams over time.

Each future graphics feature ships with its own data-flow diagram per the standing rule.

---

## 9. Diagrams (this delivery)

Version-controlled diagram sources live in `docs/diagrams/` as Mermaid text (`.mmd`) — text so they diff cleanly and render anywhere, forever (backwards-compatible by design). An offline viewer, `docs/diagrams/viewer.html`, renders all of them with no internet.

| File | Shows |
|---|---|
| `01-system-architecture.mmd` | The five parts and how they connect |
| `02-ingestion-data-flow.mmd` | The crawl→extract→queue→index flow and the OCR-later queue |
| `03-search-query-flow.mmd` | What happens from keystroke to highlighted result |
| `04-data-model.mmd` | The database tables and their relationships |

---

## 10. Roadmap (after this approval)

1. **M1 (this doc):** Architecture + diagrams. ✅
2. **M2:** Build the index schema + migrations and a working ingestion pipeline; prove it end-to-end on a few vehicle folders.
3. **M3:** Run text-first ingestion across the full 85 GB; stand up the search UI with predictive search + `Ctrl+F`.
4. **M4:** OCR background pass over scanned PDFs; fold results into the index.
5. **M5:** Procedure panels + part-variant disambiguation.
6. **M6:** Dynamic graphics layer (simple + advanced).
7. **Ongoing:** Folder-watch auto-ingest for new files (Goal E).

Every milestone obeys both standing rules: backwards-compatible changes only, and a fresh data-flow diagram with each addition.

---

## 11. v0.96.0 — The restructured server (2026-06-10; supersedes the §3 description of viewer_app.py)

*(Appended per R6 — earlier sections retained verbatim as the historical record. The engine layout below
is current as of v0.96.0; the original monolith is preserved at `backups/pre-v0.96-restructure/`.)*

### Engine layout

    engine/
      viewer_app.py          ~330-line SHELL: config, per-thread SQLite plumbing (db()/_ReuseConn),
                             RPS init, rotating error log, Handler (registry dispatch inside ONE
                             error boundary), graceful main(). Re-exports every public name, so
                             `import viewer_app as V` is unchanged for tests and scripts.
      theme.py               single source of truth for the dark-theme tokens (UI + diagrams)
      patterns.py            canonical NSN / FIG / part-number regexes + tm_side (now actually imported)
      features/              the domain logic, one module per area (moved VERBATIM from the monolith):
        registry.py          declarative {path: handler} GET/POST maps + ParamError + qint/qstr/qflag
                             central validation (bad client input → 400, hard row ceilings)
        routes.py            every endpoint declared once; static pages/scripts as data tables
        search_feature.py    synonyms/keywords/tags · offline fuzzy · type-ahead · FTS search · find-in-doc
        parts_feature.py     NSN correlations/NIIN review · look-alike recognizer · references · learning
        browse_feature.py    vehicle hub · sides · 3D + schematics lists · coverage · status/ops
        procedures_feature.py  work-package parsing · torque specs
        render_feature.py    fitz/Poppler page render · RPS page cache · word boxes · OCR callouts
        ingest_feature.py    add-docs preview/start/status (canonicalized paths, optional roots fence)
        sessions_feature.py  parts-request sessions
      collections_feature.py, sides_feature.py, chapters_feature.py, figures_feature.py,
      rpstl_feature.py, xref_feature.py, xref_online.py, material_feature.py, localmodel.py,
      image3d_experiment.py, procedure_feature.py     ← the EARLIER extractions, unchanged
      ui/                    pages + overlays; NEW: shared.js (the one ES5 helper copy, served at
                             /shared.js) and base.css (the one token sheet, served at /base.css)

**Dependency injection (unchanged pattern):** the shell injects itself as `<module>.core`; modules call
`core.db() / core.DB_PATH / core.tm_side …` at call time. No import cycles; `--db` and RPS-mode changes
propagate; the index stays read-only to the server (R1).

### Request lifecycle (hardened, v0.96.0)

    browser → Handler (timeout · same-origin POST check · 8 MB body cap)
            → registry lookup {path → handler}            (was ~90 if/elif blocks)
            → param validation (qint/qstr/qflag → 400 on bad input)
            → feature handler (verbatim domain logic)
            → ONE error boundary: ParamError→400 · FileNotFoundError→404 ·
              anything else → logged (engine/logs/server-errors.log, rotating) + generic 500 w/ ref id

`/page` is traversal-safe by construction: documents are addressed only by id; the filesystem path always
comes from the `documents` table. `/healthz`, `/api/status`, `/api/ops` carry `VERSION`. Graceful Ctrl+C
checkpoints the WAL. Binds 127.0.0.1 unless `--host` says otherwise.

### Gates (run with every change)

`tests/verify_all.py` (= `VERIFY-ALL.bat`) no longer runs a fixed, hand-maintained list of suites —
it **auto-discovers every `test_*.py` file** in `engine/tests/` via `glob.glob(os.path.join(HERE,
"test_*.py"))`, runs each as its own subprocess (900s timeout each, so a hang fails loudly instead
of blocking the gate forever), then runs `rps_lint.py` (the ES5/legacy gate — all 31 UI files
classified) and `safeguard verify`. This replaced an earlier hardcoded tuple of suite names after
that tuple let `test_procedure.py` — the one suite that would have caught `procedure_feature.py`'s
`i -= 1` infinite-loop typo — go silently unexecuted; at the same time 9 *other* real `test_*.py`
files (~1,200 lines combined) were also never run here, for the identical reason. See
`verify_all.py`'s own comment above its `glob.glob()` call for the full incident writeup. There are
23 `test_*.py` files today, and a new one joins the gate automatically the moment it's added —
nothing else to remember, and nothing here to go stale again.

Pushes and PRs to `main` now also run `tests/verify_all.py --snapshot` automatically, via GitHub
Actions (`.github/workflows/ci.yml`) — the project's first CI of any kind.
