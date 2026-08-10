#!/usr/bin/env python3
"""THE VIEWER -- mission-control COVERAGE aggregator (v0.99.6). One read-only roll-up of how enriched the whole
corpus is: OCR %, CAD renders, schematic netlists, vectorized figures, local models, figure crops, cross-ref
sidecars, and the review queues. Pure stdlib; reads the index (mode=ro) + the sidecar files (R1/R6). Functions
take db_path + index_dir explicitly (no core injection)."""
import os, sqlite3, time

_THREED_WHERE = ("characteristics IS NOT NULL AND characteristics<>'' AND ("
                 "upper(characteristics) LIKE '%DIAMETER%' OR upper(characteristics) LIKE '%LENGTH%' OR "
                 "upper(characteristics) LIKE '%HEIGHT%' OR upper(characteristics) LIKE '%WIDTH%' OR "
                 "upper(characteristics) LIKE '%THICKNESS%')")


def _db(db_path):
    con = sqlite3.connect("file:%s?mode=ro" % db_path, uri=True); con.row_factory = sqlite3.Row; return con


def _count_files(d, suffix, cap=400000):
    n = 0
    try:
        with os.scandir(d) as it:
            for e in it:
                if e.name.endswith(suffix):
                    n += 1
                    if n >= cap:
                        break
    except Exception:
        pass
    return n


def _tsv_rows(path):
    if not os.path.exists(path):
        return 0
    try:
        with open(path, encoding="utf-8") as f:
            return max(0, sum(1 for _ in f) - 1)   # minus header
    except Exception:
        return 0


def _latest_version(index_dir):
    # read the changelog top (../docs/CHANGELOG.md relative to the index dir's parent)
    try:
        cl = os.path.join(os.path.dirname(index_dir), "docs", "CHANGELOG.md")
        for ln in open(cl, encoding="utf-8"):
            if ln.startswith("## ["):
                return ln.split("[", 1)[1].split("]", 1)[0]
    except Exception:
        pass
    return None


def pct(a, b):
    return round(100.0 * a / b, 1) if b else 0.0


def overview(db_path, index_dir):
    docs = total_pages = ocr_pages = rep = parts_fig_pages = 0
    ocr_conf_avg = None; ocr_conf_scored = ocr_conf_low = 0
    try:
        con = _db(db_path)
        def scalar(sql):
            try: return con.execute(sql).fetchone()[0]
            except Exception: return 0
        docs = scalar("SELECT COUNT(*) FROM documents")
        total_pages = scalar("SELECT COUNT(*) FROM pages")
        ocr_pages = scalar("SELECT COUNT(*) FROM pages WHERE COALESCE(body_text,'')<>''")
        rep = scalar("SELECT COUNT(DISTINCT nsn) FROM ref_nsn WHERE " + _THREED_WHERE)
        parts_fig_pages = scalar("SELECT COUNT(*) FROM (SELECT DISTINCT document_id, page FROM parts "
                                 "WHERE fig_no IS NOT NULL AND page IS NOT NULL)")
        # v1.13.5: real OCR-quality signal (previously only 'ran' vs 'did not run' existed at all --
        # see ocr_one()/CHANGELOG [1.13.5]). Only scored since this migration; older pages read NULL
        # until naturally re-OCR'd, so ocr_conf_scored is expected to lag pages_ocr for a long time.
        # 0.5 is a first-pass, uncalibrated "worth a look" bar -- deliberately conservative (low false-
        # alarm risk) pending real corpus data to tune it against.
        ocr_conf_avg = scalar("SELECT AVG(ocr_confidence) FROM pages WHERE ocr_confidence IS NOT NULL")
        ocr_conf_scored = scalar("SELECT COUNT(*) FROM pages WHERE ocr_confidence IS NOT NULL")
        ocr_conf_low = scalar("SELECT COUNT(*) FROM pages WHERE ocr_confidence IS NOT NULL AND ocr_confidence < 0.5")
        con.close()
    except Exception:
        pass

    cad = _count_files(os.path.join(index_dir, "cadcache"), "_v3.png")
    schem = _tsv_rows(os.path.join(index_dir, "schemgraph_coverage.tsv"))
    vec = _tsv_rows(os.path.join(index_dir, "vectorize_coverage.tsv"))
    fig = _count_files(os.path.join(index_dir, "figcache"), ".png")
    models = _count_files(os.path.join(index_dir, "models3d"), ".obj") + _count_files(os.path.join(index_dir, "models3d"), ".stl")

    sr = {}
    try:
        import schemreview
        sr = schemreview.coverage_summary(index_dir)
    except Exception:
        pass

    sidecars = {}
    for name in ("viewer.db", "collections.db", "reviews.db", "correlations.db", "rpstl.db",
                 "cage.json", "pn_nsn.json", "chapter_sides.json", "hardware_profile.json"):
        p = os.path.join(index_dir, name)
        sidecars[name] = {"exists": os.path.exists(p),
                          "mb": round(os.path.getsize(p) / 1e6, 1) if os.path.exists(p) else 0}

    return {
        "version": _latest_version(index_dir),
        "generated": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "corpus": {"documents": docs, "pages_total": total_pages},
        "ocr": {"pages_ocr": ocr_pages, "pages_total": total_pages, "pct": pct(ocr_pages, total_pages),
                "avg_confidence": round(ocr_conf_avg, 3) if ocr_conf_avg is not None else None,
                "confidence_scored_pages": ocr_conf_scored, "low_confidence_pages": ocr_conf_low},
        "cad": {"rendered_v3": cad, "representative_parts": rep, "pct": pct(cad, rep)},
        "schematics": {"netlist_pages": schem, "avg_confidence": sr.get("avg_confidence"),
                       "pages_with_components": sr.get("pages_with_components"), "reviewed": sr.get("pages_reviewed")},
        "vectorize": {"figures_vectorized": vec, "figure_pages": parts_fig_pages, "pct": pct(vec, parts_fig_pages)},
        "figure_crops": fig,
        "local_models": models,
        "sidecars": sidecars,
    }


if __name__ == "__main__":
    import json, sys
    db = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "index", "viewer.db")
    print(json.dumps(overview(db, os.path.dirname(db)), indent=2))
