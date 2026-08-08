#!/usr/bin/env python3
"""THE VIEWER -- Living Schematic review/override queue (step 2/3).

Human-in-the-loop corrections for the inferred netlist, the same shape as the NIIN review: APPEND-ONLY
(R6), sidecar-only (R1). A reviewer can mark a page's netlist good/bad and add component ref-designators the
vectorizer missed (CAD-exported sheets outline their label text, so schemgraph finds wires but 0 comps).

Store: index/schemreviews.jsonl -- one JSON object per line, latest record for a (doc,page) wins.
The queue is derived from index/schemgraph_coverage.tsv (built by build_schemgraph.py): pages with wires but
no/low components, or low confidence, minus those already decided.

Pure stdlib. Functions take index_dir explicitly (no core injection needed).
  record / latest_for / overrides_for / queue / stats
"""
import os, json, time

def _reviews_path(index_dir):
    return os.path.join(index_dir, "schemreviews.jsonl")

def _coverage_path(index_dir):
    return os.path.join(index_dir, "schemgraph_coverage.tsv")


def record(index_dir, doc, page, verdict, labels=None, note="", by=""):
    """Append a review. verdict in {'good','bad','corrected'}; labels = [{ref,x,y}] (x,y normalized 0..1)."""
    try:
        doc = int(doc); page = int(page)
    except Exception:
        return {"ok": False, "error": "bad doc/page"}
    verdict = (verdict or "").strip().lower()
    if verdict not in ("good", "bad", "corrected"):
        return {"ok": False, "error": "verdict must be good|bad|corrected"}
    clean = []
    for l in (labels or []):
        try:
            ref = str(l.get("ref", "")).strip()[:16]
            x = max(0.0, min(1.0, float(l.get("x")))); y = max(0.0, min(1.0, float(l.get("y"))))
            if ref: clean.append({"ref": ref, "x": round(x, 5), "y": round(y, 5)})
        except Exception:
            continue
    rec = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "doc": doc, "page": page,
           "verdict": verdict, "labels": clean, "note": (note or "")[:500], "by": (by or "")[:60]}
    try:
        os.makedirs(index_dir, exist_ok=True)
        with open(_reviews_path(index_dir), "a", encoding="utf-8") as f:
            f.write(json.dumps(rec) + "\n")
    except Exception as e:
        return {"ok": False, "error": str(e)}
    return {"ok": True, "record": rec}


def _all_records(index_dir):
    p = _reviews_path(index_dir); out = []
    if not os.path.exists(p):
        return out
    try:
        for ln in open(p, encoding="utf-8"):
            ln = ln.strip()
            if ln:
                try: out.append(json.loads(ln))
                except Exception: pass
    except Exception:
        pass
    return out


def latest_for(index_dir, doc, page):
    try: doc = int(doc); page = int(page)
    except Exception: return None
    latest = None
    for r in _all_records(index_dir):
        if r.get("doc") == doc and r.get("page") == page:
            latest = r          # append-only: last line for this page wins
    return latest


def overrides_for(index_dir, doc, page):
    """What to merge into the served graph: manual component labels + the verdict, if any."""
    r = latest_for(index_dir, doc, page)
    if not r:
        return None
    return {"verdict": r.get("verdict"), "labels": r.get("labels", []),
            "by": r.get("by", ""), "ts": r.get("ts", "")}


def _decided_map(index_dir):
    m = {}
    for r in _all_records(index_dir):
        m[(r.get("doc"), r.get("page"))] = r.get("verdict")
    return m


def queue(index_dir, limit=200, offset=0, include_decided=False):
    """Pages that likely need a look: wires present but 0 components, or confidence < 0.5.
    Reads the coverage TSV; annotates each with any decision. Undecided first."""
    cov = _coverage_path(index_dir); rows = []
    decided = _decided_map(index_dir)
    if os.path.exists(cov):
        try:
            with open(cov, encoding="utf-8") as f:
                header = f.readline()
                for ln in f:
                    p = ln.rstrip("\n").split("\t")
                    if len(p) < 8: continue
                    try:
                        doc = int(p[0]); page = int(p[1]); edges = int(p[4]); nets = int(p[5])
                        comps = int(p[6]); conf = float(p[7])
                    except Exception:
                        continue
                    needs = (comps == 0) or (conf < 0.5)
                    dv = decided.get((doc, page))
                    if not needs and not (include_decided and dv):
                        continue
                    rows.append({"doc": doc, "page": page, "edges": edges, "nets": nets,
                                 "components": comps, "confidence": conf, "decision": dv,
                                 "reason": ("no components" if comps == 0 else "low confidence")})
        except Exception:
            pass
    # undecided first, then by lowest confidence
    rows.sort(key=lambda r: (r["decision"] is not None, r["confidence"]))
    total = len(rows)
    return {"total": total, "pending": sum(1 for r in rows if r["decision"] is None),
            "items": rows[offset:offset + limit]}


def coverage_summary(index_dir):
    """Roll up the schemgraph coverage TSV for the Ops dashboard: how many schematic pages have a usable
    netlist, how many have components, average confidence, and how many are reviewed."""
    cov = _coverage_path(index_dir)
    pages = with_comp = 0; conf_sum = 0.0; nets_sum = 0
    if os.path.exists(cov):
        try:
            with open(cov, encoding="utf-8") as f:
                f.readline()
                for ln in f:
                    p = ln.rstrip("\n").split("\t")
                    if len(p) < 8: continue
                    try:
                        nets = int(p[5]); comps = int(p[6]); conf = float(p[7])
                    except Exception:
                        continue
                    pages += 1; nets_sum += nets; conf_sum += conf
                    if comps > 0: with_comp += 1
        except Exception:
            pass
    st = stats(index_dir)
    return {"schematic_pages": pages, "pages_with_components": with_comp,
            "pages_without_components": pages - with_comp,
            "avg_confidence": round(conf_sum / pages, 3) if pages else 0.0,
            "nets_total": nets_sum, "pages_reviewed": st["pages_decided"],
            "built": os.path.exists(cov)}


def stats(index_dir):
    recs = _all_records(index_dir)
    by = {}
    for r in recs:
        by[r.get("verdict", "?")] = by.get(r.get("verdict", "?"), 0) + 1
    pages = len({(r.get("doc"), r.get("page")) for r in recs})
    return {"reviews": len(recs), "pages_decided": pages, "by_verdict": by}
