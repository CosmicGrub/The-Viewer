#!/usr/bin/env python3
"""THE VIEWER -- PDF-NATIVE OBJECT EXTRACTOR (v1.2.0, catalog §5.1/5.2/5.3/5.8). Data that isn't 'text on the page':
the document OUTLINE (table of contents / chapter tree), METADATA (title/author/dates), intra-PDF LINKS / named
destinations, and ANNOTATIONS (reviewer notes, highlights). Born-digital TMs and IETMs carry a real chapter tree and
metadata for free -- instant navigation and edition/date correlation without OCR. PyMuPDF only; degrades to empty if
fitz is absent. Read-only on the corpus."""
import os

try:
    import pymupdf as fitz
    _OK = True
except Exception:
    fitz = None; _OK = False


def available():
    return _OK


def metadata(pdf_path):
    """{title, author, subject, keywords, creator, producer, created, modified, pages} or {}."""
    if not _OK or not pdf_path or not os.path.exists(pdf_path):
        return {}
    try:
        d = fitz.open(pdf_path)
        m = dict(d.metadata or {})
        m["pages"] = d.page_count
        d.close()
        return {k: v for k, v in m.items() if v not in (None, "")}
    except Exception:
        return {}


def outline(pdf_path, max_items=4000):
    """The TOC / chapter tree as [{level, title, page}]. Empty if the PDF has no outline."""
    if not _OK or not pdf_path or not os.path.exists(pdf_path):
        return []
    try:
        d = fitz.open(pdf_path)
        toc = d.get_toc(simple=True) or []
        d.close()
        return [{"level": lv, "title": (ti or "").strip()[:200], "page": pg}
                for lv, ti, pg in toc[:max_items] if (ti or "").strip()]
    except Exception:
        return []


def links(pdf_path, page, max_links=200):
    """Intra-PDF links / hyperlinks on a page (1-based) -> [{kind, page, uri}]. kind: 'goto' | 'uri' | 'other'."""
    if not _OK or not pdf_path or not os.path.exists(pdf_path):
        return []
    out = []
    try:
        d = fitz.open(pdf_path); pg = d[int(page) - 1]
        for lk in (pg.get_links() or [])[:max_links]:
            kind = "goto" if lk.get("kind") == fitz.LINK_GOTO else ("uri" if lk.get("kind") == fitz.LINK_URI else "other")
            out.append({"kind": kind, "page": (lk.get("page", -1) + 1) if kind == "goto" else None,
                        "uri": lk.get("uri", "")})
        d.close()
    except Exception:
        return out
    return out


def annotations(pdf_path, page, max_annots=200):
    """Reviewer annotations on a page (1-based) -> [{type, text}]. Captures notes/highlights TMs sometimes carry."""
    if not _OK or not pdf_path or not os.path.exists(pdf_path):
        return []
    out = []
    try:
        d = fitz.open(pdf_path); pg = d[int(page) - 1]
        an = pg.first_annot
        n = 0
        while an is not None and n < max_annots:
            info = an.info or {}
            txt = (info.get("content") or info.get("title") or "").strip()
            if txt:
                out.append({"type": an.type[1] if isinstance(an.type, (list, tuple)) else str(an.type), "text": txt[:300]})
            an = an.next; n += 1
        d.close()
    except Exception:
        return out
    return out


def form_fields(pdf_path, page=None, max_fields=1000):
    """AcroForm fields (fillable IETMs / DA forms) -> [{page, name, type, value}] (catalog §5.4). `page` (1-based) limits
    to one page; None = whole doc."""
    if not _OK or not pdf_path or not os.path.exists(pdf_path):
        return []
    out = []
    try:
        d = fitz.open(pdf_path)
        if not d.is_form_pdf:
            d.close(); return []
        pages = [d[int(page) - 1]] if page else d
        for pg in pages:
            for w in (pg.widgets() or []):
                out.append({"page": pg.number + 1, "name": w.field_name or "",
                            "type": getattr(w, "field_type_string", str(getattr(w, "field_type", ""))),
                            "value": (w.field_value if w.field_value is not None else "")})
                if len(out) >= max_fields:
                    break
        d.close()
    except Exception:
        return out
    return out


def embedded_files(pdf_path):
    """Files embedded/attached inside the PDF -> [{name, length, desc}] (catalog §5.5). Sometimes CAD/CSV/spec data is
    hidden here."""
    if not _OK or not pdf_path or not os.path.exists(pdf_path):
        return []
    out = []
    try:
        d = fitz.open(pdf_path)
        for name in (d.embfile_names() or []):
            try:
                info = d.embfile_info(name) or {}
            except Exception:
                info = {}
            out.append({"name": name, "length": info.get("length", info.get("size", 0)),
                        "desc": (info.get("desc") or info.get("description") or "")[:120]})
        d.close()
    except Exception:
        return out
    return out


def layers(pdf_path):
    """Optional-content groups / layers (OCGs) in the PDF -> [{name, on, usage}] (catalog §5.6). Some engineering
    drawings put callouts, dimensions, or revisions on separate toggleable layers; this exposes them."""
    if not _OK or not pdf_path or not os.path.exists(pdf_path):
        return []
    out = []
    try:
        d = fitz.open(pdf_path)
        for _xref, g in (d.get_ocgs() or {}).items():
            out.append({"name": (g.get("name") or "").strip()[:120],
                        "on": bool(g.get("on", True)), "usage": g.get("usage", "")})
        d.close()
    except Exception:
        return out
    return out


def summary(pdf_path):
    """One call for a doc: metadata + outline + form-field / embedded-file / layer counts (catalog §5.1-5.6)."""
    md = metadata(pdf_path); ol = outline(pdf_path)
    ff = form_fields(pdf_path); ef = embedded_files(pdf_path); lg = layers(pdf_path)
    return {"metadata": md, "n_outline": len(ol), "outline": ol[:40],
            "n_form_fields": len(ff), "form_fields": ff[:60],
            "n_embedded": len(ef), "embedded_files": ef,
            "n_layers": len(lg), "layers": lg}


if __name__ == "__main__":
    if not _OK:
        print("fitz unavailable; skipping"); raise SystemExit(0)
    import tempfile
    d = fitz.open()
    for _ in range(3):
        d.new_page(width=300, height=300)
    d.set_metadata({"title": "TM 9-2320-280-24", "author": "US Army", "subject": "Maintenance"})
    d.set_toc([[1, "Chapter 1 — Introduction", 1], [2, "1.1 Scope", 1], [1, "Chapter 2 — Maintenance", 2]])
    # add a GOTO link on page 1 -> page 2
    d[0].insert_link({"kind": fitz.LINK_GOTO, "from": fitz.Rect(10, 10, 60, 30), "page": 1, "to": fitz.Point(0, 0)})
    # add an AcroForm text field (§5.4) + an embedded file (§5.5)
    try:
        w = fitz.Widget(); w.field_name = "quantity"; w.field_type = fitz.PDF_WIDGET_TYPE_TEXT
        w.rect = fitz.Rect(40, 40, 140, 62); w.field_value = "5"
        d[0].add_widget(w)
    except Exception:
        pass
    try:
        d.embfile_add("parts.csv", b"nsn,qty\n2920-01-371-9577,2\n", desc="sample attachment")
    except Exception:
        pass
    # add optional-content layers (§5.6)
    try:
        d.add_ocg("Callouts", on=True); d.add_ocg("Dimensions", on=False)
    except Exception:
        pass
    p = os.path.join(tempfile.mkdtemp(), "m.pdf"); d.save(p); d.close()

    md = metadata(p)
    assert md.get("title", "").startswith("TM 9-2320") and md.get("pages") == 3, md
    ol = outline(p)
    assert len(ol) == 3 and ol[0]["title"].startswith("Chapter 1") and ol[0]["level"] == 1, ol
    lk = links(p, 1)
    assert any(x["kind"] == "goto" and x["page"] == 2 for x in lk), lk
    ff = form_fields(p)
    assert any(f["name"] == "quantity" and str(f["value"]) == "5" for f in ff), ("form fields", ff)
    ef = embedded_files(p)
    assert any(e["name"] == "parts.csv" for e in ef), ("embedded", ef)
    lg = layers(p)
    assert any(l["name"] == "Callouts" for l in lg) and any(l["name"] == "Dimensions" and not l["on"] for l in lg), \
        ("layers", lg)
    s = summary(p)
    assert s["n_outline"] == 3 and s["n_form_fields"] >= 1 and s["n_embedded"] >= 1 and s["n_layers"] >= 2, s
    print("pdfmeta self-test OK  (metadata + %d outline + link + %d form field + %d embedded file + %d layers)"
          % (len(ol), len(ff), len(ef), len(lg)))
# END OF FILE
