#!/usr/bin/env python3
"""THE VIEWER -- reconstituted Fix/procedure engine (deepened parser + correlation).

Pulls a how-to/fix procedure out of the OCR'd manual text and rebuilds it as a clean, structured object the
UI renders as a dedicated step-by-step page (side-by-side with the original scan, exportable, correlated to
the parts + fault). Read-only on the index; shared primitives come from viewer_app via injected `core`
(no import cycle). The text is verbatim from the manual -- steps are never invented.

API:  procedure_full(query, limit=6) -> {found, title, kind, source{doc_id,page,tm,vehicle}, tools[],
        warnings[{level,text}], steps[{n,text,subs[],torque[],figs[],nsns[],pns[]}], parts[{nsn}], fault_terms[]}
"""
import re
core = None   # injected by viewer_app: _pf.core = sys.modules[__name__]

try:
    from patterns import NSN_RE, FIG_RE, PN_RE, norm_nsn, nsn_fts_phrase
except Exception:                      # standalone/test fallback
    NSN_RE = re.compile(r"\b(\d{4})-?(\d{2})-?(\d{3})-?(\d{4})\b")   # \b-anchored -- see patterns.py's NSN_RE
    FIG_RE = re.compile(r"\bFIG(?:URE)?\.?\s*([0-9]+(?:-[0-9]+)?)", re.I)
    PN_RE  = re.compile(r"\b(?:P/N|PART\s*N[O0]\.?|PART\s*NUMBER)\.?\s*[:\-]?\s*([A-Z0-9][A-Z0-9\-]{3,16})", re.I)
    def norm_nsn(s):
        m = NSN_RE.search((s or "").strip())
        return ("%s-%s-%s-%s" % m.groups()) if m else None

# torque/spec values: 35 ft-lb, 50 lb-ft, 12 N·m, 90 in-lb, 1/4-20 (left in step text too, captured for the chip)
TORQUE_RE = re.compile(r"\b(\d+(?:\.\d+)?(?:\s*-\s*\d+(?:\.\d+)?)?)\s*(ft[\s\-]?lbf?|lb[\s\-]?ft|in[\s\-]?lbf?|n[\s·\.\-]?m|newton[\s\-]?met(?:er|re)s?)\b", re.I)
_WARN_RE = re.compile(r"^\s*\**\s*(DANGER|WARNING|CAUTION|NOTE)\b[:.\-]?\s*(.*)$", re.I)
_STEP_RE = re.compile(r"^\s*(\d{1,3})[.)]\s+(.*)$")
_SUB_RE  = re.compile(r"^\s*(?:\(?([a-z])[.)]|\(([0-9]{1,2})\))\s+(.*)$")   # a.  a)  (a)  (1)  -- not capital sentence starts
_TOOLS_HDR = re.compile(r"\b(TOOLS?\s+REQUIRED|TOOLS?\s+AND\s+(?:MATERIALS?|EQUIPMENT)|SPECIAL\s+TOOLS?)\b", re.I)
_KIND_RE = [
    ("removal", re.compile(r"\bREMOV(E|AL)\b|\bDISASSEMBL", re.I)),
    ("installation", re.compile(r"\bINSTALL(ATION)?\b|\bASSEMBL|\bREPLACE", re.I)),
    ("adjustment", re.compile(r"\bADJUST(MENT)?\b|\bCALIBRAT", re.I)),
    ("inspection", re.compile(r"\bINSPECT(ION)?\b|\bCHECK\b|\bTEST\b", re.I)),
]
_END_HDR = re.compile(r"\b(WARNING|CAUTION|NOTE|DANGER|REMOVAL|INSTALLATION|FOLLOW[- ]ON|END OF (TASK|WORK))\b", re.I)

def _kind(text):
    for k, rx in _KIND_RE:
        if rx.search(text or ""): return k
    return "procedure"

def _enrich_line(s):
    return {"torque": ["%s %s" % (m.group(1).strip(), m.group(2).strip()) for m in TORQUE_RE.finditer(s)],
            "figs": sorted(set(FIG_RE.findall(s))),
            "nsns": sorted({norm_nsn(m.group(0)) for m in NSN_RE.finditer(s) if norm_nsn(m.group(0))}),
            "pns": sorted({m.group(1).upper() for m in PN_RE.finditer(s)})}

def parse_procedure(text, title=""):
    """Deepened parse: tools, classified warnings (NOTE/CAUTION/WARNING/DANGER), numbered steps with
    sub-steps, and per-step torque / figure / NSN / part-number callouts. Verbatim text."""
    lines = [ln.rstrip() for ln in re.split(r"\r?\n", text or "")]
    tools, warnings, steps = [], [], []
    cur = None; in_tools = False; i = 0
    while i < len(lines):
        ln = lines[i]; s = ln.strip()
        if not s: in_tools = False; i += 1; continue
        wm = _WARN_RE.match(ln)
        if wm:
            body = wm.group(2).strip()
            j = i + 1
            while j < len(lines) and lines[j].strip() and not _STEP_RE.match(lines[j]) and not _WARN_RE.match(lines[j]):
                body = (body + " " + lines[j].strip()).strip(); j += 1
            warnings.append({"level": wm.group(1).upper(), "text": body[:400]}); i = j; continue
        if _TOOLS_HDR.search(s): in_tools = True; i += 1; continue
        if in_tools:
            if _END_HDR.search(s) or _STEP_RE.match(ln): in_tools = False
            else:
                for piece in re.split(r"[;,]| and ", s):
                    p = piece.strip(" .-")
                    if len(p) >= 2 and not p.isdigit(): tools.append(p)
                i += 1; continue
        sm = _STEP_RE.match(ln)
        if sm:
            cur = {"n": int(sm.group(1)), "text": sm.group(2).strip(), "subs": []}
            cur.update(_enrich_line(cur["text"])); steps.append(cur); i += 1; continue
        subm = _SUB_RE.match(ln)
        if subm and cur is not None:
            cur["subs"].append((subm.group(3) or "").strip()); i += 1; continue
        if cur is not None and not _END_HDR.search(s):     # continuation of the current step
            cur["text"] = (cur["text"] + " " + s).strip()
            e = _enrich_line(s)
            for k in ("torque", "figs", "nsns", "pns"):
                cur[k] = sorted(set(cur.get(k, []) + e[k]))
        i += 1
    # de-dup tools (case-insensitive), cap
    seen = set(); tools2 = []
    for t in tools:
        if t.lower() not in seen: seen.add(t.lower()); tools2.append(t)
    return {"title": title, "kind": _kind((title or "") + " " + (text or "")),
            "tools": tools2[:24], "warnings": warnings[:12], "steps": steps[:120]}

def procedure_full(query, limit=6):
    """Find the best procedure for a query in the OCR'd text and return the reconstituted structure +
    its source page (for side-by-side) + correlated parts (NSNs in the steps) + the fault terms."""
    out = {"found": False, "query": query}
    if core is None: return out
    q = (query or "").strip()
    if not q: return out
    con = core.db()
    # bias toward procedure pages: the query terms NEAR a how-to verb
    verbs = '("removal" OR "remove" OR "install" OR "installation" OR "replace" OR "adjust" OR "disassembly" OR "assembly")'
    terms = " ".join('"%s"' % t for t in re.findall(r"[A-Za-z0-9]{3,}", q)[:6]) or '"%s"' % q
    rows = []
    try:
        rows = con.execute(
            "SELECT d.id doc_id, d.tm_number, d.vehicle, p.page_number, p.body_text "
            "FROM pages_fts JOIN pages p ON p.id=pages_fts.rowid JOIN documents d ON d.id=p.document_id "
            "WHERE pages_fts MATCH ? ORDER BY rank LIMIT ?", ("(%s) AND %s" % (terms, verbs), limit)).fetchall()
        if not rows:
            rows = con.execute(
                "SELECT d.id doc_id, d.tm_number, d.vehicle, p.page_number, p.body_text "
                "FROM pages_fts JOIN pages p ON p.id=pages_fts.rowid JOIN documents d ON d.id=p.document_id "
                "WHERE pages_fts MATCH ? ORDER BY rank LIMIT ?", (terms, limit)).fetchall()
    except Exception:
        rows = []
    finally:
        try: con.close()                  # audit fix v0.72.3: was leaking one connection per call
        except Exception: pass
    best = None
    for r in rows:
        pr = parse_procedure(r["body_text"] or "", title=q)
        score = len(pr["steps"]) * 3 + len(pr["warnings"]) + len(pr["tools"])
        if best is None or score > best[0]:
            best = (score, r, pr)
    if not best or best[0] <= 0:
        return out
    score, r, pr = best
    # Recommendations annex #11 (cautions-single-page): a TM's WARNING/CAUTION/DANGER box commonly
    # precedes the steps it gates, printed at the bottom of the PRECEDING page -- procedure_full()
    # only ever parsed the single best-matched page, so that callout was silently absent. Look back
    # exactly ONE page (not further -- a warning further back risks belonging to a different work
    # package entirely, and this app has no reliable WP-boundary signal to check against), scoped to
    # just the tail (~12 non-blank-ish lines) so unrelated body text from that prior page isn't
    # dragged in as if it were part of this procedure. Every warning is tagged with the page it
    # actually came from (mirrors cautions.py's own per-callout page tagging) so the UI can cite it
    # correctly rather than implying every warning is on the matched page.
    warnings = [dict(w, page=r["page_number"]) for w in pr["warnings"]]
    try:
        con2 = core.db()
        try:
            prev = con2.execute(
                "SELECT body_text FROM pages WHERE document_id=? AND page_number=?",
                (r["doc_id"], r["page_number"] - 1)).fetchone()
        finally:
            con2.close()
        if prev and prev["body_text"]:
            tail_lines = [l for l in prev["body_text"].splitlines() if l.strip()][-12:]
            if tail_lines:
                lead_pr = parse_procedure("\n".join(tail_lines), title=q)
                lead = [dict(w, page=r["page_number"] - 1) for w in lead_pr["warnings"]]
                warnings = (lead + warnings)[:12]
    except Exception as e:
        out["warnings_error"] = str(e)
    nsns = sorted({n for st in pr["steps"] for n in st.get("nsns", [])})
    out.update({"found": True, "title": q, "kind": pr["kind"],
                "source": {"doc_id": r["doc_id"], "page": r["page_number"], "tm": r["tm_number"], "vehicle": r["vehicle"]},
                "tools": pr["tools"], "warnings": warnings, "steps": pr["steps"],
                "parts": [{"nsn": n} for n in nsns],
                "fault_terms": re.findall(r"[A-Za-z0-9]{3,}", q)[:6]})
    return out
