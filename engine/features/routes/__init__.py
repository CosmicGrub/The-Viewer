#!/usr/bin/env python3
"""THE VIEWER -- every HTTP route, declared here (backlog A5/A7, v0.96.0; split into per-domain
submodules at v1.14 -- was one 2,198-line engine/features/routes.py, now this package).

Each handler is `fn(h, qs)` for GET or `fn(h, qs, payload)` for POST, where `h` is the live
Handler (use h._send) and qs is the parse_qs dict. Handlers run inside viewer_app's single
error boundary (B9): raise registry.ParamError -> 400; FileNotFoundError -> 404; anything
else -> logged 500 with a generic body (J69). Param parsing goes through registry.qint/qstr/
qflag (B11) so malformed input never 500s. Behavior is IDENTICAL to the pre-split monolith
(every handler body moved verbatim into its new domain submodule -- see each submodule's
docstring). DI via `core`, injected into every submodule below (+ _shared) by viewer_app.

Submodules (import order doesn't matter for route registration -- registry.GET/POST are plain
dicts and no two submodules register the same (method, path); see tests/test_congruency.py and
audit_features.py's duplicate-route-path check, which now scans every file in this package):
  _shared          -- helpers used by MORE THAN ONE submodule (_exposed_read_guard, _pages_for,
                       _signoff_db); everything single-file-use stays local to its own submodule.
  static           -- page/script serving (_PAGES / _SCRIPTS, registered at import time)
  search           -- /api/search + suggest/findindoc/hybrid/semantic/analytics/visualmatch
  browse           -- side/chapter browsing, documents/vehicles/sessions
  parts_media      -- part imagery, 3-D, CAD render/spin/mesh
  doc_extractors   -- per-doc/page field extractors (VLM, layout, dimscan, KG, IETM, PUBLOG, ...)
  parts_refs       -- parts/references, keywords/tags, the parts-request PDF
  schematics       -- collections, schematics, schem-graph, part-locate, figuresheet
  jobcards         -- printable Work Order / job-package PDFs
  diagnostics      -- offline Q&A, designation decoders, cross-manual conflict/troubleshooting
  ops_status       -- status/ops/health, command center, data integrity, sign-off, RPS mode
  field_tools      -- handover, intervals, fluids, commonality, RPSTL, serviceability, BOM, ...
  ingest           -- ingest, air-gap manifest/verify, PMCS forms
  page_render      -- page word/callout metadata + the /page image renderer
"""
import sys as _sys
from types import ModuleType as _ModuleType

from features.routes import _shared
from features.routes import static
from features.routes import search
from features.routes import browse
from features.routes import parts_media
from features.routes import doc_extractors
from features.routes import parts_refs
from features.routes import schematics
from features.routes import jobcards
from features.routes import diagnostics
from features.routes import ops_status
from features.routes import field_tools
from features.routes import ingest
from features.routes import page_render

# Every submodule DI'd with `core` by viewer_app (mirrors the exact injection pattern the
# pre-split monolith used, just fanned out to each new submodule -- see viewer_app.py).
SUBMODULES = (_shared, search, browse, parts_media, doc_extractors, parts_refs, schematics,
              jobcards, diagnostics, ops_status, field_tools, ingest, page_render)

core = None          # kept for parity with the pre-split monolith; not itself read by any handler

# ---- backward-compat re-exports: engine/audit_features.py, engine/tests/test_congruency.py, and
# engine/tests/test_search_quality.py all reach into `features.routes` for these names directly
# (`from features import routes as R; R._PAGES`, `R._SCRIPTS`, `R._SEARCH_LRU`, ...). ------------
_PAGES = static._PAGES
_SCRIPTS = static._SCRIPTS
register_static = static.register_static

_SEARCH_LRU = search._SEARCH_LRU
_SEARCH_LRU_ORDER = search._SEARCH_LRU_ORDER
_SEARCH_LRU_LOCK = search._SEARCH_LRU_LOCK

# _SEARCH_LRU_TTL / _SEARCH_LRU_MAX are plain int/float in search.py -- unlike the dict/list/Lock
# above, `name = search._SEARCH_LRU_TTL` would copy the *value*, not alias the same object, so a
# caller doing `from features import routes as R; R._SEARCH_LRU_TTL = 5` (the override idiom this
# codebase already uses elsewhere, e.g. test_barcode_wiring.py's `VI.BARCODE_SCAN = False`) would
# silently rebind only this module's copy while search.py's r_search() kept reading its own
# unchanged 60.0/200 -- no error, just a no-op override. Proxy both read and write through to
# search.py's real globals so `_SEARCH_LRU_TTL`/`_SEARCH_LRU_MAX` behave like live references,
# matching the sibling re-exports above.
_LIVE_PROXIED_ATTRS = ("_SEARCH_LRU_TTL", "_SEARCH_LRU_MAX")


class _RoutesModule(_ModuleType):
    def __getattr__(self, name):
        if name in _LIVE_PROXIED_ATTRS:
            return getattr(search, name)
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    def __setattr__(self, name, value):
        if name in _LIVE_PROXIED_ATTRS:
            setattr(search, name, value)
        else:
            super().__setattr__(name, value)


_sys.modules[__name__].__class__ = _RoutesModule
