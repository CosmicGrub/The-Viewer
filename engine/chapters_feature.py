#!/usr/bin/env python3
"""THE VIEWER -- Phase 2: chapter-level routing inside COMBINED manuals (TM ...-12/-13/-14).

A combined manual is two books in one cover: operator chapters AND maintenance chapters on different pages.
This maps page ranges to a side so an operator opens the operator chapters (not page 1 of the whole book),
and a mechanic opens the maintenance chapters -- while either can jump to the other section.

How: scan the OCR'd page text (already in the index) for chapter/section headings, classify each heading to
operator / mechanic / both via a vetted lexicon, and build contiguous page ranges. Lazy + cached per doc
(persisted to chapter_sides.json), override-able (chapter_override.json), and it FALLS BACK to whole-book when
no headings are found -- so it can never be worse than the document-level split.

Read-only on the index (R1/R6). Stdlib only (regex/json), RPS-safe. `core` is injected by viewer_app.
"""
import os, re, json, sqlite3

core = None   # injected: import chapters_feature as _ch; _ch.core = sys.modules[__name__]

_CACHE = {}            # {doc_id: {"sig": page_count, "ranges": [...]}}
_PERSIST_LOADED = False
_OVR = {"mtime": None, "data": {}}

# heading markers: a chapter/section start, or a strong section title
_CHAP_RE = re.compile(r"\b(CHAPTER|SECTION)\s+([0-9]+|[IVXLC]+)\b", re.I)
_OPER_RE = re.compile(r"\bOPERAT(?:OR|ING|ION)\b|OPERATOR'?S?\s+(?:INSTRUCTIONS|PMCS|CONTROLS)|"
                      r"\bOPERATION\s+UNDER\b|\bCONTROLS\s+AND\s+INDICATORS\b", re.I)
_MECH_RE = re.compile(r"\bUNIT\s+MAINTENANCE\b|\bORGANIZATIONAL\s+MAINTENANCE\b|\bFIELD\s+MAINTENANCE\b|"
                      r"\bDIRECT\s+SUPPORT\b|\bGENERAL\s+SUPPORT\b|MAINTENANCE\s+ALLOCATION\s+CHART|"
                      r"\bREPAIR\s+PARTS\b|\bRPSTL\b|\bTROUBLESHOOTING\b|\bSCHEMATIC", re.I)


def _persist_path():
    return os.path.join(os.path.dirname(core.DB_PATH), "chapter_sides.json")

def _override_path():
    return os.path.join(os.path.dirname(core.DB_PATH), "chapter_override.json")


def _load_persist():
    global _PERSIST_LOADED
    if _PERSIST_LOADED:
        return
    _PERSIST_LOADED = True
    p = _persist_path()
    if os.path.exists(p):
        try:
            with open(p, "r", encoding="utf-8") as f:
                for k, v in (json.load(f) or {}).items():
                    _CACHE[int(k)] = v
        except Exception:
            pass


def _save_persist():
    try:
        import safeguard          # v1.13: durable atomic write (fsync + retry)
        safeguard.atomic_write(_persist_path(), json.dumps({str(k): v for k, v in _CACHE.items()}))
    except Exception:
        pass


def load_overrides():
    p = _override_path()
    try: mt = os.path.getmtime(p)
    except OSError: _OVR["mtime"] = None; _OVR["data"] = {}; return {}
    if _OVR["mtime"] == mt: return _OVR["data"]
    data = {}
    try:
        with open(p, "r", encoding="utf-8") as f: data = json.load(f) or {}
    except Exception: data = {}
    _OVR["mtime"] = mt; _OVR["data"] = data
    return data


def save_override(doc_id, side, page):
    if side not in ("operator", "mechanic"):
        return {"ok": False, "error": "side must be operator|mechanic"}
    try: page = max(1, int(page))
    except Exception: return {"ok": False, "error": "page must be an integer"}
    p = _override_path(); blob = {}
    if os.path.exists(p):
        try:
            with open(p, "r", encoding="utf-8") as f: blob = json.load(f) or {}
        except Exception: blob = {}
    blob.setdefault(str(int(doc_id)), {})[side] = page
    import safeguard; safeguard.atomic_write(p, json.dumps(blob, indent=2))          # v1.13: fsync + retry
    _OVR["mtime"] = None
    return {"ok": True, "doc_id": int(doc_id), "side": side, "page": page}


def _heading_side(head):
    """Classify a page-head string to a side, or None if it isn't a recognizable chapter/section heading."""
    if not _CHAP_RE.search(head) and not _OPER_RE.search(head) and not _MECH_RE.search(head):
        return None
    op = bool(_OPER_RE.search(head)); me = bool(_MECH_RE.search(head))
    if op and me: return "both"
    if op: return "operator"
    if me: return "mechanic"
    return None      # a generic CHAPTER/SECTION with no side word -> inherit previous (handled by caller)


def _build_ranges(con, doc_id):
    """Scan a doc's pages for chapter headings and produce contiguous {start,end,side,heading} ranges."""
    try:
        rows = con.execute("SELECT page_number, substr(COALESCE(body_text,''),1,300) AS head "
                           "FROM pages WHERE document_id=? ORDER BY page_number", (doc_id,)).fetchall()
    except Exception:
        return []
    marks = []   # (page, side, heading)
    last_side = None
    for r in rows:
        head = (r["head"] or "")
        # normalize whitespace for matching
        h = re.sub(r"\s+", " ", head).strip()
        side = _heading_side(h)
        if side is None:
            continue
        if side == "both":
            # a combined chapter heading -> mark as 'both' (front matter / general)
            marks.append((r["page_number"], "both", h[:80])); last_side = "both"; continue
        marks.append((r["page_number"], side, h[:80])); last_side = side
    if not marks:
        return []
    # build ranges: each mark spans until the next mark's page-1; last to end
    end_page = rows[-1]["page_number"] if rows else marks[-1][0]
    ranges = []
    for i, (pg, side, heading) in enumerate(marks):
        nxt = marks[i + 1][0] - 1 if i + 1 < len(marks) else end_page
        if nxt < pg: nxt = pg
        if ranges and ranges[-1]["side"] == side and ranges[-1]["end"] + 1 >= pg:
            ranges[-1]["end"] = nxt                      # merge consecutive same-side
        else:
            ranges.append({"start": pg, "end": nxt, "side": side, "heading": heading})
    return ranges


def _doc_row(con, doc_id):
    try:
        return con.execute("SELECT id, tm_number, title, path, page_count FROM documents WHERE id=?",
                           (doc_id,)).fetchone()
    except sqlite3.OperationalError:
        # schema drift (older/partial DB) -- degrade to "not found" (chapters() already treats that as
        # "not a combined manual, use whole-book") instead of 500ing. Logged so a real, persistent DB
        # problem for a valid doc_id doesn't silently look identical to "no such document" forever.
        try: core.log_exception("chapters._doc_row")
        except Exception: pass
        return None


def chapters(doc_id):
    """Ranges + per-side landing pages for a doc. combined=False -> caller uses whole-book (current behaviour)."""
    _load_persist()
    doc_id = int(doc_id)
    con = core.db()
    try:
        row = _doc_row(con, doc_id)
        if not row:
            return {"doc_id": doc_id, "combined": False, "ranges": []}
        cls = core.tm_side(row["tm_number"] or "", row["title"] or "", row["path"] or "")
        combined = bool(cls["operator"] and cls["mechanic"])
        if not combined:
            return {"doc_id": doc_id, "combined": False, "ranges": []}
        sig = row["page_count"] or 0
        cached = _CACHE.get(doc_id)
        if not cached or cached.get("sig") != sig:
            ranges = _build_ranges(con, doc_id)
            _CACHE[doc_id] = {"sig": sig, "ranges": ranges}
            _save_persist()
        ranges = _CACHE[doc_id]["ranges"]
    finally:
        try: con.close()
        except Exception: pass

    def first_for(side):
        for rg in ranges:
            if rg["side"] == side:
                return rg["start"]
        return None
    ov = load_overrides().get(str(doc_id), {})
    op_pg = ov.get("operator") or first_for("operator")
    me_pg = ov.get("mechanic") or first_for("mechanic")
    return {"doc_id": doc_id, "combined": True, "ranges": ranges,
            "operator_page": op_pg, "mechanic_page": me_pg,
            "has_chapters": bool(ranges)}


def jump(doc_id, side):
    """First page for a side in a combined manual (override > first chapter > page 1)."""
    info = chapters(doc_id)
    if not info.get("combined"):
        return {"doc_id": int(doc_id), "side": side, "page": 1, "combined": False}
    pg = info.get("operator_page") if side == "operator" else info.get("mechanic_page")
    return {"doc_id": int(doc_id), "side": side, "page": pg or 1, "combined": True,
            "has_chapters": info.get("has_chapters", False)}


def review(limit=300):
    """List the COMBINED manuals + their detected chapter splits, for the review UI. Flags the ones with NO
    detected chapters (whole-book fallback) and the ones with a manual override, so a human can spot-check
    and correct them. Counts are cheap (cached); building ranges is lazy + cached per doc."""
    con = core.db()
    try:
        try:
            rows = con.execute("SELECT id, tm_number, title, path, page_count FROM documents "
                               "WHERE type LIKE 'pdf%' ORDER BY COALESCE(tm_number,''), id").fetchall()
        except sqlite3.OperationalError:
            # schema drift -- degrade to an empty review list instead of 500ing. Logged: this endpoint
            # backs the human chapter-audit UI, so a silent empty result would misread as "nothing to
            # review" rather than "the query never ran."
            try: core.log_exception("chapters.review")
            except Exception: pass
            rows = []
        combined = []
        for r in rows:
            cls = core.tm_side(r["tm_number"] or "", r["title"] or "", r["path"] or "")
            if cls["operator"] and cls["mechanic"]:
                combined.append(r)
    finally:
        try: con.close()
        except Exception: pass
    ov = load_overrides()
    items = []
    no_chapters = 0
    for r in combined[:max(1, min(int(limit), 1000))]:
        info = chapters(r["id"])
        if not info.get("has_chapters"):
            no_chapters += 1
        items.append({"doc_id": r["id"], "tm": r["tm_number"], "title": r["title"],
                      "pages": r["page_count"], "has_chapters": info.get("has_chapters", False),
                      "ranges": info.get("ranges", []),
                      "operator_page": info.get("operator_page"), "mechanic_page": info.get("mechanic_page"),
                      "overridden": str(r["id"]) in ov})
    return {"combined_total": len(combined), "shown": len(items),
            "no_chapters": no_chapters, "items": items}
