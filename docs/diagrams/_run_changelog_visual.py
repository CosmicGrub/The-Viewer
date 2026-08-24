#!/usr/bin/env python3
"""Generate docs/diagrams/CHANGELOG-VISUAL.svg + .pdf (rule R5). Fresh-inode runner."""
import cairosvg, html, os

KIND_FILL = {"feat": ("#16301f", "#2f5a3e"), "fix": ("#3a2f1a", "#6b5526"), "rule": ("#1a2740", "#3a4d6e")}

V = [
 ("0.1.0","Architecture & diagrams","rule",
   ["Corpus (read-only)","Design decisions","Versioned schema","Diagrams (R1/R2)"],
   "Locked: local web app + SQLite/FTS5 + text-first. Established rules R1 (backwards-compatible) and R2 (diagram per addition)."),
 ("0.2.0","Indexing engine + OCR pipeline","feat",
   ["Crawl","Extract text","FTS5 index","OCR queue"],
   "viewer_ingest + migration 0001 (documents/pages/pages_fts/jobs/runs). Text-first, resumable, idempotent; durable OCR job queue."),
 ("0.3.0","Onboarding + 104th parts request","feat",
   ["Onboarding modal","Search","Parts cart","104th PDF"],
   "Migration 0002 (sessions/faults/request_items). Offline app + dark UI; clean PDF replica of the 104th ECC sheet, header from the modal."),
 ("0.4.0","Full-corpus extraction + durability","fix",
   ["Batch crawl","Cheap skip","TRUNCATE journal","Resumable"],
   "Time-boxed resumable batches + cheap skip (size+mtime). Fixed corruption by switching to EXCLUSIVE + on-disk TRUNCATE journal."),
 ("0.5.0","PyMuPDF text backend","feat",
   ["PDF","PyMuPDF get_text","pages text"],
   "Text extraction moved to PyMuPDF (pip) with Poppler fallback - faster and removes the Poppler hard dependency."),
 ("0.6.0","RapidOCR engine; full run","feat",
   ["Scanned page","PyMuPDF render","RapidOCR","FTS5"],
   "OCR engine = RapidOCR (pip, no admin). Full crawl COMPLETED on PC: 40,291 docs, ~1.87M searchable text pages, ~133k queued for OCR."),
 ("0.6.1","OCR detail + example","feat",
   ["Scan","OCR","142 lines @99%"],
   "Detailed OCR diagram + a real before/after example page (recovered part numbers from a scanned parts page)."),
 ("0.7.0","Dark diagram standard (R3)","rule",
   ["Dark SVG","cairosvg","PDF"],
   "Rule R3: all diagrams dark-themed + a PDF version. Converted existing diagrams; viewer.html switched to dark."),
 ("0.8.0","Search GUI: document viewer","feat",
   ["Result","/page render","Viewer pane","Add part"],
   "On-demand page rendering (PyMuPDF) + viewer pane: click a result to see the real manual page, navigate, add the part to the request."),
 ("0.8.1","OCR reliability fixes","fix",
   ["cleanup (drop /tmp rows)","Thread OCR","Live progress","done, failed=0"],
   "Root cause: orphan sandbox-path rows failed instantly. Added cleanup + switched to thread-based OCR. Verified real text, zero failures."),
 ("0.9.0","Forked: GPU + Lite","feat",
   ["Shared core","GPU build (--gpu)","Lite portable","make_portable"],
   "One codebase, two profiles: GPU/production (priority) and Lite/portable (self-contained folder + finished index). Flags --gpu/--dpi."),
 ("0.9.1","Changelog standard (R4)","rule",
   ["Change","CHANGELOG.md entry"],
   "Rule R4: a versioned changelog entry accompanies every change. Retroactive CHANGELOG.md created."),
 ("0.9.2","Visual changelog (R5)","rule",
   ["Change","Changelog entry","Graphical panel","PDF"],
   "Rule R5: every changelog entry also gets a detailed graphical explanation + a functioning diagram PDF (this document)."),
 ("0.9.3","Launcher pip self-upgrade","fix",
   ["Launch .bat","upgrade pip","install deps","run"],
   "All setup/launch files now run pip install --upgrade pip before installing packages, so nothing is missing and the app launches cleanly."),
 ("0.9.4","Nomenclature carries to the sheet","fix",
   ["Search match (snippet)","deriveName","Item name (editable)","104th PDF"],
   "Part nomenclature now auto-fills the cart Item Name from the matched manual line (or search term), so it carries onto the parts request sheet."),
 ("0.10.0","NSN search + Vehicle breakdown hub","feat",
   ["Full NSN","Exact match + classify","Vehicle hub (grouped)","Open real page"],
   "Type a full NSN (part or whole-vehicle); vehicle NSN opens a hub grouping the entire manual set (operator/maint/parts/troubleshooting/schematics), each opening the actual page."),
 ("0.11.0","Express modal + Schematics on every page","feat",
   ["Express field (NSN/part)","Bypass -> page/hub","Viewer schematics panel","Always a graphic"],
   "Modal 'What do you need?' jumps straight to the page/hub on exact NSN/part#; the viewer always shows a Schematics & install panel (cited figure -> page -> vehicle schematic set), verbatim & cited."),
 ("0.12.0","OCR speedup: skip-junk + prioritize","feat",
   ["Pending","Prioritize (parts first)","Blank? skip","OCR real pages"],
   "Skip-the-junk: blank pages skipped with no OCR inference (~0.01s). Prioritized queue OCRs parts catalogs first. Migration 0003 + narrowed FTS trigger (faster requeues)."),
 ("0.13.0","Dynamic front-end UX pass","feat",
   ["Home (browse-by-vehicle)","Smart results (filters+counts)","Viewer zoom/thumbs/highlight","Responsive + large text"],
   "Home screen browses every vehicle + recents (/api/vehicles, /api/sessions). Results gain filters/counts by vehicle/type/source. Viewer adds zoom, a thumbnail strip, and highlight-the-hit (/page?hl via PyMuPDF search_for). Responsive/touch + large-text + simple/advanced toggles. Additive."),
 ("0.14.0","Search upgrades: Last-4 + smart key terms","feat",
   ["Query (one box)","Router by shape","Last-4 / NSN / key-terms","build_match -> FTS5"],
   "Type 4 digits for a Last-4 cover/end-item NSN lookup (with a full-text escape hatch). Key-term search gains synonyms (synonyms.json), offline fuzzy typo tolerance (fts5vocab, edit-distance 1), part#/FIG/callout phrase precision, and an All/Any toggle. Additive."),
 ("0.15.0","Modal aligned to the 104th sheet header","feat",
   ["Modal field","SESSION key","104th header block","Live preview + 104th PDF"],
   "Onboarding modal now mirrors the 104th sheet header 1:1 (exact labels & order); header fields always shown (Simple only hides cart FEDLOG); a live paper-style header preview fills in as you type. Field IDs/SESSION keys unchanged -> identical PDF. Additive."),
 ("0.16.0","Self-learning search + calmer UI","feat",
   ["104th sheet generated","request_items (the log)","/api/popular (freq+recency)","Rotating example - quick-picks - ranked"],
   "Surfaces what you already log: GET /api/popular ranks parts that reached a generated sheet by frequency+recency. Drives a single rotating example, a 'commonly requested' quick-pick row, and popularity-ranked results (requested). Seed list for cold start; copy trimmed. No migration."),
 ("0.17.0","Tech Status from fault+part (PMCS-cited)","feat",
   ["Fault + parts","GET /api/techstatus","PMCS criteria (cited) / history","Mandatory confirm -> 104th"],
   "Suggests equipment status from the fault: searches the vehicle's PMCS 'Not Fully Mission Capable If' criteria (cited, TM+page) -> deadline=NMCS; else prior history; else manual. Mandatory confirm gate at export (server rejects blank). Full codes FMC/PMCM/PMCS/NMCM/NMCS. App proposes & cites, human confirms."),
 ("0.18.0","Switchable layouts behind Settings","feat",
   ["Settings (preset / fine-tune)","applySettings()","body CSS classes + 2 JS vars","localStorage (per device) - core untouched"],
   "A Settings panel consolidates the toggles + 4 named presets (Simple/Advanced/Shopfloor/Compact), per-device persist + Reset, legacy keys migrated. Presentation only: a layout is just CSS classes + 2 defaults; the dataset, search, and 104th flow are invariant. Client-only, no server/schema change."),
 ("0.19.0","Structured parts index (Phase 1) + coverage","feat",
   ["RPSTL pages","viewer_ingest parts","parts: NSN->figure (cited)","/api/part - cart ref - coverage"],
   "Extracts a cited NSN->figure->page->vehicle index from RPSTL pages (migration 0004; 28,330 records on the sample). Cart shows the cited catalog figure + auto-fills FIG; vehicle hub shows '% searchable'. Multi-sheet 104th + tech-status suggestion capture. Exact part#/variant alignment deferred (OCR-noisy) - honest grounding."),
 ("0.20.0","Online -> offline reference enrichment","feat",
   ["Official sources (once)","viewer_ingest enrich","ref_hardware + ref_nsn (cited)","/api/reference - cart label"],
   "One-time online enrichment, offline after: public-domain FED-STD-H28 hardware/thread dims + official GSA NSN extract (filtered to in-index NSNs). Separate cited tables (migration 0005), labeled 'External reference'; torque is general ref (TM governs); third-party scrapers excluded. Fills sheet nomenclature + Tier 2.5 dimensions."),
 ("0.21.0","Append-only NSN enrichment (rule R6)","rule",
   ["GSA extract (re-fetch)","ref_nsn_log (append every version)","ref_nsn current pointer","/api/reference + 'N versions'"],
   "Rule R6: always add, never remove info (even outdated). NSN enrichment is now append-only/versioned (migration 0006, ref_nsn_log) - old + new both kept; current = latest. Space/scope: NSNs are cheap text (tens of MB); whole TMs are heavy (GB + OCR) and a separate sourcing path."),
 ("0.21.1","One-time enrichment reads GSA XLSX","fix",
   ["data.gov GSA extract (.xlsx)","enrich --gsa (streams xlsx/csv)","match in-index NSNs","append (R6)"],
   "enrich now reads the official GSA NSN Extract directly as .xlsx (the actual data.gov format) as well as csv. Engine stays offline; one-shot hand-run filler. Source is public-domain (CC0) but the GSA Advantage subset, dated 2017 - fills commercially-listed NSNs only; kept append-only & cited."),
 ("0.22.0","PUB LOG reference ingest (POC)","feat",
   ["PUB LOG export (CSV/XLSX)","enrich --publog (in-index NSNs)","ref_nsn +part#/CAGE/char/AAC/subs","cart auto-fills part# + AAC"],
   "POC: enrich --publog ingests the authoritative DLA PUB LOG export - fills NSN->item name, part#/CAGE (MCRD), characteristics=size for Tier 2.5 (CHAR), AAC + substitutes (MDI&S). Migration 0007; append-only/cited (R6); cart auto-fills authoritative part# and AAC. Verified on in-index NSNs. Real fill = one-time PUB LOG download on a connected machine."),
 ("0.23.0","PUB LOG via FLIS Reading Room (direct CSVs)","feat",
   ["Reading Room monthly CSVs","enrich --publog-dir","merge per NSN (non-clobbering)","cited offline reference"],
   "Correction: no PUB LOG Windows app needed - the FLIS Reading Room publishes monthly CSVs (Identification/Reference/Characteristics/Management/CAGE/History). enrich --publog-dir reads the folder, keeps in-index NSNs, composes NSN from FSC+NIIN, and merges fields per NSN without clobbering. History.zip keeps inactive NSNs (R6). Verified."),
 ("0.24.0","PUB LOG enrichment RUN on the live index","feat",
   ["16 GB FLIS Reading Room","enrich_flis (NIIN-keyed)","468 NSNs enriched","live in viewer.db (R6)"],
   "Ran the real DLA FLIS catalog into the live index: 468 NSNs got item names (406), part numbers (463), AAC (451), decoded characteristics/dimensions (421), unit prices. enrich_flis() productizes the NIIN-keyed ingest (INC->name via H6, char aggregation) for monthly re-runs. Index verified intact (39,683 docs). Append-only (R6)."),
 ("0.25.0","Overnight: full-catalog enrichment + 2D->3D + rollback","feat",
   ["Parts on full index (45k NSNs)","FLIS enrichment 41,701 NSNs","Supersession/vintage/multi-choice + 2D->3D","Rollback (R1) ready"],
   "On the live index: 227,908 parts records (45,068 NSNs); FLIS enrichment of 41,701 NSNs (names, part#/CAGE, dimensions, AAC, price, vintage date, supersession cross-refs, multiple part choices). New: FLIS year tag + supersession + multiple-choice in the cart; offline rotatable 2D->3D viewer sized to FLIS dims (cited). Search ~45ms. One-click rollback (run_rollback.bat). OCR to 100% remains a GPU job."),
 ("0.26.0","3D viewer: family shapes + material/colour","feat",
   ["FLIS dims (expanded)","Family shape (cyl/hex/disc/box)","Material/colour tint (cited)","Depth-shaded solid"],
   "Representative 3D viewer upgraded: renders family shapes from the item name with depth-sorted filled faces; tints to the FLIS-stated colour (cited) or a material-based representative tint (steel->grey, aluminium->silver, copper->bronze), labelled; expanded dimension parsing; button gated to ~20,869 parts that actually carry a bounding dimension."),
 ("0.27.0","Schematic legibility viewer","feat",
   ["Real page (PyMuPDF)","Clean + contrast (Pillow)","3D tilt (CSS)","Hover loupe 2.6x"],
   "Same drawing, made readable: a Clean toggle + contrast slider re-render the page through a grounded enhancement pipeline (grayscale, auto-contrast, de-speckle, unsharp, optional high-contrast/binarize); a flat-sheet 3D tilt (CSS perspective rotateY) and a cursor-following 2.6x loupe. Off by default, presentation-only - dataset, search and 104th sheet untouched (R1/R6). Nothing invented; cited to its page."),
 ("0.28.0","Hi-fi loupe + correlations + tests","feat",
   ["/page clip @ high DPI (21x px)","correlations.db sidecar","/api/correlations","17 pillar tests + 100% mutants"],
   "Three additive wins: (1) the loupe re-rasterises just the page region under the cursor at high DPI (~21x more pixels - sharp at any zoom, nothing invented); (2) a deletable correlations sidecar connects links the flat tables implied - 19,511 NSNs span >1 vehicle (top fits 33 platforms), 884 NIIN format-drift review groups, 311 supersession pairs held both ways - viewer.db untouched (R1/R6); (3) a pillar test suite (17/17 pass) + mutation testing (15/15 killed, 100%) over a verbatim logic mirror. Congruency audit: 0 malformed NSNs, no orphans."),
 ("0.29.0","Data protection: safeguard + recovery","feat",
   ["atomic write (temp+fsync+replace)","snapshot vault (SHA-256)","verify -> classify damage","recover byte-for-byte"],
   "Root cause of the 'truncation' found: a sandbox read-cache artifact at the host->guest boundary - the Windows files were never damaged. Built real protection anyway: engine/safeguard.py does atomic writes, SHA-256 snapshots into backups/vault, a verify that classifies TRUNCATED/CORRUPTED/EMPTY/MISSING vs the last good snapshot, and byte-for-byte recover (the archaeologist). Tested to a stranglehold: 19 pillar + 11 truncation/recovery tests pass; 2 mutation rounds inject 38 faults (engine logic + the safeguard itself) and kill 36 (95%) - the 2 survivors are equivalent mutants. Additive (R6); main index untouched (R1)."),
 ("0.30.0","Schematic orientation + HD","feat",
   ["tilt Y + tilt X (-60..60)","mirror + readable labels","/api/pagewords (OCR-gated)","on-demand HD up to 400 dpi"],
   "Schematic viewing controls: dual-axis tilt (rotateY + rotateX, honest flat-sheet); a horizontal mirror to orient from the opposite side, with each word box (new /api/pagewords from PyMuPDF) re-drawn un-mirrored so labels stay readable on text pages (a mirror is an orientation aid, NOT a true rear view); and an on-demand HD toggle that renders the full page from the lossless source at up to 400 dpi (no pre-baked duplicate files). All presentation-only and reversible - page bytes, index, search and 104th sheet untouched (R1/R6)."),
 ("0.31.0","Status page + auto-snapshots + suggestions","feat",
   ["/status + /api/status","daily snapshot task + pre-op hooks","ocrall finisher (resumable)","nomenclature/fault-parts/NIIN-review"],
   "System Status page (counts, coverage, OCR progress, snapshot, correlations, NIIN-drift queue, fault->parts) via fast indexed queries. Automatic snapshots (daily Windows task + pre-op hooks). OCR finishing (ocrall to 0 pending). Suggestions: nomenclature normalization, /api/faultparts, /api/niin_review. Additive (R1/R6)."),
 ("0.32.0","NIIN-review workflow + OCR run guide","feat",
   ["884 drift queue on /status","decide distinct/interchange/error/dismiss","reviews.db (append-only)","OCR-RUN-GUIDE.md"],
   "The 884 NIIN-drift findings become an actionable confirm/reject queue; decisions persist append-only in reviews.db (latest wins, history kept). Plus an OCR run guide. Additive (R1/R6)."),
 ("0.33.0","NSN alias map + GPU readiness","feat",
   ["mark NIIN interchangeable","reviews.db decision","nsn_aliases() expands lookup","gpu_check.py"],
   "Confirmed-interchangeable NSNs find each other in search (grounded, reversible). gpu_check.py GPU verdict. Prioritized the live OCR queue; OCR 1.6%. 23/23 pillar tests."),
 ("0.34.0","Tight, seamless loupe","feat",
   ["instant local zoom (rAF)","sharpen-on-pause (60ms)","crop cache + wheel zoom","cohesive controls"],
   "Loupe reworked: instant local magnification every frame, high-DPI crop sharpens on pause, cached, wheel-zoom. Cohesive control styling. Presentation-only (R1/R6)."),
 ("0.35.0","Page zoom: slider + scroll-to-cursor","feat",
   ["zoom slider 100-400%","hover + scroll toward the spot","double-click reset","composes with tilt/mirror"],
   "Continuous zoom slider + scroll-to-zoom centered on the cursor (loupe off); double-click reset; stacks into the CSS transform with tilt/mirror. Presentation-only (R1/R6)."),
 ("0.36.0","Hardware probe + autonomous adaptive GPU OCR","feat",
   ["sysprobe.py (OS/CPU/GPU/RAM)","hardware_profile.json","run_ocr_auto.bat -> 100%","PP-OCRv5 (self-test guarded)"],
   "sysprobe scans OS/Python/CPU/RAM/GPU/laptop+battery -> resource profile; run_ocr_auto.bat probes, installs the GPU stack (PP-OCRv5 + v4 fallback), runs to 100% unattended (self-restarting), reports. Tuned to RTX 4050: 8 workers @220dpi, 12 @240 in /max."),
 ("0.37.0","COMPLETE backward compatibility: Win11 -> Vista","rule",
   ["per-OS engine substitution","Poppler render fallback","Tesseract OCR fallback","stdlib core everywhere"],
   "Complete feature compatibility Win11 down to Win7/Vista via per-OS engine substitution (PyMuPDF<->Poppler, RapidOCR<->Tesseract; stdlib core). Only GPU acceleration is Win10+ - a speed booster, not a feature."),
 ("0.38.0","Dual-track changelog scaffolding (R7)","rule",
   ["R7: legacy gets its own track","CHANGELOG-LEGACY.md (0.37.0-legacy)","branched timeline generator","parity + backport notes"],
   "Rule R7: legacy builds get a dual-track changelog that branches at creation and shows backports. Scaffolding: CHANGELOG-LEGACY.md starts at 0.37.0-legacy; branched-timeline generator -> CHANGELOG-DUALTRACK.pdf; parity line per entry."),
 ("0.39.0","3D Library + Schematics Library + Reset","feat",
   ["Reset on every moveable view","3D Library /3d (20,869)","Schematics Library /schematics (1,093)","linked from header"],
   "Reset buttons everywhere (schematic viewer clears tilt/zoom/mirror; 3D viewer Reset + double-click). 3D Library (/3d): searchable gallery of 20,869 dimensioned parts, live mini 3D thumbnails. Schematics Library (/schematics): 1,093 schematic/wiring docs with a built-in page viewer. Additive, read-only (R1/R6)."), ("0.40.0","Make it pop: WebGL 3D + dynamic schematics","feat",
   ["gl3d.js (no Three.js, offline)","glossy lights + turntable + smooth","schematic pan/zoom toward cursor","blueprint mode + fade"],
   "Real-time WebGL 3D viewer (engine/ui/gl3d.js, dependency-free, served at /gl3d.js): glossy multi-light shading, antialiasing, smooth normals for round families, idle turntable, orbit/zoom/reset; the 3D Library uses it with an SVG fallback (RPS-safe). Schematics viewer made dynamic: buttery drag-pan + cursor-centered wheel zoom, one-tap Blueprint mode (white-on-blue), fade page transitions, plus Clean. Presentation-only and grounded (R1/R6) - same geometry/pages, just rendered & navigated dynamically. JS lint clean; interactive demos shown."), ("0.41.0","Schematics: explore from every angle + rail","feat",
   ["tilt X/Y (-70..70) + mirror","examine left/right/above/below + back","related-sheets rail (same vehicle)","reset clears tilt+mirror"],
   "The dedicated /schematics viewer now explores a sheet as thoroughly as possible: tilt X and tilt Y sliders (CSS perspective, honest flat-sheet) view it from the left, right, above, below and any angle between; a mirror flips to the back; all composed with pan + cursor-zoom + Clean + Blueprint. A related-sheets rail surfaces the same vehicle's other schematic/wiring sheets (left-side, right-side, power, lighting) one click away (/api/schematics?q=vehicle). Reset clears zoom/pan/tilt/mirror. Grounded & presentation-only (R1/R6): a 2D schematic has no true hidden 3D, so none is invented - you explore the real sheet + its real companions."), ("0.42.0","Circuit Lab: overlay editor + real-time simulator","feat",
   ["overlay editor on a real TM sheet","custom MNA engine (circuitsim.js)","run/DC/step + scope + logic view","grounded; RPS static fallback"],
   "Circuit Lab (/circuitlab): build or trace a circuit on top of a real schematic, then watch it run - a learning/advanced-display tool. Dependency-free MNA engine (engine/ui/circuitsim.js): G.v=i, backward-Euler companion models for C/L, Newton-Raphson with SPICE-style limiting for diodes/LEDs; runs as a browser global and a Node module. Snap-grid editor (V/R/C/L/D/LED/SW/GND), wire pin-to-pin, log-slider tuning; Run/DC/Step with node-voltage colours, current dots, per-node scope, Analog/Logic view, 6 demos. Opens over a sheet from /schematics (?doc=&page=). All MNA unit tests pass (divider 2.5V, RC 3.159V@tau, diode 0.574V, series D+LED 3.34mA, underdamped RLC). Grounded & additive (R1/R6): the sim never rewrites the TM; raster->netlist extraction deferred to desktop. RPS (R7): live sim is modern-browser; legacy build degrades to static-overlay only."), ("0.43.0","Look-Alike Parts recognizer","feat",
   ["query: NSN or part name","group by NSN + find discriminators","verdicts: variant/same/diff-class","grounded cues + cited figures"],
   "Look-Alike Parts (/partdiff, part_differences() + /api/partdiff): tells apart parts that look identical in the manual but are functionally different. Finds every catalogued part sharing a name, collapses to distinct NSNs, and reports the discriminators (NSN/FSC/UOC/CAGEC/SMR/part#). Four colour-coded verdicts: reference, different variant (same name diff NSN - usually a different vehicle config, the UOC is the tell), same item (NIIN format drift - interchangeable), different item class (diff FSC - shares a figure title, not a substitute). Grounded 'how to tell apart' cues + cited figure links; cross-platform interchangeability from the correlations sidecar. Read-only & additive (R1/R6); the empty part_variants table is now populated on demand. Validated on a synthetic schema mirror."), ("0.44.0","Circuit Lab deepened: active devices + save/export","feat",
   ["AC / MOSFET / op-amp / relay","generalised N-pin model","save/load + .json + netlist export","parts link to /partdiff"],
   "Circuit Lab deepened: four new active devices in the MNA engine (AC source, N-channel MOSFET square-law, ideal op-amp VCVS, behavioral relay coil+contact) - engine now 10/10 unit tests. Generalised N-pin editor model lets 3-pin (MOSFET, op-amp) and 4-pin (relay) devices place/rotate/wire; netlist() emits engine pin order. Save/Load (localStorage), download/import .circuit.json, export SPICE-style .cir netlist. Tag any part with a TM #/NSN that one-click jumps to Look-Alike Parts. 8 demos (added AC+RC, MOSFET switch, relay lamp, op-amp x2), all validated end-to-end. Grounded/additive (R1/R6); RPS (R7) static-overlay fallback on legacy."), ("0.45.0","Retroactive Post-Support: speed on old PCs","rule",
   ["probe → modern/lite/legacy mode","page-render disk cache + prebake","per-mode SQLite tuning","ES5 polyfills + lite effects"],
   "Retroactive Post-Support (rps.py): a Win11 program that stays responsive back to Win7/Vista by auto-adapting, not dropping features. One probe picks a mode (modern/lite/legacy; --mode or ?mode= override). Page-render disk cache (index/pagecache) renders a page once then serves from disk; --prebake N warms hot pages; warm-on-view renders next pages in a thread. Per-mode SQLite PRAGMAs (big mmap/MEMORY on modern; tiny/mmap-off/FILE on legacy) - connection-local, index never rewritten. rps.js shims fetch/Promise/etc for old browsers + disables animations off the modern path. New /api/rps + /rps.js; DPI capped per mode. COMPLETE compatibility via engine substitution (R1/R6), all additive/read-only. 13/13 rps.py unit tests pass."), ("0.46.0","Faster transport + Performance toggle","feat",
   ["gzip text/json/js/svg responses","HTTP/1.1 keep-alive","Settings: Auto/Modern/Lite/Legacy","server DB tuning stays auto"],
   "Two RPS finishers. gzip + HTTP/1.1 keep-alive in _send(): one TCP connection reused across requests; JSON/HTML/JS/SVG gzipped when the browser supports it (skips <512B + already-compressed PNG/PDF; Vary: Accept-Encoding). Verified by curl (2KB JSON -> 45B, keep-alive reuse, PNG/small left alone). Performance toggle in Settings (Auto/Modern/Lite/Legacy, saved per-browser; rps.js re-applies live via /api/rps?mode=). The server's SQLite tuning + page cache stay auto-picked from real hardware so a UI choice can't mis-tune the DB; --mode forces the server at launch. Additive/presentation-perf only (R1/R6)."), ("0.47.0","How to do it: the procedure view","feat",
   ["part / NSN -> FTS match","parse steps / tools / cautions","kind-tagged cited cards","grounded, grows with OCR"],
   "Procedure view (/procedure, procedure_for()): closes the 'complete instructional rundown' gap. FTS-matches pages describing the part AND a procedure word, then parses each into section kind, numbered steps, the TOOLS REQUIRED block, and WARNING/CAUTION/NOTE callouts - shown as kind-tagged cards linking the real cited page. The procedures table shipped empty so this parses page text at query time (read-only); verified on a work-package page. Improves as OCR makes scanned procedures searchable (R1/R6)."), ("0.48.0","Solve it: the workflow hub","feat",
   ["symptom -> likely parts","procedure + tools + cautions","look-alike (UOC) check","related schematic"],
   "Solve-it hub (/solve): one screen from symptom to fix. Enter a problem or part; it stitches likely parts (faultparts) + manual hits (search), then for a chosen part the procedure (steps/tools/cautions), the look-alike NSN check (partdiff - the UOC is the tell), and the related schematic. Pure client-side orchestration of tested endpoints, each panel deep-linking the cited page; keep-alive makes it snappy. Additive (R1/R6)."), ("0.49.0","Type-ahead predictive search","feat",
   ["vehicles + parts + manual words","FTS vocab, prefix-ranked","offline & instant dropdown","keyboard navigable"],
   "Type-ahead search (/api/suggest + dropdown): google-style suggestions as you type, fully offline so it's instant. Sources prefix-matched + ranked: vehicles (cached), previously-requested part names, and real manual words from the FTS vocab table by frequency. Debounced 120ms; up/down to choose, Enter to search; screen-reader labelled. Read-only over existing indexes, no scan/writes (R1/R6); validated on a synthetic FTS5 vocab DB."), ("0.50.0","Add documents (no command line)","feat",
   ["paste a folder of PDFs","read-only preview: new vs indexed","snapshot + crawl + live progress","additive, resumable"],
   "Add-documents UI (/ingest): point THE VIEWER at a folder and index the NEW PDFs, no CLI - the 'add files without a sweat' goal. Preview (read-only) shows total/already-indexed/new; Index now takes a safeguard snapshot then runs the tested viewer_ingest crawl in the background; progress (files/docs/text/OCR-queued) is read from the runs table and polled every 2s. Additive only - never deletes/overwrites, dedups by path+fingerprint, resumable, rollbackable (R1/R6). Verified on a synthetic folder."),
]

def esc(s): return html.escape(s)

def build():
    W=1020; HEAD=120; ROW=132; H=HEAD+ROW*len(V)+30
    P=[f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" role="img" font-family="-apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif">']
    P.append('<defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#9aa5b1"/></marker></defs>')
    P.append(f'<rect x="0" y="0" width="{W}" height="{H}" fill="#0f1419"/>')
    P.append('<text x="40" y="52" font-size="24" font-weight="700" fill="#e6e9ee">THE VIEWER - Visual Changelog</text>')
    P.append('<text x="40" y="78" font-size="12" fill="#9aa6b6">A functioning data-flow panel for every version (chronological). Dark (R3) - PDF (R5) - accompanies docs/CHANGELOG.md (R4).</text>')
    P.append(f'<line x1="40" y1="98" x2="{W-40}" y2="98" stroke="#2a2f37"/>')
    P.append('<rect x="40" y="104" width="12" height="10" rx="2" fill="#16301f" stroke="#2f5a3e"/><text x="58" y="113" font-size="10" fill="#9aa6b6">feature</text>')
    P.append('<rect x="120" y="104" width="12" height="10" rx="2" fill="#3a2f1a" stroke="#6b5526"/><text x="138" y="113" font-size="10" fill="#9aa6b6">fix</text>')
    P.append('<rect x="178" y="104" width="12" height="10" rx="2" fill="#1a2740" stroke="#3a4d6e"/><text x="196" y="113" font-size="10" fill="#9aa6b6">rule/standard</text>')
    for i,(ver,title,kind,flow,expl) in enumerate(V):
        y=HEAD+i*ROW; bf,bs=KIND_FILL[kind]
        P.append(f'<line x1="150" y1="{y}" x2="150" y2="{y+ROW}" stroke="#2a2f37"/>')
        P.append(f'<circle cx="150" cy="{y+34}" r="7" fill="{bf}" stroke="{bs}"/>')
        P.append(f'<rect x="40" y="{y+18}" width="92" height="30" rx="7" fill="{bf}" stroke="{bs}"/>')
        P.append(f'<text x="86" y="{y+38}" text-anchor="middle" font-size="14" font-weight="700" fill="#e6e9ee">{esc(ver)}</text>')
        P.append(f'<text x="172" y="{y+30}" font-size="14.5" font-weight="700" fill="#e6e9ee">{esc(title)}</text>')
        words=expl.split(); lines=[]; cur=""
        for w in words:
            if len(cur)+len(w)+1>112: lines.append(cur); cur=w
            else: cur=(cur+" "+w).strip()
        if cur: lines.append(cur)
        for li,ln in enumerate(lines[:2]):
            P.append(f'<text x="172" y="{y+50+li*15}" font-size="10.5" fill="#9aa6b6">{esc(ln)}</text>')
        fx=172; fy=y+84; bw=160 if len(flow)<=4 else 132; gap=26
        for j,node in enumerate(flow):
            x=fx+j*(bw+gap)
            P.append(f'<rect x="{x}" y="{fy}" width="{bw}" height="36" rx="8" fill="#1c2430" stroke="#38414e"/>')
            if len(node)<=(24 if bw>=160 else 20):
                P.append(f'<text x="{x+bw/2}" y="{fy+23}" text-anchor="middle" font-size="10.5" fill="#e6e9ee">{esc(node)}</text>')
            else:
                half=len(node)//2; sp=node.rfind(" ",0,half+6); sp=sp if sp>0 else half
                P.append(f'<text x="{x+bw/2}" y="{fy+16}" text-anchor="middle" font-size="9.5" fill="#e6e9ee">{esc(node[:sp])}</text>')
                P.append(f'<text x="{x+bw/2}" y="{fy+28}" text-anchor="middle" font-size="9.5" fill="#e6e9ee">{esc(node[sp:].strip())}</text>')
            if j<len(flow)-1:
                ax=x+bw; P.append(f'<path d="M{ax},{fy+18} L{ax+gap},{fy+18}" stroke="#9aa5b1" stroke-width="1.6" fill="none" marker-end="url(#a)"/>')
    P.append(f'<text x="40" y="{H-12}" font-size="10" fill="#6b7280">Rules in effect: R1 backwards-compatible - R2 diagram per addition - R3 dark+PDF - R4 changelog per change - R5 graphical changelog + PDF.</text>')
    P.append('</svg>')
    return "\n".join(P)

if __name__ == "__main__":
    here=os.path.dirname(os.path.abspath(__file__)); base=os.path.join(here,"CHANGELOG-VISUAL")
    svg=build(); open(base+".svg","w",encoding="utf-8").write(svg)
    cairosvg.svg2pdf(bytestring=svg.encode("utf-8"), write_to=base+".pdf")
    # (PNG preview removed 2026-08-18: redundant with the .svg above; see docs/diagrams/_common.py render() note)
    print("wrote", os.path.getsize(base+".pdf"), "bytes ->", base+".pdf")
