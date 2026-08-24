#!/usr/bin/env python3
"""THE VIEWER -- build the RPSTL part-number sidecar (index/rpstl.db) from the OCR'd parts-list pages.

Scans the parts/RPSTL pages, parses each parts-list row (item/SMR/NSN/CAGEC/part#/nomenclature/qty) via
rpstl_feature, and -- where an NSN is present -- VALIDATES/REPAIRS the nomenclature against FLIS (the ref_nsn
enrichment table, i.e. PUB LOG). Writes a fresh sidecar; the main index is never written (R1/R6). RUN ON
WINDOWS (host) -- the multi-GB index can't be read coherently through a sandbox mount.

  python build_rpstl.py [--db PATH] [--limit N]
"""
import os, sqlite3, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import rpstl_feature as R
import safeguard

DEFAULT_DB = os.path.join(HERE, "..", "index", "viewer.db")
RPSTL_LIKE = ("upper(COALESCE(d.tm_number,'')||' '||COALESCE(d.path,'')||' '||COALESCE(d.title,'')) "
              "GLOB '*24P*' OR upper(COALESCE(d.tm_number,'')||' '||COALESCE(d.path,'')) GLOB '*RPSTL*' "
              "OR upper(COALESCE(d.tm_number,'')||' '||COALESCE(d.path,'')) GLOB '*-20P*' "
              "OR upper(COALESCE(d.path,'')) GLOB '*PARTS*'")


def _connect_ro(db):
    try:
        c = sqlite3.connect("file:%s?mode=ro" % db, uri=True); c.row_factory = sqlite3.Row
        c.execute("PRAGMA query_only=ON"); c.execute("SELECT 1 FROM sqlite_master LIMIT 1").fetchone(); return c
    except sqlite3.OperationalError:
        c = sqlite3.connect("file:%s?immutable=1" % db, uri=True); c.row_factory = sqlite3.Row; return c


def _flis_name(con, nsn):
    """Official FLIS INC item name for an NSN from the ref_nsn enrichment table, if present."""
    try:
        r = con.execute("SELECT item_name FROM ref_nsn WHERE nsn=? AND item_name IS NOT NULL AND item_name<>'' LIMIT 1",
                        (nsn,)).fetchone()
        return r["item_name"] if r else None
    except Exception:
        return None


def main():
    db = DEFAULT_DB; limit = 0; args = sys.argv[1:]
    for i, a in enumerate(args):
        if a == "--db" and i + 1 < len(args): db = args[i + 1]
        if a == "--limit" and i + 1 < len(args):
            try: limit = int(args[i + 1])
            except Exception: pass
    db = os.path.abspath(db)
    if not os.path.exists(db):
        print("[ERROR] index not found: %s" % db); return 1
    con = _connect_ro(db)
    out = os.path.join(os.path.dirname(db), "rpstl.db")

    has_flis = con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ref_nsn'").fetchone() is not None
    rows = con.execute(
        "SELECT p.document_id AS doc_id, p.page_number AS page, p.body_text AS body "
        "FROM pages p JOIN documents d ON d.id=p.document_id "
        "WHERE (" + RPSTL_LIKE + ") AND p.body_text IS NOT NULL AND length(p.body_text)>40").fetchall()
    if limit: rows = rows[:limit]
    npages = len(rows); nrows = 0; nval = 0; t0 = time.time()
    print("=== Building RPSTL sidecar from %d parts pages (FLIS validate: %s) ===" % (npages, "yes" if has_flis else "no ref_nsn"))

    # Build-to-temp-then-atomic-swap, same crash-safety contract as kg.py/build_publog.py: a transient
    # antivirus/search-indexer lock on the previous rpstl.db (or a crash mid-build) no longer takes the
    # whole batch job down with an uncaught PermissionError -- it retries the removal/swap and, on any
    # failure, leaves the last-good rpstl.db untouched (safeguard.atomic_sqlite_build).
    with safeguard.atomic_sqlite_build(out) as (w, tmp):
        w.execute("""CREATE TABLE parts_rows(id INTEGER PRIMARY KEY, pn_norm TEXT, pn_base TEXT, part_no TEXT,
          item INT, smr TEXT, nsn TEXT, cagec TEXT, nomenclature TEXT, nomen_flis TEXT, qty INT,
          fig_no TEXT, doc_id INT, page INT, confidence REAL, validated INT DEFAULT 0)""")
        batch = []
        for pi, pr in enumerate(rows, 1):
            for r in R.parse_page(pr["body"] or "", doc_id=pr["doc_id"], page=pr["page"]):
                flis = _flis_name(con, r["nsn"]) if (has_flis and r["nsn"]) else None
                nomen = r["nomenclature"]
                validated = 0
                if flis:
                    nomen = flis; validated = 1; nval += 1            # FLIS official name wins
                batch.append((R.norm_pn(r["part_no"]), R.pn_base(r["part_no"]), r["part_no"], r["item"], r["smr"],
                              r["nsn"], r["cagec"], nomen, flis, r["qty"], r["fig_no"], r["doc_id"], r["page"],
                              r["confidence"], validated))
                nrows += 1
            if pi % 200 == 0 or pi == npages:
                w.executemany("INSERT INTO parts_rows(pn_norm,pn_base,part_no,item,smr,nsn,cagec,nomenclature,"
                              "nomen_flis,qty,fig_no,doc_id,page,confidence,validated) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", batch)
                w.commit(); batch = []
                print("  %d/%d pages  %d rows  %d FLIS-validated  %.1f pg/s" %
                      (pi, npages, nrows, nval, pi / max(0.001, time.time() - t0)))
        if batch:
            w.executemany("INSERT INTO parts_rows(pn_norm,pn_base,part_no,item,smr,nsn,cagec,nomenclature,"
                          "nomen_flis,qty,fig_no,doc_id,page,confidence,validated) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", batch)
        w.execute("CREATE INDEX ix_pn ON parts_rows(pn_norm)")
        w.execute("CREATE INDEX ix_base ON parts_rows(pn_base)")
        w.execute("CREATE INDEX ix_conf ON parts_rows(confidence)")
        w.commit()
    con.close()
    print("\nDone: %d rows from %d pages -> %s" % (nrows, npages, out))
    print("  FLIS-validated nomenclature: %d" % nval)
    print("  (low-confidence rows are reviewable in the app: Part-number lookup -> Review)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
