# PORTING THE VIEWER to a more powerful PC

A complete checklist for moving the whole system. Current state: **v0.98.0** (post-"THE RESTRUCTURE"),
CAD engine **CAD_VERSION 7** (colour + texture on every tier).

> **v0.96+ note:** `engine/` now contains the **`features/`** package (thin-shell architecture — see
> PROJECT-SUMMARY.md). It's inside `engine/`, so the copy list below already covers it; `make_portable.py`
> copytree picks it up automatically. Extra rollback snapshots now exist: `backups/pre-v0.96-restructure/`,
> `pre-v0.97-batch/`, `pre-v0.98-nav/` (copy `backups/` or skip for a lean move — they're regenerable safety nets).
> After moving, run **`VERIFY-V098.bat`** (core suites + integration test) for a one-shot green check.

---

## 1 · What to copy

| What | From | Notes |
|------|------|-------|
| **The project** | `C:\Users\User\Documents\Claude\Projects\THE VIEWER\` | Everything: `engine\` (all code + UI), `docs\`, the `*.bat` launchers, and `index\`. |
| **The index + sidecars** | `...\THE VIEWER\index\` | `viewer.db` (~3.65 GB — the search index + OCR text), `cadcache\` (CAD renders + spin sheets), `schemcache\`, `models3d\` (your local OBJ/STL), `mesh3d\`, figure/RPSTL/xref/correlations/reviews sidecars. Copy with the **server and OCR stopped** so the DB isn't hot. |
| **The corpus** | `E:\ALL MILITARY TMS\` | Read-only TM/PDF library. **CRITICAL: keep the same path** — see §4. |
| **publog** | `C:\Users\User\Desktop\publog\` | Only needed if you'll re-run `BUILD-XREF.bat` (PN↔NSN cross-reference rebuilds). |

Tip: the stability suite's **off-disk backup mirror** and `safeguard.py` snapshots are a clean source for the index
copy if the live one is busy.

Lean-copy option: `cadcache\`, `figcache\`, `pagecache\`, `schemcache\`, `mesh3d\` are **regenerable** — skip them
and rebuild on the (faster) new PC. **Never skip:** `viewer.db`, `collections.db`, `reviews.db` (append-only review
decisions), `correlations.db`, `rpstl.db`, `cage.json`/`pn_nsn.json`, `chapter_sides.json`, and **`models3d\`**
(your own dropped OBJ/STL files — not regenerable).

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
or the bats: `DEMO.bat` (guided tour), `VERIFY-ALL.bat` (health check after the move).

## 4 · Path gotcha (the one real trap)

`viewer.db` stores **absolute paths** to the corpus documents (`E:\ALL MILITARY TMS\...`). On the new PC either:
- mount/assign the corpus drive as **E:** again (simplest — zero changes), or
- place the corpus elsewhere and create a junction: `mklink /J "E:\ALL MILITARY TMS" "D:\wherever\ALL MILITARY TMS"`.
Re-ingesting from scratch is the slow third option.

## 5 · Hardware-aware behaviour (mostly automatic)

- **RPS** (`sysprobe.py`) re-probes on first run → a stronger PC lands on **modern** tier automatically
  (v3 CAD detail, full effects). Manual override stays in Settings.
  **Trap: delete `index\hardware_profile.json` after copying** — it's the OLD machine's cached probe; removing it
  forces a fresh probe so worker counts/tiering retune to the new hardware.
- **Parallel CAD batch** (`make_cad.py`) auto-sizes to `cpu_count − 1`, **capped at 12** for laptop RAM.
  **On a bigger CPU raise it**: `python make_cad.py --force --style v3 --workers 20` (likewise v2/v1), or edit
  `_auto_workers()` in `make_cad.py`. Measured 2.9× on the 16-core Nitro; scales with cores.
- **OCR workers** are GPU-tiered (8 default / 12 max on the RTX 4050) — re-probe will retune; bump if the new GPU
  is stronger.
- **WebGL** (Interactive 3-D, Rotate CAD, textured models) just uses the new GPU — nothing to configure.

## 6 · Finish / re-run on the new PC

1. **v7 CAD re-render** if it didn't complete before the move: `RE-RENDER-CAD.bat` (force, all tiers) or resume
   gaps with `RUN-CAD-TIERS.bat` (no force). Status anytime: `CAD-STATUS.bat`.
2. **OCR scan** if still below 100% — it resumes from the index automatically.
3. `engine\optimize_index.py` once (while OCR is paused) — perf indexes/maintenance.
4. Re-create any scheduled notifications (the auto-notify watchers live in the Claude session, not Windows).
5. Sanity pass: `VERIFY-ALL.bat`, then spot-check `/3d` (CAD tabs), `▶ Flow` on a wiring page, and a local model.

## 7 · What does NOT need attention

- The corpus is read-only and the index is append-only (R1/R6) — copying is safe, nothing is regenerated on launch.
- Caches (cadcache/schemcache/page cache) are sidecars: if any are lost they rebuild on demand — slower first
  views, no data loss.
- The legacy/RPS builds ride along automatically (tier detection re-runs per machine).

## 8 · Current in-flight state (hand-off)

- v7 colour+texture re-render: **launched** on the old PC (32,622 parts × 3 tiers, 12 workers). If interrupted by
  the move, resume per §6.1 — already-rendered v7 files are kept.
- Shader-textured 3-D verified live (`engine\ui\cadtex_test.html` — open it on the new PC for a 10-second WebGL
  sanity check; the tab title reports SHADER OK/FAIL).
