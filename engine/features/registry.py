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
    return min(v, ABS_MAX_LIMIT) if name in ("limit", "n") else v


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


def qflag(qs, name, default="0"):
    """'1' -> True, anything else False (the monolith's exact semantics)."""
    return qstr(qs, name, default) == "1"
