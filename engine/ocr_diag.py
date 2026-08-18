#!/usr/bin/env python3
"""One-shot OCR diagnostic: shows WHY OCR pages are failing. Prints the real traceback."""
import os, sys, sqlite3, traceback, importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, "..", "index", "viewer.db")

spec = importlib.util.spec_from_file_location("vi", os.path.join(HERE, "viewer_ingest.py"))
vi = importlib.util.module_from_spec(spec); spec.loader.exec_module(vi)

print("PyMuPDF (fitz) available:", vi.fitz is not None)
print("RapidOCR available     :", vi._have_rapid())

con = sqlite3.connect(DB, timeout=30)
# how many pending/failed by path location
# Low finding #48: the "other" bucket used to run `LIKE '_%'` -- SQL's `_` is a single-character
# wildcard, not a literal underscore, so that pattern matched almost every path (anything with at
# least one character), double-counting into "other" everything already counted in the first two
# buckets above and invalidating the whole breakdown. Fixed to an actual "doesn't match either of
# the other two" exclusion instead of a wildcard LIKE.
for label, where, args in [
    ("E:\\ native", "d.path LIKE ?", ("E:%",)),
    ("sandbox /sessions", "d.path LIKE ?", ("/sessions/%",)),
    ("other", "d.path NOT LIKE ? AND d.path NOT LIKE ?", ("E:%", "/sessions/%")),
]:
    n = con.execute("SELECT COUNT(*) FROM pages p JOIN documents d ON d.id=p.document_id "
                    "WHERE p.ocr_status IN ('pending','failed','running') AND " + where, args).fetchone()[0]
    print(f"  queued/failed pages with path {label:18}: {n}")

row = con.execute("SELECT d.path, p.page_number FROM pages p JOIN documents d ON d.id=p.document_id "
                  "WHERE p.ocr_status IN ('pending','failed','running') AND d.path LIKE 'E:%' LIMIT 1").fetchone()
if not row:
    row = con.execute("SELECT d.path, p.page_number FROM pages p JOIN documents d ON d.id=p.document_id "
                      "WHERE p.ocr_status IN ('pending','failed','running') LIMIT 1").fetchone()
print("\nTEST PAGE:", row)
if row:
    path, pno = row
    print("file exists on disk:", os.path.exists(path))
    print("--- rendering page to image ---")
    try:
        img = vi._render_png(path, pno)
        print("rendered image:", img, "exists:", os.path.exists(img))
        print("--- running RapidOCR ---")
        eng = vi._get_rapid()
        res, _ = eng(img)
        txt = "\n".join(r[1] for r in res).strip() if res else ""
        print("OCR OK. chars:", len(txt))
        print("sample:", repr(txt[:200]))
        try: os.unlink(img)
        except OSError: pass
    except Exception:
        print("\n*** EXCEPTION ***")
        traceback.print_exc()
con.close()
