# Schematic Highlighter Mode — feasibility & plan

**Goal:** a "highlighter mode" that makes a schematic clickable, so selecting an element/part of the
drawing highlights it (and ideally cross-links it to the legend / parts list / dossier).

## The deciding fact: your schematics are mixed

A schematic image has no inherent structure — what's clickable depends on whether the PDF carries real
geometry or is just a picture. Probed 40 schematic PDFs from the corpus (first page each):

| Type | Share | What it means |
|---|---|---|
| **Vector** (real line/curve/text ops) | **~45%** | Clickable **now**, no conversion — the geometry is in the file |
| **Raster scan** (one full-page image, often no text) | **~38%** | Just pixels — needs OCR text or image processing to click |
| **Hybrid** (vector annotations over a scan, or vector + a background image) | **~18%** | Partly clickable (the vector/text parts) |

So there is no single answer — the right mode is chosen **per page**, automatically.

## What's possible — four approaches

### 1. Vector-path overlay  ·  *recommended Phase 1*  ·  ~45% (vector) + the vector parts of hybrids
PyMuPDF can read a vector page's drawing operations (`page.get_drawings()` → lines, rects, curves with
coordinates) and its text words (`get_text("words")`) **on demand, with no conversion**. The server returns
those as normalized coordinates; the page renders a **transparent interactive SVG overlay** on top of the
existing page image. Each path (or a group of connected paths = a "net/trace") becomes hover/click →
**highlight**. Click a wire → highlight the connected run; click a symbol's strokes → highlight the symbol.
- **Pros:** works today on ~half the corpus; crisp, scalable highlight; no pre-processing or storage; reuses
  the existing page render underneath; degrades to plain view if unsupported (RPS-safe — it's SVG + DOM).
- **Cons:** vector pages only; "what is this element" is geometric, not semantic (we know *a shape*, not
  "this is relay K3") unless a nearby text label identifies it; very dense drawings need path-grouping
  heuristics to feel like "one element" instead of one line segment.

### 2. Text / callout hotspots  ·  *Phase 1b, complements #1*  ·  any page with a text layer (vector OR OCR'd)
We already extract callouts (reference designators like `R12`/`K3`, item numbers, part numbers, NSNs, `FIG n`)
and word boxes. Make those **labels clickable**: click a callout → highlight it and **cross-link** to the
legend / parts list / the part dossier (now with PUB LOG manufacturer + interchangeable data).
- **Pros:** reuses what's built (callouts, `page_words`, dossier); gives the *semantic* link a pure shape
  highlight can't; works on raster scans **after OCR** (which is now 100% complete).
- **Cons:** highlights the *label*, not the drawn symbol; depends on OCR quality for scanned pages.

### 3. Raster trace-highlight (flood fill)  ·  *Phase 2, optional*  ·  the ~38% pure scans
On a scanned page, clicking a line runs a **connected-component / flood fill** on the rendered pixels (client
canvas or server) to highlight the contiguous dark trace under the cursor — "follow this wire."
- **Pros:** brings clickable tracing to scans with no text/vector; genuinely useful for following a circuit.
- **Cons:** heuristic (can over/under-select where lines cross or are broken); no semantics; more compute.

### 4. Manual region tagging / full vectorization / ML symbol recognition  ·  *not recommended*
Hand-boxing elements is precise but unscalable across thousands of sheets; full raster→vector + symbol ML is a
large, error-prone, offline-unfriendly project. The **Circuit Lab overlay we already built** covers the
"trace a live circuit on a real schematic" need without going down this road.

## Conversions required
**None up front.** #1 reads vector geometry on demand; #2 reuses OCR; #3 processes pixels on the fly. The only
*optional* optimization is caching a page's extracted paths in a small sidecar (e.g., `schempaths` keyed by
doc+page) so repeat opens are instant — additive, never required, never touches the corpus (R1).

## Recommended build (phased)
1. **Phase 1 — Highlighter toggle + vector overlay + callout hotspots.** A `🖍 Highlighter` button in the
   schematic viewer. On a vector/hybrid page: `GET /api/schempaths?doc=&page=` returns paths + word boxes; the
   page draws the SVG overlay; hover outlines, click highlights (with connected-segment grouping), and clicking
   a labelled element cross-links to the part. On a raster-only page: fall back to callout hotspots (post-OCR).
   *Medium effort, high value, ~60%+ of pages interactive, RPS-safe.*
2. **Phase 2 — Raster trace highlight (flood fill)** for the pure scans, client-side on the canvas. *Optional.*
3. **Phase 3 — Path cache sidecar** if Phase-1 extraction feels slow on big sheets. *Optional.*

## How it fits the rules
Read-only on the corpus (R1); additive (R6); the overlay is SVG/DOM so the legacy/RPS path gets it too; every
highlight is grounded in the actual PDF geometry/text — nothing invented. Ships with the usual diagram +
changelog + legacy entry.

## Open question for you
Phase 1 as above is the sweet spot. Two choices to confirm before building:
- **Highlight granularity on vector pages:** single path under the cursor, or auto-group connected
  segments into a "net/element" (more useful, slightly heuristic)? *(Recommend: connected-group.)*
- **Raster scans:** ship Phase 1 with callout-hotspot fallback only, and add the flood-fill trace (Phase 2)
  later — or include flood-fill from the start?
