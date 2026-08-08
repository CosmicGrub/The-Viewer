# Finishing OCR on your GPU box — run guide & checklist

~119,000 scanned pages (about 6.5% of the index) still need OCR to become searchable. This is the one
step that has to run on **your** machine (it's GPU/CPU compute time, not something the assistant can do
remotely). It's fully resumable — start, stop, and re-run as often as you like.

## Preflight checklist

- [ ] **Python 3** on PATH (`py --version` or `python --version`).
- [ ] **NVIDIA GPU + recent driver** for the fast path (optional — it falls back to CPU automatically).
- [ ] The index exists at `index\viewer.db`.
- [ ] You can leave the machine running for a while (see time estimate below).
- [ ] (Recommended) Take a snapshot first — the launcher now does this for you (`pre-ocr`).

## Run it

1. Double-click **`engine\run_ocr_gpu.bat`** (or run it from a terminal).
   It will, in order:
   - install/verify PyMuPDF + RapidOCR + `onnxruntime-gpu`,
   - take a **safeguard snapshot** (`pre-ocr` restore point),
   - **cleanup** (requeue any half-finished pages),
   - run **`ocrall`** — prioritize (parts catalogs first) → OCR in batches → **loop until 0 pending** →
     refresh the parts index.
2. Leave it running. You can stop with Ctrl+C and re-run anytime; it continues where it left off.

> CPU-only is fine, just slower. If the GPU runtime isn't ready the script prints a notice and uses CPU.

## Watch progress

- Open **`http://127.0.0.1:8765/status`** (start the app with `engine\run_app.bat`). The **OCR progress**
  bar and the pending/done counts update live.
- Or, from a terminal: `python engine\viewer_ingest.py status --db index\viewer.db`.

## Time estimate (rough)

| Path | Throughput (typical) | ~119k pages |
|------|----------------------|-------------|
| GPU (RapidOCR + CUDA) | ~5–15 pages/sec | a few hours to ~half a day |
| CPU (multi-core) | ~0.5–2 pages/sec | 1–3 days |

Numbers vary widely by GPU, page complexity, and DPI. Lower `--dpi` is faster; the launcher uses 200.

## If something looks off

- **It says "CPU fallback"** → the GPU runtime isn't active. See `docs\SETUP-GPU.md`; CPU still works.
- **A few pages land in `failed`** → they're logged in `jobs`; re-running `cleanup` requeues them.
- **It seems stuck on huge files** → it's still working; check the status page — `done` keeps climbing.
- **You want to skip blank pages first** → `python engine\viewer_ingest.py prefilter --db index\viewer.db`
  marks blank pending pages as `skipped` to shrink the queue (optional; rendering each page takes time).

## When it finishes

- The status page shows **OCR progress 100%** and coverage near 100%.
- Newly-OCR'd pages are searchable immediately, and two features that are OCR-gated light up on those
  pages: **mirror-mode readable labels** and (future) **callout→part hotspots**.
- Take a fresh snapshot afterward: `engine\run_safeguard.bat snapshot` (or let the daily task do it).

Nothing about this run is destructive: OCR only **adds** text to previously-blank pages (R6), so it is
not part of any rollback, and the rest of your data is untouched.
