#!/usr/bin/env python3
"""THE VIEWER -- FEATURE AUDIT (v0.99.13). A self-check that runs HOST-side (the sandbox mount truncates grown files,
so audits done in-sandbox lie). It cross-references the live route registry against the UI folder to catch the class of
bug that shipped the command palette dark for weeks: a script that's served but included on no page, a page route with
no file, an orphan page, a broken internal link, or a feature module that no longer imports.

Run:  python audit_features.py       (from engine/)  -> writes docs/feature_audit.txt and exits non-zero on any FAIL.
Read-only. Stdlib only. Additive (R1)."""
import os, re, sys, glob, io, ast

HERE = os.path.dirname(os.path.abspath(__file__))
UI = os.path.join(HERE, "ui")
sys.path.insert(0, HERE)

OUT = []
def emit(s=""): OUT.append(s)
FAILS = [0]; WARNS = [0]
def line(level, msg):
    if level == "FAIL": FAILS[0] += 1
    if level == "WARN": WARNS[0] += 1
    emit("%-4s %s" % (level, msg))

# Known non-page files (test harnesses / partials) that are intentionally not registered as routes.
ORPHAN_ALLOW = {"cadtex_test.html"}
# Assets referenced dynamically or by other assets (not necessarily by an html <script src>).
ASSET_ALLOW = set()


def read(path):
    try:
        return open(path, encoding="utf-8", errors="replace").read()
    except Exception:
        return ""


# ------------------------------------------------------------------------------------------------
# [7] python module reachability (dead-module guard) -- module-level (not nested in main()) so
# test_audit_reachability.py can exercise the closure/BFS logic directly against a synthetic tree,
# not just observe pass/fail text from a full audit run against the live repo. See main()'s [7]
# section below for the rationale/design docstring.
# ------------------------------------------------------------------------------------------------
def reach_local_modules(engine_dir):
    """{module-key -> absolute .py path} for every module the live app could plausibly import:
    top-level engine/*.py, plus the features/ and features/routes/ packages (each package's own
    __init__.py is registered under the BARE package key too, e.g. "features/routes", so a whole-
    package import like `import features.routes` resolves to a real graph node)."""
    mods = {}
    for f in glob.glob(os.path.join(engine_dir, "*.py")):
        mods[os.path.splitext(os.path.basename(f))[0]] = f
    for sub in ("features", os.path.join("features", "routes")):
        d = os.path.join(engine_dir, sub)
        if not os.path.isdir(d):
            continue
        slash = sub.replace(os.sep, "/")
        init = os.path.join(d, "__init__.py")
        if os.path.exists(init):
            mods[slash] = init
        for f in glob.glob(os.path.join(d, "*.py")):
            base = os.path.splitext(os.path.basename(f))[0]
            if base != "__init__":
                mods[slash + "/" + base] = f
    return mods


def reach_imports_of(path):
    """Every name a file imports, anywhere in it -- ast.walk() (not a top-level-only scan)
    deliberately also finds imports nested inside function bodies: several route submodules import
    their heavier dependencies (masterfile, dedup, symbols) lazily inside a handler function, not at
    module top; a shallower walk would false-positive every one of those as unreachable."""
    try:
        tree = ast.parse(read(path), filename=path)
    except SyntaxError:
        return set()
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                names.add(a.name)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            names.add(node.module)
            for a in node.names:
                names.add(node.module + "." + a.name)
    return names


def reach_resolve(name, mods):
    """A raw dotted import name -> the set of registered module keys it could plausibly refer to
    ("masterfile" from "masterfile.build"; "features/routes" from "features.routes"; "features/
    routes/doc_extractors" from "features.routes.doc_extractors")."""
    parts = name.split(".")
    cands = {parts[0], "/".join(parts)}
    if len(parts) >= 2:
        cands.add("/".join(parts[:2]))
    return {c for c in cands if c in mods}


def reach_from(roots, mods):
    """BFS import closure from `roots` (module keys) over `mods`. Returns the set of reachable keys."""
    seen, stack = set(), [r for r in roots if r in mods]
    while stack:
        key = stack.pop()
        if key in seen:
            continue
        seen.add(key)
        for raw in reach_imports_of(mods[key]):
            for resolved in reach_resolve(raw, mods):
                if resolved not in seen:
                    stack.append(resolved)
    return seen


def reach_bat_invoked(repo_root):
    """Module base-names invoked by any root *.bat file ("python build_measures.py" ->
    "build_measures") -- a module launched by its own .bat is a legitimate standalone tool, not an
    orphan. Derived from the .bat files themselves rather than a hand-maintained whitelist, so it
    can't independently drift the way a hand-maintained list would."""
    invoked = set()
    for bat in glob.glob(os.path.join(repo_root, "*.bat")):
        for m in re.finditer(r"([A-Za-z0-9_]+)\.py\b", read(bat)):
            invoked.add(m.group(1))
    return invoked


def main():
    emit("THE VIEWER — feature audit")
    emit("=" * 60)

    # --- load the live registry + route tables --------------------------------------------------
    try:
        import viewer_app  # noqa: F401  triggers features/routes registration
        from features import routes as R
        from features import registry as REG
    except Exception as e:
        line("FAIL", "could not import viewer_app / features (%s)" % e)
        _flush(); return 1

    pages = getattr(R, "_PAGES", {})
    scripts = getattr(R, "_SCRIPTS", {})
    get_routes = set(getattr(REG, "GET", {}).keys())
    post_routes = set(getattr(REG, "POST", {}).keys())
    emit("registry: %d GET · %d POST · %d page-routes · %d served scripts"
         % (len(get_routes), len(post_routes), len(pages), len(scripts)))
    emit("")

    # --- 0. duplicate route paths: two @get/@post on the SAME path silently override in the
    #        {path:handler} registry, leaving one handler dead. The runtime dict hides it, so scan the source.
    emit("[0] duplicate route paths (a dup silently drops one handler)")
    import re as _re
    # v1.14: routes.py split into features/routes/ (per-domain submodules) -- scan every .py file
    # in the package, not one single-file source, or a dup introduced across two submodules (the
    # exact new failure mode the split adds) would go undetected.
    _routes_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "features", "routes")
    _src = "\n".join(read(os.path.join(_routes_dir, _f))
                      for _f in sorted(os.listdir(_routes_dir)) if _f.endswith(".py"))
    _decos = _re.findall(r'@(get|post)\("([^"]+)"\)', _src)   # (method, path) -- GET+POST on one path is legit
    _counts = {}
    for _m, _p in _decos:
        _counts[(_m, _p)] = _counts.get((_m, _p), 0) + 1
    _dups = sorted(k for k, n in _counts.items() if n > 1)
    if _dups:
        for _m, _p in _dups:
            line("FAIL", "%s %s declared %dx -> one handler is DEAD (merge/rename)" % (_m.upper(), _p, _counts[(_m, _p)]))
    else:
        line("PASS", "no duplicate route paths (%d decorators, all unique per method)" % len(_decos))
    emit("")

    # --- 1. every registered page + script file exists ------------------------------------------
    emit("[1] page & script files exist")
    for paths, (fname, _cache) in pages.items():
        p = os.path.join(UI, fname)
        line("PASS" if os.path.exists(p) else "FAIL",
             "page %-22s -> ui/%s%s" % (paths[0], fname, "" if os.path.exists(p) else "  (MISSING)"))
    for route, (fname, _c) in scripts.items():
        p = os.path.join(UI, fname)
        if not os.path.exists(p):
            line("FAIL", "script %-16s -> ui/%s  (MISSING)" % (route, fname))
    emit("")

    # --- 2. dead scripts: served but referenced by no page/asset --------------------------------
    emit("[2] served scripts are actually referenced (dead-feature guard)")
    html_blobs = {os.path.basename(f): read(f) for f in glob.glob(os.path.join(UI, "*.html"))}
    js_blobs = {os.path.basename(f): read(f) for f in glob.glob(os.path.join(UI, "*.js"))}
    for route, (fname, _c) in scripts.items():
        base = fname  # e.g. palette.js
        # match src="/palette.js", src="/palette.js?v=..", importScripts('palette.js'), or the bare filename
        refs_html = [n for n, h in html_blobs.items() if base in h]
        refs_js = [n for n, h in js_blobs.items() if n != base and base in h]
        n = len(refs_html) + len(refs_js)
        if n == 0 and base not in ASSET_ALLOW:
            line("FAIL", "%-20s is SERVED but referenced by NO page or asset (dead)" % base)
        else:
            where = ("%d page%s" % (len(refs_html), "" if len(refs_html) == 1 else "s")) + (", %d asset%s" % (len(refs_js), "" if len(refs_js) == 1 else "s") if refs_js else "")
            line("PASS", "%-20s referenced by %s" % (base, where))
    emit("")

    # --- 3. orphan pages: html that isn't a registered route ------------------------------------
    emit("[3] orphan UI pages (exist but no route)")
    registered = {fname for _paths, (fname, _c) in pages.items()}
    for f in sorted(html_blobs):
        if f not in registered and f not in ORPHAN_ALLOW:
            line("WARN", "ui/%s is not registered in _PAGES (unreachable, or an oversight)" % f)
    emit("")

    # --- 4. broken internal links: href/fetch to routes that don't exist ------------------------
    emit("[4] internal links resolve to a known route")
    known = set()
    for paths, _ in pages.items():
        for p in paths: known.add(p)
    known |= get_routes | post_routes | {r for r in scripts}
    known |= {"/base.css", "/favicon.ico"}
    linkre = re.compile(r'(?:href|action)=["\'](/[a-zA-Z0-9_\-./]*)["\']')
    fetchre = re.compile(r'fetch\(\s*["\'](/[a-zA-Z0-9_\-./]*)')
    unknown = {}
    for name, h in html_blobs.items():
        for m in list(linkre.finditer(h)) + list(fetchre.finditer(h)):
            u = m.group(1).split("?")[0].split("#")[0].rstrip("/")
            if not u:
                u = "/"
            if u in known or (u + ".html") in known or u.startswith("/api/") and u in known:
                continue
            # allow /api/* that exist; allow asset dirs
            if u in known:
                continue
            if u.startswith("/cadimg") or u.startswith("/page") or u.startswith("/thumb") or u.startswith("/pageimg"):
                continue  # image endpoints with dynamic args
            unknown.setdefault(u, set()).add(name)
    # only report app-looking routes (skip obvious dynamic/media)
    real_unknown = {u: v for u, v in unknown.items() if u not in known and not u.startswith("/api/")}
    if not real_unknown:
        line("PASS", "no broken internal page links detected")
    for u in sorted(real_unknown):
        # if it IS an api route present in registry, skip
        if u in get_routes or u in post_routes:
            continue
        line("WARN", "link to %-24s (in %s) has no matching route" % (u, ", ".join(sorted(real_unknown[u]))[:60]))
    emit("")

    # --- 5. feature modules import --------------------------------------------------------------
    emit("[5] feature modules import cleanly")
    for mod in ("search_feature", "parts_feature", "browse_feature", "procedures_feature",
                "render_feature", "ingest_feature", "sessions_feature", "registry", "routes"):
        try:
            __import__("features." + mod); line("PASS", "features.%s" % mod)
        except Exception as e:
            line("FAIL", "features.%s (%s)" % (mod, e))
    for mod in ("jobcard", "figureparts", "partlocate", "figuresheet", "coverage", "doctor",
                "vectorize", "schemreview", "localmodel", "pmcs", "xref", "analytics", "partspdf", "phash", "embed"):
        p = os.path.join(HERE, mod + ".py")
        if not os.path.exists(p):
            continue
        try:
            __import__(mod); line("PASS", "%s" % mod)
        except Exception as e:
            line("FAIL", "%s (%s)" % (mod, e))
    emit("")

    # --- 6. durable-write guard (v1.13): request-serving modules must persist sidecars via
    #        safeguard.atomic_write (fsync + _replace_retry), NOT a bare os.replace / open(...,"w"),
    #        which 500s on the transient Windows lock and can leak a .tmp or lose the file.
    emit("[6] sidecar writers use safeguard.atomic_write (durable-write guard)")
    _serving = ("sides_feature", "chapters_feature", "rpstl_feature", "xref_online",
                "collections_feature", "features/search_feature", "features/routes")
    _bad = 0
    for _mod in _serving:
        _pth = os.path.join(HERE, _mod.replace("/", os.sep) + ".py")
        # v1.14: features/routes.py split into the features/routes/ package -- fall back to
        # scanning every submodule .py file when the single-file path no longer exists.
        if os.path.isdir(os.path.join(HERE, _mod.replace("/", os.sep))):
            _dir = os.path.join(HERE, _mod.replace("/", os.sep))
            _txt = "\n".join(read(os.path.join(_dir, _f)) for _f in sorted(os.listdir(_dir)) if _f.endswith(".py"))
        elif os.path.exists(_pth):
            _txt = read(_pth)
        else:
            continue
        # a raw os.replace( that is NOT part of safeguard's own implementation is a durability risk
        if _re.search(r"\bos\.replace\(", _txt):
            line("WARN", "%s.py has a raw os.replace() -- route it through safeguard.atomic_write" % _mod); _bad += 1
    if not _bad:
        line("PASS", "no raw os.replace() in request-serving modules (all durable via safeguard)")
    emit("")

    # --- 7. python module reachability (dead-module guard) ---------------------------------------
    # Recommendations annex #15 (architecture-reachability): the recurring "built + self-tested but
    # never called from production" bug class (measures.py, schemgraph.py, RPSTL, pagetrim, dedup.py,
    # symbols.py, tables_plus.stitch(), Office formats, build_keywords -- all found orphaned at some
    # point) had NO mechanical defense: SELFTEST_MODULES tracks "has a self-test", never "is reachable
    # from production" -- proven by every one of those modules already being on that list when found
    # orphaned. This extends [2]'s dead-JS-script pattern to Python: an AST import-closure walk rooted
    # at the two real entry points (viewer_app.py for routes, viewer_ingest.py for the pipeline),
    # cross-checked against verifystate.SELFTEST_MODULES (imported, not re-listed, so this can't drift
    # from that roster the way SELFTEST_MODULES itself once drifted from VERIFY.bat).
    #
    # ast.walk() (not a top-level-only scan) deliberately also finds imports nested inside function
    # bodies -- several route submodules import their heavier dependencies (masterfile, dedup, symbols)
    # lazily inside a handler function, not at module top; a shallower walk would false-positive every
    # one of those as unreachable.
    #
    # WARN-only, not FAIL: a static import walk cannot see a genuinely dynamic
    # importlib.import_module(some_variable) call, and this is a first pass against the live 65-module
    # roster, not yet proven to zero false positives -- exactly the same caution [3]/[4] (orphan pages,
    # broken links) already apply below WARN rather than FAIL for the same reason.
    emit("[7] python module reachability from viewer_app/viewer_ingest (dead-module guard)")

    _mods = reach_local_modules(HERE)
    _reachable = reach_from(("viewer_app", "viewer_ingest"), _mods)
    _bat_invoked = reach_bat_invoked(os.path.join(HERE, ".."))
    try:
        from verifystate import SELFTEST_MODULES as _selftest_mods
    except Exception as e:
        _selftest_mods = []
        line("WARN", "could not import verifystate.SELFTEST_MODULES (%s) -- skipping [7]" % e)
    _flagged = 0
    for _mod in _selftest_mods:
        _base = _mod.split("/")[-1]
        if _mod in _reachable:
            line("PASS", "%-26s reachable from viewer_app/viewer_ingest" % _mod)
        elif _base in _bat_invoked or _base.startswith("build_"):
            line("PASS", "%-26s self-tested, standalone tool (invoked by a .bat)" % _mod)
        else:
            _flagged += 1
            line("WARN", "%-26s self-tested but UNREACHABLE from viewer_app/viewer_ingest and no "
                          ".bat invokes it -- verify it's actually wired in (or this checker has a "
                          "blind spot: dynamic import, indirect registration, etc.)" % _mod)
    emit("checked %d self-tested modules for production reachability -- %d flagged" % (len(_selftest_mods), _flagged))
    emit("")

    # --- summary --------------------------------------------------------------------------------
    emit("=" * 60)
    emit("SUMMARY: %d FAIL · %d WARN" % (FAILS[0], WARNS[0]))
    emit("A clean audit = 0 FAIL. WARNs are advisory (orphan test pages, dynamic links, unreachable modules).")
    _flush()
    return 1 if FAILS[0] else 0


def _flush():
    txt = "\n".join(OUT)
    print(txt)
    docs = os.path.join(HERE, "..", "docs")
    try:
        open(os.path.join(docs, "feature_audit.txt"), "w", encoding="utf-8").write(txt + "\n")
    except Exception:
        pass


if __name__ == "__main__":
    sys.exit(main())
