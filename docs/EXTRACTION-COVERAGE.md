# THE VIEWER — Extraction Coverage Map (v1.1.1)

Goal: **retrieve 100% of the information** in the corpus — every file format, every layer of a page, and
especially **measurements / dimensional data** on materiel, parts, and equipment. This map enumerates every
extraction, scrape, parse, and detection method the program applies, what each one covers, and where the
output lands. Everything here is **read-only on the corpus** and writes only to the index or an append-only
sidecar (R1 / R6).

---

## 1. Page content — what each layer pulls out

| Layer / method | Module | Covers | Output |
|---|---|---|---|
| **Native PDF text** | indexer / `fitz.get_text` | Born-digital manuals where the text is already selectable | `pages.body_text` → FTS |
| **OCR (GPU RapidOCR)** | OCR pipeline | Scanned / image-only pages (the majority of legacy TMs) | `pages.body_text` → FTS, `ocr_status` |
| **Structured tables** | `tables.py` (PyMuPDF `find_tables`) | RPSTL rows, torque tables, PMCS grids, **leading-particulars / spec tables** | `index/tables.db` sidecar, `/api/tables` |
| **Measurements / dimensions** | `measures.py` | **Every measured value**: length, dia., clearance/tolerance, torque, pressure, capacity, electrical, temp, flow, weight, force, speed, rotation, angle, thread | live FTS + `index/measures.db`, `/measures`, `/api/measures` |
| **Vector / line-art text** | `vectorize.py` + schematic tools | Callout numbers & labels drawn as vectors (not raster) on schematics/diagrams | figure callouts, `/api/schemgraph` |
| **Figure ↔ part callouts** | `figureparts.py` | Which item-numbers on a figure map to which part rows | `/api/figureparts` |
| **Perceptual image hash** | `phash.py` | Find a part by a **photo** (visual match) even with no text | `index/visual` → `/visual` |
| **Semantic embeddings** | `embed.py` | Meaning-based recall (synonyms, paraphrase) over the OCR text | `index/embeddings.npy` → `/semantic` |

## 2. Identifier & catalog parsing (RPSTL / provisioning)

| Method | Covers | Output |
|---|---|---|
| NSN / NIIN detection | 13-digit stock numbers, NIIN drift & confirmed-interchangeable aliases | search, `correlations.db`, `/partdiff` |
| FSC / CAGEC / part-number / UOC / SMR parse | Provisioning columns in RPSTL tables | `/partdiff`, look-alike warnings |
| Look-alike detection | Same-name parts that differ by NSN/UOC/CAGEC/SMR | `part_differences()` → `/partdiff` |
| Cross-reference graph | Assembly ↔ sub-part ↔ see-also siblings | `xref.py` → `/related` |

## 3. Procedure & maintenance structure

| Method | Covers | Output |
|---|---|---|
| Procedure / step extraction | Disassembly / assembly / install sequences, tools, WARNING/CAUTION | `/procedure`, `/stepflow` |
| PMCS extraction | Before/During/After checks, intervals, "not-fully-mission-capable-if" | `pmcs.py` → `/pmcs` |
| Torque quick-reference | Torque specs cross-referenced to fasteners | `/torque` |
| Fastener / thread ID | Thread size, grade, drive | `/fastener` |
| Side-of-house classify | Operator (-10) vs Mechanic (-20) coverage split | `sides_feature.py` |

## 4. Measurement extraction — the dimensional-data guarantee

`measures.py` is the piece that closes the "especially measurements/dimensional data" gap. It runs a single
tolerant regex over the text layer of every page and captures, for each hit: the **value**, an optional
**range** (`X–Y`), an optional **tolerance** (`X ± Y`), the **canonical unit**, the **dimension type**, the
**sentence it came from**, and its **cited page**. Dimension types covered:

`length · area · angle · weight · force · torque · pressure · capacity(volume) · electrical(V/A/Ω/W/Hz) ·
temperature · flow · speed · rotation`

Unit ordering is deliberate so compound units win over their substrings (`ft-lb` before `ft`, `in-lb` before
`in`, `N-m` before `N`). Two access paths:

* **Live** (`/measures`, `/api/measures`) — on-the-fly over the existing FTS index; **no build step required**.
* **Corpus-wide** (`index/measures.db` via `BUILD-MEASURES.bat`) — every measurement pre-extracted so you can
  browse/count fleet-wide (e.g. "every torque spec across all vehicles").

## 5. Ingest — adding new material (any format)

Drag-drop or `/ingest` accepts new PDFs/files; they flow through the **same** stack above (native text → OCR →
tables → measures → identifiers), so coverage of new material is automatic. Nothing in the source corpus is
modified (R1/R6); new docs are added append-only.

## 6. External gap-fill — closing blanks against the internet (corpus authoritative)

Everything above extracts from the **corpus**, which is the authoritative/default source. When the corpus is
**silent** on a dimension type for a subject, an opt-in enrichment layer cross-references the **open internet** to
fill only that blank — it never overrides a corpus value.

| Stage | Module | What it does |
|---|---|---|
| Gap detection | `enrich.find_gaps` | Per vehicle, which of the 13 dimension types have **no** corpus measurement |
| Online cross-reference | `build_enrich.py` (host-run) | Internet Archive full-text search + **Wayback Machine** snapshots for the subject |
| Extraction | `enrich.extract_external` → `measures.extract` | Same measurement engine, applied to the external text |
| Record | `enrich.record` → `index/enrich.db` | Keeps **only** the missing types; stores provenance (source, URL, Wayback ts, fetched ts); badged `external-unconfirmed` |
| Offline read | `enrich.external_for_query` → `/api/external` | App reads the sidecar with **no network**; any type the corpus answers is filtered out (corpus wins) |

The crawler pulls candidate links from **many sources** per subject — Internet Archive full-text items, optional
web-search results (`engine/enrich_search.py`), and a user seed list (`index/enrich_seeds.txt`) — and **routes every
link through the Wayback Machine** (availability, or Save Page Now with `--save`) so each harvested value is pinned to a
permanent archived snapshot. Guarantees: the running app stays **100% offline** (only the opt-in `ENRICH.bat` crawler
touches the network); the corpus is **never modified** and the sidecar is **append-only** (R1/R6); every external value
carries full provenance (archived URL + original URL + snapshot timestamp) recorded internally.

## 7. The Masterfile — one congruent consolidation (`masterfile.py`)

Everything above lands in **one all-encompassing Masterfile** that is compatible/congruent with the rest of the project:
`build_masterfile.py` merges the corpus measurements (authoritative, page-cited) with the external gap-fills into
`index/masterfile.db` + `docs/MASTERFILE.md`, keyed to the authoritative subjects.

| Layer | What it holds |
|---|---|
| `master_raw` | Every extracted value — corpus **and** external — with origin; corpus rows keep an internal page ref |
| `master_filtered` | One canonical value per subject+dimension (deduped, representative + numeric range + count) |

Rules: the corpus is **authoritative** (external only for dimension types it lacks; never overridden). **No links are
surfaced** — corpus rows point to the manual page (a reference *into* the authoritative files, which is desired);
external web provenance stays inside `enrich.db` for audit only. Served at `/master` (filtered summary over raw list).

## 8. Known gaps / roadmap

* **Rotated/curved dimension text** on engineering drawings — partially caught by vector text; a rotation-aware
  pass is on the v1.1 roadmap (visual-index quality pass).
* **Handwritten annotations** on scanned pages — OCR catches some; not guaranteed.
* **Cross-page tables** (a table split across two pages) — each page is parsed independently today; stitching
  is a v1.2 candidate.

These are tracked in `docs/ROADMAP-1.1.md`; per R6 nothing is removed as coverage improves — new methods are
added alongside the old.

<!-- END OF FILE -->
