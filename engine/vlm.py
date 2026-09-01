#!/usr/bin/env python3
"""THE VIEWER -- VISION-LANGUAGE INTERFACE (v1.4.0, catalog §10.1). The highest-ceiling extractor: ask a page image a
question ("what is the torque value in this table?", "what part does callout 12 point to?") and get an answer a
regex/geometry pipeline can't reach. This is the PLUGGABLE INTERFACE + graceful degrade -- it does NOT bundle a model
(that needs a GPU and a multi-GB download, host-side). Drop in a backend and it lights up; without one it reports
unavailable and the rest of the program is unaffected. This keeps the app offline-by-default and honest about what
needs the user's GPU box.

To enable (host-side): create `engine/vlm_backend.py` exposing `ask(image_path_or_array, question) -> str | dict`
(wrapping e.g. a local LLaVA / Qwen-VL / Donut / Pix2Struct model via llama.cpp or transformers -- the shipped default
is `engine/vlm_backend.py`'s Florence-2 integration). Or set the env var VIEWER_VLM to a module name implementing the
same `ask`.

v1.4.0 (design doc 2026-08-24-vision-language-page-qa-design.md): WIDENED the backend `ask` contract so a backend
that supports native grounding may return `{"text": ..., "region": {"x0","y0","x1","y1"}}` (coords normalized 0-1)
instead of a bare string -- `region` is always OPTIONAL in that dict; a backend that can't ground a phrase to a page
location just omits it, or returns a bare string exactly like every backend has always been allowed to. This module
does not itself interpret `answer`'s shape (it never has -- `ask()` below has always passed the backend's return
value through untouched); the widening is a contract change for CALLERS, not a behavior change here. `pageqa.py`
is the first caller that actually understands the dict shape -- see it for the {text, region} -> trust-tier folding.
100% backward compatible: a backend that still returns a bare string (today's/every prior shape) needs no changes
and `/api/vlm` (whose only caller understands a bare string) is completely untouched by this.

v1.5.0 (Phase 2, design doc's "design-resolution" addendum): ADDS `ground(image, phrase)` -- a NEW, separate,
optional capability, genuinely different from `ask()`/`describe()` above. `ask()`'s own grounding (when a backend
supports it) always grounds a caption/answer the BACKEND just generated -- it has no way to re-check an arbitrary
ALREADY-CLAIMED phrase supplied by the caller. `pageqa.py`'s structured/strict verification path needs exactly that
(a self-grounding re-check of ITS OWN specific claim, not a second freshly-generated answer), so `ground()` is a
direct, smaller, more targeted operation: hand it a phrase, get back where (if anywhere) that EXACT phrase is on
the page. Mirrors `describe()`'s existing role as a thin, documented convenience wrapper over the same pluggable-
backend/graceful-degrade contract `ask()` already established -- a backend without `ground()` support (there will
be others besides vlm_backend.py eventually) means "verification unavailable for this backend," not an error, not
a crash: `available` stays True, `region` is simply None, `note` says why."""
import os


def _load_backend():
    name = os.environ.get("VIEWER_VLM", "vlm_backend")
    try:
        mod = __import__(name)
        if hasattr(mod, "ask"):
            return mod
    except Exception:
        pass
    return None


def available():
    return _load_backend() is not None


def backend_name():
    b = _load_backend()
    return getattr(b, "__name__", None) if b else None


def ask(image, question, _backend=None):
    """Ask the vision-language backend a question about `image` (path or array). `_backend` is injectable for tests.
    Returns {available, answer, backend, note}. `answer` is the backend's return value UNCHANGED -- either a bare
    string (every backend before v1.4.0, and any backend that still doesn't ground) or a {"text":..., "region":...}
    dict (v1.4.0+: a backend that grounds its answer to a page location; `region` itself is always optional even
    when the dict shape is used). This function does not normalize or inspect that shape -- it never has; callers
    that care about `region` (pageqa.py) do the shape-folding themselves. Never raises."""
    b = _backend or _load_backend()
    if b is None:
        return {"available": False, "answer": None, "backend": None,
                "note": "No vision-language backend installed. Add engine/vlm_backend.py (ask(image, question)->str) "
                        "or set VIEWER_VLM; needs a GPU + local VLM model. Catalog §10.1."}
    try:
        ans = b.ask(image, question)
        return {"available": True, "answer": ans, "backend": getattr(b, "__name__", "vlm_backend"), "note": ""}
    except Exception as e:
        return {"available": True, "answer": None, "backend": getattr(b, "__name__", "vlm_backend"),
                "note": "backend error: %s" % e}


def describe(image, _backend=None):
    """Convenience: general description of a figure/page."""
    return ask(image, "Describe this technical illustration and list any part numbers, callouts, or measurements.",
               _backend=_backend)


def ground(image, phrase, _backend=None):
    """Ask the vision-language backend to locate a SPECIFIC, caller-supplied `phrase` on `image` -- a direct
    self-grounding re-check, NOT a caption-then-ground round trip. This is genuinely different from `ask()`
    (and from `describe()`, which is just `ask()` with a fixed question): `ask()`'s own grounding, when a
    backend supports it, always grounds a caption/answer the BACKEND just freshly generated -- it cannot be
    reused to re-check an arbitrary, already-claimed phrase the CALLER hands in, because it never takes one.
    `ground()` takes exactly that phrase and asks the backend "where (if anywhere) is THIS text on the page,"
    with no captioning step of its own. `pageqa.py`'s structured/strict verification path (Phase 2) calls this
    -- never a second `ask()` -- specifically because it needs to re-check ITS OWN prior claim, not generate a
    new one. `_backend` is injectable for tests, mirroring `ask()`'s own `_backend` param.

    Returns {available, region, backend, note}. `region` is a {"x0","y0","x1","y1"} dict (normalized 0-1,
    same convention as `ask()`'s grounded region) when the backend located the phrase, else None. A backend
    that has no `ground()` at all (checked via `hasattr` -- there will be others besides vlm_backend.py
    eventually) means "self-grounding verification unavailable for this backend," not an error and not a
    crash: `available` is still True (a backend loaded), `region` is simply None, `note` explains why. Never
    raises -- a backend exception is caught and folded into `note` exactly like `ask()` already does."""
    b = _backend or _load_backend()
    if b is None:
        return {"available": False, "region": None, "backend": None,
                "note": "No vision-language backend installed. Add engine/vlm_backend.py "
                        "(ground(image, phrase)->{'x0','y0','x1','y1'}|None) or set VIEWER_VLM; needs a GPU + "
                        "local VLM model. Catalog §10.1."}
    name = getattr(b, "__name__", "vlm_backend")
    if not hasattr(b, "ground"):
        return {"available": True, "region": None, "backend": name,
                "note": "backend %r has no ground() -- self-grounding verification unavailable for this "
                        "backend (not an error; some backends only implement ask())" % name}
    try:
        region = b.ground(image, phrase)
        return {"available": True, "region": region, "backend": name, "note": ""}
    except Exception as e:
        return {"available": True, "region": None, "backend": name, "note": "backend error: %s" % e}


if __name__ == "__main__":
    # v1.47: force a genuinely-nonexistent VIEWER_VLM module name for the "no backend" checks below,
    # rather than relying on the ambient environment never having a real vlm_backend/transformers/torch
    # installed. That ambient-absence assumption broke for real this session: once sentence-transformers
    # (and its transformers/torch deps) got installed, vlm_backend's default Florence-2 backend became
    # importable, so _load_backend() started returning a real (if ultimately failing-to-load) backend --
    # available flipped to True and these hardcoded "available is False" asserts failed. Forcing the env
    # var here makes _load_backend()'s __import__() fail deterministically regardless of what happens to
    # be installed, matching the same fix already applied to engine/tests/test_pageqa.py.
    os.environ["VIEWER_VLM"] = "definitely_not_a_real_vlm_backend_module_xyz123"

    # with no backend installed, it must degrade cleanly (never crash)
    r = ask("anything.png", "what is this?")
    assert r["available"] is False and r["answer"] is None and "§10.1" in r["note"], r

    import types
    _Fake = types.SimpleNamespace(__name__="fake_vlm", ask=lambda image, question: "Torque value is 30 ft-lb.")
    r2 = ask("img", "torque?", _backend=_Fake)
    assert r2["available"] and "30 ft-lb" in r2["answer"] and r2["backend"] == "fake_vlm", r2
    r3 = describe("img", _backend=_Fake)
    assert r3["available"] and r3["answer"], r3

    # v1.4.0: a backend MAY return {"text":..., "region":{...}} instead of a bare string -- ask() must
    # pass that shape through completely untouched (no coercion back to a string, no dropped keys).
    _FakeGrounded = types.SimpleNamespace(
        __name__="fake_vlm_grounded",
        ask=lambda image, question: {"text": "Bolt torque is 35 N-m.",
                                      "region": {"x0": 0.1, "y0": 0.2, "x1": 0.4, "y1": 0.3}})
    r4 = ask("img", "torque?", _backend=_FakeGrounded)
    assert r4["available"] and isinstance(r4["answer"], dict), r4
    assert r4["answer"]["text"] == "Bolt torque is 35 N-m.", r4
    assert r4["answer"]["region"] == {"x0": 0.1, "y0": 0.2, "x1": 0.4, "y1": 0.3}, r4

    # ... and a dict answer with region OMITTED (a grounding attempt that found nothing) must also pass
    # through as-is -- callers must treat 'region' as optional, never assume its presence (design spec).
    _FakeUngrounded = types.SimpleNamespace(
        __name__="fake_vlm_ungrounded", ask=lambda image, question: {"text": "General page description."})
    r5 = ask("img", "torque?", _backend=_FakeUngrounded)
    assert r5["available"] and r5["answer"] == {"text": "General page description."}, r5
    assert "region" not in r5["answer"], r5

    # v1.5.0: ground(image, phrase) -- a NEW, separate capability (self-grounding re-check of a SPECIFIC
    # claimed phrase, not a second caption-then-ground ask()). Must degrade cleanly with no backend, same
    # contract as ask()/describe() above.
    g1 = ground("anything.png", "torque bolts to 35 N-m")
    assert g1["available"] is False and g1["region"] is None and "§10.1" in g1["note"], g1

    _FakeGrounder = types.SimpleNamespace(
        __name__="fake_vlm_grounder",
        ask=lambda image, question: "unused",
        ground=lambda image, phrase: {"x0": 0.27, "y0": 0.44, "x1": 0.56, "y1": 0.60})
    g2 = ground("img", "torque bolts to 35 N-m", _backend=_FakeGrounder)
    assert g2["available"] and g2["region"] == {"x0": 0.27, "y0": 0.44, "x1": 0.56, "y1": 0.60}, g2
    assert g2["backend"] == "fake_vlm_grounder", g2

    # a backend with NO ground() support at all (e.g. _Fake above, which only has ask()) means
    # "self-grounding verification unavailable for THIS backend" -- available stays True, region is None,
    # never an exception.
    g3 = ground("img", "torque bolts to 35 N-m", _backend=_Fake)
    assert g3["available"] and g3["region"] is None, g3
    assert "no ground()" in g3["note"], g3

    # a phrase the backend genuinely can't locate on the page -> None region is a real (non-error) signal.
    _FakeNoMatch = types.SimpleNamespace(__name__="fake_vlm_nomatch", ask=lambda i, q: "x",
                                          ground=lambda image, phrase: None)
    g4 = ground("img", "nonexistent phrase", _backend=_FakeNoMatch)
    assert g4["available"] and g4["region"] is None and g4["note"] == "", g4

    # a backend whose ground() raises must still degrade -- never crash out of vlm.ground().
    _FakeGroundBroken = types.SimpleNamespace(
        __name__="fake_vlm_ground_broken", ask=lambda i, q: "x",
        ground=lambda image, phrase: (_ for _ in ()).throw(RuntimeError("boom")))
    g5 = ground("img", "torque?", _backend=_FakeGroundBroken)
    assert g5["available"] and g5["region"] is None and "backend error" in g5["note"], g5

    print("vlm self-test OK  (graceful degrade with no backend; pluggable backend answers when present; "
          "widened str|{text,region} contract passed through untouched either way; ground() self-grounding "
          "capability degrades cleanly with no backend/no ground()-support/no-match/exception, and passes "
          "a located region through when a backend provides one)")
# END OF FILE
