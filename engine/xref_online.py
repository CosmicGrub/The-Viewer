#!/usr/bin/env python3
"""THE VIEWER -- X4: OPTIONAL online cross-reference enrichment (off by default, cached, public-only).

Offline-first: PUB LOG/FLIS does the decisive resolving. This is only for the RESIDUAL unknowns, and only
PUBLIC reference data (NSN catalog nomenclature, manufacturer cross-reference, colloquial names). Results are
CACHED to a sidecar (index/xref_online.json) so the offline system keeps them; the app never fetches at
runtime. Gated behind VIEWER_XREF_ONLINE=1 AND a user-configured public endpoint -- and it must NEVER fetch
controlled technical data (ITAR/EAR). The default is fully disabled.

Configure (you accept the source's terms / legality):
  set VIEWER_XREF_ONLINE=1
  set VIEWER_XREF_URL=https://EXAMPLE-public-nsn-catalog/api?nsn={nsn}     # returns public JSON

`core` injected by viewer_app. The running app only READS the cache; fetching is a deliberate, separate step.
"""
import os, json, time

core = None


def _cache_path():
    return os.path.join(os.path.dirname(core.DB_PATH), "xref_online.json")


def _load():
    p = _cache_path()
    if not os.path.exists(p): return {}
    try:
        with open(p, "r", encoding="utf-8") as f: return json.load(f) or {}
    except Exception:
        return {}


def cached(nsn):
    """Read-only: any cached online enrichment for this NSN (used by the offline resolver)."""
    return _load().get((nsn or "").strip())


def enabled():
    return os.environ.get("VIEWER_XREF_ONLINE", "0") == "1" and bool(os.environ.get("VIEWER_XREF_URL", "").strip())


def status():
    return {"enabled": enabled(), "cached_count": len(_load()),
            "note": "Off by default. Public reference data only; never controlled (ITAR/EAR) technical data.",
            "setup": "docs/XREF-ONLINE-SETUP.md" if not enabled() else None}


def enrich(nsn, timeout=15):
    """Fetch + cache PUBLIC reference for one NSN -- ONLY when explicitly enabled + configured. This is a
    deliberate online step (not part of normal serving). Stdlib urllib; stores {item_name, colloquial, source}."""
    nsn = (nsn or "").strip()
    if not nsn:
        return {"ok": False, "error": "no nsn"}
    if not enabled():
        return {"ok": False, "enabled": False, "setup": "docs/XREF-ONLINE-SETUP.md"}
    url = os.environ.get("VIEWER_XREF_URL", "").replace("{nsn}", nsn).replace("{niin}", nsn.replace("-", "")[-9:])
    try:
        import urllib.request
        req = urllib.request.Request(url, headers={"User-Agent": "THE-VIEWER/xref (offline cache)"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read(200000)
        data = json.loads(raw.decode("utf-8", "ignore"))
    except Exception as e:
        return {"ok": False, "enabled": True, "error": "fetch failed: %s" % e}
    # store a conservative subset (public nomenclature/cross-ref only)
    rec = {"item_name": data.get("item_name") or data.get("name"),
           "colloquial": data.get("colloquial") or data.get("common_name"),
           "manufacturer": data.get("manufacturer") or data.get("company"),
           "source": url, "at": time.strftime("%Y-%m-%dT%H:%M:%S")}
    blob = _load(); blob[nsn] = rec
    p = _cache_path()
    import safeguard; safeguard.atomic_write(p, json.dumps(blob, indent=1))          # v1.13: fsync + retry
    return {"ok": True, "nsn": nsn, "record": rec}
