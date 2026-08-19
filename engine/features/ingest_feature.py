#!/usr/bin/env python3
"""THE VIEWER -- add-docs ingestion control (extracted verbatim from viewer_app, v0.96.0).

Preview (read-only count of new PDFs), start (background viewer_ingest crawl behind a safeguard
snapshot), and status. v0.96.0 hardening (J70): the requested path is canonicalized (realpath)
before use, and when the optional VIEWER_INGEST_ROOTS env (os.pathsep-separated) is set, only
folders under those roots may be indexed. Unset = any local folder (the original behavior, kept
for backwards compatibility). DI via `core`."""
import os
import sys
import threading
import time

core = None          # injected by viewer_app at startup
ENGINE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

_INGEST = {"proc": None, "path": "", "started": 0.0}
# Guards the ingest_start() check-then-act: without this, two concurrent POST /api/ingest
# requests can both read _INGEST["proc"] as not-running before either has recorded the new
# subprocess, so both pass the "already in progress" guard and both Popen() a crawl against
# the same DB (live-reproduced: two 'crawl' rows in `runs` starting/finishing in the same
# second). The whole read-check-write section below is serialized under this lock.
_INGEST_LOCK = threading.Lock()


def canon_ingest_path(path):
    """Canonicalize + (optionally) fence a folder against VIEWER_INGEST_ROOTS. Returns
    (ok, canonical_or_error). Public (no leading underscore) specifically so every route that
    reads an arbitrary folder off the host filesystem can share this one fence -- r_airgap_manifest
    and r_ingest_scan in features/routes.py used to call ingestpipe.scan_folder() on the raw,
    unvalidated path directly, silently bypassing VIEWER_INGEST_ROOTS even when an operator had
    configured it specifically to restrict which folders may be indexed/scanned."""
    path = (path or "").strip()
    if not path:
        return False, "Not a folder on this machine: (empty)"
    real = os.path.realpath(path)
    if not os.path.isdir(real):
        return False, "Not a folder on this machine: " + path
    roots = [r.strip() for r in (os.environ.get("VIEWER_INGEST_ROOTS") or "").split(os.pathsep) if r.strip()]
    if roots:
        rl = os.path.normcase(real)
        if not any(rl.startswith(os.path.normcase(os.path.realpath(r)).rstrip("\\/") + os.sep) or
                   rl == os.path.normcase(os.path.realpath(r)).rstrip("\\/") for r in roots):
            return False, "Folder is outside the configured ingest roots (VIEWER_INGEST_ROOTS)."
    return True, real


# Back-compat alias -- keep the original private name working for anything else that imported it.
_canon_ingest_path = canon_ingest_path


def ingest_preview(path):
    """Read-only: scan a folder on THIS machine for PDFs and report how many are new vs already indexed.
    No writes — just a safe look before the user commits to indexing."""
    ok, real = _canon_ingest_path(path)
    if not ok:
        return {"ok": False, "error": real}
    path = real
    pdfs = []
    for dp, dn, fn in os.walk(path, followlinks=True):
        if os.sep + "." in dp: continue
        for f in fn:
            if f.lower().endswith(".pdf"): pdfs.append(os.path.join(dp, f))
        if len(pdfs) > 8000: break
    con = core.db()
    # realpath() both sides before comparing -- `pdfs` above is built from `path`, already realpath'd
    # by _canon_ingest_path(), but a documents.path row can have been recorded via a DIFFERENT (but
    # equivalent) representation of the same on-disk location: a junction/symlink, or -- confirmed
    # live on a GitHub Actions Windows runner -- an 8.3 short-name alias in %TEMP% (RUNNER~1 vs the
    # long form). A plain string comparison then miscounts an already-indexed file as new. realpath()
    # is idempotent and cheap relative to the os.walk() above; a missing/renamed file just returns its
    # own (still-comparable) normalized form rather than raising.
    try: have = {os.path.realpath(r[0]) for r in con.execute("SELECT path FROM documents")}
    except Exception: have = set()
    con.close()
    new = [p for p in pdfs if p not in have]
    return {"ok": True, "path": path, "total_pdfs": len(pdfs), "already_indexed": len(pdfs) - len(new),
            "new_pdfs": len(new), "sample": [os.path.basename(p) for p in new[:12]]}


def ingest_start(path):
    """Kick off indexing a folder of PDFs (additive crawl) in the background, after a safeguard snapshot.
    Reuses the tested viewer_ingest.py 'crawl' CLI; progress is read back from the runs table (R1)."""
    global _INGEST
    ok, real = _canon_ingest_path(path)
    if not ok: return {"ok": False, "error": real}
    path = real
    # Hold the lock across the "already running?" check AND the write that records the new
    # subprocess, so two concurrent callers can't both observe no run in progress and both
    # Popen() a crawl (see _INGEST_LOCK comment above).
    with _INGEST_LOCK:
        if _INGEST.get("proc") and _INGEST["proc"].poll() is None:
            return {"ok": False, "error": "An indexing run is already in progress."}
        try:
            import safeguard as _sg; _sg.snapshot("pre-ingest")     # R1: snapshot before any write
        except Exception: pass
        import subprocess
        py = sys.executable or "python"
        cmd = [py, os.path.join(ENGINE_DIR, "viewer_ingest.py"), "crawl", "--root", path, "--db", core.DB_PATH]
        try:
            p = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            _INGEST = {"proc": p, "path": path, "started": time.time()}
            return {"ok": True, "started": True, "path": path}
        except Exception as e:
            return {"ok": False, "error": str(e)}


def ingest_status():
    con = core.db(); run = None
    try:
        r = con.execute("SELECT started_at, finished_at, files_seen, new_docs, pages_indexed, ocr_queued "
                        "FROM runs WHERE kind='crawl' ORDER BY id DESC LIMIT 1").fetchone()
        if r: run = dict(r)
    except Exception: pass
    con.close()
    proc = _INGEST.get("proc"); running = bool(proc and proc.poll() is None)
    return {"running": running, "path": _INGEST.get("path", ""),
            "elapsed": round(time.time() - _INGEST["started"]) if _INGEST.get("started") else 0, "run": run}
