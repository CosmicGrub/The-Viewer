#!/usr/bin/env python3
"""Ground-truth probe for the FIGURES-FIRST 3-D library (v0.82.0). Read-only. RUN ON WINDOWS (host).

Replicates EXACTLY what the server's threed_list(figures_only=True) does, so we can see -- without a browser --
whether /api/threed returns real cards with images, or comes back empty (which would explain "nothing changes").
Writes index/diag_threed.txt.
"""
import os, sqlite3, sys, glob
HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.abspath(os.path.join(HERE, "..", "index", "viewer.db"))
FIGDIR = os.path.join(os.path.dirname(DB), "figcache")
out = []
def p(s=""):
    print(s); out.append(str(s))

def main():
    if not os.path.exists(DB):
        p("[ERROR] index not found: %s" % DB); return 1
    try:
        con = sqlite3.connect("file:%s?mode=ro" % DB, uri=True)
    except Exception:
        con = sqlite3.connect("file:%s?immutable=1" % DB, uri=True)
    con.row_factory = sqlite3.Row

    def one(sql, a=()):
        try: return con.execute(sql, a).fetchone()[0]
        except Exception as e: return "ERR(%s)" % e

    p("=== DB ===")
    p("path: %s" % DB)
    # which tables exist
    tabs = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    p("tables: %s" % ", ".join(sorted(tabs)))
    p("")

    # parts schema + the counts the WHERE clause depends on
    p("=== parts table ===")
    try:
        cols = [r[1] for r in con.execute("PRAGMA table_info(parts)").fetchall()]
        p("columns: %s" % ", ".join(cols))
    except Exception as e:
        p("PRAGMA failed: %s" % e); cols = []
    p("rows total .......................... %s" % one("SELECT COUNT(*) FROM parts"))
    p("fig_no IS NOT NULL .................. %s" % one("SELECT COUNT(*) FROM parts WHERE fig_no IS NOT NULL"))
    p("nsn non-empty ...................... %s" % one("SELECT COUNT(*) FROM parts WHERE COALESCE(TRIM(nsn),'')<>''"))
    p("fig_no NOT NULL *AND* nsn non-empty  %s   <-- the figures-first WHERE clause" %
      one("SELECT COUNT(*) FROM parts WHERE fig_no IS NOT NULL AND COALESCE(TRIM(nsn),'')<>''"))
    p("distinct such NSNs ................. %s" % one(
      "SELECT COUNT(DISTINCT nsn) FROM parts WHERE fig_no IS NOT NULL AND COALESCE(TRIM(nsn),'')<>''"))
    # show what fig_no / nsn actually look like in a few rows (are they really populated?)
    p("")
    p("sample parts rows (any 6):")
    try:
        for r in con.execute("SELECT nsn, fig_no, fig_title, document_id, page FROM parts LIMIT 6").fetchall():
            p("   nsn=%r fig_no=%r doc=%r page=%r title=%r" % (r["nsn"], r["fig_no"], r["document_id"], r["page"], (r["fig_title"] or "")[:40]))
    except Exception as e:
        p("   sample failed: %s" % e)
    p("")

    # EXACT server query (figures-first)
    p("=== EXACT /api/threed (figures_only) RESULT ===")
    wf = "p.fig_no IS NOT NULL AND COALESCE(TRIM(p.nsn),'')<>''"
    try:
        total = con.execute("SELECT COUNT(DISTINCT p.nsn) FROM parts p LEFT JOIN ref_nsn r ON r.nsn=p.nsn WHERE " + wf).fetchone()[0]
        p("total cards the page would show: %s" % total)
        rows = con.execute(
            "SELECT p.nsn AS nsn, MAX(COALESCE(NULLIF(r.item_name,''), p.fig_title)) AS item_name, "
            "MAX(p.fig_no) AS fig_no, MAX(p.document_id) AS _doc, MAX(p.page) AS _page "
            "FROM parts p LEFT JOIN ref_nsn r ON r.nsn=p.nsn WHERE " + wf +
            " GROUP BY p.nsn ORDER BY item_name LIMIT 8").fetchall()
        nimg = ncrop = 0
        for r in rows:
            doc = r["_doc"]; pg = r["_page"]
            url = ("/figcrop?doc=%s&page=%s&dpi=150" % (doc, pg)) if (doc and pg) else "(NO doc/page -> NO image)"
            if doc and pg: nimg += 1
            cp = os.path.join(FIGDIR, "%s_%s_150.png" % (doc, pg))
            ondisk = os.path.exists(cp)
            if ondisk: ncrop += 1
            p("  - %s  %-26s fig=%s  %s  crop_on_disk=%s" % (
                r["nsn"], (r["item_name"] or "(no name)")[:26], r["fig_no"], url, "YES" if ondisk else "no(render on demand)"))
        p("")
        p("of the 8 shown: %d have an image_url, %d already have the crop PNG cached" % (nimg, ncrop))
    except Exception as e:
        p("[ERROR] figures query failed: %s" % e)
    p("")

    # figcache dir
    n = len(glob.glob(os.path.join(FIGDIR, "*.png"))) if os.path.isdir(FIGDIR) else 0
    p("figcache PNG files on disk: %d  (%s)" % (n, FIGDIR))
    p("")

    # served-file identity: is the threed.html the server reads the v0.82 one?
    p("=== served file identity ===")
    th = os.path.join(HERE, "ui", "threed.html")
    try:
        txt = open(th, "r", encoding="utf-8").read()
        p("threed.html size: %d bytes" % len(txt))
        for marker in ["working examples", "id=\"showall\"", "all=1", "image_url"]:
            p("  contains %-18r : %s" % (marker, marker in txt))
    except Exception as e:
        p("could not read threed.html: %s" % e)

    con.close()
    try:
        open(os.path.join(os.path.dirname(DB), "diag_threed.txt"), "w", encoding="utf-8").write("\n".join(out))
        p("\n[saved to index/diag_threed.txt]")
    except Exception as e:
        p("save failed: %s" % e)
    return 0

if __name__ == "__main__":
    sys.exit(main())
