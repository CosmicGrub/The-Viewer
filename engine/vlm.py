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
and `/api/vlm` (whose only caller understands a bare string) is completely untouched by this."""
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


if __name__ == "__main__":
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

    print("vlm self-test OK  (graceful degrade with no backend; pluggable backend answers when present; "
          "widened str|{text,region} contract passed through untouched either way)")
# END OF FILE
