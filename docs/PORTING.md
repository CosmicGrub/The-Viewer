# PORTING THE VIEWER to a more powerful PC

A complete checklist for moving the whole system. Current state: **v1.13.2** (2026-07-18; rewritten 2026-08-08 —
see reconciliation note below), post-"THE RESTRUCTURE" + the v1.13.0 "HOLISTIC HARDENING" pass, CAD engine
**CAD_VERSION 7** (colour + texture on every tier).

> **Reconciliation note (2026-08-08):** this file had gone stale at "v0.98.0" — the same class of drift
> `docs/PROJECT-SUMMARY.md` had, fixed in the same session (see that file's own reconciliation note). Rewritten
> below against `docs/MASTER-RECONCILIATION.md` + `docs/CHANGELOG.md`. The copy mechanics (§1–§4) were already
> accurate; what was stale was the version header, the verify command, and the "current in-flight" snapshot at the
> bottom (§8), which described a CAD re-render that has long since finished shipping (CAD_VERSION 7 has been
> stable since the 0.86→0.93.3 wave).

> **v0.96+ note:** `engine/` contains the **`features/`** package (thin-shell architecture — see
> PROJECT-SUMMARY.md §2). It's inside `engine/`, so "copy the project" already covers it; `make_portable.py`
> copytree picks it up automatically. Rollback snapshots exist under `backups/`: `pre-v0.96-restructure/`,
> `pre-v0.97-batch/`, `pre-v0.98-nav/`, and **`pre-v1.13/`** (current rollback point). After moving, run root
> **`VERIFY.bat`** — the single authoritative gate since v1.13.0 (`VERIFY-099.bat` forwards to it; the older,
> pre-1.13 `VERIFY-V098.bat` was removed -- low finding #50 -- since it was superseded, unreferenced by any
> other launcher, and had no exit-code truth at all: each test ran `... && echo [X PASS]` on its own
> independent line (so one failing test did NOT block later tests, unlike the true `&&`-chaining bug
> VERIFY.bat's header warns about), but the script never checked `errorlevel` or propagated a failure exit
> code -- it always printed "Done." and relied on a human eyeballing the log for missing `[X PASS]` markers,
> the exact "eyeball the log" anti-pattern VERIFY.bat's rewrite was built to replace).

---

## 1 · What to copy

| What | From | Notes |
|------|------|-------|
| **The project** | `C:\Users\User\Documents\Claude\Projects\THE VIEWER\` | Everything: `engine\` (all code + UI), `docs\`, the `*.bat` launchers, and `index\`. |
| **The index + sidecars** | `...\THE VIEWER\index\` | `viewer.db` (~3.65 GB — the search index + OCR text), plus per-feature sidecars: `masterfile.db`, `conflicts.db` (if built), `rpstl.db` (~950 MB), `measures.db` (~465 MB), `kg.db`, `correlations.db`, `collections.db`, `reviews.db`, `tables.db`, `embeddings.npy`/`embeddings_ids.tsv` (~300 MB, semantic search), `viewer_settings.json` (the persisted RPS run-mode choice, v1.13.2 — see §5's new trap), `cadcache\`, `figcache\`, `schemcache\`, `models3d\` (your local + AI-illustrative OBJ/STL), `mesh3d\`. Copy with the **server and OCR stopped** so the DBs aren't hot. |
| **The PUBLOG/FLIS catalog** | `...\THE VIEWER\engine\index\publog.db` | **A separate ~9 GB file, NOT under `index\`** — easy to miss if you're lean-copying by hand instead of copying `engine\` wholesale. Powers `/publog`, `/binaudit`, and every `publogdiff.py` interchangeability/supersession feature (added v1.5.0). Regenerable via `BUILD-PUBLOG.bat` but that's a multi-GB re-stream — copying the built `.db` is far faster. |
| **The corpus** | `E:\ALL MILITARY TMS\` | Read-only TM/PDF library. **CRITICAL: keep the same path** — see §4. |
| **publog source export** | `C:\Users\User\Desktop\publog\` | The raw ~16 GB DLA export. Only needed if you'll re-run `BUILD-PUBLOG.bat` from scratch (rebuilding `engine/index/publog.db`) or `BUILD-XREF.bat`. |

Tip: the stability suite's **off-disk backup mirror** and `safeguard.py` snapshots are a clean source for the index
copy if the live one is busy.

Lean-copy option: `cadcache\`, `figcache\`, `pagecache\`, `schemcache\`, `mesh3d\`, and `embeddings.npy`/
`embeddings_ids.tsv` are **regenerable** (via `BUILD-VECTORIZE.bat`/`BUILD-EMBEDDINGS.bat` for the latter) — skip
them and rebuild on the (faster) new PC. `masterfile.db` and `conflicts.db` are similarly regenerable
(`BUILD-MASTERFILE.bat`, `BUILD-CONFLICTS.bat`) and may not even exist yet on your source machine — that's fine,
they're optional. **Never skip:** `viewer.db`, `engine/index/publog.db`, `collections.db`, `reviews.db`
(append-only review decisions), `correlations.db`, `rpstl.db`, `cage.json`/`pn_nsn.json`, `chapter_sides.json`, and
**`models3d\`** (your own dropped OBJ/STL files — not regenerable; the `ai\` illustrative-tier subfolder is
regenerable if you kept the source Meshy exports elsewhere, but treat it as precious if you didn't).

## 2 · Install on the new PC

- **Python 3.11+** → core: `pip install pillow numpy pymupdf`
  (Pillow = CAD renderer · numpy = textures · PyMuPDF/fitz = page rendering + vector extraction)
- **OCR stack (for the scan / rebuilds):** `pip install rapidocr-onnxruntime onnxruntime` — and use the **GPU
  build** of onnxruntime on the new machine (`onnxruntime-gpu` for NVIDIA/CUDA, or `onnxruntime-directml`).
  CPU fallback: `pip install pytesseract` + the Tesseract binary.
- **Exports:** `pip install openpyxl reportlab` (spreadsheet + PDF outputs, e.g. the parts-request packet).
- **Optional dev tools:** Node.js (only used by the verify bats for `node --check`).
- A modern browser (WebGL) for the 3-D / Rotate CAD / Living Schematic views.

## 3 · Launch

```
cd "THE VIEWER\engine"
python viewer_app.py          # http://127.0.0.1:8765  (or --port N)
```
or the bats: `DEMO.bat` (guided tour), root `VERIFY.bat` (the authoritative health check after the move — see §6.3).

## 4 · Path gotcha (the one real trap)

`viewer.db` stores **absolute paths** to the corpus documents (`E:\ALL MILITARY TMS\...`). On the new PC either:
- mount/assign the corpus drive as **E:** again (simplest — zero changes), or
- place the corpus elsewhere and create a junction: `mklink /J "E:\ALL MILITARY TMS" "D:\wherever\ALL MILITARY TMS"`.
Re-ingesting from scratch is the slow third option.

## 5 · Hardware-aware behaviour (mostly automatic)

- **RPS** (`sysprobe.py`) re-probes on first run → a stronger PC lands on **modern** tier automatically
  (v3 CAD detail, full effects).
  **Trap: delete `index\hardware_profile.json` after copying** — it's the OLD machine's cached probe; removing it
  forces a fresh probe so worker counts/tiering retune to the new hardware.
  **New trap (v1.13.2): the run-mode choice is now a persisted Setting, not just an env flag.** If you copied
  `index\viewer_settings.json` from the old machine and it had **Performance** or **Retroactive Post-Support**
  manually forced (rather than **Auto**), that forced choice follows you to the new PC and will NOT re-adapt on its
  own — it overrides the fresh hardware probe (precedence: `VIEWER_MODE` env > `VIEWER_RUN_MODE` env > saved
  setting > `auto`). Check the **Run mode** card on `/status` after the move and switch back to Auto if you want
  the new hardware's tier picked automatically. If you didn't copy `viewer_settings.json`, the app starts on
  Auto by default (fail-open read) and this doesn't apply.
- **Parallel CAD batch** (`make_cad.py`) auto-sizes to `cpu_count − 1`, **capped at 12** for laptop RAM.
  **On a bigger CPU raise it**: `python make_cad.py --force --style v3 --workers 20` (likewise v2/v1), or edit
  `_auto_workers()` in `make_cad.py`. Measured 2.9× on the 16-core Nitro; scales with cores.
- **OCR workers** are GPU-tiered (8 default / 12 max on the RTX 4050) — re-probe will retune; bump if the new GPU
  is stronger.
- **WebGL** (Interactive 3-D, Rotate CAD, textured models) just uses the new GPU — nothing to configure.

## 6 · Finish / re-run on the new PC

1. **CAD renders**: v7 is the stable baseline (~32,622-part cache) — nothing to re-render unless you skipped
   `cadcache\` in a lean copy, in which case it rebuilds on demand (slower first views) or via `RE-RENDER-CAD.bat`
   (force, all tiers) / `RUN-CAD-TIERS.bat` (fill gaps only). Status anytime: `CAD-STATUS.bat`.
2. **OCR scan** if still below 100% — it resumes from the index automatically; check current % via `/command` or
   the OCR watchdog before assuming it's finished.
3. **Root `VERIFY.bat`** — the authoritative gate (exit-code truth, wall-clock guarded, unions every suite +
   `rps_lint`/`verify_ui`/`check_crlf` + module self-tests). Run this, not the older `VERIFY-ALL.bat`, for
   the current one-shot green check. (`VERIFY-V098.bat` was removed -- see the note above.)
4. Optional, if you skipped them in the lean copy and want them fresh: `BUILD-MASTERFILE.bat`,
   `BUILD-CONFLICTS.bat` (both append-only, safe to run anytime OCR is paused).
5. `engine\optimize_index.py` once (while OCR is paused) — perf indexes/maintenance.
6. Re-create any scheduled notifications (the auto-notify watchers live in the Claude session, not Windows).
7. Sanity pass: spot-check `/status` (Run mode card — see §5's new trap), `/3d` (CAD tabs), `▶ Flow` on a wiring
   page, `/publog` (confirms `engine/index/publog.db` came across), and a local model.

## 7 · What does NOT need attention

- The corpus is read-only and the index is append-only (R1/R6) — copying is safe, nothing is regenerated on launch.
- Caches (cadcache/schemcache/page cache) are sidecars: if any are lost they rebuild on demand — slower first
  views, no data loss.
- The legacy/RPS builds ride along automatically (tier detection re-runs per machine).

## 8 · Current in-flight state (hand-off)

CAD v7 colour+texture rendering is long finished and stable (not "in progress" — see the reconciliation note at
the top of this file). For what's actually still outstanding as of today, see `docs/HANDOFF-NOTE.md` and
`docs/MASTER-RECONCILIATION.md` §6 — as of the last reconciliation (2026-08-08, state v1.13.2) that's: R10 literal
screenshots never captured (`docs/screenshots/` holds only a route README), root `VERIFY.bat` not yet confirmed
green on an actual host for the v1.13.0–1.13.2 work, the pre-OCR `safeguard.py` snapshot needs re-baselining, and
`BUILD-CONFLICTS.bat`'s first sweep is still optional/pending. None of these block a port — they're regular
project TODOs, not move-blockers.

Shader-textured 3-D can be spot-checked with `engine\ui\cadtex_test.html` on the new PC — a 10-second WebGL sanity
check; the tab title reports SHADER OK/FAIL.
