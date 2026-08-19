#!/usr/bin/env python3
"""THE VIEWER -- central registry for the extraction-pipeline opt-out toggles (the VIEWER_*_SCAN
family + VIEWER_OCR_PREPROCESS). Every one of these gates exactly one stage of viewer_ingest.py's
crawl()/ocr()/run pipeline (barcode read, dimensional-data extraction, schematic detection, table
extraction, RPSTL parts-list rows, keywords.json refresh, OCR preprocessing), all follow the SAME
convention (env var unset or anything but "0" -> the stage runs; "0" -> the stage is skipped), and
all default ON.

Why this exists: a full-codebase audit (see docs/SYSTEM-REQUIREMENTS.md's "Extraction pipeline
stages" section) found that every one of these toggles had been declared inline, at its own
os.environ.get() call site, with no shared list anywhere -- which is exactly how 7 of the 8 in this
family shipped with ZERO mention in the docs, across several separate features added over time
(the doc gap wasn't a one-time oversight, it was the natural consequence of there being no single
place a new toggle had to register itself). Declaring through scan_toggle() instead doesn't change
runtime behavior at all -- same env var, same default, same resolved bool assigned to the same
module-level name every existing caller already references. The registry is a side effect, purely
for introspection: this gives `python viewer_ingest.py flags` and the in-app ingest UI's breakdown
panel one place to ask "what's on/off right now" instead of either one hardcoding the list a second
time.

LIVE, not a snapshot: each registry entry remembers WHERE its resolved value lives (the declaring
module's own namespace + attribute name), and re-reads it fresh on every disabled()/report() call --
it does NOT cache the boolean computed at registration time. This matters because viewer_ingest.py's
own tests (and any future in-process caller) monkeypatch these toggles directly as plain module
attributes, e.g. `viewer_ingest.RPSTL_SCAN = False`, entirely bypassing the environment variable --
a snapshot taken once at import time would silently go stale the moment that happened, which is
exactly the class of drift this whole module exists to eliminate (see the doc-gap paragraph above).
Reading live guarantees flags.disabled() always agrees with what the pipeline will actually do
(`if not RPSTL_SCAN: return 0`), regardless of whether the value came from the env var at import or
a later direct assignment.

Deliberately scoped to JUST this one family of flags (extraction-stage opt-outs living in
viewer_ingest.py) -- not a general config system for the ~25 OTHER VIEWER_* environment variables
(security/exposure, server/runtime, OCR tuning, preflight, optional backends), which already have a
single well-documented home in docs/SYSTEM-REQUIREMENTS.md and live in the files that actually use
them (viewer_app.py, preflight.py, sysprobe.py, etc.) -- those aren't broken, so this doesn't touch
them. Pure stdlib. Read-only: this module never writes anything, and importing it has no side
effects beyond the registry list growing as each toggle-declaring module (today, just
viewer_ingest.py) is itself imported."""
import os

_REGISTRY = []   # append-only, one entry per scan_toggle() call, in declaration order


def scan_toggle(env, stage, note, attr, ns, module="viewer_ingest.py"):
    """Resolve + register one opt-out extraction-stage toggle: unset or anything but "0" -> True
    (stage runs); "0" -> False (stage skipped) -- the exact semantics every VIEWER_*_SCAN toggle
    already used before this module existed. Returns the resolved bool; assign it directly to the
    module-level name callers reference, e.g. (from inside viewer_ingest.py):
        RPSTL_SCAN = flags.scan_toggle("VIEWER_RPSTL_SCAN", "rpstl",
                                        "RPSTL parts-list row extraction (rpstl_feature.parse_page())",
                                        attr="RPSTL_SCAN", ns=globals())
    `attr`+`ns` are what make this LIVE (see module docstring): `ns` is the declaring module's own
    `globals()` dict (a live reference, not a copy -- a later `viewer_ingest.RPSTL_SCAN = False`
    mutates this exact same dict), `attr` is the module-level name the resolved value was assigned
    to. disabled()/report() re-read `ns[attr]` fresh every call instead of trusting the bool
    computed here at registration time.
    `stage` is the short label used in the ingest UI's breakdown panel and progress JSON (e.g.
    "rpstl", "schematics") -- keep it matching the `stage=` string _write_progress() uses for that
    pipeline stage where one exists. `note` is a one-line, human-readable description for `flags.py`'s
    own report() and docs/SYSTEM-REQUIREMENTS.md (keep them in sync when either changes)."""
    raw = os.environ.get(env)
    value = raw != "0"
    _REGISTRY.append({"env": env, "stage": stage, "module": module, "note": note,
                       "default": True, "raw": raw, "attr": attr, "ns": ns})
    return value


def _live_value(entry):
    """The toggle's CURRENT effective value, re-read from its owning module's namespace -- see the
    module docstring for why this isn't just the bool computed at registration time. Fails safe to
    the env-var-resolved default if the namespace lookup ever breaks (attr renamed, ns is None from
    a hand-built test entry, etc.) -- introspection must never raise."""
    try:
        return bool(entry["ns"][entry["attr"]])
    except Exception:
        return entry["raw"] != "0"


def all_toggles():
    """A copy of every toggle registered so far, in declaration order, each entry's current LIVE
    value included as `value`. Only meaningful once the module(s) that declare them have actually
    been imported -- registration happens at import time, same as every other module-level constant
    in this codebase (there is nothing to call to 'load' the registry; importing viewer_ingest.py
    IS what populates it)."""
    return [dict(t, value=_live_value(t)) for t in _REGISTRY]


def disabled():
    """Just the toggles currently resolved OFF (live, see module docstring) -- what
    _write_progress()'s `flags_off` field and the ingest UI's breakdown-panel indicator both want."""
    return [t for t in all_toggles() if not t["value"]]


def disabled_stage_names():
    """Just the `stage` labels of whatever's OFF, e.g. ["schematics", "rpstl"] -- the exact shape
    ingest_progress.json's `flags_off` field carries (JSON-serializable, no need for the caller to
    know this module's internal dict shape)."""
    return [t["stage"] for t in disabled()]


def report():
    """Human-readable one-line-per-toggle report for `python viewer_ingest.py flags`. Returns the
    text (the CLI subcommand prints it; tests can inspect the string directly without capturing
    stdout)."""
    if not _REGISTRY:
        return ("THE VIEWER -- extraction pipeline toggles\n" + "=" * 60 +
                "\n(none registered yet -- import viewer_ingest.py first)")
    toggles = all_toggles()
    lines = ["THE VIEWER -- extraction pipeline toggles", "=" * 60]
    for t in toggles:
        state = "ON " if t["value"] else "OFF"
        lines.append("[%s] %-24s (stage: %-11s in %s)" % (state, t["env"], t["stage"], t["module"]))
        lines.append("      %s" % t["note"])
    lines.append("=" * 60)
    off = [t for t in toggles if not t["value"]]
    n_on = len(toggles) - len(off)
    lines.append("%d of %d toggles active%s" % (n_on, len(toggles), "" if not off else
                  "  -- OFF: " + ", ".join(t["env"] for t in off)))
    return "\n".join(lines)


if __name__ == "__main__":
    # A bare `python flags.py` registers nothing on its own (this module declares no toggles
    # itself -- viewer_ingest.py does, at import time) -- `python viewer_ingest.py flags` is the
    # real entry point. This just proves the module loads and an empty report reads sensibly.
    print(report())

# END OF FILE
