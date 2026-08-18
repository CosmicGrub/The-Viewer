#!/usr/bin/env python3
"""Declarative route registry + central request-param validation (backlog A5, A7, B11; v0.96.0).

GET/POST map url-path -> handler(handler_instance, qs[, payload]). viewer_app's Handler does one
dict lookup inside ONE error boundary (B9) instead of ~90 if/elif blocks. Param helpers raise
ParamError for malformed client input, which the boundary turns into a clean 400 (was: 500).

Stdlib-only, RPS-safe.
"""

GET = {}
POST = {}

# Hard server-side ceilings (backlog J67): no client can request more than this many rows,
# whatever the per-route default/cap says.
ABS_MAX_LIMIT = 2000

# SQLite binds integer params into a signed 64-bit column; anything outside this range raises an
# uncaught OverflowError deep in whichever route/feature module later does con.execute(..., (v,)) --
# reject it here, once, as a clean 400 instead of letting every qint()-consuming callsite 500 on it.
_SQLITE_INT_MIN = -(2 ** 63)
_SQLITE_INT_MAX = 2 ** 63 - 1


class ParamError(ValueError):
    """Malformed client input -> 400 (never a 500)."""


def register_get(path, fn, aliases=()):
    GET[path] = fn
    for a in aliases:
        GET[a] = fn
    return fn


def register_post(path, fn):
    POST[path] = fn
    return fn


def get(path, *aliases):
    def deco(fn):
        return register_get(path, fn, aliases)
    return deco


def post(path):
    def deco(fn):
        return register_post(path, fn)
    return deco


# ---- central param parsing/clamping (B11): bad input -> ParamError -> 400 ----------------------

def qstr(qs, name, default=""):
    v = (qs.get(name) or [default])[0]
    return default if v is None else v


def qint(qs, name, default, lo=None, hi=None):
    raw = (qs.get(name) or [None])[0]
    if raw is None or raw == "":
        v = default
    else:
        try:
            v = int(str(raw).strip())
        except Exception:
            raise ParamError("parameter '%s' must be an integer (got %r)" % (name, raw))
    if lo is not None:
        v = max(lo, v)
    if hi is not None:
        v = min(hi, v)
    v = min(v, ABS_MAX_LIMIT) if name in ("limit", "n") else v
    # SQLite-range check runs LAST, after lo/hi/ABS_MAX_LIMIT clamping: most callers pass a small `hi`
    # that already makes an oversized value safe (previously silently clamped -- keep that), so only
    # reject here when nothing upstream bounded it (e.g. qint(qs, "doc", 0) has no hi) and the value
    # would otherwise raise an uncaught OverflowError wherever it's later bound into a SQL query.
    if v < _SQLITE_INT_MIN or v > _SQLITE_INT_MAX:
        raise ParamError("parameter '%s' out of range (got %r)" % (name, raw))
    return v


def qfloat(qs, name, default, lo=None, hi=None):
    """Float param with clamping; malformed / non-finite input -> ParamError -> 400 (mirrors qint;
    v1.13 -- routes previously did their own float() with ad-hoc handling)."""
    raw = (qs.get(name) or [None])[0]
    if raw is None or raw == "":
        v = default
    else:
        try:
            v = float(str(raw).strip())
        except Exception:
            raise ParamError("parameter '%s' must be a number (got %r)" % (name, raw))
        if v != v or v in (float("inf"), float("-inf")):     # NaN / +-inf are never valid route params
            raise ParamError("parameter '%s' must be a finite number (got %r)" % (name, raw))
    if lo is not None:
        v = max(lo, v)
    if hi is not None:
        v = min(hi, v)
    return v


def safe_header_token(s, maxlen=30):
    """ASCII-only alnum/-_ filter for values embedded in an HTTP header (e.g. a Content-Disposition
    filename built from a user query). str.isalnum() accepts non-ASCII Unicode digit/letter categories
    (e.g. Arabic-indic digits) that can't be Latin-1-encoded when the header is written, crashing the
    response mid-write (the client sees a dropped connection, not a clean error) -- restrict to true
    ASCII here instead."""
    return "".join(ch for ch in (s or "") if ch.isascii() and (ch.isalnum() or ch in "-_"))[:maxlen]


def qflag(qs, name, default="0"):
    """'1' -> True, anything else False (the monolith's exact semantics)."""
    return qstr(qs, name, default) == "1"
