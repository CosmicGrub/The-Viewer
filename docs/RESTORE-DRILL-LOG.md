# Restore Drill Log — THE VIEWER

Real, dated records of backup **restore** drills — actually starting `viewer_app.py` against a
restored copy of a backup file and hitting live endpoints with real queries, not just verifying the
backup file's own internal consistency. `safeguard.py backupdb()`'s `PRAGMA quick_check` (run at
backup time, see `docs/MASTER-RECONCILIATION.md` item 4 and `docs/CHANGELOG.md` `[1.25.0]`) proves
the backup file's B-tree/page structure is internally consistent to SQLite. It never opens a
connection against application tables, runs a real query, or feeds a result through the app layer —
a backup could be schema-stale, or the app's queries could no longer match the backup's schema, and
`quick_check` would never know. Restore drills close that specific gap. Newest at top.

---

## Drill 1 — 2026-08-31

**Performed from:** worktree `wf_b043bea2-455-4` (`docs/restore-drill-log` branch), against the real
files on disk at `C:\Users\User\Documents\Claude\Projects\THE VIEWER\`.

### 1. Pre-flight

- Live free disk space (`.NET System.IO.DriveInfo`, not assumed from any prior observation):
  - `C:` — **8.69 GB free** of 476.16 GB total.
  - `E:` — **6.3 GB free** of 232.88 GB total (an earlier planning pass had estimated ~63 GB free on
    `E:`; the live figure is an order of magnitude lower — flagged here as a real discrepancy, not
    silently corrected away).
  - Backup to restore: `backups\db\viewer-20260830-1348.db`, 3,639,091,200 bytes (~3.64 GB,
    LastWriteTimeUtc `2026-08-30T18:50:12Z`). Copying it to `C:` leaves ~5 GB free — thin, but
    sufficient with margin; `E:`'s 6.3 GB free would leave only ~2.7 GB, tighter. **Chose `C:`**
    (specifically `%LOCALAPPDATA%\Temp\viewer_restore_drill\`, outside the repo) for the larger
    post-copy safety margin.
- Running processes checked (`Get-CimInstance Win32_Process`): two Python processes were live —
  `embed_rebuild_v2.py` (both `python.exe` PID 26228 and `python3.13.exe` PID 3016) — an embeddings
  rebuild, confirmed by command line. **Not touched, not disturbed** — the drill's own instance used
  a separate DB copy, a separate port, and never queried anything the rebuild was writing to.
- Port check (`netstat -ano`): nothing listening on `8765` (the app's default) or `18765` (the port
  chosen for this drill). No collision.

### 2. Copy (never move) to isolated scratch

- Source: `backups\db\viewer-20260830-1348.db` (the newer of the two backups on disk; the older,
  `viewer-20260830-1332.db`, was left untouched throughout).
- Destination: `C:\Users\User\AppData\Local\Temp\viewer_restore_drill\viewer-drill.db` (outside the
  repo, as required).
- `Copy-Item`, 3,639,091,200 bytes, completed in 5.1 s.
- **Integrity verified by SHA-256, not just size**: source and destination hashes matched exactly —
  `3EAF0EDC3D09A5D76B1E2D81104423E5099BE2F77B06FF3F71897DC679DD6BA3`.

### 3. Started a real drill instance

```
python engine\viewer_app.py --db "C:\Users\User\AppData\Local\Temp\viewer_restore_drill\viewer-drill.db" --port 18765 --host 127.0.0.1
```

Confirmed listening on `127.0.0.1:18765` (`netstat`) within a few seconds. This process only ever
touched the isolated copy — `DB_PATH`/`INDEX_DIR` are fully overridden per-process by `--db`
(`engine/viewer_app.py` `main()`, `args.db` → `DB_PATH = os.path.abspath(args.db)`), no shared state
with `index/viewer.db` or with the running embeddings-rebuild process.

### 4. Real endpoints, real queries, real responses

**`GET /healthz`** — `200`:
```json
{"ok":true,"version":"1.42.0","started_with_version":"1.42.0","started_at":"2026-08-31T22:43:12",
 "code_changed_since_start":false,
 "checks":[
   {"name":"python","status":"OK","detail":"3.13"},
   {"name":"disk","status":"OK","detail":"5416 MB free (need >= 1024)"},
   {"name":"index","status":"OK","detail":"opened ok: 23 tables, 888450 pages x 4096 B; full scan skipped on large DB (3470 MB) -- run --deep to force"},
   {"name":"schema","status":"WARN","detail":"schema_version=8 < migrations=12 -> run fix_schema_version.py"},
   {"name":"gpu","status":"INFO","detail":"no CUDA provider (CPU / lite / legacy is fine)"}
 ]}
```
The app opened the restored file cleanly and reported its true size (3470 MiB — matches the drill
copy, confirming `--db` really was honored, not silently defaulting back to `index/viewer.db`). It
also immediately surfaced the finding below on its own, unprompted.

**`GET /api/part_record?nsn=2815-01-644-2377`** (a real NSN sampled live from the restored copy's own
`parts` table) — `200`, real data:
```json
{"found":true,"query":"2815-01-644-2377","part_no":"1B30-2-274B","cagec":"1FE91","nsn":"2815-01-644-2377",
 "nomenclature":"ENGINE,DIESEL","confidence":0.6,
 "links":{"dossier":"/dossier?q=2815-01-644-2377","procedure":"/procedure?q=ENGINE,DIESEL","lookalike":"/partdiff?q=2815-01-644-2377"},
 "provenance":{"nomenclature":"flis","cagec":"flis","part_no":"flis"}}
```
Correct, complete part record served from the restored file.

**`GET /api/part_by_number?pn=1B30-2-274B&cagec=1FE91`** — `200`, `{"found":false,"query":"1B30-2-274B"}`.
Verified directly against the restored copy (`SELECT COUNT(*) FROM parts WHERE part_number IS NOT
NULL`) that `parts.part_number` is **0 rows populated in this corpus** — this is an honest, accurate
"not found" reflecting real (empty) data, not an app or restore defect.

**`GET /api/search?q=...`** (tried five real terms sampled from the restored copy's own indexed text:
`ENGINE ASSEMBLY`, `ENGINE`, `brake`, `gasket`, `TAMPER`) — every one returned `200` with
**`"results":[]`**, e.g.:
```json
{"results":[],"side":null,"did_you_mean":["engines","engin"]}
```

**`GET /api/pmcs?vehicle=5 TON&limit=5`** and `?vehicle=HMMWV&limit=5` — both `200`,
**`{"vehicle":"...","count":0,"results":[]}`**.

### 5. Root-caused the zero-result finding (this is what the drill exists to catch)

Confirming these weren't corpus-content misses, the exact same FTS query run directly against the
restored copy (`sqlite3`, no app layer) returned real, correct hits immediately — e.g. `MATCH
'engine'` returned 5+ rows including body-text snippets on the first try. The discrepancy is in the
app layer: `engine/features/search_feature.py`'s `_meta_rows()` and its LIKE-fallback both `SELECT
... p.ocr_confidence`, and `engine/features/corpus.py`'s `fts_pages()` (used by `pmcs.find()`) does
the same. **`PRAGMA table_info(pages)` on the restored copy shows no `ocr_confidence` column** — it
was added by a later migration than this backup was taken under. `healthz`'s own `schema` check had
already flagged this: `schema_version=8 < migrations=12`. The result: `_meta_rows()` throws
`OperationalError`, falls to the LIKE fallback, which selects the same missing column and throws
again, caught, and returns `[]` — silently, with a `200` and no error surfaced anywhere in the
response. `pmcs.find()`'s `except Exception` wrapper around `corpus.fts_pages()` behaves the same way
(no `error` key appears in its `200` response either).

**This is exactly the "wrote a file vs. proven safety net" gap this drill exists to close.** If this
backup (`viewer-20260830-1348.db`) were restored today onto a host still running current app code,
`/api/search` and `/api/pmcs` — two of the app's most heavily used endpoints — would come back up,
answer every request with `200 OK`, and silently return zero results for every query, with nothing in
the UI or `/healthz`'s `ok:true` top-level field distinguishing that from "the corpus doesn't have
this." (`/healthz`'s `schema` check does say `WARN`, but nothing gates traffic on it, and nothing
prior to this drill had ever actually exercised the failure it warns about end-to-end.) `part_record`/
`part_by_number` are unaffected because they never touch `pages.ocr_confidence`. **No code was
changed to work around this during the drill** — it is reported here for a human to decide whether to
add a schema-version gate to backup/restore, run `fix_schema_version.py` against future backups
before they're trusted, or something else.

### 6. Clean shutdown, confirmed untouched

- `taskkill /PID <drill pid>` (non-forceful) did not stop the process within 2 s (expected — Windows
  has no SIGINT-equivalent for a console-less Python HTTP server via non-forceful `taskkill`);
  `taskkill /PID <drill pid> /F` then stopped it. Port `18765` confirmed released
  immediately after (only `TIME_WAIT` client sockets from the drill's own `curl` calls remained,
  no listener).
- Deleted **only** `C:\Users\User\AppData\Local\Temp\viewer_restore_drill\` (the copy, its `-wal`/
  `-shm` sidecars the app created, and its own `analytics.jsonl`) — confirmed the directory no longer
  exists afterward.
- **Originals confirmed byte-for-byte untouched**, before vs. after the drill:

  | file | size (bytes) | LastWriteTimeUtc | unchanged? |
  |---|---|---|---|
  | `backups\db\viewer-20260830-1332.db` | 3,639,091,200 | `2026-08-30T18:35:59.698Z` | yes |
  | `backups\db\viewer-20260830-1348.db` | 3,639,091,200 | `2026-08-30T18:50:12.687Z` | yes (**SHA-256 re-verified equal to the pre-drill hash above**) |
  | `index\viewer.db` | 3,669,012,480 | `2026-08-30T18:52:27.012Z` | yes |

  `index/viewer.db` was never opened by the drill process at all — `--db` pointed exclusively at the
  isolated copy for the drill's entire lifetime.

### Summary

The restore mechanics themselves work: a real backup file, copied (not moved) to an isolated
location, starts a real, isolated `viewer_app.py` instance that opens it correctly, and two of four
endpoint families (`/healthz`, `/api/part_record`) serve correct real data from it. Two endpoint
families (`/api/search`, `/api/pmcs`) silently return empty results against this specific backup due
to a genuine schema-version gap between when it was taken (`schema_version=8`) and what current app
code expects (migrations through `12`) — a real finding this drill was designed to surface, previously
invisible behind `backupdb()`'s `PRAGMA quick_check`-only verification. The original backup file and
the live index were left completely unmodified throughout.
