"""verifystate.py -- the VERIFICATION COCKPIT's data (R13: make the proof state visible). It answers, at a
glance, 'what have we actually verified?' by reading the last host-side VERIFY-099 log, listing the modules
that carry self-tests, and reporting which data sidecars are built. Verification you can't see is
verification you won't keep green.

Read-only. Pure stdlib. parse_verify_log() is unit-testable on a captured log string."""

from __future__ import annotations
import os, re, time

# modules that ship a self-test (kept in step with root VERIFY.bat's gate-6 self-test loop, the
# authoritative module list since v1.13.0 -- VERIFY-099.bat is now just a forwarder to it).
# v1.13.6 (low-tier review-fix, aad1709's own review): this roster had drifted to 38 of the 65
# modules VERIFY.bat's gate 6 actually self-tests -- undercounting n_modules on the live
# /api/verifystate "verification cockpit" route by ~40%. The drift predated the crossval removal
# (which only ever touched the one now-dead entry); rebuilt here as the true subset match against
# VERIFY.bat line 129's %%M list.
SELFTEST_MODULES = [
    "analytics", "xref", "phash", "embed", "measures", "tables", "enrich", "masterfile", "units",
    "leadingspecs", "specparse", "pdfmeta", "barcodes", "cautions", "textquality", "acronyms", "pagetrim",
    "tables_plus", "ietm", "kg", "dimscan", "ocrprep", "layout", "dedup", "callouts", "symbols", "vlm",
    "specsheet", "qrgen", "publog", "hybrid", "publogdiff", "dimscad", "conflicts", "faulttree", "ask",
    "jobpack", "validate", "trust", "integrity", "signoff", "tmrev", "verifystate", "serviceability",
    "torqueseq", "bom", "pinouts", "training", "fieldnotes", "crossmethod", "rpstl", "intervals",
    "fluidsmatrix", "commonality", "handover", "forms", "ingestpipe", "airgap", "standards", "nsndecode",
    "smrdecode", "cage", "harnesstrace", "macchart", "features/corpus",
]

_PASS = re.compile(r"\[([^\]]*?)\s+PASS\]|\b([a-z_]+) self-test (?:OK|PASS)\b|\bpy parse OK\b", re.I)
# v1.13.4: root VERIFY.bat (the gate since v1.13.0 -- VERIFY-099.bat now just forwards to it) prints its
# per-assertion results as bare "PASS <name>" lines (tests/test_pillars.py etc.), not the old "[name PASS]"
# bracket form or "<module> self-test PASS" phrasing above. Without this, parse_verify_log() silently
# undercounted -- it still caught real FAILs (generic enough), but severely undercounted passes on today's
# actual log format, on the one page whose whole job is showing the true proof state.
_PASS_BARE = re.compile(r"^PASS\s+(\S.*)$")
_FAIL = re.compile(r"\bFAIL\b|Traceback|AssertionError|Error:", re.I)


def parse_verify_log(text):
    """Parse a VERIFY.bat (or legacy VERIFY-099) log -> {passes list, failed bool, n_pass, n_fail_lines}.
    Best-effort."""
    if not text:
        return {"passes": [], "failed": None, "n_pass": 0, "n_fail_lines": 0}
    passes, fails = [], 0
    for ln in text.splitlines():
        stripped = ln.strip()
        # v1.13.4: an explicit "PASS <name>" label is authoritative -- don't let a generic "Error:"/"FAIL"
        # substring elsewhere on the SAME line override it. Confirmed live: test_truncation.py's own PASS
        # message legitimately quotes the error string it just verified recovery from ("PASS DB corruption
        # detected (ERROR: file is not a database) + recovered (ok)"), which the old naive check flagged as
        # a failure -- a real GREEN run (0 FAIL, confirmed host-side) would have shown as failed=True.
        is_explicit_pass = bool(_PASS_BARE.match(stripped))
        if not is_explicit_pass and _FAIL.search(ln) and "0 FAIL" not in ln and "FAIL]" not in ln:
            # 'audit 0 FAIL' is a pass phrasing; a bare FAIL / traceback is a real failure
            if not re.search(r"\b0\s+FAIL", ln):
                fails += 1
        m = _PASS.search(ln)
        if m:
            label = next((g for g in m.groups() if g), "parse")
            passes.append(label.strip())
        elif is_explicit_pass:
            passes.append(_PASS_BARE.match(stripped).group(1).strip())
    return {"passes": passes, "failed": fails > 0, "n_pass": len(passes), "n_fail_lines": fails}


def _sidecars(db_path):
    d = os.path.dirname(db_path)
    def has(name):
        p = os.path.join(d, name)
        return {"built": os.path.exists(p) and os.path.getsize(p) > 0,
                "mb": round(os.path.getsize(p) / 1e6, 1) if os.path.exists(p) else 0}
    return {"index/viewer.db": has(os.path.basename(db_path)), "publog.db": has("publog.db"),
            "masterfile.db": has("masterfile.db"), "measures.db": has("measures.db"),
            "tables.db": has("tables.db"), "enrich.db": has("enrich.db"), "kg.db": has("kg.db"),
            "signoff.db": has("signoff.db")}


def snapshot(db_path, docs_dir=None):
    """Full cockpit snapshot: last verify result, module self-test roster, sidecar build state."""
    docs_dir = docs_dir or os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs")
    # v1.13.4: root VERIFY.bat (the authoritative gate since v1.13.0) writes docs/verify.log; the legacy
    # VERIFY-099.bat name (now just a forwarder) is kept as a fallback so an old captured log still shows.
    # Prefer whichever is NEWER if both exist -- an old verify.log left over from before a legacy run
    # shouldn't shadow a more recent VERIFY-099 log, or vice versa.
    candidates = [os.path.join(docs_dir, "verify.log"), os.path.join(docs_dir, "verify_099.log")]
    existing = [p for p in candidates if os.path.exists(p)]
    log_path = max(existing, key=os.path.getmtime) if existing else candidates[0]
    verify = {"present": False}
    if os.path.exists(log_path):
        try:
            txt = open(log_path, "r", encoding="utf-8", errors="replace").read()
            verify = parse_verify_log(txt)
            verify["present"] = True
            verify["ran"] = time.strftime("%Y-%m-%d %H:%M", time.localtime(os.path.getmtime(log_path)))
            verify["source"] = os.path.basename(log_path)
        except Exception as e:
            verify = {"present": False, "error": str(e)}
    return {"modules": SELFTEST_MODULES, "n_modules": len(SELFTEST_MODULES),
            "sidecars": _sidecars(db_path), "last_verify": verify,
            "note": "Run root VERIFY.bat host-side to refresh the proof state."}


# --------------------------------------------------------------------------- #
# self-test: `python verifystate.py`                                          #
# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    log = ("=== v1.7 verification ===\n"
           "py parse OK\n"
           "--- feature audit ---\n"
           "audit: 0 FAIL 0 WARN\n"
           "validate self-test PASS\n"
           "[test_features PASS]\n"
           "[test_routes PASS]\n"
           "integrity self-test PASS\n")
    p = parse_verify_log(log)
    assert p["failed"] is False, p
    assert p["n_pass"] >= 5, p
    assert "test_features" in p["passes"], p
    print("parse_verify_log OK -> %d passes, failed=%s" % (p["n_pass"], p["failed"]))

    bad = parse_verify_log("running...\nAssertionError: boom\n")
    assert bad["failed"] is True, bad
    print("parse detects failure OK")

    assert len(SELFTEST_MODULES) >= 60 and "validate" in SELFTEST_MODULES and "publogdiff" in SELFTEST_MODULES
    print("module roster OK -> %d self-tested modules" % len(SELFTEST_MODULES))

    # v1.13.6: cross-check SELFTEST_MODULES against root VERIFY.bat's actual gate-6 %%M list, the
    # true source of truth -- a hand-maintained list that can only ever be checked against itself
    # (the old ">= 35" floor) drifts silently forever. Best-effort: skip quietly if VERIFY.bat's
    # layout ever changes shape rather than false-failing this module's own self-test on that.
    _verify_bat = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "VERIFY.bat")
    if os.path.exists(_verify_bat):
        _txt = open(_verify_bat, "r", encoding="utf-8", errors="replace").read()
        _m = re.search(r"for %%M in \(([^)]+)\) do", _txt)
        if _m:
            _bat_mods = set(t[:-3] if t.lower().endswith(".py") else t
                            for t in (_m.group(1).replace("\\", "/").split()))
            _ours = set(SELFTEST_MODULES)
            _missing = _bat_mods - _ours
            assert not _missing, ("SELFTEST_MODULES has drifted behind VERIFY.bat gate 6 -- missing: %s" % sorted(_missing))
            print("module roster matches VERIFY.bat gate 6 (%d modules) OK" % len(_bat_mods))
    print("verifystate self-test PASS")

# END OF FILE
