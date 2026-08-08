#!/usr/bin/env python3
"""THE VIEWER -- parts-request sessions (extracted verbatim from viewer_app, v0.96.0).

Recent sessions for the home screen + saving a request (session, fault, items) before the
104th sheet PDF is generated. DI via `core`."""
import sqlite3

core = None          # injected by viewer_app at startup


def recent_sessions(limit=12):
    """Recent parts-request sessions (for the home screen's 'recent requests')."""
    con = core.db()
    try:
        rows = con.execute(
            "SELECT s.id, s.bumper_number, s.mechanic, s.tm, s.created_at, "
            "       (SELECT description FROM faults f WHERE f.session_id=s.id LIMIT 1) AS fault, "
            "       (SELECT COUNT(*) FROM request_items ri WHERE ri.session_id=s.id) AS items "
            "FROM sessions s ORDER BY s.id DESC LIMIT ?", (limit,)).fetchall()
    except sqlite3.OperationalError:
        rows = []
    con.close()
    return [dict(r) for r in rows]


def save_request(payload):
    """v1.13: any failure ROLLS BACK before re-raising -- the per-thread connection is REUSED by later
    requests, so an open half-written transaction must never be left behind (it would hold the write
    lock and silently absorb the next request's work)."""
    s = payload.get("session", {}); items = payload.get("items", [])
    con = core.db()
    try:
        try:
            cur = con.execute("INSERT INTO sessions(mechanic,bumper_number,tm,uoc,tech_status,motor_sergeant,tech_status_suggested,tech_status_basis) VALUES(?,?,?,?,?,?,?,?)",
                (s.get("mechanic"), s.get("bumper"), s.get("tm"), s.get("uoc"), s.get("tech_status"), s.get("motor_sergeant"), s.get("tech_status_suggested"), s.get("tech_status_basis")))
        except sqlite3.OperationalError:
            cur = con.execute("INSERT INTO sessions(mechanic,bumper_number,tm,uoc,tech_status,motor_sergeant) VALUES(?,?,?,?,?,?)",
                (s.get("mechanic"), s.get("bumper"), s.get("tm"), s.get("uoc"), s.get("tech_status"), s.get("motor_sergeant")))
        sid = cur.lastrowid
        if s.get("fault"): con.execute("INSERT INTO faults(session_id,description) VALUES(?,?)", (sid, s.get("fault")))
        for it in items:
            con.execute("INSERT INTO request_items(session_id,item_name,nsn,qty,fig_no,part_no,unit_price,aac,arc,source_document_id,source_page) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                (sid, it.get("item_name"), it.get("nsn"), it.get("qty"), it.get("fig"), it.get("part"), it.get("unit_price"), it.get("aac"), it.get("arc"), it.get("source_document_id"), it.get("source_page")))
        con.commit()
        return sid
    except Exception:
        try:
            con.rollback()
        except Exception:
            pass
        raise                                 # fail LOUD (R13) -- but on a clean connection
    finally:
        con.close()                           # no-op on the pooled connection; real close in relaxed mode
