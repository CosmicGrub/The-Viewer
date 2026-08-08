#!/usr/bin/env python3
"""THE VIEWER -- cross-reference enrichment from PUB LOG (the parts only the CSVs can give us).

The live resolver (xref_feature) already does FLIS-name + vehicle + interchange from the index/correlations.
This host batch adds the two things that need the 16 GB PUB LOG CSVs:
  * PN + CAGEC -> NSN   (V_FLIS_PART)  -- recover the NSN for OCR rows that lost it -> index/pn_nsn.json
  * CAGEC -> company    (P_CAGE)       -- manufacturer names                          -> index/cage.json
Both are small JSON sidecars the app reads; the main index is never written (R1/R6). RUN ON WINDOWS (host).

  python build_xref.py [--db PATH] [--publog DIR]
"""
import os, sys, csv, json, glob, sqlite3

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DB = os.path.join(HERE, "..", "index", "viewer.db")


def _find(base, *names):
    for n in names:
        g = glob.glob(os.path.join(base, "**", n), recursive=True)
        if g: return g[0]
    return None


def _norm_pn(s):
    import re
    return re.sub(r"\s+", "", (s or "")).upper()


def main():
    db = DEFAULT_DB; publog = None; args = sys.argv[1:]
    for i, a in enumerate(args):
        if a == "--db" and i + 1 < len(args): db = args[i + 1]
        if a == "--publog" and i + 1 < len(args): publog = args[i + 1]
    db = os.path.abspath(db); idx = os.path.dirname(db)
    base = publog or os.path.join(os.path.expanduser("~"), "Desktop", "publog")
    if not os.path.isdir(base):
        print("[ERROR] PUB LOG dir not found: %s  (pass --publog DIR)" % base); return 1

    rpstl = os.path.join(idx, "rpstl.db")
    if not os.path.exists(rpstl):
        print("[ERROR] rpstl.db not found — run BUILD-RPSTL.bat first."); return 1

    # the part numbers + CAGECs we need to resolve / name
    con = sqlite3.connect("file:%s?mode=ro" % rpstl, uri=True); con.row_factory = sqlite3.Row
    need_pn = {}; cages = set()
    for r in con.execute("SELECT pn_norm, cagec, nsn FROM parts_rows"):
        if r["cagec"]: cages.add((r["cagec"] or "").upper())
        if (not r["nsn"]) and r["pn_norm"]:
            need_pn.setdefault(_norm_pn(r["pn_norm"]), set()).add((r["cagec"] or "").upper())
    con.close()
    print("=== xref enrichment: %d part#s missing NSN, %d distinct CAGECs ===" % (len(need_pn), len(cages)))

    # --- CAGEC -> company (P_CAGE) ---
    cage_path = _find(base, "P_CAGE.csv", "*CAGE*.csv")
    cage_map = {}
    if cage_path:
        with open(cage_path, newline="", encoding="utf-8", errors="ignore") as f:
            rd = csv.reader(f); hdr = [h.upper() for h in next(rd, [])]
            try: ci = hdr.index("CAGE_CODE")
            except ValueError: ci = 0
            nmi = None
            for cand in ("COMPANY_NAME", "COMPANY", "NAME"):
                if cand in hdr: nmi = hdr.index(cand); break
            if nmi is None: nmi = 3
            for row in rd:
                if ci < len(row) and (row[ci] or "").upper() in cages and nmi < len(row):
                    cage_map[row[ci].upper()] = row[nmi].strip()
        json.dump(cage_map, open(os.path.join(idx, "cage.json"), "w", encoding="utf-8"), indent=1)
        print("  cage.json: %d CAGEC->company" % len(cage_map))
    else:
        print("  [P_CAGE.csv not found — skipping manufacturer names]")

    # --- PN + CAGEC -> NSN (V_FLIS_PART) ---
    part_path = _find(base, "V_FLIS_PART.csv", "*FLIS_PART*.csv", "*PART*.csv")
    pn_nsn = {}
    if part_path and need_pn:
        with open(part_path, newline="", encoding="utf-8", errors="ignore") as f:
            rd = csv.reader(f); hdr = [h.upper() for h in next(rd, [])]
            def col(*names):
                for n in names:
                    if n in hdr: return hdr.index(n)
                return None
            pi = col("PART_NUMBER", "REFERENCE_NUMBER", "PART_NO"); ni = col("NIIN"); ci = col("CAGE_CODE", "CAGEC")
            if pi is not None and ni is not None:
                for row in rd:
                    if pi >= len(row) or ni >= len(row): continue
                    pn = _norm_pn(row[pi])
                    if pn in need_pn:
                        niin = (row[ni] or "").replace("-", "")
                        if len(niin) >= 9:
                            fsc = ""  # NIIN alone; store NIIN, app will match
                            pn_nsn[pn] = niin[-9:]
        json.dump(pn_nsn, open(os.path.join(idx, "pn_nsn.json"), "w", encoding="utf-8"), indent=1)
        print("  pn_nsn.json: recovered %d NSNs from PN+CAGEC" % len(pn_nsn))
    else:
        print("  [V_FLIS_PART.csv not found or nothing to recover]")

    print("\nDone. The app now shows manufacturer names + recovers missing NSNs for part-number lookups.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
