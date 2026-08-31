#!/usr/bin/env python3
"""THE VIEWER -- static pages + scripts (was ~30 separate if-blocks; moved verbatim out of the
former monolithic engine/features/routes.py at the v1.14 routes/ split). No `core` dependency --
these handlers only ever read files under ui/."""
import os

ENGINE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
UI_DIR = os.path.join(ENGINE_DIR, "ui")


_PAGES = {  # route(+aliases) -> ui file
    ("/", "/index.html"): ("index.html", None),
    ("/ops", "/ops.html"): ("ops.html", None),
    ("/ingest", "/ingest.html"): ("ingest.html", None),
    ("/status",): ("status.html", None),
    ("/3d", "/3d.html"): ("threed.html", "no-cache"),
    ("/demo", "/demo.html", "/onboarding"): ("demo.html", "no-cache"),
    ("/circuitlab", "/circuitlab.html"): ("circuitlab.html", None),
    ("/keywords", "/keywords.html"): ("keywords.html", None),
    ("/schematics", "/schematics.html"): ("schematics.html", None),
    ("/collections", "/collections.html"): ("collections.html", None),
    ("/partdiff", "/partdiff.html"): ("partdiff.html", None),
    ("/procedure", "/procedure.html"): ("procedure.html", None),
    ("/solve", "/solve.html"): ("solve.html", None),
    ("/packet", "/packet.html"): ("packet.html", None),
    ("/dossier", "/dossier.html"): ("dossier.html", None),
    ("/stepflow", "/stepflow.html"): ("stepflow.html", None),
    ("/help", "/help.html"): ("help.html", None),
    ("/deepzoom", "/deepzoom.html"): ("deepzoom.html", "no-cache"),
    ("/coverage", "/coverage.html"): ("coverage.html", "no-cache"),
    ("/locate", "/locate.html"): ("locate.html", "no-cache"),
    ("/jobcard", "/jobcard.html"): ("jobcard.html", "no-cache"),
    ("/handover", "/handover.html"): ("handover.html", "no-cache"),  # v1.31 (gap-sweep item 4): handover.py had zero UI callers
    ("/torque", "/torque.html"): ("torque.html", "no-cache"),
    ("/decode", "/decode.html", "/reference-codes"): ("decode.html", "no-cache"),
    ("/bench", "/bench.html"): ("bench.html", "no-cache"),
    ("/fastener", "/fastener.html"): ("fastener.html", "no-cache"),
    ("/pmcs", "/pmcs.html"): ("pmcs.html", "no-cache"),
    ("/semantic", "/semantic.html"): ("semantic.html", "no-cache"),
    ("/related", "/related.html"): ("related.html", "no-cache"),
    ("/visual", "/visual.html"): ("visual.html", "no-cache"),
    ("/measures", "/measures.html"): ("measures.html", "no-cache"),
    ("/master", "/master.html"): ("master.html", "no-cache"),
    ("/mastercov", "/mastercov.html"): ("mastercov.html", "no-cache"),
    ("/audit", "/audit.html"): ("audit.html", "no-cache"),
    ("/publog", "/publog.html"): ("publog.html", "no-cache"),
    ("/scan", "/scan.html"): ("scan.html", "no-cache"),
    ("/exploded", "/exploded.html", "/assembly"): ("exploded.html", "no-cache"),
    ("/binaudit", "/binaudit.html"): ("binaudit.html", "no-cache"),
    ("/part", "/part.html"): ("part.html", "no-cache"),
    ("/troubleshoot", "/troubleshoot.html", "/faulttree"): ("troubleshoot.html", "no-cache"),
    ("/ask", "/ask.html"): ("ask.html", "no-cache"),
    ("/command", "/command.html"): ("command.html", "no-cache"),
    ("/verify", "/verify.html"): ("verify.html", "no-cache"),
    ("/review", "/review.html", "/signoff"): ("review.html", "no-cache"),
    ("/learn", "/learn.html", "/quiz"): ("learn.html", "no-cache"),
    ("/readiness", "/readiness.html", "/fluids"): ("readiness.html", "no-cache"),
    ("/kg", "/kg.html"): ("kg.html", "no-cache"),
}

_SCRIPTS = {  # route -> (ui file, Cache-Control)
    "/tagger.js": ("tagger.js", "max-age=3600"),
    "/partgeo.js": ("partgeo.js", "no-cache"),
    "/partview.js": ("partview.js", "no-cache"),
    "/cadview.js": ("cadview.js", "max-age=3600"),
    "/loupe.js": ("loupe.js", "no-cache"),
    "/schemhl.js": ("schemhl.js", "max-age=3600"),
    "/schemflow.js": ("schemflow.js", "max-age=3600"),
    "/gl3d.js": ("gl3d.js", "no-cache"),
    "/circuitsim.js": ("circuitsim.js", "max-age=3600"),
    "/circuitsim-worker.js": ("circuitsim-worker.js", "max-age=3600"),
    "/rps.js": ("rps.js", "max-age=600"),
    "/palette.js": ("palette.js", "max-age=600"),
    "/shared.js": ("shared.js", "max-age=600"),       # v0.96.0 (A2): the one copy of the page helpers
    "/deepzoom.js": ("deepzoom.js", "max-age=3600"),  # v0.99.3: offline deep-zoom + callout hotspots
    "/scanner.js": ("scanner.js", "max-age=600"),     # v1.5: global hand-scanner (keyboard-wedge) listener
    "/readaloud.js": ("readaloud.js", "max-age=600"), # v1.7: offline read-aloud (TTS) + voice input
}


def _serve_ui(h, fname, ctype, cache=None):
    try:
        body = open(os.path.join(UI_DIR, fname), "r", encoding="utf-8").read()
    except FileNotFoundError:
        h._send(404, fname + " not found"); return
    extra = {"Cache-Control": cache} if cache else None
    h._send(200, body, ctype, extra)


def _mk_page(fname, cache):
    def handler(h, qs):
        _serve_ui(h, fname, "text/html; charset=utf-8", cache)
    return handler


def _mk_script(fname, cache):
    def handler(h, qs):
        _serve_ui(h, fname, "application/javascript; charset=utf-8", cache)
    return handler


def register_static():
    from features import registry
    for paths, (fname, cache) in _PAGES.items():
        fn = _mk_page(fname, cache)
        for p in paths:
            registry.GET[p] = fn
    for p, (fname, cache) in _SCRIPTS.items():
        registry.GET[p] = _mk_script(fname, cache)
    registry.GET["/base.css"] = lambda h, qs: _serve_ui(h, "base.css", "text/css; charset=utf-8", "max-age=600")


register_static()
