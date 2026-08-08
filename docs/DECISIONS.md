# THE VIEWER — Decision Log & Version History

A running record of decisions and changes. Append-only. Newest at top.

## Standing rules (never expire unless explicitly retired)

- **R1 — Backwards compatibility.** Every change preserves backwards compatibility for future reference, continuity, and rollbacks. No breaking changes without a versioned migration path + rollback. Source corpus is read-only and never modified.
- **R2 — Diagram with every addition.** Every addition to THE VIEWER ships with a diagram showing how it works and how data is queued/flows through the app.
- **R3 — Dark diagrams + PDF.** Every diagram must use a professional dark theme and have at least one PDF version saved (dark SVG → PDF via cairosvg, in `docs/diagrams/`).
- **R4 — Changelog with every change.** Every change appends a versioned entry to `docs/CHANGELOG.md` (Keep a Changelog style).
- **R5 — Graphical changelog + PDF.** Every changelog entry also gets a detailed graphical explanation and a functioning diagram in PDF form (panel added to `docs/diagrams/CHANGELOG-VISUAL.svg` → `.pdf`).

---

## 2026-06-01 — Forked into two builds (GPU production + Lite portable)

Split THE VIEWER into two deploy profiles from **one shared codebase** (no divergent forks → R1 safe).

- **Engine (additive):** `viewer_ingest.py` gained `--gpu` (RapidOCR on CUDA via onnxruntime-gpu,
  automatic CPU fallback) and `--dpi` (render DPI). Defaults unchanged.
- **Advanced/GPU production (priority):** master `THE VIEWER`; `engine\run_ocr_gpu.bat`
  (`ocrall --gpu --workers 8 --dpi 200`) + `docs\SETUP-GPU.md`. ~10–30× faster OCR on the NVIDIA GPU.
- **Lite/portable (weaker PC):** `engine\make_portable.py/.bat` builds a self-contained
  `THE VIEWER PORTABLE` folder (engine + finished index + one-click `SETUP.bat` + both-mode CPU
  launchers incl. `run_ocr_lite.bat --workers 2 --dpi 150`) + `docs\SETUP-LITE.md`.
- **Overview:** `docs\FORKS.md`. **Diagram (dark+PDF):** `docs\diagrams\09-forks`.
- Verified: portable assembly excludes GPU-only/diagnostic files and bundles the index + both-mode
  launchers; `--gpu/--dpi` flags parse with CPU fallback.

**Priority going forward:** the GPU/production build leads; the Lite build is kept available and
revisited when Chris is ready.

---

## 2026-06-01 — Search GUI: document viewer added (see the actual page)

Added the "find it → see it" loop to the offline app. New engine endpoints:
`GET /api/doc?id=` (metadata) and `GET /page?doc=&page=&dpi=` which renders the requested
PDF page to PNG on demand with PyMuPDF (no pre-rendering, storage-free). The dark UI now lets
you click any result to open a full-screen document viewer — the real manual page image, with
prev/next page navigation, keyboard arrows/Esc, and an "Add this part" button into the 104th request.
OCR-recovered results are tagged with an `OCR` badge. Verified end-to-end (search + metadata +
real page render).

Diagram (dark + PDF): `docs/diagrams/08-search-gui-viewer`. Files: `engine/viewer_app.py`,
`engine/ui/index.html`. Runs via `engine/run_app.bat`. R1: read-only corpus, additive; R2/R3 satisfied.

---

## 2026-06-01 — New standing rule R3: dark diagrams + PDF

All diagrams now use a professional dark theme and ship with a PDF. Established a dark palette
(bg #0f1419, light text, muted accents) and a cairosvg SVG→PDF export step. Note: Mermaid can't
render to PDF without a browser, so diagrams are authored as dark hand-SVGs and converted with cairosvg.

**Converted/added (dark SVG + PDF in docs/diagrams/):**
- `00-architecture-darkset` — system architecture + ingestion queue + search flow + data model (one PDF).
- `06-ocr-build-featureset-dark`, `07-ocr-detailed-dark`.
- `viewer.html` switched to Mermaid dark theme + dark canvases.

Going forward every new diagram is dark + PDF by default.

---

## 2026-06-01 — OCR engine set up: RapidOCR (pip, no admin) + full run launched on PC

**Two things happened:**

1. **Full text-first indexing launched on Chris's Windows PC.** Found Python (`py`), auto-installed
   PyMuPDF, and `run_indexing.bat` is crawling `E:\ALL MILITARY TMS` → `index\viewer.db` natively
   (no sandbox limits). Resumable. Note: sandbox-built rows used Linux paths, so the native run
   re-indexes under `E:\` paths; a one-line cleanup can drop the old `/sessions/%`-path rows later.

2. **OCR engine = RapidOCR (replaces Tesseract).** Tesseract's Windows installer needs admin (UAC)
   which automation can't drive. Switched OCR to **RapidOCR** (`pip rapidocr-onnxruntime`) — no admin,
   bundles its own models, installs like PyMuPDF. Pages are rasterized with PyMuPDF and read by RapidOCR;
   Tesseract kept as a fallback. Verified on a scanned parts page (recovered part numbers 5P8500/9X2205/8H5306).

**Delivered:** `viewer_ingest.py` RapidOCR backend; new `run_ocr.bat` (installs deps, runs the resumable
OCR loop). Run `run_ocr.bat` after the text crawl finishes.

**Backwards compatibility (R1):** no schema/data change; Poppler + Tesseract paths preserved as fallbacks.

---

## 2026-06-01 — Full-corpus extraction begun (resumable batches) + durability fix

**Doing:** extending the canonical `index\viewer.db` over the entire corpus in resumable,
idempotent, time-boxed crawl batches (text-first; OCR queued).

**Durability fix (important, R1):** the sandbox mount lacks normal SQLite locking. The first
attempt used `journal_mode=MEMORY`, which corrupted the index when a batch was interrupted.
Switched `VIEWER_RELAXED` mode to `locking_mode=EXCLUSIVE` + `journal_mode=TRUNCATE` — a durable
on-disk rollback journal, so an interrupted write rolls back cleanly instead of corrupting.
Verified: batches that were killed mid-run left the index intact. (Native Windows is unaffected —
relaxed mode is off by default and SQLite is fully durable there.)
The known-good `viewer_index.db` (sample) was kept untouched as the rollback point and used to re-seed.

**Crawler improvements:** cheap skip (compare size+mtime before hashing) so re-walks are fast;
`--max-seconds` clean time-boxed pause so each batch exits before any timeout.

**Progress this session:** index grew 226 → 413 documents, ~67,800 text pages, 14 vehicle folders,
~147 MB. Resumable — re-running continues from where it stopped.

**Completing the full 85 GB:** best done unattended on the Windows machine via `engine\run_indexing.bat`
(no time limits, native durable SQLite) — it does one continuous crawl then OCR. The sandbox proves
the mechanism but isn't the place to finish 40k files.

---

## 2026-06-01 — Onboarding + Parts Request flow wired in (offline app)

**Addition:** the two end-cap processes, now a working offline app over the index.

- **Front process — onboarding modal:** on open, captures Mechanic, Bumper#, Fault(s), TM,
  UOC, Tech Status → a session.
- **Search loop:** predictive, offline search by part#, NSN, material#, or keyword (e.g. gasket).
- **End process — export:** one-click **104th ECC Parts Request Sheet** PDF; header auto-filled
  from the onboarding answers, item blocks from the parts cart. Session + items saved (reprintable).

**Delivered (in `engine\`):**
- `viewer_app.py` — local offline server: `GET /api/search`, `POST /api/request` (saves + returns PDF), serves UI.
- `ui/index.html` — single-page UI: onboarding modal → predictive search → editable parts cart → export.
- `parts_request_pdf.py` — clean 104th ECC sheet replica generator (reportlab).
- `run_app.bat` — launcher (opens browser to the local app).
- Migration `0002_sessions.sql` — additive `sessions` / `faults` / `request_items` (schema v2).
- Diagram `docs/diagrams/onboarding_and_parts_request_flow` (shown to Chris; rule R2).

**Verified end-to-end on the real sample index:** search returns gasket hits with NSN/TM/page;
export saved 1 session + 1 fault + 2 items and returned a valid filled PDF
(`104th_parts_request_B-14.pdf`). Schema upgraded 1→2 with all 226 documents intact.

**Backwards compatibility:** migration additive + rollbackable; existing engine/index untouched;
FEDLOG fields left as editable blanks pending a data source.

**Requires on Windows:** Python + reportlab (`run_app.bat` auto-installs reportlab); Poppler/Tesseract only for indexing.

---

## 2026-06-01 — OCR indexing pipeline built & launched

**Addition:** the real ingestion + OCR indexing engine (collapses M2–M4 foundations).

**Delivered (in `engine\`):**

- `viewer_ingest.py` — crawl / ocr / run / status / search. Text-first, resumable, idempotent, parallel OCR.
- `migrations/0001_init.sql` — versioned schema: `documents`, `pages`, FTS5 `pages_fts` (+ sync triggers), `jobs` queue, `runs`, `schema_meta`, forward-compat `parts/part_variants/procedures/figures`.
- `run_indexing.bat` — one-click Windows launcher (checks Poppler/Tesseract/Python, crawl then OCR loop).
- `README.md` — prerequisites, usage, scale expectations.
- `docs/diagrams/05-ocr-indexing.mmd` — diagram for this addition (rule R2).

**Sample index shipped:** `index\viewer_index.db` built from a representative subset
(HMMWV M998, Buffalo MRAP, M113, Cummins, generators): **226 documents, 41,426 text pages,
78 OCR pages so far, 3,709 pending**. Searches verified across vehicles (voltage, torque,
hydraulic, "dual voltage alternator") including OCR-recovered scanned pages.

**Environment notes (sandbox only, not the shipped program):**
- Shell calls are isolated PID namespaces → no cross-call background jobs; work runs in
  resumable synchronous batches.
- The mounted project folder blocks file deletion and durable SQLite locking, so the index
  is built on local disk and copied in; `VIEWER_RELAXED=1` enables a locking fallback. On
  native Windows none of this applies — SQLite runs fully durable.

**Backwards compatibility:** corpus read-only; schema versioned + additive; index fully
rebuildable from source (ultimate rollback).

**To finish at full scale:** run `engine\run_indexing.bat` on the Windows machine (needs
Python + Poppler + Tesseract on PATH). Text-first is quick; full OCR runs for hours, resumable.

---

## 2026-06-01 — Milestone M1: architecture & diagrams

**Decisions locked (via clarifying questions):**

- App shell: **Local web app** (Windows background service + browser UI).
- Search core: **SQLite + FTS5**.
- Indexing: **text-first, OCR queued for later**.
- M1 scope: **architecture + diagrams only**, no code yet.

**Delivered:**

- `docs/ARCHITECTURE.md` — master architecture.
- `docs/diagrams/01-system-architecture.mmd`
- `docs/diagrams/02-ingestion-data-flow.mmd`
- `docs/diagrams/03-search-query-flow.mmd`
- `docs/diagrams/04-data-model.mmd`
- `docs/diagrams/viewer.html` — offline diagram viewer.

**Corpus baseline at design time:** ~39,700 files, ~85 GB, 7,315 PDFs, 13,695 JPGs, 6,320 svgz, ~70 categories. Source folder: `E:\ALL MILITARY TMS`.

**Next:** M2 — build schema + migrations + ingestion pipeline, prove on a subset (pending approval).
