#!/usr/bin/env python3
"""THE VIEWER -- PAGE QUESTION-ANSWERING CORE (v1.0, catalog §10.1, design doc
docs/superpowers/specs/2026-08-24-vision-language-page-qa-design.md). The SHARED core both consumers of
`vlm.py`'s pluggable vision-language backend call, so neither reimplements trust-tier logic or (Phase 2)
verification -- the same reasoning that already has `cautions.py`/`_parse_procedure()` share
`textquality.annotate()` instead of each computing text quality independently. Today (Phase 1) the two
consumers are the interactive "Ask this page" page-viewer control and `ask.py`'s retrieve-then-answer
fallback; Phase 2 adds a third, `build_pageqa.py`'s batch structured-extraction sweep.

Two modes, one implemented so far:
    mode="text", strict=False  (Phase 1 -- this file, now.) Free-text answer + an optional grounded
        region, straight from vlm.ask(). Trust is HARD-CAPPED at "review" (trust.py's amber "check"
        tier) NO MATTER WHAT the backend claims -- a human is looking at the actual page right there,
        so this is a second pair of eyes, not a verified fact (R13: an AI-sourced value must never
        visually pass as authoritative). Nothing is persisted -- matches ask.py's own answer-and-
        forget contract; this module never opens anything but a read-only connection.
    mode="structured", strict=True  (Phase 2 -- NOT YET.) Typed {type, value, value2, unit, region,
        source_text} rows reusing measures.py's own taxonomy, gated behind a two-part verification
        pass (self-grounding re-check + an OCR cross-check against this page's own already-trusted
        stored text) before a row is ever allowed into index/pageqa.db. Both params are already
        accepted by ask() below -- calling either now returns a clean, explicit "not yet implemented"
        note (this module's whole philosophy is "never raise, always return the documented dict"; an
        unimplemented mode is just one more reason `note` is set, not a special case a caller has to
        catch separately) rather than an AttributeError, so Phase 2 only has to ADD real behavior
        behind this branch -- the public signature and every existing caller are already correct for
        it (R1: additive, never a breaking rework).

Read-only; `db_path` is passed explicitly (ask.py's own `answer(db_path, index_dir, question, ...)`
convention, and coverage.py's "functions take db_path + index_dir explicitly, no core injection") --
this module has no `core` DI because the Phase 2 batch driver that will also call ask() is a standalone
host script, not a route; a bare default is resolved from VIEWER_DB / index/viewer.db (same env-var
convention every build_*.py driver already uses) only when a caller doesn't supply one. Never raises --
every path returns the same {available, answer_text, region, trust_tier, verified, backend, note} shape;
a missing backend, a GPU-less machine, a bad doc/page, or a genuine backend exception are all just
another reason `available` is False or `note` is set, never a 500 (mirrors vlm.py's own contract, one
layer up)."""
from __future__ import annotations

import os
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


def ask(doc_id, page, question, mode="text", strict=False, db_path=None, _backend=None, _image=None):
    """Ask a vision-language backend a question about one page, cited to doc_id/page. THE entry point
    both consumers share (the interactive route now; the Phase 2 batch tool later) so trust-tier and
    verification logic lives in exactly one place. `db_path` defaults to VIEWER_DB/index/viewer.db when
    omitted (see _default_db_path()); the route always supplies core.DB_PATH explicitly instead.
    `_backend`/`_image` are test-only injectable hooks -- `_backend` mirrors vlm.ask()'s own `_backend`
    param (bypasses vlm.py's real _load_backend() import), and `_image` bypasses the real doc_id/page ->
    rendered-page-array resolution the same way, so this module's self-test can exercise the full text-
    mode/trust-cap path without a real PDF or a populated `documents` table. Never raises; always
    returns {available, answer_text, region, trust_tier, verified, backend, note}."""
    out = {"available": False, "answer_text": None, "region": None, "trust_tier": None,
           "verified": False, "backend": None, "note": ""}

    if mode not in ("text", "structured"):
        out["note"] = "unknown mode %r (expected 'text' or 'structured')" % (mode,)
        return out

    if mode == "structured" or strict:
        # Phase 2 (design spec's "Automatic consumer" section): typed extraction + the two-part
        # self-grounding/OCR-cross-check verification pass. Not implemented yet in this phase -- degrade
        # gracefully rather than raise, matching every other not-yet-wired path in this codebase.
        out["note"] = ("mode=%r/strict=%r not yet implemented -- Phase 2 (see "
                        "docs/superpowers/plans/2026-08-24-vision-language-page-qa-plan.md, items 10-17)"
                        % (mode, strict))
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
    # no backend installed (this dev/CI environment has neither transformers nor a GPU) -> must degrade
    # cleanly, never crash, same contract vlm.py itself already guarantees one layer down.
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

    # mode="structured"/strict=True: Phase 2, not yet implemented -- must degrade, never raise/crash,
    # and must say so plainly rather than silently answering as if verified.
    r5 = ask(1, 1, "torque?", mode="structured", _backend=_Fake, _image="fake-page-array")
    assert r5["available"] is False and "Phase 2" in r5["note"], r5
    r6 = ask(1, 1, "torque?", strict=True, _backend=_Fake, _image="fake-page-array")
    assert r6["available"] is False and "Phase 2" in r6["note"], r6

    # an unknown mode is a clean note, not a KeyError/crash.
    r7 = ask(1, 1, "torque?", mode="bogus")
    assert r7["available"] is False and "unknown mode" in r7["note"], r7

    print("pageqa self-test OK  (graceful degrade with no backend; text-mode answers hard-capped at "
          "'review'; bare-string and grounded-dict vlm.ask() shapes both handled; backend errors and "
          "unknown modes degrade cleanly; structured/strict correctly deferred to Phase 2)")
# END OF FILE
