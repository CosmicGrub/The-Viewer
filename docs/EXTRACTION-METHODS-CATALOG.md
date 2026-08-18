# THE VIEWER — Extraction Methods Catalog (every possible path to pull data from the files)

The goal of R11: pull **100% of the information** out of the corpus (scanned + born-digital TM PDFs, IETMs, catalog
data files, images). This is the full menu — everything already in the program plus every method still on the table —
so we can choose deliberately. Status: **✅ done** · **◐ partial** · **○ potential (not yet built)**. Each entry notes
the *approach / library* and a rough *effort* (S/M/L). Everything stays read-only on the corpus; new data goes to
append-only sidecars (R1/R6).

---

## 1. Getting the text off the page (the raw character layer)

| # | Method | Status | Approach / library | Effort |
|--|--------|--------|--------------------|--------|
|1.1| Native PDF text | ✅ | PyMuPDF `get_text` for born-digital pages | — |
|1.2| GPU OCR (scanned pages) | ✅ | RapidOCR PP-OCRv5/v4 (RTX 4050, onnxruntime-gpu; Tesseract CPU fallback) — switched from EasyOCR in v0.6.0 | — |
|1.3| **OCR pre-processing** — deskew, denoise, binarize (Sauvola/Otsu), dewarp | ✅ | `ocrprep.py` (skew/denoise/Otsu, cv2) | — |
|1.4| **Super-resolution before OCR** — upscale low-DPI scans | ○ | Real-ESRGAN / OpenCV; recovers tiny dimension text | M |
|1.5| **OCR ensemble / voting** — run 2+ engines, keep highest-confidence tokens | ○ | Tesseract + PaddleOCR/RapidOCR + EasyOCR, merge by confidence | M |
|1.6| **Transformer OCR (degraded text)** | ○ | TrOCR / PaddleOCR-rec for hard pages only (GPU) | M |
|1.7| **Handwriting recognition (HTR)** — margin notes, stamps | ○ | Kraken/Calamari or TrOCR-handwritten | L |
|1.8| Per-page rotation / orientation detection | ✅ | `ocrprep.detect_orientation` (pytesseract OSD) | — |
|1.9| Per-word OCR **confidence capture** (drives everything downstream) | ◐ | RapidOCR already returns per-line conf, persisted page-level since v1.13.5 — per-token capture still not built | S |

## 2. Understanding page structure (layout, reading order, regions)

| # | Method | Status | Approach / library | Effort |
|--|--------|--------|--------------------|--------|
|2.1| Ruled-table detection & extraction | ✅ | PyMuPDF `find_tables` (`tables.py`) | — |
|2.2| **Advanced table extraction** — borderless / spanning cells | ✅ | `tables_plus.borderless_tables` (pdfplumber) + `/api/tables_plus` | — |
|2.3| **Cross-page table stitching** — one table split over pages | ✅ | `tables_plus.stitch` (data-row/repeated-header aware) | — |
|2.4| **Document layout analysis** — title/para/figure/table/caption/header | ✅ | `layout.py` (heuristic over PyMuPDF blocks, no ML) + `/api/layout` | — |
|2.5| **Reading-order reconstruction** (multi-column TMs) | ○ | column detection + XY-cut; fixes scrambled OCR order | M |
|2.6| Header/footer / running-title stripping | ✅ | `pagetrim.py` (recurrence heuristic) | — |
|2.7| **Section / chapter hierarchy** — TOC + heading detection | ◐ | PDF outline + font-size heading model; powers chapter routing | M |
|2.8| **Page-type classifier** — RPSTL vs procedure vs schematic vs PMCS vs LP | ◐ | features + small model; routes each page to the right parser | M |

## 3. Turning text into meaning (semantic / structured extraction)

| # | Method | Status | Approach / library | Effort |
|--|--------|--------|--------------------|--------|
|3.1| Measurements / dimensions (13 types, ranges, tolerances) | ✅ | `measures.py` regex | — |
|3.2| Unit normalization + dual display | ✅ | `units.py` (new) | — |
|3.3| RPSTL / NSN / NIIN / CAGE / P-N / UOC / SMR parsing | ✅ | `viewer_ingest` + correlations | — |
|3.4| Torque & PMCS structured extraction | ✅ | `torque` / `pmcs.py` | — |
|3.5| Procedure / step / tools / materials / cautions parsing | ✅ | `procedures_feature` / `jobcard` | — |
|3.6| **Leading-particulars key:value pairs** ("Length: 180 in") | ✅ | `leadingspecs.py` → measures sidecar → Masterfile | — |
|3.7| **Thread / fit / GD&T spec parsing** (1/2-13 UNC, class 2A, Ø.500±.002) | ✅ | `specparse.py` + `/api/specs` | — |
|3.8| **Fluid / lubricant / MIL-SPEC references** (MIL-PRF-2104, DF-2, JP-8) | ✅ | `specparse.py` (standard/fluid kinds) | — |
|3.9| **Warnings / Cautions / Notes** as first-class objects | ✅ | `cautions.py` (severity-ranked) + `/api/cautions` + dossier card | — |
|3.10| **Acronym / abbreviation expansion** (per-TM glossary) | ✅ | `acronyms.py` + `/api/acronyms` | — |
|3.11| **Relation extraction** (part→assembly, callout→part, see-also) | ✅ | `kg.py`/`build_kg.py` graph (part↔figure↔spec↔nsn↔vehicle) | — |
|3.12| **Local-LLM structured extraction** — page text → JSON specs | ○ | small offline GGUF (llama.cpp) for messy pages | L |

## 4. Figures, drawings, and imagery

| # | Method | Status | Approach / library | Effort |
|--|--------|--------|--------------------|--------|
|4.1| Figure ↔ part callout mapping | ✅ | `figureparts.py` | — |
|4.2| Vector / line-art text extraction | ✅ | `vectorize.py` | — |
|4.3| Perceptual-hash visual part search | ✅ | `phash.py` | — |
|4.4| Schematic netlist inference + flow overlay | ✅ | `schemgraph.py` | — |
|4.5| **Callout-number OCR on figures** (leader lines → item no.) | ✅ | `callouts.py` (Tesseract digits + link to `dimscan` lines) + `/api/callout_numbers` | — |
|4.6| **Dimension-line / GD&T extraction from drawings** (arrows + numbers, rotation-aware) | ◐ | `dimscan.py` detects rotated dimension-line geometry (cv2) + `/api/dimscan`; number-OCR is the host-side step (needs OCR engine) | — |
|4.7| **Exploded-view association** — every callout → its RPSTL row | ○ | combine 4.5 + RPSTL; completes the parts picture | M |
|4.8| **Symbol / component detection on schematics** | ✅ | `symbols.py` (OpenCV template match + NMS) | — |
|4.9| **Barcode / QR / Data-Matrix** on pages | ◐ | `barcodes.py` (OpenCV QR now; add `pyzbar` for 1-D/DataMatrix) | S |
|4.10| Figure / photo vs diagram classification | ◐ | region + classifier; routes to the right handler | M |
|4.11| **Icon / warning-symbol detection** (⚠, ☢, electrical) | ✅ | `symbols.py` (same template-match engine) | — |

## 5. PDF-native objects (data that isn't "text on a page")

| # | Method | Status | Approach / library | Effort |
|--|--------|--------|--------------------|--------|
|5.1| PDF bookmarks / outline (TOC) | ✅ | `pdfmeta.outline` + `/api/pdfmeta` | — |
|5.2| PDF metadata (title/author/dates/producer) | ✅ | `pdfmeta.metadata` + `/api/pdfmeta` | — |
|5.3| **PDF annotations / comments / highlights** | ✅ | `pdfmeta.annotations` | — |
|5.4| **AcroForm form fields** (fillable IETMs, DA forms) | ✅ | `pdfmeta.form_fields` + `/api/pdfmeta` | — |
|5.5| **Embedded files / attachments** in the PDF | ✅ | `pdfmeta.embedded_files` + `/api/pdfmeta` | — |
|5.6| Optional-content **layers (OCGs)** | ✅ | `pdfmeta.layers` (name/on/usage) + `/api/pdfmeta` | — |
|5.7| Embedded-font / glyph mapping (fix garbled ToUnicode) | ○ | rebuild CMap; recovers "unreadable" born-digital text | M |
|5.8| Intra-PDF hyperlinks / named destinations | ✅ | `pdfmeta.links` | — |

## 6. Catalog & structured source files (not PDFs)

| # | Method | Status | Approach / library | Effort |
|--|--------|--------|--------------------|--------|
|6.1| PUB LOG / FLIS CSV & DBF ingest | ◐ | `viewer_ingest` (publog); expand coverage | M |
|6.2| **IETM / S1000D / MIL-STD-40051 XML/SGML** parsing | ✅ | `ietm.py` (stdlib xml.etree, namespace-agnostic) + `/api/ietm` | — |
|6.3| Fixed-width / legacy mainframe extracts | ○ | schema-driven parser | M |
|6.4| Excel / ODS spec workbooks | ○ | `openpyxl` | S |

## 7. Cross-document intelligence (connecting what's extracted)

| # | Method | Status | Approach / library | Effort |
|--|--------|--------|--------------------|--------|
|7.1| Edition / duplicate detection across TMs | ◐ | `dedup.py` (shingle + Jaccard clustering) — implemented, no caller yet (no `build_dedup.py` sidecar or `/api/dedup` route) | S |
|7.2| NIIN-drift correlation + confirmed-interchangeable alias map | ✅ | `correlations.db` | — |
|7.3| Semantic / embedding index | ✅ | `embed.py` | — |
|7.4| **Knowledge graph** (part↔figure↔procedure↔spec↔NSN) | ✅ | `kg.py` + `build_kg.py` → `index/kg.db` + `/api/kg` | — |
|7.5| **Multi-method cross-validation** — same value from ≥2 methods ⇒ higher confidence | ✅ | `crossval.py` (agreement → confidence; conflict flag) | — |

## 8. External enrichment (fill blanks — corpus authoritative, R11)

| # | Method | Status | Approach / library | Effort |
|--|--------|--------|--------------------|--------|
|8.1| Internet Archive full-text + **Wayback-route every link** | ✅ | `enrich.py` / `build_enrich.py` | — |
|8.2| Consolidate into the linkless **Masterfile** | ✅ | `masterfile.py` | — |
|8.3| Manufacturer / MIL-SPEC / standards spec sheets | ○ | seed list + Wayback (already supported via seeds) | S |
|8.4| Official FLIS / PUB LOG online lookups | ○ | add as an enrich source | M |

## 9. Quality, confidence & validation (trust the data)

| # | Method | Status | Approach / library | Effort |
|--|--------|--------|--------------------|--------|
|9.1| OCR-confidence capture & low-confidence flagging | ◐ | `textquality.py` post-hoc quality score + clean/suspect/poor flag | — |
|9.2| Unit **sanity / outlier detection** (implausible values) | ◐ | `masterfile._spread` wide-variance flag (new); extend with plausible ranges | S |
|9.3| Provenance tracking (source, archived URL, timestamp) | ✅ | `enrich.db` | — |
|9.4| Duplicate-value dedup + canonicalization | ✅ | Masterfile filtered layer | — |
|9.5| **Active-learning review queue** for low-confidence items | ◐ | `reviews.db`; extend to measurements | M |

## 10. Heavy ML / vision-language (highest ceiling, highest cost)

| # | Method | Status | Approach / library | Effort |
|--|--------|--------|--------------------|--------|
|10.1| **Vision-language document QA** (ask a page for a value) | ◐ | `vlm.py` pluggable interface + `/api/vlm`; drop in a GPU model backend (Donut/Qwen-VL/…) to enable | — |
|10.2| Table-structure transformer (TATR) for scanned tables | ○ | microsoft/table-transformer | M |
|10.3| Mil-spec-tuned NER (parts, tools, specs) | ○ | fine-tune a small token classifier | L |
|10.4| Layout model to drive *every* parser (§2.4) | ○ | one segmentation feeding all extractors | L |

---

## How to choose — recommended sequencing

**Highest value, lowest cost first** (each feeds the Masterfile and needs no GPU):
1. **§3.6 leading-particulars key:value** + **§5.1/5.2 PDF outline & metadata** + **§4.9 barcodes** — pure-stdlib/PyMuPDF, immediate dimensional & catalog gains. (S each)
2. **§9.1 OCR-confidence capture** — unlocks quality flagging everywhere for little work. (S)
3. **§3.7 thread/fit/GD&T** + **§3.8 MIL-SPEC/lubricant** parsers — direct machining value. (M)
4. **§2.3 cross-page table stitch** + **§2.2 borderless tables (Camelot/pdfplumber)** — recover tables OCR/`find_tables` miss. (M)

**Big structural wins (medium-heavy):**
5. **§2.4 layout analysis** as the backbone that improves reading order, table, and figure extraction at once. (L)
6. **§4.6 dimension-line / GD&T from drawings (rotation-aware)** — the marquee "spatial data" capability. (L)
7. **§6.2 IETM/S1000D XML** — if any structured TM source exists, it's the richest data of all. (L)

**Force-multiplier (GPU, transformative):**
8. **§10.1 vision-language page QA** — ask each page directly for the values the regex/table paths miss.

Each method here is additive, sidecar-based, and slots into the existing measures → tables → enrich → **Masterfile**
pipeline. Pick a lane and it ships with the usual R1–R10 discipline.

<!-- END OF FILE -->
