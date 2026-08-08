# Rollback — undo the overnight enrichment (R1, backwards-compatible)

Everything done in this batch is **additive and reversible**. If you want to undo it, you have a one-click
rollback. Nothing about your manuals, pages, or OCR'd text is removed by rollback.

## What was done (and can be rolled back)
- **Structured parts index** built on the full index: **227,908** records / **45,068 distinct part NSNs**
  (in the `parts` table, `confidence='page'`).
- **FLIS enrichment** of **41,701 NSNs** from the DLA FLIS Reading Room catalog — item names, part #/CAGE,
  characteristics (dimensions), AAC, unit price, **FLIS vintage date**, **supersession cross-references**,
  and **multiple part-number choices** (in `ref_nsn` + append-only `ref_nsn_log`). Plus the public-domain
  hardware reference (`ref_hardware`).

## What rollback removes vs. keeps
| Removes (the enrichment) | Keeps (untouched) |
|--------------------------|-------------------|
| `ref_nsn`, `ref_nsn_log`, `ref_hardware` tables | All 39,683 documents |
| extracted `parts` rows (`confidence` set) | All 1,848,465 pages + their text/OCR |
| | Additive columns/migrations (harmless, backwards-compatible) |

After rollback, search and the 104th sheet behave exactly as they did **before** the enrichment.

## How to roll back
- **Dry run (default — shows what would change, changes nothing):**
  double-click `engine\run_rollback.bat`, or run
  `python engine\viewer_ingest.py rollback --db index\viewer.db`
- **Actually roll back:** `engine\run_rollback.bat /yes`, or add `--yes` to the command.

## How to restore after a rollback
Re-run the enrichment: `python engine\viewer_ingest.py parts` then
`python engine\viewer_ingest.py enrich --publog-dir "C:\path\to\publog"` (auto-detects the FLIS files).

## Note on OCR
OCR only **adds** text to previously-blank scanned pages (it never removes content — R6), so it is not
part of this rollback. The OCR pass to 100% is a separate, GPU-bound job (`engine\run_ocr_gpu.bat`).
