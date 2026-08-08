#!/usr/bin/env python3
"""THE VIEWER -- VISION-LANGUAGE INTERFACE (v1.3.3, catalog §10.1). The highest-ceiling extractor: ask a page image a
question ("what is the torque value in this table?", "what part does callout 12 point to?") and get an answer a
regex/geometry pipeline can't reach. This is the PLUGGABLE INTERFACE + graceful degrade -- it does NOT bundle a model
(that needs a GPU and a multi-GB download, host-side). Drop in a backend and it lights up; without one it reports
unavailable and the rest of the program is unaffected. This keeps the app offline-by-default and honest about what
needs the user's GPU box.

To enable (host-side): create `engine/vlm_backend.py` exposing `ask(image_path_or_array, question) -> str`
(wrapping e.g. a local LLaVA / Qwen-VL / Donut / Pix2Struct model via llama.cpp or transformers). Or set the env var
VIEWER_VLM to a module name implementing the same `ask`.
"""
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
    Returns {available, answer, backend, note}. Never raises."""
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
    print("vlm self-test OK  (graceful degrade with no backend; pluggable backend answers when present)")
# END OF FILE
