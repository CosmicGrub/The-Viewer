@echo off
REM ============================================================================================
REM  Build the semantic-search embedding index over the OCR text -> index\embeddings.npy + ids.
REM  Uses a local sentence-transformers model if installed (TRUE semantic); otherwise a keyword
REM  hashing fallback (still works, lower quality). Host-side; GPU helps. Resumable (re-run to refresh).
REM
REM  For real semantic quality, first (one-time, needs internet): pip install sentence-transformers
REM ============================================================================================
cd /d "%~dp0engine"
where py >nul 2>nul && (set "PY=py") || (set "PY=python")
set "DB=%~dp0index\viewer.db"
%PY% -c "import numpy" 2>nul || %PY% -m pip install --user --disable-pip-version-check --timeout 15 --retries 1 numpy
echo Backend check:
%PY% -c "import embed; print('  semantic backend =', embed.backend())"
echo Building embedding index (this can take a while on the full corpus; GPU recommended)...
%PY% -c "import embed,os; n=embed.build_index(r'%DB%', os.path.join('..','index')); print('embedded', n, 'pages -> index\\embeddings.npy')"
echo Done. /semantic will now use it.
pause
