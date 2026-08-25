#!/usr/bin/env python3
"""THE VIEWER -- HEURISTIC LAYOUT ANALYSIS (v1.4.1, catalog §2.4 + §2.5). Segments a page into logical regions --
title, heading, paragraph, caption, header, footer, figure -- WITHOUT a heavy ML layout model. It reads PyMuPDF's
native block structure (position, font size, block type) and classifies by relative font size + page position.
That gives reading order, header/footer bands, and figure/caption regions that make every other extractor sharper
(and can drive per-region routing). v1.4.1 (catalog §2.5) adds column-aware reading order: a single-level column
split (not full recursive XY-cut -- this corpus's TM pages are single-column body text or a simple 2-column layout
with full-width headers/footers/titles, never a deeper multi-region magazine layout) so a genuine 2-column page
reads "whole left column, then whole right column" instead of interleaving the two columns line-by-line the way a
flat top-to-bottom/left-to-right sort does. A single-column page's order is unaffected -- see `_reading_order()`.
PyMuPDF only; degrades to [] if fitz is absent. Read-only on the corpus."""
import os
import statistics

try:
    import pymupdf as fitz
    _OK = True
except Exception:
    fitz = None; _OK = False

# Column-detection thresholds (catalog §2.5) -- tuned against the synthetic fixtures in this module's own
# __main__ self-test below, not guessed in advance (per the design spec's own "open items" framing).
_FULL_WIDTH_FRAC = 0.65     # a block spanning >= this fraction of the page's own content width is full-width
_MIN_NARROW_BLOCKS = 4      # fewer narrow blocks than this is "too few to call a real 2-column layout"
_MIN_COLUMN_BLOCKS = 2      # each side of a detected gutter needs at least this many blocks to count as a column
_MIN_GUTTER_FRAC = 0.04     # the gutter itself must be at least this fraction of content width...
_MIN_GUTTER_ABS = 12.0      # ...or this many page-units, whichever is larger (guards tiny/degenerate pages)
_MAX_ALIGNMENT_RATIO = 0.30  # see _row_alignment_ratio()'s docstring -- the gate that actually distinguishes
                             # real side-by-side column text from a false-positive (adversarial-review
                             # finding, see _column_order()). Empirically separates two concrete, directly-
                             # reproduced cases cleanly: a genuine 2-column TM page scores ~0.14 (accept);
                             # ordinary single-column steps with right-indented CAUTION/NOTE/WARNING boxes
                             # score ~0.49 (reject) -- 0.30 sits with real margin on both sides, not tuned to
                             # the edge of either measurement.


def available():
    return _OK


def _content_span(blocks):
    """The union x-range of every non-header/footer block -- the page's own CONTENT width, not the raw page
    width, so margins (and a page that happens to have wide running headers) don't skew the full-width
    threshold. Falls back to all blocks if every block is a header/footer (degenerate page)."""
    cand = [b for b in blocks if b["type"] not in ("header", "footer")] or blocks
    if not cand:
        return 0.0, 0.0
    return min(b["bbox"][0] for b in cand), max(b["bbox"][2] for b in cand)


def _is_full_width(b, c_x0, c_x1):
    """A header/footer/title/heading is ALWAYS full-width regardless of its own measured text width -- each
    is a page-spanning band positioned by role (running header/footer, chapter title, section heading), not
    narrow column content, even when the actual text happens to render narrow (a short page number, a short
    title like "COOLING", a two-word section heading). Adversarial-review fix: the first draft only exempted
    header/footer -- a short title/heading measuring under _FULL_WIDTH_FRAC of the content width was left to
    the plain width check, got misclassified as ordinary narrow content, and could be silently column-
    assigned and sorted into the MIDDLE of the page (after an entire column of body text) instead of acting
    as the page-spanning band delimiter it actually is. Everything else is measured against content width."""
    if b["type"] in ("header", "footer", "title", "heading"):
        return True
    cw = c_x1 - c_x0
    if cw <= 0:
        return True
    return (b["bbox"][2] - b["bbox"][0]) >= _FULL_WIDTH_FRAC * cw


def _find_gutter(narrow, min_gap):
    """Merge the x-intervals of the narrow blocks (sorted by x0), treating any two whose gap is smaller than
    min_gap as touching. What's left is one interval per real cluster of x-coverage; the widest gap between
    two clusters is the best gutter candidate (a page with 3+ clusters collapses to left/right of the widest
    gap -- 3+ column detection is explicitly out of scope, see the design spec's open items). Returns None
    when there's nothing to merge down to (a single cluster -- no gap at all)."""
    if len(narrow) < 2:
        return None
    ivs = sorted(((b["bbox"][0], b["bbox"][2]) for b in narrow), key=lambda t: t[0])
    merged = [ivs[0]]
    for x0, x1 in ivs[1:]:
        if x0 - merged[-1][1] < min_gap:
            merged[-1] = (merged[-1][0], max(merged[-1][1], x1))
        else:
            merged.append((x0, x1))
    if len(merged) < 2:
        return None
    gaps = [(merged[i][1], merged[i + 1][0]) for i in range(len(merged) - 1)]
    return max(gaps, key=lambda g: g[1] - g[0])


def _median(xs):
    xs = sorted(xs)
    n = len(xs)
    if n == 0:
        return 0.0
    return xs[n // 2] if n % 2 else (xs[n // 2 - 1] + xs[n // 2]) / 2.0


def _row_alignment_ratio(left, right):
    """Adversarial-review fix: x-gap clustering alone is NOT enough to tell a genuine 2-column body-text
    layout apart from an ordinary single-column TM page that uses the standard right-indented NOTE/CAUTION/
    WARNING callout-box convention next to left-margin step text -- both shapes produce two x-clusters with
    a real gutter between them (confirmed by direct reproduction of both as concrete PyMuPDF fixtures, not
    just reasoned about). A density check (each column's own "ink" over its own y-span) was tried first and
    rejected: both cases score similarly low with a small number of short, sparse blocks -- a real but SHORT
    2-column section looks just as "sparse" as a handful of scattered callouts when there are only 2-3 blocks
    per side, so density alone doesn't discriminate at the block counts this heuristic actually has to work
    with.

    The signal that DOES discriminate, verified numerically against both reproduced fixtures: genuine
    side-by-side columns have matching items at roughly the SAME y (real typeset text fills both columns row
    by row), while an interleaved callout sits roughly HALFWAY between two consecutive same-column items --
    offset by about half a within-column gap, not aligned with either. This returns, for the LEFT column,
    the ratio of (median distance from each left block to its nearest right-column neighbor) to (median gap
    between consecutive left blocks): a genuine 2-column TM fixture measures ~0.14 (right blocks sit close
    beside their left counterparts); the left-margin-steps-plus-right-callouts fixture measures ~0.49
    (callouts sit roughly midway between steps, not beside any one of them). Low ratio = real columns
    (accept); high ratio = interleaved/offset (reject). Returns 0.0 (treated as "aligned," i.e. permissive)
    when there's fewer than 2 blocks in either column or a degenerate zero within-column gap -- callers
    already gate on `_MIN_COLUMN_BLOCKS` before this runs, so this is a defensive fallback, not a real path."""
    if len(left) < 2 or len(right) < 2:
        return 0.0
    left_y = sorted(b["bbox"][1] for b in left)
    right_y = [b["bbox"][1] for b in right]
    within_gaps = [b - a for a, b in zip(left_y, left_y[1:]) if b > a]
    if not within_gaps:
        return 0.0
    med_gap = _median(within_gaps)
    if med_gap <= 0:
        return 0.0
    cross = [min(abs(ly - ry) for ry in right_y) for ly in left_y]
    return _median(cross) / med_gap


def _column_order(blocks):
    """Column-aware reading order (catalog §2.5). Returns a reordered list when a genuine 2-column split is
    found, or None when the split is weak/ambiguous -- callers must fall back to the plain flat sort in that
    case (this is what keeps a single-column page byte-identical to the pre-§2.5 behavior)."""
    c_x0, c_x1 = _content_span(blocks)
    full, narrow = [], []
    for b in blocks:
        (full if _is_full_width(b, c_x0, c_x1) else narrow).append(b)
    if len(narrow) < _MIN_NARROW_BLOCKS:
        return None                              # too few candidate blocks -- not worth calling 2-column
    min_gap = max(_MIN_GUTTER_ABS, _MIN_GUTTER_FRAC * (c_x1 - c_x0))
    gutter = _find_gutter(narrow, min_gap)
    if not gutter:
        return None                              # no real gap in x-coverage -- this is a single-column page
    mid = (gutter[0] + gutter[1]) / 2.0
    left = sorted((b for b in narrow if (b["bbox"][0] + b["bbox"][2]) / 2.0 < mid),
                  key=lambda r: (r["bbox"][1], r["bbox"][0]))
    right = sorted((b for b in narrow if (b["bbox"][0] + b["bbox"][2]) / 2.0 >= mid),
                   key=lambda r: (r["bbox"][1], r["bbox"][0]))
    if len(left) < _MIN_COLUMN_BLOCKS or len(right) < _MIN_COLUMN_BLOCKS:
        return None                              # a lone outlier block isn't a real second column
    # Adversarial-review fix: x-gap clustering + a block-count minimum both stay true for a false-positive
    # shape (a few right-indented NOTE/CAUTION/WARNING boxes interleaved with a left-margin step list) --
    # neither is enough on its own. Require the two sides to actually READ AS aligned side-by-side columns
    # (matching row positions), not interleaved/offset content that just happens to sit in two x-clusters.
    # See _row_alignment_ratio()'s docstring for the reasoning and the two concrete, reproduced fixtures this
    # threshold was measured against.
    if _row_alignment_ratio(left, right) > _MAX_ALIGNMENT_RATIO:
        return None                              # left/right items are offset/interleaved, not aligned columns
    full.sort(key=lambda r: (r["bbox"][1], r["bbox"][0]))
    # Band the page by the full-width blocks' own y-positions: each full-width block sits exactly where its
    # y puts it, and within the band above it every left-column block sorts before every right-column block.
    result = []
    li = ri = 0
    for f in full:
        y_limit = f["bbox"][1]
        while li < len(left) and left[li]["bbox"][1] < y_limit:
            result.append(left[li]); li += 1
        while ri < len(right) and right[ri]["bbox"][1] < y_limit:
            result.append(right[ri]); ri += 1
        result.append(f)
    result.extend(left[li:])
    result.extend(right[ri:])
    return result


def _reading_order(blocks):
    """Reading order for one page's already-classified blocks (catalog §2.4 + §2.5). Tries the column-aware
    order first; a weak/ambiguous split (few narrow blocks, no real gutter, or not enough blocks on both
    sides) falls back to EXACTLY the original flat (y, x) sort -- a single-column page's order is therefore
    unaffected by this function's existence."""
    ordered = _column_order(blocks)
    if ordered is not None:
        return ordered
    blocks.sort(key=lambda r: (r["bbox"][1], r["bbox"][0]))
    return blocks


def analyze(pdf_path, page, header_frac=0.08, footer_frac=0.92):
    """Return [{type, bbox:[x0,y0,x1,y1], text, size}] for one page (1-based). Types: title, heading, paragraph,
    caption, header, footer, figure. Ordered top-to-bottom (reading order)."""
    if not _OK or not pdf_path or not os.path.exists(pdf_path):
        return []
    out = []
    try:
        d = fitz.open(pdf_path)
        pg = d[int(page) - 1]
        ph = pg.rect.height or 1.0
        raw = pg.get_text("dict")
        blocks = raw.get("blocks", [])
        # gather text block sizes to get a page baseline
        sizes = []
        for b in blocks:
            if b.get("type", 0) == 0:
                for ln in b.get("lines", []):
                    for sp in ln.get("spans", []):
                        if sp.get("size"):
                            sizes.append(sp["size"])
        med = statistics.median(sizes) if sizes else 10.0
        for b in blocks:
            x0, y0, x1, y1 = b.get("bbox", (0, 0, 0, 0))
            ymid = (y0 + y1) / 2.0
            if b.get("type", 0) == 1:                       # image block
                out.append({"type": "figure", "bbox": [round(x0), round(y0), round(x1), round(y1)], "text": "", "size": 0})
                continue
            spans = [sp for ln in b.get("lines", []) for sp in ln.get("spans", [])]
            if not spans:
                continue
            text = " ".join(sp.get("text", "") for sp in spans).strip()
            if not text:
                continue
            bsize = max((sp.get("size", med) for sp in spans), default=med)
            frac = ymid / ph
            # Size-based checks run first so a genuinely large title/heading near the top (or bottom) of
            # the page is classified by its font size rather than being swallowed by the position-based
            # header/footer band -- a real running header/footer is small text, not a large one.
            if bsize >= 1.6 * med and frac < 0.30:
                typ = "title"
            elif bsize >= 1.25 * med:
                typ = "heading"
            elif frac <= header_frac:
                typ = "header"
            elif frac >= footer_frac:
                typ = "footer"
            elif bsize <= 0.85 * med:
                typ = "caption"
            else:
                typ = "paragraph"
            out.append({"type": typ, "bbox": [round(x0), round(y0), round(x1), round(y1)],
                        "text": text[:300], "size": round(bsize, 1)})
        d.close()
    except Exception:
        return out
    return _reading_order(out)          # column-aware reading order (catalog §2.5); flat (y,x) sort on fallback


def summarize(regions):
    c = {}
    for r in regions:
        c[r["type"]] = c.get(r["type"], 0) + 1
    return {"n": len(regions), **c}


if __name__ == "__main__":
    if not _OK:
        print("fitz unavailable; skipping"); raise SystemExit(0)
    import tempfile
    d = fitz.open(); pg = d.new_page(width=400, height=520)
    pg.insert_text((40, 30), "TM 9-2320-280-24  Running Header", fontsize=8)          # header (top)
    pg.insert_text((40, 90), "CHAPTER 2  MAINTENANCE", fontsize=24)                    # title (large, upper)
    pg.insert_text((40, 140), "2-1. Scope", fontsize=15)                              # heading
    pg.insert_text((40, 180), "This paragraph describes the maintenance procedure in normal body text at ten point size for the section.", fontsize=10)
    pg.insert_text((40, 300), "Figure 2-1. Alternator assembly", fontsize=8)          # caption (small)
    pg.insert_text((40, 500), "Change 2                          2-1", fontsize=8)    # footer (bottom)
    pm = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 60, 60)); pm.set_rect(pm.irect, (180, 180, 180))
    pg.insert_image(fitz.Rect(60, 330, 160, 430), pixmap=pm)                          # figure (image block)
    p = os.path.join(tempfile.mkdtemp(), "l.pdf"); d.save(p); d.close()

    reg = analyze(p, 1)
    s = summarize(reg)
    types = {r["type"] for r in reg}
    assert "title" in types, ("title not found", [(r["type"], r["text"][:20]) for r in reg])
    assert "header" in types and "footer" in types, ("header/footer", s)
    assert "figure" in types, ("figure block not detected", s)
    assert any(r["type"] == "paragraph" for r in reg), ("paragraph", s)
    # reading order: header (top) comes before footer (bottom)
    ys = [r["bbox"][1] for r in reg]
    assert ys == sorted(ys), "not in reading order"
    print("layout self-test OK  (%s)" % s)

    # --- catalog §2.5: genuine 2-column fixture -----------------------------------------------------
    # Full-width header + title, THREE left-column paragraphs and THREE right-column paragraphs whose
    # y-ranges overlap pairwise (left N's y-range overlaps right N's) -- the exact shape that makes a
    # flat (y, x) sort interleave the two columns line-by-line instead of reading one column fully
    # before the next -- then a full-width footer.
    d2 = fitz.open(); pg2 = d2.new_page(width=640, height=700)
    pg2.insert_text((40, 30), "TM 9-2320-280-24  RUNNING HEADER FOR THE COOLING SYSTEM CHAPTER", fontsize=8)
    pg2.insert_text((40, 90), "CHAPTER 3  COOLING SYSTEM MAINTENANCE PROCEDURES", fontsize=24)
    pg2.insert_text((40, 150), "Radiator inspection steps go here", fontsize=10)     # left 1
    pg2.insert_text((320, 160), "Hose clamp torque specification", fontsize=10)      # right 1 (overlaps left 1's y)
    pg2.insert_text((40, 220), "Thermostat replacement procedure", fontsize=10)      # left 2
    pg2.insert_text((320, 230), "Fan clutch inspection procedure", fontsize=10)      # right 2 (overlaps left 2's y)
    pg2.insert_text((40, 290), "Water pump removal steps follow", fontsize=10)       # left 3
    pg2.insert_text((320, 300), "Coolant reservoir pressure test", fontsize=10)      # right 3 (overlaps left 3's y)
    pg2.insert_text((40, 660), "Change 3                                                              3-1", fontsize=8)
    p2 = os.path.join(tempfile.mkdtemp(), "l2.pdf"); d2.save(p2); d2.close()

    reg2 = analyze(p2, 1)
    texts2 = [r["text"][:8] for r in reg2]
    assert texts2 == ["TM 9-232", "CHAPTER ", "Radiator", "Thermost", "Water pu",
                       "Hose cla", "Fan clut", "Coolant ", "Change 3"], \
        ("2-column order wrong -- got %r" % (texts2,))
    print("layout 2-column self-test OK  (%s)" % [r["type"] for r in reg2])

    # --- catalog §2.5: NOT a real 2-column layout (fallback must trigger) --------------------------
    # A couple of small scattered captions on an otherwise single-column page -- too few narrow blocks
    # to ever count as a genuine second column. Must fall back to the exact flat (y, x) sort, not a
    # false-positive column split.
    d3 = fitz.open(); pg3 = d3.new_page(width=400, height=520)
    pg3.insert_text((40, 30), "TM 9-2320-280-24  Running Header", fontsize=8)
    pg3.insert_text((40, 90), "CHAPTER 4  BRAKES", fontsize=24)
    pg3.insert_text((40, 180), "This paragraph describes the maintenance procedure in normal body text at ten point size for the section.", fontsize=10)
    pg3.insert_text((40, 230), "This second paragraph continues describing the brake bleeding procedure in normal body text as well.", fontsize=10)
    pg3.insert_text((40, 300), "Fig. 4-1", fontsize=8)          # scattered caption 1 (narrow, but only 2 total)
    pg3.insert_text((300, 320), "Fig. 4-2", fontsize=8)         # scattered caption 2
    pg3.insert_text((40, 480), "Change 4                          4-1", fontsize=8)
    p3 = os.path.join(tempfile.mkdtemp(), "l3.pdf"); d3.save(p3); d3.close()

    reg3 = analyze(p3, 1)
    ys3 = [r["bbox"][1] for r in reg3]
    assert ys3 == sorted(ys3), ("weak 2-column candidate was misdetected as a real column split", reg3)
    print("layout fallback (not-really-2-column) self-test OK  (%s)" % [r["type"] for r in reg3])

    # --- adversarial-review regression #1: a SHORT title over a 2-column page must still act as a
    # page-spanning band delimiter, not get swallowed as narrow column content just because its own
    # rendered text is short. First draft only exempted header/footer from the full-width check;
    # a short title ("COOLING", well under _FULL_WIDTH_FRAC of the content width) was measured by width
    # alone, got column-assigned to whichever side its x-center fell on, and was sorted into the MIDDLE
    # of the page -- after an entire column of body text -- instead of appearing first. -------------
    d4 = fitz.open(); pg4 = d4.new_page(width=640, height=700)
    pg4.insert_text((40, 30), "TM 9-2320-280-24  RUNNING HEADER", fontsize=8)
    pg4.insert_text((470, 90), "COOLING", fontsize=24)          # SHORT title, positioned over the RIGHT column
    pg4.insert_text((40, 150), "Radiator inspection steps go here", fontsize=10)     # left 1
    pg4.insert_text((320, 160), "Hose clamp torque specification", fontsize=10)      # right 1 (offset y, own line)
    pg4.insert_text((40, 220), "Thermostat replacement procedure", fontsize=10)      # left 2
    pg4.insert_text((320, 230), "Fan clutch inspection procedure", fontsize=10)      # right 2 (offset y, own line)
    pg4.insert_text((40, 290), "Water pump removal steps follow", fontsize=10)       # left 3
    pg4.insert_text((320, 300), "Coolant reservoir pressure test", fontsize=10)      # right 3 (offset y, own line)
    pg4.insert_text((40, 660), "Change 3                                                              3-1", fontsize=8)
    p4 = os.path.join(tempfile.mkdtemp(), "l4.pdf"); d4.save(p4); d4.close()

    reg4 = analyze(p4, 1)
    types4 = [r["type"] for r in reg4]
    texts4 = [r["text"] for r in reg4]
    assert types4[1] == "title" and texts4[1] == "COOLING", \
        ("short title must stay full-width, not get column-assigned", reg4)
    ok_pos = texts4.index("COOLING")
    assert ok_pos <= 1, ("short title must sort near the top, not mid-page after a column", texts4)
    assert texts4 == ["TM 9-2320-280-24  RUNNING HEADER", "COOLING", "Radiator inspection steps go here",
                       "Thermostat replacement procedure", "Water pump removal steps follow",
                       "Hose clamp torque specification", "Fan clutch inspection procedure",
                       "Coolant reservoir pressure test", "Change 3                                                              3-1"], \
        ("full expected order for short-title-over-2-column case", texts4)
    print("layout short-title-stays-full-width self-test OK  (%s)" % [t[:20] for t in texts4])

    # --- adversarial-review regression #2: ordinary single-column left-margin procedure steps with
    # right-indented CAUTION/NOTE/WARNING callout boxes (the standard Army-TM convention) must NOT be
    # misdetected as a genuine 2-column layout. This is not just a cosmetic ordering bug if it regresses
    # -- regrouping every callout away from the specific step it modifies is actively misleading on a
    # maintenance manual. Direct reproduction of the exact false-positive adversarial review caught. ---
    d5 = fitz.open(); pg5 = d5.new_page(width=612, height=792)
    # header_frac=0.08/footer_frac=0.92 on a 792pt page -> header band y_mid<63.4, footer band y_mid>728.6.
    # Positioned to actually land in those bands (the first draft of this fixture didn't -- both "header"
    # and "footer" text landed as plain "paragraph" blocks instead, silently leaking into the narrow-block
    # pool and confounding what this test meant to isolate; caught by tracing the actual classified output,
    # not assumed correct because the assertions happened to pass).
    # Step text kept SHORT enough that its rendered x1 stays well clear of the callouts' x0=380 -- the
    # first draft of this fixture used long step sentences whose rendered width ran past x=300, overlapping
    # the callouts' own x-range, so _find_gutter() correctly merged them into ONE x-cluster and returned no
    # gutter at all -- the fixture never reached _row_alignment_ratio() to begin with, so it wasn't actually
    # testing what its own comment claimed. Caught by tracing _find_gutter()'s real return value directly,
    # not by trusting that green assertions meant the right code path ran.
    pg5.insert_text((72, 40), "Running Header", fontsize=8)
    pg5.insert_text((72, 130), "2-4. Procedure", fontsize=15)
    pg5.insert_text((72, 180), "a. Remove the four bolts.", fontsize=10)
    pg5.insert_text((380, 220), "CAUTION: Hot surface.", fontsize=9)
    pg5.insert_text((72, 280), "b. Disconnect the sensor.", fontsize=10)
    pg5.insert_text((380, 330), "NOTE: Torque 30 ft-lb.", fontsize=9)
    pg5.insert_text((72, 390), "c. Install the gasket.", fontsize=10)
    pg5.insert_text((380, 440), "WARNING: Check ground.", fontsize=9)
    pg5.insert_text((72, 750), "Change 5                          2-9", fontsize=8)
    p5 = os.path.join(tempfile.mkdtemp(), "l5.pdf"); d5.save(p5); d5.close()

    reg5 = analyze(p5, 1)
    texts5 = [r["text"] for r in reg5]
    ys5 = [r["bbox"][1] for r in reg5]
    assert ys5 == sorted(ys5), \
        ("false-positive column split: steps + right-indented callouts must fall back to flat sort", reg5)
    a_i = next(i for i, t in enumerate(texts5) if t.startswith("a. Remove"))
    caution_i = next(i for i, t in enumerate(texts5) if t.startswith("CAUTION"))
    b_i = next(i for i, t in enumerate(texts5) if t.startswith("b. Disconnect"))
    assert caution_i == a_i + 1, \
        ("CAUTION must immediately follow the step it modifies, not be regrouped to the end", texts5)
    assert b_i == caution_i + 1, ("step b must immediately follow the CAUTION above it", texts5)
    print("layout steps-plus-callouts-not-misdetected-as-columns self-test OK  (%s)" % [t[:20] for t in texts5])
# END OF FILE
