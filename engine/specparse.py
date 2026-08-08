#!/usr/bin/env python3
"""THE VIEWER -- FASTENER / THREAD / GD&T / MIL-SPEC PARSER (v1.2.0, catalog §3.7 + §3.8). Pulls the *named engineering
specifications* out of the text that plain measurement regex misses: thread callouts, fit/tolerance classes, diameter +
bilateral tolerances, and the MIL-SPEC / fuel / lubricant references that tell a mechanic exactly what part or fluid to
use. Pure stdlib regex; read-only; feeds the Masterfile as typed spec records. Corpus authoritative."""
import re

# --- thread callouts: 1/2-13 UNC-2A · 3/8-16 · #10-24 UNF · M10x1.5 · M6-1.0 ---
_THREAD = re.compile(
    r"\b(?:(?P<imp>(?:#\d{1,2}|\d{1,2}/\d{1,2}|\d(?:\.\d+)?)\s*-\s*\d{1,2}(?:\s*-?\s*UN[CEFRJS]?(?:-?[123][AB])?)?)"
    r"|(?P<met>M\d{1,3}(?:\.\d+)?\s*[x×-]\s*\d(?:\.\d+)?))\b")
# --- fit / tolerance class: class 2A, class 3B ---
_CLASS = re.compile(r"\bclass\s*([123][AB])\b", re.I)
# --- diameter + bilateral tolerance: Ø.500 ±.002 · dia 0.75 +.002/-.001 in ---
_DIA = re.compile(r"(?:Ø|dia\.?|diameter)\s*(?P<v>[\d.]+)\s*(?:(?:±|\+/-)\s*(?P<tol>[\d.]+))?", re.I)
# --- MIL / federal / industry standards & hardware: MIL-PRF-2104, MIL-STD-1913, MS35206, AN960, NAS1234, SAE J1926 ---
_STD = re.compile(
    r"\b(?:MIL-(?:PRF|STD|DTL|L|C|G|A|S|W|T|F|H|P|R)-[0-9A-Z]{2,6}[A-Z]?(?:/\d+)?"
    r"|(?:MS|AN|NAS|NASM|MS)\d{3,6}[A-Z]?"
    r"|SAE\s?(?:J|AS|AMS)\d{2,5}"
    r"|FED-STD-\d+|A-A-\d+|ASTM\s?[A-Z]\d{2,4})\b")
# --- fuels / lubricants / greases: DF-2, JP-8, OE/HDO 15W40, GAA, DEXRON, GO-80/90, BFA ---
_FLUID = re.compile(
    r"\b(?:DF-[12A]|JP-[458]|MOGAS|DIESEL|OE/HDO|OEA|HDO|GAA|GO(?:-\d{2,3})?|GOS|BFA|CLP|RBC|"
    r"DEXRON(?:\s?[IVX]+)?|SAE\s?\d{1,2}W?-?\d{0,2}|MIL-PRF-\d+)\b")


def _ctx(text, s, e, pad=45):
    return re.sub(r"\s+", " ", text[max(0, s - pad):min(len(text), e + pad)]).strip()


def extract(text, page=None, cap=200):
    """Return typed spec records: {kind, value, [tolerance], context, [page]} where kind in
    {thread, fit_class, diameter, standard, fluid}. Deduped."""
    if not text:
        return []
    out = []; seen = set()

    def add(kind, value, s, e, tol=None):
        v = re.sub(r"\s+", " ", value).strip()
        key = (kind, v.lower())
        if not v or key in seen:
            return
        seen.add(key)
        rec = {"kind": kind, "value": v, "context": _ctx(text, s, e)}
        if tol:
            rec["tolerance"] = tol
        if page is not None:
            rec["page"] = page
        out.append(rec)

    for m in _THREAD.finditer(text):
        add("thread", m.group(0), m.start(), m.end())
    for m in _CLASS.finditer(text):
        add("fit_class", "class " + m.group(1).upper(), m.start(), m.end())
    for m in _DIA.finditer(text):
        add("diameter", m.group("v"), m.start(), m.end(), tol=m.group("tol"))
    for m in _STD.finditer(text):
        add("standard", m.group(0), m.start(), m.end())
    for m in _FLUID.finditer(text):
        add("fluid", m.group(0).upper(), m.start(), m.end())
        if len(out) >= cap:
            break
    return out[:cap]


def by_kind(text):
    c = {}
    for r in extract(text):
        c[r["kind"]] = c.get(r["kind"], 0) + 1
    return c


def find_for_query(db_path, q, limit=40):
    """On-the-fly: FTS-match pages for `q`, pull thread/fit/diameter/standard/fluid specs, grouped + cited. No prebuilt
    index (uses the existing OCR/text layer). Returns {query, count, by_kind, results:[{...,page,doc,vehicle,tm}]}."""
    import sqlite3
    q = (q or "").strip()
    if len(q) < 2:
        return {"query": q, "count": 0, "by_kind": {}, "results": []}
    terms = [t for t in re.findall(r"[A-Za-z0-9]+", q) if len(t) > 1]
    match = " OR ".join(terms) if terms else q
    rows = []
    # v1.13.4: con=None + finally -- `match` falls back to the raw query verbatim when it has no
    # alnum characters (e.g. a lone '"'), reaching FTS5's MATCH parser unescaped and raising a syntax
    # error on ordinary malformed user input, not just a corrupted-db edge case; the old shape leaked
    # a handle on the PRIMARY viewer.db every time that happened.
    con = None
    try:
        con = sqlite3.connect("file:%s?mode=ro" % db_path, uri=True); con.row_factory = sqlite3.Row
        rows = con.execute(
            "SELECT d.id AS doc, d.vehicle, d.tm_number AS tm, p.page_number AS page, p.body_text AS body "
            "FROM pages_fts JOIN pages p ON p.id=pages_fts.rowid JOIN documents d ON d.id=p.document_id "
            "WHERE pages_fts MATCH ? ORDER BY rank LIMIT ?", (match, limit)).fetchall()
    except Exception as e:
        return {"query": q, "count": 0, "by_kind": {}, "results": [], "error": str(e)}
    finally:
        if con is not None:
            con.close()
    out = []; counts = {}
    for r in rows:
        for m in extract(r["body"] or "", page=r["page"], cap=40):
            m["doc"] = r["doc"]; m["vehicle"] = r["vehicle"]; m["tm"] = r["tm"]
            m["page_url"] = "/deepzoom?doc=%s&page=%s" % (r["doc"], r["page"])
            counts[m["kind"]] = counts.get(m["kind"], 0) + 1
            out.append(m)
    return {"query": q, "count": len(out), "by_kind": counts, "results": out}


if __name__ == "__main__":
    sample = (
        "Install capscrew 1/2-13 UNC-2A and torque per table. Jam nut #10-24 UNF. Metric bolt M10x1.5 class 6g. "
        "Bushing bore diameter .500 +/- .002 in. Shaft dia 0.75 in. Fit class 2A. "
        "Lubricate with GAA (MIL-PRF-10924). Engine oil OE/HDO 15W40 per MIL-PRF-2104. Fuel DF-2 or JP-8. "
        "Hardware MS35206-228 and AN960 washer, NAS1149. Standard MIL-STD-1913 rail. Seal per SAE J1926."
    )
    rows = extract(sample, page=9)
    kinds = by_kind(sample)
    for need in ("thread", "fit_class", "diameter", "standard", "fluid"):
        assert need in kinds, "missing kind %s (%s)" % (need, kinds)
    threads = [r["value"] for r in rows if r["kind"] == "thread"]
    assert any("1/2-13" in x for x in threads), threads
    stds = [r["value"] for r in rows if r["kind"] == "standard"]
    assert any(x.startswith("MIL-PRF-2104") for x in stds) and any(x.startswith("MS35206") for x in stds), stds
    fluids = [r["value"] for r in rows if r["kind"] == "fluid"]
    assert "DF-2" in fluids and "JP-8" in fluids and "GAA" in fluids, fluids
    dia = [r for r in rows if r["kind"] == "diameter"]
    assert any(r.get("tolerance") == ".002" for r in dia), dia
    print("specparse self-test OK  (thread/fit/diameter/standard/fluid — %s)" % kinds)
# END OF FILE
