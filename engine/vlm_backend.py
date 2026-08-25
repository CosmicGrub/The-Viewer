#!/usr/bin/env python3
"""THE VIEWER -- VISION-LANGUAGE BACKEND, Florence-2 (v1.0, catalog §10.1, design doc
2026-08-24-vision-language-page-qa-design.md). The real, shipped default for `engine/vlm.py`'s pluggable
interface: `microsoft/Florence-2-base` via `transformers` (`AutoModelForCausalLM` + `AutoProcessor`,
`trust_remote_code=True` -- Florence-2 ships its own modeling code, not a stock architecture the base
`transformers` package knows). Advanced/GPU-fork-only optional dependency, same posture as RapidOCR-on-
`onnxruntime-gpu` or `easyocr` (see requirements.txt's OPTIONAL tier) -- the Lite/portable fork never
imports this file at all, and `vlm.py`'s `_load_backend()` already isolates a missing/failed import via
`__import__()` + `try/except`, so `import vlm` and `import pageqa` never need `transformers`/`torch`
installed; only `import vlm_backend` (directly, or transitively through `_load_backend()`) does. That is
why the two heavy imports below are UNGUARDED at module scope -- deliberately, so a missing dependency
fails the *import itself* immediately and loudly, which `_load_backend()`'s `try/except` already expects
and turns into a clean "unavailable" rather than a crash anywhere else in the app.

LAZY MODEL LOAD: importing this module only needs the `transformers`/`torch` *packages* to be installed --
it does NOT touch the network or download the ~460MB Florence-2-base weights until the first real
`ask()` call (mirrors `embed.py`'s `_load_model()` lazy-load convention, including its tri-state cache:
None = not yet tried, False = tried and failed, else = loaded). A host can safely `import vlm_backend`
just to probe availability (`vlm.available()` does exactly this) without ever paying for a model load.

WHY THE PROMPTING LOOKS LIKE THIS (read before changing it): Florence-2 has NO native open-ended
visual-question-answering task in its documented task-prompt vocabulary (`<OCR>`, `<CAPTION>`,
`<DETAILED_CAPTION>`, `<MORE_DETAILED_CAPTION>`, `<OD>`, `<DENSE_REGION_CAPTION>`, `<REGION_PROPOSAL>`,
`<CAPTION_TO_PHRASE_GROUNDING>`, `<REFERRING_EXPRESSION_SEGMENTATION>`, `<REGION_TO_SEGMENTATION>`,
`<OPEN_VOCABULARY_DETECTION>`, `<REGION_TO_CATEGORY>`, `<REGION_TO_DESCRIPTION>`, `<OCR_WITH_REGION>`) --
it cannot be instructed "answer this question" the way an instruction-tuned VLM can. This ships the
official cascaded pattern from Florence-2's own model card instead: caption the whole page with
`<MORE_DETAILED_CAPTION>`, then ground THAT caption's noun phrases onto the page with
`<CAPTION_TO_PHRASE_GROUNDING>` (this is a real Florence-2 task -- it locates phrases already present in
whatever text it's given; it does not invent new ones). The grounded phrase whose words overlap the
ASKED question the most (same plain term-overlap ranking `ask.py`'s own `extract_answer()` already uses
to score sentences against a question -- reused as an idea, not imported, since that function is
`ask.py`-private and this module must stay independently importable/skippable) is treated as the
"answer", with its bounding box as `region`. This is a genuine, documented approximation of VQA, NOT
real instruction-following -- said plainly here so nobody mistakes it for more than it is (R13: an
AI-sourced value must never visually pass as more authoritative than it is; `pageqa.py` is what actually
enforces the "review"-tier cap on anything this file returns, but the honesty starts in this docstring).

Returns `{"text": ..., "region": {"x0","y0","x1","y1"}}` matching `vlm.py`'s v1.4.0 widened contract --
`region` present only when grounding found a matching phrase; coordinates normalized 0-1 (divided by the
image's own pixel size) so callers never need to know what DPI the page was rendered at."""
import os
import re

import torch                                            # unguarded on purpose -- see module docstring
from transformers import AutoModelForCausalLM, AutoProcessor
from PIL import Image

_MODEL_ID = "microsoft/Florence-2-base"

# Task-prompt strings are Florence-2's actual vocabulary (see module docstring) -- not free text.
_TASK_CAPTION = "<MORE_DETAILED_CAPTION>"
_TASK_GROUND = "<CAPTION_TO_PHRASE_GROUNDING>"

# Tri-state lazy-load cache (embed.py's _load_model() convention): None = not yet tried, False = tried
# and failed (don't retry a broken/absent install on every single ask() call -- a failed load attempt
# still costs a real GPU/CPU probe + an attempted HF cache read), else (model, processor, device, dtype).
_LOADED = None

_WORD = re.compile(r"[A-Za-z0-9]+")


def _terms(s):
    return {w.lower() for w in _WORD.findall(s or "") if len(w) > 1}


def _load():
    """Load Florence-2 once, on first real use. NEVER called at import time (see module docstring) --
    only from ask() below. Returns the cached (model, processor, device, dtype) tuple, or None if the
    load failed (missing weights/network for the first-ever download, no CUDA when one was assumed,
    OOM, etc.) -- ask() turns a None here into a clear RuntimeError that vlm.py's own ask() already
    catches and reports as a backend error, never a crash."""
    global _LOADED
    if _LOADED is not None:
        return _LOADED if _LOADED is not False else None
    try:
        device = "cuda" if torch.cuda.is_available() else "cpu"
        dtype = torch.float16 if device == "cuda" else torch.float32
        model = AutoModelForCausalLM.from_pretrained(
            _MODEL_ID, trust_remote_code=True, torch_dtype=dtype).to(device).eval()
        processor = AutoProcessor.from_pretrained(_MODEL_ID, trust_remote_code=True)
        _LOADED = (model, processor, device, dtype)
    except Exception:
        _LOADED = False
        return None
    return _LOADED


def _to_pil(image):
    """`image` may be a filesystem path, an already-open PIL.Image, or a numpy RGB/gray array --
    pageqa.py's _page_image() (and doc_extractors.py's own _page_gray() for /api/vlm) both hand this a
    numpy array rendered off a PDF page, never a raw file, but a path is accepted too so this backend
    stays usable standalone (e.g. a quick `python -c "import vlm_backend; vlm_backend.ask('page.png', ...)"`
    smoke test on the host)."""
    if isinstance(image, Image.Image):
        return image.convert("RGB")
    if isinstance(image, (str, bytes, os.PathLike)):
        return Image.open(image).convert("RGB")
    import numpy as np
    arr = np.asarray(image)
    if arr.ndim == 2:
        return Image.fromarray(arr).convert("RGB")
    return Image.fromarray(arr[:, :, :3] if arr.shape[-1] >= 3 else arr).convert("RGB")


def _run_task(model, processor, device, dtype, image, task_prompt, text_input=None):
    """One Florence-2 generate + post_process_generation round trip for a single task-prompt string.
    `skip_special_tokens=False` on decode is deliberate, not an oversight -- Florence-2's own
    post_process_generation() parses the task/location special tokens back OUT of the generated text
    to build the structured {bboxes, labels} / caption result; stripping them first would break it."""
    prompt = task_prompt if text_input is None else task_prompt + text_input
    inputs = processor(text=prompt, images=image, return_tensors="pt").to(device, dtype)
    with torch.no_grad():
        generated_ids = model.generate(
            input_ids=inputs["input_ids"], pixel_values=inputs["pixel_values"],
            max_new_tokens=1024, num_beams=3, do_sample=False, early_stopping=False)
    generated_text = processor.batch_decode(generated_ids, skip_special_tokens=False)[0]
    return processor.post_process_generation(generated_text, task=task_prompt,
                                               image_size=(image.width, image.height))


def _best_match(question, labels):
    """Which grounded phrase (if any) best answers `question` -- see module docstring for why this is a
    term-overlap heuristic and not real question-answering. Returns (index, score); index is None only
    when `labels` itself is empty (nothing was grounded at all)."""
    if not labels:
        return None, 0
    qterms = _terms(question)
    if not qterms:
        return 0, 0                       # no question terms to score against -- take the first phrase
    best_i, best_score = 0, -1
    for i, label in enumerate(labels):
        score = len(qterms & _terms(label))
        if score > best_score:
            best_i, best_score = i, score
    return best_i, best_score


def ask(image, question):
    """Matches vlm.py's pluggable `ask(image, question) -> str | dict` contract (hasattr(mod, "ask") is
    all `_load_backend()` checks). Returns {"text": ..., "region": {...}} -- `region` present only when
    `<CAPTION_TO_PHRASE_GROUNDING>` actually located a phrase on the page, coordinates normalized 0-1.
    Can raise: vlm.py's own ask() already wraps every backend call in try/except and turns an exception
    into a clean {"note": "backend error: ..."} response (never a crash), so this function does the real
    work and lets a genuine failure (bad weights, OOM, no CUDA when one was assumed) surface as one
    rather than silently swallowing it here too."""
    loaded = _load()
    if loaded is None:
        raise RuntimeError(
            "Florence-2 (%s) failed to load -- check that transformers/torch are installed and, if a "
            "GPU is expected, that CUDA is set up; see docs/SYSTEM-REQUIREMENTS.md." % _MODEL_ID)
    model, processor, device, dtype = loaded
    img = _to_pil(image)

    caption = (_run_task(model, processor, device, dtype, img, _TASK_CAPTION).get(_TASK_CAPTION) or "").strip()
    grounded = (_run_task(model, processor, device, dtype, img, _TASK_GROUND,
                           text_input=caption or question).get(_TASK_GROUND) or {})
    bboxes, labels = grounded.get("bboxes") or [], grounded.get("labels") or []

    idx, _score = _best_match(question, labels)
    if idx is None or not bboxes:
        return {"text": caption or "Florence-2 found nothing groundable on this page for that question."}

    x0, y0, x1, y1 = bboxes[idx]
    w, h = max(float(img.width), 1.0), max(float(img.height), 1.0)
    region = {"x0": round(max(0.0, min(1.0, x0 / w)), 4), "y0": round(max(0.0, min(1.0, y0 / h)), 4),
              "x1": round(max(0.0, min(1.0, x1 / w)), 4), "y1": round(max(0.0, min(1.0, y1 / h)), 4)}
    text = "%s -- %s" % (labels[idx], caption) if caption and caption != labels[idx] else labels[idx]
    return {"text": text, "region": region}


# --------------------------------------------------------------------------- #
# self-test: `python vlm_backend.py` (host-only -- needs transformers/torch)  #
# UNLIKE office.py/embed.py's optional-dependency self-tests, this one can't  #
# degrade to "test what's installed" -- this module's own import is the      #
# isolation boundary (module docstring), so on a machine without             #
# transformers/torch (every CI runner, this dev sandbox) `import vlm_backend`#
# itself raises before __main__ is ever reached. That's correct, not a bug:  #
# vlm.py's _load_backend() is exactly what's supposed to catch that. Only    #
# runnable, and only meaningful, on a real GPU-fork host with the OPTIONAL   #
# dependency installed (requirements.txt) -- exercises the pure, model-free  #
# helpers (_terms/_best_match) without needing a GPU or downloaded weights.  #
# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    assert _terms("Torque the bolt to 35 N-m") >= {"torque", "bolt", "n"}
    idx, score = _best_match("what is the torque value here?", ["alternator bracket", "torque spec 35 N-m"])
    assert idx == 1 and score >= 1, (idx, score)
    idx2, score2 = _best_match("anything", [])
    assert idx2 is None, (idx2, score2)
    idx3, score3 = _best_match("", ["some label"])
    assert idx3 == 0, (idx3, score3)      # no question terms -> first grounded phrase, never a crash
    print("vlm_backend self-test OK  (pure helpers only -- no model load attempted, matches this repo's "
          "no-GPU/no-weights CI environment)")
# END OF FILE
