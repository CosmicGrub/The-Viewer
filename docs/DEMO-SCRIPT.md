# THE VIEWER — end-to-end demo & test script

A repeatable flow to (1) PROVE the whole app is functional and congruent, then (2) give a confident, complete
end-to-end demonstration. Run everything on **Windows** (the host), where files are coherent.

## 0. Prove it works (do this first — green before you demo)

```
engine\RUN-ALL-TESTS.bat
```

This runs, in one shot:
- **test_pillars** — core search / NSN routing / parts / reference / tech-status / coverage.
- **test_features** — procedure, suggest, look-alike, ingest, RPS.
- **test_patterns** — the shared NSN/FIG/part-number extractors.
- **test_routes** — starts the **real server** against a fixture index and hits **every major route**
  (search, collections, callouts, 3D refs, schematic paths, tags, keywords, dossier, procedure, healthz, the
  static JS bundles, …), asserting **no 5xx** and valid JSON — this is the congruence check that the parts
  work together.
- **test_truncation** — the safeguard's damage-detect + recover.
- **RPS lint** — every legacy-required page is ES5-clean (legacy still works).

Expected last line: **ALL TESTS GREEN**. If anything fails, it names the file — fix or `recover` before demoing.

Then launch the app and confirm it serves:
```
engine\run_app.bat          (it starts the server AND opens http://127.0.0.1:8765 — don't open the URL by hand first)
```
A green `/healthz` (open `http://127.0.0.1:8765/healthz`) confirms python / disk / DB integrity / schema.

## 1. The demo flow (≈6 minutes, end-to-end)

1. **Search like a mechanic.** Type a slang/functional term — `juice box`, `zerk`, `the alt`. It finds the right
   part (the keyword layer maps slang → catalog nomenclature). Show the result cards: vehicle, TM, NSN, OCR badge.
2. **Tag a part in passing.** Hover a result → the small **pencil** appears → add a tag (e.g. `B-14 battery`).
   Re-search by that tag — it now finds the part. (Tagging is background; no dedicated page.)
3. **Open the page.** Click a result → the document page renders. Toggle **🔎 Loupe** (instant magnify),
   **🏷 Callouts** (clickable NSN/part/figure hotspots that jump to the dossier / Look-Alike).
4. **Schematics + Highlighter (Phase 1).** Open **📐 Schematics**, open a *vector* sheet (e.g. a Buffalo
   "Schematic - alternator gauge"), click **🖍 Highlight** → hover outlines an element, click highlights the
   **connected net/trace**. On a scanned sheet it shows the callout chips instead (honest fallback).
5. **3-D library.** Open **🧊 3D Library**, open a part → a **detailed** model (hex-headed bolt / ball bearing /
   toothed gear), and the side panel lists the **manual pages** that reference its NSN + its dossier / Look-Alike.
6. **Collections.** Open **🗂 Collections** → built-in living groups (Torque specs, Warnings…) that auto-fill
   from OCR; show the **+N new** badge, scope one to a vehicle, **🖨 print** a take-to-bay sheet.
7. **Solve → request.** From the home **📋 Parts session** (or just **Browse the repository**), run the
   symptom → procedure → tools → parts flow and generate the **104th job packet** PDF.
8. **PUB LOG depth.** Open a part **dossier** — official name, **manufacturer (CAGE)**, characteristics,
   **interchangeable NSNs**, supersession — all from PUB LOG, offline and cited.
9. **It's a repository AND a request tool.** Note the **Browse the repository** path (no parts sheet needed)
   and **Ctrl-K** command palette to reach anything.

## 2. One-time finishing touches (so the demo is its best)

- `engine\FINALIZE-OCR.bat` — rebuilds the type-ahead vocabulary from the complete scan, refreshes the parts
  index, takes a milestone backup, and prints the top part nomenclatures.
- `engine\ENRICH-PUBLOG.bat` — cross-references your NSNs against PUB LOG (manufacturer / interchangeable /
  characteristics) so the dossiers are full.
- `engine\run_safeguard.bat snapshot` — a rollback point right before the demo.

## 3. If something looks off mid-demo
- Page won't load / "refused to connect": make sure `run_app.bat` is **running** (it hosts the server).
- A schematic won't highlight: it's a scanned sheet (no vector geometry) — use the callout chips; ~45% of
  sheets are vector and fully clickable.
- Anything red in `RUN-ALL-TESTS.bat`: `run_safeguard.bat recover /all` restores the last good snapshot.

> Note on verification: the AI sandbox can't always run the full app (its file mount intermittently corrupts
> reads of the large `viewer_app.py`), so the authoritative gate is **`RUN-ALL-TESTS.bat` on Windows**. Components
> that don't depend on the server (geometry, extractors, keyword/tag logic, schematic paths) were verified
> directly; the server wiring is verified by `test_routes` host-side.
