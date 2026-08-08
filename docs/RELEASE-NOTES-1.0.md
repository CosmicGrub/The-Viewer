# THE VIEWER — v1.0.0 Release Notes

**An offline search engine + dynamic viewer for military Technical Manuals**, built for mechanics: find any part or
procedure fast, see how to remove/install it with the right tools and torque, tell look-alike parts apart, and read the
figures with dynamic graphics — all with **no internet**.

## What it does (the pillars)
- **Find anything, offline & fast** — full-text search across the whole corpus (NSN, part number, nomenclature, key
  terms), Last-4 NSN lookup, typo/synonym tolerance, predictive type-ahead, in-document Ctrl+F, and now **semantic
  search** (by meaning) and **visual search** (photo → figure crop).
- **Complete instructional rundown** — the **Work Order** builds one cited PDF for a task: procedure steps, tools,
  materials, WARNING/CAUTION callouts, torque values, the parts on each figure, and the rendered TM pages. Plus
  dedicated **Torque quick-reference** (with ft-lb/in-lb/N·m converter), **Fastener reference**, and **PMCS finder**.
- **Tell parts apart** — the **Look-Alike Parts** recognizer and per-part look-alike warnings distinguish same-name
  parts by NSN/UOC/CAGEC/SMR/FSC; **Related parts & assemblies** shows what a part sits inside and ships with.
- **Dynamic graphics for every level** — deep-zoom with callout hotspots, offline line-art vectorization, auto-CAD
  renders (static + interactive turntable), a 3-D library, the Living Schematic (inferred netlist + animated flow),
  and Circuit Lab.
- **Add documents without a sweat** — drag-drop / paste-a-path ingest, resumable, corpus stays read-only.
- **Find your way around** — a Ctrl+K command palette on every page (Recent + tag search), a Tools menu, My Bench
  (pin what you're working on), and a "Most used here" home panel driven by local, offline usage analytics.

## Under the hood
- **Two build tiers**: modern GPU/production and a **Retroactive Post-Support** legacy tier (Windows 7/Vista, dual-track
  changelog with parity notes).
- **Quality bar**: a self-auditing feature check (no dead wiring), property/fuzz harness over the pure helpers
  (~2M+ cases, real bugs caught & fixed), an HTTP-level integration fuzz (no 5xx), mutation testing, and a
  no-truncation completeness gate — all consolidated in `VERIFY-099.bat` / `RUN-ALL-VERIFY.bat`.
- **Portable**: one-click `BUILD-INSTALLER.bat` produces a no-Python package for shop-floor PCs; `FIRST-RUN.bat`
  points it at the corpus and re-tunes to the machine.

## Before you cut 1.0 (run these host-side)
1. `RUN-ALL-VERIFY.bat` — green-light everything (verify + audit + completeness + HTTP fuzz + mutation + visual index).
2. `RESUME-OCR.bat` — finish OCR (the text layer; currently ~43.8%). Not required for 1.0 of the *software*, but it
   completes the *dataset*.
3. Optional: `BUILD-EMBEDDINGS.bat` (semantic index), `BUILD-INSTALLER.bat` (package).
4. `CUT-V1.0.bat` — stamps VERSION 1.0.0, banners the changelogs, snapshots a tagged backup.

## Known follow-ups
- Semantic/visual indexes must be built once host-side before those pages return results.
- OCR completion is a long GPU run (resumable); the daily task reports progress.

*The full per-iteration history is in `docs/CHANGELOG.md` (+ `CHANGELOG-LEGACY.md`) and the visual
`docs/ITERATION-DASHBOARD.html`.*
<!-- END OF FILE -->
