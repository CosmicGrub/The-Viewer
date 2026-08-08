#!/usr/bin/env python3
"""THE VIEWER -- HEADER / FOOTER / RUNNING-TITLE STRIPPER (v1.2.3, catalog §2.6). Scanned TM pages repeat the same
running header/footer (TM number, title, page banner, 'Change 3', classification markings) on every page. Those repeats
pollute search and every text extractor. This finds the lines that recur across many pages (top/bottom bands) and
strips them from a page's body -- purely statistical, language-agnostic, stdlib only. Read-only; used to clean text
before measures/specs/leadingspecs run. Corpus authoritative (originals untouched)."""
import re
from collections import Counter


def _norm(line):
    s = re.sub(r"\s+", " ", (line or "").strip())
    # normalise page numbers / change numbers so 'Page 12' and 'Page 13' count as the same boilerplate
    s = re.sub(r"\b\d{1,4}\b", "#", s)
    return s


def detect_boilerplate(pages, band=4, min_frac=0.4, min_pages=5):
    """Given a list of page texts, return the set of NORMALISED lines that recur (in the top/bottom `band` lines) on at
    least `min_frac` of pages -- i.e. the running header/footer. Needs >= `min_pages` pages to bother."""
    if not pages or len(pages) < min_pages:
        return set()
    counts = Counter()
    npages = 0
    for txt in pages:
        lines = [l for l in (txt or "").splitlines() if l.strip()]
        if not lines:
            continue
        npages += 1
        edge = lines[:band] + lines[-band:]
        for l in set(_norm(l) for l in edge):
            if 2 <= len(l) <= 80:
                counts[l] += 1
    if not npages:
        return set()
    thresh = max(min_pages * min_frac, min_frac * npages)
    return {l for l, c in counts.items() if c >= thresh}


def strip(text, boilerplate, band=6):
    """Remove boilerplate lines from the top/bottom band of one page's text. Middle content is never touched."""
    if not text or not boilerplate:
        return text
    lines = text.splitlines()
    n = len(lines)

    def is_bp(i):
        return (i < band or i >= n - band) and _norm(lines[i]) in boilerplate and len(lines[i].strip()) <= 80
    kept = [ln for i, ln in enumerate(lines) if not is_bp(i)]
    return "\n".join(kept)


def clean_pages(pages):
    """Convenience: detect boilerplate across `pages` then return the stripped pages."""
    bp = detect_boilerplate(pages)
    return [strip(p, bp) for p in pages], bp


if __name__ == "__main__":
    header = "TM 9-2320-280-24"
    words = ["alternator", "bracket", "coolant", "differential", "engine", "flywheel", "gasket", "harness"]
    pages = []
    for i in range(10):
        body = "\n".join("Install the %s and torque the %s fitting properly on this page." % (words[j], words[(i + j) % 8])
                         for j in range(6))
        pages.append("%s\nSECTION II\n%s\nChange 2   Page %d" % (header, body, 12 + i))
    bp = detect_boilerplate(pages)
    assert _norm(header) in bp, ("header not detected", bp)
    assert any("Change" in b for b in bp), ("footer not detected", bp)
    cleaned, bp2 = clean_pages(pages)
    assert "TM 9-2320-280-24" not in cleaned[0], "header not stripped"
    assert "Change 2" not in cleaned[0], "footer not stripped"
    assert "Install the alternator" in cleaned[0], "body wrongly stripped"
    print("pagetrim self-test OK  (%d boilerplate lines detected & stripped, body preserved)" % len(bp))
# END OF FILE
