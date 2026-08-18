#!/usr/bin/env python3
"""THE VIEWER -- ingestion + OCR indexing pipeline (offline, resumable, backwards-compatible).

PDF text: PyMuPDF (pip 'pymupdf'); falls back to Poppler pdftotext.
OCR for scanned pages: RapidOCR (pip 'rapidocr-onnxruntime', no admin, bundles models);
falls back to Tesseract if RapidOCR is unavailable. Page rasterized via PyMuPDF (or pdftoppm).
OCR parallelism uses THREADS (shared engine; PyMuPDF render under a lock) -- reliable on Windows.
"""
import argparse, hashlib, os, re, sqlite3, subprocess, tempfile, threading, time
from concurrent.futures import ThreadPoolExecutor, as_completed
try:
    import fitz  # PyMuPDF
except Exception:
    fitz = None
try:
    import numpy as _np
except Exception:
    _np = None
try:
    import ocrprep
except Exception:
    ocrprep = None
# OCR pre-processing (deskew/denoise/binarize) before every OCR call (finding #14): ocrprep.py
# already had a working, self-tested preprocessing pipeline, but nothing in this file ever called
# it -- every scanned page was OCR'd raw. Operator-toggleable (VIEWER_OCR_PREPROCESS=0 to disable)
# because the real accuracy effect on this corpus hasn't been benchmarked yet -- default on, but
# easy to turn off if it turns out to hurt more than it helps. See _ocr_preprocessed_input() below
# for why RapidOCR and Tesseract get different pipelines (preprocess_light vs. preprocess).
OCR_PREPROCESS = os.environ.get("VIEWER_OCR_PREPROCESS", "1") != "0"

OCR_CHAR_THRESHOLD = 15
NSN_RE = re.compile(r"\b\d{4}-\d{2}-\d{3}-\d{4}\b")
TM_RE  = re.compile(r"\bTM\s*[0-9][0-9A-Za-z\-]+")

_RAPID = None
OCR_DPI = 200          # render DPI for OCR (profile-tunable)
USE_CUDA = False       # GPU OCR when True (RapidOCR + onnxruntime-gpu)
ADAPTIVE_DPI = os.environ.get("VIEWER_ADAPTIVE_DPI") == "1"   # opt-in: lower DPI on sparse pages (default OFF = no accuracy change)
_RAPID_LOCK = threading.Lock()
_FITZ_LOCK = threading.Lock()
# No timeout previously guarded either PDF rendering (PyMuPDF) or OCR inference (RapidOCR/
# Tesseract) on the default/preferred engine path -- one pathological page could stall an entire
# multi-hour ocrall() batch forever (finding #15). signal.alarm/SIGALRM isn't usable here: it can
# only preempt at a bytecode boundary or an interruptible syscall, and a single opaque native call
# (fitz.Page.get_pixmap(), an ONNX Runtime Run()) is exactly the case with neither -- that's true on
# any platform, not just Windows. A thread + .join(timeout) is the primitive that actually works:
# it gives up waiting on a real wall-clock deadline regardless of whether the target thread ever
# cooperates. The one thread that hung is leaked (never reclaimed -- Python has no safe way to kill
# a thread), but the process keeps going and the OS reclaims everything when it eventually exits.
OCR_PAGE_TIMEOUT_SECONDS = int(os.environ.get("VIEWER_OCR_PAGE_TIMEOUT", "120"))
_DEDUP = {}                       # img_hash -> OCR text: identical pages (boilerplate) reuse text, skip re-inference
_DEDUP_LOCK = threading.Lock()
_DEDUP_STATS = {"hits": 0}
def _page_density(path, page_number):
    """Fraction of dark pixels at 50 DPI gray — a cheap blank/complexity probe (one render reused for both
    the blank-skip and the optional adaptive DPI). Returns None if PyMuPDF/numpy aren't available.
    Review finding: this calls fitz directly and used to run OUTSIDE _FITZ_LOCK even after the
    render-lock hardening below — PyMuPDF's C state isn't thread-safe, so with --workers>1 this
    probe (called at the top of every ocr_one()) could still race concurrently against another
    thread's render, exactly the class of wedge/crash _FITZ_LOCK exists to prevent. Bounded (not
    unbounded) for the same reason _render_png's acquire is bounded: a busy lock degrades this
    best-effort probe to "skip it" (default DPI, no blank-skip) instead of blocking a worker thread
    indefinitely."""
    if fitz is None or _np is None: return None
    if not _FITZ_LOCK.acquire(timeout=OCR_PAGE_TIMEOUT_SECONDS):
        return None
    try:
        doc = fitz.open(path); pix = doc[page_number-1].get_pixmap(dpi=50, colorspace=fitz.csGRAY)
        arr = _np.frombuffer(pix.samples, dtype=_np.uint8); doc.close()
        if arr.size == 0: return 0.0
        return float((arr < 110).mean())
    except Exception:
        return None
    finally:
        _FITZ_LOCK.release()
def _have_rapid():
    try:
        import rapidocr  # modern unified package (PP-OCRv5, higher accuracy)  # noqa
        return True
    except Exception:
        pass
    try:
        import rapidocr_onnxruntime  # noqa  (PP-OCRv4)
        return True
    except Exception:
        return False

def _providers():
    try:
        import onnxruntime as ort; return ort.get_available_providers()
    except Exception:
        return []

class _RapidAdapter:
    """Normalises both the modern `rapidocr` (PP-OCRv5) output and the classic
    `rapidocr_onnxruntime` (PP-OCRv4) output to the (res, elapse) shape ocr_one expects,
    where each res item is [box, text, score]."""
    def __init__(self, eng, kind): self.eng = eng; self.kind = kind
    def __call__(self, img):
        out = self.eng(img)
        if hasattr(out, "txts"):                       # modern RapidOCROutput object
            txts = list(out.txts or [])
            boxes = list(out.boxes) if getattr(out, "boxes", None) is not None else [None]*len(txts)
            scores = list(out.scores) if getattr(out, "scores", None) is not None else [1.0]*len(txts)
            res = [[boxes[i] if i < len(boxes) else None, txts[i],
                    scores[i] if i < len(scores) else 1.0] for i in range(len(txts))]
            return res, float(getattr(out, "elapse", 0) or 0)
        if isinstance(out, tuple):                     # classic (result, elapse)
            return (out[0] or []), (out[1] if len(out) > 1 else 0)
        return (out or []), 0

def _selftest(adapter):
    """Render clear synthetic text and confirm the adapter actually extracts it end-to-end.
    Guards an untested engine API: if extraction fails, we fall back to the proven path."""
    try:
        from PIL import Image, ImageDraw
        import numpy as _np
        im = Image.new("RGB", (320, 90), "white"); d = ImageDraw.Draw(im)
        d.text((12, 28), "TM 5305 24P", fill="black")
        res, _ = adapter(_np.array(im))
        txt = " ".join((r[1] or "") for r in res)
        return sum(ch.isalnum() for ch in txt) >= 3
    except Exception:
        return False

def _get_rapid():
    global _RAPID
    if _RAPID is None:
        with _RAPID_LOCK:
            if _RAPID is None:
                _RAPID = _build_rapid()
    return _RAPID

def _build_rapid():
    prov = _providers(); gpu = "CUDAExecutionProvider" in prov
    log("OCR providers: " + (", ".join(prov) or "unknown") + (" [GPU]" if gpu else " [CPU]"))
    # 1) Preferred: modern rapidocr (PP-OCRv5, ~13pt more accurate than v4). GPU auto-engages via
    #    onnxruntime-gpu. Guarded by a self-test so a version/API mismatch can't break extraction.
    if os.environ.get("VIEWER_OCR_V5", "1") != "0":
        try:
            from rapidocr import RapidOCR as RapidV5
            ad = _RapidAdapter(RapidV5(), "v5")
            if _selftest(ad):
                log("OCR engine: RapidOCR PP-OCRv5" + (" on GPU" if gpu else " on CPU"))
                return ad
            log("PP-OCRv5 self-test did not extract text; falling back to PP-OCRv4.")
        except Exception as e:
            log("PP-OCRv5 unavailable (%s); using PP-OCRv4." % str(e)[:70])
    # 2) Proven: rapidocr_onnxruntime (PP-OCRv4), with CUDA when requested.
    from rapidocr_onnxruntime import RapidOCR
    if USE_CUDA:
        try:
            import rapidocr_onnxruntime as _ro
            base = os.path.join(os.path.dirname(_ro.__file__), "config.yaml")
            cfg = open(base, encoding="utf-8").read().replace("use_cuda: false", "use_cuda: true")
            tf = tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False, encoding="utf-8")
            tf.write(cfg); tf.close()
            log("OCR engine: RapidOCR PP-OCRv4, CUDA requested" + (" (GPU available)" if gpu else " (no GPU -> CPU)"))
            return _RapidAdapter(RapidOCR(config_path=tf.name), "v4")
        except Exception as e:
            log(f"GPU config failed ({str(e)[:70]}); using CPU")
            return _RapidAdapter(RapidOCR(), "v4")
    log("OCR engine: RapidOCR PP-OCRv4 (CPU)")
    return _RapidAdapter(RapidOCR(), "v4")

def log(msg): print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

def connect(db_path):
    con = sqlite3.connect(db_path, timeout=60)
    con.execute("PRAGMA foreign_keys=ON"); con.execute("PRAGMA synchronous=NORMAL")
    if os.environ.get("VIEWER_RELAXED") == "1":
        con.execute("PRAGMA locking_mode=EXCLUSIVE"); con.execute("PRAGMA journal_mode=TRUNCATE")
    return con

def _sql_statements(script):
    """Split a migration script into individual statements with sqlite3.complete_statement (aware of
    string literals, comments and trigger BEGIN..END bodies), skipping comment-only fragments. Needed
    because executescript() force-COMMITs any open transaction first -- which would break the
    one-transaction-per-migration atomicity guarantee below."""
    stmt = ""
    for line in script.splitlines(keepends=True):
        stmt += line
        if sqlite3.complete_statement(stmt):
            s = stmt.strip()
            if s and any(l.strip() and not l.strip().startswith("--") for l in s.splitlines()):
                yield s
            stmt = ""
    tail = stmt.strip()
    if tail and any(l.strip() and not l.strip().startswith("--") for l in tail.splitlines()):
        yield tail

def migrate(con, migrations_dir, db_path=None):
    """v1.13: each migration's DDL + its schema_version bump commit ATOMICALLY (one BEGIN IMMEDIATE ..
    COMMIT). Previously executescript() committed the DDL first and the version bump after -- a crash
    between the two left columns applied with a stale schema_version, the exact crash-loop class
    fix_schema_version.py exists to patch. Now a crash rolls the whole migration back cleanly.

    Backs up db_path via safeguard.backupdb() before applying any pending migration -- docs/
    ARCHITECTURE.md's standing rule R1 ("no breaking changes without ... a way to roll back")
    applies to schema DDL as much as anything else, and migrations are the least reversible write
    class in this codebase (SQLite's ALTER TABLE ADD COLUMN has no clean per-migration undo; only 1
    of 9 migration files even documents a rollback, and only in a prose comment). The docs used to
    separately claim this backup already happened (a fictional `viewer.db.bak-<version>-<date>`
    file) -- it never did; this makes that claim true, via the same VACUUM INTO backup mechanism
    every other write path that touches viewer.db already uses (ingest_feature.py, run_ocr_auto.bat,
    ENRICH-PUBLOG.bat, ...). Gated on `pending` being non-empty so the common no-op case (nothing to
    migrate, which is every read-only CLI invocation) doesn't pay a multi-GB backup cost. Backup
    failure aborts the whole migrate() call (raises) rather than proceeding without a rollback path
    -- unlike ingest_feature.py's best-effort pre-ingest snapshot, a migration that can't be rolled
    back if it goes wrong is exactly the scenario R1 exists to prevent."""
    has = con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='schema_meta'").fetchone()
    version = 0
    if has:
        row = con.execute("SELECT schema_version FROM schema_meta WHERE id=1").fetchone()
        version = row[0] if row else 0
    files = sorted(f for f in os.listdir(migrations_dir) if re.match(r"\d{4}_.*\.sql$", f))
    pending = [f for f in files if int(f[:4]) > version]
    if pending and db_path and os.path.exists(db_path):
        import safeguard
        log(f"migrate: {len(pending)} pending migration(s) -- backing up {db_path} before applying...")
        try:
            # Only the CANONICAL index (safeguard.DB_DEFAULT) backs up into the shared, rotated
            # <repo>/backups/db/ vault every other backup path in this codebase already writes to.
            # Any OTHER db_path (a test's tempdir DB, a staging/alternate corpus passed via --db)
            # gets its own sibling backups/db/ folder instead -- review finding: migrating a
            # throwaway/alternate DB must never write into (and keep=2-rotate stale copies out
            # of) the real production backup vault. Confirmed live: running the test suite used
            # to write into and rotate the actual repo's backups/db/ on every run.
            dest_dir = None
            if os.path.abspath(db_path) != os.path.abspath(safeguard.DB_DEFAULT):
                dest_dir = os.path.join(os.path.dirname(os.path.abspath(db_path)), "backups", "db")
            backup_path = safeguard.backupdb(db_path, dest_dir=dest_dir)
            log(f"migrate: backup OK -> {backup_path}")
        except Exception as e:
            log(f"MIGRATION ABORTED: pre-migration backup failed, refusing to apply DDL with no "
                f"rollback path. Fix the backup issue (often: free disk space) and rerun. Error: {e}")
            raise
    applied = 0
    for f in files:
        v = int(f[:4])
        if v > version:
            script = open(os.path.join(migrations_dir, f), encoding="utf-8").read()
            stmts = list(_sql_statements(script))
            # connection-level PRAGMAs (e.g. foreign_keys) are no-ops inside a transaction -> run first
            pragmas = [s for s in stmts if s.lstrip().upper().startswith("PRAGMA")]
            body = [s for s in stmts if s not in pragmas]
            try:
                for s in pragmas:
                    con.execute(s)
                con.commit()                              # close any implicit txn; BEGIN must start clean
                con.execute("BEGIN IMMEDIATE")            # DDL + version bump: ONE atomic unit
                for s in body:
                    con.execute(s)
                con.execute("UPDATE schema_meta SET schema_version=? WHERE id=1", (v,))
                con.commit()
            except Exception as e:
                try: con.rollback()
                except Exception: pass
                log(f"MIGRATION FAILED: {f} -- rolled back ATOMICALLY, schema_version stays {version}; "
                    f"nothing was partially applied. Fix the migration and rerun. Error: {e}")
                raise
            applied += 1; version = v; log(f"applied migration {f}")
    if applied == 0: log(f"schema up to date (v{version})")
    return con

def fingerprint(path, st):
    h = hashlib.md5()
    try:
        with open(path, "rb") as fh: h.update(fh.read(65536))
    except OSError: pass
    return f"{st.st_size}:{int(st.st_mtime)}:{h.hexdigest()[:12]}"

def run_cmd(args, timeout=300):
    return subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=timeout).stdout.decode("utf-8","ignore")

def pdf_pages_text(path):
    if fitz is not None:
        try:
            doc = fitz.open(path)
            pages = [doc[i].get_text("text") for i in range(doc.page_count)]
            doc.close(); return pages
        except Exception:
            return None
    try: out = run_cmd(["pdftotext","-q",path,"-"], timeout=300)
    except Exception: return None
    return out.split("\f")

def classify_ext(path):
    e = os.path.splitext(path)[1].lower().lstrip(".")
    if e == "pdf": return "pdf"
    if e in ("jpg","jpeg","png","tif","tiff","bmp","gif","svg","svgz"): return "image"
    if e in ("doc","docx","ppt","pptx","xls","xlsx","rtf","txt","htm","html"): return "office"
    return "other"

def upsert_document(con, path, root):
    st = os.stat(path)
    prefix = f"{st.st_size}:{int(st.st_mtime)}"
    row = con.execute("SELECT id, fingerprint FROM documents WHERE path=?", (path,)).fetchone()
    if row and row[1] and row[1].startswith(prefix + ":"):
        return None
    fp = fingerprint(path, st)
    rel = os.path.relpath(path, root)
    vehicle = rel.split(os.sep)[0] if os.sep in rel else rel
    if row and row[1] == fp: return None
    kind = classify_ext(path)
    if row:
        doc_id = row[0]
        con.execute("DELETE FROM pages WHERE document_id=?", (doc_id,))
        con.execute("UPDATE documents SET fingerprint=?, type=?, size_bytes=?, mtime=?, status='discovered', updated_at=datetime('now') WHERE id=?",
                    (fp, kind, st.st_size, st.st_mtime, doc_id))
    else:
        cur = con.execute("INSERT INTO documents(path, rel_path, fingerprint, type, vehicle, size_bytes, mtime, status) VALUES(?,?,?,?,?,?,?, 'discovered')",
                          (path, rel, fp, kind, vehicle, st.st_size, st.st_mtime))
        doc_id = cur.lastrowid
    return doc_id, kind

def index_pdf(con, doc_id, path):
    pages = pdf_pages_text(path)
    if pages is None:
        con.execute("UPDATE documents SET status='failed' WHERE id=?", (doc_id,)); return 0, 0
    indexed = queued = 0; meta_text = ""
    for i, txt in enumerate(pages, start=1):
        body = txt.strip(); cc = len(body)
        if i <= 3: meta_text += " " + body
        if cc < OCR_CHAR_THRESHOLD:
            con.execute("INSERT INTO pages(document_id,page_number,body_text,char_count,source,ocr_status) VALUES(?,?,?,?, 'none','pending')",(doc_id,i,"",cc)); queued += 1
        else:
            con.execute("INSERT INTO pages(document_id,page_number,body_text,char_count,source,ocr_status) VALUES(?,?,?,?, 'text','none')",(doc_id,i,body,cc)); indexed += 1
    nsn = NSN_RE.search(meta_text); tm = TM_RE.search(meta_text)
    title = next((l.strip() for l in meta_text.splitlines() if len(l.strip()) > 6), "")[:200]
    dtype = "pdf_text" if indexed >= queued else "pdf_scanned"
    con.execute("UPDATE documents SET page_count=?, tm_number=?, nsn=?, title=?, type=?, status=? WHERE id=?",
                (len(pages), tm.group(0) if tm else None, nsn.group(0) if nsn else None, title, dtype, 'indexed' if queued==0 else 'partial', doc_id))
    return indexed, queued

def crawl(con, root, max_files=0, max_seconds=0):
    rid = con.execute("INSERT INTO runs(kind) VALUES('crawl')").lastrowid
    seen=new=pi=q=fail=0; t0=time.time()
    for dirpath, dirnames, filenames in os.walk(root, followlinks=True):
        if os.sep + "." in dirpath: continue
        for fn in filenames:
            if fn.lower() in ("thumbs.db",".ds_store"): continue
            path = os.path.join(dirpath, fn); seen += 1
            try:
                res = upsert_document(con, path, root)
                if res is None:
                    if max_seconds and seen % 200 == 0 and time.time()-t0 > max_seconds:
                        con.commit(); log(f"crawl: time budget reached while scanning (seen={seen}), pausing"); return
                    continue
                doc_id, kind = res; new += 1
                if kind == "pdf":
                    a,b = index_pdf(con, doc_id, path); pi += a; q += b
                else:
                    con.execute("UPDATE documents SET status='indexed' WHERE id=?", (doc_id,))
                if new % 10 == 0:
                    con.execute("UPDATE runs SET files_seen=?, new_docs=?, pages_indexed=?, ocr_queued=? WHERE id=?",(seen,new,pi,q,rid)); con.commit()
                    log(f"crawl: seen={seen} new={new} pages_text={pi} ocr_queued={q} ({seen/max(1,time.time()-t0):.0f} files/s)")
                if max_files and new >= max_files:
                    con.execute("UPDATE runs SET finished_at=datetime('now'), files_seen=?, new_docs=?, pages_indexed=?, ocr_queued=?, failed=? WHERE id=?",(seen,new,pi,q,fail,rid)); con.commit()
                    log(f"crawl: batch cap {max_files} reached, pausing (resumable)"); return
                if max_seconds and time.time()-t0 > max_seconds:
                    con.execute("UPDATE runs SET finished_at=datetime('now'), files_seen=?, new_docs=?, pages_indexed=?, ocr_queued=?, failed=? WHERE id=?",(seen,new,pi,q,fail,rid)); con.commit()
                    log(f"crawl: time budget {max_seconds}s reached, pausing (resumable)"); return
            except Exception as e:
                fail += 1; log(f"ERROR {path}: {e}")
    con.execute("UPDATE runs SET finished_at=datetime('now'), files_seen=?, new_docs=?, pages_indexed=?, ocr_queued=?, failed=? WHERE id=?",(seen,new,pi,q,fail,rid)); con.commit()
    log(f"CRAWL DONE seen={seen} new={new} pages_text={pi} ocr_queued={q} failed={fail}")

def _render_png(path, page_number, dpi=None):
    d = int(dpi or OCR_DPI)
    if fitz is not None:
        # Bounded acquire, not a bare `with _FITZ_LOCK:` -- PyMuPDF's C state isn't thread-safe, so
        # every render in this process serializes behind this one lock. If a render ever wedges
        # *while holding it*, an unbounded acquire means every OTHER worker thread's next call to
        # _render_png() also blocks forever trying to acquire the same lock -- "one page hangs"
        # silently becomes "the whole process wedges on its very next render." A bounded acquire
        # means a page that can't get the lock in time fails fast (raises, caught by _ocr_task's
        # own timeout/except handling) instead of hanging, so the batch keeps draining even after a
        # wedge -- degraded, but ocrall() still exits normally and the existing crash/restart loop
        # in run_ocr_auto.bat can pick it back up (finding #15).
        if not _FITZ_LOCK.acquire(timeout=OCR_PAGE_TIMEOUT_SECONDS):
            raise TimeoutError("PyMuPDF render lock busy for >%ds -- a prior render may be wedged" % OCR_PAGE_TIMEOUT_SECONDS)
        try:
            doc = fitz.open(path); pix = doc[page_number-1].get_pixmap(dpi=d)
            data = pix.tobytes("png"); doc.close()
        finally:
            _FITZ_LOCK.release()
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tf:
            tf.write(data); return tf.name
    td = tempfile.mkdtemp(); prefix = os.path.join(td, "pg")
    subprocess.run(["pdftoppm","-r",str(d),"-f",str(page_number),"-l",str(page_number),"-png",path,prefix],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=180)
    pngs = [os.path.join(td,f) for f in os.listdir(td) if f.endswith(".png")]
    if not pngs: raise RuntimeError("pdftoppm produced no image")
    return pngs[0]

def _page_is_blank(path, page_number):
    """Skip-the-junk: True if the page is essentially blank (covers, dividers, empty backs)."""
    if fitz is None or _np is None: return False
    try:
        doc = fitz.open(path)
        pix = doc[page_number-1].get_pixmap(dpi=50, colorspace=fitz.csGRAY)
        arr = _np.frombuffer(pix.samples, dtype=_np.uint8); doc.close()
        if arr.size == 0: return True
        return float((arr < 110).mean()) < 0.004   # < 0.4% dark pixels => blank
    except Exception:
        return False

def _ocr_preprocessed_input(img_path, for_tesseract):
    """Best-effort OCR preprocessing (finding #14). Returns what to actually feed to the OCR
    engine: for RapidOCR (for_tesseract=False), a preprocessed numpy array via
    ocrprep.preprocess_light() -- deskew + denoise, NOT binarize, since a hard Otsu threshold is a
    classic-OCR-era optimization that can hurt a deep-learning detector/recognizer by discarding
    anti-aliasing/gradient information a DL model can actually use. For Tesseract (for_tesseract=
    True, this project's fallback engine -- a classic pipeline that DOES benefit from
    binarization), a NEW temp PNG file path via the full ocrprep.preprocess() (deskew + denoise +
    binarize). Falls back to the raw, unmodified image on any failure or when OpenCV/numpy aren't
    available -- this is a quality improvement, never a hard requirement; a preprocessing bug must
    never be the reason a page fails to OCR at all."""
    if not (OCR_PREPROCESS and ocrprep is not None and ocrprep.available() and _np is not None):
        return img_path
    try:
        from PIL import Image
        with Image.open(img_path) as im:
            arr = _np.array(im.convert("RGB"))
        if for_tesseract:
            import cv2
            proc, _meta = ocrprep.preprocess(arr)
            out_path = img_path + ".prep.png"
            # cv2.imwrite() can fail (bad path, bad array) by returning False, not by raising --
            # review finding: the old unconditional `return out_path` broke the docstring's own
            # "falls back to the raw image on any failure" promise on exactly that failure mode.
            if not cv2.imwrite(out_path, proc):
                return img_path
            return out_path
        proc, _meta = ocrprep.preprocess_light(arr)
        # Review finding: preprocess_light() always collapses to a 2-D grayscale array (ocrprep.
        # _gray() is unconditional inside deskew()/denoise()); RapidOCR is only ever self-tested
        # against a 3-channel array elsewhere in this codebase, so restore 3 channels here rather
        # than ship an unverified grayscale-array shape on this default-on path.
        if getattr(proc, "ndim", 3) == 2:
            import cv2
            proc = cv2.cvtColor(proc, cv2.COLOR_GRAY2RGB)
        return proc
    except Exception:
        return img_path


def ocr_one(path, page_number):
    """Returns (text, confidence). confidence is RapidOCR's page-level average of its per-line detection
    scores (0.0-1.0), rounded to 4dp -- None on the blank-skip path, the Tesseract fallback (no per-line
    scores exposed the same way), or if RapidOCR returned no scored lines. v1.13.5: this score was always
    being computed (see _RapidAdapter, r[2]) but silently discarded here -- captured now as the first real,
    corpus-wide OCR-quality signal (previously the only signal was 'OCR ran' vs 'OCR did not run')."""
    dens = _page_density(path, page_number)
    if dens is not None and dens < 0.004: return "", None   # skip-the-junk: no OCR on blanks (same threshold)
    dpi = OCR_DPI
    if ADAPTIVE_DPI and dens is not None and dens < 0.02:   # opt-in: sparse pages render lower (never below 160)
        dpi = max(160, OCR_DPI - 50)
    img = None
    tess_img = None
    try:
        img = _render_png(path, page_number, dpi)
        h = None                                          # identical-page dedup: reuse text for repeated boilerplate
        try:
            with open(img, "rb") as f: h = hashlib.md5(f.read()).hexdigest()
        except Exception: h = None
        if h is not None:
            with _DEDUP_LOCK: cached = _DEDUP.get(h)
            if cached is not None:
                _DEDUP_STATS["hits"] += 1; return cached
        # Dedup hash above is deliberately over the RAW render, before preprocessing -- identical
        # source pages still produce an identical raw render, so the dedup key is unaffected by
        # whether preprocessing itself is on/off or changes over time.
        if _have_rapid():
            ocr_input = _ocr_preprocessed_input(img, for_tesseract=False)
            res, _ = _get_rapid()(ocr_input)
            text = "\n".join(r[1] for r in res).strip() if res else ""
            scores = [r[2] for r in res if len(r) > 2 and isinstance(r[2], (int, float))] if res else []
            conf = round(sum(scores) / len(scores), 4) if scores else None
        else:
            tess_img = _ocr_preprocessed_input(img, for_tesseract=True)
            out = subprocess.run(["tesseract", tess_img, "-", "-l", "eng", "--psm", "1"],
                                 stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=180)
            text = out.stdout.decode("utf-8","ignore").strip()
            conf = None   # tesseract fallback: no per-line confidence captured (yet)
        result = (text, conf)
        if h is not None:
            with _DEDUP_LOCK:
                if len(_DEDUP) < 200000: _DEDUP[h] = result
        return result
    finally:
        if img and os.path.exists(img):
            try: os.unlink(img)
            except OSError: pass
        if tess_img and tess_img != img and os.path.exists(tess_img):
            try: os.unlink(tess_img)
            except OSError: pass

def _ocr_task(args):
    """Runs ocr_one() with a wall-clock deadline (OCR_PAGE_TIMEOUT_SECONDS) via a helper thread +
    .join(timeout) -- see the module-level comment by OCR_PAGE_TIMEOUT_SECONDS for why this, not
    signal.alarm or a bare subprocess. Called both from ocr()'s single-threaded loop (workers<=1)
    and from inside its ThreadPoolExecutor (workers>1) -- wrapping it here (rather than in ocr()
    itself) means the timeout applies uniformly in both cases with one implementation. Times out ->
    same (pid, None, None, err) shape as any other failure, so handle() needs no changes: the page
    is marked 'failed' and the batch moves on to the next one instead of hanging on it forever."""
    pid, pno, path = args
    box = {}
    def run():
        try:
            box["text"], box["conf"] = ocr_one(path, pno)
        except Exception as e:
            box["err"] = str(e)[:300]
    t = threading.Thread(target=run, daemon=True)
    t.start()
    t.join(OCR_PAGE_TIMEOUT_SECONDS)
    if t.is_alive():
        return pid, None, None, "timeout after %ds" % OCR_PAGE_TIMEOUT_SECONDS
    if "err" in box:
        return pid, None, None, box["err"]
    return pid, box.get("text"), box.get("conf"), None

def _db_dir(con):
    try:
        for _seq, name, fpath in con.execute("PRAGMA database_list"):
            if name == "main" and fpath: return os.path.dirname(os.path.abspath(fpath))
    except Exception: pass
    return None

def _heartbeat(d, done, fail, remaining):
    """Write a progress heartbeat next to the index so a watchdog can tell a working pass from a hung
    one. Best-effort: a write failure never affects OCR."""
    if not d: return
    try:
        with open(os.path.join(d, "ocr_heartbeat.txt"), "w") as f:
            f.write("%s done=%d fail=%d remaining=%s\n" % (time.strftime("%Y-%m-%d %H:%M:%S"), done, fail, remaining))
    except Exception: pass

def ocr(con, limit, workers=1):
    rid = con.execute("INSERT INTO runs(kind) VALUES('ocr')").lastrowid
    done=fail=0
    dbdir = _db_dir(con)
    # disk guard (RPS-safe): if the index drive is low on space, pause this pass cleanly instead of
    # filling the disk. Fail-open if free space can't be read. The auto-runner will retry.
    if dbdir:
        try:
            from preflight import disk_ok
            ok, free, thr = disk_ok(dbdir)
            if not ok:
                log("ocr: PAUSED -- low disk (%s MB free, need >= %s). Free space and it resumes." % (free, thr))
                con.execute("UPDATE runs SET finished_at=datetime('now') WHERE id=?", (rid,)); con.commit()
                return con.execute("SELECT COUNT(*) FROM pages WHERE ocr_status='pending'").fetchone()[0]
        except Exception:
            pass
    rows = con.execute("SELECT p.id, p.page_number, d.path FROM pages p JOIN documents d ON d.id=p.document_id WHERE p.ocr_status='pending' ORDER BY p.ocr_priority, p.id LIMIT ?", (limit,)).fetchall()
    log(f"ocr: {len(rows)} pages to process this batch (threads={workers}, engine={'RapidOCR' if _have_rapid() else 'tesseract'})")
    if not rows:
        con.execute("UPDATE runs SET finished_at=datetime('now') WHERE id=?", (rid,)); con.commit()
        _heartbeat(dbdir, 0, 0, 0); return 0
    con.executemany("UPDATE pages SET ocr_status='running' WHERE id=?", [(r[0],) for r in rows]); con.commit()
    if _have_rapid(): _get_rapid()            # build the shared engine once, up front
    def handle(pid, text, conf, err):
        nonlocal done, fail
        if err is None:
            con.execute("UPDATE pages SET body_text=?, char_count=?, source='ocr', ocr_status='done', ocr_confidence=? WHERE id=?", (text, len(text), conf, pid)); done += 1
        else:
            con.execute("UPDATE pages SET ocr_status='failed' WHERE id=?", (pid,))
            con.execute("INSERT INTO jobs(page_id,stage,state,attempts,last_error) VALUES(?,?, 'failed', 1, ?)", (pid,"ocr",err)); fail += 1
        if (done+fail) % 5 == 0: con.commit(); _heartbeat(dbdir, done, fail, None); log(f"ocr: done={done} failed={fail} (last page {len(text) if text else 0} chars)")
    if workers <= 1:
        for r in rows: handle(*_ocr_task(r))
    else:
        with ThreadPoolExecutor(max_workers=workers) as ex:
            for fut in as_completed([ex.submit(_ocr_task, r) for r in rows]): handle(*fut.result())
    con.execute("UPDATE documents SET status='indexed' WHERE status='partial' AND id NOT IN (SELECT document_id FROM pages WHERE ocr_status IN ('pending','running','failed'))")
    con.execute("UPDATE runs SET finished_at=datetime('now'), ocr_done=?, failed=? WHERE id=?", (done,fail,rid)); con.commit()
    remaining = con.execute("SELECT COUNT(*) FROM pages WHERE ocr_status='pending'").fetchone()[0]
    _heartbeat(dbdir, done, fail, remaining)
    log(f"OCR BATCH DONE done={done} failed={fail} dedup_reused={_DEDUP_STATS['hits']} remaining_pending={remaining}")
    return remaining

def cleanup(con):
    # Remove leftover sandbox/Unix-path documents (start with '/') whose files don't exist
    # on this machine, and requeue any pages stuck in 'failed'/'running'. Clear non-cascading
    # references (request_items, figures, parts -- none of these cascade-delete, see prune()'s
    # docstring below for why) first so the document delete doesn't trip a FK.
    con.execute("UPDATE request_items SET source_document_id=NULL WHERE source_document_id IN (SELECT id FROM documents WHERE path LIKE '/%')")
    con.execute("DELETE FROM figures WHERE document_id IN (SELECT id FROM documents WHERE path LIKE '/%')")
    # Review finding: this used to omit `parts`, unlike prune()'s otherwise-identical delete
    # sequence below -- orphaning parts rows for every orphan document this removed.
    con.execute("DELETE FROM parts WHERE document_id IN (SELECT id FROM documents WHERE path LIKE '/%')")
    n = con.execute("DELETE FROM documents WHERE path LIKE '/%'").rowcount
    con.commit()
    r = con.execute("UPDATE pages SET ocr_status='pending' WHERE ocr_status IN ('failed','running')").rowcount
    con.execute("DELETE FROM jobs WHERE stage='ocr'")
    con.commit()
    print(f"cleanup: removed {n} orphan documents; requeued {r} pages to 'pending'")

def _prune_sidecars(index_dir, doc_ids, log=log):
    """Best-effort cleanup of the optional per-document sidecars after documents are pruned from the
    main index. Every sidecar here is built by a SEPARATE host-run script (BUILD-MEASURES.bat etc.)
    and may simply not exist yet -- that is not an error, just nothing to prune. A sidecar that DOES
    exist but is locked/corrupt must never abort the (already-committed) main-index prune, so every
    step is wrapped and merely logged on failure (R1: this is cleanup, not a required step)."""
    if not index_dir or not doc_ids:
        return
    ids = list(doc_ids)
    # measures.db: doc-keyed rows, explicit DELETE WHERE doc=? (finding #11's own plan)
    meas_db = os.path.join(index_dir, "measures.db")
    if os.path.exists(meas_db):
        try:
            mc = sqlite3.connect(meas_db, timeout=30)
            try:
                qs = ",".join("?" * len(ids))
                mc.execute("DELETE FROM meas WHERE doc IN (%s)" % qs, ids)
                mc.execute("DELETE FROM meas_done WHERE doc IN (%s)" % qs, ids)
                mc.commit()
            finally:
                mc.close()
        except Exception as e:
            log(f"prune: measures.db cleanup skipped ({e})")
    # tables.db: same doc-keyed shape, same treatment (schema is build_tables.py's own: tables
    # `tbl`/`tbl_done`, both doc-keyed -- confirmed against build_tables.py's SCHEMA, NOT
    # guessed; a review finding caught an earlier version of this using wrong table names,
    # which made the DELETE a silent permanent no-op).
    tab_db = os.path.join(index_dir, "tables.db")
    if os.path.exists(tab_db):
        try:
            tc = sqlite3.connect(tab_db, timeout=30)
            try:
                qs = ",".join("?" * len(ids))
                names = {r[0] for r in tc.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                for tbl, col in (("tbl", "doc"), ("tbl_done", "doc")):
                    if tbl in names:
                        tc.execute("DELETE FROM %s WHERE %s IN (%s)" % (tbl, col, qs), ids)
                tc.commit()
            finally:
                tc.close()
        except Exception as e:
            log(f"prune: tables.db cleanup skipped ({e})")
    # Cache directories keyed by doc_id, one prefix pattern per directory's OWN naming convention
    # (confirmed against each cache's cache_path()/cache_key(), not assumed uniform -- a review
    # finding caught an earlier version of this missing pagecache/ entirely, since rps.py's
    # pagecache uses a HYPHEN ("<doc>-<page>-d<dpi>.png"), not the underscore the other three
    # caches use, plus figcache's callout_crop() output ("callout_<doc>_<page>_<item>_<dpi>.png")
    # doesn't start with the doc_id at all).
    _CACHE_DIR_PREFIXES = {
        "figcache":   ("%d_", "callout_%d_"),
        "schemcache": ("%d_",),
        "veccache":   ("%d_",),
        "pagecache":  ("%d-",),
    }
    for sub, templates in _CACHE_DIR_PREFIXES.items():
        d = os.path.join(index_dir, sub)
        if not os.path.isdir(d):
            continue
        prefixes = tuple(t % i for i in ids for t in templates)
        try:
            for fn in os.listdir(d):
                if fn.startswith(prefixes):
                    try: os.remove(os.path.join(d, fn))
                    except OSError: pass
        except Exception as e:
            log(f"prune: {sub}/ cleanup skipped ({e})")


def prune(con, root="", confirm=False, missing_threshold=0.5, index_dir=None):
    """Reconcile documents whose SOURCE FILE has been deleted or renamed/moved off disk since the
    last crawl (finding #11). crawl()/upsert_document() only ever ADD or UPDATE documents matched by
    exact path -- nothing ever notices a source file that is simply gone, so its row (and every page,
    part, and figure cited from it) sits in the index forever, dead weight that can also surface as a
    broken 'open the PDF' link in the UI. Dry-run by default (same --yes-to-confirm shape as
    rollback()); a plain re-run after --yes shows nothing left to prune.

    Safety valves (a prune is a DELETE -- must never mistake 'can't see the corpus right now' for
    'the corpus shrank'):
      * corpus root unreachable: if `root` is given and isn't a directory (e.g. an unmounted external
        drive or an unmapped network share), abort without looking at a single document -- otherwise
        EVERY document would appear missing and a naive prune would wipe the whole index.
      * missing-fraction threshold: even with a reachable root, if the fraction of indexed documents
        whose file is gone exceeds `missing_threshold` (default 50%), abort and ask for confirmation
        via a higher --missing-threshold -- a mass-disappearance is far more likely a moved corpus
        root or a bad --root than a real mass-deletion.

    A 'renamed/moved' file is detected without re-reading anything: if a missing document's stored
    fingerprint (size:mtime:headhash) matches another, PRESENT document's fingerprint, crawl() has
    already re-discovered that same file under its new path -- the stale old row is a pure duplicate
    and is safe to drop outright (its content is already indexed under the new row).

    Removes the stale row's non-cascading references first (figures, parts: no ON DELETE CASCADE;
    request_items: SET NULL, keeping the session's own history instead of erasing it) so the
    documents DELETE itself doesn't trip a foreign-key error -- pages/jobs DO cascade (schema-level
    ON DELETE CASCADE) and need no manual handling. Then best-effort-prunes the optional per-document
    sidecars (measures.db/tables.db/figcache/schemcache/veccache/pagecache) for the same doc_ids.

    Returns a summary dict; never raises for an ordinary abort (aborted reasons are returned, not
    thrown) so callers/tests can assert on the outcome instead of parsing log output."""
    if root and not os.path.isdir(root):
        log(f"prune: ABORT -- corpus root not reachable ({root!r}); refusing to treat every indexed "
            f"document as deleted. Fix --root (or unmount/mount the drive) and retry.")
        return {"ok": False, "aborted": "root_unreachable", "root": root}

    rows = con.execute("SELECT id, path, fingerprint FROM documents").fetchall()   # tuple rows (this
    total = len(rows)                                                              # file's convention --
    if total == 0:                                                                 # connect() sets no
        log("prune: no documents in the index -- nothing to do")                  # row_factory)
        return {"ok": True, "total": 0, "missing": 0, "deleted": 0, "renamed": 0, "removed_ids": []}

    missing = [r for r in rows if not os.path.isfile(r[1])]
    if not missing:
        log(f"prune: all {total} indexed documents' files exist -- nothing to do")
        return {"ok": True, "total": total, "missing": 0, "deleted": 0, "renamed": 0, "removed_ids": []}

    frac = len(missing) / total
    if frac > missing_threshold:
        log(f"prune: ABORT -- {len(missing)}/{total} ({frac:.0%}) of indexed documents appear missing, "
            f"over the {missing_threshold:.0%} safety threshold. This looks like a moved corpus root or "
            f"an unmounted drive, not a real mass-deletion. Re-run with --root pointing at the corpus, "
            f"or a higher --missing-threshold if this is genuinely intended.")
        return {"ok": False, "aborted": "missing_fraction", "total": total, "missing": len(missing),
                "fraction": round(frac, 4)}

    present_fp = {r[2]: r[0] for r in rows if r[2] and os.path.isfile(r[1])}
    renamed, deleted = [], []
    for r in missing:
        dup = present_fp.get(r[2]) if r[2] else None
        (renamed if dup else deleted).append((r[0], r[1], dup))

    if not confirm:
        log(f"prune: DRY RUN -- would remove {len(missing)}/{total} document(s) "
            f"({len(renamed)} moved/renamed, {len(deleted)} deleted). Re-run with --yes to actually prune.")
        for doc_id, path, dup in (renamed + deleted)[:25]:
            tag = f"moved -> now doc {dup}" if dup else "deleted, no replacement found"
            log(f"  [{tag}] doc {doc_id}: {path}")
        return {"ok": True, "total": total, "missing": len(missing), "deleted": len(deleted),
                "renamed": len(renamed), "removed_ids": [d for d, _, _ in renamed + deleted]}

    ids = [d for d, _, _ in renamed + deleted]
    qs = ",".join("?" * len(ids))
    con.execute(f"UPDATE request_items SET source_document_id=NULL WHERE source_document_id IN ({qs})", ids)
    con.execute(f"DELETE FROM figures WHERE document_id IN ({qs})", ids)
    con.execute(f"DELETE FROM parts WHERE document_id IN ({qs})", ids)
    con.execute(f"DELETE FROM documents WHERE id IN ({qs})", ids)   # pages/jobs cascade (schema ON DELETE CASCADE)
    con.commit()
    log(f"PRUNE DONE: removed {len(ids)} document(s) ({len(renamed)} moved/renamed, {len(deleted)} deleted) "
        f"+ their figures/parts; {len(renamed)} request_items reference(s) cleared to NULL.")
    _prune_sidecars(index_dir, ids, log=log)
    return {"ok": True, "total": total, "missing": len(missing), "deleted": len(deleted),
            "renamed": len(renamed), "removed_ids": ids}


def prioritize(con):
    """Set OCR order: parts catalogs first, then maintenance/troubleshooting, then operator, then rest."""
    try:
        con.execute("""UPDATE pages SET ocr_priority = (SELECT CASE
              WHEN upper(d.path) LIKE '%24P%' OR upper(d.path) LIKE '%PARTS%' OR upper(d.path) LIKE '%RPSTL%' OR upper(coalesce(d.tm_number,'')) LIKE '%24P%' THEN 0
              WHEN upper(d.path) LIKE '%TROUBLESHOOT%' THEN 1
              WHEN upper(d.path) LIKE '%MAINT%' OR upper(coalesce(d.tm_number,'')) LIKE '%-20%' OR upper(coalesce(d.tm_number,'')) LIKE '%-24%' THEN 2
              WHEN upper(d.path) LIKE '%OPERATOR%' OR upper(coalesce(d.tm_number,'')) LIKE '%-10%' THEN 3
              ELSE 5 END FROM documents d WHERE d.id = pages.document_id)
            WHERE ocr_status='pending'""")
        con.commit()
        log("prioritized OCR queue (parts > maintenance/troubleshooting > operator > rest)")
    except sqlite3.OperationalError as e:
        log(f"prioritize skipped ({e}) -- run migrate first")

def prefilter(con, limit, workers=1):
    """Mark blank pending pages as 'skipped' so they leave the OCR queue (shrinks the backlog)."""
    rows = con.execute("SELECT p.id, p.page_number, d.path FROM pages p JOIN documents d ON d.id=p.document_id WHERE p.ocr_status='pending' ORDER BY p.ocr_priority, p.id LIMIT ?", (limit,)).fetchall()
    log(f"prefilter: scanning {len(rows)} pending pages for blanks")
    skipped=0
    for pid, pno, path in rows:
        if _page_is_blank(path, pno):
            con.execute("UPDATE pages SET ocr_status='skipped' WHERE id=?", (pid,)); skipped += 1
            if skipped % 50 == 0: con.commit(); log(f"prefilter: skipped {skipped} blanks")
    con.commit()
    remaining = con.execute("SELECT COUNT(*) FROM pages WHERE ocr_status='pending'").fetchone()[0]
    log(f"PREFILTER DONE skipped={skipped} remaining_pending={remaining}")
    return remaining

def status(con):
    def one(q,*a): return con.execute(q,a).fetchone()[0]
    print("documents       :", one("SELECT COUNT(*) FROM documents"))
    print("  pdf_text      :", one("SELECT COUNT(*) FROM documents WHERE type='pdf_text'"))
    print("  pdf_scanned   :", one("SELECT COUNT(*) FROM documents WHERE type='pdf_scanned'"))
    print("  other types   :", one("SELECT COUNT(*) FROM documents WHERE type NOT LIKE 'pdf%'"))
    print("pages total     :", one("SELECT COUNT(*) FROM pages"))
    print("  text-indexed  :", one("SELECT COUNT(*) FROM pages WHERE source='text'"))
    print("  ocr-indexed   :", one("SELECT COUNT(*) FROM pages WHERE source='ocr'"))
    print("  ocr pending   :", one("SELECT COUNT(*) FROM pages WHERE ocr_status='pending'"))
    print("  ocr failed    :", one("SELECT COUNT(*) FROM pages WHERE ocr_status='failed'"))

def search(con, query, k=8):
    rows = con.execute("SELECT d.vehicle, d.tm_number, p.page_number, snippet(pages_fts,0,'[',']','...',8) FROM pages_fts JOIN pages p ON p.id=pages_fts.rowid JOIN documents d ON d.id=p.document_id WHERE pages_fts MATCH ? ORDER BY rank LIMIT ?", (query,k)).fetchall()
    for v,tm,pg,sn in rows: print(f"  [{v}] {tm or ''} p.{pg}: {sn.replace(chr(10),' ')}")
    if not rows: print("  (no matches)")

_PARTS_NSN_RE = re.compile(r'\b(\d{4}-\d{2}-\d{3}-\d{4})\b')
_PARTS_FIG_RE = re.compile(r'\bFIG(?:URE)?\.?\s*(\d+)\s*[:.\-]?\s*([A-Za-z][A-Za-z0-9 ,/&()\-]{2,50})')

def extract_parts(con):
    """Build a structured, cited parts index from RPSTL pages: each NSN tied to its figure
    (number + title), document, page, and vehicle. Reliable + idempotent (full rebuild). Exact
    NSN->part#/nomenclature row alignment is OCR-noisy, so it is intentionally NOT asserted here;
    every record carries its source page for citation/verification."""
    log("extracting structured parts from RPSTL pages...")
    dbdir = _db_dir(con)
    # Review finding: ocrall's heartbeat only covered the OCR batch loop, not this phase that runs
    # after it -- ocr_supervisor.py could mistake a long extract_parts() pass for a stale hang and
    # kill it, discarding the work (and run_ocr_auto.bat would still declare "OCR COMPLETE" since
    # OCR itself had already reached 0 pending by then).
    _heartbeat(dbdir, 0, 0, "extract_parts")
    con.execute("DELETE FROM parts WHERE confidence IS NOT NULL"); con.commit()
    try:
        rows = con.execute(
            "SELECT p.document_id, p.page_number, p.body_text, d.vehicle "
            "FROM pages_fts JOIN pages p ON p.id=pages_fts.rowid JOIN documents d ON d.id=p.document_id "
            "WHERE pages_fts MATCH ?", ('"usable on code"',)).fetchall()
    except Exception as e:
        log(f"parts: FTS query failed ({e}); run migrate/crawl first"); return 0
    batch = []; seen = set(); npages = 0
    for r in rows:
        # Bug found + fixed during review verification (pre-existing, predates this diff): this
        # loop used dict-style row access (r["document_id"], ...) against a connection that
        # returns plain tuples -- connect() sets no row_factory anywhere in this file. Reproduced
        # directly: extract_parts() raised "tuple indices must be integers or slices, not str" on
        # the first RPSTL-style page matching the FTS phrase below, which real parts-list text
        # commonly does. Switched to positional unpacking, matching every other query in this file.
        document_id, page_number, body_text, vehicle = r
        npages += 1
        bt = body_text or ""
        figs = [(m.start(), m.group(1), re.sub(r'\s+', ' ', m.group(2)).strip()) for m in _PARTS_FIG_RE.finditer(bt)]
        for m in _PARTS_NSN_RE.finditer(bt):
            nsn = m.group(1); pos = m.start(); fno = ftit = None
            for fp, fn, ft in figs:
                if fp <= pos: fno, ftit = fn, ft
                else: break
            key = (document_id, page_number, nsn)
            if key in seen: continue
            seen.add(key)
            batch.append((nsn, ftit, ftit, document_id, page_number, vehicle, fno, ftit, "page"))
        if npages % 200 == 0:
            _heartbeat(dbdir, npages, 0, "extract_parts")
    con.executemany(
        "INSERT INTO parts(nsn, name, nomenclature, document_id, page, vehicle, fig_no, fig_title, confidence, created_at) "
        "VALUES(?,?,?,?,?,?,?,?,?,datetime('now'))", batch)
    con.commit()
    _heartbeat(dbdir, npages, 0, 0)
    log(f"parts: {npages} RPSTL pages -> {len(batch)} NSN records ({len(set(b[0] for b in batch))} distinct NSNs)")
    return len(batch)

_HW_SEED = [
    # (size, series, major_in, major_mm, tpi_or_pitch, tap_drill, torque_ref_lbft)  -- public-domain facts
    ("1/4-20 UNC","UNC",0.250,None,"20","#7 (.201)","8"),
    ("5/16-18 UNC","UNC",0.3125,None,"18","F (.257)","17"),
    ("3/8-16 UNC","UNC",0.375,None,"16","5/16 (.3125)","30"),
    ("7/16-14 UNC","UNC",0.4375,None,"14","U (.368)","50"),
    ("1/2-13 UNC","UNC",0.500,None,"13","27/64 (.4219)","75"),
    ("9/16-12 UNC","UNC",0.5625,None,"12","31/64 (.4844)","110"),
    ("5/8-11 UNC","UNC",0.625,None,"11","17/32 (.5312)","150"),
    ("3/4-10 UNC","UNC",0.750,None,"10","21/32 (.6562)","270"),
    ("7/8-9 UNC","UNC",0.875,None,"9","49/64 (.7656)","430"),
    ("1-8 UNC","UNC",1.000,None,"8","7/8 (.875)","640"),
    ("1/4-28 UNF","UNF",0.250,None,"28","#3 (.213)","10"),
    ("5/16-24 UNF","UNF",0.3125,None,"24","I (.272)","19"),
    ("3/8-24 UNF","UNF",0.375,None,"24","Q (.332)","35"),
    ("1/2-20 UNF","UNF",0.500,None,"20","29/64 (.4531)","85"),
    ("5/8-18 UNF","UNF",0.625,None,"18","37/64 (.5781)","170"),
    ("3/4-16 UNF","UNF",0.750,None,"16","11/16 (.6875)","300"),
    ("M6x1.0","metric",None,6.0,"1.0","5.0 mm","7"),
    ("M8x1.25","metric",None,8.0,"1.25","6.8 mm","18"),
    ("M10x1.5","metric",None,10.0,"1.5","8.5 mm","37"),
    ("M12x1.75","metric",None,12.0,"1.75","10.2 mm","64"),
    ("M14x2.0","metric",None,14.0,"2.0","12.0 mm","100"),
    ("M16x2.0","metric",None,16.0,"2.0","14.0 mm","160"),
]

def _iter_tabular(path):
    """Yield dict rows from a .csv or .xlsx/.xlsm file (streaming, for large extracts)."""
    ext = os.path.splitext(path)[1].lower()
    if ext in (".xlsx", ".xlsm"):
        try:
            from openpyxl import load_workbook
        except Exception:
            log("enrich: openpyxl not installed -- run `pip install openpyxl`, or save the file as CSV and use --gsa file.csv")
            return
        ws = load_workbook(path, read_only=True, data_only=True).active
        it = ws.iter_rows(values_only=True)
        try:
            header = [("" if c is None else str(c)).strip() for c in next(it)]
        except StopIteration:
            return
        for r in it:
            yield {header[i]: ("" if v is None else str(v)) for i, v in enumerate(r) if i < len(header)}
    else:
        import csv as _csv
        with open(path, encoding="utf-8", errors="replace", newline="") as fh:
            for row in _csv.DictReader(fh):
                yield row

def rollback(con, confirm=False):
    """Reverse the additive reference enrichment + structured-parts extraction (R1 rollback).
    Drops the external reference tables and clears the extracted parts; the index returns to its
    pre-enrichment search behavior. Additive columns/migrations remain (harmless, backwards-compatible).
    OCR-filled page text is NOT touched (it only ADDED text to blank pages -- R6)."""
    n_ref = n_log = n_hw = n_parts = 0
    try: n_ref = con.execute("SELECT COUNT(*) FROM ref_nsn").fetchone()[0]
    except sqlite3.OperationalError: pass
    try: n_log = con.execute("SELECT COUNT(*) FROM ref_nsn_log").fetchone()[0]
    except sqlite3.OperationalError: pass
    try: n_hw = con.execute("SELECT COUNT(*) FROM ref_hardware").fetchone()[0]
    except sqlite3.OperationalError: pass
    try: n_parts = con.execute("SELECT COUNT(*) FROM parts WHERE confidence IS NOT NULL").fetchone()[0]
    except sqlite3.OperationalError: pass
    log(f"rollback would remove: ref_nsn={n_ref}, ref_nsn_log={n_log}, ref_hardware={n_hw}, extracted parts={n_parts}")
    if not confirm:
        log("DRY RUN -- nothing changed. Re-run with --yes to actually roll back."); return
    for tbl in ("ref_nsn", "ref_nsn_log", "ref_hardware"):
        try: con.execute(f"DROP TABLE IF EXISTS {tbl}")
        except sqlite3.OperationalError as e: log(f"  ({tbl}: {e})")
    try: con.execute("DELETE FROM parts WHERE confidence IS NOT NULL")
    except sqlite3.OperationalError: pass
    con.commit()
    log("ROLLED BACK: enrichment + extracted parts removed. Search/sheet behavior restored to pre-enrichment.")

def enrich_flis(con, folder):
    """Ingest the DLA FLIS Reading Room table extracts (NIIN-keyed), pure-Python streaming (Windows-ok):
      V_FLIS_IDENTIFICATION (NIIN->INC) + P_H6_PICK (INC->item name); V_FLIS_PART (part#/CAGE);
      V_FLIS_MANAGEMENT (AAC + unit price); V_CHARACTERISTICS (aggregated size/thread/material);
      V_FLIS_CANCELLED_NIIN (status/replacement, kept per R6). Filters to in-index NIINs; append-only."""
    import csv as _csv
    def find(*names):
        for nm in names:
            p = os.path.join(folder, nm)
            if os.path.exists(p): return p
        return None
    nsns = set()
    for t in ("documents", "parts"):
        try:
            for (n,) in con.execute(f"SELECT DISTINCT nsn FROM {t} WHERE nsn IS NOT NULL AND nsn<>''"): nsns.add(n.strip())
        except sqlite3.OperationalError: pass
    niin2nsn = {}
    for n in nsns:
        d = re.sub(r"\D", "", n)
        if len(d) >= 13: niin2nsn[d[4:13]] = n
    if not niin2nsn:
        log("enrich_flis: no NSNs in the index to match"); return 0
    niinset = set(niin2nsn)
    log(f"enrich_flis: matching {len(niinset)} index NIINs against FLIS files in {folder} (streaming; large files take a few minutes)")
    def stream(path):
        if not path: return
        with open(path, encoding="utf-8", errors="replace", newline="") as fh:
            rd = _csv.reader(fh); next(rd, None)
            for r in rd: yield r
    inc2name = {}
    for r in (stream(find("P_H6_PICK.CSV")) or []):
        if len(r) >= 2: inc2name[r[0].strip().zfill(5)] = r[1].strip()
    name = {}; part = {}; cage = {}; aac = {}; price = {}; char = {}; cancel = {}
    niin_inc = {}; cage_company = {}; colloq = {}; alt = {}
    for r in (stream(find("V_FLIS_IDENTIFICATION.CSV")) or []):
        if len(r) >= 2 and r[0].strip() in niinset:
            inc = r[1].strip().zfill(5); niin_inc[r[0].strip()] = inc
            name.setdefault(r[0].strip(), inc2name.get(inc, ""))
    for r in (stream(find("V_FLIS_PART.CSV")) or []):
        k = r[0].strip() if r else ""
        if len(r) >= 3 and k in niinset and k not in part: part[k] = r[1].strip(); cage[k] = r[2].strip()
    for r in (stream(find("V_FLIS_MANAGEMENT.CSV")) or []):
        k = r[0].strip() if r else ""
        if len(r) >= 9 and k in niinset and k not in aac:
            aac[k] = r[3].strip(); up = re.sub(r"^0+", "", r[8].strip()) or "0"
            try: price[k] = f"{float(up):,.2f}"
            except Exception: pass
    for r in (stream(find("V_CHARACTERISTICS.CSV")) or []):
        if len(r) >= 4 and r[0].strip() in niinset: char.setdefault(r[0].strip(), []).append(f"{r[2].strip()}: {r[3].strip()}")
    for r in (stream(find("V_FLIS_CANCELLED_NIIN.CSV")) or []):
        if len(r) >= 4 and r[0].strip() in niinset:
            cancel[r[0].strip()] = f"status {r[3].strip()}" + (f", repl NIIN {r[2].strip()}" if r[2].strip() else "")
    # CAGE -> manufacturer name (who actually makes the part); only the CAGE codes we reference.
    needed_cages = set(v for v in cage.values() if v)
    if needed_cages:
        for r in (stream(find("P_CAGE.CSV")) or []):  # CAGE_CODE,CAGE_STATUS,TYPE,CAO,COMPANY,CITY,STATE,...
            c0 = r[0].strip() if r else ""
            if len(r) >= 5 and c0 in needed_cages and c0 not in cage_company:
                loc = ", ".join(x for x in [(r[5].strip() if len(r) > 5 else ""), (r[6].strip() if len(r) > 6 else "")] if x)
                cage_company[c0] = r[4].strip() + ((" (" + loc + ")") if loc else "")
    # INC -> colloquial / common name (so 'battery', 'wrench', etc. are recognisable).
    needed_incs = set(niin_inc.values())
    if needed_incs:
        for r in (stream(find("V_COLLOQUIAL_NAME.CSV")) or []):  # INC,RELATED_INC,COLLOQUIAL_NAME
            if len(r) >= 3 and r[0].strip().zfill(5) in needed_incs and r[2].strip():
                colloq.setdefault(r[0].strip().zfill(5), r[2].strip())
    # FLIS standardization -> interchangeable / related NSNs (kept in alt_parts).
    for r in (stream(find("V_FLIS_STANDARDIZATION.CSV")) or []):  # NIIN,RELATED_NSN,ISC,...
        if len(r) >= 2 and r[0].strip() in niinset and r[1].strip():
            alt.setdefault(r[0].strip(), []).append(r[1].strip())
    SRC = "PUB LOG (DLA FLIS Reading Room, publicly releasable)"
    URL = "https://www.dla.mil/Information-Operations/FLIS-Data-Electronic-Reading-Room/"
    n = 0
    for niin, nsn in niin2nsn.items():
        itnm = name.get(niin, ""); pno = part.get(niin, ""); cg = cage.get(niin, "")
        ac = aac.get(niin, ""); pr = price.get(niin, ""); ch = "; ".join(char.get(niin, [])[:12])
        subs = cancel.get(niin, "")
        mfr = cage_company.get(cg, "") if cg else ""
        coll = colloq.get(niin_inc.get(niin, ""), "")
        altp = "; ".join(list(dict.fromkeys(alt.get(niin, [])))[:20])
        desc = "; ".join(x for x in [
            ("Made by " + mfr + " (CAGE " + cg + ")") if mfr else "",
            ("Also called: " + coll) if coll else "",
            ("Unit price $" + pr) if pr else ""] if x)
        if not any([itnm, pno, cg, ac, ch, subs, altp]): continue
        con.execute("INSERT INTO ref_nsn_log(nsn,item_name,description,part_no,cagec,characteristics,aac,substitutes,alt_parts,source,source_url,fetched_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,datetime('now'))",
                    (nsn, itnm, desc, pno, cg, ch, ac, subs, altp, SRC, URL))
        con.execute("INSERT INTO ref_nsn(nsn,item_name,description,part_no,cagec,characteristics,aac,substitutes,alt_parts,source,source_url,fetched_at,official) VALUES(?,?,?,?,?,?,?,?,?,?,?,datetime('now'),1) "
                    "ON CONFLICT(nsn) DO UPDATE SET "
                    "item_name=COALESCE(NULLIF(excluded.item_name,''),item_name),description=COALESCE(NULLIF(excluded.description,''),description),"
                    "part_no=COALESCE(NULLIF(excluded.part_no,''),part_no),cagec=COALESCE(NULLIF(excluded.cagec,''),cagec),"
                    "characteristics=COALESCE(NULLIF(excluded.characteristics,''),characteristics),aac=COALESCE(NULLIF(excluded.aac,''),aac),"
                    "substitutes=COALESCE(NULLIF(excluded.substitutes,''),substitutes),alt_parts=COALESCE(NULLIF(excluded.alt_parts,''),alt_parts),source=excluded.source,source_url=excluded.source_url,fetched_at=excluded.fetched_at",
                    (nsn, itnm, desc, pno, cg, ch, ac, subs, altp, SRC, URL))
        n += 1
    con.commit()
    log(f"enrich_flis: enriched {n} NSNs from the FLIS Reading Room catalog (append-only, R6)")
    return n

def enrich(con, gsa_csv=None, publog_csv=None, publog_dir=None):
    """One-time ONLINE -> OFFLINE reference enrichment, kept separate and fully cited. The running
    engine never goes online; this is a one-shot filler you run by hand (ideally on a connected
    machine, then copy the DB back).
    (1) Public-domain standard-hardware dimensions seed (FED-STD-H28). (2) Optional official GSA NSN
    Extract CSV, ingested ONLY for NSNs already in the index. The engine stays offline after."""
    SRC = "FED-STD-H28 (public domain) + standard fastener references"
    URL = "https://everyspec.com/FED-STD/FED-STD-H28B_56183/"
    con.execute("DELETE FROM ref_hardware")
    con.executemany(
        "INSERT INTO ref_hardware(size,series,major_in,major_mm,tpi_or_pitch,tap_drill,torque_ref_lbft,source,source_url,fetched_at) "
        "VALUES(?,?,?,?,?,?,?,?,?,datetime('now'))",
        [(s, se, mi, mm, tp, td, tq, SRC, URL) for (s, se, mi, mm, tp, td, tq) in _HW_SEED])
    con.commit()
    log(f"enrich: loaded {len(_HW_SEED)} public-domain hardware reference rows (torque = general reference; TM value governs)")
    if not gsa_csv and not publog_csv:
        log("enrich: hardware reference loaded; no --gsa/--publog extract given, so NSN ingest skipped. Done."); return
    idx = set()
    for (n,) in con.execute("SELECT DISTINCT nsn FROM documents WHERE nsn IS NOT NULL AND nsn<>''"): idx.add(n.strip())
    for (n,) in con.execute("SELECT DISTINCT nsn FROM parts WHERE nsn IS NOT NULL AND nsn<>''"): idx.add(n.strip())
    log(f"enrich: {len(idx)} distinct NSNs in the index to match against the extract(s)")

    def _nrm(raw):
        d = re.sub(r"\D", "", raw or "")
        return f"{d[0:4]}-{d[4:6]}-{d[6:9]}-{d[9:13]}" if len(d) >= 13 else (raw or "").strip()
    def _g(row, *names):
        for nm in names:
            v = row.get(nm)
            if v not in (None, ""): return str(v).strip()
        return ""

    if gsa_csv:
        if not os.path.exists(gsa_csv):
            log(f"enrich: GSA file not found at {gsa_csv}")
        else:
            SRCN = "GSA National Stock Number Extract (data.gov, CC0)"
            URLN = "https://catalog.data.gov/dataset/national-stock-number-extract"
            added = 0
            for row in _iter_tabular(gsa_csv):
                nsn = _nrm(_g(row, "NSN","nsn","NationalStockNumber","National Stock Number"))
                if not nsn or nsn not in idx: continue
                name = _g(row, "ItemName","Item Name","ITEM_NAME","Item Description","Description")
                desc = _g(row, "LongDescription","Description","Item Description")
                price = _g(row, "Price","UnitPrice","GSA Price","Unit Price")
                con.execute("INSERT INTO ref_nsn_log(nsn,item_name,description,gsa_price,source,source_url,fetched_at) VALUES(?,?,?,?,?,?,datetime('now'))", (nsn,name,desc,price,SRCN,URLN))
                con.execute("INSERT INTO ref_nsn(nsn,item_name,description,gsa_price,source,source_url,fetched_at,official) VALUES(?,?,?,?,?,?,datetime('now'),1) "
                            "ON CONFLICT(nsn) DO UPDATE SET item_name=excluded.item_name,description=excluded.description,gsa_price=excluded.gsa_price,source=excluded.source,source_url=excluded.source_url,fetched_at=excluded.fetched_at", (nsn,name,desc,price,SRCN,URLN))
                added += 1
            con.commit(); log(f"enrich: GSA extract -> {added} NSN versions appended (R6: history retained)")

    URLP = "https://www.dla.mil/Information-Operations/FLIS-Data-Electronic-Reading-Room/"
    def _ingest_publog(path):
        """Ingest one PUB LOG Reading Room CSV/XLSX (Identification / Reference / Characteristics /
        Management / History / H-Series). Flexible columns; merges fields per NSN without clobbering
        values another file already supplied. Append-only log (R6)."""
        if not os.path.exists(path):
            log(f"enrich: PUB LOG file not found at {path}"); return 0
        src = "PUB LOG " + os.path.basename(path) + " (DLA FLIS Reading Room, publicly releasable)"
        n = 0
        for row in _iter_tabular(path):
            nsn = _nrm(_g(row, "NSN","nsn","NATIONAL_STOCK_NUMBER","National Stock Number"))
            if not nsn:
                fsc = _g(row, "FSC","FSC_CD","FSC_CODE"); niin = _g(row, "NIIN","NIIN_CD")
                if fsc and niin: nsn = _nrm(fsc + niin)
            if not nsn or nsn not in idx: continue
            name = _g(row, "ITEM_NAME","Item_Name","ItemName","Item Name","INC_ITEM_NAME","NAME")
            part = _g(row, "PART_NUMBER","PARTNBR","PART_NBR","Part_Number","PartNumber","REFERENCE_NUMBER","REF_NUM","Reference Number")
            cage = _g(row, "CAGE","CAGEC","CAGE_CD","Cage")
            char = _g(row, "CHARACTERISTICS","CLEAR_TEXT_REPLY","Clear_Text_Reply","REQUIREMENTS_STATEMENT","Requirements_Statement","REPLY")
            aac  = _g(row, "AAC","ACQUISITION_ADVICE_CODE","Acquisition_Advice_Code")
            subs = _g(row, "SUBSTITUTES","I_AND_S","INTERCHANGEABILITY","INTERCHANGEABLE_NSN","Interchangeable")
            con.execute("INSERT INTO ref_nsn_log(nsn,item_name,part_no,cagec,characteristics,aac,substitutes,source,source_url,fetched_at) VALUES(?,?,?,?,?,?,?,?,?,datetime('now'))",
                        (nsn,name,part,cage,char,aac,subs,src,URLP))
            con.execute("INSERT INTO ref_nsn(nsn,item_name,part_no,cagec,characteristics,aac,substitutes,source,source_url,fetched_at,official) VALUES(?,?,?,?,?,?,?,?,?,datetime('now'),1) "
                        "ON CONFLICT(nsn) DO UPDATE SET "
                        "item_name=COALESCE(NULLIF(excluded.item_name,''),item_name),"
                        "part_no=COALESCE(NULLIF(excluded.part_no,''),part_no),"
                        "cagec=COALESCE(NULLIF(excluded.cagec,''),cagec),"
                        "characteristics=COALESCE(NULLIF(excluded.characteristics,''),characteristics),"
                        "aac=COALESCE(NULLIF(excluded.aac,''),aac),"
                        "substitutes=COALESCE(NULLIF(excluded.substitutes,''),substitutes),"
                        "source=excluded.source,source_url=excluded.source_url,fetched_at=excluded.fetched_at",
                        (nsn,name,part,cage,char,aac,subs,src,URLP))
            n += 1
        con.commit(); log(f"enrich: PUB LOG {os.path.basename(path)} -> {n} NSN rows merged (R6 append + non-clobbering)")
        return n
    if publog_csv:
        _ingest_publog(publog_csv)
    if publog_dir:
        flis = any(os.path.exists(os.path.join(publog_dir, x)) for x in ("V_FLIS_PART.CSV", "V_FLIS_IDENTIFICATION.CSV", "V_CHARACTERISTICS.CSV"))
        if flis:
            enrich_flis(con, publog_dir)   # DLA FLIS Reading Room table extracts (NIIN-keyed)
        else:
            import glob
            files = sorted(set(glob.glob(os.path.join(publog_dir, "*.csv")) + glob.glob(os.path.join(publog_dir, "*.CSV")) + glob.glob(os.path.join(publog_dir, "*.xlsx"))))
            if not files: log(f"enrich: no .csv/.xlsx files found in {publog_dir}")
            for fp in files: _ingest_publog(fp)

def main():
    here = os.path.dirname(os.path.abspath(__file__))
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["migrate","crawl","ocr","ocrall","prefilter","prioritize","parts","enrich","rollback","run","status","search","cleanup","prune"])
    ap.add_argument("query", nargs="?", default="")
    ap.add_argument("--root", default=os.environ.get("VIEWER_ROOT",""))
    ap.add_argument("--db", default=os.environ.get("VIEWER_DB", os.path.join(here,"..","index","viewer.db")))
    ap.add_argument("--limit", type=int, default=200)
    ap.add_argument("--ocr-limit", type=int, default=100000)
    ap.add_argument("--workers", type=int, default=max(1,(os.cpu_count() or 2)))
    ap.add_argument("--max-files", type=int, default=0)
    ap.add_argument("--max-seconds", type=int, default=0)
    ap.add_argument("--gpu", action="store_true", help="use GPU (CUDA) for OCR; CPU fallback if unavailable")
    ap.add_argument("--dpi", type=int, default=200, help="OCR render DPI (lower = faster on weak hardware)")
    ap.add_argument("--adaptive", action="store_true", help="adaptive DPI: render sparse pages lower (faster). Off by default so accuracy is unchanged.")
    ap.add_argument("--gsa", default="", help="path to the official GSA NSN Extract CSV/XLSX (for `enrich`)")
    ap.add_argument("--publog", default="", help="path to a single PUB LOG (DLA) CSV/XLSX (for `enrich`)")
    ap.add_argument("--publog-dir", dest="publog_dir", default="", help="folder of extracted PUB LOG Reading Room CSVs (Identification/Reference/Characteristics/Management/History/...)")
    ap.add_argument("--yes", action="store_true", help="confirm a destructive action (e.g. `rollback`, `prune`)")
    ap.add_argument("--missing-threshold", type=float, default=0.5, help="`prune` abort threshold: max fraction of indexed documents allowed to be missing before refusing (default 0.5 = 50%%)")
    args = ap.parse_args()
    global OCR_DPI, USE_CUDA, ADAPTIVE_DPI
    OCR_DPI = args.dpi; USE_CUDA = args.gpu
    if getattr(args, "adaptive", False): ADAPTIVE_DPI = True
    os.makedirs(os.path.dirname(os.path.abspath(args.db)), exist_ok=True)
    con = connect(args.db); migrate(con, os.path.join(here,"migrations"), db_path=args.db)
    if args.cmd == "migrate": pass
    elif args.cmd == "crawl": crawl(con, args.root, args.max_files, args.max_seconds)
    elif args.cmd == "ocr": ocr(con, args.limit, args.workers)
    elif args.cmd == "prioritize": prioritize(con)
    elif args.cmd == "parts": extract_parts(con)
    elif args.cmd == "enrich": enrich(con, args.gsa or None, args.publog or None, args.publog_dir or None)
    elif args.cmd == "rollback": rollback(con, args.yes)
    elif args.cmd == "prefilter": prefilter(con, args.limit if args.limit and args.limit>200 else 100000)
    elif args.cmd == "ocrall":
        prioritize(con)
        while ocr(con, args.limit, args.workers) > 0: pass
        extract_parts(con)   # refresh the structured parts index after OCR adds pages
    elif args.cmd == "run":
        crawl(con, args.root)
        while ocr(con, 200, args.workers) > 0 and args.ocr_limit > 0: args.ocr_limit -= 200
        extract_parts(con)
    elif args.cmd == "status": status(con)
    elif args.cmd == "search": search(con, args.query)
    elif args.cmd == "cleanup": cleanup(con)
    elif args.cmd == "prune": prune(con, args.root, confirm=args.yes, missing_threshold=args.missing_threshold,
                                     index_dir=os.path.dirname(os.path.abspath(args.db)))
    con.close()

if __name__ == "__main__": main()
