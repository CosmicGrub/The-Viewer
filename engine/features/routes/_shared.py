#!/usr/bin/env python3
"""THE VIEWER -- route helpers shared across MORE THAN ONE routes/ submodule (v1.14, routes.py split).

Only helpers with real multi-file callers live here (per the split's ground rule: no duplicated
helpers across submodules). Everything single-file-use stays local to its own submodule, same as
the original monolith. DI via `core` (injected by viewer_app at startup, same convention as every
other routes/ submodule)."""

core = None          # injected by viewer_app at startup


def _exposed_read_guard(h):
    """Gate for GET endpoints that leak host internals (filesystem paths, run/ingest state) rather
    than manual content. do_POST already requires the shared X-Viewer-Token when the server is
    network-exposed (_EXPOSED); do_GET never did, on the (correct, and kept as-is) assumption that
    the normal exposed-mode use case is a mechanic's phone browsing/searching manuals over LAN with
    no way to set a custom header on plain navigation. But that same blanket assumption left every
    GET route that reveals real filesystem paths or internal run state -- not manual content --
    wide open to anyone on the network. Applied to: /api/audit, /api/ops, /api/status,
    /api/command_status (embeds status_summary(), the same payload /api/status protects),
    /api/ingest_status (leaks the raw host path of the current/last ingest job), /api/provenance
    (self-documented "INTERNAL AUDIT (operator, not mechanic)"), and /api/integrity (streams file
    paths/checksums). Returns True if the request may proceed; sends 401 and returns False otherwise.
    """
    if not core._EXPOSED:
        return True
    if core._auth_ok(h.headers.get("X-Viewer-Token")):
        return True
    h._send(401, core.AUTH_REQUIRED_BODY)
    return False


def _signoff_db():
    import os
    return os.path.join(os.path.dirname(core.DB_PATH), "signoff.db")


def _pages_for(q, limit=12):
    """Bounded FTS page bodies for a query (shared by the text extractors below)."""
    import sqlite3, re as _re
    terms = [t for t in _re.findall(r"[A-Za-z0-9]+", q or "") if len(t) > 1]
    if not terms:
        return []
    try:
        con = core.db()          # v1.13: pooled + Row factory already set; close() no-op -> leak-free
        rows = con.execute("SELECT d.id AS doc, d.tm_number AS tm, p.page_number AS page, p.body_text AS body "
                           "FROM pages_fts JOIN pages p ON p.id=pages_fts.rowid JOIN documents d ON d.id=p.document_id "
                           "WHERE pages_fts MATCH ? ORDER BY rank LIMIT ?", (" OR ".join(terms), limit)).fetchall()
        con.close(); return [dict(r) for r in rows]
    except Exception:
        return []
