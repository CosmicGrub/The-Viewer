#!/usr/bin/env python3
"""THE VIEWER -- OCR TEXT-QUALITY / CONFIDENCE HEURISTIC (v1.2.2, catalog §9.1). The OCR pass is already done, so instead
of per-token engine confidence we score a page/snippet's quality AFTER the fact -- garbage-char ratio, vowel-less
'words' (classic OCR garble), stray single chars -- to a 0..1 clean score. Extractions pulled from a low-quality page
can then be flagged 'suspect'/'poor' so a mechanic knows to double-check the cited page. Pure stdlib; read-only; no
network. Used to attach a confidence flag to measurements/specs and to prioritise pages for re-OCR."""
import re

_WORD = re.compile(r"[A-Za-z]{2,}")
_TOKEN = re.compile(r"\S+")
_VOWEL = re.compile(r"[aeiouyAEIOUY]")
# "clean" characters we expect in a TM: letters, digits, common punctuation/whitespace, degree/±
_CLEAN = re.compile(r"[A-Za-z0-9\s.,;:!?()\-/%'\"&+=°±#*@\[\]]")


def score(text):
    """Return a 0..1 cleanliness score for `text` (1 = pristine OCR/native text, →0 = garbled). Empty/short → 0.5
    (unknown). Heuristics are cheap and language-agnostic."""
    if not text:
        return 0.5
    s = text.strip()
    if len(s) < 12:
        return 0.5
    total = len(s)
    clean = len(_CLEAN.findall(s))
    garbage_ratio = 1.0 - (clean / total)                       # fraction of unexpected characters
    words = _WORD.findall(s)
    if words:
        voweless = sum(1 for w in words if len(w) >= 3 and not _VOWEL.search(w))
        voweless_ratio = voweless / len(words)                  # long alpha words with no vowel = garble
    else:
        voweless_ratio = 0.5
    toks = _TOKEN.findall(s)
    singles = sum(1 for t in toks if len(t) == 1 and not t.isalnum())
    single_ratio = singles / max(1, len(toks))                  # scattered stray punctuation tokens
    # combine (weights tuned so a clean paragraph ~0.95, heavy garble <0.4)
    val = 1.0 - (2.2 * garbage_ratio + 0.8 * voweless_ratio + 0.6 * single_ratio)
    return max(0.0, min(1.0, round(val, 3)))


def flag(text):
    """'clean' (>=0.75) | 'suspect' (0.5-0.75) | 'poor' (<0.5)."""
    q = score(text)
    return "clean" if q >= 0.75 else ("suspect" if q >= 0.5 else "poor")


def annotate(record, context_key="context", real_confidence=None):
    """Attach {'quality': float, 'confidence': flag} to an extraction record based on its context snippet. Returns the
    same dict (mutated) so it can be mapped over measures/specs/leadingspecs output before it reaches the Masterfile.

    `real_confidence`: optional 0..1 engine-reported OCR confidence for the record's source page (e.g.
    pages.ocr_confidence, RapidOCR's own per-line average -- see features/corpus.py's fts_pages()). When
    given, blends CONSERVATIVELY: it can only pull the text-heuristic score DOWN, never raise it above what
    the heuristic already found. A confidently-wrong OCR read (garbled-but-plausible-looking digits) is
    exactly the failure mode this module exists to catch, so a high real_confidence must never override a
    heuristic 'poor' call; but a low real_confidence CAN catch garble the text heuristic alone reads as
    clean (e.g. a single swapped digit in an otherwise well-formed sentence). None/out-of-range/unparsable
    values are ignored -- the heuristic-only score is the safe default, unchanged from before this existed."""
    q = score(record.get(context_key) or record.get("raw") or "")
    if real_confidence is not None:
        try:
            rc = float(real_confidence)
            if 0.0 <= rc <= 1.0:
                q = min(q, rc)
        except (TypeError, ValueError):
            pass
    record["quality"] = q
    record["confidence"] = "clean" if q >= 0.75 else ("suspect" if q >= 0.5 else "poor")
    return record


if __name__ == "__main__":
    clean_txt = ("Torque the mounting bolts to 30 to 35 foot-pounds. The overall length is 180 inches and the curb "
                 "weight is 5200 pounds. Charging voltage is 28 volts at 100 amperes.")
    garbled = "Tqrq7e th3 m0un+1ng b0l+s |o 3O f7-|b. 0vera|| |eng+h l8O 1n. Bxk zzz tttt vwxq mnbb kkkk ~~|| ^^^^"
    cs = score(clean_txt); gs = score(garbled)
    print("clean=%.3f (%s)  garbled=%.3f (%s)" % (cs, flag(clean_txt), gs, flag(garbled)))
    assert cs >= 0.75 and flag(clean_txt) == "clean", cs
    assert gs < cs and flag(garbled) in ("suspect", "poor"), gs
    assert score("") == 0.5 and score("short") == 0.5
    rec = annotate({"context": clean_txt, "raw": "30 ft-lb"})
    assert rec["confidence"] == "clean" and 0.0 <= rec["quality"] <= 1.0
    rec2 = annotate({"context": garbled, "raw": "3O f7-lb"})
    assert rec2["confidence"] in ("suspect", "poor")
    print("textquality self-test OK  (clean vs garbled separation + record annotation)")
# END OF FILE
