#!/usr/bin/env python3
"""THE VIEWER -- PAGE QUESTION-ANSWERING CORE (v1.1, catalog §10.1, design doc
docs/superpowers/specs/2026-08-24-vision-language-page-qa-design.md). The SHARED core both consumers of
`vlm.py`'s pluggable vision-language backend call, so neither reimplements trust-tier logic or (Phase 2)
verification -- the same reasoning that already has `cautions.py`/`_parse_procedure()` share
`textquality.annotate()` instead of each computing text quality independently. Today (Phase 1) the two
consumers are the interactive "Ask this page" page-viewer control and `ask.py`'s retrieve-then-answer
fallback; Phase 2 adds a third, `build_pageqa.py`'s batch structured-extraction sweep.

Two modes, both implemented:
    mode="text", strict=False  (Phase 1.) Free-text answer + an optional grounded region, straight from
        vlm.ask(). Trust is HARD-CAPPED at "review" (trust.py's amber "check" tier) NO MATTER WHAT the
        backend claims -- a human is looking at the actual page right there, so this is a second pair of
        eyes, not a verified fact (R13: an AI-sourced value must never visually pass as authoritative).
        Nothing is persisted -- matches ask.py's own answer-and-forget contract; this module never opens
        anything but a read-only connection.
    mode="structured" (or strict=True)  (Phase 2.) Typed {type, value, value2, unit} extracted out of the
        free-text answer via measures.py's OWN extraction (no parallel regex logic here -- that module is
        the established, tested way this codebase turns free text into typed measurements), gated behind
        a two-part verification pass before `verified` is ever True:
          (1) self-grounding -- vlm.ground() (NOT a second vlm.ask(); see vlm.ground()'s own docstring for
              why ask()'s own grounding can't be reused here) re-checks the SPECIFIC phrase the answer's
              typed value came from, directly on the page image. No located region => verified=False.
          (2) OCR cross-check -- the claimed phrase is fuzzy-matched (see _ocr_overlap() below) against
              THIS page's own already-stored, already-trusted OCR text (pages.body_text) -- independent of
              the model's own self-consistency, checked against ground truth already in the DB rather than
              the model's own say-so. No substantial overlap => verified=False.
        Both must pass for verified=True. Returns the typed value alongside `region`/`source_text`/
        `answer_text`/`verified`, matching the design spec's structured output shape. Still never writes
        anything -- verification is a pure function; persistence is Phase 2's batch driver's job (build_
        pageqa.py, not yet written), matching dedup.py's build()-does-the-writing-not-the-library-function
        precedent. Nothing extractable in the answer text at all (measures.py finds no typed value) means
        there is nothing TO verify -- returns available=True, verified=False, with a clear note; never
        raises, never fabricates a type/value this module made up itself (R13).

Read-only; `db_path` is passed explicitly (ask.py's own `answer(db_path, index_dir, question, ...)`
convention, and coverage.py's "functions take db_path + index_dir explicitly, no core injection") --
this module has no `core` DI because the Phase 2 batch driver that will also call ask() is a standalone
host script, not a route; a bare default is resolved from VIEWER_DB / index/viewer.db (same env-var
convention every build_*.py driver already uses) only when a caller doesn't supply one. Never raises --
every path returns the same {available, answer_text, structured, region, source_text, trust_tier,
verified, backend, note} shape (`structured`/`source_text` are always present as keys, populated only by
the mode="structured"/strict=True path -- None otherwise, same "optional but always-present key" pattern
`region` already established in Phase 1); a missing backend, a GPU-less machine, a bad doc/page, or a
genuine backend exception are all just another reason `available` is False or `note` is set, never a 500
(mirrors vlm.py's own contract, one layer up)."""
from __future__ import annotations

import difflib
import os
import re
import sqlite3


def _default_db_path():
    """Same VIEWER_DB env-var + index/viewer.db fallback every build_*.py driver already resolves --
    only consulted when a caller doesn't pass db_path explicitly. The route always will (core.DB_PATH,
    same as diagnostics.py's ask.answer(core.DB_PATH, ...) call); a standalone script or this module's
    own self-test can rely on this default instead."""
    here = os.path.dirname(os.path.abspath(__file__))
    root = os.path.dirname(here)
    return os.environ.get("VIEWER_DB", os.path.join(root, "index", "viewer.db"))


def _gpu_tier():
    """Same modern-OS-plus-GPU signal office.py's _modern_tier() already uses to gate other Win10+/GPU-
    only extras (sysprobe.py's build_profile()['use_gpu']) -- fails OPEN (assume available) only when
    the probe itself can't run for any reason, same "a probe glitch must never break extraction"
    precedent office.py sets; a probe that runs cleanly and reports no GPU correctly gates this feature
    OFF, per the design spec ('Ask this page' isn't offered at all on a no-GPU machine, not offered-and-
    unusably-slow). Florence-2-base is small enough to technically run on CPU, but this app's documented
    posture for this catalog entry is Advanced/GPU-fork-only, matching RapidOCR-on-onnxruntime-gpu."""
    try:
        here = os.path.dirname(os.path.abspath(__file__))
        import sys as _sys
        if here not in _sys.path:
            _sys.path.insert(0, here)
        import sysprobe
        return bool(sysprobe.load_or_build().get("use_gpu", True))
    except Exception:
        return True


def available():
    """True only when a real vision-language backend is importable (vlm.available()) AND this machine
    is on the GPU-capable tier. Checked BEFORE any model-load attempt (vlm.py's own _load_backend()
    already isolates the import; this adds the tier gate on top) so CI -- no GPU, no downloaded weights
    -- and any legacy/lite-fork machine report False cleanly and cheaply, with zero import side effects
    beyond vlm.py itself (which is stdlib-only)."""
    import vlm
    return vlm.available() and _gpu_tier()


def _page_image(db_path, doc_id, page, dpi=150):
    """Render one page to an RGB array -- same recipe doc_extractors.py's own _page_gray() uses for
    /api/vlm, duplicated rather than imported (features/routes/* must never be a dependency of an
    engine/ core module; the import direction only ever goes the other way -- routes import core
    modules, not vice versa). Resolves doc_id -> filesystem path via its OWN read-only connection
    (this module has no `core` DI; see module docstring). Returns None on ANY failure -- bad doc id,
    missing/moved file, page number out of range, pymupdf not installed -- never raises; the caller
    folds a None straight into the same graceful 'note' contract everything else here has."""
    try:
        did = int(doc_id)
    except (TypeError, ValueError):
        return None
    path = None
    try:
        con = sqlite3.connect("file:%s?mode=ro" % db_path, uri=True)
        try:
            r = con.execute("SELECT path FROM documents WHERE id=?", (did,)).fetchone()
            path = r[0] if r else None
        finally:
            con.close()
    except Exception:
        return None
    if not path or not os.path.exists(path):
        return None
    try:
        import pymupdf as fitz
        import numpy as np
        d = fitz.open(path)
        try:
            pg = max(1, min(int(page), d.page_count))   # clamp: page<=0 must never wrap to the wrong page
            pix = d[pg - 1].get_pixmap(dpi=dpi)
            arr = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
            return arr[:, :, :3] if arr.shape[2] >= 3 else arr
        finally:
            d.close()
    except Exception:
        return None


def _page_ocr_text(db_path, doc_id, page):
    """This page's own already-stored, already-trusted OCR/text-layer body -- the OCR cross-check's
    ground truth. Reads the exact same `pages.body_text` field field_tools.py/procedure_feature.py already
    query (`SELECT body_text FROM pages WHERE document_id=? AND page_number=?`), through this module's OWN
    read-only connection -- same pattern as `_page_image()` above (this module has no `core` DI; see
    module docstring). Returns "" on ANY failure -- bad doc id, no such page, closed/locked db, missing
    row -- never raises; the caller folds an empty string into "no overlap found" rather than treating a
    lookup failure as a separate case."""
    try:
        did = int(doc_id)
        pg = int(page)
    except (TypeError, ValueError):
        return ""
    try:
        con = sqlite3.connect("file:%s?mode=ro" % db_path, uri=True)
        try:
            r = con.execute("SELECT body_text FROM pages WHERE document_id=? AND page_number=? LIMIT 1",
                             (did, pg)).fetchone()
            return (r[0] if r else "") or ""
        finally:
            con.close()
    except Exception:
        return ""


_WORD_RE = re.compile(r"[a-z0-9]+")


def _tokens(s):
    return _WORD_RE.findall((s or "").lower())


# OCR cross-check threshold: 0.6 (60% of the claimed phrase's own words found, in order, on the page).
# Mirrors dedup.py's own 0.6 threshold for "meaningfully similar but not byte-identical" content (its
# edition-vs-different-document self-test case) -- lenient enough to survive the model's own paraphrasing
# plus this page's OCR noise, strict enough that an unrelated or fabricated claim (near-zero shared word
# sequence with the real page text) still fails clearly. See _ocr_overlap()'s own docstring for why this
# is measured as coverage of the SHORT side rather than a plain SequenceMatcher.ratio().
_OCR_OVERLAP_THRESHOLD = 0.6


def _ocr_overlap(claimed_text, page_text):
    """Fraction of `claimed_text`'s own words that difflib.SequenceMatcher finds, IN ORDER (gaps allowed),
    somewhere inside `page_text` -- both compared as lowercased word-token sequences, so whitespace/
    punctuation/OCR-spacing differences never count against a match; word identity and relative order do.
    Deliberately NOT a plain `SequenceMatcher(a, b).ratio()`: that formula is 2*M/(len(a)+len(b)), which is
    dominated by len(page_text) the moment a page has any real amount of text on it -- a perfect, verbatim
    substring match of a short claimed sentence inside a multi-paragraph page would still score near zero.
    Measuring matched-block coverage of the SHORT side only (the claim, not the whole page) is the correct
    shape for "is this specific short claim actually present on this longer page," which is the actual
    question the OCR cross-check needs answered. Returns 0.0 for an empty claim or an empty/unreadable
    page -- never raises, never divides by zero.

    DELIBERATELY NOT SUFFICIENT ON ITS OWN (see _value_grounded() below, which must ALSO pass): this
    scores every word in the claim equally, including the boilerplate around a measurement ("bolt",
    "torque", "is", "wrench", "required", ...). A hallucinated claim that keeps the real sentence's wording
    but swaps the actual number ("35 N-m" claimed against a page that really says "22 N-m") still clears a
    high threshold here, because the surrounding words -- not the value itself -- dominate the score.
    Confirmed live during review: _ocr_overlap('Bolt torque is 35 N-m. Torque wrench required for
    reassembly', 'Bolt torque is 22 N-m. Torque wrench required for reassembly.') == 0.909, i.e. a WRONG
    torque value alone does not move this score meaningfully. This function still matters as a check
    against wholesale off-topic/fabricated claims (near-zero overlap when the claim isn't from this page at
    all); it just cannot be trusted alone to catch a swapped digit inside an otherwise-real sentence."""
    a = _tokens(claimed_text)
    b = _tokens(page_text)
    if not a or not b:
        return 0.0
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    matched = sum(blk.size for blk in sm.get_matching_blocks())
    return matched / len(a)


def _value_grounded(structured, page_text):
    """THE check that actually catches a hallucinated/swapped VALUE, which _ocr_overlap() alone cannot
    (see its docstring) -- every token of the claimed value (and value2, for a range) must appear, as its
    own literal word-token, somewhere in the page's real OCR text. Tokenized the SAME way _ocr_overlap()
    tokenizes everything else (_tokens(), lowercased [a-z0-9]+ runs) so "0.5" and "-40" compare against
    page text on equal footing regardless of how punctuation/sign characters get split -- a value string
    that tokenizes to nothing (should not happen for anything measures.py extracts, but fail closed rather
    than assume) is treated as ungrounded, never as vacuously true. Requires EVERY token present (not a
    coverage fraction) -- there is no partial credit for a wrong digit; "22" containing the substring "2"
    is not what this checks, exact whole-token identity is."""
    want = _tokens(structured.get("value"))
    v2 = structured.get("value2")
    if v2 not in (None, ""):
        want += _tokens(v2)
    if not want:
        return False
    have = set(_tokens(page_text))
    return all(tok in have for tok in want)


def _split_answer(raw):
    """vlm.ask()'s `answer` is now (v1.4.0) either a bare string or a {"text":..., "region":{...}} dict
    -- fold either shape into a plain (answer_text, region) pair so the rest of this module only has to
    reason about one shape. `region` is None whenever the backend didn't ground (bare-string answer, or
    a dict that omitted the key) -- callers must treat it as optional either way, exactly like vlm.py's
    own contract requires."""
    if raw is None:
        return None, None
    if isinstance(raw, dict):
        return raw.get("text"), raw.get("region")
    return str(raw), None


def ask(doc_id, page, question, mode="text", strict=False, db_path=None, _backend=None, _image=None,
        _page_text=None):
    """Ask a vision-language backend a question about one page, cited to doc_id/page. THE entry point
    both consumers share (the interactive route now; the Phase 2 batch tool later) so trust-tier and
    verification logic lives in exactly one place. `db_path` defaults to VIEWER_DB/index/viewer.db when
    omitted (see _default_db_path()); the route always supplies core.DB_PATH explicitly instead.
    `_backend`/`_image`/`_page_text` are test-only injectable hooks -- `_backend` mirrors vlm.ask()'s own
    `_backend` param (bypasses vlm.py's real _load_backend() import), `_image` bypasses the real doc_id/
    page -> rendered-page-array resolution, and `_page_text` bypasses the real pages.body_text lookup the
    OCR cross-check uses -- so this module's self-test can exercise the full text-mode/trust-cap path AND
    the structured/strict verification path without a real PDF or a populated `documents`/`pages` table.
    Never raises; always returns {available, answer_text, structured, region, source_text, trust_tier,
    verified, backend, note}."""
    out = {"available": False, "answer_text": None, "structured": None, "region": None,
           "source_text": None, "trust_tier": None, "verified": False, "backend": None, "note": ""}

    if mode not in ("text", "structured"):
        out["note"] = "unknown mode %r (expected 'text' or 'structured')" % (mode,)
        return out

    if mode == "structured" or strict:
        # Phase 2 (design spec's "Automatic consumer" section): typed extraction + the two-part
        # self-grounding/OCR-cross-check verification pass, gating `verified` before this row could ever
        # be considered for index/pageqa.db (persistence itself stays the batch driver's job, not this
        # module's -- see module docstring).
        if _backend is None and not available():
            out["note"] = ("No vision-language backend installed, or this machine isn't on the GPU-capable "
                            "tier catalog §10.1 needs. Add engine/vlm_backend.py's dependencies "
                            "(transformers + torch) or set VIEWER_VLM; see docs/SYSTEM-REQUIREMENTS.md.")
            return out

        if _image is not None:
            img = _image
        else:
            img = _page_image(db_path or _default_db_path(), doc_id, page)
        if img is None:
            out["available"] = True
            out["note"] = "could not render doc %r page %r (bad id, missing file, or page out of range)" % (
                doc_id, page)
            return out

        import vlm
        res = vlm.ask(img, question, _backend=_backend)
        out["available"] = bool(res.get("available"))
        out["backend"] = res.get("backend")
        if not res.get("available"):
            out["note"] = res.get("note") or ""
            return out
        if res.get("answer") is None:
            out["note"] = res.get("note") or "backend returned no answer"
            return out

        answer_text, _initial_region = _split_answer(res.get("answer"))
        out["answer_text"] = answer_text
        # `_initial_region` (ask()'s own grounding, if the backend does that too) is deliberately NOT the
        # verification signal here -- it's the model grounding its OWN freshly-generated text, exactly the
        # weaker check the design resolution says NOT to reuse. `region` below comes only from vlm.ground()
        # re-checking the specific claimed phrase, once one has actually been parsed out of the answer.

        # (b) parse a TYPED value out of the free-text answer via measures.py's OWN extraction -- the
        # established, tested way this codebase turns free text into {type,value,value2,unit} (no
        # parallel regex logic here). Nothing extractable => nothing to verify; fail loud, never fabricate
        # a type/value this module made up itself (R13).
        import measures
        found = measures.extract(answer_text or "", cap=1)
        if not found:
            out["verified"] = False
            out["note"] = "measures.py found no extractable typed value in the answer text -- nothing to verify"
            return out
        m0 = found[0]
        out["structured"] = {"type": m0["type"], "value": m0["value"], "value2": m0["value2"], "unit": m0["unit"]}
        # measures.py's own "context" window -- the sentence-fragment the number/unit actually matched
        # inside, not just the bare few-character raw token ("35 N-m") and not the whole (possibly multi-
        # topic) answer_text -- is used as the "specific claimed phrase" for BOTH checks below: it's more
        # locatable/groundable than the bare token (a bounding box for "35 N-m" alone is nearly meaningless
        # -- that exact string can appear anywhere) and more targeted than the full free-text answer.
        source_text = m0["context"]
        out["source_text"] = source_text

        # (c) self-grounding: locate THIS specific claimed phrase back on the actual page image, via
        # vlm.ground() -- NOT a second vlm.ask() (design resolution: ask()'s own grounding, if any, only
        # ever grounds text it just generated itself, which cannot re-check an already-made claim).
        gres = vlm.ground(img, source_text, _backend=_backend)
        region = gres.get("region") if gres.get("available") else None
        out["region"] = region
        if not region:
            out["verified"] = False
            out["note"] = "self-grounding failed -- %s" % (gres.get("note") or "vlm.ground() found no region")
            return out

        # (d) OCR cross-check: independent of the model's own self-consistency -- does the claimed phrase
        # substantially overlap what THIS page's own already-trusted stored OCR text actually says? TWO
        # PARTS, both required -- see each function's own docstring for why neither is sufficient alone:
        #   - _ocr_overlap(): the claim's surrounding context is genuinely from this page, not fabricated
        #     or lifted from an unrelated document (catches wholesale hallucination).
        #   - _value_grounded(): the SPECIFIC claimed number itself -- not just the sentence around it --
        #     literally appears on this page (catches a swapped/hallucinated digit inside an otherwise-
        #     real sentence, which _ocr_overlap() alone was proven, live, NOT to catch).
        page_text = _page_text if _page_text is not None else _page_ocr_text(
            db_path or _default_db_path(), doc_id, page)
        overlap = _ocr_overlap(source_text, page_text)
        if overlap < _OCR_OVERLAP_THRESHOLD:
            out["verified"] = False
            out["note"] = ("OCR cross-check failed -- claimed text does not substantially overlap this "
                            "page's own stored OCR text (word-overlap %.2f < %.2f threshold)"
                            % (overlap, _OCR_OVERLAP_THRESHOLD))
            return out
        if not _value_grounded(out["structured"], page_text):
            out["verified"] = False
            out["note"] = ("OCR cross-check failed -- the claimed value %r%s does not itself appear in "
                            "this page's own stored OCR text, even though the surrounding phrasing does "
                            "(the specific number, not just the sentence, must be real)"
                            % (out["structured"].get("value"),
                               (" (or %r)" % out["structured"].get("value2")) if out["structured"].get("value2") else ""))
            return out

        # (e) all checks passed.
        out["verified"] = True
        out["note"] = "verified -- self-grounded, and both the phrase and its specific value cross-checked against this page's own stored text"
        return out

    # mode="text", strict=False from here down.
    if _backend is None and not available():
        out["note"] = ("No vision-language backend installed, or this machine isn't on the GPU-capable "
                        "tier catalog §10.1 needs. Add engine/vlm_backend.py's dependencies "
                        "(transformers + torch) or set VIEWER_VLM; see docs/SYSTEM-REQUIREMENTS.md.")
        return out

    if _image is not None:
        img = _image
    else:
        img = _page_image(db_path or _default_db_path(), doc_id, page)
    if img is None:
        out["available"] = True
        out["note"] = "could not render doc %r page %r (bad id, missing file, or page out of range)" % (doc_id, page)
        return out

    import vlm
    res = vlm.ask(img, question, _backend=_backend)
    out["available"] = bool(res.get("available"))
    out["backend"] = res.get("backend")
    if not res.get("available"):
        out["note"] = res.get("note") or ""
        return out
    if res.get("answer") is None:
        out["note"] = res.get("note") or "backend returned no answer"
        return out

    out["answer_text"], out["region"] = _split_answer(res.get("answer"))
    # strict=False: HARD-CAPPED at 'review' no matter what the backend claims -- a human is looking at
    # the actual page right there, this is a second pair of eyes, not a verified fact (R13; design
    # spec's "Interactive consumer" section). Reuses trust.py's own vocabulary via its normal "explicit
    # upstream confidence label is respected" path (trust.py's own docstring precedent) rather than
    # hardcoding the string "review" here and duplicating what that module already means by it.
    import trust
    out["trust_tier"] = trust.level(confidence="review")
    out["verified"] = False              # only ever meaningful once strict=True lands in Phase 2
    out["note"] = "AI-read -- verify on page."
    return out


# --------------------------------------------------------------------------- #
# self-test: `python pageqa.py` (mirrors vlm.py's own __main__ convention:    #
# no real backend/DB/PDF needed -- graceful degrade + an injectable fake)     #
# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    # v1.47: force a genuinely-nonexistent VIEWER_VLM module name, rather than relying on the ambient
    # environment never having transformers/torch installed. That assumption broke for real this session:
    # once sentence-transformers (and its transformers/torch deps) got installed, vlm.available() started
    # returning True -- and since this module's own available() is `vlm.available() and _gpu_tier()`, on
    # a real GPU-equipped dev machine that whole gate silently passed, skipping straight past the "no
    # backend" short-circuit (line ~360) into a real page-render attempt for a doc/page that doesn't
    # exist in this self-test's fixture-free context, surfacing as a confusing "could not render doc 1
    # page 1" note instead of the intended "no backend installed" one. Forcing the env var here makes
    # vlm.available() -- and therefore this module's available() -- return False deterministically
    # regardless of what happens to be installed or which GPU this host has, matching the identical fix
    # already applied to engine/vlm.py's own self-test and engine/tests/test_pageqa.py.
    os.environ["VIEWER_VLM"] = "definitely_not_a_real_vlm_backend_module_xyz123"

    # no backend installed -> must degrade cleanly, never crash, same contract vlm.py itself already
    # guarantees one layer down.
    r = ask(1, 1, "what is this?")
    assert r["available"] is False and r["answer_text"] is None and r["trust_tier"] is None, r
    assert r["verified"] is False and r["region"] is None, r

    import types
    _Fake = types.SimpleNamespace(__name__="fake_vlm",
                                   ask=lambda image, question: "Torque value is 30 ft-lb.")
    r2 = ask(1, 1, "torque?", _backend=_Fake, _image="fake-page-array")
    assert r2["available"] and r2["answer_text"] == "Torque value is 30 ft-lb.", r2
    assert r2["backend"] == "fake_vlm", r2
    assert r2["trust_tier"] == "review", r2      # hard-capped -- R13, never anything else in text/non-strict mode
    assert r2["verified"] is False, r2           # only meaningful once strict=True (Phase 2)
    assert r2["region"] is None, r2              # this fake backend doesn't ground

    # v1.4.0 vlm.ask() widened contract: a backend MAY return {"text":..., "region":{...}} instead of a
    # bare string -- pageqa.py must fold either shape into the same answer_text/region pair.
    _FakeGrounded = types.SimpleNamespace(
        __name__="fake_vlm_grounded",
        ask=lambda image, question: {"text": "Bolt torque is 35 N-m.",
                                      "region": {"x0": 0.1, "y0": 0.2, "x1": 0.4, "y1": 0.3}})
    r3 = ask(1, 1, "torque?", _backend=_FakeGrounded, _image="fake-page-array")
    assert r3["answer_text"] == "Bolt torque is 35 N-m.", r3
    assert r3["region"] == {"x0": 0.1, "y0": 0.2, "x1": 0.4, "y1": 0.3}, r3
    assert r3["trust_tier"] == "review", r3      # still hard-capped even with a grounded region

    # a backend that errors mid-call must still degrade, never raise out of pageqa.ask().
    _FakeBroken = types.SimpleNamespace(__name__="fake_vlm_broken",
                                         ask=lambda image, question: (_ for _ in ()).throw(RuntimeError("boom")))
    r4 = ask(1, 1, "torque?", _backend=_FakeBroken, _image="fake-page-array")
    assert r4["available"] is True and r4["answer_text"] is None, r4
    assert "backend error" in r4["note"], r4

    # --------------------------------------------------------------------- #
    # mode="structured", strict=True (Phase 2): typed extraction + the      #
    # two-part self-grounding/OCR-cross-check verification pass.           #
    # --------------------------------------------------------------------- #

    # Case 1: ask-backend and ground-backend AGREE, and the claimed phrase genuinely overlaps this page's
    # own stored OCR text -> verified=True, with the typed value + region + source_text all populated.
    _FakeAskGround = types.SimpleNamespace(
        __name__="fake_vlm_ask_ground",
        ask=lambda image, question: "Bolt torque is 35 N-m.",
        ground=lambda image, phrase: {"x0": 0.1, "y0": 0.2, "x1": 0.4, "y1": 0.3})
    s1 = ask(1, 1, "torque?", mode="structured", strict=True, _backend=_FakeAskGround,
             _image="fake-page-array",
             _page_text="Page 12: Bolt torque is 35 N-m. Torque wrench required for reassembly.")
    assert s1["available"] is True, s1
    assert s1["verified"] is True, s1
    assert s1["structured"] == {"type": "torque", "value": "35", "value2": None, "unit": "N-m"}, s1
    assert s1["region"] == {"x0": 0.1, "y0": 0.2, "x1": 0.4, "y1": 0.3}, s1
    assert s1["source_text"] and "35" in s1["source_text"], s1
    assert s1["answer_text"] == "Bolt torque is 35 N-m.", s1

    # Case 2: self-grounding fails (vlm.ground() finds no region for the claimed phrase) -> verified=False,
    # even though the ask-backend's answer itself parsed fine and would otherwise have OCR-matched.
    _FakeGroundFails = types.SimpleNamespace(
        __name__="fake_vlm_ground_fails",
        ask=lambda image, question: "Bolt torque is 35 N-m.",
        ground=lambda image, phrase: None)
    s2 = ask(1, 1, "torque?", mode="structured", strict=True, _backend=_FakeGroundFails,
             _image="fake-page-array",
             _page_text="Page 12: Bolt torque is 35 N-m. Torque wrench required for reassembly.")
    assert s2["available"] is True, s2
    assert s2["verified"] is False, s2
    assert s2["region"] is None, s2
    assert "self-grounding failed" in s2["note"], s2
    assert s2["structured"] == {"type": "torque", "value": "35", "value2": None, "unit": "N-m"}, s2  # parsed OK

    # Case 3: self-grounding succeeds, but the claimed text does NOT substantially overlap this page's own
    # stored OCR text (e.g. the model hallucinated a value not actually on this page) -> verified=False.
    s3 = ask(1, 1, "torque?", mode="structured", strict=True, _backend=_FakeAskGround,
             _image="fake-page-array",
             _page_text="This page covers coolant capacity, fan belt replacement, and battery service.")
    assert s3["available"] is True, s3
    assert s3["verified"] is False, s3
    assert s3["region"] == {"x0": 0.1, "y0": 0.2, "x1": 0.4, "y1": 0.3}, s3   # grounding itself DID succeed
    assert "OCR cross-check failed" in s3["note"], s3

    # Case 4: measures.py finds NOTHING extractable in the answer text at all -> nothing to verify;
    # verified=False with a clear note, never a crash, and grounding/OCR are never even attempted.
    _FakeNoMeasure = types.SimpleNamespace(
        __name__="fake_vlm_no_measure",
        ask=lambda image, question: "This is a general description of the page with no measurable values.",
        ground=lambda image, phrase: {"x0": 0.1, "y0": 0.2, "x1": 0.4, "y1": 0.3})
    s4 = ask(1, 1, "torque?", mode="structured", strict=True, _backend=_FakeNoMeasure,
             _image="fake-page-array", _page_text="irrelevant")
    assert s4["available"] is True, s4
    assert s4["verified"] is False, s4
    assert s4["structured"] is None, s4
    assert s4["region"] is None, s4                  # ground() never reached -- nothing to ground yet
    assert "nothing to verify" in s4["note"], s4

    # Case 5 (adversarial-review regression, found live): self-grounding succeeds AND the claimed
    # sentence's surrounding wording genuinely overlaps the page -- but the SPECIFIC claimed value is
    # wrong (page really says 22 N-m, not 35 N-m). _ocr_overlap() ALONE scores this 0.909 -- comfortably
    # above the 0.6 threshold -- because it weighs every word equally and the boilerplate around the
    # number ("bolt torque is ... n-m. torque wrench required for reassembly") dominates a short claim.
    # A wrong number surrounded by correct prose must NOT verify; this is exactly the failure mode
    # _value_grounded() exists to close, and this case is the proof it actually does.
    s5 = ask(1, 1, "torque?", mode="structured", strict=True, _backend=_FakeAskGround,
             _image="fake-page-array",
             _page_text="Bolt torque is 22 N-m. Torque wrench required for reassembly.")
    assert s5["available"] is True, s5
    assert _ocr_overlap(s5["source_text"], "Bolt torque is 22 N-m. Torque wrench required for reassembly.") >= 0.6, \
        "test fixture assumption broken -- _ocr_overlap alone was supposed to still pass this case"
    assert s5["verified"] is False, s5          # must fail DESPITE passing _ocr_overlap alone
    assert s5["region"] == {"x0": 0.1, "y0": 0.2, "x1": 0.4, "y1": 0.3}, s5   # grounding itself DID succeed
    assert "does not itself appear" in s5["note"], s5

    # a backend with no vision-language support at all -> mode="structured" degrades exactly like
    # mode="text" does (available=False, clean note), never a crash.
    s6 = ask(1, 1, "torque?", mode="structured", strict=True)
    assert s6["available"] is False and s6["verified"] is False, s6

    # an unknown mode is a clean note, not a KeyError/crash.
    r7 = ask(1, 1, "torque?", mode="bogus")
    assert r7["available"] is False and "unknown mode" in r7["note"], r7

    print("pageqa self-test OK  (graceful degrade with no backend; text-mode answers hard-capped at "
          "'review'; bare-string and grounded-dict vlm.ask() shapes both handled; backend errors and "
          "unknown modes degrade cleanly; structured/strict verification: agreeing ask+ground -> verified, "
          "failed self-grounding -> unverified, failed OCR cross-check -> unverified, nothing extractable "
          "-> unverified with no crash, a hallucinated VALUE inside otherwise-correct phrasing -> "
          "unverified despite passing phrase-overlap alone, no backend -> clean degrade)")
# END OF FILE
