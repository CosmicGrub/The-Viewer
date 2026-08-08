# THE VIEWER — Handoff Note (reconciled 2026-08-08)

**Purpose:** hand this project to another chat/device without losing context. Read this + the canonical docs
(`docs/EXTRACTION-COVERAGE.md`, `docs/ROADMAP-1.1.md`, `docs/CHANGELOG.md`, `docs/ITERATION-SNAPSHOTS.md`).

> **Reconciliation note (2026-08-08):** this file had gone stale at v1.13.0 while `CHANGELOG.md` and
> `ITERATION-SNAPSHOTS.md` had already moved on to **v1.13.2** (both shipped 2026-07-18, same session, just not
> back-ported here). No work has landed between 2026-07-18 and today — v1.13.2 is confirmed the true current
> state on disk. The two missing entries are added below; nothing else changed. `docs/PROJECT-SUMMARY.md` is
> separately stale (still headed "v0.98.0 · 2026-07-01") — treat `CHANGELOG.md` + this note as the source of
> truth for version state, not PROJECT-SUMMARY.md's header.

## LATEST — v1.13.2 (2026-07-18) — Retroactive Post-Support: run-mode is now a saved Settings choice
**VERSION → `1.13.2`.** The RPS runtime mode (`modern`/`lite`/`legacy`) is no longer env/CLI-only — it's a durable
user choice. New `engine/settings.py` (stdlib-only, `safeguard.atomic_write` + atomic-rename fallback, fail-open
read / fail-loud write) persists it to `index/viewer_settings.json`. `status.html` gets a **Run mode** card (Auto ·
Performance · Retroactive Post-Support) showing resolved mode + reason, hardware recommendation, page-cache size;
`POST /api/rps_mode` persists + re-applies live, `GET /api/rps` reports saved setting + `recommended_mode`.
`rps.mode_for_setting()` maps the choice to a concrete mode; `sysprobe.py` surfaces `recommended_run_mode`.
Precedence (R1): `VIEWER_MODE` env (back-compat) > `VIEWER_RUN_MODE` env > saved setting > `auto`. Verified: 5
changed files compile, 22 isolation tests + 13 live-wiring tests green, audit 0 FAIL/0 WARN (150 unique route
decorators). Diagram: `docs/diagrams/53-rps-run-mode-setting.{svg,pdf,_preview.png}`. **R10 screenshot still
pending host-side** (`/status` Run-mode card).

## v1.13.1 (2026-07-18) — AI-generated 3-D models: illustrative tier (Meshy import lane)
`localmodel.py` gains an AI illustrative tier: drop an AI-generated `<NSN>.obj|.stl` (e.g. a Meshy image-to-3D
export) into `index/models3d/ai/` and it loads in the Interactive 3-D tab with a red **"AI-GENERATED
APPROXIMATION — not to scale, not for part ID or measurement"** banner. `localmodel.find_any()` returns
`(path, fmt, tier)`. **R13 accuracy boundary enforced structurally:** an authoritative model in `models3d/` always
wins over an `ai/` one — a generated mesh can never shadow a real one; `/partdiff` stays text/DB-only and never
touches these meshes. Back-compatible: `find()` unchanged.

## v1.13.0 (2026-07-18) — HOLISTIC HARDENING: dev-team review implemented — trust everywhere, one verify gate, UI coherence, safety features
**VERSION → `1.13.0`** (shipped; `backups/pre-v1.13` is the rollback point, R1). A four-lane parallel implementation
of the dev-team review (ACCURACY · VERIFY/OPS · UI · FEATURES) on top of the concurrent groundwork (pooled
`viewer_app.doc_path()`, exposure posture), then an independent audit + adversarial hardening + polish pass.
- **FEATURES:** fielded search operators **`tm:` / `nsn:` / `vehicle:` / `side:`** (`search_feature.parse_operators`,
  parameterized filters, quoted values, home-page hint, `test_search_quality` 23 green) · **`oneuse.py` +
  `/api/oneuse`** one-time-use / torque-to-yield / discard-after-removal fastener flags (R13 extractive + cited;
  red card on `/part`; merged into the `/api/bom` kit as cited `warnings`) · **zero-result GAP LOG** (`gap` events →
  **`/api/searchgaps`** + a `/command` card: what the corpus could NOT answer) · **`build_conflicts.py` +
  `BUILD-CONFLICTS.bat`** precomputed conflict sweep into append-only `index/conflicts.db`; `/api/conflicts` serves
  fresh exact-subject sweeps instantly (`precomputed: true`), falls back live otherwise.
- **ACCURACY (R13):** `features/corpus.py` = the ONE shared FTS retrieval (measures/ask/faulttree/cautions/pmcs/
  oneuse all ride it; pooled in-app, leak-proof standalone) · `validate.py` woven into `/measures` (per-row
  `quality`; quarantined garble withheld-but-returned) and `conflicts.detect` (quarantined values dropped
  pre-grouping — garble can't fabricate a safety conflict) · trust badges on measures/ask/conflicts/publogdiff ·
  `patterns.niin_of()` canonical (publog/publogdiff/xref_feature/build_publog delegate) · `hybrid._GLOSS` lock ·
  `sessions_feature` rollback · `signoff.py` DDL-once + RO reads · `registry.qfloat` · `viewer_ingest.migrate()`
  atomic per-migration transactions.
- **VERIFY/OPS:** root **`VERIFY.bat`** = THE authoritative union gate (exit-code truth, `run_timeout`-wrapped;
  `VERIFY-099.bat` forwards) · `test_routes.py` blanket **POST** sweep added to the GET sweep (**281 green**) ·
  `rps_lint.py` unclassified page = FAIL · NEW `engine/tools/check_crlf.py` (repo CRLF gate; 20 engine bats fixed,
  83 verified) · `safeguard.py backupdb` (VACUUM INTO + disk guard + keep-2; **manual — run when wanted**) + fixed
  dead `gc` CLI branch · `run_ocr_auto.bat` post-run gc.
- **UI:** Tools menu "Diagnose & decode" group on `index.html` · `shared.js` footer nav injector (+ `#vw-footer` in
  base.css) · `esc()`/`toast()` dedup across 29 pages (all load `/shared.js`; `verify_ui.py` dedup guard) ·
  base.css linked into schematics/threed/circuitlab/demo/cadtex_test · all `alert()`→`toast()` · `palette.js`
  aria-modal + focus trap · index modals `role=dialog` · dossier→`/part` banner · packet↔jobcard cross-links.
- **AUDIT (this session, isolated /tmp copy — never the real 8.4 GB index):** 188/188 .py compile, 0 NUL/truncation;
  no route collisions (244 GET + 20 POST); search-LRU key verified operator-safe (raw `q` + `side` in the key —
  no stale-cache path); all `corpus.fts_pages` callers signature-checked; bom `warnings` shape matches `/part` +
  job-package consumers. Suites: routes **281** · search_quality 23 · hardening 12 · patterns 20 · features 21 ·
  pillars 23 · rps_lint / verify_ui / check_crlf PASS · 12 module self-tests PASS. **Adversarial:** 63 hostile
  cases on `/api/search` + `/api/oneuse` + `/api/searchgaps` (10KB params, unicode, SQL-ish, `vehicle:"unclosed`,
  `side:'; DROP`, repeated operators) → 0×5xx, 0 tracebacks, **0 fixes needed**. Polish: dead `sqlite3/os` imports
  out of measures/faulttree; v1.13.0 tags + shebangs on the new modules.
- **Docs:** CHANGELOG `[1.13.0]` (2026-07-18 final entry; the 07-03 preliminary draft is retained below it per R6)
  + legacy parity; diagram `docs/diagrams/113-holistic-hardening.{svg,pdf}` (`_make_113_holistic.py`); iteration
  snapshot row appended (R10 **literal screenshot still pending host-side** — server not running in the sandbox).

### RUN THESE ON THE HOST (v1.13.0)
1. **`VERIFY.bat`** (the one gate; VERIFY-099 forwards to it) — must come back GREEN.
2. **R10 screenshot:** capture the running app (e.g. `/part` red one-use card, `/command` gap card, or home with the
   operators hint) at `127.0.0.1:8765` → `docs/screenshots/`. **Partial progress 2026-08-08:** confirmed the app
   genuinely running (`THE VIEWER v1.13.2 running at http://127.0.0.1:8765`, GPU CUDA provider present, RPS
   mode=modern) via `RUN-VIEWER.bat`, and captured one real literal screenshot of `/` (home — search box +
   maintenance-session/parts-request-sheet fields visible), delivered to you via chat this session. **Could not**
   reach further routes (`/status`, `/part`, `/command`, `/decode`) or write the PNG directly into
   `docs/screenshots/` this session: the Claude-in-Chrome extension's controlled tab could not connect to
   `127.0.0.1:8765` (consistent "frame showing error page" on every route, while a separately-open, already-working
   Brave window on the same machine loaded the app fine — the extension's tab is on a different network path this
   session) and the sandboxed tool workspace was down (`Request timed out: startVM`), so there was no working file
   channel from the captured screenshot into this repo. **To finish R10:** either (a) retry next session once
   Claude-in-Chrome/the sandbox are healthy — same routes, same convention (`<version>-<page>.png`), or (b) save the
   chat-delivered screenshot into `docs/screenshots/1.13.2-home.png` by hand and click through
   `/status`/`/part`/`/command`/`/decode` yourself for the app to screenshot live if you want the rest done
   immediately.
3. Optional while OCR is paused: **`BUILD-CONFLICTS.bat`** (precompute the conflict sweep; append-only sidecar).
4. **`safeguard.py backupdb`** is manual + documented — run for an off-index full-DB backup when wanted.
5. Still outstanding from before: **re-baseline the stale pre-OCR safeguard snapshot** (`safeguard.py snapshot`)
   once convenient — the old baseline predates the OCR text layer.

## v1.10 → v1.12.9 (2026-07-02 → 07-03) — compressed (full detail in CHANGELOG.md)
- **1.10.0 Recommendations wave:** `rpstl.py` structured RPSTL import + `crossmethod.py` cross-method agreement
  scoring; the **200-idea roadmap** (`docs/ROADMAP-200.md`, Vol.2).
- **1.11.x Fleet readiness:** `intervals.py` service intervals + `fluidsmatrix.py` per-system fluids/capacities +
  `commonality.py` fleet shared-parts + **`/readiness`** page (1.11.0); shift-handover digest `handover.py`
  (1.11.1); PMCS worksheet DA-2404-style `forms.py` + `/api/form_2404` (1.11.2); **bulk folder ingestion**
  `ingestpipe.py` + `BULK-INGEST.bat` (1.11.3); first host VERIFY-099 fixes — RPS `let`-in-comment, Windows
  atomic-rename retry (`_replace_retry`), no-truncation false positives (1.11.4).
- **1.12.x Decoder + safety batch:** air-gap signed update package `airgap.py` HMAC-SHA256 fail-closed (1.12.0);
  standards designation decoder `standards.py` (1.12.1); DA-2407/5990-E `build_2407` (1.12.2); NSN-structure
  decoder `nsndecode.py` (1.12.3); SMR decoder `smrdecode.py` (1.12.4); CAGE/NCAGE validator `cage.py` (1.12.5);
  harness continuity trace `harnesstrace.py` (1.12.6); VERIFY-099 hang-proofing + `run_timeout.py` (1.12.7); MAC
  parser `macchart.py` + `/api/mac` (1.12.8); **1.12.9 DEEP AUDIT** — the green `test_routes 87/87` was testing
  NONE of the v1.12 work (hardcoded list): curated 87→106 + **blanket GET crash-sweep** (new routes auto-covered
  forever), the decoders got their **`/decode`** page + palette command (they had been unreachable), 24k fuzz over
  the six new modules (0 crashes), `/reference`→`/decode` rename (collision).

## v1.13.0 preliminary groundwork (2026-07-03, concurrent session) — kept for context
Unified data access (`corpus.py`, `doc_path()`), startup auto-optimizer (WAL + bg indexes), error-boundary `_sent`
hard contract, `safeguard.atomic_write` everywhere, bounded worker pool, exposure posture (`VIEWER_AUTH_TOKEN`
off-loopback), `/part` cite fixes (incl. the `cautions`→`results` regression), home-page kiosk/a11y fix, VERIFY.bat
first cut. ⚠ **Process note preserved:** the three review subagents were told read-only but two wrote code; it was
competent and was independently re-verified to green — but treat autonomous subagent edits as UNVERIFIED and audit
them (memory `gotcha-review-agents-wrote-files`).

## v1.9.0 (2026-07-02) — Serviceability & safety graphics · kit/BOM · pinouts · training · field notes
**VERSION → `1.9.0`.** Built under **R13**. Additive/rollbackable (R1); read-only except append-only `notes.db`; no new deps.
- **`serviceability.py` + `/api/serviceability`** — wear/serviceable-limit extraction + a go/no-go "is my measured value
  in spec?" checker (serviceable/marginal/replace). **`torqueseq.py` + `/api/torqueseq`** — pattern + staged torques →
  a numbered bolt-pattern diagram. Both on `/part`.
- **`bom.py` + `/api/bom`** — complete kit (parts+qty + consumables + tools), into the job package. **`pinouts.py` +
  `/api/pinouts`** — connector pinout + wire-color extraction.
- **`training.py` + `/learn` + `/api/quiz`** — cited multiple-choice learn mode. **`fieldnotes.py` + `/api/notes`** —
  append-only cited tips with SME endorsement, on `/part`.

**Docs:** CHANGELOG `[1.9.0]` + legacy; dark diagram `docs/diagrams/190-serviceability-kit-training.{svg,pdf,png}`;
VERIFY-099 self-tests all six. **Deferred:** fleet commonality, service-interval/fluids readiness, wiring fault isolation
(all three since shipped in 1.11.0 / roadmap items).

## v1.8.0 (2026-07-02) — R13 trust layer: validation · integrity · human sign-off · TM currency · verification cockpit
**VERSION → `1.8.0`.** First batch under **R13 (above military grade)**. Additive/rollbackable (R1); read-only except
the append-only signoff sidecar; no new deps. Every new pure module self-tested.
- **`validate.py` + `/api/validate`** — quarantines garbled/impossible extracted values (physical-plausibility + OCR-garble),
  flags suspect ones; **wired into `/part`** (a red banner withholds bad data). **`trust.py`** = one canonical trust level.
- **`verifystate.py` + `/verify`** — the verification cockpit (last VERIFY result, module roster, sidecar state,
  DB integrity). **`tests/test_accuracy.py`** — measured extraction recall/precision vs a ground-truth set.
- **`signoff.py` + `/review` + `/api/signoff`** — SME approve/reject/override → verified & locked, **append-only** audit
  trail. **`tmrev.py` + `/api/tmrev`** — flags when a newer TM revision exists (don't work from a superseded book).
- **`integrity.py` + `/api/integrity`** — SQLite corruption detection + SHA-256 tamper-evidence + online-safe backup.

**Docs:** CHANGELOG `[1.8.0]` + legacy; dark diagram `docs/diagrams/180-r13-trust-verify.{svg,pdf,png}`; governed by
**R13** (`rule-above-military-grade`).

## v1.7.0 (2026-07-02) — Unified part page + job PDF · troubleshooting · conflicts · offline Q&A · read-aloud · command center
**VERSION → `1.7.0`.** App-wide batch; additive/rollbackable (R1), read-only (R6), no new deps. Every new pure module
is self-tested and fuzz-hardened (0 crashes / 3,000+ cases per target).
- **`/part`** — one fast pane per part (identity + supersession + parts + dims + torque + cautions + procedure +
  approximate model + a cross-manual **conflict banner**), via `/api/partsummary`. **`jobpack.py` + `/api/jobpack`** =
  the complete **job-package PDF**. Both linked from `/dossier`.
- **`/troubleshoot`** (`faulttree.py`) — parses MALFUNCTION→check→corrective-action into interactive fault trees.
  **`conflicts.py` + `/api/conflicts`** — flags where manuals disagree on a torque/spec (safety), cited + ranked.
- **`/ask`** (`ask.py`) — offline, extractive, **cited** Q&A (no LLM/network). **`readaloud.js`** — offline read-aloud
  + voice input, auto-injected app-wide by `palette.js`.
- **`/command`** (`/api/command_status`) — OCR % · coverage · PUBLOG state · Masterfile gaps at a glance.
- **`tests/test_newmodules.py`** — property/fuzz across publogdiff/dimscad/conflicts/faulttree/ask/hybrid/jobpack.

**Docs:** CHANGELOG `[1.7.0]` + legacy; dark diagram `docs/diagrams/170-partpage-solve-ask.{svg,pdf,png}`.

## v1.6.0 (2026-07-02) — Look-alike intelligence from PUBLOG + approximate 3-D
**VERSION → `1.6.0`.** Builds on the PUBLOG sidecar; all additive/rollbackable (R1), read-only (R6). `BUILD-PUBLOG.bat`
now loads five more FLIS tables (standardization/ISC, MOE/AAC, phrase/TECH_DOC, related-INC, CAGE status).
- **`publogdiff.py`** + `/api/publogdiff` (two parts) + `/api/publog_intel` (one part): characteristics **diff +
  fit-fingerprint %**, **interchangeability verdict** (GREEN/AMBER/RED) with substitutes + AAC/replaced-chain
  **supersession**, **RNCC/RNVC** exact-vs-similar decode + **inactive-vendor** flag, **PUBLOG↔TM crosslink**
  (TECH_DOC_NBR) and **nickname reconciliation** with clash warnings. Shown on `/publog` (intel cards + "⇄ Compare")
  and the new scanner-powered **`/binaudit`** (scan a shelf → flag look-alikes + obsolete).
- **`dimscad.py`** + `/api/dimscad`: approximate **3-D from dimensions** — parses named dims from PUBLOG
  characteristics, picks a primitive, and emits a dimensioned isometric SVG + a parametric OBJ (`?obj=1`) that drops
  into the 3-D library. "Approximate model" card on `/dossier`.

**Docs:** CHANGELOG `[1.6.0]` + legacy; dark diagram `docs/diagrams/160-lookalike-publog-dimscad.{svg,pdf,png}`.
**Host step:** `BUILD-PUBLOG.bat` (multi-GB; degrades gracefully until run).

## v1.5.0 (2026-07-02) — PUBLOG catalog · scanner · hybrid search · exploded view
**VERSION → `1.5.0`.** Five lanes, all additive/rollbackable (R1); corpus + the PUBLOG CSVs are read-only (R6):
1. **PUBLOG/FLIS federal catalog** — `build_publog.py` + `BUILD-PUBLOG.bat` stream the ~16 GB DLA PUBLOG export
   (`C:\Users\User\Desktop\publog`) into a NIIN-keyed **`index/publog.db`** (nomenclature, manufacturer part numbers +
   CAGE, item characteristics, weight/cube, cancelled/replaced NIIN). `publog.py` + **`/api/publog`** (NSN/NIIN lookup
   and reverse `?pn=`), a **`/publog`** page, and a Federal-catalog card on `/dossier`. Offline, no links (R11).
2. **Hand scanner + camera** — `scanner.js` is a global keyboard-wedge listener (auto-injected app-wide by palette.js):
   scan a bin/part label on ANY page and it routes the NSN/part number to the catalog. `/scan` adds offline camera
   scanning via the native `BarcodeDetector`.
3. **Hybrid + glossary search** — `hybrid.py` + `/api/search_hybrid`: acronym/glossary query expansion, RRF fusion of
   keyword + semantic, and fuzzy NSN "did you mean" (grounded in PUBLOG). The home search now shows acronym + NSN hints
   (ranking unchanged).
4. **Exploded / assembly view** — `/exploded` turns a figure into numbered hotspots + a step-through assembly order
   (disassembly toggle, dimensions overlay); linked from `/dossier` + palette.

**Docs:** CHANGELOG `[1.5.0]` + legacy; dark diagram `docs/diagrams/150-publog-scanner-search.{svg,pdf,png}`.

## v1.4.0 (2026-07-02) — Bay-floor batch
**VERSION → `1.4.0`** (`engine/viewer_app.py`). Four lanes shipped together, all additive/rollbackable (R1), corpus read-only (R6):
1. **Offline QR** — `qrgen.py` + `/api/qr` render a QR encoding a deep-link to the part's dossier on THIS server (URL from the request `Host` header) so a phone / 2nd bay tablet on the same LAN scans straight to it. Backend order: **segno**(SVG) → **qrcode+Pillow**(PNG) → friendly 503. QR appears on the printable `/packet` header (self-hides if no backend). `segno` now installed by `INSTALL.bat` (recommended tier).
2. **Masterfile spec-sheet + coverage** — `specsheet.py` + `/api/specsheet` (1-page leading-particulars PDF from `masterfile.db`); `/mastercov` dashboard (least-covered first, missing-dimension chips, per-subject PDF). Buttons on `/master`.
3. **Confidence** — `masterfile._confidence(f)` → high / medium / review / low, surfaced on `/master` as a colored badge + legend.
4. **Kiosk mode + ops** — `body.kiosk-mode` (base.css: bigger text, ≥44px touch targets) toggled from the command palette, persisted in `localStorage`, applied app-wide. `VIEWER-MENU.bat` launcher. `verify_ui.py` ASCII console guard.

**Docs:** CHANGELOG `[1.4.0]` + CHANGELOG-LEGACY `[1.4.0-legacy]`; dark diagram `docs/diagrams/140-bayfloor-batch.{svg,pdf,png}` (R2/R3/R5). The v1.2–v1.3.8 waves (extractors, IETM/KG, vision scaffolds, Tools-menu fix) sit underneath, unchanged.

## Where the build is (historical — v1.1 wave)
- **VERSION → `1.1.4`** (`engine/viewer_app.py`). v1.0.0 was cut and verify-green; that session added the
  **v1.1 extraction + enrichment + Masterfile wave** on top (1.1.0 → 1.1.4).
- Everything is additive and rollbackable (R1). The corpus at `E:\ALL MILITARY TMS` was **not touched**; all new data
  lives in **append-only sidecars** under `index\` (R6).

## v1.1.3 / v1.1.4 (added after the first extraction wave)
- **1.1.3 — Wayback-everything.** The gap-fill crawler now harvests candidate links from **many sources** per subject
  (Internet Archive items, optional web-search plugin `engine/enrich_search.py`, and a seed list `index/enrich_seeds.txt`)
  and **routes every link through the Wayback Machine** (availability, or Save Page Now via `--save`) before extraction.
  Provenance now stores the archived URL + original URL + snapshot timestamp. **Live-verified**: real searches → all
  links resolved to Wayback snapshots → 34 measurements recovered from one archived HMMWV spec page.
- **1.1.4 — The Masterfile.** `masterfile.py` + `BUILD-MASTERFILE.bat` consolidate corpus (`measures.db`, authoritative)
  + external (`enrich.db`) into ONE congruent `index/masterfile.db` + `docs/MASTERFILE.md`, keyed to the authoritative
  subjects. RAW + FILTERED layers. **No external links surfaced** — corpus rows keep their manual page cite; external
  web provenance stays inside `enrich.db`. Served at `/master`. `/measures` external block updated to drop the link.
- New host builders (run when OCR paused; `ENRICH` needs internet): `BUILD-TABLES.bat`, `ENRICH.bat`, `BUILD-MASTERFILE.bat`.
  Recommended order: `BUILD-MEASURES` → (`ENRICH`) → `BUILD-MASTERFILE`.

## What shipped in the v1.1.0 → v1.1.2 session
1. **`measures.py` — measurement / dimensional-data extractor (1.1.0).** Pulls every measured value (length, dia.,
   clearance/**tolerance**, weight, force, torque, pressure, capacity, electrical, temperature, flow, speed, rotation,
   angle) with value(s), range, tolerance, canonical unit, dimension type, context sentence, and cited page. New
   **`/measures`** page (grouped + filterable by type) works **live over FTS — no build step**. Optional
   `BUILD-MEASURES.bat` → `index\measures.db` for fleet-wide counts. Self-test: 19 measurements, all types — PASS.
2. **`tables.py` — structured-table extraction (1.1.1).** PyMuPDF `find_tables` over every page; flags **spec/dimension
   tables** (cells carrying units, via `measures`). `/api/tables?doc=&page=` live; `BUILD-TABLES.bat` → `index\tables.db`.
3. **`enrich.py` + `build_enrich.py` — external gap-fill (1.1.2).** The **corpus is authoritative**; this cross-references
   the **open internet** (Internet Archive full-text + **Wayback Machine**) **only to fill dimension types the corpus is
   silent on**. External values never override the corpus, are surfaced only where the corpus is blank, and are badged
   `external-unconfirmed` with full **provenance** (source, URL, Wayback ts, fetched ts). `/api/external` + a badged
   section on `/measures`. **App stays 100% offline** — only the opt-in `ENRICH.bat` crawler touches the network; the
   server only reads the append-only `index\enrich.db`. Self-test (mocked network + extractor) — PASS.
4. **Docs:** `docs/EXTRACTION-COVERAGE.md` (full map of every extraction/parse/detection method + the enrichment layer),
   changelog `[1.1.0]/[1.1.1]/[1.1.2]`, legacy `[1.1.x-legacy]`, dark diagrams **132/133/134** (SVG+PDF+PNG, R2/R3/R5).
   `/measures` added to the command palette.

## VERIFY wiring (current)
Root **`VERIFY.bat`** is the single authoritative gate (v1.13.0): exit-code truth per step, `run_timeout.py`
wall-clock guards, concise RESULT summary + `pause >nul` (the QuickEdit console-hang lesson), CRLF-safe.
`VERIFY-099.bat` forwards to it. It unions: audit · test_routes (GET+POST sweeps) · the regression suites
(search_quality/hardening/patterns/features/pillars/newmodules/accuracy) · rps_lint · verify_ui · check_crlf ·
module self-tests · no-truncation completeness (R9). The old subroutine `call :body > log` pattern is retained —
do **not** re-wrap the body in CMD parens (the `( )` paren-block bug silently killed earlier host-verifies).

## Known gotchas still in force
- **Mount truncation:** sandbox reads of grown host files are truncated/stale; verify host-side or via the Read tool.
  Snapshot/verify HOST-SIDE (`safeguard.py` / root `VERIFY.bat`).
- **Never** write the big `viewer.db` through the mount; sidecars are written by host-run builders only.
- **LF-only .bat blink-crashes** — now gated mechanically by `engine/tools/check_crlf.py` (in VERIFY).
- Duplicate route paths silently override — audited (244 GET + 20 POST, no collisions) + covered by the audit rule.
- Standing rules R1–R13 are **THE VIEWER-only**; do not carry them to other projects.

## Suggested next
Complete OCR → re-index; re-baseline the pre-OCR safeguard snapshot; run `BUILD-CONFLICTS.bat` (first sweep) and
`BUILD-MEASURES`/`BUILD-MASTERFILE` refreshes on the grown text layer; real semantic embeddings + hybrid ranking;
R12 catalog march continues (`docs/EXTRACTION-METHODS-CATALOG.md` — next cheapest uncaptured methods).

<!-- END OF FILE -->
