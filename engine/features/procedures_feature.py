#!/usr/bin/env python3
"""THE VIEWER -- procedure parsing + torque specs (extracted verbatim from viewer_app, v0.96.0).

Heuristic structure extraction from TM work-package pages (kind/steps/tools/cautions) and the
torque-value finder. Read-only on the index; every result cites its real page. DI via `core`."""
import re
import sqlite3

from patterns import norm_nsn

core = None          # injected by viewer_app at startup


def _proc_kind(line):
    u = line.upper()
    if "REMOVAL" in u or re.search(r"\bREMOVE\b", u): return "Removal"
    if "INSTALLATION" in u or re.search(r"\bINSTALL\b", u): return "Installation"
    if "DISASSEMBL" in u: return "Disassembly"
    if "ASSEMBL" in u: return "Assembly"
    if "REPLACE" in u: return "Replacement"
    if "ADJUST" in u: return "Adjustment"
    if "INSPECT" in u: return "Inspection"
    if "CLEAN" in u: return "Cleaning"
    if "REPAIR" in u: return "Repair"
    if "SERVICE" in u: return "Service"
    return None


def _parse_procedure(text):
    """Heuristically pull structure out of a TM work-package page: kind, numbered steps, a
    tools-required list, materials/consumables, referenced manuals, and WARNING/CAUTION/NOTE
    callouts. Best-effort extraction — the cited page image is always the source of truth (the UI
    links to it and says 'verify on the sheet'). `materials`/`references` added v0.99.10 (additive)."""
    if not text: return None
    lines = [l.rstrip() for l in re.split(r"[\r\n]+", text)]
    kind = None; title = None; steps = []; tools = []; cautions = []; materials = []
    refs = []; refseen = set(); in_tools = False; in_mat = False
    for i, l in enumerate(lines):
        s = l.strip()
        if not s: in_tools = False; in_mat = False; continue
        if not kind and len(s) <= 24 and re.match(r"^(REMOVAL|INSTALLATION|DISASSEMBLY|ASSEMBLY|REPLACEMENT|ADJUSTMENT|REPAIR|SERVICE|INSPECTION|CLEANING)\b", s.upper()):
            kind = _proc_kind(s); title = s    # only a standalone section heading sets the kind (not 'ENGINE ASSEMBLY')
        # referenced manuals anywhere on the page (TM / WP / LO / TB / TC numbers)
        for rm in re.finditer(r"\b(TM|WP|LO|TB|TC)\s?\d[\dA-Z\-]{2,}", s.upper()):
            rf = re.sub(r"\s+", " ", rm.group(0)).strip()
            if rf not in refseen: refseen.add(rf); refs.append(rf)
        # section switches
        if re.search(r"TOOLS?\s+(REQUIRED|AND)|SPECIAL TOOLS|TEST EQUIPMENT|\bTMDE\b", s.upper()):
            in_tools = True; in_mat = False; continue
        if re.search(r"MATERIALS?\s*/?\s*PARTS|EXPENDABLE|CONSUMABLE|MATERIALS?\s+(REQUIRED|LIST)|SUPPLIES", s.upper()):
            in_mat = True; in_tools = False; continue
        if in_tools:
            if re.match(r"^(MATERIAL|PARTS|PERSONNEL|REFERENCE|EQUIPMENT|WARNING|CAUTION|NOTE|STEP|\d)", s.upper()): in_tools = False
            elif len(s) > 2: tools.append(s[:80])
        elif in_mat:
            if re.match(r"^(TOOLS|PERSONNEL|REFERENCE|EQUIPMENT|WARNING|CAUTION|NOTE|STEP|\d)", s.upper()): in_mat = False
            elif len(s) > 2: materials.append(s[:80])
        if re.match(r"^(WARNING|CAUTION|NOTE|DANGER)\b", s.upper()):
            nxt = lines[i+1].strip() if i+1 < len(lines) else ""
            body = (s.split(":", 1)[1].strip() if ":" in s else nxt)
            cautions.append({"kind": re.match(r"^(WARNING|CAUTION|NOTE|DANGER)", s.upper()).group(1), "text": body[:160]})
        m = re.match(r"^(\d{1,3})[\.\)]\s+(.+)", s)
        if m and len(m.group(2)) > 4: steps.append(m.group(2)[:300])
    if not steps and not tools: return None
    # UX finding #6 (priority 5, R13 safety-relevant): flag each caution's OCR-quality confidence (the
    # same signal cautions.find_for_query() already computes for /api/cautions via textquality.annotate,
    # additive -- no change to the {kind, text} shape above) so a mechanic reading a printed Job Card
    # away from the screen -- with no way to re-check a garbled DANGER line against the corpus -- can
    # see that it needs verifying, instead of every callout displaying with identical visual weight.
    # Review finding: the try/except used to wrap the WHOLE loop, so one bad caution mid-list would
    # silently leave every LATER caution un-annotated (no exception surfaced, no consumer able to tell
    # "clean" from "never scored") -- exactly the safety-relevant item this fix cares most about could
    # be the one left unflagged. Each caution is now scored independently.
    try:
        import textquality as _tq
    except Exception:
        _tq = None
    if _tq:
        for c in cautions:
            try:
                scored = _tq.annotate({"text": c["text"]}, context_key="text")
                c["confidence"] = scored["confidence"]; c["quality"] = scored["quality"]
            except Exception:
                pass
    return {"kind": kind or "Procedure", "title": (title or "")[:80], "steps": steps[:40],
            "tools": tools[:25], "materials": materials[:20], "references": refs[:12],
            "cautions": cautions[:12]}


def procedure_for(query, limit=6):
    """Surface step-by-step instructions (remove/install/etc.) + tools + cautions for a part, parsed
    from the manual pages that describe it, each cited to its real page. Read-only; improves with OCR."""
    q = (query or "").strip()
    if not q: return {"query": "", "found": False, "procedures": []}
    con = core.db(); nom = None; ref = norm_nsn(q)
    rows = []
    try:
        if ref:
            r = con.execute("SELECT COALESCE(NULLIF(name,''),NULLIF(nomenclature,''),fig_title) AS nom "
                            "FROM parts WHERE nsn=? AND COALESCE(name,nomenclature,fig_title) IS NOT NULL LIMIT 1", (ref,)).fetchone()
            if r: nom = r["nom"]
        if not nom: nom = q
        terms = [t for t in re.findall(r"[A-Za-z0-9]+", nom) if len(t) > 1]
        phrase = '"' + " ".join(terms) + '"' if terms else nom
        match = phrase + ' AND (removal OR installation OR remove OR install OR disassembly OR assembly OR replace OR adjustment OR service)'
        try:
            rows = con.execute(
                "SELECT d.id AS doc_id, d.vehicle, d.tm_number, d.title, p.page_number, p.body_text, p.source "
                "FROM pages_fts JOIN pages p ON p.id=pages_fts.rowid JOIN documents d ON d.id=p.document_id "
                "WHERE pages_fts MATCH ? ORDER BY rank LIMIT ?", (match, limit*3)).fetchall()
        except sqlite3.OperationalError:
            rows = []
    except sqlite3.OperationalError:
        rows = []
    # v1.13.4: dedup by (tm_number, page) not (doc_id, page) -- the corpus holds confirmed duplicate
    # ingestions of the same manual (same TM/page, different doc_id; the same root cause already fixed
    # in faulttree.py's find_for_query()), so keying on doc_id let every duplicate copy fill its own
    # result slot with an identical procedure instead of surfacing distinct ones.
    out = []; seen = {}
    for r in rows:
        pr = _parse_procedure(r["body_text"])
        if not pr: continue
        kk = (r["tm_number"] or "", r["page_number"])
        if kk in seen:
            seen[kk]["dupe_copies"] = seen[kk].get("dupe_copies", 1) + 1
            continue
        pr.update({"doc_id": r["doc_id"], "vehicle": r["vehicle"], "tm_number": r["tm_number"],
                   "doc_title": r["title"], "page": r["page_number"], "source": r["source"]})
        seen[kk] = pr
        out.append(pr)
        if len(out) >= limit: break
    con.close()
    return {"query": q, "nomenclature": nom, "found": bool(out), "n": len(out), "procedures": out}


_TORQUE_RE = re.compile(
    r"(\d{1,4}(?:\.\d+)?)\s*(?:(?:-|to|–)\s*(\d{1,4}(?:\.\d+)?)\s*)?"
    r"(ft[\s\-\.]?lb[s]?|lb[s]?[\s\-\.]?ft|foot[\s\-]?pound[s]?|in[\s\-\.]?lb[s]?|inch[\s\-]?pound[s]?|n[\s·\.]?m|newton[\s\-]?met(?:er|re)[s]?)",
    re.I)


def _norm_unit(u):
    u = u.lower().replace(" ", "").replace(".", "").replace("-", "")
    if u.startswith("n") and ("m" in u or "newton" in u): return "N·m"
    if "in" in u or "inch" in u: return "in-lb"
    return "ft-lb"


def torque_specs(query, limit=14):
    """Find torque values stated in the manuals for a part: sentences mentioning torque/tighten near a
    number + unit (ft-lb / in-lb / N·m), each cited to its page. Read-only; grows with OCR."""
    q = (query or "").strip()
    if not q: return {"query": "", "found": False, "specs": []}
    con = core.db(); nom = None; ref = norm_nsn(q)
    rows = []
    try:
        if ref:
            r = con.execute("SELECT COALESCE(NULLIF(name,''),NULLIF(nomenclature,''),fig_title) AS nom "
                            "FROM parts WHERE nsn=? AND COALESCE(name,nomenclature,fig_title) IS NOT NULL LIMIT 1", (ref,)).fetchone()
            if r: nom = r["nom"]
        if not nom: nom = q
        terms = [t for t in re.findall(r"[A-Za-z0-9]+", nom) if len(t) > 1]
        phrase = '"' + " ".join(terms) + '"' if terms else nom
        match = phrase + ' AND (torque OR tighten OR "ft-lb" OR "lb-ft")'
        try:
            rows = con.execute(
                "SELECT d.id AS doc_id, d.vehicle, d.tm_number, p.page_number, p.body_text "
                "FROM pages_fts JOIN pages p ON p.id=pages_fts.rowid JOIN documents d ON d.id=p.document_id "
                "WHERE pages_fts MATCH ? ORDER BY rank LIMIT ?", (match, limit*2)).fetchall()
        except sqlite3.OperationalError:
            rows = []
    except sqlite3.OperationalError:
        rows = []
    con.close()
    specs = []; seen = set()
    for r in rows:
        bt = r["body_text"] or ""
        for sent in re.split(r"(?<=[\.\n])\s+", bt):
            low = sent.lower()
            if "torque" not in low and "tighten" not in low: continue
            for m in _TORQUE_RE.finditer(sent):
                v1, v2, unit = m.group(1), m.group(2), _norm_unit(m.group(3))
                val = v1 + ("–" + v2 if v2 else "") + " " + unit
                ctx = re.sub(r"\s+", " ", sent).strip()[:160]
                key = (val, ctx[:40])
                if key in seen: continue
                seen.add(key)
                specs.append({"value": val, "context": ctx, "page": r["page_number"],
                              "doc_id": r["doc_id"], "vehicle": r["vehicle"], "tm_number": r["tm_number"]})
                if len(specs) >= limit: break
            if len(specs) >= limit: break
        if len(specs) >= limit: break
    return {"query": q, "nomenclature": nom, "found": bool(specs), "n": len(specs), "specs": specs}
