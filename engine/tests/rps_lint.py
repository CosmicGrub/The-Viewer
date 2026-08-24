#!/usr/bin/env python3
"""THE VIEWER -- RPS (Retroactive Post-Support) lint: the "does legacy still work?" gate.

ES5 engines (IE11 / old Firefox on Win7/Vista) throw a SyntaxError on ES6 *syntax* -- arrow functions,
const/let, template literals, spread/rest, for...of, destructuring, classes. Polyfills (rps.js) add
missing *methods*, but they CANNOT fix syntax. So any ES6 syntax in a page that is supposed to run on
legacy breaks it outright.

This scans engine/ui/*.html (+ *.js) and flags ES6 syntax in **ES5-required** pages. Pages that are
intentionally modern-only (rich graphics: live 3D, WebGL, the loupe, the circuit simulator) are listed
as exempt -- reported for visibility, never failing the gate.

  python rps_lint.py            # exit 1 if an ES5-required page contains ES6 syntax OR any UI file
                                # is UNCLASSIFIED (v1.13.0: unclassified = gate failure, not a report)
  python rps_lint.py --strict   # kept for compatibility (unclassified now always fails the gate)
"""
import os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
UI = os.path.join(os.path.dirname(HERE), "ui")

# Pages/scripts that MUST stay ES5-safe so the legacy build runs them. (Simple, mechanic-facing tools.)
ES5_REQUIRED = {
    "collections.html", "partdiff.html", "procedure.html", "solve.html", "dossier.html",
    "packet.html", "stepflow.html", "ingest.html", "ops.html", "status.html", "help.html",
    "torque.html", "collections.html", "keywords.html", "palette.js", "rps.js", "shared.js", "tagger.js",
    # v0.96.0 (G48): tiered/shared overlays that must run on every build — ES5-clean today, locked.
    "cadview.js", "demo.html", "loupe.js", "partview.js", "schemflow.js", "schemhl.js",
    # v1.5-1.7: injected app-wide by palette.js onto EVERY page (incl. legacy) -> must stay ES5.
    "scanner.js", "readaloud.js",
}
# Intentionally modern-only (rich graphics). Reported for visibility; not a gate failure.
MODERN_BY_DESIGN = {
    "index.html", "schematics.html", "threed.html", "circuitlab.html",
    "gl3d.js", "circuitsim.js", "circuitsim-worker.js",
    # v0.96.0 (G48): WebGL parametric geometry + the CAD-texture dev/test page.
    "partgeo.js", "cadtex_test.html",
    # pre-existing + v1.1-1.11 feature pages (rich fetch/SVG UIs served on the modern build; the legacy
    # build offers the core ES5 tools above). Reported for visibility; not a gate failure.
    "audit.html", "bench.html", "coverage.html", "deepzoom.html", "deepzoom.js", "fastener.html",
    "jobcard.html", "locate.html", "master.html", "mastercov.html", "measures.html", "pmcs.html",
    "decode.html",
    "related.html", "semantic.html", "visual.html",
    "ask.html", "binaudit.html", "command.html", "exploded.html", "learn.html", "part.html",
    "publog.html", "readiness.html", "review.html", "scan.html", "troubleshoot.html", "verify.html",
    # v1.4.0: /kg — a discovery/analysis tool (fetch + free-text query against /api/kg), same class
    # as related.html/semantic.html/ask.html above, not one of the core ES5-required mechanic tools.
    "kg.html",
}

# ES6 syntax patterns that are NOT polyfillable (each would SyntaxError on a true ES5 engine).
PATTERNS = [
    ("arrow function", re.compile(r"=>")),
    ("const declaration", re.compile(r"(?<![\w.])const\s")),
    ("let declaration", re.compile(r"(?<![\w.])let\s")),
    ("template literal", re.compile(r"`")),
    ("for...of", re.compile(r"\bfor\s*\([^)]*\bof\b")),
    ("spread/rest", re.compile(r"\.\.\.")),
    ("class declaration", re.compile(r"(?<![\w.])class\s+[A-Za-z_$]")),
    ("async function", re.compile(r"(?<![\w.])async\s")),
    ("await", re.compile(r"(?<![\w.])await\s")),
]

def _scripts(html):
    """Return inline <script> bodies (skip src= includes). For .js files, the whole text."""
    return re.findall(r"<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>", html, re.S | re.I)

def scan_text(js):
    hits = []
    for label, rx in PATTERNS:
        n = len(rx.findall(js))
        if n: hits.append((label, n))
    return hits

def scan_file(path):
    try:
        txt = open(path, "r", encoding="utf-8", errors="replace").read()
    except Exception as e:
        return [("read error: %s" % e, 1)]
    js = txt if path.endswith(".js") else "\n".join(_scripts(txt))
    return scan_text(js)

def main():
    strict = "--strict" in sys.argv
    if not os.path.isdir(UI):
        print("no ui/ dir at %s" % UI); return 1
    files = sorted(f for f in os.listdir(UI) if f.endswith(".html") or f.endswith(".js"))
    violations = []; modern_with_es6 = []; unclassified = []
    print("RPS lint -- scanning %d UI files in %s" % (len(files), UI))
    print("=" * 60)
    for f in files:
        hits = scan_file(os.path.join(UI, f))
        tag = "ES5-required" if f in ES5_REQUIRED else ("modern" if f in MODERN_BY_DESIGN else "UNCLASSIFIED")
        if f not in ES5_REQUIRED and f not in MODERN_BY_DESIGN:
            unclassified.append(f)
        if hits:
            summ = ", ".join("%s x%d" % (l, n) for l, n in hits)
            if f in ES5_REQUIRED:
                violations.append((f, summ)); print("  [FAIL] %-26s ES6: %s" % (f, summ))
            else:
                modern_with_es6.append(f); print("  [info] %-26s (modern) ES6: %s" % (f, summ))
        else:
            print("  [ ok ] %-26s ES5-clean" % f)
    print("=" * 60)
    rc = 0
    if unclassified:
        # v1.13.0: unclassified files are a GATE FAILURE (previously report-only). An unlisted file
        # silently escapes the ES5 gate, so the legacy build could break with a green lint -- R13
        # forbids that kind of quiet hole. Classify every new UI file when you add it.
        rc = 1
        print("RPS GATE: FAIL -- %d UNCLASSIFIED UI file(s). Every file in engine/ui/ must be declared" % len(unclassified))
        print("in rps_lint.py: add it to ES5_REQUIRED (simple mechanic-facing page that must run on the")
        print("legacy Win7/Vista build) or MODERN_BY_DESIGN (rich graphics / modern-build-only page):")
        for f in unclassified: print("   %s" % f)
    if violations:
        rc = 1
        print("RPS GATE: FAIL -- %d ES5-required page(s) contain ES6 syntax:" % len(violations))
        for f, s in violations: print("   %s -> %s" % (f, s))
    if rc:
        return rc
    print("RPS GATE: PASS -- every ES5-required page is ES5-clean (%d modern-by-design pages noted)."
          % len(modern_with_es6))
    return 0

if __name__ == "__main__":
    sys.exit(main())
