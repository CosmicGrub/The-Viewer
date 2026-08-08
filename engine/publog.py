"""publog.py -- read-only query layer over the PUBLOG/FLIS sidecar (index/publog.db, built host-side by
build_publog.py). Gives the running app AUTHORITATIVE, OFFLINE federal-catalog data for an NSN / NIIN /
manufacturer part number: nomenclature, FSC class title, part numbers + the CAGE (vendor) behind each,
item CHARACTERISTICS (the real basis for telling look-alike parts apart), weight/cube, colloquial names,
and the cancelled/replaced-NIIN chain.

Never writes anything; if publog.db isn't built, available() is False and callers degrade gracefully
(the app keeps working exactly as before). Distinct from the corpus (TM procedures, authoritative there)
and from the Wayback enrichment (supplemental, web) -- PUBLOG is the official part-identity source and is
labelled as such. No links, fully offline (R11)."""

from __future__ import annotations
import os, sqlite3

_DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "index", "publog.db")


def db_path() -> str:
    return _DB


def available() -> bool:
    return os.path.exists(_DB) and os.path.getsize(_DB) > 0


def _con():
    con = sqlite3.connect(_DB)
    con.row_factory = sqlite3.Row
    return con


def norm_niin(s: str) -> str:
    """Accepts an NSN ('2530-01-234-5678' / '2530012345678') or a bare 9-digit NIIN, dashed or not,
    and returns the 9-char NIIN. Returns '' if it can't. v1.13: delegates to patterns.niin_of, THE
    canonical extractor (R13: ambiguous fragments -- 10-12 digits, <9 digits -- are now REFUSED
    instead of zero-padded into a guessed, possibly wrong, key)."""
    import patterns
    return patterns.niin_of(s)


def _norm_pn(s: str) -> str:
    return "".join(ch for ch in (s or "").upper() if ch.isalnum())


def lookup(nsn_or_niin: str, max_charx: int = 60) -> dict:
    """Consolidated authoritative record for a NIIN/NSN. Returns {} if not built or not found."""
    if not available():
        return {}
    niin = norm_niin(nsn_or_niin)
    if not niin:
        return {}
    con = _con()
    try:
        base = con.execute("SELECT * FROM nsn WHERE niin=? LIMIT 1", (niin,)).fetchone()
        out: dict = {"niin": niin, "found": bool(base)}
        if base:
            fsc_code = base["fsc"] or ""
            out["nsn"] = ("%s-%s-%s-%s" % (fsc_code, niin[:2], niin[2:5], niin[5:])) if fsc_code else niin
            out["fsc"] = fsc_code
            out["item_name"] = base["item_name"]
            out["inc"] = base["inc"]
            out["end_item_name"] = base["end_item_name"]
            fr = con.execute("SELECT fsg_title,fsc_title FROM fsc WHERE fsc=? LIMIT 1", (fsc_code,)).fetchone()
            if fr:
                out["fsc_title"] = fr["fsc_title"]; out["fsg_title"] = fr["fsg_title"]
            if base["inc"]:
                cn = con.execute("SELECT colloquial_name FROM colloquial WHERE inc=? LIMIT 8", (base["inc"],)).fetchall()
                out["colloquial"] = [c["colloquial_name"] for c in cn if c["colloquial_name"]]
        # part numbers + CAGE company
        parts = []
        for p in con.execute("SELECT part_number,cage_code FROM part WHERE niin=? LIMIT 40", (niin,)).fetchall():
            cage = con.execute("SELECT company,city,state,country FROM cage WHERE cage_code=? LIMIT 1",
                               (p["cage_code"],)).fetchone()
            parts.append({"part_number": p["part_number"], "cage": p["cage_code"],
                          "company": cage["company"] if cage else "",
                          "city": cage["city"] if cage else "", "state": cage["state"] if cage else ""})
        out["parts"] = parts
        # characteristics (decode MRC label where we have it)
        charx = []
        for c in con.execute("SELECT mrc,requirement,reply FROM charx WHERE niin=? LIMIT ?", (niin, max_charx)).fetchall():
            label = ""
            if c["mrc"]:
                m = con.execute("SELECT name FROM mrc WHERE mrc=? LIMIT 1", (c["mrc"],)).fetchone()
                label = m["name"] if m else ""
            charx.append({"mrc": c["mrc"], "requirement": c["requirement"] or label, "reply": c["reply"]})
        out["characteristics"] = charx
        # weight/cube
        wc = con.execute("SELECT weight,cube FROM weightcube WHERE niin=? LIMIT 1", (niin,)).fetchone()
        if wc:
            out["weight"] = _num(wc["weight"]); out["cube"] = _num(wc["cube"])
        # cancelled / replacement chain (this NIIN was replaced BY, or replaces, another)
        repl = con.execute("SELECT cancelled_niin,fsc,eff_date FROM cancelled WHERE niin=? LIMIT 6", (niin,)).fetchall()
        out["replaces"] = [{"niin": r["cancelled_niin"], "fsc": r["fsc"], "date": r["eff_date"]} for r in repl if r["cancelled_niin"]]
        back = con.execute("SELECT niin,fsc,eff_date FROM cancelled WHERE cancelled_niin=? LIMIT 6", (niin,)).fetchall()
        out["replaced_by"] = [{"niin": r["niin"], "fsc": r["fsc"], "date": r["eff_date"]} for r in back if r["niin"]]
        return out
    finally:
        con.close()


def by_part_number(pn: str, limit: int = 25) -> list:
    """Reverse lookup: a manufacturer part number -> the NIIN(s)/NSN(s) that carry it (+ item name).
    This is what a shelf-bin / hand-scanner SKU resolves against when it isn't an NSN."""
    if not available():
        return []
    norm = _norm_pn(pn)
    if len(norm) < 3:
        return []
    con = _con()
    try:
        rows = con.execute("SELECT DISTINCT niin,part_number,cage_code FROM part WHERE part_norm=? LIMIT ?",
                           (norm, limit)).fetchall()
        out = []
        for r in rows:
            nm = con.execute("SELECT fsc,item_name FROM nsn WHERE niin=? LIMIT 1", (r["niin"],)).fetchone()
            fsc = nm["fsc"] if nm else ""
            out.append({"niin": r["niin"],
                        "nsn": ("%s-%s-%s-%s" % (fsc, r["niin"][:2], r["niin"][2:5], r["niin"][5:])) if fsc else r["niin"],
                        "part_number": r["part_number"], "cage": r["cage_code"],
                        "item_name": nm["item_name"] if nm else ""})
        return out
    finally:
        con.close()


def suggest_nsn(partial: str, limit: int = 6) -> list:
    """Fuzzy 'did you mean' for a mistyped NSN/NIIN: given the digits typed, return REAL catalogued NSNs
    that share the leading digits (catches a wrong/transposed digit near the end). Fast (indexed prefix)."""
    if not available():
        return []
    digits = "".join(ch for ch in (partial or "") if ch.isdigit())
    if len(digits) < 6:
        return []
    niin = digits[-9:] if len(digits) >= 13 else digits
    con = _con()
    try:
        out = []
        # widen the prefix until we have a few candidates (7 -> 6 -> 5 leading digits)
        for plen in (7, 6, 5):
            if len(niin) < plen:
                continue
            pref = niin[:plen]
            rows = con.execute("SELECT niin,fsc,item_name FROM nsn WHERE niin GLOB ? LIMIT ?",
                               (pref + "*", limit * 2)).fetchall()
            for r in rows:
                nn = r["niin"]
                if nn == niin:
                    continue                          # exact match isn't a "did you mean"
                nsn = ("%s-%s-%s-%s" % (r["fsc"], nn[:2], nn[2:5], nn[5:])) if r["fsc"] else nn
                out.append({"niin": nn, "nsn": nsn, "item_name": r["item_name"]})
                if len(out) >= limit:
                    return out
            if out:
                break
        return out
    finally:
        con.close()


def stats() -> dict:
    if not available():
        return {"available": False}
    con = _con()
    try:
        def c(t):
            try: return con.execute("SELECT COUNT(*) FROM %s" % t).fetchone()[0]
            except Exception: return 0
        meta = {r["k"]: r["v"] for r in con.execute("SELECT k,v FROM meta").fetchall()}
        return {"available": True, "nsn": c("nsn"), "part": c("part"), "cage": c("cage"),
                "charx": c("charx"), "cancelled": c("cancelled"), "meta": meta}
    finally:
        con.close()


def _num(s):
    """PUBLOG stores weight/cube as zero-padded fixed strings ('0000015.0000'); show a clean number."""
    try:
        v = float(str(s).strip() or 0)
        return ("%g" % v) if v else ""
    except Exception:
        return (str(s) or "").strip()


# --------------------------------------------------------------------------- #
# self-test: `python publog.py`  (builds a tiny sample db from the PUBLOG      #
# folder if one is reachable; otherwise SKIPS gracefully)                      #
# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    import sys
    # norm_niin is pure and always testable
    assert norm_niin("2530-01-234-5678") == "012345678", norm_niin("2530-01-234-5678")
    assert norm_niin("012345678") == "012345678"
    assert norm_niin("5305001234567") == "001234567"
    assert norm_niin("nonsense") == ""
    print("publog norm_niin OK")

    if not available():
        # try to build a tiny sample db from a reachable PUBLOG folder so the query path is exercised
        cand = [r"C:\Users\User\Desktop\publog", "/sessions/beautiful-admiring-dirac/mnt/publog",
                os.path.join(os.path.dirname(_DB), "..", "..", "..", "publog")]
        src = next((c for c in cand if os.path.isdir(c)), None)
        if not src:
            print("publog self-test SKIPPED (no publog.db and no PUBLOG source folder reachable). "
                  "Build it host-side: BUILD-PUBLOG.bat"); sys.exit(0)
        import build_publog, tempfile
        tmp = os.path.join(tempfile.gettempdir(), "publog_sample.db")
        build_publog.build(src, tmp, sample=4000, log=lambda *a: None)
        globals()["_DB"] = tmp

    st = stats()
    assert st.get("available"), st
    print("publog sample stats:", {k: st[k] for k in ("nsn", "part", "charx") if k in st})
    # pull the first NIIN present and round-trip a lookup
    con = _con(); row = con.execute("SELECT niin FROM nsn WHERE niin!='' LIMIT 1").fetchone(); con.close()
    if row:
        rec = lookup(row["niin"])
        assert rec and rec.get("niin") == row["niin"], rec
        print("publog lookup OK -> %s | item=%r | parts=%d | charx=%d"
              % (rec.get("nsn"), rec.get("item_name"), len(rec.get("parts", [])), len(rec.get("characteristics", []))))
    print("publog self-test PASS")

# END OF FILE
