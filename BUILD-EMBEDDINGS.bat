@echo off
REM ============================================================================================
REM  Build the semantic-search embedding index over the OCR text -> index\embeddings.npy + ids.
REM  Uses a local sentence-transformers model if installed (TRUE semantic); otherwise a keyword
REM  hashing fallback (still works, lower quality). Host-side; GPU helps.
REM
REM  For real semantic quality, first (one-time, needs internet): pip install sentence-transformers
REM
REM  Row cap: defaults to 200,000 rows (~12%% of a full corpus this size). For a full-corpus rebuild,
REM  set VIEWER_EMBED_LIMIT before running this .bat (e.g. `set VIEWER_EMBED_LIMIT=2000000`) --
REM  above the real eligible-row count so nothing gets cut off.
REM
REM  Resumable: interrupting a run (Ctrl+C, kill, power loss) mid-build leaves behind
REM  index\embeddings.progress.json + index\_embed_build\ (per-chunk shards) -- just re-run this
REM  .bat with the SAME VIEWER_EMBED_LIMIT and it picks up where it left off instead of restarting.
REM  index\embeddings.npy / embeddings_ids.tsv / embeddings.meta.json are only written once the WHOLE
REM  run finishes -- a partial/interrupted build is never picked up as "fresh" by a live server.
REM
REM  Partial fallback: if a chunk's real-model encode() call fails mid-build (bad input, transient
REM  OOM), that chunk silently gets keyword-hash vectors instead -- embeddings.meta.json is then
REM  deliberately NOT written (same "never picked up as fresh" protection as above) and
REM  index\embeddings.fallback.json names exactly which rows are suspect. Just re-run this .bat.
REM ============================================================================================
cd /d "%~dp0engine"
where py >nul 2>nul && (set "PY=py") || (set "PY=python")
set "DB=%~dp0index\viewer.db"
%PY% -c "import numpy" 2>nul || %PY% -m pip install --user --disable-pip-version-check --timeout 15 --retries 1 numpy
echo Backend check:
%PY% -c "import embed; print('  semantic backend =', embed.backend())"
if defined VIEWER_EMBED_LIMIT (echo Row cap: %VIEWER_EMBED_LIMIT% (VIEWER_EMBED_LIMIT)) else (echo Row cap: 200000 (default -- set VIEWER_EMBED_LIMIT for a full-corpus rebuild))
echo Building embedding index (this can take a while on the full corpus; GPU recommended)...
%PY% -c "import embed, os; idx=os.path.join('..','index'); n=embed.build_index(r'%DB%', idx); print('embedded', n, 'pages -> index\\embeddings.npy'); fb=os.path.join(idx,'embeddings.fallback.json'); print('WARNING -- one or more chunks fell back to hash vectors mid-build; index NOT marked fresh, see index\\embeddings.fallback.json -- just re-run this .bat to retry' if os.path.exists(fb) else 'index is fresh and ready.')"
echo Done. /semantic will now use it.
pause
