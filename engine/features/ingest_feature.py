#!/usr/bin/env python3
"""THE VIEWER -- add-docs ingestion control (extracted verbatim from viewer_app, v0.96.0).

Preview (read-only count of new PDFs), start (background viewer_ingest crawl behind a safeguard
snapshot), and status. v0.96.0 hardening (J70): the requested path is canonicalized (realpath)
before use, and when the optional VIEWER_INGEST_ROOTS env (os.pathsep-separated) is set, only
folders under those roots may be indexed. Unset = any local folder (the original behavior, kept
for backwards compatibility). DI via `core`."""
import os
import sys
import time

core = None          # injected by viewer_app at startup
ENGINE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

_INGEST = {"proc": None, "path": "", "started": 0.0}


def _canon_ingest_path(path):
    """Canonicalize + (optionally) fence the ingest folder. Returns (ok, canonical_or_error)."""
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
    try: have = {r[0] for r in con.execute("SELECT path FROM documents")}
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
