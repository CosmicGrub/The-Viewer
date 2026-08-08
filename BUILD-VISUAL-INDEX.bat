@echo off
REM Build the visual-search perceptual-hash index over the figure crops (index\figcache) -> index\phash.tsv.
REM Host-side; needs numpy + Pillow (already used by the app). Resumable/idempotent. Then /visual matches photos.
cd /d "%~dp0engine"
where py >nul 2>nul && (set "PY=py") || (set "PY=python")
%PY% -c "import numpy,PIL" 2>nul || %PY% -m pip install --user --disable-pip-version-check --timeout 15 --retries 1 numpy pillow
%PY% -c "import phash,os; d=os.path.join('..','index','figcache'); out=os.path.join('..','index','phash.tsv'); print('hashing', d); n=phash.build_index(d,out) if os.path.isdir(d) else 0; print('wrote', n, 'hashes ->', out)"
pause
