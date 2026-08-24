#!/usr/bin/env python3
"""Regression: /page (engine/features/routes/page_render.py:r_page) must clamp the requested render
DPI against RPS's tier-keyed `render_dpi_cap` (rps.feature_flags()['render_dpi_cap']: modern=400,
lite=220, legacy=150) instead of a flat 400 (or 700 for a small clip) applied to EVERY tier alike.

Before this fix, r_page hardcoded `req_dpi = min(req_dpi, 700 if small_clip else 400)`, completely
ignoring core.RPS_FLAGS -- so a legacy Win7/Vista/low-RAM machine (tier cap 150) could still trigger
a full-page render at up to 400dpi (2.7x its intended cap) via a plain /page request, or 700dpi via
any small-clip request, bypassing the tier protection RPS's own feature_flags() docstring claims
exists ("the server reads render_dpi_cap").

Pure stdlib, no server/DB/PDF required: r_page's DPI-cap decision is pure request-handling logic, so
this drives it directly with a fake `core` (exposing only RPS_FLAGS + stub render methods that record
the dpi they were called with) and a fake handler -- isolating the clamp from rendering itself."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ENGINE = os.path.dirname(HERE)
sys.path.insert(0, ENGINE)

import features.routes.page_render as PR  # noqa: E402


class FakeHandler:
    """Minimal stand-in for viewer_app's Handler -- only what r_page touches."""
    def __init__(self):
        self.headers = {}          # .get("If-None-Match") -> None (never hit the 304 path)
        self.sent = None

    def _send(self, status, data, content_type=None, headers=None):
        self.sent = (status, data, content_type, headers)


class FakeCore:
    """Stand-in for viewer_app-as-`core`: only RPS_FLAGS + the two render entry points r_page calls."""
    def __init__(self, rps_flags):
        self.RPS_FLAGS = rps_flags
        self.captured_dpi = None

    def cached_page_render(self, doc_i, pg_i, req_dpi, clean=False, contrast=0, binarize=False):
        self.captured_dpi = req_dpi
        return b"PNGDATA"

    def _warm_adjacent(self, *a, **kw):
        pass

    def render_page_png(self, doc_i, pg_s, req_dpi, hl, clean=False, contrast=0, binarize=False, clip=None):
        self.captured_dpi = req_dpi
        return b"PNGDATA"


def _hit(rps_flags, requested_dpi, clip=None):
    """Call r_page with the given RPS_FLAGS + requested dpi (+ optional clip), return the dpi that
    actually reached the renderer."""
    fake_core = FakeCore(rps_flags)
    PR.core = fake_core
    h = FakeHandler()
    qs = {"dpi": [str(requested_dpi)], "doc": ["1"], "page": ["1"]}
    if clip is not None:
        qs["clip"] = [clip]
    PR.r_page(h, qs)
    assert h.sent is not None and h.sent[0] == 200, "r_page did not answer 200: %r" % (h.sent,)
    return fake_core.captured_dpi


def main():
    tests = []
    def check(name, cond):
        tests.append((name, cond))

    # --- (a) legacy tier: requested dpi above the tier cap clamps to the TIER's cap (150), not the
    # old flat 400/700 every tier used to get. ---
    legacy_flags = {"render_dpi_cap": 150}

    d = _hit(legacy_flags, 999)                     # plain full-page request, way over every cap
    check("legacy full-page: 999dpi clamps to tier cap 150 (not flat 400)", d == 150)

    d = _hit(legacy_flags, 999, clip="0.1,0.1,0.3,0.3")   # genuinely small clip (<=0.35 each side)
    check("legacy small-clip: 999dpi clamps to ~262 (150*1.75), not flat 700", d == int(150 * 1.75) == 262)

    d = _hit(legacy_flags, 999, clip="0,0,1,1")      # whole-page "clip" must NOT get the raised ceiling
    check("legacy whole-page clip=0,0,1,1 still capped at 150, not the small-clip bonus", d == 150)

    d = _hit(legacy_flags, 100)                      # under the cap -> passed through unchanged
    check("legacy request under cap (100) is not raised to the cap", d == 100)

    # --- (b) modern tier: behavior is UNCHANGED (still effectively 400 / 700), since modern's own
    # render_dpi_cap IS 400 -- this proves the fix doesn't regress the capable-hardware path. ---
    modern_flags = {"render_dpi_cap": 400}

    d = _hit(modern_flags, 999)
    check("modern full-page: 999dpi clamps to 400 (unchanged)", d == 400)

    d = _hit(modern_flags, 999, clip="0.1,0.1,0.3,0.3")
    check("modern small-clip: 999dpi clamps to 700 (unchanged)", d == 700)

    # --- lite tier, for completeness (mid-tier cap 220, not modern's 400 or legacy's 150). ---
    lite_flags = {"render_dpi_cap": 220}
    d = _hit(lite_flags, 999)
    check("lite full-page: 999dpi clamps to tier cap 220", d == 220)
    d = _hit(lite_flags, 999, clip="0.1,0.1,0.3,0.3")
    check("lite small-clip: 999dpi clamps to ~385 (220*1.75)", d == int(220 * 1.75) == 385)

    # --- default fallback: no render_dpi_cap key at all (e.g. viewer_app's pre-rps_init default
    # RPS_FLAGS = {"sqlite": {}, "page_cache": False, "prefetch": 0}) must fall back to 400, matching
    # the prior flat default -- never crash on a missing key. ---
    d = _hit({}, 999)
    check("missing render_dpi_cap key falls back to 400", d == 400)

    fails = [n for n, ok in tests if not ok]
    for n, ok in tests:
        print(("PASS " if ok else "FAIL ") + n)
    print("\n%d passed, %d failed" % (len(tests) - len(fails), len(fails)))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
