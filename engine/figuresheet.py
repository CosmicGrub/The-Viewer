#!/usr/bin/env python3
"""THE VIEWER -- FIGURE SHEET (v0.99.7): a printable take-to-the-bay PDF of EVERY figure a part appears on.
Combines the cross-figure locator (partlocate) with page renders (fitz) into one document. Pure reportlab +
PyMuPDF + Pillow (all offline). Read-only. db_path/index_dir passed explicitly."""
import os, io, time, sqlite3


def _page_image(pdf_path, page, dpi):
    try:
        import pymupdf as fitz
        from PIL import Image
        doc = fitz.open(pdf_path); pix = doc[int(page) - 1].get_pixmap(dpi=int(dpi))
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples); doc.close(); return img
    except Exception:
        return None


def build_pdf(items, part_label, subtitle=""):
    """items = [(PIL.Image, caption_str)]. Returns PDF bytes."""
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas as rlc
    from reportlab.lib.utils import ImageReader
    buf = io.BytesIO(); c = rlc.Canvas(buf, pagesize=letter); W, H = letter
    # cover
    c.setFillColorRGB(0.07, 0.09, 0.12); c.rect(0, 0, W, H, fill=1, stroke=0)
    c.setFillColorRGB(0.90, 0.93, 0.96); c.setFont("Helvetica-Bold", 24); c.drawString(50, H - 90, "Figure Sheet")
    c.setFillColorRGB(0.50, 0.66, 0.90); c.setFont("Helvetica-Bold", 15); c.drawString(50, H - 118, (part_label or "")[:78])
    c.setFillColorRGB(0.55, 0.60, 0.68); c.setFont("Helvetica", 10)
    if subtitle: c.drawString(50, H - 140, subtitle[:110])
    c.drawString(50, H - 158, "THE VIEWER  ·  %d figure%s  ·  %s" % (len(items), "" if len(items) == 1 else "s", time.strftime("%Y-%m-%d")))
    c.setFillColorRGB(0.40, 0.44, 0.50); c.setFont("Helvetica-Oblique", 8)
    c.drawString(50, 40, "Representative pages from cited TMs. Verify against the source manual before performing maintenance.")
    c.showPage()
    for img, cap in items:
        if img is None: continue
        iw, ih = img.size; margin = 38; avail_w = W - 2 * margin; avail_h = H - 2 * margin - 34
        s = min(avail_w / iw, avail_h / ih); dw, dh = iw * s, ih * s; x = (W - dw) / 2; y = H - margin - dh
        try: c.drawImage(ImageReader(img), x, y, dw, dh, preserveAspectRatio=True, anchor='n')
        except Exception: pass
        c.setFillColorRGB(0.10, 0.12, 0.15); c.rect(0, 0, W, 32, fill=1, stroke=0)
        c.setFillColorRGB(0.85, 0.88, 0.92); c.setFont("Helvetica", 10); c.drawString(18, 11, (cap or "")[:135])
        c.showPage()
    c.save(); return buf.getvalue()


def figuresheet(db_path, index_dir, q, dpi=150, max_figs=12):
    try:
        import partlocate
        r = partlocate.locate(db_path, q, limit=max_figs * 2)
    except Exception:
        return None
    aps = (r or {}).get("appearances", [])
    if not aps:
        return None
    # doc -> path
    paths = {}
    # v1.13.4: con=None + finally -- backs GET /api/figuresheet (the job-package figure-crop PDF); a
    # dynamically-built IN(...) query throwing (schema drift, or a locked db mid-ingest) used to leak
    # the viewer.db handle AND silently continue with an empty `paths` dict (a PDF with no images and
    # no diagnostic). The empty-paths silent-continue is the existing degrade-gracefully design here --
    # only the leak is fixed; a caller with zero paths still gets a (blank) PDF rather than a 500.
    con = None
    try:
        con = sqlite3.connect("file:%s?mode=ro" % db_path, uri=True)
        docs = sorted({a["doc"] for a in aps})
        qmarks = ",".join("?" * len(docs))
        for row in con.execute("SELECT id, path FROM documents WHERE id IN (%s)" % qmarks, docs):
            paths[row[0]] = row[1]
    except Exception:
        pass
    finally:
        if con is not None:
            con.close()
    items = []
    for a in aps[:max_figs]:
        p = paths.get(a["doc"])
        img = _page_image(p, a["page"], dpi) if p else None
        cap = "%s · %s · %s · p.%s" % (a.get("vehicle") or "?", a.get("tm") or "", a.get("fig_no") or "", a["page"])
        items.append((img, cap))
    label = (r.get("names") or [q])[0] if r.get("names") else q
    sub = "NSN %s" % r["nsn"] if r.get("nsn") else "query: %s" % q
    return build_pdf(items, label, "%s  ·  %d appearances across %d documents" % (sub, r["count"], r.get("documents", 0)))


if __name__ == "__main__":
    # self-test the PDF assembly with synthetic images (no corpus needed)
    from PIL import Image, ImageDraw
    ims = []
    for k in range(3):
        im = Image.new("RGB", (600, 440), "white"); d = ImageDraw.Draw(im)
        d.rectangle([40, 40, 560, 400], outline="black", width=2); d.text((60, 60), "FIG %d (synthetic)" % (k + 5), fill="black")
        ims.append((im, "HMMWV M998 · TM 9-2320-280-24P · FIG %d · p.%d" % (k + 5, 12 + k)))
    pdf = build_pdf(ims, "ALTERNATOR", "NSN 2920-01-111-1111 · 3 appearances")
    open("/tmp/figuresheet_test.pdf", "wb").write(pdf)
    print("pdf bytes:", len(pdf), "| valid header:", pdf[:5] == b"%PDF-")
