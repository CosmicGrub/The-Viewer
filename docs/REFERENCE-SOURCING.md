# THE VIEWER — Authoritative reference-data sourcing (NSN & hardware)

*Assessment for filling the database's blanks from authoritative public sources. The engine stays
offline; any pull is a one-time, hand-run step (ideally on a connected machine, then copy the DB back).
Companion diagram: `docs/diagrams/33-nsn-sourcing-assessment.pdf`.*

## Sourcing your TM PDFs (the manuals themselves)

Everything below this section is about NSN/parts *reference* data (PUB LOG, FLIS) — a separate
question from where the Technical Manual PDFs THE VIEWER indexes come from in the first place.
Recommendations annex #16 (onboarding-sourcing).

**THE VIEWER does not ship, host, download, or redistribute any TMs.** It only indexes PDFs you
already have and place in your local `corpus` folder (see `START-HERE.bat` option 0 /
`FIRST-RUN.bat`). This is deliberate, not an oversight: most Army TMs carry a DoD distribution
statement (commonly B, C, or D — controlled, not public release), so a generic "here's where to
download TMs" guide would risk pointing at, or facilitating, unauthorized redistribution of
controlled technical data. That's a real legal boundary this doc won't cross, even informally.

What to actually do: get your unit's manuals through the channel your unit already uses —
- Your unit's **publications clerk / S4** — the normal channel for issuing/updating TMs.
- **LOGSA's Electronic TM (ETM) system**, for units with an active account for their assigned
  equipment.
- Your existing **AKO / unit publications library**, if your unit maintains one.
- A manual **you already legitimately possess** (a physical copy scanned, or a PDF already on a
  unit share drive) — just copy or link it into the `corpus` folder.

Whichever path applies, confirm the copy you're indexing is the current authorized edition for your
equipment before relying on any value THE VIEWER extracts from it — this app never validates that on
its own (see `docs/SYSTEM-REQUIREMENTS.md` and the Masterfile's own confidence badges for how
extracted values are flagged, not verified against publication currency).

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
