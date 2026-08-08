# THE VIEWER — Authoritative reference-data sourcing (NSN & hardware)

*Assessment for filling the database's blanks from authoritative public sources. The engine stays
offline; any pull is a one-time, hand-run step (ideally on a connected machine, then copy the DB back).
Companion diagram: `docs/diagrams/33-nsn-sourcing-assessment.pdf`.*

## Verdict: PUB LOG® (DLA) is the source for military NSN data

After assessing the options, **PUB LOG®** (Public Logistics Data, from DLA Logistics Information
Services) is the right authoritative source — it is **free, updated monthly, requires no CAC or
subscription**, and is **publicly releasable** (restricted / proprietary / NATO data excluded).

- Landing page: <https://www.dla.mil/Information-Operations/Services/Applications/PUB-LOG/>
- Direct download (updated monthly): `https://publogstorage.blob.core.windows.net/publog/PublogDVD.zip`
- Also via the FLIS Data Electronic Reading Room.

### Why it's better than the GSA extract we'd looked at
The GSA NSN Extract (data.gov, CC0) is the **GSA-Advantage commercial subset, last updated 2017** — it
fills only commercially-listed NSNs with dated data. PUB LOG covers that and far more, and is current.

## What PUB LOG provides (and which of our gaps it closes)

PUB LOG bundles five NSN-keyed products + handbooks. The ones that matter here:

- **FLIS Data** — all active non-restricted NSNs + supply data → **NSN → item name / nomenclature**
  (fills the parts-request sheet item names).
- **MCRD (Master Cross-Reference Data)** — **NSN ↔ part number ↔ CAGE**. This is the authoritative
  part number we *deferred* in the structured-parts work because RPSTL OCR was noisy. Solved by data.
- **CHAR (Characteristics Data)** — characteristics per NSN (the item's defining attributes) → the
  **size / thread / material parameter** Tier 2.5 needs to build a parametric 3D model.
- **MDI&S (Management Data, Interchangeability & Substitutability)** — real substitutes/interchangeables
  → grounds **look-alike / variant warnings**; also carries **AAC (Acquisition Advice Code)** → fills the
  **104th's AAC** FEDLOG block.
- **H6 (Federal Item Name Directory)** — approved item names / INCs.

So one public, free, monthly dataset additively closes several open gaps at once (R6: add, never remove).

## Other sources (for completeness)
- **WebFLIS®** (DLA) — per-NSN web lookup; good for verifying a single NSN, not a bulk fill.
- **FED LOG®** (DLA) — fuller product incl. management/pricing, but **access-controlled** (not the public
  path).
- **Commercial mirrors** (nsnlookup, ISO Group, etc.) — scrape FLIS; unofficial, variable quality;
  excluded by the "official-only" preference.

## One-time, offline-preserving procedure
1. On a **connected** machine, download `PublogDVD.zip` (free, no CAC) and extract it.
2. Use PUB LOG's built-in **Search Batch / SQL export** to dump the records for your NSN list to **CSV**
   — fields of interest: NSN, item name, part number, CAGE, characteristics, AAC.
3. Run `python viewer_ingest.py enrich --gsa <export.csv>` (the ingester reads CSV/XLSX) → fills the
   offline reference tables, **append-only and cited** (R6). Copy the DB back. The engine never goes online.

### Caveats
- The `.ZIP` is large (~GB) — a deliberate one-time download.
- The data is delivered in the IMD product format; the **Batch/SQL export** step is how you get clean CSV
  for ingestion (we don't parse the raw IMD files directly).
- To capture part#/CAGE/characteristics/AAC (not just name/price), `enrich` and the `ref_nsn` tables
  would be extended a little — additive, on your go-ahead.

## Recommendation
Adopt **PUB LOG** as the authoritative reference source. When ready: extend `enrich` to the PUB LOG
fields (part#, CAGE, characteristics, AAC, substitutes), you do the one-time download + Batch/SQL export
on a connected machine, and we bake it into the offline index — closing the nomenclature, part-number,
Tier-2.5-size, AAC, and look-alike gaps together, additively.
