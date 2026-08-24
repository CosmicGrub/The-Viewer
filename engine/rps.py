#!/usr/bin/env python3
"""THE VIEWER -- Retroactive Post-Support (RPS).

Makes the modern (Win 10/11) program feel responsive on older / slower PCs (down to Win 7 / Vista)
WITHOUT changing the corpus or the index. Three runtime modes, auto-picked from the hardware probe
(sysprobe.py) and overridable:

    modern  -- full effects, server-side hi-fi loupe, page prefetch, large SQLite cache
    lite    -- effects off, lower default DPI, local-only loupe, small SQLite cache (low-RAM / HDD)
    legacy  -- lite + ES5 polyfills + Poppler render path + minimal SQLite footprint (Win 7 / Vista)

This module is PURE LOGIC (mode decision, feature flags, page-cache key) so it can be unit-tested
without a server or a GPU. The server (viewer_app.py) consumes it; nothing here writes to the index.
"""
import os, json, hashlib

VALID_MODES = ("modern", "lite", "legacy")

def mode_for(profile, override=None):
    """Pick a runtime mode from a sysprobe profile dict. `override` (modern|lite|legacy) wins if valid.
    Returns (mode, reason)."""
    if override in VALID_MODES:
        return override, "forced by user/override"
    p = profile or {}
    py_ok    = p.get("python_ok", True)
    modern   = p.get("modern_os", True)
    backend  = p.get("render_backend", "pymupdf")
    ram      = p.get("ram_gb", 16) or 0
    tier     = p.get("tier", "")
    # Legacy OS / toolchain -> legacy
    if (not py_ok) or (backend == "poppler") or (not modern):
        return "legacy", "older OS or Poppler render path or old Python -> legacy compatibility mode"
    # Modern OS but weak hardware -> lite
    if tier in ("Legacy / low-power", "Modest CPU") or ram < 8:
        return "lite", "modern OS but limited CPU/RAM -> lite-effects mode"
    return "modern", "capable machine -> full experience"


# User-facing Settings-panel choices. These are INTENT (what the user asked for); mode_for_setting()
# maps them onto the concrete engine modes using the hardware probe. Kept next to mode_for so the whole
# decision is unit-testable without a server.
# "premium" is deliberately last and deliberately never returned by mode_for()'s own hardware auto-pick
# (VALID_MODES stays exactly modern/lite/legacy) -- it's an opt-in, non-default visual-effects layer a
# capable machine can additionally choose, not a fourth concrete engine tier. See mode_for_setting()
# and PREMIUM_MIN_TIER below for the actual capability gate.
RUN_MODE_LABELS = {"auto": "Auto (recommended)", "performance": "Performance",
                   "retro": "Retroactive Post-Support", "premium": "Premium (visual effects)"}


def mode_for_setting(profile, setting):
    """Map a Settings-panel run-mode choice to a concrete engine mode. Returns (mode, reason).
        auto        -> hardware auto-pick (same as mode_for with no override)
        performance -> force the full experience (modern)
        retro       -> force the compatibility path (never full-effects); still auto-distinguishes
                       lite (modern OS but weak) from legacy (old OS / Poppler / old Python)
        premium     -> full experience (modern) PLUS the opt-in premium visual-effects layer, but ONLY
                       on hardware the auto-probe would already call "modern" on its own -- premium never
                       forces capability onto weak hardware the way "performance" forces modern. If the
                       probe wouldn't pick modern anyway, this falls back to whatever auto WOULD pick
                       (lite/legacy), with a plain-language reason explaining the fallback -- never a
                       silent downgrade.
    Back-compatible: a concrete legacy value (modern|lite|legacy) passes straight through so older
    callers and the VIEWER_MODE env var keep working unchanged."""
    s = str(setting or "auto").strip().lower()
    if s in VALID_MODES:                          # concrete mode -> honour directly (back-compat)
        return mode_for(profile, s)
    if s in ("performance", "perf", "full", "modern"):
        return "modern", "Performance mode (Settings): full experience forced"
    if s in ("retro", "rps", "retroactive", "compat", "compatibility", "lite", "legacy"):
        m, why = mode_for(profile, None)          # let the probe pick lite vs legacy...
        if m == "modern":                         # ...but never full-effects when the user forced compat
            return "lite", "Retroactive Post-Support (Settings): compatibility forced on a capable machine"
        return m, "Retroactive Post-Support (Settings): " + why
    if s in ("premium", "premiumui", "premium_ui", "hifi"):
        m, why = mode_for(profile, None)          # hardware auto-pick, never forced
        if m == "modern":
            return "modern", "Premium mode (Settings): full experience + premium visual effects (hardware supports it)"
        return m, ("Premium mode (Settings) requested, but the hardware probe says " + m +
                    " -- falling back rather than forcing premium effects onto weaker hardware (" + why + ")")
    return mode_for(profile, None)                # "auto" / unknown -> hardware auto-pick


def premium_active(profile, setting):
    """True only when the Settings-panel choice is 'premium' AND the hardware probe independently
    agrees the machine is capable (mode_for_setting() actually landed on 'modern' via the premium
    branch, not a fallback). Kept as a small, separately-testable predicate rather than parsing
    mode_for_setting()'s reason string at call sites."""
    s = str(setting or "").strip().lower()
    if s not in ("premium", "premiumui", "premium_ui", "hifi"):
        return False
    m, _ = mode_for_setting(profile, setting)
    return m == "modern"

def feature_flags(mode, premium=False):
    """Return the on/off switches + tuning for a mode. Genuinely consumed today: the UI (rps.js) reads
    `default_dpi`/`animations`/`premium_ui`, and ops.html's diagnostics table reads `effects` for display;
    the server reads `page_cache`/`prefetch`/`sqlite`/`render_dpi_cap`/`doc_cache`. `loupe` and `polyfills`
    are carried in the dict for every mode but have no live consumer: `polyfills` because rps.js applies
    its ES5 polyfills unconditionally via feature-detection before this flag is even fetched from the
    server, and `loupe` because nothing (client or server) reads it -- both are kept for payload-shape
    stability rather than because anything acts on them today.
    `premium` is additive and ONLY meaningful when mode=="modern" (see premium_active()) -- it never
    changes any of the backend-behavior values above (page_cache/prefetch/sqlite/render_dpi_cap/
    doc_cache stay exactly what "modern" already used), only adds a UI-facing marker the client's CSS
    keys off of. A caller passing premium=True with mode!="modern" gets it silently ignored, matching
    mode_for_setting()'s own "premium never forces capability onto weak hardware" contract."""
    if mode == "modern":
        f = {"mode": "modern", "effects": "full", "animations": True, "default_dpi": 150,
                "loupe": "server", "polyfills": False, "page_cache": True, "prefetch": 2,
                "render_dpi_cap": 400, "doc_cache": 8,        # open-PDF LRU size (memory)
                "sqlite": {"cache_kb": -8000, "mmap": 268435456, "temp_store": "MEMORY"}}
        f["premium_ui"] = bool(premium)
        return f
    if mode == "lite":
        return {"mode": "lite", "effects": "lite", "animations": False, "default_dpi": 120,
                "loupe": "local", "polyfills": False, "page_cache": True, "prefetch": 1,
                "render_dpi_cap": 220, "doc_cache": 3,        # fewer open PDFs on limited RAM
                "sqlite": {"cache_kb": -2000, "mmap": 0, "temp_store": "FILE"}, "premium_ui": False}
    # legacy
    return {"mode": "legacy", "effects": "lite", "animations": False, "default_dpi": 100,
            "loupe": "local", "polyfills": True, "page_cache": True, "prefetch": 0,
            "render_dpi_cap": 150, "doc_cache": 2,            # smallest footprint on Win7/Vista low-RAM
            "sqlite": {"cache_kb": -1000, "mmap": 0, "temp_store": "FILE"}, "premium_ui": False}

def profile_summary(profile, mode, reason, premium=False):
    p = profile or {}
    return {"mode": mode, "reason": reason, "flags": feature_flags(mode, premium),
            "os": p.get("os"), "modern_os": p.get("modern_os"), "tier": p.get("tier"),
            "ram_gb": p.get("ram_gb"), "render_backend": p.get("render_backend"),
            "python_ok": p.get("python_ok", True)}

# ---- page-render disk cache -------------------------------------------------
def cache_dir(index_dir):
    return os.path.join(index_dir, "pagecache")

def cache_key(doc_id, page, dpi, clean=False, contrast=0, binarize=False):
    """Deterministic filename for a full-page render. Loupe (clip) and highlight renders are transient
    and intentionally NOT cached. Returns a bare filename (no directory)."""
    parts = ["%s-%s-d%s" % (doc_id, page, int(dpi))]
    if clean: parts.append("clean")
    if contrast: parts.append("c%d" % int(contrast))
    if binarize: parts.append("bin")
    return "-".join(parts) + ".png"

def cache_path(index_dir, doc_id, page, dpi, clean=False, contrast=0, binarize=False):
    return os.path.join(cache_dir(index_dir), cache_key(doc_id, page, dpi, clean, contrast, binarize))

def cache_read(index_dir, doc_id, page, dpi, clean=False, contrast=0, binarize=False):
    p = cache_path(index_dir, doc_id, page, dpi, clean, contrast, binarize)
    try:
        if os.path.exists(p) and os.path.getsize(p) > 0:
            return open(p, "rb").read()
    except Exception:
        pass
    return None

def cache_write(index_dir, doc_id, page, dpi, data, clean=False, contrast=0, binarize=False):
    try:
        # disk guard (RPS-safe): never let the page-render cache fill the drive. Fail-open if free space
        # can't be measured, so a probe glitch never stops serving pages.
        try:
            from preflight import disk_ok
            if not disk_ok(index_dir)[0]:
                return False
        except Exception:
            pass
        d = cache_dir(index_dir); os.makedirs(d, exist_ok=True)
        p = cache_path(index_dir, doc_id, page, dpi, clean, contrast, binarize)
        tmp = p + ".tmp%d" % os.getpid()
        with open(tmp, "wb") as f: f.write(data)
        os.replace(tmp, p)
        return True
    except Exception:
        return False

def cache_stats(index_dir):
    d = cache_dir(index_dir); n = 0; sz = 0
    try:
        for f in os.listdir(d):
            if f.endswith(".png"):
                n += 1
                try: sz += os.path.getsize(os.path.join(d, f))
                except Exception: pass
    except Exception:
        pass
    return {"files": n, "bytes": sz, "dir": d}

def prebake(index_dir, render_fn, docs, dpi=120, pages_per_doc=1, clean=False, log=None):
    """Pre-render hot pages into the cache so a slow PC opens them instantly.
    render_fn(doc_id, page, dpi, clean) -> PNG bytes.  docs = iterable of (doc_id, page_count).
    Returns count rendered. Safe to re-run (skips pages already cached)."""
    made = 0
    for doc_id, pc in docs:
        for page in range(1, min(int(pages_per_doc), max(1, int(pc or 1))) + 1):
            if cache_read(index_dir, doc_id, page, dpi, clean=clean) is not None:
                continue
            try:
                data = render_fn(doc_id, page, dpi, clean)
                if data and cache_write(index_dir, doc_id, page, dpi, data, clean=clean):
                    made += 1
                    if log and made % 50 == 0: log("prebaked %d pages..." % made)
            except Exception:
                continue
    return made

if __name__ == "__main__":
    import sys
    here = os.path.dirname(os.path.abspath(__file__))
    try:
        sys.path.insert(0, here); import sysprobe
        prof = sysprobe.load_or_build()
    except Exception as e:
        prof = {}; print("(could not load profile: %s)" % e)
    ov = None
    for a in sys.argv[1:]:
        if a.startswith("--mode="): ov = a.split("=", 1)[1]
    m, why = mode_for(prof, ov)
    print("=== THE VIEWER -- Retroactive Post-Support ===")
    print("OS            :", prof.get("os"), "| modern:", prof.get("modern_os"), "| tier:", prof.get("tier"))
    print("RAM (GB)      :", prof.get("ram_gb"), "| render:", prof.get("render_backend"))
    print("CHOSEN MODE   :", m, "(%s)" % why)
    print("Feature flags :", json.dumps(feature_flags(m), indent=2))
    idx = os.path.abspath(os.path.join(here, "..", "index"))
    print("Page cache    :", cache_stats(idx))
