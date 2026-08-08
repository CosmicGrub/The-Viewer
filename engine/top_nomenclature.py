#!/usr/bin/env python3
"""THE VIEWER -- which part nomenclature comes up the most (a battery, a specific bolt, a gasket, ...).

Reads the structured parts index (built by `viewer_ingest.py parts` from RPSTL pages) and ranks the most
common part names across the corpus. Read-only. RUN ON WINDOWS (host) -- the multi-GB live index can't be
read coherently through a sandbox mount.

It prints (and saves to ../index/MOST-COMMON-PART.txt) three views, most-useful first:
  1. Most common NOMENCLATURE (the headline answer) -- the cited RPSTL item / figure name.
  2. Most common exact NSN -- the single part that recurs the most.
  3. (optional, --flis) the official FLIS item name (INC) for the top NSNs, if PUB LOG is reachable.

  python top_nomenclature.py [--db PATH] [--n 30] [--vehicle NAME] [--flis] [--publog DIR]
"""
import os, sqlite3, sys, io

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DB = os.path.join(HERE, "..", "index", "viewer.db")
OUT_TXT = os.path.join(HERE, "..", "index", "MOST-COMMON-PART.txt")

# The cited RPSTL item name, falling back to name / figure title when nomenclature wasn't captured.
LABEL = "COALESCE(NULLIF(TRIM(nomenclature),''), NULLIF(TRIM(name),''), NULLIF(TRIM(fig_title),''), '(unnamed)')"


def _connect(db):
    """Open read-only; tolerate a live OCR writer. Fall back to immutable if a stray lock blocks us."""
    try:
        con = sqlite3.connect("file:%s?mode=ro" % db.replace("?", "%3f"), uri=True, timeout=120)
        con.execute("PRAGMA query_only=ON")
        con.execute("SELECT 1 FROM sqlite_master LIMIT 1").fetchone()
        return con
    except sqlite3.OperationalError:
        return sqlite3.connect("file:%s?immutable=1" % db.replace("?", "%3f"), uri=True, timeout=120)


def main():
    db = DEFAULT_DB; topn = 30; vehicle = None; do_flis = False; publog = None
    args = sys.argv[1:]
    for i, a in enumerate(args):
        if a == "--db" and i + 1 < len(args): db = args[i + 1]
        if a == "--n" and i + 1 < len(args):
            try: topn = int(args[i + 1])
            except Exception: pass
        if a == "--vehicle" and i + 1 < len(args): vehicle = args[i + 1]
        if a == "--flis": do_flis = True
        if a == "--publog" and i + 1 < len(args): publog = args[i + 1]
    db = os.path.abspath(db)
    if not os.path.exists(db):
        print("[ERROR] index not found: %s  (pass --db <path>)" % db); return 1

    buf = io.StringIO()
    def out(line=""):
        print(line); buf.write(line + "\n")

    con = _connect(db); con.row_factory = sqlite3.Row
    where = ""; params = []
    if vehicle:
        where = " WHERE vehicle = ? COLLATE NOCASE"; params = [vehicle]
    try:
        total = con.execute("SELECT COUNT(*) FROM parts" + where, params).fetchone()[0]
        distinct = con.execute("SELECT COUNT(DISTINCT %s) FROM parts%s" % (LABEL, where), params).fetchone()[0]
        rows = con.execute(
            "SELECT %s AS nom, COUNT(*) c, COUNT(DISTINCT nsn) nsns, COUNT(DISTINCT vehicle) veh "
            "FROM parts%s GROUP BY nom ORDER BY c DESC LIMIT ?" % (LABEL, where),
            params + [topn]).fetchall()
        nsn_rows = con.execute(
            "SELECT nsn, COUNT(*) c, COUNT(DISTINCT vehicle) veh, MAX(%s) nom "
            "FROM parts%s%s nsn IS NOT NULL AND TRIM(nsn)<>'' GROUP BY nsn ORDER BY c DESC LIMIT ?"
            % (LABEL, where, (" AND" if where else " WHERE")),
            params + [topn]).fetchall()
    except sqlite3.OperationalError as e:
        print("[ERROR] could not query 'parts' (%s).\n  Build it first:  python viewer_ingest.py parts" % e)
        return 1

    scope = (" for %s" % vehicle) if vehicle else ""
    out("=== THE VIEWER -- most common part nomenclature%s ===" % scope)
    out("    (%s part records, %s distinct nomenclatures)" % (format(total, ","), format(distinct, ",")))
    out("")
    if rows:
        top = rows[0]
        out(">>> ANSWER: the nomenclature that comes up THE MOST is")
        out(">>>   \"%s\"  --  %s records, across %d vehicle(s), %d distinct NSN(s)."
            % ((top["nom"] or "").strip(), format(top["c"], ","), top["veh"], top["nsns"]))
        out("")
    out("--- Top %d nomenclatures ---" % topn)
    out("%-4s %-46s %9s %7s %5s" % ("#", "nomenclature", "records", "NSNs", "vehs"))
    out("-" * 75)
    for i, r in enumerate(rows, 1):
        out("%-4d %-46s %9s %7d %5d" % (i, (r["nom"] or "")[:46], format(r["c"], ","), r["nsns"], r["veh"]))

    out("")
    out("--- Top %d exact NSNs (the single recurring part) ---" % topn)
    out("%-4s %-18s %9s %5s  %s" % ("#", "NSN", "records", "vehs", "nomenclature"))
    out("-" * 75)
    for i, r in enumerate(nsn_rows, 1):
        out("%-4d %-18s %9s %5d  %s" % (i, r["nsn"], format(r["c"], ","), r["veh"], (r["nom"] or "")[:40]))

    if do_flis:
        try:
            _flis_names(out, nsn_rows, publog)
        except Exception as e:
            out("\n[FLIS lookup skipped: %s]" % e)

    con.close()
    try:
        with open(OUT_TXT, "w", encoding="utf-8") as f:
            f.write(buf.getvalue())
        out("\n[saved to %s]" % os.path.abspath(OUT_TXT))
    except Exception as e:
        out("\n[could not save txt: %s]" % e)
    return 0


def _flis_names(out, nsn_rows, publog):
    """Optional: resolve the official FLIS item name (INC -> H6 name) for the top NSNs from PUB LOG CSVs."""
    import csv, glob
    base = publog or os.path.join(os.path.expanduser("~"), "Desktop", "publog")
    if not os.path.isdir(base):
        out("\n[FLIS: PUB LOG dir not found at %s -- pass --publog DIR]" % base); return
    out("\n--- Official FLIS item names for the top NSNs (PUB LOG) ---")

    def find(*names):
        for n in names:
            g = glob.glob(os.path.join(base, "**", n), recursive=True)
            if g: return g[0]
        return None
    ident = find("V_FLIS_IDENTIFICATION.csv", "*IDENTIFICATION*.csv")
    h6 = find("P_H6_PICK.csv", "*H6*PICK*.csv")
    if not ident or not h6:
        out("[FLIS: could not locate identification/H6 CSVs under %s]" % base); return
    niins = {(r["nsn"] or "").replace("-", "")[-9:] for r in nsn_rows if r["nsn"]}
    niin_inc = {}
    with open(ident, newline="", encoding="utf-8", errors="ignore") as f:
        rd = csv.reader(f); hdr = [h.upper() for h in next(rd, [])]
        try: ni = hdr.index("NIIN"); ii = hdr.index("INC")
        except ValueError: ni, ii = 0, None
        for row in rd:
            if ni < len(row) and row[ni].replace("-", "") in niins and ii is not None and ii < len(row):
                niin_inc[row[ni].replace("-", "")] = row[ii]
    inc_name = {}
    incs = set(niin_inc.values())
    with open(h6, newline="", encoding="utf-8", errors="ignore") as f:
        rd = csv.reader(f); hdr = [h.upper() for h in next(rd, [])]
        try: ci = hdr.index("INC"); nmi = hdr.index("ITEM_NAME")
        except ValueError: ci, nmi = 0, 1
        for row in rd:
            if ci < len(row) and row[ci] in incs and nmi < len(row):
                inc_name[row[ci]] = row[nmi]
    for r in nsn_rows[:15]:
        ninn = (r["nsn"] or "").replace("-", "")[-9:]
        nm = inc_name.get(niin_inc.get(ninn, ""), "(no FLIS name)")
        out("  %-18s  %s" % (r["nsn"], nm))


if __name__ == "__main__":
    sys.exit(main())
