"""build_publog.py -- HOST-SIDE batch: stream the DLA PUBLOG / FLIS export CSVs into a compact,
NIIN-keyed SQLite sidecar (index/publog.db) that the running app reads for AUTHORITATIVE, OFFLINE
federal-catalog part data.

WHY: the corpus (the TMs) is authoritative for vehicle-specific *procedures*; PUBLOG/FLIS is the
official federal source for part *identity* -- nomenclature, the manufacturer part numbers behind an
NSN, the CAGE (vendor) behind each part number, the item's measured CHARACTERISTICS (the real basis
for telling look-alike parts apart), weight/cube, and the cancelled/replaced-NIIN chain. Adding it
makes /dossier and Look-Alike Parts authoritative instead of gap-filled.

SCOPE / SAFETY:
  * READ-ONLY over the PUBLOG CSVs and over the corpus (R1/R6). Writes ONLY index/publog.db (a new,
    append-only sidecar). Deleting publog.db fully removes the feature.
  * Streaming, constant-memory: every CSV is read row-by-row; indexes are built AFTER the bulk load.
  * ~17M NSNs / ~16.5M part rows -> this is a HOST job (minutes, multi-GB db). Never run it through the
    sandbox mount. Use `--sample N` to build a tiny db from the first N rows of each CSV for testing.

USAGE (host):
    python build_publog.py "C:\\Users\\User\\Desktop\\publog"            # full build
    python build_publog.py "C:\\Users\\User\\Desktop\\publog" --sample 5000   # quick test db
BUILD-PUBLOG.bat wraps this with the default source path.
"""

from __future__ import annotations
import csv, os, sqlite3, sys, time

csv.field_size_limit(1 << 24)   # some CLEAR_TEXT / DEFINITION fields are large

# ---- which CSVs feed which table. (file, table, columns-in-db, source-column-indices) ----------
# Each spec: table name, CREATE sql, source CSV, and a row-mapper (list of source col indices, or a fn).
def _niin(s):
    """v1.13: delegates to patterns.niin_of, the canonical NIIN extractor. The old inline version
    (`zfill(9)[:9]`) took the FIRST 9 digits of a 13-digit NSN -- FSC + 5 NIIN digits, a WRONG key
    (R13 wrong-key bug). Now: 13 digits -> digits[4:13]; 9 -> as-is; ambiguous fragments -> ''."""
    import patterns
    return patterns.niin_of(s)


def build(src_dir, db_path, sample=0, log=print):
    t0 = time.time()
    if os.path.exists(db_path):
        os.remove(db_path)                       # rebuildable from scratch (R1)
    con = sqlite3.connect(db_path)
    con.execute("PRAGMA journal_mode=OFF")
    con.execute("PRAGMA synchronous=OFF")
    cur = con.cursor()

    # --- schema (NIIN-keyed; NSN = FSC(4) + NIIN(9)) ---
    cur.executescript("""
    CREATE TABLE nsn(niin TEXT, fsc TEXT, inc TEXT, item_name TEXT, end_item_name TEXT, sos TEXT, cancelled_niin TEXT);
    CREATE TABLE fsc(fsc TEXT, fsg TEXT, fsg_title TEXT, fsc_title TEXT);
    CREATE TABLE part(niin TEXT, part_number TEXT, part_norm TEXT, cage_code TEXT, rncc TEXT, rnvc TEXT);
    CREATE TABLE cage(cage_code TEXT, company TEXT, city TEXT, state TEXT, country TEXT, status TEXT);
    CREATE TABLE charx(niin TEXT, mrc TEXT, requirement TEXT, reply TEXT);
    CREATE TABLE weightcube(niin TEXT, weight TEXT, cube TEXT);
    CREATE TABLE cancelled(niin TEXT, cancelled_niin TEXT, fsc TEXT, eff_date TEXT, stat TEXT);
    CREATE TABLE colloquial(inc TEXT, colloquial_name TEXT);
    CREATE TABLE mrc(mrc TEXT, name TEXT, definition TEXT);
    CREATE TABLE stdz(niin TEXT, related_nsn TEXT, isc TEXT, dt TEXT);
    CREATE TABLE moe(niin TEXT, aac TEXT, pica TEXT, sica TEXT);
    CREATE TABLE phrase(niin TEXT, phrase TEXT, tech_doc TEXT);
    CREATE TABLE h6related(inc TEXT, related_inc TEXT, item_name TEXT);
    CREATE TABLE meta(k TEXT, v TEXT);
    """)

    def stream(fname, sql, mapper, label):
        path = os.path.join(src_dir, fname)
        if not os.path.exists(path):
            log("  [skip] %s not found" % fname); return 0
        n = 0
        with open(path, "r", encoding="utf-8", errors="replace", newline="") as fh:
            r = csv.reader(fh)
            try: next(r)                          # header
            except StopIteration: return 0
            batch = []
            for row in r:
                rec = mapper(row)
                if rec is None: continue
                batch.append(rec); n += 1
                if len(batch) >= 20000:
                    cur.executemany(sql, batch); batch = []
                if sample and n >= sample: break
            if batch: cur.executemany(sql, batch)
        con.commit()
        log("  %-28s %10d rows" % (fname, n))
        return n

    def col(row, i):
        return row[i].strip() if i < len(row) and row[i] is not None else ""

    # P_FLIS_NSN: FSC,NIIN,INC,ITEM_NAME,SOS,END_ITEM_NAME,CANCELLED_NIIN
    stream("P_FLIS_NSN.CSV", "INSERT INTO nsn VALUES(?,?,?,?,?,?,?)",
           lambda r: (_niin(col(r,1)), col(r,0), col(r,2), col(r,3), col(r,5), col(r,4), _niin(col(r,6)) if col(r,6) else ""),
           "nsn")
    # P_H2_PICK: FSG,FSC,FSG_TITLE,FSC_TITLE
    stream("P_H2_PICK.CSV", "INSERT INTO fsc VALUES(?,?,?,?)",
           lambda r: (col(r,1), col(r,0), col(r,2), col(r,3)), "fsc")
    # V_FLIS_PART: NIIN,PART_NUMBER,CAGE_CODE,CAGE_STATUS,RNCC,RNVC,...
    def _part(r):
        pn = col(r,1)
        norm = "".join(ch for ch in pn.upper() if ch.isalnum())
        return (_niin(col(r,0)), pn, norm, col(r,2), col(r,4), col(r,5))
    stream("V_FLIS_PART.CSV", "INSERT INTO part VALUES(?,?,?,?,?,?)", _part, "part")
    # P_CAGE: CAGE_CODE,CAGE_STATUS,TYPE,CAO,COMPANY,CITY,STATE_PROVINCE,ZIP,COUNTRY
    stream("P_CAGE.CSV", "INSERT INTO cage VALUES(?,?,?,?,?,?)",
           lambda r: (col(r,0), col(r,4), col(r,5), col(r,6), col(r,8), col(r,1)), "cage")
    # V_CHARACTERISTICS: NIIN,MRC,REQUIREMENTS_STATEMENT,CLEAR_TEXT_REPLY
    stream("V_CHARACTERISTICS.CSV", "INSERT INTO charx VALUES(?,?,?,?)",
           lambda r: (_niin(col(r,0)), col(r,1), col(r,2), col(r,3)), "charx")
    # V_DSS_WEIGHT_AND_CUBE: NIIN,DSS_WEIGHT,DSS_CUBE
    stream("V_DSS_WEIGHT_AND_CUBE.CSV", "INSERT INTO weightcube VALUES(?,?,?)",
           lambda r: (_niin(col(r,0)), col(r,1), col(r,2)), "weightcube")
    # V_FLIS_CANCELLED_NIIN: NIIN,CANCELLED_NIIN_FSC,CANCELLED_NIIN,NIIN_STAT_CD,EFF_DATE,DEMIL
    stream("V_FLIS_CANCELLED_NIIN.CSV", "INSERT INTO cancelled VALUES(?,?,?,?,?)",
           lambda r: (_niin(col(r,0)), _niin(col(r,2)), col(r,1), col(r,4), col(r,3)), "cancelled")
    # V_COLLOQUIAL_NAME: INC,RELATED_INC,COLLOQUIAL_NAME
    stream("V_COLLOQUIAL_NAME.CSV", "INSERT INTO colloquial VALUES(?,?)",
           lambda r: (col(r,0), col(r,2)), "colloquial")
    # V_FLIS_STANDARDIZATION: NIIN,RELATED_NSN,ISC,ORIG_STDZN_DEC,DT_STDZN_DEC,NIIN_STAT_CD
    stream("V_FLIS_STANDARDIZATION.CSV", "INSERT INTO stdz VALUES(?,?,?,?)",
           lambda r: (_niin(col(r,0)), col(r,1), col(r,2), col(r,4)), "stdz")
    # V_MOE_RULE: NIIN,MOE_RL,MOE_CD,AMC,AMSC,NIMSC,DT_ASGND,IMC,IMCA,AAC,PICA,PICA_LOA,SICA,...
    stream("V_MOE_RULE.CSV", "INSERT INTO moe VALUES(?,?,?,?)",
           lambda r: (_niin(col(r,0)), col(r,9), col(r,10), col(r,12)), "moe")
    # V_FLIS_PHRASE: NIIN,MOE,USC,PHRS_CD,PHRASE_STATEMENT,ORDER_OF_USE,JUMP_TO_CODE,QPA,UM,TECH_DOC_NBR,ROW_OBS_DT
    stream("V_FLIS_PHRASE.CSV", "INSERT INTO phrase VALUES(?,?,?)",
           lambda r: (_niin(col(r,0)), col(r,4), col(r,9)), "phrase")
    # V_H6_RELATED: INC,RELATED_INC,ITEM_NAME
    stream("V_H6_RELATED.CSV", "INSERT INTO h6related VALUES(?,?,?)",
           lambda r: (col(r,0), col(r,1), col(r,2)), "h6related")

    # MRC dictionary from MRD0107.txt (fixed-width): code (cols 0-4/5) then name. Best-effort so the
    # characteristics' MRC codes can be shown with a human label. Format: <MRC><flags> <NAME>...<def>...
    mrd = os.path.join(src_dir, "MRD0107.txt")
    if os.path.exists(mrd):
        seen = {}
        with open(mrd, "r", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                code = line[:5].strip()
                if not code or len(code) < 4 or not code[0].isalpha():
                    continue
                rest = line[5:]
                # the NAME is the first run of non-space text after the leading flags/spaces
                parts = rest.split("  ")
                name = ""
                for p in parts:
                    p = p.strip()
                    if p:
                        name = p; break
                if code not in seen:
                    seen[code] = name[:120]
                if sample and len(seen) >= sample: break
        cur.executemany("INSERT INTO mrc VALUES(?,?,?)", [(k, v, "") for k, v in seen.items()])
        con.commit()
        log("  %-28s %10d codes" % ("MRD0107.txt (MRC dict)", len(seen)))

    # --- indexes AFTER bulk load (much faster) ---
    log("  building indexes ...")
    cur.executescript("""
    CREATE INDEX ix_nsn_niin ON nsn(niin);
    CREATE INDEX ix_fsc ON fsc(fsc);
    CREATE INDEX ix_part_niin ON part(niin);
    CREATE INDEX ix_part_norm ON part(part_norm);
    CREATE INDEX ix_cage ON cage(cage_code);
    CREATE INDEX ix_charx_niin ON charx(niin);
    CREATE INDEX ix_wc_niin ON weightcube(niin);
    CREATE INDEX ix_canc_niin ON cancelled(niin);
    CREATE INDEX ix_canc_old ON cancelled(cancelled_niin);
    CREATE INDEX ix_coll_inc ON colloquial(inc);
    CREATE INDEX ix_mrc ON mrc(mrc);
    CREATE INDEX ix_stdz_niin ON stdz(niin);
    CREATE INDEX ix_stdz_isc ON stdz(isc);
    CREATE INDEX ix_moe_niin ON moe(niin);
    CREATE INDEX ix_phrase_niin ON phrase(niin);
    CREATE INDEX ix_h6r_inc ON h6related(inc);
    """)
    con.commit()
    cur.execute("INSERT INTO meta VALUES('built_ts', ?)", (str(int(time.time())),))
    cur.execute("INSERT INTO meta VALUES('sample', ?)", (str(sample),))
    cur.execute("INSERT INTO meta VALUES('src', ?)", (src_dir,))
    con.commit()
    con.execute("PRAGMA optimize")
    con.close()
    dt = time.time() - t0
    log("DONE in %.1fs -> %s (%.1f MB)" % (dt, db_path, os.path.getsize(db_path) / 1e6))
    return db_path


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    sample = 0
    for a in sys.argv[1:]:
        if a.startswith("--sample"):
            try: sample = int(a.split("=", 1)[1]) if "=" in a else int(sys.argv[sys.argv.index(a) + 1])
            except Exception: sample = 5000
    src = args[0] if args else r"C:\Users\User\Desktop\publog"
    here = os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(here, "index", "publog.db")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    if not os.path.isdir(src):
        print("[ERROR] PUBLOG source folder not found: %s" % src)
        print("        Pass it as the first argument, e.g.:  python build_publog.py \"D:\\path\\to\\publog\"")
        sys.exit(2)
    print("Building PUBLOG sidecar from: %s  (sample=%s)" % (src, sample or "FULL"))
    build(src, out, sample=sample)

# END OF FILE
