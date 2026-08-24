# Changelog — THE VIEWER (Legacy / Retroactive Post-Support)

Legacy builds for older Windows (**7 / Vista**). This track **branched from the modern line at 0.37.0**
(the complete-compatibility point) and is versioned `<modern-base>-legacy`. Every entry notes **parity**
with the modern build: **✓ same** · **~ adapted** (Poppler / Tesseract / lite) · **– N/A** (GPU-only,
not a feature). Branched timeline: `docs/diagrams/CHANGELOG-DUALTRACK.pdf`. Rules **R1–R7** apply; the
modern track lives in `CHANGELOG.md`.

---

## [1.14.0-legacy] — 2026-08-18 — 50-finding 4-tier audit + UX pass + CI + doc reconciliation ........ ~ adapted
- Critical tier (8 findings): `procedure_feature.py` infinite-loop fix, `airgap.py` fail-closed validation,
  ingest-route `VIEWER_INGEST_ROOTS` fencing, `Content-Length` guards, GET-route auth parity, `embed.py`
  hash-fallback → `zlib.crc32`, `build_publog.py` atomic temp-then-swap rebuild, atomic sidecar-cache writes,
  `verify_all.py` glob auto-discovery — pure stdlib/regex/SQL logic, no GPU/rendering dependency ........... ✓ same
- High tier (12 findings): `kg.py` atomic rebuild, `xref.py` NULL-`fig_no` fix, new `viewer_ingest.py prune`
  subcommand, `migrate()` pre-migration snapshot, word-boundary NSN regex (`patterns.py`/`core_pillars.py`/
  `partlocate.py`), `safe_public_base()` QR allowlist, this repo's first CI workflow, 171 new regression checks
  — pure stdlib, identical on both tracks ..................................................................... ✓ same
- High tier, OCR-pipeline items: OCR preprocessing (deskew/denoise, **+ binarize for the Tesseract fallback**)
  is now actually wired into the OCR path — the binarize step exists specifically FOR the engine this track
  uses, so legacy benefits directly here, not just by parity (same `ocrprep.py` module already noted ✓ same at
  1.3.2-legacy). New `ocr_supervisor.py` heartbeat-staleness watchdog wraps whichever `ocrall` pass is running
  (GPU/RapidOCR or CPU/Tesseract) via the same `ocr_heartbeat.txt` file either engine writes — pure stdlib
  process supervision, no OCR-engine dependency of its own ................................................... ✓ same
- Medium tier (19 of 24 findings): `xref.py` NSN-fabrication guard, `dedup.py` hash() → `zlib.crc32`,
  `masterfile.py` streaming build, `kg.py neighbors()` indexed lookup, 8 batch-script hardening fixes
  (`VERIFY.bat` + 7 others) — pure stdlib/CMD, identical on both tracks ...................................... ✓ same
- Medium tier, render-path item: the large-foldout-page DPI cap was extended to the **Poppler fallback render
  path** — Poppler IS this track's own renderer (no PyMuPDF needed) — so this closes a real uncapped-rasterize
  gap on legacy directly, the same "helps legacy most" shape as the 0.56–0.58-legacy speed passes ........... ✓ same
- Low tier (6 findings): dead-file/module cleanup, `tables.py counts_for_doc()` short-circuit fix (same
  fitz-gated degrade-to-`[]` behavior already noted at 1.1.1-legacy — fixed where PyMuPDF is present, a no-op
  where it's absent), `ocr_diag.py` SQL wildcard fix, `verifystate.py` self-test roster drift fix — engine-layer,
  pure stdlib .................................................................................................. ~ adapted
- Priority-5 UI/UX pass — `index.html`'s ES6-only front door (the exact gap RPS-Legacy exists to close) now
  boots a genuine ES5 capability probe + `#legacyHome` fallback shell (search + side chooser + toolset nav)
  when the engine can't run the rest of the page ................................ ✓ FIXED (was broken on legacy)
- Interactive 3-D's **SVG fallback** (this track's own no-WebGL render path) gained the same touch-orbit +
  pinch-zoom + zoom/reset row as the WebGL path, ported from `cadview.js`; the AI-illustrative-model watermark
  now survives the SVG-fallback's own redraw path too — a review-pass fix explicitly named for "the legacy/
  no-WebGL path" ............................................................................................... ✓ same
- Kiosk/glove touch-target fix (min-width, `[role=button]`, footer nav) touches `cadview.js`/`deepzoom.js` —
  both already-legacy-parity files; Deep Zoom's OCR-only-page chip-list fallback, bin/shelf-audit NIIN-
  fabrication guard, QR job-packet self-explaining banner + blob-URL fix, and Look-Alike Parts' inline figure
  thumbnail are all plain DOM/server logic, identical on both tracks .......................................... ✓ same
- Safety-callout confidence flag (dossier/packet/solve/stepflow + Job Card PDF) reuses `textquality.py`'s
  existing garbled-text heuristic (already ✓ same at 1.2.2-legacy) — **not** the RapidOCR-only
  `pages.ocr_confidence` signal from 1.13.5-legacy — so it renders identically over Tesseract-sourced text too . ✓ same
- Circuit Lab wire selection/deletion lives entirely in `circuitlab.html`'s live-simulation canvas, which this
  track has never mounted (0.42.0-legacy/0.44.0-legacy: live MNA sim needs a modern JS engine) .................. – N/A
- `gl3d.js`'s pinch-should-pause-autorotate fix is WebGL-only; a no-WebGL legacy box uses the SVG-fallback's
  own pinch path instead, unaffected by this specific bug ..................................................... ~ adapted
- CI-fix pass and the Tier-1 staleness pass (incl. the 19+3-file `fitz`→`pymupdf` alias migration — an
  import-statement swap only; every existing `fitz.*` call site keeps working unchanged wherever PyMuPDF is
  present on either track) — pure stdlib/CMD fixes, no runtime behavior change ............................... ✓ same
- `verify_all.py` is now 26/26 ALL GREEN — the same gate `VERIFY.bat`'s union already runs; the first fully
  clean run in the project's history, on the one shared engine both tracks execute ........................... ✓ same

---

## [1.13.5-legacy] — 2026-08-09 — OCR confidence capture + temperature extraction gap ................. ~ adapted
- Temperature bare-F/C fix: `measures.extract()`'s new regex alternative + the designator/C-rate collision
  guards are pure stdlib `re` over already-OCR'd text — no rendering/OCR-engine dependency, so it applies
  identically on both tracks (same 100% recall result on `test_accuracy.py` as the modern entry reports) ... ✓ same
- OCR confidence capture is a RapidOCR-only signal: `ocr_one()`'s new per-line-average confidence score only
  exists on the modern engine's code path; the Tesseract-fallback legacy path returns `confidence=None` exactly
  as the modern entry itself documents, so `coverage.overview()`'s new `avg_confidence`/`low_confidence_pages`
  fields simply report zero scored pages on an all-Tesseract legacy corpus, not an error .. – N/A (GPU-only,
  not a feature)
- Migration `0009_ocr_confidence.sql` (additive, nullable) is pure stdlib SQLite DDL — applies to both tracks'
  schema identically even though only the RapidOCR path ever writes a non-NULL value ......................... ✓ same

---

## [1.13.4-legacy] — 2026-08-08 — Live-driving pass + parallel audit: 36 bugs fixed .................... ✓ same
- 12 resource leaks across 10 pure-stdlib `sqlite3` modules (con=None + finally) — no GPU/WebGL/UI involved ..... ✓ same
- Search side-filter starvation, did-you-mean ranking, fault-tree/procedure duplicate-doc dedup, 2 uncached
  aggregate endpoints (`/command`, `/verify` — 60s/300s TTL caches) ............................................. ✓ same
- `verifystate.py` triple fix (log path, pass-regex, false-positive) + a path-depth bug dating to the v0.96.0
  restructure — engine-layer, identical on both tracks .......................................................... ✓ same
- `rpstl.py`/`smrdecode.py`/`standards.py`/`measures.py`/`fluidsmatrix.py` regex/classification tightenings
  (SMR mislabeling, item-fabrication via prefix-match, oil-grade/newline/RPSTL-suffix measurement collisions) —
  pure `re`, no rendering path ................................................................................... ✓ same
- `ingestpipe.py` folder-scan cap fix, `pinouts.py` corrupted-byte cleanup — same on both tracks ................ ✓ same
- 6 hardcoded example NSNs corrected (index.html/jobcard.html/demo.html) — same static markup both tracks share . ✓ same

---

## [1.13.3-legacy] — 2026-08-08 — VERIFY.bat confirmed GREEN on host: two real bugs fixed .............. ✓ same
- `safeguard.db_integrity()` connection leak on the error path (Windows file-lock on the next write) — pure
  stdlib `sqlite3`/`try-finally`, no GPU/WebGL involved ........................................................ ✓ same
- `search_feature.user_keywords_save()` duplicate-group accumulation, same dedup pattern as `user_tags_add()` .... ✓ same
- Both fixes + the `VERIFY.bat` gate itself are engine-layer, not UI-layer — identical on Win7/Vista .......... ✓ same

---

## [1.13.2-legacy] — 2026-07-18 — RPS run-mode is a saved Settings choice (this IS the legacy story) ... ✓ same
- `settings.py` durable choice + `status.html` Run mode card + `/api/rps_mode` — pure stdlib + ES5/XHR .... ✓ same
- **This feature exists FOR the legacy line:** picking **Retroactive Post-Support** forces the compat path
  (ES5/polyfilled UI, local loupe, lower DPI, small-footprint SQLite) and it now persists across restarts .. ✓ same
- Auto-pick already lands Win7/Vista on `legacy` and low-RAM/HDD on `lite`; the override just makes it
  explicit and sticky. `mode_for()` unchanged; precedence `VIEWER_MODE` > `VIEWER_RUN_MODE` > saved > auto .. ✓ same

---

## [1.13.1-legacy] — 2026-07-18 — AI-generated 3-D models: illustrative tier (Meshy import lane) ....... ~ adapted
- `models3d/ai/` file-drop + stdlib OBJ/ASCII-STL parse + red "not to scale / not for part ID" banner ...... ✓ same
- Interactive turntable render is WebGL (`gl3d.js`); on an old browser it falls back to the still image, so
  the illustrative mesh may not spin — the authoritative-wins folder rule and caveats are identical ......... ~ adapted

---

## [1.13.0-legacy] — 2026-07-18 — Holistic hardening: trust everywhere · one gate · UI · safety ...... ~ adapted
- search operators tm:/nsn:/vehicle:/side: — server-side parse + parameterized SQL, pure stdlib ............. ✓ same
- oneuse.py `/api/oneuse` + bom kit warnings; gap log `/api/searchgaps`; build_conflicts.py sidecar ......... ✓ same
- validate/trust weave (measures quarantine, conflicts pre-grouping drop, badges); niin_of canonical ........ ✓ same
- signoff DDL-once, sessions rollback, hybrid _GLOSS lock, registry.qfloat, atomic migrations ............... ✓ same
- VERIFY.bat union gate, test_routes POST sweep (281), rps_lint unclassified=FAIL, check_crlf.py ............ ✓ same
- shared.js footer injector + esc()/toast() dedup — ES5-safe (var/function only); alert()→toast() ........... ✓ same
- Tools "Diagnose & decode" group + palette focus trap / aria-modal — modern-by-design home/palette;
  legacy home bundle keeps its flat button row to the same destinations ..................................... ~ adapted

---

## [1.13.0-legacy] — 2026-07-03 — Holistic review: unified access · hardening · trust · a11y ......... ~ adapted
- `features/corpus.py` unified FTS retrieval + `doc_path()` + atomic sidecar writes — pure stdlib ........... ✓ same
- error-boundary `_sent` contract, bounded worker pool, chunked-TE reject, exposure token ................... ✓ same
- startup auto-optimizer (WAL + bg index build) — WAL is a no-op win on legacy too ......................... ~ adapted
- `/measures` quarantine-withhold, `/part` dim/caution page cites, home-page kiosk/focus inline ............. ✓ same
- VERIFY.bat exit-code gate + safeguard backupdb — cmd/py, identical on legacy ............................. ✓ same

---

## [1.12.9-legacy] — 2026-07-03 — Deep audit: coverage gap, /decode page, decoder fuzz ............... ~ adapted
- test_routes curated cases 87->106 + blanket registry.GET crash-sweep — pure stdlib, same on legacy ........ ✓ same
- decoder fuzz (24k cases) over standards/nsn/smr/cage/harnesstrace/macchart — stdlib ....................... ✓ same
- `/decode` page — fetch + template literals (modern tier); legacy tier keeps the core ES5 tools ........... ~ adapted
- `/reference` -> `/decode` rename (collided with pre-existing /api/reference) .............................. ✓ same

---

## [1.12.8-legacy] — 2026-07-03 — Maintenance Allocation Chart (MAC) parser ........................... ✓ parity
- `macchart.py` (function/level/man-hours rows, component carry-down) — pure stdlib regex ................... ✓ same
- GET `/api/mac` — plain handler; parses matched pages/text, optional component filter ..................... ✓ same
- R13: extractive, null-not-guessed for unreadable columns, raw line kept for verification .................. ✓ same

---

## [1.12.7-legacy] — 2026-07-03 — VERIFY-099 hang-proofing + no-truncation fixes ..................... ✓ parity
- `run_timeout.py` wall-clock guard + concise RESULT summary in VERIFY-099 — stdlib cmd/py, same on legacy ... ✓ same
- airgap.py / harnesstrace.py docstring `[...]` reworded (no-truncation false positives) .................... ✓ same
- verification logic unchanged; launcher reporting + per-step timeouts only (R1) ............................ ✓ same

---

## [1.12.6-legacy] — 2026-07-03 — Harness continuity trace ............................................ ✓ parity
- `harnesstrace.py` (nets by shared signal + alias, trace endpoints) — pure stdlib on pinouts.py output ..... ✓ same
- GET `/api/harnesstrace` — plain handler; nets for a page/text, or a connector/pin trace .................. ✓ same
- R13: continuity inferred (not measured), confidence-labelled, no force-joining, missing pin = found:false . ✓ same

---

## [1.12.5-legacy] — 2026-07-03 — CAGE / NCAGE code validator ......................................... ✓ parity
- `cage.py` (length / alnum / no-I-O / 1st-5th-numeric rules; US vs NCAGE) — pure stdlib regex .............. ✓ same
- GET `/api/cage` — plain handler; validates the query token or scans labelled codes in text ............... ✓ same
- R13: structure only, never a fabricated assignee — identity stays PUBLOG's CAGE table ..................... ✓ same

---

## [1.12.4-legacy] — 2026-07-03 — SMR code decoder ..................................................... ✓ parity
- `smrdecode.py` (source/use/repair/recoverability decode from published tables) — pure stdlib regex ........ ✓ same
- GET `/api/smr` — plain handler; decodes the query token or scans given text ............................... ✓ same
- R13: deterministic split, null meaning for uncarried codes — never an invented SMR interpretation ......... ✓ same

---

## [1.12.3-legacy] — 2026-07-03 — NSN structure decoder ................................................ ✓ parity
- `nsndecode.py` (FSG/FSC + NCB-country decode from published tables) — pure stdlib regex ................... ✓ same
- GET `/api/nsndecode` — plain handler; decodes the query token or scans given text ......................... ✓ same
- R13: deterministic split, null name for uncarried groups/NCB codes — never a fabricated country ........... ✓ same

---

## [1.12.2-legacy] — 2026-07-03 — DA Form 2407 / 5990-E maintenance request ............................ ~ adapted
- `forms.build_2407()` maintenance-request PDF — reportlab; identical where reportlab is present ............. ✓ same
- GET/POST `/api/form_2407` — plain handlers, 503-gated when reportlab absent (lite legacy tier) ............ ~ adapted
- Worksheet-aid discipline (transcribe onto the authoritative form) preserved verbatim ...................... ✓ same

---

## [1.12.1-legacy] — 2026-07-03 — Standard-hardware / spec designation decoder ......................... ✓ parity
- `standards.py` (MS/AN/NAS/MIL-PRF/SAE/ASTM decode → family+kind, curated item set) — pure stdlib regex .... ✓ same
- GET `/api/standards` — plain handler; classifies the query token + scans matching pages .................... ✓ same
- R13 honesty preserved on legacy: family classified, never a fabricated item for uncatalogued numbers ....... ✓ same

---

## [1.9.0-legacy] — 2026-07-02 — Serviceability · torque-seq · kit/BOM · pinouts · training · field notes .. ✓ parity
- serviceability / torqueseq / bom / pinouts / training / fieldnotes — pure stdlib (regex + sqlite + math SVG) ... ✓ same
- `/learn` quiz + the /part cards — plain DOM + fetch; work on legacy browsers via rps.js ...................... ✓ same
- Field-note store is append-only sqlite (same audit discipline) ............................................... ✓ same

---

## [1.8.0-legacy] — 2026-07-02 — R13 trust layer: validate · integrity · signoff · tmrev · verify cockpit ... ✓ parity
- `validate.py`, `trust.py`, `tmrev.py`, `verifystate.py`, `signoff.py` — pure stdlib; identical on legacy ....... ✓ same
- `integrity.py` — SQLite integrity_check + hashlib + the online backup API are all stdlib ...................... ✓ same
- `/verify` + `/review` pages — plain DOM + fetch; work on legacy browsers via rps.js .......................... ✓ same
- Append-only audit trail is inherently the same on either track (sqlite, no updates) .......................... ✓ same

---

## [1.7.0-legacy] — 2026-07-02 — Part page · job PDF · troubleshooting · conflicts · Q&A · read-aloud ... ~ adapted
- `jobpack.py` (reportlab), `conflicts.py`, `faulttree.py`, `ask.py` — pure stdlib/reportlab; identical on legacy .. ✓ same
- `/part`, `/troubleshoot`, `/ask`, `/command` — plain DOM + fetch; work on legacy browsers via rps.js ........... ✓ same
- Offline Q&A retrieval uses FTS always; the semantic half needs embeddings (optional either track) ............. ~ adapted
- `readaloud.js` — native SpeechSynthesis / SpeechRecognition; older browsers lack them → the button/mic just
  don't appear (graceful). Reading procedures aloud is a modern-browser nicety, not required ..................... ~ adapted
- `test_newmodules.py` fuzz — stdlib random; runs on legacy Python unchanged ................................... ✓ same

---

## [1.6.0-legacy] — 2026-07-02 — Look-alike PUBLOG intelligence + approximate 3-D from dimensions ... ✓ parity
- `publogdiff.py` (diff/fingerprint, interchangeability verdict, substitution, supersession, RNCC/RNVC decode,
  vendor status, nickname reconcile, TECH_DOC crosslink) is pure stdlib sqlite — identical on legacy ......... ✓ same
- Extended `build_publog.py` (standardization/MOE/phrase/related/CAGE-status) — pure csv+sqlite ............... ✓ same
- `dimscad.py` approximate 3-D — pure-python math → dimensioned SVG + parametric OBJ; the OBJ drops into the
  same legacy 3-D library (localmodel.py). No GPU, no deps .................................................... ✓ same
- `/binaudit` scanner-powered audit — plain DOM + the ES5 scanner hook; works on legacy browsers ............. ✓ same

---

## [1.5.0-legacy] — 2026-07-02 — PUBLOG catalog · scanner · hybrid search · exploded view .......... ~ adapted
- **PUBLOG/FLIS** (`build_publog.py`/`publog.py`) — pure stdlib csv+sqlite; the loader + query run identically on
  legacy Python. The db is large but the app only READS it ...................................................... ✓ same
- **Hand scanner** (`scanner.js`) — keyboard-wedge listener is plain ES5; works on legacy browsers via rps.js ... ✓ same
- **Camera `/scan`** — uses the native `BarcodeDetector`; older browsers lack it → graceful fallback to the hand
  scanner / manual entry (that is the legacy path) .............................................................. ~ adapted
- **Hybrid search** (`hybrid.py`) — glossary expansion + RRF fusion + NSN did-you-mean are stdlib; the semantic
  half needs embeddings (optional on either track), so legacy runs keyword+glossary+NSN ......................... ~ adapted
- **Exploded/assembly view** — composes existing endpoints; the SVG overlay is basic DOM, fine on legacy ........ ✓ same

---

## [1.4.0-legacy] — 2026-07-02 — Bay-floor batch: kiosk · QR · spec-sheet · confidence · ops ...... ~ adapted
- **Kiosk mode** — pure CSS class + `localStorage` toggle in palette.js; identical on legacy ................ ✓ same
- **Confidence** on `/master`, **spec-sheet** + `/mastercov` — reportlab + stdlib; identical .............. ✓ same
- **Offline QR** (`qrgen.py`, `/api/qr`) — prefers pure-python **segno** (works on legacy Python too); the
  qrcode+Pillow fallback also works. Same graceful-degrade if neither is installed ....................... ~ adapted
- **`VIEWER-MENU.bat`** — CRLF menu launcher; runs on Win7/Vista cmd.exe unchanged ......................... ✓ same
- **ASCII console guard** in verify_ui.py particularly helps legacy (cp1252 consoles are the norm there) .... ✓ same

---

## [1.3.8-legacy] — 2026-07-02 — Tools dropdown stuck-open fix ................................... ✓ parity
- Pure CSS/markup fix (`[hidden]{display:none!important}` in base.css + index.html) + a verify_ui guard -- all ✓ same

---

## [1.3.6-legacy] — 2026-07-02 — Fixes from the first clean host-verify ............................. ✓ parity
- `measures.py` leading-decimal `_NUM` fix, `kg.py`/`callouts.py` ASCII-console fixes, docstring rewords -- all pure ✓ same
- `callouts.py` OCR-skip guard helps legacy (Tesseract) too when the binary path differs ................... ✓ same

---

## [1.3.5-legacy] — 2026-07-02 — Duplicate route fixes + audit guard ............................... ✓ parity
- `/figcrop` + `/api/coverage` handler merges are pure routing logic -- identical on legacy .................. ✓ same
- `audit_features.py` duplicate-(method,path) scan is stdlib regex over the source ......................... ✓ same

---

## [1.3.4-legacy] — 2026-07-02 — Read routes degrade gracefully on un-built sidecars ................ ✓ parity
- The `sqlite3.OperationalError` "no such table" -> graceful-200 boundary fix is pure stdlib -- identical on legacy .. ✓ same
- Keeps real errors (column drift / locked DB / logic bugs) as 500 on both tracks .......................... ✓ same

---

## [1.3.3-legacy] — 2026-07-02 — Figure vision: callouts · symbols · VLM interface ................. ~ adapted
- `callouts.py` uses Tesseract (already the legacy OCR engine) — full parity ................................ ✓ same
- `symbols.py` uses OpenCV template match (both tiers) ..................................................... ✓ same
- `vlm.py` is a stdlib interface; the optional model backend is GPU/host on either track ................... ~ adapted

---

## [1.3.2-legacy] — 2026-07-02 — OCR prep · layout · dedup · cross-validation ...................... ~ adapted
- `dedup.py` + `crossval.py` are pure stdlib — identical on the legacy toolchain ............................. ✓ same
- `ocrprep.py` uses OpenCV (present both tiers); orientation via pytesseract OSD (Tesseract already on legacy) . ✓ same
- `layout.py` uses PyMuPDF blocks (modern); on legacy, Poppler `pdftotext -bbox` supplies block boxes ........ ~ adapted

---

## [1.3.1-legacy] — 2026-07-02 — Dimension-line scanner ............................................ ~ adapted
- `dimscan.py` uses OpenCV (present on both tiers via the same wheels); degrades to [] if absent ............. ✓ same
- Number-OCR step is host-side on both tracks (Tesseract on legacy, GPU OCR on modern) ...................... ~ adapted
- `/api/dimscan` is a stdlib route handler; read-only ...................................................... ✓ same

---

## [1.3.0-legacy] — 2026-07-02 — IETM/S1000D XML + knowledge graph ................................. ✓ parity
- `ietm.py` (stdlib `xml.etree`) + `kg.py`/`build_kg.py` (stdlib `sqlite3`) — identical on the legacy toolchain ✓ same
- `/api/ietm` + `/api/kg` are stdlib route handlers; kg.db is an append-only sidecar ......................... ✓ same
- No modern-only dependency in this wave — full parity ...................................................... ✓ same

---

## [1.2.3-legacy] — 2026-07-02 — Acronyms · page cleanup · borderless/cross-page tables ............. ~ adapted
- `acronyms.py` + `pagetrim.py` are pure stdlib — identical on the legacy toolchain ......................... ✓ same
- `tables_plus.py` uses pdfplumber (pure-Python, works on legacy); degrades to [] if absent ................. ✓ same
- `/api/acronyms` + `/api/tables_plus` are stdlib route handlers ........................................... ✓ same

---

## [1.2.2-legacy] — 2026-07-02 — Cheap-wins bundle ................................................. ~ adapted
- `cautions.py` + `textquality.py` are pure stdlib — identical on the legacy toolchain ....................... ✓ same
- `/api/cautions` + dossier "Safety callouts" card are ES5-safe ............................................. ✓ same
- `pdfmeta.form_fields`/`embedded_files` use PyMuPDF (modern); on legacy, Poppler `pdftk`/`pdfdetach` can supply these ~ adapted

---

## [1.2.1-legacy] — 2026-07-02 — Internal provenance-audit view ...................................... ✓ parity
- `enrich.provenance_rows` is pure stdlib; `/audit` is an ES5 page — identical on the legacy toolchain ........ ✓ same
- Only operator-facing view with links; mechanic views stay link-free (R11) .................................. ✓ same

---

## [1.2.0-legacy] — 2026-07-02 — Five new extractors + Masterfile intelligence ..................... ~ adapted
- `units.py` / `leadingspecs.py` / `specparse.py` are **pure stdlib** — identical on the legacy toolchain ....... ✓ same
- `pdfmeta.py` uses PyMuPDF (modern); on legacy, Poppler `pdfinfo`/`pdftotext -bbox` can supply TOC/metadata .... ~ adapted
- `barcodes.py` degrades to OpenCV-QR or empty if `pyzbar` absent; ES5 dossier cards ......................... ✓ same
- Masterfile dual-units + variance + coverage are stdlib; corpus authoritative, append-only (R1/R6/R11) ....... ✓ same

---

## [1.1.6-legacy] — 2026-07-02 — Masterfile in the Work Order / dossier ............................. ✓ parity
- `jobcard._master_dims` + `/api/master` reads are pure stdlib; Work Order PDF section uses the existing reportlab pen ✓ same
- `/jobcard` + `/dossier` panels are ES5-safe lazy fetches; no links surfaced (R11) .......................... ✓ same
- Depends only on masterfile.db (built on both tracks); degrades to an empty-state prompt if absent ........... ✓ same

---

## [1.1.5-legacy] — 2026-07-02 — Extraction-pipeline regression guard ............................... ✓ parity
- `tests/test_extraction.py` is pure stdlib (temp sqlite + fake fetch) — runs identically on the legacy toolchain ✓ same
- Guards measures/enrich/masterfile logic that is itself stdlib on both tracks; tables portion self-skips w/o fitz ~ adapted
- Integrity check (no code lost to truncation) applies to the shared source tree ............................. ✓ same

---

## [1.1.4-legacy] — 2026-07-02 — The Masterfile (consolidation) ..................................... ✓ parity
- `masterfile.py` is **pure stdlib** (`sqlite3`/`collections`) — consolidates measures.db + enrich.db identically ✓ same
- `/master` page is ES5-safe; no external links surfaced (corpus page cites kept) ............................. ✓ same
- Rebuildable append-only `masterfile.db` + `docs/MASTERFILE.md`; corpus untouched (R1/R6) .................... ✓ same
- Depends only on the corpus/external sidecars, which exist on both tracks ................................... ✓ same

---

## [1.1.3-legacy] — 2026-07-02 — Wayback-route every link; multi-source harvest ................... ✓ parity
- All new `enrich` primitives (wayback save/get, `fetch_via_wayback`, `strip_html`, seeds, web_links) are **pure stdlib**
  (`urllib`/`re`/`json`/`sqlite3`) — run identically on the legacy toolchain ................................... ✓ same
- Save Page Now + Wayback fetch need outbound HTTPS; on Win7/Vista ensure current root certs / TLS 1.2 .......... ~ adapted
- Offline read (`/api/external`, badged `/measures` with archived links) is stdlib + ES5 UI .................... ✓ same
- Corpus authoritative; append-only `enrich.db` (auto-migrates `orig_url`); app offline (R1/R6) ................ ✓ same

---

## [1.1.2-legacy] — 2026-07-02 — External gap-fill enrichment ...................................... ~ adapted
- `enrich.py` gap-fill (IA/Wayback) is **pure stdlib** (`urllib`/`json`/`sqlite3`) — runs on the legacy toolchain ✓ same
- The offline read path (`/api/external`, badged `/measures` block) is stdlib + ES5 UI ....................... ✓ same
- The crawler needs outbound HTTPS; on Win7/Vista ensure current root certs / TLS 1.2 ....................... ~ adapted
- Corpus stays authoritative; append-only `enrich.db`; app offline (R1/R6) ................................... ✓ same

## [1.1.1-legacy] — 2026-07-02 — Structured-table extraction ....................................... ~ adapted
- `tables.py` uses PyMuPDF `find_tables`, which is a **modern-only** dependency ............................. ~ adapted
- Legacy fallback: table detection degrades to `[]` where fitz is absent; `/measures` (text-based) still works ✓ same
- Append-only `tables.db` sidecar, read-only on corpus (R1/R6) .............................................. ✓ same

## [1.1.0-legacy] — 2026-07-02 — Measurement & dimensional-data extraction ........................... ✓ parity
- `measures.py` is **pure-Python regex** over the text layer — no GPU/native deps; runs identically on legacy .. ✓ same
- `/measures` UI is ES5-safe (var/function, no fetch-chaining ES6) .......................................... ✓ same
- Works over whatever text layer exists (Tesseract on legacy) ............................................... ~ adapted
- Optional `measures.db` sidecar, append-only, read-only on the index (R1/R6) ............................... ✓ same

---

## [1.0.0-legacy] — 2026-07-02 — v1.0.0 (legacy track) ................................................. ✓ parity
Legacy/RPS tier reaches 1.0 alongside modern: same features via the compatibility toolchain (Poppler/Tesseract/
ES5), GPU-only items degrade gracefully. See CHANGELOG-LEGACY history for per-item parity.

## [0.37.0-legacy] — 2026-06-02 — Legacy track created (compatibility foundation)
Forked from **modern 0.37.0** at the complete-compatibility point. Target: Windows 7 / Vista with
comparable responsiveness for everyday tasks (search, browse, open a page).

### Present now (the compat foundation already in the engine)
- Core search · vehicle hub · 104th sheet — pure Python stdlib + SQLite ....... ✓ same
- Page render via **Poppler** (`pdftoppm`/`pdftocairo`) when PyMuPDF is absent .. ~ adapted
- OCR via **Tesseract** (CPU) ................................................. ~ adapted
- `sysprobe.py` detects `render_backend` / `ocr_backend` + gives legacy guidance ✓ same
- Safeguard / snapshots / 104th sheet generation ............................. ✓ same
- GPU acceleration ........................................................... – N/A (speed, not a feature)

### Pending (Retroactive Post-Support enhancements — targeted for 0.38.0-legacy)
- ES5 / polyfilled UI bundle (runs in IE11 / old browsers) + Firefox ESR note
- Pre-baked page-image cache (hot pages, on the fast PC) + warm-on-view caching
- SQLite low-RAM / HDD tuning · lite-effects mode (local-only loupe, lower DPI) · gzip + keep-alive
- Mode = auto-pick from the probe + manual override (Settings)

### Parity with modern
Matches **modern 0.37.0** features through the compatibility toolchain (engine substitution); GPU
acceleration is the only omission, and that's speed — not a feature. The responsiveness enhancements
above land in **0.38.0-legacy**.

## [0.95.0-legacy] — 2026-06-05 — Parallel CAD batch (✓ same) + textured 3-D (~ WebGL only)
Backported from modern `0.95.0`:
- **Parallel CAD render batch** (`make_cad.py`, multiprocessing auto-sized to the CPU) — pure stdlib, helps legacy
  multi-core boxes just as much. ............................................................. ✓ same
- **CAD colour + texture on the 3-D model** is a `gl3d.js` (WebGL) shader feature → modern/lite; no-WebGL legacy
  boxes keep the static CAD image / sprite turntable (which already carry the colour+texture). ..... ~ adapted
RPS tier mapping unchanged.

## [0.94.0-legacy] — 2026-06-04 — Local 3-D models (✓ same — needs WebGL to display)
Backported from modern `0.94.0`. `localmodel.py` is pure stdlib (incl. binary-STL via `struct`), so the parsing +
routes are **identical on legacy**. Display uses `gl3d.js` (WebGL):
- Drop `index/models3d/<NSN>.obj|.stl` → parsed to {V,F}, served at /api/localmodel_mesh ............ ✓ same
- Shown in the Interactive 3-D tab (WebGL) ........................................................ ~ adapted (no-WebGL boxes keep the static CAD image / sprite turntable)
No corpus/index writes (R1/R6). See `docs/LOCAL-MODELS.md`.

## [0.93.3-legacy] — 2026-06-04 — Legacy v1 CAD images get material TEXTURE too (~ adapted: needs numpy)
Backported from modern `0.93.3`. Texture now applies at v1 as well as v2/v3 — **if numpy is present** on the legacy
box. The texture step is wrapped in try/except, so a numpy-less Win7/Vista install **gracefully skips texture** and
still shows the (now coloured) flat v1 render — no error. ........................................ ~ adapted
Refresh with **RUN-CAD-TIERS.bat**. RPS mapping unchanged.

## [0.93.2-legacy] — 2026-06-04 — Legacy v1 CAD images are now COLOURED too (✓ same renderer)
Backported from modern `0.93.2`. Colour is in `cad_render.py`, so **legacy's v1 images now carry FLIS colour /
material tint** instead of being grey — same as lite/modern, just without specular (v1) or texture (v1/v2).
Refresh with **RUN-CAD-TIERS.bat**. RPS tier mapping unchanged. Before/after: `docs/cad_color_before_after.png`.

## [0.93.1-legacy] — 2026-06-04 — Max-quality CAD reaches legacy (v1) too (✓ same renderer)
Backported from modern `0.93.1`. Pure-Pillow renderer, tier-aware, so **legacy v1 gets the full upgrade**:
SS 3→4, key+fill lighting, denser curved meshes ........................................... ✓ same (v1 stays flat/no-colour)
- Render cost stays low (~0.15 s/image), so even on-demand legacy renders are fine; the set is cached anyway.
- Refresh with **RUN-CAD-TIERS.bat** (v1/v2/v3). RPS tier mapping unchanged.

## [0.93.0-legacy] — 2026-06-04 — Higher-quality CAD reaches legacy too (✓ same renderer)
Backported from modern `0.93.0`. The quality pass is in `cad_render.py`, which is pure Pillow and tier-aware, so
**legacy (v1) gets the same upgrades**:
- SS 2→3, finer tessellation, silhouette ink-line, contact shadow, softer facet edges ............. ✓ same (v1)
- v1 keeps its character (flat diffuse, no colour/texture) — it's just cleaner and rounder now.
- Re-render the legacy set with the same **RUN-CAD-TIERS.bat** (renders v1/v2/v3).
- Rotate CAD's new flat machined-steel look is WebGL-only; on no-WebGL legacy the sprite turntable still serves the
  (now higher-quality) v1 frames. ............................................................... ~ adapted

### Parity with modern
Quality parity for the static image (v1 improved in lockstep). The WebGL "technical steel" styling is a modern/
lite tab; legacy continues to rotate via the sprite sheet built from the same improved renderer.

## [0.92.1-legacy] — 2026-06-04 — Rotate CAD: the sprite turntable IS the legacy path (✓ by design)
Modern `0.92.1` upgrades the Rotate CAD tab to smooth WebGL where the GPU supports it. On legacy that's exactly
the fallback we already shipped:
- WebGL present → smooth `GL3D` orbit (same as the 3-D tab) ......... – N/A on no-WebGL machines
- No WebGL (Win7/Vista) → the **`/cadspin` sprite turntable** (`cadview.js`): drag-rotate / zoom / pan ... ✓ same
So nothing regresses on legacy — the GPU-free turntable built in 0.92.0 is now formally the no-WebGL branch.

## [0.92.0-legacy] — 2026-06-04 — Interactive CAD turntable (✓ same — GPU-free by design)
Backported from modern `0.92.0`. The rotatable CAD is a **canvas + one sprite-sheet PNG** — no WebGL — so it
works on legacy unchanged, just with fewer frames:
- `render_spin` / `/cadspin` / `cadview.js` (drag-rotate, scroll/pinch-zoom, pan, auto-rotate) ....... ✓ same
- Frame count scales with the tier: **legacy = 12** frames (v1), lite = 16 (v2), modern = 24 (v3) ..... ~ adapted
- CAD detail per frame follows the RPS tier (v1 flat / v2 specular / v3 textured+colour), same as the static image.

### Parity with modern
Full parity. Because the widget never used WebGL, legacy gets the *same* rotate/zoom/scale interaction the modern
build does — the only difference is frame density (smoothness), which is the intended RPS trade.

## [0.91.0-legacy] — 2026-06-04 — "Living Schematic" flow overlay (~ adapted: STEP, no animation loop)
Backported from modern `0.91.0`. The netlist inference (`schemgraph.py`) is pure stdlib and the route is
the same, so the **graph is identical** on legacy. The overlay (`schemflow.js`) is ES5 and detects the tier:
- Netlist inference + `/api/schemgraph` + cache .................................... ✓ same
- Click-a-wire net isolation · click-a-component breakdown ......................... ✓ same
- Animated flow (rAF / SMIL dashes) ............................................... ~ adapted → on legacy there is **no animation loop**: a **▸ STEP** button advances the flow one hop at a time from the source side (RPS-safe, no `requestAnimationFrame`), plus a static highlight.
- Confidence score + flow direction (BFS from power/ground) ........................ ✓ same

### Parity with modern
Full feature parity — only the *continuous* animation is omitted (a deliberate RPS choice to avoid a
render loop on old hardware). The mechanic still sees direction and can step the signal source → load.

## [0.69.0-legacy] — 2026-06-03 — Inline tagging (ES5, full parity)
Backported from modern `0.69.0`. The tagger was written ES5 and the tag store/search are server-side, so it
works on legacy too.
- `tagger.js` pencil + popover — XHR / var, no ES6 (RPS lint covers it) ............................ ✓ same
- `/api/tags` + keywords_user.json tag store, folded into search expansion (server-side) .......... ✓ same
- Pencil on NSN search results + 3D cards ......................................................... ✓ same

### Parity with modern
The pencil/popover is plain DOM + XHR, the tags live server-side and feed the shared search expansion, so a
legacy browser tags parts and finds them by tag identically. Now part of the RPS-required lint set.

## [0.90.0-legacy] — 2026-06-04 — CAD-first library (full parity, legacy gets v1 CAD images)
Backported from modern `0.90.0`. The card + modal lead with the CAD image; on a legacy build the `&tier=` resolves
to v1 (flat, numpy-free) so the library is CAD-first even on Win 7/Vista, with the interactive 3-D as the SVG
fallback and the real figure a tab away. Pure ES5.
- card + modal lead with the CAD image ............................. ✓ same
- detail level follows the build tier (legacy → v1) ............... ✓ same

## [0.89.1-legacy] — 2026-06-04 — Failure-proof renders + all-tier batch (full parity)
Backported from modern `0.89.1`. The placeholder fallback + texture guard are plain Python; RUN-CAD-TIERS renders
the legacy v1 set too. Legacy build still needs no numpy for v1.
- ensure() never leaves a gap (fallback card) ...................... ✓ same
- RUN-CAD-TIERS.bat renders v1/v2/v3 ............................... ✓ same

## [0.89.0-legacy] — 2026-06-04 — Legacy build gets the lightweight v1 CAD images (by design)
Backported from modern `0.89.0`. This is the legacy track's reward: the CAD detail level is tied to the RPS tier,
so a **legacy build serves v1 CAD images** — flat shaded, no colour parse, and crucially **no numpy dependency**, so
the auto-CAD engine works on Win 7/Vista and low-RAM machines with no extra install. /cadimg picks the style from
RPS_MODE automatically; the cache is per-tier so the legacy build only renders the light ones.
- CAD detail = RPS tier (legacy → v1, lite → v2, modern → v3) ........ ✓ same mechanism
- legacy v1 render needs no numpy / no GPU ......................... ✓ legacy win
- per-tier cache (<nsn>_v1/_v2/_v3.png) ............................ ✓ same

## [0.88.0-legacy] — 2026-06-04 — CAD material textures + colour parsing (parity, numpy-gated)
Backported from modern `0.88.0`. Procedural textures use numpy (CPU); if a legacy host lacks numpy the renderer
just skips the texture and still produces the shaded + coloured CAD image. Colour parsing is pure Python.
- per-material surface textures (brushed/grain/speckle/orange-peel)  ~ adapted (skips if no numpy)
- FLIS colour parsing (olive drab / CARC green / etc.) .............. ✓ same

## [0.87.0-legacy] — 2026-06-04 — STL/OBJ export + CAD fidelity pass (full parity)
Backported from modern `0.87.0`. STL/OBJ are plain text written in Python; the shading/orientation are CPU math.
All legacy-safe. Download buttons are plain links.
- /cadstl + /cadobj export (STL/OBJ) ............................... ✓ same
- head-up orientation + specular/metallic shading ................. ✓ same
- download CAD image/STL/OBJ from the modal + drawer .............. ✓ same

## [0.86.0-legacy] — 2026-06-04 — CAD images for the representative 3-D library (full parity)
Backported from modern `0.86.0`. The renderer is pure Python + Pillow (CPU, no GPU), so legacy hosts render the
same CAD images. Served as plain PNGs — old browsers display them with no WebGL needed (a real win for legacy,
which can't run the live 3-D well).
- cad_render.py CAD images (shaded iso + dims + title block) ........ ✓ same
- /cadimg route + MAKE-CAD.bat batch into cadcache ................. ✓ same
- library thumbnails show the CAD image (static PNG, no WebGL) ...... ✓ same (arguably better on legacy)

## [0.85.0-legacy] — 2026-06-04 — Streamlined image search drawer + reusable loupe (adapted)
Backported from modern `0.85.0`. The drawer + loupe are ES5; the loupe uses CSS background magnification (no
server crops) so it runs on old browsers. 3-D in the drawer uses the SVG fallback when WebGL is absent.
- callout -> results -> figure / 3-D / pages drawer .................. ✓ same
- magnifier loupe on schematics + figures (CSS magnification) ....... ~ adapted (no GPU crisp-crop)
- page highlight of the searched number + matching figure ........... ✓ same

## [0.84.2-legacy] — 2026-06-04 — Detailed geometry in both views + wiring audit (full parity)
Backported from modern `0.84.2`. The detailed mesh feeds the SVG fallback (the legacy render path) too, so legacy
machines without WebGL get the same detailed shape on the card and in the modal. Pure ES5.
- thumbnail uses the detailed PartGeo mesh (artist approx == representative)  ✓ same
- 22 families all wired to a builder; FSC values all covered ........ ✓ same

## [0.84.1-legacy] — 2026-06-04 — NSN/FSC shape fallback for nameless parts (full parity)
Backported from modern `0.84.1`. A plain ES5 lookup table + two functions; recovers a shape from the NSN's
Federal Supply Class when the name can't classify. Helps legacy identically.
- familyFromNSN()/classify() NSN→shape fallback ..................... ✓ same
- box-rate 9.3% → 1.5% on the corpus ................................ ✓ same

## [0.84.0-legacy] — 2026-06-04 — Parametric shape pass (full parity)
Backported from modern `0.84.0`. `partgeo.js` is plain ES5 procedural geometry — the 9 new families build the
same {V,F} for the WebGL path where present and for the SVG fallback where not, so legacy gets the richer shapes
and the lower box-rate identically.
- 9 new families (plate/cover/pad/link/lever/rivet/switch/cylinder/canister)  ✓ same
- CLAMP→shaft bug fixed (bounded LAMP/BULB/CAP) ........................ ✓ same
- box-rate 24.7% → 9.3% on the corpus ................................. ✓ same

## [0.83.3-legacy] — 2026-06-04 — E2E harness + coverage cache (full parity)
Backported from modern `0.83.3`. The coverage TTL cache is plain in-process Python (no GPU, no new deps) so it
helps the legacy build identically — arguably more, since legacy machines are slower. The E2E harness is stdlib
urllib and runs anywhere Python does.
- /api/coverage memoized (all-vehicles full scan) .................. ✓ same
- RUN-E2E.bat / diag_e2e.py smoke test ............................ ✓ same

## [0.83.2-legacy] — 2026-06-04 — Skip-demo + skip-to-browsing buttons (full parity)
Backported from modern `0.83.2`. Plain buttons + one localStorage flag; reuses the existing browse-only path.
- “Skip the demo →” on the tour gate + “Skip demo” in the bar ...... ✓ same
- “Skip to browsing →” next to “Watch the guided tour” ............. ✓ same
- browse-only remembered (viewer_browse_only); side choice overrides ✓ same

## [0.83.1-legacy] — 2026-06-04 — Demo wired into onboarding; Finish → real chooser (full parity)
Backported from modern `0.83.1`. All ES5: an `iframe`, `postMessage`, and a localStorage flag — all supported on
the legacy targets. Returning users with a saved side are unaffected.
- First-run shows the tour, then the real side chooser ............. ✓ same
- Finish/Skip hand off to the genuine #sidegate (no guides) ........ ✓ same
- “Watch the guided tour” replay button + ?onboard=1 force ......... ✓ same

## [0.83.0-legacy] — 2026-06-04 — Interactive demo / onboarding tour (full parity)
Backported from modern `0.83.0`. The demo is pure ES5 + inline CSS/SVG with no dependencies, so it runs on the
legacy (Win 7 / Vista, IE11 / Firefox ESR) browsers exactly the same. The spotlight uses four positioned scrim
rectangles (not a CSS clip-path), specifically so it works on old engines.
- Self-contained demo.html (ES5, no deps) ........................... ✓ same
- Coach-marks: scrim + spotlight + SVG arrows + tooltips ............ ✓ same
- Click-through + autoplay, both sides of the house ................ ✓ same
- DEMO.bat one double-click launch ................................. ✓ same
- /demo in-app route .............................................. ✓ same

## [0.82.0-legacy] — 2026-06-03 — Figures-first 3-D library (full parity)
Backported from modern `0.82.0`. The figures-first ordering is a server-side query change plus an ES5
checkbox + hint on the existing page — nothing GPU- or modern-only about it.
- 3-D library leads with parts that have a real cited figure ......... ✓ same
- “include parts without a manual figure” toggle (ES5 checkbox) ...... ✓ same
- Card preview uses the server `image_url` first, XHR fallback ....... ✓ same
- Figure crop served via Poppler path when PyMuPDF absent ............ ~ adapted

## [0.81.1-legacy] — 2026-06-03 — Shape + colour + material on every 3-D image (full parity)
Backported from modern `0.81.1`. All client-side ES5: the expanded `appearance()` parser + classifier apply to
cards, the SVG fallback and the modal. SVG fallback takes the colour; WebGL adds the metalness/finish.
- Full colour/material/finish vocabulary in appearance() .............. ✓ same
- Expanded shape classifier (more families) ......................... ✓ same

## [0.81.0-legacy] — 2026-06-03 — Live parametric CAD panel (full parity)
Backported from modern `0.81.0`. `partgeo.js` is plain ES5 procedural geometry; the panel is ES5 DOM. Live
rebuild works in WebGL where present, else the SVG fallback re-renders from the same generated {V,F}.
- Parametric panel (family + dims + teeth/turns, live rebuild, reset) .. ✓ same
- partgeo teeth/turns drivable params ................................. ✓ same
No new dependency; runs on the legacy/low-power build (procedural geometry is cheap).

## [0.80.0-legacy] — 2026-06-03 — Scan colour + material on the 3-D models (parity, with fallback)
Backported from modern `0.80.0`. `material_feature.py` is pure stdlib regex; `/api/part_material` is a plain
read; the material is applied in WebGL where available.
- material_for parser + /api/part_material ......................... ✓ same
- gl3d material uniform + setMaterial .............................. ✓ same
- On a legacy box without WebGL, the SVG fallback still takes the parsed COLOUR (flat), just not the glossy
  metalness — no regression. ........................................ ~ adapted

## [0.79.1-legacy] — 2026-06-03 — xref coverage in Ops + cross-ref in procedure/3-D (full parity)
Backported from modern `0.79.1`. All read-only JSON + ES5 DOM.
- Ops 'Part-number cross-reference' card (/api/xref_coverage) ........ ✓ same
- 3-D modal CROSS-REFERENCE block + procedure parts enrichment ...... ✓ same (ES5/XHR)

## [0.79.0-legacy] — 2026-06-03 — Cross-reference engine X1–X5 (full parity, offline-first)
Backported from modern `0.79.0`. `xref_feature.py` / `build_xref.py` / `xref_online.py` are pure stdlib
(sqlite + json + urllib); the part card is ES5; sidecars are plain JSON.
- Live part_record: FLIS name (preferred, OCR kept + conflict), vehicles, interchange, supersession .. ✓ same
- build_xref: CAGEC→company + PN+CAGEC→NSN recovery (PUB LOG) ........................................ ✓ same
- X4 online enrichment OFF by default; public-only, cached, ITAR-aware ............................... ✓ same (stays off)
Legacy benefit: the decisive work is offline FLIS, so a Win7/Vista box with no internet loses nothing — X4 is
the only online piece and it's opt-in.

## [0.78.0-legacy] — 2026-06-03 — Part-number ↔ figure correlation (full parity)
Backported from modern `0.78.0`. `rpstl_feature.py` + `build_rpstl.py` are pure stdlib (regex + sqlite + json);
the part-number match card is ES5; the breakdown image is a plain `<img>`.
- RPSTL row parser + lookup + variant grouping + override ......... ✓ same
- FLIS nomenclature validation (ref_nsn) .......................... ✓ same
- Part# search card showing the breakdown image .................. ✓ same (ES5)
- Callout (T3) gated; needs Tesseract, else whole-figure fallback .. ✓ adapted (legacy without Tesseract just
  shows the whole figure — no regression)

## [0.77.0-legacy] — 2026-06-03 — Scanned crop tightening + image→3D scaffold (parity, opt-in stays off)
Backported from modern `0.77.0`.
- Scanned-page crop tightening: OCR word-box caption (optional Tesseract) + numpy density fallback + top-62%.
  Where Tesseract/numpy aren't present on the legacy box, it simply falls back to top-62% (no regression). ✓ adapted
- Local image→3D scaffold: present but **off by default**; needs a configured GPU backend, so on a legacy/low
  -power machine it just stays off and the Approximation tab shows the parametric placeholder. ✓ same (gated)
No ES6; the Approximation tab UI is ES5. Figure crops continue to work via the same PyMuPDF page renderer.

## [0.76.0-legacy] — 2026-06-03 — Real part imagery / figure crops (parity, with a caveat)
Backported from modern `0.76.0`. `figures_feature.py` uses PyMuPDF (same renderer as the page viewer) + a
stdlib regex heuristic; the endpoints are plain reads; the 3D tabs/preview swap is ES5. So legacy gets the
real cited figure crops in previews and the "Manual illustration" tab.
- figure_for + figcache crop + /api/part_image + /figcrop ......... ✓ same
- 3D preview boxes show the cited figure; modal tabs .............. ✓ same (ES5)
- extract_figures.py / EXTRACT-FIGURES.bat prewarm ................ ✓ same
Caveat: requires PyMuPDF present in the legacy Python (the page viewer already needs it). WebGL 3D stays
optional — the figure crop is a plain <img>, so it works even where WebGL doesn't.

## [0.75.0-legacy] — 2026-06-03 — Chapter-level routing in combined manuals (full parity)
Backported from modern `0.75.0`. `chapters_feature.py` is pure stdlib (regex over OCR text + json cache); the
viewer banner/jump is ES5. So legacy gets chapter routing too.
- Chapter→side ranges + lazy cache (chapter_sides.json) ............ ✓ same
- /api/chapters, /api/chapter_jump, POST /api/chapter_override ..... ✓ same
- Open-to-side-chapter + cross-section banner (viewer) ............. ✓ same (ES5)
Falls back to whole-book when a scan finds no headings, so older/poorly-OCR'd manuals behave exactly as before.

## [0.74.0-legacy] — 2026-06-03 — Tighter sorting (full parity)
Backported from modern `0.74.0`. `sides_feature.py` is pure stdlib (regex + json + dict cache), the endpoints
are plain reads/writes, and the review-uncertain UI + deep-link + declutter are ES5 (var/XHR, localStorage).
- Side-map cache (O(1) after first build) ......................... ✓ same
- sides_override.json overrides + POST /api/side_override ......... ✓ same
- cover/MAC corroboration for low-confidence docs ................. ✓ same (reads OCR text already present)
- confidence field on tm_side; /api/side_uncertain; review pins ... ✓ same (ES5)
RPS note: the corroboration only fires on docs with no coverage code, so it adds no cost on the common case;
the cache makes legacy (slower disks) feel snappier on the side views.

## [0.73.0-legacy] — 2026-06-03 — Two sides of the house (full parity)
Backported from modern `0.73.0`. The classifier is pure stdlib regex in `patterns.py`, the endpoints are
plain reads, and the chooser modal is ES5-safe DOM (var/XHR-free; uses `localStorage`, supported on legacy
browsers). So legacy gets the full operator/mechanic split.
- `tm_side()` classifier + `/api/by_side` + `side=` search filter ............. ✓ same
- "Choose your side of the house" modal (operator→browser, mechanic→parts sheet) ✓ same (ES5)
- `classify_sides.py` / `CLASSIFY-SIDES.bat` manifest ......................... ✓ same (stdlib)
RPS note: the modal's inline handlers are ES5; verify with `rps_lint.py` that index.html stays polyfill-safe.

## [0.72.3-legacy] — 2026-06-03 — Audit pass: preflight + leaks + mutation (full parity)
Backported from modern `0.72.3`. Same `preflight.py` / `viewer_app.py` / `procedure_feature.py`, so legacy gets
every fix verbatim. The fast index probe is pure stdlib (no GPU/onnx), and the time-budgeted `--deep` uses
`set_progress_handler` (sqlite3, py3.6+) — so it runs identically on Win7/Vista.
- Preflight fast-probe + large-DB skip + budgeted `--deep` ........................ ✓ same
- Connection-leak fixes (procedure_full, threed_refs) ............................. ✓ same
- mutate.py / test_procedure.py / RUN-MUTATION.bat ................................ ✓ same (stdlib)
Note: legacy on Win7/Vista benefits MORE from the preflight fix (slower disks made the full scan even worse).

## [0.72.2-legacy] — 2026-06-03 — Fix: /api/threed_refs 500 (full parity)
Backported from modern `0.72.2`. Legacy runs the **same** `viewer_app.py` (RPS is a runtime toggle), so it had
the identical `_collections_defs` NameError → 500 on `/api/threed_refs`. The one-line import fix applies verbatim.
- Re-import `_collections_defs` into `viewer_app` namespace ................................ ✓ same
No ES5/legacy-specific concern — the fix is a server-side import, nothing browser-facing changed.

## [0.72.0-legacy] — 2026-06-03 — Reconstituted procedure pages (full parity)
Backported from modern `0.72.0`. The parser is server-side and `procedure.html` was rebuilt ES5, so legacy
gets the whole thing.
- `procedure_feature.py` + `/api/procedure_full` (server-side parse + correlate) ................... ✓ same
- Rebuilt `procedure.html` — side-by-side, checklist (localStorage), print sheet, parts panel (ES5/XHR) ✓ same
- Per-step torque / FIG / NSN chips; warnings classified ......................................... ✓ same

### Parity with modern
The reconstitution is server-side parsing; the page is ES5 (XHR / var, in the RPS lint set), the checklist uses
localStorage (supported on legacy browsers), and the print sheet is plain print-CSS. Legacy gets the same
verifiable, exportable step-by-step.

## [0.71.0-legacy] — 2026-06-03 — Schematic highlighter (SVG, works on legacy) + test suite
Backported from modern `0.71.0`. The highlighter overlay is plain SVG + DOM and `schemhl.js` is ES5, so the
clickable vector schematics work on legacy too; the geometry extraction is server-side.
- `schem_overlay.py` (server) + `/api/schempaths` ................................................. ✓ same
- `schemhl.js` overlay (SVG, ES5; RPS lint covers it) ............................................. ✓ same
- Raster fallback to callout chips ............................................................... ✓ same
- `test_routes` congruence suite + DEMO-SCRIPT.md ................................................. ✓ same (host-run)

### Parity with modern
Nothing here needs WebGL or modern JS — the overlay is SVG, the highlighter is ES5, the geometry comes from the
server. Legacy gets clickable vector schematics and the same end-to-end test gate.

## [0.68.0-legacy] — 2026-06-03 — Detailed 3D shapes reach the SVG path too
Backported from modern `0.68.0`. `partgeo.js` outputs a plain `{V,F}` mesh consumed by BOTH renderers, so the
detailed shapes appear on legacy as well.
- partgeo.js detailed meshes (bolt/nut/bearing/gear/spring/…) ...................................... ✓ same geometry
- WebGL glossy render (modern) vs SVG painter's-fill render (legacy) ............................... ~ adapted (shading; same shape)
- Light gallery thumbnails; detailed mesh on open ................................................. ✓ same

### Parity with modern
The geometry is renderer-agnostic, so legacy's SVG fallback draws the same hex-headed bolt / toothed gear /
ball bearing — flat-shaded instead of WebGL-glossy, but no longer a block. No new dependency; offline.

## [0.67.0-legacy] — 2026-06-03 — Cross-reference + keyword layer (full parity)
Backported from modern `0.67.0`. Enrichment is server-side; the keyword manager was built ES5 from the start.
- PUB LOG cross-reference (manufacturer / colloquial / interchangeable) — server-side enrich ........ ✓ same
- keywords.json + keywords_user.json -> search synonym expansion (server-side) ..................... ✓ same
- `/keywords` manager page (XHR / var, no ES6) — RPS lint covers it ................................ ✓ same
- Browse-mode + Parts-session buttons (index.html) ................................................ ~ adapted (index.html is modern-by-design; the buttons are plain anchors/handlers)

### Parity with modern
The enrichment and the keyword expansion are entirely server-side, read identically by legacy and modern
pages. The new keyword manager is ES5 (XHR/var) and is now part of the RPS-required set the lint enforces.
The running app remains offline on every build.

## [0.66.0-legacy] — 2026-06-03 — Finalized scan benefits legacy identically
Backported from modern `0.66.0`. Finalizing is server-side index work, so the completed corpus serves the
legacy build exactly as it does modern.
- Structured parts re-extraction, optimize_index (suggest_terms/ANALYZE/WAL) — server-side ............ ✓ same
- FINALIZE-OCR.bat / top_nomenclature.py — plain stdlib, no UI ....................................... ✓ same
- Complete text layer (search/find/collections/callouts) over the whole corpus ...................... ✓ same

### Parity with modern
None of the finalize steps touch the browser. The faster, complete `suggest_terms` and the full parts index
are read identically by the ES5 legacy pages and the modern ones. WAL is local-disk only (as designed).

## [0.65.0-legacy] — 2026-06-03 — Dev-infra only (parity neutral)
Backported from modern `0.65.0`. This release is shared Python/diagram/test infrastructure — no UI or runtime
behavior change — so it is parity-neutral by construction.
- `patterns.py` + `test_patterns` (stdlib regex module) ............................................ ✓ same
- `_common.py` diagram helpers (build-time only) .................................................. – N/A (authoring tool)
- `test_routes.py` route smoke (host-side; exercises the same routes legacy uses) ................. ✓ same

### Parity with modern
Nothing here ships to the browser. The route smoke test exercises the same endpoints the legacy UI calls, so it
indirectly protects legacy too. The RPS lint remains green after this change.

## [0.64.0-legacy] — 2026-06-03 — Legacy parity now has a guard (and a real fix)
Backported from modern `0.64.0`. This release *adds the enforcement* for this whole track.
- RPS lint (`rps_lint.py`) — flags ES6 syntax in ES5-required pages; run by RUN-ALL-TESTS.bat ......... ✓ same (the legacy gate itself)
- **`status.html` rewritten ES5** — was ES6 and would have failed on IE11/Win7; now `var`/`function`/XHR .. ✓ FIXED (was broken on legacy)
- `/healthz` JSON — plain stdlib endpoint ......................................................... ✓ same

### Parity with modern
The lint is the retroactive contract made executable: an ES5-required page that drifts to ES6 now fails the
build instead of silently breaking the legacy browser. `status.html` was exactly that case — caught and fixed,
so the System Status page works on Win7/Vista again. Going forward every change runs through `RUN-ALL-TESTS.bat`,
whose RPS step is this gate.

## [0.63.0-legacy] — 2026-06-02 — Stability suite (built RPS-safe from the start)
Backported from modern `0.63.0`. Every piece is stdlib-only with no modern-OS or GPU assumption, so it lands
at **full parity** on Win7/Vista.
- Preflight gate (python/disk/DB integrity/schema) — GPU is INFO, never fatal ...................... ✓ same
- Disk-space guard (OCR pause + page-cache stop; fail-open) ........................................ ✓ same
- Off-disk backup mirror (SHA-256 verified) + BACKUP-OFFDISK.bat ................................... ✓ same
- Server watchdog (auto-restart) + OCR heartbeat / stall watchdog .................................. ✓ same

### Parity with modern
Nothing here uses a third-party package, a modern API, or the GPU. The preflight explicitly treats a missing
CUDA provider as INFO (the normal lite/legacy case), thresholds are modest, and the disk guard fails open.
Legacy gets the identical health layer.

## [0.62.0-legacy] — 2026-06-02 — 3D references panel (works on the SVG path)
Backported from modern `0.62.0`. The references are server-side; the panel is plain DOM + fetch, so it works
even where the 3D shape falls back to SVG.
- `threed_refs()` + `/api/threed_refs` — pure server FTS read + EXISTS .............................. ✓ same
- Side-panel links to manual pages (NSN highlighted), dossier, Look-Alike Parts .................... ✓ same
- "In collections" membership chips ............................................................... ✓ same
- The 3D shape itself ............................................................................. ~ adapted (SVG render on legacy; WebGL on modern — pre-existing)

### Parity with modern
The OCR hookup is entirely server-side (FTS phrase + EXISTS) and the panel is plain DOM + `fetch`, so legacy gets
the identical references, jumps and collection chips alongside the existing SVG 3D fallback. Closes the 3-batch
OCR wiring on the legacy track too.

## [0.61.0-legacy] — 2026-06-02 — Smart Collections add-ons (full parity)
Backported from modern `0.61.0`. All four add-ons are plain server logic + ES5 DOM, so legacy gets them in full.
- Scope to vehicle / manual-type (server-side WHERE + GLOB) ......................................... ✓ same
- "New since last visit" +N badge (collection_seen sidecar; server computes the delta) ............. ✓ same
- Save-as-collection from the results bar + ★ pin .................................................. ✓ same
- Group by vehicle/manual + printable take-to-bay sheet (plain HTML print window) .................. ✓ same

### Parity with modern
Nothing here needs a modern browser: scope/seen/pin are server-side over the sidecar, the page is ES5 (XHR,
`var`), and the print sheet is plain HTML. Legacy gets identical behaviour. Auto-fill + the "new" delta are
properties of the shared index, so they apply regardless of client.

## [0.60.0-legacy] — 2026-06-02 — Page callouts (server does the work)
Backported from modern `0.60.0`. The extraction and jumps are server-side, so legacy gets the substance; the
on-image positioned dots are the one modern-leaning nicety.
- `page_callouts()` + `/api/callouts` — pure server regex over `body_text` ........................... ✓ same
- Chip bar of clickable callouts (NSN → dossier, P/N → Look-Alike, FIG → find-in-manual) ............ ✓ same (plain DOM)
- Positioned hotspot DOTS on the image (anchored to word boxes, follow tilt/zoom) .................. ~ adapted (dots need the modern viewer's transforms; legacy shows the chip bar)
- Targets (dossier / partdiff / find-in-manual) all render server-side ............................. ✓ same

### Parity with modern
The valuable part — finding the NSNs/part numbers/figures on a page and jumping to them — is server-side regex
plus plain links, so legacy gets it in full via the chip bar. Only the on-image numbered dots, which ride the
modern viewer's CSS tilt/zoom transforms, are modern-leaning; legacy simply uses the chips. Auto-improves as OCR
fills `body_text`, regardless of client.

## [0.59.0-legacy] — 2026-06-02 — Smart Collections (full parity on legacy)
Backported from modern `0.59.0`. This one lands at **full parity** on Win7/Vista because it was built ES5-safe
from the start.
- `/collections` page — ES5 (XHR, `var`, no arrow/template) + `rps.js` ................................ ✓ same
- Live `pages_fts` evaluation + bounded counts (read-only on the index) .............................. ✓ same
- `collections.db` sidecar (own file/lock) — saving never touches the index ......................... ✓ same
- Click-a-hit → page with the term highlighted (server-side `/page` `hl`) ........................... ✓ same (server renders; no client GPU needed)

### Parity with modern
Nothing here depends on a modern browser or GPU — the page is plain XHR + DOM, the query runs on the server,
and the highlighted page is rendered server-side. Legacy gets the identical feature. The auto-fill-from-OCR
behaviour is a property of the shared index, so it applies regardless of client.

## [0.58.0-legacy] — 2026-06-02 — Gap-closing pass (legacy gains the most where it counts)
Backported from modern `0.58.0`. The two server-side gaps help legacy directly; the two client-side ones
degrade gracefully on old browsers.
- OCR identical-page dedup + adaptive DPI (Tesseract path) — fewer CPU inferences per batch ... ~ adapted (CPU OCR, same logic)
- **Legacy memory sizing** — `doc_cache` = **2** open PDFs on legacy + cold-start warmup ....... ✓ same (tuned FOR legacy)
- Circuit Lab MNA → Web Worker — Run loop off-thread on modern browsers ........................ ~ adapted (no Worker → inline sim, same as before)
- Result hover-prefetch + loupe neighbour-prefetch ............................................ ✓ same (loupe already local-only on legacy; prefetch is plain `<img>`)

### Parity with modern
The **legacy memory + cold-start** work is tuned explicitly for low-RAM Win7/Vista — legacy benefits most.
OCR dedup/adaptive-DPI apply through the CPU (Tesseract) path. The Web Worker offload **degrades to the
existing inline simulator** when `Worker` is unavailable (ES5/IE11), so behaviour is unchanged there.
Hover-prefetch is a plain hidden-`<img>` warm, valid since the earliest browsers; the loupe is already
local-only in lite/legacy mode and simply gains neighbour-crop warming where the network allows it.

## [0.57.0-legacy] — 2026-06-02 — Speed pass round 2 (full parity, helps legacy most)
Backported from modern `0.57.0`. Pure server-internal optimizations — they apply identically on legacy,
where the gains matter most (slow disk, weak CPU, low bandwidth).
- Compact JSON, pre-render page ETag, suggest_terms prefix lookup, WAL concurrency ........... ✓ same
- Smaller payloads + 304s especially help low-bandwidth legacy clients; WAL helps the HDD case . ✓ same (bigger benefit)

### Parity with modern
**Full parity** — no browser dependency. The legacy build gets the same (often larger) speedup. Additive
& rollbackable (R1).

## [0.56.0-legacy] — 2026-06-02 — Speed & efficiency pass (full parity, helps legacy most)
Backported from modern `0.56.0`. Pure server-internal optimizations — no client code at all — so they
apply identically on the legacy build, where they matter most (slow HDD / low RAM).
- Open-PDF LRU, thread-local DB connections, ETag/304, NOCASE indexes, ANALYZE ............... ✓ same
- ETag/304 + the page cache especially help slow links and HDDs ............................. ✓ same (bigger benefit)

### Parity with modern
**Full parity** — these are transport/query/render optimizations with no browser dependency. The legacy
build gets the same (often larger) speedup. Additive & rollbackable (R1).

## [0.55.0-legacy] — 2026-06-02 — UX consolidation (full parity)
Backported from modern `0.55.0`. This wave is deliberately ES5-safe, so it's the cleanest parity yet.
- Visual steps, torque panel, Ctrl+K palette, help guide — all **ES5-safe + rps.js** ......... ✓ same
- `rps.js` parity gap closed on `threed.html` + `status.html` ................................. ✓ same
- Rich-graphics pages (3-D / Circuit Lab / schematic tilt) remain modern-by-design ........... – N/A (graphics)

### Parity with modern
**Full parity** for the whole core workflow, including raw IE11 (via the rps.js polyfills) — these
additions use no ES6 syntax. The only legacy delta remains the rich-graphics features, by design.

## [0.54.0-legacy] — 2026-06-02 — Ops dashboard (full parity)
Backported from modern `0.54.0`. Read-only summary endpoints + a plain page on the `rps.js` shim.
- `/ops` (mode, counts, cache, runs, coverage, file audit), all read-only ..................... ✓ same

## [0.53.0-legacy] — 2026-06-02 — Find in manual / Ctrl+F (full parity)
Backported from modern `0.53.0`. A scoped server query + a viewer find box; no modern-only dependency.
- in-document find with highlight + next/prev, doc-scoped ..................................... ✓ same

## [0.52.0-legacy] — 2026-06-02 — Part dossier (full parity)
Backported from modern `0.52.0`. Read-only aggregation of legacy-capable endpoints via a plain page.
- `/dossier` (reference + figures + look-alike + procedure + schematic + 3-D links) ........... ✓ same

## [0.51.0-legacy] — 2026-06-02 — Job packet (full parity)
Backported from modern `0.51.0`. Pure print layout — works on any browser; the print path is universal.
- `/packet` print sheet (procedure + tools + cautions + parts-to-order) ....................... ✓ same

## [0.50.0-legacy] — 2026-06-02 — Add documents UI (full parity)
Backported from modern `0.50.0`. A folder path + a plain page driving the same `crawl` pipeline that
already runs on legacy.

### Carried over
- `/ingest` preview + index + live progress (snapshot-first, additive) ........................ ✓ same
- Render/extract via the legacy toolchain (Poppler / Tesseract) during crawl ................. ~ adapted

### Parity with modern
**Full parity** — the ingest pipeline already supported the legacy render/OCR backends; the UI is plain
HTML on the `rps.js` shim. Additive & rollbackable (R1).

## [0.49.0-legacy] — 2026-06-02 — Type-ahead predictive search (full parity)
Backported from modern `0.49.0`. A server-side prefix query + a small dropdown using the `rps.js` fetch
shim — runs as-is on old browsers.

### Carried over
- `/api/suggest` dropdown (vehicles + parts + manual words, ranked) ........................... ✓ same
- Reads existing indexes only (vocab + vehicles + history); offline & instant ................. ✓ same

### Parity with modern
**Full parity** — read-only query feature, no modern-only dependency. The dropdown uses the shimmed
`fetch`. Additive & rollbackable (R1).

## [0.48.0-legacy] — 2026-06-02 — Solve-it workflow hub (full parity)
Backported from modern `0.48.0`. It only orchestrates endpoints that already run on legacy, through a
plain HTML page using the `rps.js` fetch shim.

### Carried over
- `/solve` hub: symptom → parts → procedure → look-alike → schematic, all cited ............... ✓ same
- Calls the same legacy-capable endpoints (faultparts/search/procedure/partdiff/schematics) .... ✓ same

### Parity with modern
**Full parity** — presentation/orchestration only, no modern-only dependency. Additive & rollbackable (R1).

## [0.47.0-legacy] — 2026-06-02 — How-to-do-it procedure view (full parity)
Backported from modern `0.47.0`. A server-side FTS query + a plain HTML page — no modern-only features —
so it runs as-is on Win7/Vista.

### Carried over
- `/procedure` view (steps, tools, cautions parsed from the page, cited) ...................... ✓ same
- FTS over the same index; reads page text only (read-only) .................................. ✓ same
- ES5-friendly page (uses the `rps.js` fetch shim already in the legacy bundle) .............. ~ adapted

### Parity with modern
**Full parity** — a data/query feature, not a rendering one. Like the Look-Alike recognizer, it degrades
in nothing on legacy. Additive & rollbackable (R1).

## [0.46.0-legacy] — 2026-06-02 — Faster transport + one-tap Legacy mode (full parity)
Backported from modern `0.46.0`. Both finishers are plain transport/UI and help the legacy build directly.

### Carried over
- **gzip + keep-alive** — smaller transfers + fewer handshakes on slow links / old NICs ........ ✓ same
- **Settings → Performance toggle** with a one-tap **Legacy** choice (and Auto/Modern/Lite) ..... ✓ same
- Server SQLite tuning + page cache still auto-picked from the probe (unchanged) ............... ✓ same

### Parity with modern
**Full parity** — these are presentation/transport features with no modern-only dependency. The gzip
path is feature-detected per request, so an old browser that doesn't send `Accept-Encoding` simply gets
the uncompressed body. Additive & rollbackable (R1).

## [0.45.0-legacy] — 2026-06-02 — RPS delivered: the legacy build is now real
The Retroactive Post-Support layer (modern `0.45.0`) is what makes this legacy track **actually run well**
on Win7/Vista — it lands the enhancements that were marked *pending* back at `0.37.0-legacy`.

### Now delivered (was pending since 0.37.0-legacy)
- **Mode auto-pick** from the probe → this build runs in **legacy** mode ......................... ✓ new
- **ES5 / polyfilled UI** (`rps.js`: fetch/Promise/Object.assign/Array+String/URLSearchParams) ... ✓ new
- **Pre-baked page cache + warm-on-view** (`index/pagecache`, `--prebake N`) — HDD-friendly ...... ✓ new
- **SQLite low-RAM / HDD tuning** (tiny cache, `mmap=0`, FILE temp) .............................. ✓ new
- **Lite-effects mode** (animations off, local loupe, DPI capped 150) ........................... ✓ new
- **Poppler render path** (already present since the foundation) ................................ ✓ same

### Parity with modern
**Full feature parity** with modern `0.45.0` for *content and capability*; the differences are purely
*how* it runs (Poppler instead of PyMuPDF, no GPU OCR speed, effects off). That is the whole point of RPS:
COMPLETE compatibility by adaptation, not by removing features. Additive & rollbackable (R1).

## [0.44.0-legacy] — 2026-06-02 — Circuit Lab deepened: still static-overlay only
Backported from **modern 0.44.0** (adapted). The new active devices (AC/MOSFET/op-amp/relay), save/load,
and netlist export all live in the live-simulator layer, which the legacy build does not mount.

### Carried over / adapted
- Build/trace a circuit on a real sheet; the static schematic viewer still opens it ... ~ adapted
- Part **TM #/NSN tags** that link to Look-Alike Parts (a plain link) ................... ✓ same
- **Live simulation + save/export of the running model** ............................... – N/A on legacy

### Parity with modern
Same as `0.42.0-legacy`: the **static overlay** is carried; the **live engine** (now richer) remains the
deliberate omission on Win7/Vista. Additive & rollbackable (R1).

## [0.43.0-legacy] — 2026-06-02 — Look-Alike Parts recognizer (full parity)
Backported from **modern 0.43.0**. Pure server-side query + a plain HTML page — no modern-browser
features — so it runs as-is on the legacy build.

### Carried over
- `/partdiff` recognizer (NSN/FSC/UOC/CAGEC/SMR discriminators, 4 verdicts, cited figures) ... ✓ same
- Reads the parts index + optional correlations sidecar (read-only) ......................... ✓ same
- The page is ES5-friendly (fetch shim already in the legacy bundle) ......................... ~ adapted

### Parity with modern
**Full parity** with modern 0.43.0 — this is a data/query feature, not a rendering one, so nothing
degrades on Win7/Vista. Additive & rollbackable (R1).

## [0.42.0-legacy] — 2026-06-02 — Circuit Lab: static-overlay only (no live sim)
Backported from **modern 0.42.0** (adapted). The Circuit Lab's **overlay editor + real-time simulator**
is a modern-browser feature; on Win7/Vista it degrades gracefully.

### Carried over / adapted
- Open a real schematic and **build/trace a circuit on top of it** (the overlay editor draws) .. ~ adapted
- The schematic still opens in the **static viewer** (Poppler render path) ................. ✓ same
- **Live MNA simulation** (animated transient, current dots, scope, logic colours) ......... – N/A on legacy
  (needs a modern JS engine + `requestAnimationFrame`; the `circuitsim.js` MNA core is ES-modern). On the
  ES5/polyfilled legacy UI bundle the **▶ Run / DC / Step** controls are hidden and the page falls back to
  static overlay + the existing viewer.

### Parity with modern
Matches **modern 0.42.0** for *viewing and tracing* on a real sheet; the **live circuit solve/animation**
is the deliberate omission (speed/engine, surfaced as static-overlay only). Fully additive & rollbackable
(R1): the legacy build simply doesn't mount the `/circuitlab` live controls.

## [0.96.0-legacy] — 2026-06-10 — THE RESTRUCTURE lands identically on legacy
Backported from **modern 0.96.0** (same code — the restructure is server-side Python, stdlib-only, and
the RPS tiers all run the same shell + `engine/features/` package).

### Carried over / adapted
- Thin shell + features package, route registry, ONE error boundary ......................... ✓ same
- Central param validation (400), POST cap (413), same-origin (403), error log, graceful stop  ✓ same
- `ui/shared.js` is **strictly ES5** (lint-locked) and `ui/base.css` is plain CSS2/3 — both safe
  on the polyfilled legacy UI bundle ........................................................ ✓ same
- Six tiered overlays (`cadview/demo/loupe/partview/schemflow/schemhl`) now **lint-locked ES5**
  so future edits can't silently break this build (G48) .................................... ✓ guarded
- Poppler render path: moved verbatim into `features/render_feature.py`; `fitz is None` fallback
  unchanged ................................................................................. ✓ same

### Parity with modern
**Full parity** — structure-only change; no new modern-only API anywhere in the request path
(`viewer_app.py` + `features/` import nothing beyond stdlib). The RPS gate (`rps_lint`) now runs in
VERIFY-ALL on every change, so the retroactive guarantee is enforced, not just promised. Additive &
rollbackable (R1): restore `backups/pre-v0.96-restructure/viewer_app.py` and remove `features/`.

## [0.97.0-legacy] — 2026-06-10 — Search quality + dedup land identically; layout fix helps small screens most
Backported from **modern 0.97.0** (same code — all server-side stdlib Python + ES5-safe UI changes).

### Carried over / adapted
- Exact-match boost, did-you-mean, phrase/NEAR operators, search LRU (all server-side) ....... ✓ same
- Did-you-mean links render on the home page (index.html is modern-by-design; legacy home gets
  the same API field and ignores it gracefully if the bundle differs) ........................ ~ adapted
- 12 ES5 pages now load `/base.css` + `/shared.js` (both strictly ES5/CSS2-3, lint-locked);
  inline helper copies stripped — fewer bytes per page on slow links ......................... ✓ same
- Header-wrap layout fix: matters MOST on the older, smaller screens this track targets —
  the nav now wraps instead of forcing sideways scroll ....................................... ✓ same

### Parity with modern
**Full parity.** The RPS gate (now incl. the 6 lint-locked tiered overlays) ran green over every
modified page. Additive & rollbackable (R1): `backups/pre-v0.97-batch/`.

## [0.99.35-legacy] — 2026-07-02 — Verify-run fixes (✓ same — batch + stdlib)
The CMD subroutine-redirect fix + test_http registry-import fix are toolchain-agnostic; the verify suite runs the same
on the legacy tier. ............................................................................................. ✓ same

## [0.99.34-legacy] — 2026-07-01 — Release prep (✓ same — stdlib + batch)
`cut_v1.py` is pure stdlib; the orchestrator/cut batch files are plain CMD. Runs the same on the legacy toolchain;
the 1.0.0 banner is written to the legacy changelog too. ......................................................... ✓ same

## [0.99.33-legacy] — 2026-07-01 — Most-used home panel (✓ same — ES5 fetch)
Plain ES5 fetch of `/api/analytics_top` + DOM; hidden until data exists. Renders on legacy browsers. .............. ✓ same

## [0.99.24–0.99.32-legacy] — 2026-07-01 — Nine-feature wave (mostly ✓ same; two ~ adapted)
- 0.99.24 analytics, 0.99.25 xref, 0.99.26 parts-PDF+barcode, 0.99.27 PMCS items, 0.99.30 HTTP-fuzz, 0.99.31 mutation:
  pure stdlib / reportlab (already parity) / SQLite — run identically on the legacy toolchain. ................. ✓ same
- 0.99.28 visual pHash + 0.99.29 semantic embed: need numpy (+ optional OpenCV/sentence-transformers); on a legacy box
  without them these degrade gracefully (feature shows "index not built" / hash-fallback) rather than breaking. ..... ~ adapted
- 0.99.32 installer: PyInstaller build targets modern Windows; legacy tier keeps the Python-script launch. ......... ~ adapted
- All new UI pages are plain ES5 fetch+DOM (base.css) → render on IE11 / old Firefox ESR.

## [0.99.23-legacy] — 2026-07-01 — PMCS finder (✓ same — stdlib FTS)
`pmcs.py` is pure stdlib + SQLite FTS, read-only; `/pmcs` is a plain fetch+DOM page. Runs identically on legacy. ..... ✓ same

## [0.99.22-legacy] — 2026-07-01 — Fastener reference (✓ same — client-side ES5)
`fastener.html` is a self-contained ES5 reference table (no backend) — works the same on IE11 / old browsers. ....... ✓ same

## [0.99.21-legacy] — 2026-07-01 — My Bench (✓ same — localStorage + ES5)
`bench.html` + the ☆ pin pill use localStorage via the rps.js polyfills; plain DOM. Works on legacy browsers. ....... ✓ same

## [0.99.20-legacy] — 2026-07-01 — Torque quick-reference (✓ same — ES5 page + existing API)
`torque.html` is a plain fetch+DOM page (base.css, ES5-safe) hitting the already-present `/api/torque`; the unit
converter is pure client-side math. Runs identically on legacy / old browsers. ................................... ✓ same

## [0.99.19-legacy] — 2026-07-01 — Fuzz the param front-door (✓ same — pure stdlib)
The `registry.qstr/qint/qflag` fuzz is pure stdlib and runs identically on the legacy toolchain; the ParamError→400
guarantee protects legacy/older-OS users the same way. .......................................................... ✓ same

## [0.99.18-legacy] — 2026-07-01 — Hardening wider (✓ same — pure stdlib fuzz)
`test_property_fuzz.py`'s new partlocate/coverage/pct checks are pure stdlib + sqlite on a synthetic index — they run
identically on the legacy Python toolchain (no GPU/PyMuPDF needed). ................................................ ✓ same

## [0.99.17-legacy] — 2026-07-01 — Offline startup fix + version + R10 (✓ same — the offline fix HELPS legacy most)
The unconditional `pip install --upgrade pip` hang on offline machines hits legacy/older-OS boxes hardest, so the
offline-safe guard in run_app/run_ocr_*/run_enrich/run_indexing is a straight win on legacy. .................... ✓ same
- VERSION bump + R10 snapshot generator are pure stdlib, host-side — identical on legacy.
- The iteration dashboard is plain ES5 + inline data (no framework) → opens in IE11 / old browsers too.

## [0.99.16-legacy] — 2026-07-01 — OCR resume tooling (✓ same — stdlib launcher)
`RESUME-OCR.bat` delegates to the existing autonomous runner (stdlib probe + resumable loop); the daily progress task
reads the TSV/heartbeat. All pure stdlib / plain batch — runs the same on the legacy toolchain. ................. ✓ same

## [0.99.15-legacy] — 2026-07-01 — All recommendations + congruency (~ adapted — a11y/ingest ES5; rest stdlib)
- vectorize thin-image fix + its fuzz invariant: pure OpenCV/stdlib — identical where cv2 is present; on legacy the
  vectorizer is a gated extra, so the fix is a no-op-safe guard. ................................................. ✓ same
- per-part look-alike (jobcard) + test_congruency + R9 no-truncation gate: pure stdlib, host-side — same on legacy. ... ✓ same
- ingest drop-zone + Recent paths: `webkitGetAsEntry` degrades gracefully (falls back to the paste-path flow) on old
  browsers; Recent uses localStorage via the rps.js polyfill. ................................................... ~ adapted
- a11y: `:focus-visible` + ARIA are progressive — modern browsers get the outline/roles, IE11 ignores them harmlessly. .. ~ adapted

## [0.99.14-legacy] — 2026-07-01 — Property/fuzz hardening (✓ same — stdlib fuzz; Hypothesis optional)
`test_property_fuzz.py` runs a pure-stdlib fuzz with no third-party requirement (Hypothesis is used only if present),
so the hardening pass runs identically on the legacy Python toolchain; the invariants are the same code paths. ......... ✓ same
- `RUN-HARDENING.bat` degrades gracefully when offline (skips the hypothesis install, keeps the stdlib fuzz).

## [0.99.13-legacy] — 2026-07-01 — Feature audit + palette QoL (~ adapted — audit stdlib; QoL ES5)
`audit_features.py` is pure stdlib and host-authoritative → runs the same on legacy. The palette Recent uses
`localStorage` + a `URLSearchParams` regex fallback, so it works on IE11/old ESR via the rps.js polyfills. .......... ~ adapted
- The "⌘K jump" pill is plain DOM/CSS; no modern APIs.

## [0.99.12-legacy] — 2026-07-01 — Work-order regression tests (✓ same — pure stdlib)
`tests/test_jobcard.py` is pure stdlib + sqlite on a synthetic index; it runs identically on the legacy Python
toolchain (no GPU/PyMuPDF/reportlab needed for the logic checks; the build_pdf smoke reuses the already-parity reportlab). .. ✓ same

## [0.99.11-legacy] — 2026-07-01 — Discoverability: palette revived (~ adapted — ES5 + rps.js polyfills)
`palette.js` is explicitly ES5 and rides the `rps.js` polyfills (URLSearchParams/fetch) so Ctrl+K works on IE11 /
old Firefox ESR; the `?q=` deep-link uses a regex fallback when URLSearchParams is absent. ...................... ~ adapted
- Script includes + Tools-menu group are plain HTML/anchors — identical on legacy.
- The whole feature is navigation only; no GPU/PyMuPDF path involved.

## [0.99.10-legacy] — 2026-07-01 — Job Card deeper (✓ same — regex + stdlib + ES5)
Task-intent, materials/reference extraction, and the look-alike warning are pure regex over the OCR text + stdlib
SQLite; `/api/jobcard_preview` is one `@get` and `/jobcard` is a plain fetch+DOM page (IE11 / Firefox ESR ok). ...... ✓ same
- `_parse_procedure`'s new materials/references keys work identically on Tesseract-sourced text.
- Look-alike warning reuses `part_differences` (already legacy-parity) — no GPU/PyMuPDF dependency in the logic.

## [0.99.9-legacy] — 2026-07-01 — Job Card / Work Order (✓ same — reportlab, already required)
`jobcard.py` uses the same toolchain the parts-request packet + figure-sheet already need (reportlab + PyMuPDF +
Pillow), all present in the legacy build; `/api/jobcard` is one `@get` and the 🧾 button is a plain anchor. ........ ✓ same
- Procedure/torque parsing is pure regex over the OCR text layer — identical on legacy (Tesseract-sourced text works too).
- Figure rendering falls back to Poppler on legacy exactly as the figure-sheet does; text sections render with no figures if fitz is absent.

## [0.99.8-legacy] — 2026-07-01 — Figure → Parts (✓ same — stdlib + ES5)
`figureparts.py` is pure stdlib + read-only SQLite; `/api/figureparts` is one `@get`. The `/deepzoom` **🧩 Parts
on page** drawer is plain fetch + DOM (no canvas/WebGL of its own) so it renders on IE11 / old Firefox ESR. .. ✓ same
- Runs identically on the legacy toolchain; nothing GPU- or PyMuPDF-specific in the module itself.
- Closes the two-way figure↔parts navigation on legacy exactly as on modern.

## [0.99.7-legacy] — 2026-07-01 — Figure-sheet PDF (✓ same — reportlab, already required)
`figuresheet.py` uses reportlab (the parts-request packet already needs it) + PyMuPDF — both in the legacy
toolchain — so it works identically; the ⛭/🖨 button is a plain anchor. Output PDF is universal. ......... ✓ same

## [0.99.6-legacy] — 2026-07-01 — Coverage dashboard + part locator + doctor (✓ same)
All three are pure stdlib + ES5 pages (`/base.css`), read-only, sidecar-only — they run identically on legacy:
- coverage.py / partlocate.py / doctor.py — stdlib + sqlite; coverage's cv2/ocr rows just report "missing" if a dep
  isn't installed. ................................................................................. ✓ same
- /coverage + /locate pages are plain fetch + DOM (no WebGL/canvas). ............................... ✓ same
- doctor's corpus-path check is especially useful on legacy/migrated boxes.

## [0.99.5-legacy] — 2026-07-01 — Vectorization batch (~ adapted: needs OpenCV)
Modern 0.99.5's `build_vectorize.py` is a host tool (stdlib + OpenCV). With cv2 it runs identically on legacy (just
fewer cores); without cv2 it prints a clear "unavailable" and exits — the raster deep-zoom is unaffected. ... ~ adapted

## [0.99.4-legacy] — 2026-07-01 — Line-art vectorization (~ adapted: needs OpenCV)
Backported from modern 0.99.4. `vectorize.py` + `/vectorize` are stdlib + OpenCV; on a legacy box **with cv2** it
works identically (SVG output is universal). **Without cv2** the route returns a clean 503 and the ⛭ Vectorize
button simply yields "vectorizer needs OpenCV" — the raster deep-zoom still works. ................. ~ adapted
No RPS/ES5 surface change (the button is a plain anchor).

## [0.99.3-legacy] — 2026-07-01 — Deep-zoom + callout hotspots (✓ same — offline by design)
Backported from modern 0.99.3. `deepzoom.js` is a plain canvas + `/page?dpi=N` renders + `/api/callouts` — **no
CDN, no WebGL**, ES5-safe — so it works on the legacy tier as-is (a legacy box just caps the DPI ladder lower
via slower renders). The `/deepzoom` page uses `/base.css`. .................................... ✓ same
Line-art vectorization deferred on both tracks.

## [0.99.1-legacy] — 2026-07-01 — Review queue + Circuit Lab bridge + coverage (~ adapted)
Backported from modern 0.99.1. All stdlib/ES5, sidecar-only:
- schemreview queue/record/override + `/api/schemgraph_review(_decision)` + `/api/schemgraph_coverage` ...... ✓ same
- schemflow ⚑ Correct mode is ES5 (prompt-based label add) — works on the legacy overlay too ............. ✓ same
- Circuit Lab reference panel is a plain fetch + DOM node ................................................ ✓ same
- Full continuous flow animation is still modern/lite; legacy keeps the ▸ STEP overlay (unchanged) ...... ~ adapted
No RPS gate change. Run VERIFY-099.bat host-side.

## [0.99.0-legacy] — 2026-07-01 — Schematic netlist batch (✓ same — host tool)
Modern 0.99.0's `build_schemgraph.py` is pure stdlib + PyMuPDF (same as the OCR/xref batches) and writes only
sidecars, so it runs identically on a legacy host — just slower without many cores. The cached netlists it
produces make the legacy `▶ Flow` overlay open instantly (no per-open inference). ................. ✓ same
Coverage TSV + resumable done-file are plain text. No RPS/ES5 surface touched.

## [0.98.2-legacy] — 2026-07-01 — Root run button (✓ same)
`RUN-VIEWER.bat` delegates to the existing `engine\run_app.bat`; nothing legacy-specific. ........... ✓ same

## [0.98.1-legacy] — 2026-07-01 — Post-restructure gap-fill (tests/docs only)
Modern 0.98.1 adds an integration test + refreshed hand-off docs — **no runtime code**, so there is nothing
legacy-specific to adapt:
- `test_features_integration.py` runs pure stdlib + Pillow, same as the other suites ................ ✓ same
- The features it guards (CAD colour/texture, schemgraph, localmodel) already had their legacy parity noted in
  0.90–0.95-legacy; this only confirms the restructure kept them wired. ............................ ✓ same
- Docs/`VERIFY-V098.bat` apply to both tracks. No RPS/ES5 surface touched. ......................... – N/A

## [0.98.0-legacy] — 2026-06-10 — Nav consolidation carries over
Backported from **modern 0.98.0** (adapted where noted).

### Carried over / adapted
- Collections page LIBRARIES cards (plain anchors + existing .card CSS — ES5/CSS2-safe) ...... ✓ same
- Tools dropdown on the home page: index.html is modern-by-design; the legacy home bundle keeps
  its flat (wrapping) button row — same destinations, no dropdown JS required ................ ~ adapted
- All routes unchanged; nothing removed ....................................................... ✓ same

### Parity with modern
**Full parity of capability**; presentation differs only on the modern home page (dropdown vs
wrapped row). RPS gate green over both edited pages. Rollback: `backups/pre-v0.98-nav/` (R1).

<!-- Add new legacy entries above this line. When a modern feature is carried over, add a dated
     [x.y.z-legacy] entry noting "backported from modern x.y.z (adapted …)" and a parity line, and add
     a backport link in docs/diagrams/_make_changelog_dualtrack.py so the timeline shows it. -->
