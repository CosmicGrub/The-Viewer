"""verifystate.py -- the VERIFICATION COCKPIT's data (R13: make the proof state visible). It answers, at a
glance, 'what have we actually verified?' by reading the last host-side VERIFY-099 log, listing the modules
that carry self-tests, and reporting which data sidecars are built. Verification you can't see is
verification you won't keep green.

Read-only. Pure stdlib. parse_verify_log() is unit-testable on a captured log string."""

from __future__ import annotations
import os, re, time

# modules that ship a self-test (kept in step with VERIFY-099.bat)
SELFTEST_MODULES = [
    "measures", "tables", "enrich", "masterfile", "units", "leadingspecs", "specparse", "pdfmeta", "barcodes",
    "cautions", "textquality", "acronyms", "pagetrim", "tables_plus", "ietm", "kg", "dimscan", "ocrprep",
    "layout", "dedup", "crossval", "callouts", "symbols", "vlm", "specsheet", "qrgen", "publog", "hybrid",
    "publogdiff", "dimscad", "conflicts", "faulttree", "ask", "jobpack",
    "validate", "trust", "integrity", "signoff", "tmrev",
]

_PASS = re.compile(r"\[([^\]]*?)\s+PASS\]|\b([a-z_]+) self-test (?:OK|PASS)\b|\bpy parse OK\b", re.I)
_FAIL = re.compile(r"\bFAIL\b|Traceback|AssertionError|Error:", re.I)


def parse_verify_log(text):
    """Parse a VERIFY-099 log -> {passes list, failed bool, n_pass, n_fail_lines}. Best-effort."""
    if not text:
        return {"passes": [], "failed": None, "n_pass": 0, "n_fail_lines": 0}
    passes, fails = [], 0
    for ln in text.splitlines():
        if _FAIL.search(ln) and "0 FAIL" not in ln and "FAIL]" not in ln:
            # 'audit 0 FAIL' is a pass phrasing; a bare FAIL / traceback is a real failure
            if not re.search(r"\b0\s+FAIL", ln):
                fails += 1
        m = _PASS.search(ln)
        if m:
            label = next((g for g in m.groups() if g), "parse")
            passes.append(label.strip())
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
    log_path = os.path.join(docs_dir, "verify_099.log")
    verify = {"present": False}
    if os.path.exists(log_path):
        try:
            txt = open(log_path, "r", encoding="utf-8", errors="replace").read()
            verify = parse_verify_log(txt)
            verify["present"] = True
            verify["ran"] = time.strftime("%Y-%m-%d %H:%M", time.localtime(os.path.getmtime(log_path)))
        except Exception as e:
            verify = {"present": False, "error": str(e)}
    return {"modules": SELFTEST_MODULES, "n_modules": len(SELFTEST_MODULES),
            "sidecars": _sidecars(db_path), "last_verify": verify,
            "note": "Run VERIFY-099.bat host-side to refresh the proof state."}


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

    assert len(SELFTEST_MODULES) >= 35 and "validate" in SELFTEST_MODULES and "publogdiff" in SELFTEST_MODULES
    print("module roster OK -> %d self-tested modules" % len(SELFTEST_MODULES))
    print("verifystate self-test PASS")

# END OF FILE
