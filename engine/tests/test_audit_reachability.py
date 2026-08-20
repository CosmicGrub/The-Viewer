#!/usr/bin/env python3
"""Regression coverage for audit_features.py's reachability-closure checker (recommendations annex
#15: architecture-reachability). Builds a synthetic 3-module tree -- one genuinely imported by a fake
viewer_app.py, one invoked only via a fake .bat, one truly orphaned -- and proves the checker flags
EXACTLY the orphan, not the other two, and not vacuously (i.e. it isn't just returning "everything
unreachable" or "everything reachable"). Also proves the real, live audit_features.py run against
THIS repo currently reports zero flagged modules, so a future regression here is caught immediately.
Pure stdlib test runner."""
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ENGINE = os.path.dirname(HERE)
sys.path.insert(0, ENGINE)
import audit_features as AF


def _write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, "w", encoding="utf-8").write(text)


def run():
    passed, failed = [], []

    def check(name, cond):
        (passed if cond else failed).append(name)

    d = tempfile.mkdtemp(prefix="audit_reachability_")

    # viewer_app.py imports "wired_module" directly, and also imports the "features.routes" PACKAGE
    # whole -- exercising the __init__.py package-node resolution, not just a flat top-level import.
    _write(os.path.join(d, "viewer_app.py"),
           "import wired_module\nimport features.routes\n")
    _write(os.path.join(d, "viewer_ingest.py"), "# pipeline driver, imports nothing extra here\n")
    _write(os.path.join(d, "wired_module.py"), "X = 1\n")

    # features/routes/__init__.py re-exports a submodule, which in turn LAZILY imports a deeper
    # module inside a function body -- the exact real-world shape doc_extractors.py uses for
    # masterfile/dedup/symbols, and the reason the checker uses ast.walk() not a top-level-only scan.
    _write(os.path.join(d, "features", "__init__.py"), "")
    _write(os.path.join(d, "features", "routes", "__init__.py"),
           "from features.routes import doc_stuff\n")
    _write(os.path.join(d, "features", "routes", "doc_stuff.py"),
           "def handler():\n    import lazily_wired_module\n    return lazily_wired_module.Y\n")
    _write(os.path.join(d, "lazily_wired_module.py"), "Y = 2\n")

    # a module invoked only by its own .bat -- a legitimate standalone tool, not an orphan
    _write(os.path.join(d, "build_something.py"), "print('standalone build tool')\n")
    _write(os.path.join(d, "BUILD-SOMETHING.bat"), "python build_something.py\n")

    # a module with a self-test that NOTHING calls -- the real bug class this checker exists to catch
    _write(os.path.join(d, "truly_orphaned_module.py"), "Z = 3\n")

    mods = AF.reach_local_modules(d)
    check("synthetic tree registered all expected module keys",
          {"viewer_app", "viewer_ingest", "wired_module", "features/routes",
           "features/routes/doc_stuff", "lazily_wired_module", "build_something",
           "truly_orphaned_module"} <= set(mods))

    reachable = AF.reach_from(("viewer_app", "viewer_ingest"), mods)
    check("the directly-imported module is reachable", "wired_module" in reachable)
    check("the package __init__.py node itself is reachable (whole-package import resolved)",
          "features/routes" in reachable)
    check("a submodule reached only via the package's __init__.py is reachable",
          "features/routes/doc_stuff" in reachable)
    check("a module imported lazily inside a function body is still reachable (ast.walk, not a "
          "top-level-only scan)", "lazily_wired_module" in reachable)
    check("the standalone build tool is NOT import-reachable (it's legitimate via .bat, not imports)",
          "build_something" not in reachable)
    check("the truly orphaned module is NOT reachable", "truly_orphaned_module" not in reachable)

    bat_invoked = AF.reach_bat_invoked(d)
    check("the .bat-invoked module is correctly detected", "build_something" in bat_invoked)
    check("the truly orphaned module is NOT .bat-invoked", "truly_orphaned_module" not in bat_invoked)

    # ---- end-to-end: replay exactly the same classification main()'s [7] section applies ----------
    fake_selftest_roster = ["wired_module", "lazily_wired_module", "build_something",
                             "truly_orphaned_module"]
    flagged = []
    for mod in fake_selftest_roster:
        base = mod.split("/")[-1]
        if mod in reachable:
            continue
        if base in bat_invoked or base.startswith("build_"):
            continue
        flagged.append(mod)
    check("the classifier flags EXACTLY the truly orphaned module -- not the wired ones, not the "
          "bat-invoked one, and not vacuously empty/everything",
          flagged == ["truly_orphaned_module"])

    # ---- sanity: the checker isn't vacuous (doesn't just always say "reachable" or "unreachable") --
    check("reach_from() is not vacuously empty", len(reachable) > 0)
    check("reach_from() is not vacuously everything (the orphan and the build tool are excluded)",
          len(reachable) < len(mods))

    # ---- the real, live repo currently has zero flagged modules -- lock this in as a regression ---
    # guard, and prove the checker's OWN plumbing (verifystate import, roots resolving, etc.) works
    # against the real 65+-module roster, not just the synthetic fixture above.
    real_mods = AF.reach_local_modules(ENGINE)
    real_reachable = AF.reach_from(("viewer_app", "viewer_ingest"), real_mods)
    real_bat_invoked = AF.reach_bat_invoked(os.path.join(ENGINE, ".."))
    sys.path.insert(0, ENGINE)
    import verifystate
    real_flagged = []
    for mod in verifystate.SELFTEST_MODULES:
        base = mod.split("/")[-1]
        if mod in real_reachable or base in real_bat_invoked or base.startswith("build_"):
            continue
        real_flagged.append(mod)
    check("the live repo's roots (viewer_app/viewer_ingest) resolve to real files",
          "viewer_app" in real_mods and "viewer_ingest" in real_mods)
    check("the live repo currently has zero unreachable self-tested modules (%s)" % real_flagged,
          real_flagged == [])

    return passed, failed


if __name__ == "__main__":
    p, f = run()
    for n in p:
        print("PASS", n)
    for n in f:
        print("FAIL", n)
    print("\n%d passed, %d failed" % (len(p), len(f)))
    sys.exit(1 if f else 0)

# END OF FILE
