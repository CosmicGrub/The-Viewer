#!/usr/bin/env python3
"""Measure the 3-D shape classifier against the REAL corpus, INCLUDING an NSN Federal-Supply-Class (FSC)
fallback for parts whose name is missing/generic/unclassifiable. Read-only. RUN ON WINDOWS (host).
Writes index/shape_analysis.txt. Keep family()/FSC_MAP in sync with partgeo.js."""
import os, re, sqlite3, sys, collections
HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.abspath(os.path.join(HERE, "..", "index", "viewer.db"))
out = []
def p(s=""):
    print(s); out.append(str(s))

# ---- keep in sync with partgeo.js family() ----
def family(name, chars=""):
    t = ((name or "") + " " + (chars or "")).upper()
    R = lambda pat: re.search(pat, t)
    if R(r"\bNUT\b"): return "nut"
    if R(r"\bRIVET\b"): return "rivet"
    if R(r"BOLT|SCREW|CAPSCREW|\bSTUD\b|\bSCRW\b"): return "bolt"
    if R(r"WASHER\b"): return "washer"
    if R(r"GASKET|\bSHIM\b"): return "gasket"
    if R(r"O-?RING|\bSEAL\b|PACKING|QUAD RING"): return "oring"
    if R(r"BEARING"): return "bearing"
    if R(r"GEAR|SPROCKET|PINION"): return "gear"
    if R(r"SPRING|\bCOIL\b"): return "spring"
    if R(r"\bLINK\b"): return "link"
    if R(r"\bLEVER\b|\bHANDLE\b|\bCRANK\b|\bPEDAL\b|CONTROL ARM|\bARM\b"): return "lever"
    if R(r"SWITCH|\bRELAY\b"): return "switch"
    if R(r"CIRCUIT CARD|\bCCA\b|PRINTED.*BOARD|\bBOARD\b"): return "plate"
    if R(r"AIR CLEANER|\bFILTER\b|\bCARTRIDGE\b|\bELEMENT\b|CANISTER|RESERVOIR|\bTANK\b|ACCUMULATOR|DRIER"): return "canister"
    if R(r"CYLINDER|ACTUATOR|\bMOTOR\b|\bPUMP\b|SOLENOID|COMPRESSOR|\bVALVE\b"): return "cylinder"
    if R(r"COVER|\bDOOR\b|\bPANEL\b|HATCH|\bLID\b|\bGUARD\b|SHIELD|DEFLECTOR|BEZEL"): return "cover"
    if R(r"INSULAT|\bPAD\b|CUSHION|\bMAT\b|\bSTRAP\b|WEBBING"): return "pad"
    if R(r"PIPE|TUBE|TUBING|HOSE|CONDUIT|NIPPLE|COUPLING|ADAPTER|UNION|ELBOW|FITTING|CONNECTOR|CABLE|\bWIRE\b|WIRING|HARNESS|CORD|\bLEAD\b"): return "tube"
    if R(r"GROMMET|\bBAND\b|\bBELT\b|\bRING\b"): return "oring"
    if R(r"\bPIN\b|DOWEL|\bSHAFT\b|\bROD\b|SPACER|SLEEVE|BUSHING|ROLLER|\bKEY\b|WEDGE|COTTER|\bPLUG\b|\bCAP\b|\bCOCK\b|\bLAMP\b|\bBULB\b|\bFUSE\b|STANDOFF"): return "shaft"
    if R(r"BRACKET|MOUNT|\bCLAMP\b|SUPPORT|\bANGLE\b|TERMINAL|\bLUG\b|CONTACT|RETAINER|\bCLIP\b|HINGE|LATCH|STRIKE|\bCATCH\b|\bHASP\b|\bHOOK\b"): return "bracket"
    if R(r"PLATE|MARKER|DECAL|LABEL|PLACARD|NAMEPLATE|\bTAG\b|IDENTIFICATION|ARMOR|ARMOUR|\bBUS\b|\bBAR\b"): return "plate"
    if R(r"BATTERY"): return "battery"
    return "box"

# ---- NSN Federal Supply Class -> shape (first 4 digits of the NSN). Keep in sync with partgeo.js FSC_MAP ----
FSC_MAP = {
 "5305":"bolt","5306":"bolt","5307":"bolt","5315":"shaft","5320":"rivet","5310":"nut","5311":"nut",
 "5325":"bracket","5330":"gasket","5331":"oring","5340":"bracket","5342":"bracket","5345":"washer",
 "5355":"shaft","5360":"spring","5365":"shaft","5970":"pad","5975":"box","5999":"plate",
 "3110":"bearing","3120":"bearing","3130":"bearing","3020":"gear","3010":"cylinder","3040":"lever",
 "4710":"tube","4720":"tube","4730":"tube","4820":"cylinder","4730":"tube",
 "2910":"cylinder","2915":"cylinder","2920":"cylinder","2930":"canister","2940":"canister","2990":"cover",
 "2510":"cover","2520":"cylinder","2530":"cylinder","2540":"bracket","2541":"bracket","2590":"box","2805":"cylinder",
 "5905":"shaft","5910":"shaft","5915":"shaft","5920":"shaft","5925":"switch","5930":"switch","5935":"tube",
 "5940":"bracket","5945":"switch","5950":"cylinder","5955":"shaft","5960":"shaft","5961":"shaft","5962":"plate",
 "5963":"plate","5985":"cylinder","5995":"tube","5999":"plate","6150":"tube",
 "6210":"cover","6220":"cover","6240":"shaft","6250":"shaft","6260":"shaft",
 "4010":"tube","4030":"bracket","9905":"plate","7690":"plate","9390":"pad",
 "2610":"oring","2620":"oring","2640":"oring","4130":"canister","4140":"cylinder","4320":"cylinder","4330":"canister",
 "5120":"shaft","5130":"cylinder","5133":"shaft","5136":"shaft","5210":"shaft","1005":"tube","1010":"tube",
}
FSG_MAP = {"53":"bracket","31":"bearing","30":"gear","47":"tube","48":"cylinder","29":"cylinder",
           "26":"oring","25":"box","28":"box","61":"tube","59":"tube"}
GENERIC = {"", "NAME", "ITEM NAME", "NOMENCLATURE", "PART", "ITEM", "NONE", "N/A", "UNKNOWN", "NConnection"}

def fsc_family(nsn):
    m = re.match(r"\s*(\d{4})", nsn or "")
    if not m: return None
    fsc = m.group(1)
    if fsc in FSC_MAP: return FSC_MAP[fsc]
    return FSG_MAP.get(fsc[:2])

def is_generic(nm):
    s = re.sub(r"\s+", " ", (nm or "").strip()).upper()
    if s in GENERIC: return True
    if re.match(r"^(FOR|OF)\b", s): return True
    if len(s) <= 2: return True
    return False

def main():
    if not os.path.exists(DB):
        p("[ERROR] index not found: %s" % DB); return 1
    con = sqlite3.connect("file:%s?mode=ro" % DB, uri=True); con.row_factory = sqlite3.Row
    rows = con.execute(
        "SELECT p.nsn AS nsn, COALESCE(NULLIF(r.item_name,''), p.fig_title) AS nm, MAX(r.characteristics) AS ch "
        "FROM parts p LEFT JOIN ref_nsn r ON r.nsn=p.nsn "
        "WHERE p.fig_no IS NOT NULL AND COALESCE(TRIM(p.nsn),'')<>'' GROUP BY p.nsn").fetchall()
    con.close()
    total = len(rows)
    fam_count = collections.Counter()
    fam_count_fsc = collections.Counter()      # after FSC fallback
    box_fsc_hist = collections.Counter()
    box_still = collections.Counter()
    generic = 0; generic_rescued = 0
    for r in rows:
        nm = (r["nm"] or "").strip(); nsn = r["nsn"] or ""
        fam = family(nm, r["ch"] or "")
        fam_count[fam] += 1
        gen = is_generic(nm)
        if gen: generic += 1
        # FSC fallback when the name produced a box
        eff = fam
        if eff == "box":
            ff = fsc_family(nsn)
            box_fsc_hist[(re.match(r"\s*(\d{4})", nsn).group(1) if re.match(r"\s*(\d{4})", nsn) else "????")] += 1
            if ff:
                eff = ff
                if gen: generic_rescued += 1
            else:
                box_still[(re.match(r"\s*(\d{4})", nsn).group(1) if re.match(r"\s*(\d{4})", nsn) else "????")] += 1
        fam_count_fsc[eff] += 1
    p("=== 3-D SHAPE COVERAGE (figures-first set) — with NSN/FSC fallback ===")
    p("parts (distinct NSN with a figure): %d" % total)
    boxn = fam_count.get("box", 0); boxn2 = fam_count_fsc.get("box", 0)
    p("name-only classifier:   box = %d (%.1f%%)   recognizable = %.1f%%" % (boxn, 100.0*boxn/total, 100.0*(total-boxn)/total))
    p("+ NSN/FSC fallback:      box = %d (%.1f%%)   recognizable = %.1f%%" % (boxn2, 100.0*boxn2/total, 100.0*(total-boxn2)/total))
    p("parts with a GENERIC/blank name: %d   of which FSC rescued: %d" % (generic, generic_rescued))
    p("")
    p("-- family distribution AFTER FSC fallback --")
    for fam, c in fam_count_fsc.most_common():
        p("  %-9s %6d  (%.1f%%)" % (fam, c, 100.0*c/total))
    p("")
    p("-- FSC classes among the name->box parts (top 30; * = now mapped by FSC) --")
    for fsc, c in box_fsc_hist.most_common(30):
        mapped = fsc in FSC_MAP or (fsc[:2] in FSG_MAP)
        p("  %s  %5d   %s%s" % (fsc, c, "-> " + (FSC_MAP.get(fsc) or FSG_MAP.get(fsc[:2])) if mapped else "(still box)", "  *" if mapped else ""))
    p("")
    p("-- FSC classes STILL box after fallback (top 20 — candidates to map next) --")
    for fsc, c in box_still.most_common(20):
        p("  %s  %5d" % (fsc, c))
    try:
        open(os.path.join(HERE, "..", "index", "shape_analysis.txt"), "w", encoding="utf-8").write("\n".join(out))
        p("\n[saved]")
    except Exception:
        pass
    return 0

if __name__ == "__main__":
    sys.exit(main())
