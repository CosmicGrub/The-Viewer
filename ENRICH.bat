@echo off
REM ============================================================================================
REM  EXTERNAL GAP-FILL ENRICHMENT  --  OPT-IN, ONLINE, HOST-RUN.
REM
REM  Cross-references the OPEN INTERNET to FILL BLANKS in the corpus's measurement/dimension data,
REM  and PUSHES EVERY LINK IT FINDS THROUGH THE WAYBACK MACHINE so the data is pinned to a permanent
REM  archived snapshot. Link sources per subject:
REM     (A) Internet Archive full-text items       (B) web-search results (optional plugin, see below)
REM     (C) your own seed URLs: index\enrich_seeds.txt   ('subject | url' to scope, or bare url = global)
REM  Every (B)/(C) link is routed through Wayback (availability, or Save Page Now with --save).
REM
REM  The corpus stays AUTHORITATIVE; external values only complete MISSING dimension types and are
REM  badged 'external-unconfirmed' with full provenance (archived URL + snapshot timestamp + original
REM  URL + fetched time). Writes only the append-only sidecar index\enrich.db -- corpus never touched
REM  (R1/R6). Resumable. The running app stays 100%% offline; only THIS touches the network.
REM
REM  Flags (all optional):  --subject "HMMWV"   --limit 80   --maxlinks 12   --save   --sleep 2
REM    --save      also SAVE PAGE NOW any link the Wayback Machine hasn't archived yet
REM    --maxlinks  cap on links routed through Wayback per subject
REM  OPTIONAL web-search: drop an engine\enrich_search.py with  search(query, limit) -> [url,...]
REM    (see engine\enrich_search.py.sample). Without it, sources (A)+(C) still run.
REM  TIP: run BUILD-MEASURES.bat first so gaps are computed from the full corpus.
REM ============================================================================================
cd /d "%~dp0engine"
where py >nul 2>nul && (set "PY=py") || (set "PY=python")
echo Checking internet reachability to archive.org...
%PY% -c "import urllib.request as u; u.urlopen('https://archive.org/wayback/available?url=example.com',timeout=15); print('  online OK')" 2>nul || (echo   NOT ONLINE -- connect to the internet and re-run. & pause & exit /b 1)
echo.
echo Crawling + routing every link through the Wayback Machine to fill dimensional-data gaps...
%PY% -B build_enrich.py %*
echo.
echo Done. External fills live in index\enrich.db and appear badged on /measures (archived Wayback links).
pause
