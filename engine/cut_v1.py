#!/usr/bin/env python3
"""THE VIEWER -- CUT v1.0.0. Stamps VERSION=1.0.0, banners both changelogs, and regenerates the iteration snapshot so
it still matches (R10). Idempotent-ish: refuses if VERSION is already 1.x. Run via CUT-V1.0.bat (which snapshots a
backup first). Edits are limited to viewer_app.py VERSION + the two changelog tops + the snapshot files."""
import os, re, sys, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
DOCS = os.path.join(HERE, "..", "docs")
APP = os.path.join(HERE, "viewer_app.py")
CL = os.path.join(DOCS, "CHANGELOG.md")
CLL = os.path.join(DOCS, "CHANGELOG-LEGACY.md")
TODAY = datetime.date.today().isoformat()

BANNER = (
    "## [1.0.0] — %s — \U0001f6a2 v1.0.0 — first stable release\n"
    "The offline TM search engine + dynamic viewer reaches 1.0: full-text + semantic + visual search, the cited Work\n"
    "Order, torque/fastener/PMCS references, look-alike + related parts, dynamic graphics (deep-zoom/vectorize/CAD/3-D/\n"
    "schematic), drag-drop ingest, and a self-auditing + fuzz/mutation-hardened core. Two build tiers (GPU + legacy RPS).\n"
    "See docs/RELEASE-NOTES-1.0.md. Everything below is the 0.x path that got here.\n\n---\n\n"
)
BANNER_L = (
    "## [1.0.0-legacy] — %s — v1.0.0 (legacy track) ................................................. ✓ parity\n"
    "Legacy/RPS tier reaches 1.0 alongside modern: same features via the compatibility toolchain (Poppler/Tesseract/\n"
    "ES5), GPU-only items degrade gracefully. See CHANGELOG-LEGACY history for per-item parity.\n\n"
)


def _bump_version():
    s = open(APP, encoding="utf-8").read()
    m = re.search(r'^VERSION\s*=\s*"([^"]+)"', s, re.M)
    if not m:
        print("could not find VERSION in viewer_app.py"); return False
    if m.group(1).startswith("1."):
        print("VERSION already %s -- refusing to re-cut." % m.group(1)); return False
    s2 = re.sub(r'^VERSION\s*=\s*"[^"]+"', 'VERSION = "1.0.0"', s, count=1, flags=re.M)
    open(APP, "w", encoding="utf-8").write(s2)
    print("VERSION -> 1.0.0")
    return True


def _banner(path, banner):
    s = open(path, encoding="utf-8").read()
    if "[1.0.0]" in s or "[1.0.0-legacy]" in s:
        print("%s already has a 1.0.0 banner." % os.path.basename(path)); return
    i = s.find("\n## [")
    if i < 0:
        s = s + "\n" + banner
    else:
        s = s[:i + 1] + banner + s[i + 1:]
    open(path, "w", encoding="utf-8").write(s)
    print("bannered", os.path.basename(path))


def main():
    if not _bump_version():
        return 1
    _banner(CL, BANNER % TODAY)
    _banner(CLL, BANNER_L % TODAY)
    try:
        sys.path.insert(0, HERE)
        import build_iteration_snapshot as B
        B.main()
        print("snapshot regenerated (R10).")
    except Exception as e:
        print("snapshot regen skipped:", e)
    print("\nv1.0.0 stamped. Commit / zip a tagged backup and you're released.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
# END OF FILE
