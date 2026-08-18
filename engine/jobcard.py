#!/usr/bin/env python3
"""THE VIEWER -- JOB CARD / WORK ORDER (v0.99.10): one printable take-to-the-bay PDF for a TASK, not just a part.
Composes pieces already in the app -- procedure steps + tools + materials + referenced manuals + WARNING/CAUTION/NOTE
callouts (procedures_feature), torque values (procedures_feature), the parts that appear on the part's figures
(partlocate + figureparts), the rendered figure pages (fitz), and a LOOK-ALIKE NSN warning (parts_feature.part_differences)
-- into a single work order. Understands free-text tasks ('replace the alternator') via lightweight intent parsing that
biases the right procedure kind to the top. Pure reportlab + PyMuPDF + Pillow, offline. Read-only; db_path explicit; the
text sections + look-alike are gathered by the route from the live features and passed in."""
import os, io, re, time, sqlite3

# ---- palette ------------------------------------------------------------------------------------------
_DARK = (0.07, 0.09, 0.12); _INK = (0.90, 0.93, 0.96); _ACC = (0.50, 0.66, 0.90)
_SUB = (0.55, 0.60, 0.68); _WARN = (0.95, 0.55, 0.35); _OK = (0.45, 0.80, 0.55); _RULE = (0.20, 0.24, 0.30)

# ---- task intent --------------------------------------------------------------------------------------
_VERB_KIND = [
    (r"\b(remov|take\s*off|detach|dismount)", "Removal"),
    (r"\b(install|refit|reinstall|mount|attach|fit)", "Installation"),
    (r"\b(disassembl|tear\s*down|break\s*down)", "Disassembly"),
    (r"\b(assembl|build\s*up|reassembl)", "Assembly"),
    (r"\b(replac|swap|change\s*out|r\s*&\s*r|r&r|r/r)", "Replacement"),
    (r"\b(adjust|align|set|calibrat|time|tension)", "Adjustment"),
    (r"\b(inspect|check|examine|test)", "Inspection"),
    (r"\b(repair|fix|rebuild|overhaul)", "Repair"),
    (r"\b(servic|lubricat|clean|drain|fill|bleed|torque|tighten)", "Service"),
]
_STOP = set("the a an on of to for and from with my your his her its our this that these those into onto at in".split())


def _task_intent(q):
    """Return {'kind': canonical procedure kind or None, 'verb': matched verb display, 'focus': the part/noun phrase}."""
    low = (q or "").lower(); kind = None; verb = None
    for rx, k in _VERB_KIND:
        m = re.search(rx, low)
        if m: kind = k; verb = m.group(0); break
    focus_words = [w for w in re.findall(r"[A-Za-z0-9\-]+", q or "") if w.lower() not in _STOP]
    if verb:
        focus_words = [w for w in focus_words if not re.match(_VERB_KIND[[k for _, k in _VERB_KIND].index(kind)][0], w.lower())]
    focus = " ".join(focus_words).strip() or (q or "")
    return {"kind": kind, "verb": verb, "focus": focus}


def _order_procs(procedures, kind):
    """Put procedures whose kind matches the task intent first (stable)."""
    if not kind: return list(procedures)
    return sorted(procedures, key=lambda p: 0 if (p.get("kind") == kind) else 1)


def _lookalike_warning(lookalike):
    """From parts_feature.part_differences -> a one-line safety warning, or None."""
    if not lookalike or not lookalike.get("found"):
        return None
    real = [v for v in lookalike.get("variants", []) if v.get("relation") in ("different variant", "different item class")]
    n = lookalike.get("n_variants", 0)
    if n > 1 and real:
        fields = ", ".join(d["field"] for d in lookalike.get("discriminators", [])[:5]) or "NSN"
        return ("LOOK-ALIKE: %d parts share the name “%s” but differ by %s. Confirm the exact NSN/UOC for THIS "
                "vehicle before ordering or installing — see /partdiff.") % (n, (lookalike.get("nomenclature") or "")[:40], fields)
    return None


def _lookalike_index(lookalike):
    """(set of variant NSNs, lowered nomenclature) IF the look-alike has REAL differences — else empty."""
    if not lookalike or not lookalike.get("found"):
        return set(), ""
    real = any(v.get("relation") in ("different variant", "different item class") for v in lookalike.get("variants", []))
    if not real:
        return set(), ""
    nsns = set(v.get("nsn") for v in lookalike.get("variants", []) if v.get("nsn"))
    return nsns, (lookalike.get("nomenclature") or "").strip().lower()


def _flag_lookalikes(parts, lookalike):
    """Mark parts on the figures that are among the task's look-alike variants (congruent with /partdiff)."""
    nsns, nom = _lookalike_index(lookalike)
    if not nsns and not nom:
        return parts
    for p in parts:
        if (p.get("nsn") and p["nsn"] in nsns) or (nom and (p.get("name") or "").strip().lower() == nom):
            p["lookalike"] = True
    return parts


# ---- low-level reportlab text cursor ------------------------------------------------------------------
def _wrap(c, text, font, size, max_w):
    from reportlab.pdfbase.pdfmetrics import stringWidth
    words = str(text or "").split(); lines = []; cur = ""
    for w in words:
        t = (cur + " " + w).strip()
        if stringWidth(t, font, size) <= max_w: cur = t
        else:
            if cur: lines.append(cur)
            cur = w
    if cur: lines.append(cur)
    return lines or [""]


class _Pen:
    def __init__(self, c, W, H, margin=48):
        self.c = c; self.W = W; self.H = H; self.m = margin; self.x = margin; self.y = H - margin; self._new_bg()
    def _new_bg(self):
        self.c.setFillColorRGB(*_DARK); self.c.rect(0, 0, self.W, self.H, fill=1, stroke=0)
        self.c.setFillColorRGB(*_SUB); self.c.setFont("Helvetica-Oblique", 7.5)
        self.c.drawRightString(self.W - self.m, 30, "THE VIEWER · Work Order · verify every step on the cited TM page before performing maintenance")
    def _room(self, h):
        if self.y - h < self.m + 24:
            self.c.showPage(); self._new_bg(); self.y = self.H - self.m
    def gap(self, h=8): self.y -= h
    def line(self, text, font="Helvetica", size=10, color=_INK, indent=0, lead=None):
        lead = lead or (size + 3)
        for ln in _wrap(self.c, text, font, size, self.W - 2 * self.m - indent):
            self._room(lead); self.c.setFillColorRGB(*color); self.c.setFont(font, size)
            self.c.drawString(self.x + indent, self.y - size, ln); self.y -= lead
    def rule(self):
        self._room(10); self.c.setStrokeColorRGB(*_RULE); self.c.setLineWidth(0.7)
        self.c.line(self.m, self.y - 3, self.W - self.m, self.y - 3); self.y -= 12
    def heading(self, text, color=_ACC):
        self.gap(6); self.line(text, "Helvetica-Bold", 13, color); self.rule()


# ---- PDF assembly -------------------------------------------------------------------------------------
def build_pdf(meta, procedures, torque, parts, figure_items, warnings=None):
    """meta={task,label,nsn,subtitle,intent}; procedures/torque/parts=dict lists; figure_items=[(PIL,caption)];
    warnings=[str]. Returns PDF bytes."""
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas as rlc
    from reportlab.lib.utils import ImageReader
    buf = io.BytesIO(); c = rlc.Canvas(buf, pagesize=letter); W, H = letter
    label = (meta.get("label") or meta.get("task") or "").strip()
    intent = meta.get("intent") or {}
    warnings = [w for w in (warnings or []) if w]

    # --- cover ---
    c.setFillColorRGB(*_DARK); c.rect(0, 0, W, H, fill=1, stroke=0)
    c.setFillColorRGB(*_INK); c.setFont("Helvetica-Bold", 26); c.drawString(50, H - 92, "Work Order")
    c.setFillColorRGB(*_ACC); c.setFont("Helvetica-Bold", 16); c.drawString(50, H - 122, label[:74])
    c.setFillColorRGB(*_SUB); c.setFont("Helvetica", 11); y = H - 146
    if intent.get("kind"): c.drawString(50, y, "Task: %s" % intent["kind"]); y -= 16
    if meta.get("nsn"): c.drawString(50, y, "NSN %s" % meta["nsn"]); y -= 16
    if meta.get("subtitle"): c.drawString(50, y, meta["subtitle"][:110]); y -= 16
    c.drawString(50, y, "%d procedure%s · %d torque · %d part%s · %d figure%s · %s" % (
        len(procedures), "" if len(procedures) == 1 else "s", len(torque),
        len(parts), "" if len(parts) == 1 else "s", len(figure_items), "" if len(figure_items) == 1 else "s",
        time.strftime("%Y-%m-%d"))); y -= 24
    # warnings box (look-alike etc.)
    if warnings:
        bh = 20 + 26 * len(warnings)
        c.setFillColorRGB(0.18, 0.09, 0.06); c.roundRect(50, y - bh, W - 100, bh, 7, fill=1, stroke=0)
        c.setStrokeColorRGB(*_WARN); c.setLineWidth(1); c.roundRect(50, y - bh, W - 100, bh, 7, fill=0, stroke=1)
        c.setFillColorRGB(*_WARN); c.setFont("Helvetica-Bold", 10); c.drawString(64, y - 18, "⚠  BEFORE YOU START")
        c.setFillColorRGB(*_INK); c.setFont("Helvetica", 9)
        yy = y - 34
        for w in warnings:
            for ln in _wrap(c, w, "Helvetica", 9, W - 140)[:2]:
                c.drawString(64, yy, ln); yy -= 12
            yy -= 4
        y -= bh + 14
    # contents box
    ch = 150
    c.setFillColorRGB(0.10, 0.12, 0.15); c.roundRect(50, y - ch, W - 100, ch, 8, fill=1, stroke=0)
    c.setFillColorRGB(*_ACC); c.setFont("Helvetica-Bold", 11); c.drawString(66, y - 22, "IN THIS WORK ORDER")
    c.setFillColorRGB(*_INK); c.setFont("Helvetica", 10)
    for i, ln in enumerate(["1.  Procedures — steps, tools, materials, referenced manuals & safety callouts",
                            "2.  Torque values (cited to the page)",
                            "•   Key dimensions & specs (consolidated: manuals + external)",
                            "3.  Parts on the associated figures (NSN / P-N / CAGE / SMR)",
                            "4.  Figure pages (rendered from the source TMs)"]):
        c.drawString(66, y - 44 - i * 20, ln)
    c.setFillColorRGB(*_WARN); c.setFont("Helvetica-Bold", 9.5)
    c.drawString(50, 78, "SAFETY: This work order is assembled from OCR/heuristic parsing of the manuals.")
    c.setFillColorRGB(*_SUB); c.setFont("Helvetica", 9)
    c.drawString(50, 62, "Every step, torque and part is cited — confirm against the referenced TM page image before turning a wrench.")
    c.showPage()

    p = _Pen(c, W, H)

    # --- 1. procedures ---
    p.heading("1 · Procedures")
    if not procedures:
        p.line("No parsed procedure pages matched this task. Try /procedure or open the figures below.", "Helvetica-Oblique", 10, _SUB)
    for pr in procedures:
        cite = "%s · %s · p.%s" % (pr.get("vehicle") or "?", pr.get("tm_number") or "", pr.get("page") or "?")
        p.gap(4); p.line("%s — %s" % (pr.get("kind") or "Procedure", (pr.get("title") or "").strip() or label), "Helvetica-Bold", 11.5, _INK)
        p.line(cite, "Helvetica-Oblique", 8.5, _SUB)
        for ca in (pr.get("cautions") or [])[:8]:
            # Review finding (R13 safety-relevant): the Work Order PDF -- explicitly the take-to-the-bay,
            # away-from-the-screen document per this module's own header -- never showed the OCR-quality
            # confidence its sibling jobpack.py Job Packet PDF was fixed to show in this same review.
            conf = ca.get("confidence")
            qual = "  (OCR quality: %s -- verify on page)" % conf if conf and conf != "clean" else ""
            p.line("%s: %s%s" % (ca.get("kind", "NOTE"), ca.get("text", ""), qual), "Helvetica-Bold", 9, _WARN, indent=8)
        if pr.get("tools"):
            p.gap(2); p.line("Tools / test equipment:", "Helvetica-Bold", 9.5, _ACC, indent=4)
            for tl in pr["tools"][:20]: p.line("• " + tl, "Helvetica", 9, _INK, indent=14)
        if pr.get("materials"):
            p.gap(2); p.line("Materials / consumables:", "Helvetica-Bold", 9.5, _ACC, indent=4)
            for ml in pr["materials"][:20]: p.line("• " + ml, "Helvetica", 9, _INK, indent=14)
        if pr.get("steps"):
            p.gap(2); p.line("Steps:", "Helvetica-Bold", 9.5, _ACC, indent=4)
            for i, st in enumerate(pr["steps"][:40], 1): p.line("%d.  %s" % (i, st), "Helvetica", 9.5, _INK, indent=14)
        if pr.get("references"):
            p.gap(1); p.line("Referenced manuals: " + " · ".join(pr["references"][:12]), "Helvetica-Oblique", 8.5, _SUB, indent=4)
        p.gap(6)

    # --- 2. torque ---
    p.heading("2 · Torque values")
    if not torque:
        p.line("No torque values found in the cited pages for this task.", "Helvetica-Oblique", 10, _SUB)
    for sp in torque[:30]:
        cite = "%s · %s · p.%s" % (sp.get("vehicle") or "?", sp.get("tm_number") or "", sp.get("page") or "?")
        p.line("%s" % sp.get("value", "?"), "Helvetica-Bold", 11, _OK, indent=4)
        p.line((sp.get("context") or "").strip(), "Helvetica", 9, _INK, indent=16)
        p.line(cite, "Helvetica-Oblique", 8, _SUB, indent=16); p.gap(3)

    # --- key dimensions & specs (consolidated Masterfile: corpus authoritative + external supplemental) ---
    dims = meta.get("dimensions") or []
    if dims:
        p.heading("Key dimensions & specs (consolidated)")
        p.line("Authoritative values are from the manuals; \"ext\" = external reference, unconfirmed — verify before use.",
               "Helvetica-Oblique", 8.5, _SUB, indent=6)
        for d in dims[:40]:
            span = ""
            if d.get("low") and d.get("high") and d.get("low") != d.get("high"):
                span = "  (range %s-%s)" % (d["low"], d["high"])
            tag = "" if d.get("authoritative") else "   [ext · unconfirmed]"
            col = _INK if d.get("authoritative") else _WARN
            p.line("• %-12s %s %s%s%s" % (d.get("type", ""), d.get("value", ""), d.get("unit", ""), span, tag),
                   "Helvetica-Bold", 9.5, col, indent=6)

    # --- 3. parts ---
    p.heading("3 · Parts on the associated figures")
    if not parts:
        p.line("No indexed parts resolved for this task.", "Helvetica-Oblique", 10, _SUB)
    if any(pt.get("lookalike") for pt in parts):
        p.line("⚠ = this part has look-alike NSNs on file — verify the exact NSN/UOC (see /partdiff).", "Helvetica-Oblique", 8.5, _WARN, indent=6)
    for pt in parts[:80]:
        nm = pt.get("name") or pt.get("part_number") or pt.get("nsn") or "part"
        flag = "⚠ " if pt.get("lookalike") else ""
        extra = " · ".join([x for x in [
            ("NSN " + pt["nsn"]) if pt.get("nsn") else "",
            ("P/N " + pt["part_number"]) if pt.get("part_number") else "",
            ("CAGE " + pt["cagec"]) if pt.get("cagec") else "",
            ("SMR " + pt["smr"]) if pt.get("smr") else ""] if x])
        p.line("• %s%s" % (flag, nm), "Helvetica-Bold", 9.5, (_WARN if pt.get("lookalike") else _INK), indent=6)
        if extra: p.line(extra, "Helvetica", 8.5, _SUB, indent=18)

    # --- 4. figures ---
    if figure_items:
        c.showPage()
        for img, cap in figure_items:
            if img is None: continue
            c.setFillColorRGB(*_DARK); c.rect(0, 0, W, H, fill=1, stroke=0)
            iw, ih = img.size; margin = 38; avail_w = W - 2 * margin; avail_h = H - 2 * margin - 34
            s = min(avail_w / iw, avail_h / ih); dw, dh = iw * s, ih * s; x = (W - dw) / 2; yy = H - margin - dh
            try: c.drawImage(ImageReader(img), x, yy, dw, dh, preserveAspectRatio=True, anchor='n')
            except Exception: pass
            c.setFillColorRGB(0.10, 0.12, 0.15); c.rect(0, 0, W, 32, fill=1, stroke=0)
            c.setFillColorRGB(*_INK); c.setFont("Helvetica", 10); c.drawString(18, 11, (cap or "")[:135])
            c.showPage()
    else:
        c.showPage()
    c.save(); return buf.getvalue()


# ---- data gathering -----------------------------------------------------------------------------------
def _page_image(pdf_path, page, dpi):
    try:
        import pymupdf as fitz
        from PIL import Image
        doc = fitz.open(pdf_path); pix = doc[int(page) - 1].get_pixmap(dpi=int(dpi)); img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples); doc.close(); return img
    except Exception:
        return None


def _gather(db_path, q, max_figs):
    """Return (label, nsn, count, ndocs, parts, appearances)."""
    label = q; nsn = None; count = 0; ndocs = 0; parts = []
    try:
        import partlocate
        r = partlocate.locate(db_path, q, limit=max_figs * 2) or {}
    except Exception:
        r = {}
    aps = r.get("appearances", [])
    if r.get("names"): label = r["names"][0]
    nsn = r.get("nsn"); count = r.get("count", 0); ndocs = r.get("documents", 0)
    try:
        import figureparts
        seen = set()
        for a in aps[:6]:
            fp = figureparts.parts_on(db_path, a["doc"], a["page"], limit=120)
            for pt in fp.get("parts", []):
                key = (pt.get("nsn") or "", (pt.get("part_number") or "").upper(), (pt.get("name") or "").upper())
                if key in seen: continue
                seen.add(key); parts.append(pt)
    except Exception:
        pass
    return label, nsn, count, ndocs, parts, aps


def _master_dims(db_path, subject, limit=40):
    """Consolidated key dimensions for `subject` from the Masterfile (authoritative corpus first, external labelled).
    NO links (the Masterfile never carries them). Fail-soft -> []. Used on the Work Order + builder + dossier."""
    try:
        import masterfile
        mp = os.path.join(os.path.dirname(db_path), "masterfile.db")
        if not os.path.exists(mp):
            return []
        res = masterfile.for_subject(mp, subject)
        return res.get("filtered", [])[:limit]
    except Exception:
        return []


def preview(db_path, q, procedures, torque, lookalike=None, max_figs=8):
    """Structured summary of what a Work Order for `q` would contain — powers /api/jobcard_preview and the builder page."""
    intent = _task_intent(q)
    procedures = _order_procs(procedures or [], intent["kind"])
    label, nsn, count, ndocs, parts, aps = _gather(db_path, q, max_figs)
    dims = _master_dims(db_path, label or q)
    parts = _flag_lookalikes(parts, lookalike)
    warn = _lookalike_warning(lookalike)
    procs_sum = [{"kind": p.get("kind"), "title": p.get("title"), "vehicle": p.get("vehicle"),
                  "tm_number": p.get("tm_number"), "page": p.get("page"),
                  "n_steps": len(p.get("steps") or []), "n_tools": len(p.get("tools") or []),
                  "n_materials": len(p.get("materials") or []), "n_cautions": len(p.get("cautions") or []),
                  "references": (p.get("references") or [])[:8]} for p in procedures]
    return {"task": q, "intent": intent, "label": label, "nsn": nsn,
            "appearances": count, "documents": ndocs,
            "n_procedures": len(procedures), "procedures": procs_sum,
            "n_torque": len(torque or []), "torque_sample": [t.get("value") for t in (torque or [])[:8]],
            "n_parts": len(parts), "n_lookalike_parts": sum(1 for p in parts if p.get("lookalike")),
            "parts_sample": [{"name": p.get("name"), "nsn": p.get("nsn"), "part_number": p.get("part_number"),
                              "lookalike": bool(p.get("lookalike"))} for p in parts[:12]],
            "n_dimensions": len(dims), "n_dimensions_authoritative": sum(1 for d in dims if d.get("authoritative")),
            "dimensions_sample": [{"type": d.get("type"), "value": d.get("value"), "unit": d.get("unit"),
                                   "authoritative": bool(d.get("authoritative"))} for d in dims[:12]],
            "n_figures": min(len(aps), max_figs), "warning": warn}


def jobcard(db_path, q, procedures, torque, lookalike=None, dpi=150, max_figs=8):
    """procedures/torque/lookalike are gathered by the route from the live features. Returns PDF bytes or None."""
    intent = _task_intent(q)
    procedures = _order_procs(procedures or [], intent["kind"])
    label, nsn, count, ndocs, parts, aps = _gather(db_path, q, max_figs)
    parts = _flag_lookalikes(parts, lookalike)
    warn = _lookalike_warning(lookalike)
    dims = _master_dims(db_path, label or q)
    # figure page images
    paths = {}
    if aps:
        try:
            con = sqlite3.connect("file:%s?mode=ro" % db_path, uri=True)
            docs = sorted({a["doc"] for a in aps})
            for row in con.execute("SELECT id, path FROM documents WHERE id IN (%s)" % ",".join("?" * len(docs)), docs):
                paths[row[0]] = row[1]
            con.close()
        except Exception:
            pass
    figure_items = []
    for a in aps[:max_figs]:
        pth = paths.get(a["doc"])
        img = _page_image(pth, a["page"], dpi) if pth else None
        cap = "%s · %s · %s · p.%s" % (a.get("vehicle") or "?", a.get("tm") or "", a.get("fig_no") or "", a["page"])
        figure_items.append((img, cap))
    if not (procedures or torque or parts or figure_items or dims):
        return None
    sub = ("%d appearances across %d documents" % (count, ndocs)) if count else ("query: %s" % q)
    meta = {"task": q, "label": label, "nsn": nsn, "subtitle": sub, "intent": intent, "dimensions": dims}
    return build_pdf(meta, procedures, torque or [], parts, figure_items, warnings=[warn] if warn else None)


if __name__ == "__main__":
    from PIL import Image, ImageDraw
    print("intent 'replace the alternator':", _task_intent("replace the alternator"))
    print("intent 'adjust brakes on M1097':", _task_intent("adjust the brakes on an M1097"))
    print("lookalike warn:", _lookalike_warning({"found": True, "n_variants": 3, "nomenclature": "VALVE",
          "discriminators": [{"field": "UOC"}, {"field": "NSN"}], "variants": [{"relation": "different variant"}]})[:60], "...")
    procs = [{"kind": "Installation", "title": "ALTERNATOR INSTALLATION", "vehicle": "HMMWV M998", "tm_number": "TM 9-2320-280-24P", "page": 216, "tools": ["Socket, 9/16 in"], "materials": ["Lockwasher", "Sealant"], "references": ["TM 9-2320-280-24P", "WP 0057"], "cautions": [{"kind": "WARNING", "text": "Battery ground disconnected."}], "steps": ["Position the alternator.", "Torque the mounting bolts."]},
             {"kind": "Removal", "title": "ALTERNATOR REMOVAL", "vehicle": "HMMWV M998", "tm_number": "TM 9-2320-280-24P", "page": 214, "tools": ["Pry bar"], "materials": [], "references": ["TB 43-0001"], "cautions": [], "steps": ["Disconnect battery.", "Remove bolts."]}]
    tq = [{"value": "30–35 ft-lb", "context": "Tighten to 30-35 ft-lb.", "vehicle": "HMMWV M998", "tm_number": "TM 9-2320-280-24P", "page": 215}]
    parts = [{"name": "ALTERNATOR", "nsn": "2920-01-111-1111", "part_number": "A1", "cagec": "19207", "smr": "PAOZZ"}]
    figs = []
    for k in range(2):
        im = Image.new("RGB", (620, 460), "white"); d = ImageDraw.Draw(im)
        d.rectangle([40, 40, 580, 420], outline="black", width=2); d.text((60, 60), "FIG %d" % (k + 5), fill="black")
        figs.append((im, "HMMWV M998 · TM 9-2320-280-24P · FIG %d · p.%d" % (k + 5, 214 + k)))
    la = {"found": True, "n_variants": 2, "nomenclature": "ALTERNATOR", "discriminators": [{"field": "UOC"}], "variants": [{"relation": "different variant"}]}
    # intent should float Removal/Installation as titled; here simulate 'remove alternator' ordering:
    ordered = _order_procs(procs, _task_intent("remove alternator")["kind"])
    pdf = build_pdf({"task": "remove alternator", "label": "ALTERNATOR", "nsn": "2920-01-111-1111", "subtitle": "2 appearances", "intent": _task_intent("remove alternator")},
                    ordered, tq, parts, figs, warnings=[_lookalike_warning(la)])
    open("/tmp/jobcard_test.pdf", "wb").write(pdf)
    import pymupdf as fitz
    d = fitz.open("/tmp/jobcard_test.pdf")
    print("pdf bytes:", len(pdf), "| valid:", pdf[:5] == b"%PDF-", "| pages:", d.page_count, "| first ordered kind:", ordered[0]["kind"])
    d.close()
