#!/usr/bin/env python3
"""THE VIEWER -- MEASUREMENT / DIMENSIONAL DATA EXTRACTOR (v1.1.0). Beyond OCR text: pull EVERY measured quantity out of
the manual text -- lengths, diameters, clearances/tolerances, weights, pressures, torque, volumes/capacities,
temperatures, electrical, flow, force, speed, angle, thread sizes -- each with its value(s), canonical unit, dimension
type, the sentence it came from, and its cited page. Ranges (X-Y) and tolerances (X +/- Y) handled. Pure regex over the
text layer; read-only; db_path passed explicitly. Feeds /measures + a measures sidecar (build_measures.py).
v1.13.0: retrieval moved to features.corpus (shared FTS helper) -- this module no longer opens sqlite directly."""
import re

# unit alternation -> (dimension type, canonical unit). Order matters: longer/rarer first so e.g. 'in-lb' isn't 'in'.
_UNITS = [
    # torque (before length, so 'ft-lb'/'in-lb' win over 'ft'/'in')
    (r"ft[\s\-\.]?lb[s]?|lb[s]?[\s\-\.]?ft|foot[\s\-]?pound[s]?", "torque", "ft-lb"),
    (r"in[\s\-\.]?lb[s]?|inch[\s\-]?pound[s]?", "torque", "in-lb"),
    # v1.13.4: the multiplication dot in "N·m" is written as several look-alike Unicode chars depending on
    # the source font/OCR pass -- U+00B7 MIDDLE DOT, U+2022 BULLET, and U+2219 BULLET OPERATOR all show up
    # in this corpus. Missing any of them used to fall through to the bare-"N" FORCE pattern below and
    # silently mislabel a torque value (e.g. "854 N•m") as force -- confirmed live via a generated quiz
    # question that asked "what is the force" with Newton-only answer options for a torque-nut spec.
    # Separately (found while fixing the above): a plain HYPHEN was never in this character class either,
    # so the equally-common hyphenated form "25 N-m" matched nothing at all -- only "25 Nm"/"25 N m" did.
    (r"n[\s·•∙\-\.]?m|newton[\s\-]?met(?:er|re)[s]?", "torque", "N-m"),
    # pressure
    (r"psi[ag]?|lb[s]?/in\^?2|lb[s]?[\s\-]?per[\s\-]?square[\s\-]?inch", "pressure", "psi"),
    (r"kpa|kilopascal[s]?", "pressure", "kPa"),
    (r"mpa|megapascal[s]?", "pressure", "MPa"),
    (r"bar\b", "pressure", "bar"),
    (r"in[\s\-\.]?hg|inches?[\s\-]?of[\s\-]?mercury", "pressure", "inHg"),
    # electrical
    (r"vdc|vac|volt[s]?|(?<![a-z])v(?![a-z])", "electrical", "V"),
    (r"amp[s]?|amperes?|(?<![a-z])a(?=\b)", "electrical", "A"),
    (r"milliamp[s]?|ma\b", "electrical", "mA"),
    (r"ohm[s]?|Ω", "electrical", "ohm"),
    # v1.13.4: exclude "W" immediately followed by "-<digit>" -- that's the SAE oil-viscosity grade
    # suffix (5W-30, 10W-40, 15W-40, 75W-90, ...), not a wattage reading, and viscosity-grade codes are
    # standard content in essentially every vehicle TM's lubrication/servicing chart, so without this the
    # bare-W pattern fabricated a "-5 Watts"/"-15 Watts" electrical spec next to real oil-grade text.
    (r"watt[s]?|(?<![a-z])w(?![a-z])(?!-\d)", "electrical", "W"),
    (r"hertz|hz\b", "electrical", "Hz"),
    # flow / speed / rotation
    (r"gpm|gal(?:lon)?[s]?[\s/]*(?:per[\s]*)?min", "flow", "gpm"),
    (r"cfm|cu\.?[\s]*ft[\s/]*(?:per[\s]*)?min", "flow", "cfm"),
    (r"rpm|rev(?:olution)?[s]?[\s/]*(?:per[\s]*)?min", "rotation", "rpm"),
    (r"mph|miles?[\s/]*(?:per[\s]*)?h(?:ou)?r", "speed", "mph"),
    (r"km/?h|kph|kilomet(?:er|re)[s]?[\s/]*(?:per[\s]*)?h(?:ou)?r", "speed", "km/h"),
    # volume / capacity
    (r"gal(?:lon)?[s]?", "capacity", "gal"),
    (r"quart[s]?|qt[s]?", "capacity", "qt"),
    (r"pint[s]?|pt[s]?", "capacity", "pt"),
    (r"fl[\s\.]?oz|fluid[\s\-]?ounce[s]?", "capacity", "fl-oz"),
    (r"lit(?:er|re)[s]?|(?<![a-z])l(?=\b)", "capacity", "L"),
    (r"millilit(?:er|re)[s]?|ml\b|cc\b|cubic[\s\-]?cent", "capacity", "mL"),
    # weight / mass / force
    (r"lb[s]?f", "force", "lbf"),
    (r"kn\b|kilonewton[s]?", "force", "kN"),
    (r"(?<![a-z])n(?![a-z\-])", "force", "N"),
    (r"pound[s]?|lb[s]?(?![\s\-\.]?ft)|lbs\.?", "weight", "lb"),
    (r"ounce[s]?|oz\b", "weight", "oz"),
    (r"kilogram[s]?|kg[s]?", "weight", "kg"),
    (r"gram[s]?|(?<![a-z])g(?=\b)", "weight", "g"),
    (r"ton[s]?", "weight", "ton"),
    # temperature
    # v1.13.5: bare F/C (no deg-word or degree-symbol) now also matches -- e.g. "-40 F to 120 F" -- since
    # that's a real, common way TMs write temperature ranges, and previously extracted NOTHING at all.
    # Bare single-letter units are the highest collision-risk pattern in this file (see
    # _BARE_LETTER_UNITS below), and this corpus specifically is full of hyphen-suffixed military
    # designators that look just like it (F-15, F-16, F/A-18, C-5, C-17, C-130) plus battery "C-rate"
    # notation (0.5C, 1C) -- (?!-\d)/(?!\d)/(?!/) exclude the designators here (same technique as the
    # oil-grade "5W-30" guard above); the no-space C-rate form is excluded in extract() below, which can
    # see whether real whitespace separated the number from the letter (the isolated per-unit regex used
    # by _classify() cannot -- a positive lookbehind for whitespace would silently stop matching there).
    (r"°\s*f|deg(?:ree)?[s]?[\s\.]*f(?:ahrenheit)?|(?<![a-z])f(?![a-z])(?!\d)(?!-\d)(?!/)", "temperature", "degF"),
    (r"°\s*c|deg(?:ree)?[s]?[\s\.]*c(?:elsius|entigrade)?|(?<![a-z])c(?![a-z])(?!\d)(?!-\d)(?!/)", "temperature", "degC"),
    # area
    (r"sq\.?[\s\-]?in|in\^?2|square[\s\-]?inch(?:es)?", "area", "sq-in"),
    (r"sq\.?[\s\-]?ft|ft\^?2|square[\s\-]?f(?:ee|oo)t", "area", "sq-ft"),
    # angle
    (r"°|deg(?:ree)?[s]?", "angle", "deg"),
    # LENGTH / DIMENSION (last, most generic) -- inches, feet, metric, mils
    (r"in(?:ch(?:es)?)?\.?|\"", "length", "in"),
    (r"f(?:ee|oo)t\.?|'", "length", "ft"),
    (r"yard[s]?|yd[s]?", "length", "yd"),
    (r"millimet(?:er|re)[s]?|mm\b", "length", "mm"),
    (r"centimet(?:er|re)[s]?|cm\b", "length", "cm"),
    (r"met(?:er|re)[s]?|(?<![a-z])m(?![a-z])", "length", "m"),
    (r"mil[s]?|thou\b|thousandth[s]?", "length", "mil"),
]
_UNIT_RE = "|".join("(?:%s)" % u for u, _, _ in _UNITS)
# number, optional range/tolerance, then a unit
_NUM = r"[+\-]?(?:\d{1,6}(?:,\d{3})*(?:\.\d+)?|\.\d+)"   # also matches leading-decimal values like .015 / .002
_MEAS = re.compile(
    r"(?P<v1>%s)\s*(?:(?:-|–|to|through)\s*(?P<v2>%s)\s*)?(?:(?:±|\+/-|plus or minus)\s*(?P<tol>%s)\s*)?(?P<unit>%s)\b"
    % (_NUM, _NUM, _NUM, _UNIT_RE), re.I)


def _classify(unit_raw):
    u = unit_raw.lower()
    for pat, typ, canon in _UNITS:
        if re.fullmatch(pat, u, re.I) or re.match(pat + r"$", u, re.I):
            return typ, canon
    # fallback: match against each pattern loosely
    for pat, typ, canon in _UNITS:
        if re.search(r"^(?:%s)$" % pat, u, re.I):
            return typ, canon
    return "other", unit_raw


# v1.13.4: canonical units matched by a BARE single letter/symbol ((?<![a-z])X(?![a-z])-style patterns in
# _UNITS) -- these are the ones a number can accidentally bridge into across an OCR-linearized table row,
# since \s* (the number-to-unit connector) matches newlines by default. Multi-char/word units (ft-lb, psi,
# gpm, ...) aren't included: they're not ambiguous the same way, and guarding them too would cost real
# recall on genuinely line-wrapped prose measurements.
# v1.13.5: degF/degC added -- their new bare-letter F/C alternative (see _UNITS above) has the exact same
# newline-bridging risk as V/A/W/N/L/m/g. Note this also (harmlessly) applies the guard to a genuine
# "deg F"/"°F" match that happens to span a newline -- same conservative trade-off already accepted above.
_BARE_LETTER_UNITS = {"V", "A", "W", "N", "L", "m", "g", "degF", "degC"}


def extract(text, page=None, cap=200):
    """Return [{type, value, value2, tolerance, unit, raw, context}] for every measurement in `text`."""
    if not text:
        return []
    out = []; seen = set()
    for m in _MEAS.finditer(text):
        typ, canon = _classify(m.group("unit"))
        if canon in _BARE_LETTER_UNITS and "\n" in m.group(0):
            # the number and its "unit" were on different source lines -- almost certainly two unrelated
            # table cells bridged by linearized OCR text, not a real measurement. Confirmed live: a
            # transmission-solenoid fault-code table produced a fabricated "26 N" / "22 G" this way.
            continue
        if canon in ("degF", "degC") and len(m.group("unit")) == 1:
            # v1.13.5: the bare-letter F/C alternative needs REAL whitespace between the number and the
            # unit -- a no-space form is the signature of a collision, not a genuine temperature: battery
            # C-rate notation (0.5C, 1C discharge) writes it with no space, and a stray digit immediately
            # before a designator (e.g. a parts-list count next to "C130") would too. A real prose
            # temperature reading puts a space there ("120 F", "-40 F"). The ° and "deg" forms are exact
            # words/symbols already and don't need this extra check.
            ustart = m.start("unit")
            if ustart == 0 or not text[ustart - 1].isspace():
                continue
        raw = m.group(0).strip()
        start = max(0, m.start() - 45); end = min(len(text), m.end() + 45)
        ctx = re.sub(r"\s+", " ", text[start:end]).strip()
        key = (raw.lower(), ctx[:30])
        if key in seen:
            continue
        seen.add(key)
        rec = {"type": typ, "unit": canon, "value": m.group("v1"),
               "value2": m.group("v2"), "tolerance": m.group("tol"),
               "raw": raw[:60], "context": ctx[:160]}
        if page is not None:
            rec["page"] = page
        out.append(rec)
        if len(out) >= cap:
            break
    return out


def by_type(text):
    """Summary: {type: count} across the text."""
    c = {}
    for r in extract(text):
        c[r["type"]] = c.get(r["type"], 0) + 1
    return c


def find_for_query(db_path, q, limit=40):
    """On-the-fly: FTS-match pages for `q`, extract every measurement from them, grouped by type + cited. No prebuilt
    index needed (uses the existing OCR/text layer). Returns {query, count, by_type, results:[{...,page,doc,vehicle}]}.
    v1.13: retrieval via features.corpus (pooled in-app, leak-proof standalone); every row carries a
    validate.py verdict as row["quality"] (ok|suspect|quarantined) + a trust.py level; quarantined rows
    are WITHHELD from `results` (R13: never show garble as fact) but returned in `quarantined` -- flagged,
    not deleted."""
    q = (q or "").strip()
    if len(q) < 2:
        return {"query": q, "count": 0, "by_type": {}, "results": [], "quarantined": []}
    terms = [t for t in re.findall(r"[A-Za-z0-9]+", q) if len(t) > 1]
    match = " OR ".join(terms) if terms else q
    try:
        from features import corpus as _corpus
        rows = _corpus.fts_pages(match, limit=limit, with_body=True, db_path=db_path)
    except Exception as e:
        return {"query": q, "count": 0, "by_type": {}, "results": [], "quarantined": [], "error": str(e)}
    import validate as _validate, trust as _trust
    out = []; counts = {}; quarantined = []
    for r in rows:
        for m in extract(r["body_text"] or "", page=r["page_number"], cap=60):
            m["doc"] = r["doc_id"]; m["vehicle"] = r["vehicle"]; m["tm"] = r["tm_number"]
            m["page_url"] = "/deepzoom?doc=%s&page=%s" % (r["doc_id"], r["page_number"])
            v = _validate.validate_value(m["type"], m["value"], m["unit"])
            m["quality"] = "quarantined" if v["status"] == "quarantine" else v["status"]
            if v.get("reason"):
                m["quality_reason"] = v["reason"]
            m["trust"] = _trust.level(source="corpus", validation_status=v["status"], n_samples=1)
            if v["status"] == "quarantine":
                quarantined.append(m)            # withheld from display by default; never silently dropped
                continue
            counts[m["type"]] = counts.get(m["type"], 0) + 1
            out.append(m)
    return {"query": q, "count": len(out), "by_type": counts, "results": out,
            "quarantined": quarantined, "quarantined_count": len(quarantined),
            "trust": (_trust.worst([m["trust"] for m in out]) if out else None)}


if __name__ == "__main__":
    sample = (
        "Torque the mounting bolts to 30-35 ft-lb. Tire pressure 32 psi cold. Oil capacity 6 qt. "
        "Overall length 180 in, width 85 in, height 72 in. Curb weight 5,200 lb. Clearance .015 +/- .002 in. "
        "Charging voltage 28 VDC at 100 A. Coolant 12 L. Operating temperature -25 degF to 120 degF. "
        "Drain plug torque 18 in-lb. Idle 700 rpm. Fuel flow 4 gpm. Thread 1/2 in. Angle 15 deg. "
        "Regulator set to 45 N-m. Bead 2.5 mm gap."
    )
    rows = extract(sample, page=42)
    from collections import Counter
    print("total measurements:", len(rows))
    print("by type:", dict(Counter(r["type"] for r in rows)))
    for r in rows[:8]:
        print("  [%s] %s %s%s  <= %s" % (r["type"], r["value"], r["unit"],
              ("-" + r["value2"]) if r["value2"] else "", r["raw"]))
    types = set(r["type"] for r in rows)
    for need in ("torque", "pressure", "capacity", "length", "weight", "electrical", "temperature", "rotation", "flow", "angle"):
        assert need in types, "missing dimension type: %s" % need
    print("measures self-test OK (all target dimension types found)")
# END OF FILE
