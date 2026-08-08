#!/usr/bin/env python3
"""Quick CAD-batch status: how many parts have a current-version CAD image, out of the whole set, + live rate/ETA.
Read-only. RUN ON WINDOWS (host)."""
import os, sqlite3, time, glob
HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.abspath(os.path.join(HERE, "..", "index", "viewer.db"))
CDIR = os.path.join(os.path.dirname(DB), "cadcache")
try:
    import cad_render
    VER = cad_render.CAD_VERSION
except Exception:
    VER = "3"
_THREED_WHERE = ("characteristics IS NOT NULL AND characteristics<>'' AND ("
                 "upper(characteristics) LIKE '%DIAMETER%' OR upper(characteristics) LIKE '%LENGTH%' OR "
                 "upper(characteristics) LIKE '%HEIGHT%' OR upper(characteristics) LIKE '%WIDTH%' OR "
                 "upper(characteristics) LIKE '%THICKNESS%')")

def total_target():
    try:
        con = sqlite3.connect("file:%s?mode=ro" % DB, uri=True)
        q = ("SELECT COUNT(*) FROM (SELECT nsn FROM ref_nsn WHERE " + _THREED_WHERE +
             " AND COALESCE(TRIM(nsn),'')<>'' UNION "
             "SELECT nsn FROM parts WHERE fig_no IS NOT NULL AND COALESCE(TRIM(nsn),'')<>'')")
        n = con.execute(q).fetchone()[0]; con.close(); return n
    except Exception as e:
        return None

def rendered():
    return len(glob.glob(os.path.join(CDIR, "*_v%s.png" % VER)))

def bar(pct, width=42):
    fill = int(round(width*pct/100.0)); return "[" + "#"*fill + "-"*(width-fill) + "]"

def main():
    tot = total_target()
    n0 = rendered(); t0 = time.time()
    time.sleep(5)
    n1 = rendered(); dt = time.time() - t0
    rate = (n1 - n0)/dt if dt else 0
    pct = (100.0*n1/tot) if tot else 0
    print("=== THE VIEWER — CAD batch status (v%s) ===" % VER)
    print("  rendered : %d" % n1)
    if tot:
        print("  target   : %d" % tot)
        print("  %s  %.1f%%" % (bar(pct), pct))
    print("  rate     : %.0f parts/sec" % rate)
    if tot and n1 >= tot:
        print("  status   : COMPLETE (100%)")
    elif rate > 0.2:
        if tot:
            eta = (tot - n1)/rate
            print("  status   : RENDERING  ·  ETA %dm %02ds" % (eta//60, eta % 60))
        else:
            print("  status   : RENDERING (%.0f parts/sec)" % rate)
    else:
        print("  status   : idle / paused (not rendering right now — re-run RUN-CAD-BATCH.bat to continue)")
    try:
        v1 = len(glob.glob(os.path.join(CDIR, "*_v1.png")))
        v2 = len(glob.glob(os.path.join(CDIR, "*_v2.png")))
        v3 = len(glob.glob(os.path.join(CDIR, "*_v3.png")))
        print("  tiers    : legacy(v1)=%d  lite(v2)=%d  modern(v3)=%d  (target ~%s each)" % (v1, v2, v3, tot or "?"))
    except Exception:
        pass
    print("  cache    : %s" % CDIR)

if __name__ == "__main__":
    main()
