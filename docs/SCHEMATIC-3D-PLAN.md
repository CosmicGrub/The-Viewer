# THE VIEWER — Interactive Schematics & (optional) 3D: plan, spec, and sourcing assessment

*Status: planning / shovel-ready. No code built yet (build is gated on OCR — see §2). Companion
diagrams: `docs/diagrams/28-3d-feasibility-spectrum.pdf`, `docs/diagrams/29-3d-architecture-roadmap.pdf`.*

## 0. The decision

- **Build the grounded interactive 2D schematic viewer (Tier 1)** — deep zoom on the real drawing +
  auto callout-hotspots that link to the parts index.
- **Finish OCR (especially schematics) first**, then build.
- **True 3D is optional and deferred**, fed only by *real* 3D data (CAD or photogrammetry). **No
  AI-generated 3D from scans** — it invents geometry (wrong hole count / wrong port), which is exactly
  the failure mode that matters and breaks the project's never-invent rule.

## 0a. Confirmed build order (decided)

1. **Finish OCR** (especially figure/schematic pages) — gate for everything below.
2. **Tier 1 — interactive 2D schematic viewer** (deep zoom + callout-hotspots → parts). §3.
3. **Tier 2.5 — dimension-driven parametric reconstruction**, **scoped to standard parts + the
   look-alike-distinguishing features** (decided). §4b. Parameters sourced from **all four**: NSN→standard
   tables, parsed TM spec/dimension tables, SME-confirmed key dimensions, and countable features from the
   figure.
4. **Optional true-3D module** (real CAD or photogrammetry) for complex bespoke parts. §4, §5.
5. **Never** AI-generated 3D from a scan. §1.

## 1. Why not "AI converts the schematic to 3D"

A single 2D line drawing contains no depth information; recovering 3D from it is mathematically
underdetermined. Neural image-to-3D produces a *plausible* mesh by guessing the unseen geometry. For
maintenance and parts identification, **accuracy beats realism**: a deep zoom of the authoritative
drawing reliably shows the distinguishing detail (number of holes, which port, the connector type); a
generated mesh may quietly get it wrong. So we surface and magnify the real drawing, and reserve true
3D for cases backed by real geometry.

## 2. Readiness gate — "are the schematics ready?"

The viewer's auto-hotspots need the figure pages to be OCR'd (to read callout numbers and their
coordinates). Today the figure/schematic pages are the least-covered part of the corpus:

- Sample index: dedicated schematic/wiring docs are **~43% searchable** vs **~92%** overall — the
  scanned figure pages are the OCR gap.
- Most "schematics" are **exploded-view figures embedded throughout the RPSTL and maintenance manuals**
  (~18k pages reference a figure), not separate wiring documents. So "finish schematic OCR" effectively
  means "finish the OCR pass," prioritising the parts/figure pages (the prioritized queue already does
  this).

**How you'll know it's ready:** the per-vehicle **"% searchable" coverage meter** (shipped in v0.19.0,
shown in the vehicle hub) is the readiness signal. Build Tier 1 for a vehicle once its coverage is high
(say ≥90%). Action item on your side: complete the GPU OCR pass (`run_ocr_gpu.bat`; needs the CUDA
runtime).

## 3. Tier 1 — interactive 2D schematic viewer (the build)

### 3.1 What the user gets
- Open a figure/schematic → **pan and deep-zoom** smoothly to fine detail (holes, ports, connectors).
- **Clickable callout hotspots**: the FIG item-numbers on the drawing become hotspots; click one to jump
  to that part (NSN / part #) in the parts index, cited to the page.
- A back-link the other way: from a part, "show me on the figure" highlights its callout.

### 3.2 Architecture (grounded, offline)
- **Deep zoom:** render the page at high DPI (PyMuPDF) and serve a tile pyramid; display with
  **OpenSeadragon** (MIT, self-hostable offline) or an equivalent. Cache tiles per (doc, page, figure).
- **Hotspot coordinates (the clever, grounded bit):** get the on-page position of each callout number
  - **Text-layer figures:** `PyMuPDF page.get_text("words")` returns every token with its bounding box —
    filter to the small integer callouts near the figure.
  - **Scanned figures:** the OCR engine (RapidOCR) already returns per-token boxes; persist them so
    callout coordinates are available without re-OCR.
  - Store as a new additive table `figure_hotspots(document_id, page, figure_no, item_no, x, y, w, h)`
    (migration 0005, additive — R1).
- **Linking:** `item_no` + `figure_no` + vehicle → the parts index (the Phase-2 row-aligned parts table
  makes this exact; until then, link figure → part *list* and let the user pick, always cited).
- **Endpoints (additive):** `GET /api/figure?doc=&page=` → hotspots + figure meta; reuse `/page` for
  tiles or add `/tile`. No change to search, request, or the dataset.
- **UI:** a new viewer mode (or panel) hosting the OpenSeadragon canvas + an SVG hotspot overlay; clicks
  route into the existing parts/search flow.

### 3.3 Grounding guarantees
- Only the **real rendered page** is shown; hotspots are placed from actual callout coordinates.
- A hotspot links to a part **only when the figure/item mapping is known**; otherwise it opens the
  figure's parts list for the user to confirm. Never a guessed part.

### 3.4 Acceptance criteria
- Smooth zoom to ≥4× native on a representative figure; callouts clickable; click opens the correct,
  cited part; works offline; no regression to search or sheet generation.

### 3.5 Effort
- ~2–4 weeks focused, after schematic OCR coverage is adequate. Phase B (multi-view switcher where TMs
  provide multiple views + hotspot touch-up tooling) is a ~1–2 week add-on.

## 4. Optional true-3D module (BYO real 3D) — design only

A slot, not an auto-converter. A part record can carry a `model_ref`; when present, a **Three.js**
viewer renders it (rotate, free-angle, zoom-to-feature) linked from the part. Two *real* sources feed it;
**never** AI-from-scan.

### 4.1 Source A — existing CAD / 3D technical data
Render real models (**glTF**, or **STEP/IGES → glTF** via an offline converter). Where such data lives,
and the realistic caveats:
- **Technical Data Package (TDP)** — *MIL-STD-31000* defines the deliverable, which can include 3D
  models / **Model-Based Definition (MBD)**. Government rights depend on the acquisition contract.
- **IETM / S1000D** publications can embed 3D models and animations; if a platform's pubs are S1000D,
  3D assets may already exist in the data module set.
- **OEM / prime contractor** holds the source CAD; availability hinges on **data rights** (unlimited vs
  limited/restricted) negotiated in the contract.
- **Provisioning data (LSA/LSAR, GEIA-STD-0007)** ties parts to figures and sometimes to 3D.
- **Caveats (important):** availability varies enormously by platform and contract; much is **export-
  controlled (ITAR/EAR)** or classified; obtain and store only through proper channels. Treat this as an
  **acquisition/data-rights question**, not an engineering one — the viewer is the easy part.

### 4.2 Source B — photogrammetry of the real part
Capture the actual part and reconstruct an accurate textured mesh:
- **Tooling (offline / self-host):** COLMAP or Meshroom (open source), or RealityCapture / Metashape
  (commercial). Output OBJ/glTF.
- **Capture rig:** turntable, even diffuse lighting, fixed-focus camera, 40–120 photos per part, matte
  reference markers; struggles with reflective/transparent/occluded internal features.
- **Workflow:** build a **library over time, prioritising look-alike parts** (the highest-value cases —
  same nomenclature, different connector/port/output). Each becomes a `model_ref` linked from its NSN.
- **Pros:** genuinely accurate, rotatable, zoomable to the distinguishing feature — because it's the real
  part. **Cons:** per-part labor; not automatic; internal geometry needs disassembly or section views.

### 4.3 Effort
- 3D import + viewer: ~2–3 weeks (gated on having real files).
- Photogrammetry pipeline + first library batch: ~3–5 weeks + ongoing capture labor.

## 4b. Tier 2.5 — dimension-driven parametric reconstruction (from dims + views)

*Companion diagram: `docs/diagrams/30-parametric-reconstruction.pdf`.*

This is the grounded version of "approximate 3D from the documentation." It is **reconstruction from
stated dimensions + orthographic/section views** (real engineering), not AI **generation** from a
picture (a guess). The combination does account for something real — for a specific, valuable subset.

**What it reliably grounds**
- **Standard / parametric parts** (a large share of any RPSTL): NSN/part# → a recognized standard
  (bolt, nut, washer, fitting, bearing, connector) → exact geometry from the standard's own tables.
- **The distinguishing features themselves**: thread size, hole/port **count**, connector/pin type —
  stated in specs or countable in the figure. This is precisely the look-alike case.
- **Key stated dimensions** the manual does give (diameters, lengths, clearances, thread/port sizes) —
  enough to size a parametric family member exactly.

**Where it becomes inference (and must be flagged or skipped)**
- Complex castings/housings a TM doesn't fully dimension → the model would interpolate un-stated
  geometry. Under-dimensioned single illustrations → depth unrecoverable. Internal/occluded features
  not drawn → not reconstructable.
- Corpus reality check: TMs/RPSTLs carry scattered specs (diameters ~846, threads ~600, torque ~1,706,
  dim/spec tables ~1,301 pages in the sample) **but** near-zero full GD&T (tolerances ~85, explicit
  bolt-circles ~2). They are illustrations + key specs, **not** dimensioned engineering drawings (TDP).

**Pipeline (offline, grounded)**
1. **Extract parameters:** parse spec tables, resolve NSN→standard identity, count features from the
   figure, and let an SME confirm a few key dimensions.
2. **Parametric CAD generator:** code-CAD (CadQuery / build123d / OpenSCAD) builds the part from those
   parameters — exact and offline, one template per part *family*.
3. **Confidence-labeled 3D (Three.js):** rotate / angle / zoom-to-feature, linked from the part.
   Specified features are exact and cited; un-stated surfaces are shown as a plain schematic placeholder
   marked "representative — not to scale," never as authoritative geometry.

**The grounding rule:** model only what the docs specify; the reconstructed part is trustworthy exactly
where it's labeled trustworthy — and the look-alike difference always lives in the trustworthy part.

**Verdict:** for standard hardware and for the exact look-alike-distinguishing features, this gives
accurate, rotatable, cited 3D from the documents alone — no photos, no CAD sourcing. It does **not** give
accurate full 3D of arbitrary complex castings from a TM (that still needs a TDP or photogrammetry).
Effort: ~3–5 weeks for the first part-family templates + extractor; grows family-by-family.

## 5. Sourcing assessment — your "help me assess" ask

You said real CAD *may* be obtainable and photogrammetry is *possible*. Suggested next moves:
1. **Pick 3–5 high-value look-alike parts** (where the wrong choice is costly) as the pilot scope.
2. **CAD path:** for each platform, ask the PM/PdM or prime for the **TDP / data rights status** and
   whether pubs are **S1000D/IETM with 3D**. If rights and assets exist → cheapest accurate 3D.
3. **Photogrammetry path (fallback you control):** if CAD is unavailable/restricted, capture those pilot
   parts yourselves. You own the result and avoid data-rights friction.
4. **Always verify classification/export controls** before importing or storing any 3D asset.
5. Meanwhile, **Tier 1 covers the daily need** for every figure, grounded, no sourcing required.

## 6. Bottom line
Build the grounded interactive viewer once OCR is done — it delivers the inspect-and-identify value
honestly for every schematic. Keep an optional 3D slot for real CAD or photogrammetry on the highest-
value parts. Don't generate 3D from scans. Full arc if you pursue everything: ~3 months focused, but
phased so each step ships on its own.
