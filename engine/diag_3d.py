#!/usr/bin/env python3
"""THE VIEWER -- diagnose the 3-D pipeline end to end on the LIVE data.

For a sample of the parts the 3-D library shows (ref_nsn with dimensional characteristics), print exactly what
each stage produces, so we can see WHY shapes are boxes / figures don't show:
  - item_name + a slice of characteristics
  - the SHAPE family the classifier picks (box = no recognizable shape word)
  - whether a cited FIGURE exists for that NSN (figure_for) and whether the crop PNG is actually on disk
  - the MATERIAL/colour the description parses to
Then a summary tally. Read-only. RUN ON WINDOWS (host).
"""
import os, re, sqlite3, sys, glob
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
DB = os.path.join(HERE, "..", "index", "viewer.db")


def family(name, chars=""):
    t = ((name or "") + " " + (chars or "")).upper()
    pats = [("nut", r"\bNUT\b"), ("bolt", r"BOLT|SCREW|CAPSCREW|STUD|\bSCRW\b"), ("washer", r"WASHER\b"),
            ("gasket", r"GASKET|\bSHIM\b"), ("oring", r"O-?RING|\bSEAL\b|PACKING|QUAD RING"),
            ("bearing", r"BEARING"), ("gear", r"GEAR|SPROCKET|PINION"), ("spring", r"SPRING|COIL\b"),
            ("oring", r"GROMMET|\bBAND\b|\bBELT\b|\bRING\b"),
            ("tube", r"PIPE|TUBE|TUBING|HOSE|CONDUIT|NIPPLE|FILTER|ELEMENT|CARTRIDGE|COUPLING|ADAPTER|UNION|ELBOW|FITTING|CONNECTOR|CABLE|WIRE|CORD|\bLEAD\b"),
            ("shaft", r"PIN\b|DOWEL|SHAFT|\bROD\b|SPACER|SLEEVE|BUSHING|ROLLER|\bKEY\b|WEDGE|COTTER|\bPLUG\b|\bCAP\b|VALVE|\bCOCK\b|LAMP|BULB|\bFUSE\b"),
            ("bracket", r"BRACKET|MOUNT|CLAMP|SUPPORT|PLATE|ANGLE|TERMINAL|\bLUG\b|CONTACT|RETAINER|\bCLIP\b"),
            ("battery", r"BATTERY")]
    for fam, pat in pats:
        if re.search(pat, t):
            return fam
    return "box"


def main():
    db = os.path.abspath(DB)
    out = []
    def p(s=""):
        print(s); out.append(s)
    if not os.path.exists(db):
        print("[ERROR] index not found:", db); return 1
    try:
        con = sqlite3.connect("file:%s?mode=ro" % db, uri=True); con.row_factory = sqlite3.Row
    except Exception:
        con = sqlite3.connect("file:%s?immutable=1" % db, uri=True); con.row_factory = sqlite3.Row

    # 0) sanity: do the tables/sidecars exist + have rows?
    def count(sql):
        try: return con.execute(sql).fetchone()[0]
        except Exception as e: return "ERR(%s)" % e
    p("=== TABLE COUNTS ===")
    p("ref_nsn rows ............ %s" % count("SELECT COUNT(*) FROM ref_nsn"))
    p("ref_nsn w/ characteristics %s" % count("SELECT COUNT(*) FROM ref_nsn WHERE characteristics IS NOT NULL AND characteristics<>''"))
    p("ref_nsn w/ DIAMETER/LEN .. %s" % count("SELECT COUNT(*) FROM ref_nsn WHERE upper(COALESCE(characteristics,'')) LIKE '%DIAMETER%' OR upper(COALESCE(characteristics,'')) LIKE '%LENGTH%'"))
    p("parts rows .............. %s" % count("SELECT COUNT(*) FROM parts"))
    p("parts w/ fig_no ......... %s" % count("SELECT COUNT(*) FROM parts WHERE fig_no IS NOT NULL"))
    figdir = os.path.join(os.path.dirname(db), "figcache")
    nfig = len(glob.glob(os.path.join(figdir, "*.png"))) if os.path.isdir(figdir) else 0
    p("figcache PNG files ...... %d  (%s)" % (nfig, figdir))
    p("")

    # 1) the exact set the 3-D library shows
    where = ("characteristics IS NOT NULL AND characteristics<>'' AND (upper(characteristics) LIKE '%DIAMETER%' "
             "OR upper(characteristics) LIKE '%LENGTH%' OR upper(characteristics) LIKE '%HEIGHT%' OR "
             "upper(characteristics) LIKE '%WIDTH%' OR upper(characteristics) LIKE '%THICKNESS%')")
    try:
        rows = con.execute("SELECT nsn,item_name,part_no,characteristics FROM ref_nsn WHERE " + where +
                           " ORDER BY COALESCE(NULLIF(item_name,''),nsn) LIMIT 15").fetchall()
    except Exception as e:
        p("[ERROR] threed query failed: %s" % e); con.close(); return 1
    p("=== SAMPLE OF 15 PARTS THE 3-D LIBRARY SHOWS ===")
    nbox = nfound = ncrop = nmat = 0
    # figures_feature / material_feature (with a tiny injected core)
    try:
        import types, figures_feature as ff, material_feature as mf
        core = types.ModuleType("core"); core.DB_PATH = db
        def _db():
            c = sqlite3.connect("file:%s?mode=ro" % db, uri=True); c.row_factory = sqlite3.Row; return c
        core.db = _db; ff.core = core; mf.core = core
        have_feat = True
    except Exception as e:
        p("[warn] could not import figures/material_feature: %s" % e); have_feat = False
    for r in rows:
        nm = (r["item_name"] or "").strip(); ch = r["characteristics"] or ""
        fam = family(nm, ch)
        if fam == "box": nbox += 1
        figtxt = "n/a"
        if have_feat:
            try:
                fi = ff.figure_for(r["nsn"])
                if fi.get("found"):
                    nfound += 1
                    cp = os.path.join(figdir, "%s_%s_150.png" % (fi["doc_id"], fi["page"]))
                    ondisk = os.path.exists(cp)
                    if ondisk: ncrop += 1
                    figtxt = "FOUND doc%s p%s fig%s crop=%s" % (fi["doc_id"], fi["page"], fi.get("fig_no"), "yes" if ondisk else "NO")
                else:
                    figtxt = "no cited figure for this NSN"
            except Exception as e:
                figtxt = "err %s" % e
        mattxt = ""
        if have_feat:
            try:
                m = mf.material_for(ch, nm); mattxt = m["label"]
                if m["found"]: nmat += 1
            except Exception as e:
                mattxt = "err %s" % e
        p("- %s  %-28s shape=%-7s | figure: %s | material: %s" % (r["nsn"], (nm or "(no name)")[:28], fam, figtxt, mattxt))
        p("    chars: %s" % (re.sub(r"\s+", " ", ch)[:140]))
    p("")
    p("=== SUMMARY (of 15) ===")
    p("shape=box (no recognizable shape word): %d" % nbox)
    p("has a cited figure: %d   crop PNG on disk: %d" % (nfound, ncrop))
    p("material recognized from description: %d" % nmat)
    con.close()
    try:
        with open(os.path.join(os.path.dirname(db), "diag_3d.txt"), "w", encoding="utf-8") as f:
            f.write("\n".join(out))
        p("\n[saved to index/diag_3d.txt]")
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
