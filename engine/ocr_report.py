#!/usr/bin/env python3
"""Generate a detailed OCR report for THE VIEWER (run anytime; auto-run when OCR completes).
Reads the index read-only and writes docs/OCR-COMPLETION-REPORT.md. Queries are thorough and run
fine on a local SSD (a per-vehicle scan may take ~a minute on a multi-GB index)."""
import sqlite3, os, re, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DB = os.path.join(ROOT, "index", "viewer.db")
OUT = os.path.join(ROOT, "docs", "OCR-COMPLETION-REPORT.md")
NSN = re.compile(r"\b\d{4}-?\d{2}-?\d{3}-?\d{4}\b")

def main():
    db = DB
    for i, a in enumerate(sys.argv[1:]):
        if a == "--db" and i+2 <= len(sys.argv[1:]): db = sys.argv[i+2]
    if not os.path.exists(db):
        print("index not found:", db); return 1
    c = sqlite3.connect("file:%s?mode=ro" % db, uri=True); c.row_factory = sqlite3.Row
    def one(q, *a):
        try: return c.execute(q, a).fetchone()[0]
        except Exception: return None

    dist = {r[0]: r[1] for r in c.execute("SELECT ocr_status, COUNT(*) FROM pages GROUP BY ocr_status")}
    pend = dist.get("pending", 0) + dist.get("running", 0)
    done = dist.get("done", 0); skip = dist.get("skipped", 0)
    scanned = pend + done + skip
    total_pages = one("SELECT COUNT(*) FROM pages") or 0
    searchable = total_pages - pend
    progress = (100.0 * (done + skip) / scanned) if scanned else 100.0
    cov = (100.0 * searchable / total_pages) if total_pages else 0

    # throughput from the runs log (kind='ocr')
    tp = ""
    try:
        rr = c.execute("SELECT SUM(ocr_done) d, MIN(started_at) s, MAX(finished_at) f, COUNT(*) n "
                       "FROM runs WHERE kind='ocr' AND ocr_done IS NOT NULL").fetchone()
        if rr and rr["d"]:
            tp = "OCR'd %s pages across %s run batches." % (f"{rr['d']:,}", rr["n"])
    except Exception: pass

    # engine marker (written by run_ocr_auto.bat)
    eng = "(unknown — see the OCR console output)"
    mk = os.path.join(ROOT, "index", "ocr_engine.txt")
    if os.path.exists(mk):
        try: eng = open(mk, encoding="utf-8").read().strip()
        except Exception: pass

    # sample wins: newly OCR'd pages that contain NSNs/part numbers (done is indexed -> fast)
    wins = []
    try:
        for r in c.execute("SELECT p.body_text, d.vehicle, d.tm_number, p.page_number "
                           "FROM pages p JOIN documents d ON d.id=p.document_id "
                           "WHERE p.ocr_status='done' AND p.char_count>0 LIMIT 4000"):
            m = NSN.search(r["body_text"] or "")
            if m:
                wins.append((m.group(0), r["vehicle"] or "?", r["tm_number"] or "?", r["page_number"]))
            if len(wins) >= 12: break
    except Exception: pass

    # failures
    failed = dist.get("failed", 0)
    fsample = []
    try:
        for r in c.execute("SELECT last_error FROM jobs WHERE stage='ocr' AND state='failed' LIMIT 5"):
            if r["last_error"]: fsample.append(r["last_error"][:120])
    except Exception: pass

    # per-vehicle table. --full = thorough searchable coverage (scans pages; ~a minute on a big
    # index, fine on a local SSD). Default = fast size table from document metadata only.
    full = "--full" in sys.argv
    veh = []; veh_mode = "coverage" if full else "size"
    try:
        if full:
            for r in c.execute(
                "SELECT d.vehicle, COUNT(*) total, "
                "SUM(CASE WHEN p.ocr_status='none' OR p.ocr_status='done' THEN 1 ELSE 0 END) searchable "
                "FROM pages p JOIN documents d ON d.id=p.document_id "
                "WHERE d.vehicle IS NOT NULL AND d.vehicle<>'' "
                "GROUP BY d.vehicle ORDER BY total DESC LIMIT 20"):
                tot = r["total"] or 0; s = r["searchable"] or 0
                veh.append((r["vehicle"], tot, s, round(100*s/tot) if tot else 0))
        else:
            for r in c.execute(
                "SELECT vehicle, COUNT(*) docs, COALESCE(SUM(page_count),0) pages FROM documents "
                "WHERE vehicle IS NOT NULL AND vehicle<>'' GROUP BY vehicle ORDER BY pages DESC LIMIT 20"):
                veh.append((r["vehicle"], r["docs"], r["pages"], None))
    except Exception: pass
    c.close()

    done_flag = (pend == 0)
    L = []
    L.append("# OCR report — THE VIEWER")
    L.append("")
    L.append("_Generated %s._  %s" % (time.strftime("%Y-%m-%d %H:%M:%S"),
             "**OCR is COMPLETE.** ✅" if done_flag else "**OCR in progress.**"))
    L.append("")
    L.append("## Headline")
    L.append("")
    L.append("| Metric | Value |")
    L.append("|---|---|")
    L.append("| OCR progress | **%.1f%%** of scanned pages |" % progress)
    L.append("| Searchable coverage | **%.1f%%** of all %s pages |" % (cov, f"{total_pages:,}"))
    L.append("| Scanned pages (OCR queue) | %s |" % f"{scanned:,}")
    L.append("| OCR'd (done) | %s |" % f"{done:,}")
    L.append("| Blank (skipped) | %s |" % f"{skip:,}")
    L.append("| Remaining (pending/running) | %s |" % f"{pend:,}")
    L.append("| Failed | %s |" % f"{failed:,}")
    L.append("| Engine | %s |" % eng)
    L.append("")
    if tp: L.append(tp); L.append("")
    L.append("## Searchable coverage by vehicle (top 20 by size)")
    L.append("")
    if veh:
        L.append("| Vehicle | Pages | Searchable | % |")
        L.append("|---|--:|--:|--:|")
        for v, tot, s, pct in veh:
            L.append("| %s | %s | %s | %d%% |" % (v, f"{tot:,}", f"{s:,}", pct))
    else:
        L.append("_(coverage scan unavailable)_")
    L.append("")
    L.append("## Sample recovered content (newly searchable NSNs)")
    L.append("")
    if wins:
        L.append("These NSNs were pulled from pages that were image-only before OCR:")
        L.append("")
        for nsn, v, tm, pg in wins:
            L.append("- `%s` — %s, %s p.%s" % (nsn, v, tm, pg))
    else:
        L.append("_(no NSN samples yet — more appear as OCR progresses)_")
    L.append("")
    if failed:
        L.append("## Failures")
        L.append("")
        L.append("%s pages failed and were logged in `jobs`. Re-running `cleanup` requeues them. Sample:" % f"{failed:,}")
        L.append("")
        for e in fsample: L.append("- `%s`" % e)
        L.append("")
    L.append("## Notes")
    L.append("")
    L.append("- OCR only **adds** text to previously-blank pages (R6) — it's outside any rollback.")
    if done_flag:
        L.append("- With OCR complete, **mirror-mode readable labels** and full search coverage are now")
        L.append("  available on every page. Take a snapshot: `engine\\run_safeguard.bat snapshot`.")
        L.append("- You can stop the daily OCR reminder — it's done.")
    else:
        L.append("- The run is resumable: `engine\\run_ocr_auto.bat` continues to 100%. Watch `/status`.")
    open(OUT, "w", encoding="utf-8").write("\n".join(L) + "\n")
    print("wrote", OUT, "(progress %.1f%%, %s pending)" % (progress, f"{pend:,}"))
    return 0

if __name__ == "__main__":
    sys.exit(main())
