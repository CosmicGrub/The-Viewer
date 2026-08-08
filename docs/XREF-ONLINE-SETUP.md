# Online cross-reference enrichment (X4) — OPTIONAL, off by default

THE VIEWER resolves parts **offline** from PUB LOG/FLIS + the platform map. This optional step fills only the
**residual unknowns** with **public** reference data (NSN catalog nomenclature, manufacturer cross-reference,
colloquial names), and **caches** it so your offline system keeps it.

> ⚠️ **Public data only. Never controlled technical data.** Do not point this at ITAR/EAR-controlled sources
> (engineering drawings, CAD, repair/manufacturing data). Use only public catalogs you are permitted to query,
> and you are responsible for honoring that source's terms.

## It is OFF unless you turn it on
```
set VIEWER_XREF_ONLINE=1
set VIEWER_XREF_URL=https://your-public-nsn-catalog/api?nsn={nsn}
```
- `{nsn}` (and `{niin}`) are substituted. The endpoint should return JSON with any of: `item_name`/`name`,
  `colloquial`/`common_name`, `manufacturer`/`company`.
- With nothing configured, the feature reports "off" and the app stays 100% offline.

## How it's used
- The running app **only reads the cache** (`index/xref_online.json`) — it never fetches while serving pages.
- Fetching is a **deliberate, separate step** (`xref_online.enrich(nsn)` when enabled), so an offline
  deployment never reaches the network unexpectedly.
- Cached fields surface in the part record as **colloquial name** / **manufacturer** with provenance
  `online(cached)`, clearly distinct from the authoritative FLIS values.

## Status
`GET /api/xref_online` → `{enabled, cached_count, note, setup}`.

## Why it's gated this way
Offline-first is the whole point of THE VIEWER. The internet is a convenience for the long tail only, kept
optional, cached, public-only, and ITAR-aware — never a runtime dependency and never a source of controlled
data.
