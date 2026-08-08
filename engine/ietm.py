#!/usr/bin/env python3
"""THE VIEWER -- IETM / S1000D / MIL-STD-40051 XML PARSER (v1.3.0, catalog §6.2). When a TM ships as a structured
Interactive Electronic Technical Manual (S1000D data modules, or MIL-STD-40051 XML/SGML) the data is already tagged --
titles, warnings, cautions, notes, procedural steps, tables -- which is the richest, cleanest source of all. This reads
those files (namespace-agnostic, stdlib xml.etree so it copes with any S1000D issue/vendor variant) into the same
structured shape the PDF parsers produce, and runs the measurement extractor over the text. Read-only; degrades safely
on malformed XML. Corpus authoritative."""
import os
import xml.etree.ElementTree as ET


def _local(tag):
    return tag.rsplit("}", 1)[-1] if "}" in (tag or "") else (tag or "")


def _text(el):
    return " ".join(t.strip() for t in el.itertext() if t and t.strip())


def is_ietm(path):
    """True if `path` looks like an S1000D/IETM/40051 XML data module (by root/opening tags)."""
    if not path or not os.path.exists(path) or os.path.getsize(path) > 40_000_000:
        return False
    try:
        head = open(path, "rb").read(4000).decode("utf-8", "replace").lower()
    except Exception:
        return False
    return ("<dmodule" in head or "s1000d" in head or "<techmanual" in head or "<40051" in head
            or "mil-std-40051" in head or ("<dmodule" not in head and "<content" in head and "<dmaddress" in head))


def parse(path, measure_fn=None):
    """Parse an IETM XML file -> {title, dmc, warnings[], cautions[], notes[], steps[], tables[], measurements[]}.
    `measure_fn` (default measures.extract) pulls measurements from the combined text. Fail-soft -> mostly-empty dict."""
    out = {"title": "", "dmc": "", "warnings": [], "cautions": [], "notes": [], "steps": [], "tables": [],
           "measurements": []}
    if not path or not os.path.exists(path):
        return out
    try:
        root = ET.parse(path).getroot()
    except Exception:
        return out
    texts = []
    for el in root.iter():
        lt = _local(el.tag).lower()
        if lt in ("dmtitle", "techname", "infoname") and not out["title"]:
            out["title"] = _text(el)[:200]
        elif lt in ("title",) and not out["title"]:
            out["title"] = _text(el)[:200]
        elif lt == "dmcode":
            out["dmc"] = (el.get("dmCode") or el.get("assyCode") or "").strip() or out["dmc"]
        elif lt == "warning":
            t = _text(el)
            if t:
                out["warnings"].append(t[:300])
        elif lt == "caution":
            t = _text(el)
            if t:
                out["cautions"].append(t[:300])
        elif lt == "note":
            t = _text(el)
            if t:
                out["notes"].append(t[:300])
        elif lt in ("proceduralstep", "step"):
            t = _text(el)
            if t:
                out["steps"].append(t[:400])
        elif lt in ("table", "ghpstbl"):
            rows = []
            for r in el.iter():
                if _local(r.tag).lower() in ("row",):
                    cells = [_text(c) for c in r if _local(c.tag).lower() in ("entry", "td", "th")]
                    if any(cells):
                        rows.append(cells)
            if rows:
                out["tables"].append({"rows": rows[:60], "n_rows": len(rows)})
        # collect body text for measurement extraction (paras & step text)
        if lt in ("para", "proceduralstep", "step", "listitem", "entry"):
            tt = _text(el)
            if tt:
                texts.append(tt)
    blob = "\n".join(texts) or _text(root)
    if measure_fn is None:
        try:
            import measures
            measure_fn = measures.extract
        except Exception:
            measure_fn = None
    if measure_fn:
        try:
            out["measurements"] = measure_fn(blob, cap=120)
        except Exception:
            out["measurements"] = []
    # de-dup warnings/cautions/notes/steps preserving order
    for k in ("warnings", "cautions", "notes", "steps"):
        seen = set(); uniq = []
        for x in out[k]:
            if x.lower() not in seen:
                seen.add(x.lower()); uniq.append(x)
        out[k] = uniq
    return out


if __name__ == "__main__":
    import tempfile
    xml = """<?xml version="1.0"?>
    <dmodule xmlns="http://www.s1000d.org/S1000DBk/xml_schema_flat">
      <identAndStatusSection><dmAddress><dmIdent>
        <dmCode assyCode="2320-01" /><dmTitle><techName>HMMWV Leading Particulars</techName></dmTitle>
      </dmIdent></dmAddress></identAndStatusSection>
      <content>
        <description>
          <levelledPara><title>Leading particulars</title>
            <para>Overall length 180 in. Curb weight 5200 lb. Charging voltage 28 VDC.</para></levelledPara>
        </description>
        <warning><warningAndCautionPara>High voltage present. Disconnect battery ground.</warningAndCautionPara></warning>
        <caution><warningAndCautionPara>Do not overtighten the fitting.</warningAndCautionPara></caution>
        <note><notePara>Torque values are for dry threads.</notePara></note>
        <procedure><mainProcedure>
          <proceduralStep><para>Remove the access panel.</para></proceduralStep>
          <proceduralStep><para>Torque the bolts to 30 ft-lb.</para></proceduralStep>
        </mainProcedure></procedure>
      </content>
    </dmodule>"""
    p = os.path.join(tempfile.mkdtemp(), "dm.xml"); open(p, "w").write(xml)

    import re
    def fm(t, cap=120):
        out = []
        for m in re.finditer(r"(\d+)\s*(in|lb|VDC|ft-lb)\b", t):
            u = m.group(2); ty = {"in": "length", "lb": "weight", "VDC": "electrical", "ft-lb": "torque"}[u]
            out.append({"type": ty, "unit": u, "value": m.group(1), "value2": None, "tolerance": None,
                        "raw": m.group(0), "context": ""})
        return out

    assert is_ietm(p), "should detect S1000D dmodule"
    d = parse(p, measure_fn=fm)
    assert d["title"].startswith("HMMWV") or "Leading" in d["title"], ("title", d["title"])
    assert any("High voltage" in w for w in d["warnings"]), ("warnings", d["warnings"])
    assert any("overtighten" in c for c in d["cautions"]), ("cautions", d["cautions"])
    assert any("dry threads" in n for n in d["notes"]), ("notes", d["notes"])
    assert len(d["steps"]) == 2 and "access panel" in d["steps"][0], ("steps", d["steps"])
    mt = {m["type"] for m in d["measurements"]}
    assert {"length", "weight", "electrical", "torque"} <= mt, ("measurements", d["measurements"])
    print("ietm self-test OK  (S1000D detect + title/warnings/cautions/notes/%d steps + %d measurements)"
          % (len(d["steps"]), len(d["measurements"])))
# END OF FILE
