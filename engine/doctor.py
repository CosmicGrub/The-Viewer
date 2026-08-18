#!/usr/bin/env python3
"""THE VIEWER -- DOCTOR: one-shot health + inventory report. Deps, versions, corpus-path reachability (the #1
migration trap), coverage, cache counts, disk space, recent errors. Read-only. Writes docs/doctor_report.txt.
  python doctor.py            # full report
  python doctor.py --quick    # skip the coverage roll-up (faster)"""
import os, sys, sqlite3, shutil, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
DB = os.path.abspath(os.path.join(HERE, "..", "index", "viewer.db"))
IDX = os.path.dirname(DB)


def _dep(imp):
    try:
        __import__(imp); return True
    except Exception:
        return False


def _corpus_paths(db, n=12):
    try:
        con = sqlite3.connect("file:%s?mode=ro" % db, uri=True)
        rows = con.execute("SELECT path FROM documents WHERE COALESCE(path,'')<>'' LIMIT ?", (n,)).fetchall()
        con.close()
        res = [(r[0], os.path.exists(r[0])) for r in rows]
        return res, sum(1 for _, e in res if e), len(res)
    except Exception:
        return [], 0, 0


def main():
    quick = "--quick" in sys.argv
    L = []
    def out(s=""):
        L.append(s); print(s)

    out("THE VIEWER — DOCTOR   " + time.strftime("%Y-%m-%d %H:%M:%S"))
    out("=" * 62)
    out("index db: " + DB + ("  (present)" if os.path.exists(DB) else "  !! MISSING"))

    out("\n[dependencies]")
    for label, imp in [("PyMuPDF (fitz)", "pymupdf"), ("Pillow (PIL)", "PIL"), ("numpy", "numpy"),
                       ("OpenCV (cv2)", "cv2"), ("reportlab", "reportlab"),
                       ("rapidocr", "rapidocr_onnxruntime"), ("onnxruntime", "onnxruntime")]:
        ok = _dep(imp)
        out("  %-22s %s" % (label, "OK" if ok else "missing" + ("  (needed for vectorize/deep-zoom)" if imp == "cv2" else
                                                                 "  (needed for OCR)" if "ocr" in imp or imp == "onnxruntime" else "")))

    res, ok, tot = _corpus_paths(DB)
    out("\n[corpus paths]  %d/%d sampled documents reachable at their stored path" % (ok, tot))
    if tot and ok < tot:
        out("  !! some corpus PDFs are NOT where the index says — deep-zoom / vectorize / open-page will fail for those.")
        out("     fix: keep the corpus at the path you originally crawled from, or junction it (mklink /J). See docs/PORTING.md.")
    for p, e in res[:6]:
        out("   [%s] %s" % ("ok" if e else "MISSING", p))

    if not quick:
        try:
            import coverage
            ov = coverage.overview(DB, IDX)
            out("\n[coverage]   (version %s)" % ov.get("version"))
            out("  documents %s · pages %s · OCR %.1f%%" % (ov["corpus"]["documents"], ov["corpus"]["pages_total"], ov["ocr"]["pct"]))
            out("  CAD v3 %s / %s (%.1f%%) · schematic netlists %s · vectorized figures %s / %s (%.1f%%) · local models %s"
                % (ov["cad"]["rendered_v3"], ov["cad"]["representative_parts"], ov["cad"]["pct"],
                   ov["schematics"]["netlist_pages"], ov["vectorize"]["figures_vectorized"],
                   ov["vectorize"]["figure_pages"], ov["vectorize"]["pct"], ov["local_models"]))
        except Exception as e:
            out("\n[coverage] unavailable: %s" % e)

    out("\n[caches]  (file counts)")
    for name, suf in [("cadcache", "_v3.png"), ("veccache", ".svg"), ("schemcache", ".json"), ("figcache", ".png"), ("pagecache", ".png")]:
        d = os.path.join(IDX, name); n = 0
        try:
            with os.scandir(d) as it:
                for e in it:
                    if e.name.endswith(suf):
                        n += 1
                        if n >= 500000:
                            break
        except Exception:
            n = -1
        out("  %-12s %s" % (name, ("(none)" if n < 0 else n)))

    try:
        du = shutil.disk_usage(IDX)
        out("\n[disk]  index drive: %.1f GB free / %.1f GB total" % (du.free / 1e9, du.total / 1e9))
        if du.free < 5e9:
            out("  !! low free space (<5 GB) — the CAD/vectorize batches need room for their sidecars.")
    except Exception:
        pass

    elog = os.path.join(HERE, "logs", "server-errors.log")
    if os.path.exists(elog):
        try:
            tail = [x for x in open(elog, encoding="utf-8", errors="ignore").read().splitlines() if x.strip()][-4:]
            if tail:
                out("\n[recent server errors]  (last %d)" % len(tail))
                for t in tail:
                    out("  " + t[:120])
        except Exception:
            pass

    try:
        rp = os.path.join(os.path.dirname(IDX), "docs", "doctor_report.txt")
        open(rp, "w", encoding="utf-8").write("\n".join(L))
        out("\nwrote " + rp)
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
