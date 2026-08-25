#!/usr/bin/env python3
"""THE VIEWER -- MASTERFILE (v1.2.0). The single, all-encompassing consolidation of measurement/dimensional data for the
whole project. It MERGES the corpus's authoritative measurements (from measures.db, page-cited to the real TM files)
with the external gap-fills (from enrich.db) and, when present, self-grounded/OCR-cross-checked vision-language
extractions (from pageqa.db) into ONE congruent dataset keyed to the authoritative subjects, so the rest of the project
sees a unified picture instead of scattered sources.

Design goals (Chris's ask):
  * ONE Masterfile that is compatible / complementary / congruent with the existing data and sidecars.
  * The reader sees the RAW values AND a FILTERED (deduped, canonical) view, correlated to the authoritative files.
  * NO links surfaced. Corpus rows keep their page cite (a pointer INTO the authoritative TM — desired). External rows
    carry NO URL in the Masterfile or UI; their web provenance stays inside enrich.db for audit only.
  * Corpus is authoritative: external values appear only for (subject, dimension type) the corpus is silent on.

v1.2.0 (plan item 13, docs/superpowers/plans/2026-08-24-vision-language-page-qa-plan.md): build() gains index/pageqa.db
as one more CORROBORATING source, tagged origin='vlm-verified' -- the same distinguishable-provenance pattern
barcode-decoded NSN rows already use (confidence='barcode') in the parts table, so an operator can always tell which
pipeline produced a given value. build_pageqa.py (Phase 2's batch driver) only ever writes verified=True rows -- self-
grounded via vlm.ground() AND fuzzy-matched against this page's own already-trusted stored OCR text (see pageqa.py's
structured/strict path) -- before a row ever reaches pageqa.db, so what lands here has already passed real
verification, not a bare model claim. Still kept as its OWN (subject,type,unit,origin) group, never merged into
'corpus': it must never silently inflate or override a regex-extracted corpus value's own count/note/confidence badge
(R13 -- an AI-sourced tier must never visually pass as more authoritative than it is). Degrades EXACTLY like
measures_db/enrich_db already do -- an absent/missing pageqa.db (the common case on a fresh checkout, or before an
operator has ever run BUILD-PAGEQA.bat) simply contributes nothing, never raises, never blocks the rest of the build.

Read-only on the corpus/index; writes only the append-only sidecar index/masterfile.db (R1/R6). Rebuilt by
build_masterfile.py / BUILD-MASTERFILE.bat. Degrades gracefully if a source sidecar is absent."""
import os, sqlite3, statistics, time
from collections import Counter, defaultdict

SCHEMA = """
CREATE TABLE IF NOT EXISTS master_raw(
  id INTEGER PRIMARY KEY, subject TEXT, subject_label TEXT, doc INTEGER, page INTEGER,
  type TEXT, unit TEXT, value TEXT, value2 TEXT, tolerance TEXT, context TEXT,
  origin TEXT);     -- 'corpus' (authoritative) | 'external' (supplemental, unconfirmed) | 'vlm-verified'
                     -- (page-cited, self-grounded + OCR-cross-checked vision-language extraction -- see pageqa.py)
CREATE INDEX IF NOT EXISTS ix_mraw_subj ON master_raw(subject);
CREATE INDEX IF NOT EXISTS ix_mraw_type ON master_raw(type);
CREATE TABLE IF NOT EXISTS master_filtered(
  id INTEGER PRIMARY KEY, subject TEXT, subject_label TEXT, type TEXT, unit TEXT,
  value TEXT, low TEXT, high TEXT, n INTEGER, origin TEXT, authoritative INTEGER, note TEXT);
CREATE INDEX IF NOT EXISTS ix_mflt_subj ON master_filtered(subject);
CREATE TABLE IF NOT EXISTS master_meta(k TEXT PRIMARY KEY, v TEXT);
"""


def _num(v):
    try:
        return float(str(v).replace(",", ""))
    except Exception:
        return None


def _canonical_core(counter, low, high):
    """Shared math for the representative value + numeric span, given an already-aggregated
    Counter of values and a running (low, high) numeric span (either or both may be None if no
    numeric value was seen). Both _canonical() (batch, from a raw value list) and build()'s
    streaming accumulator reduce to this one implementation -- review finding: the streaming
    rewrite (medium finding #25) originally duplicated this most_common()/min-max-formatting logic
    inline instead of sharing it, leaving _canonical() itself dead in the production path.

    Masterfile comparison audit (data-consistency finding): the representative value used to be
    Counter.most_common(1) -- the STRING mode. For continuous physical measurements this is nearly
    always "arbitrary first-seen tiebreak dressed as most common": two documents rarely produce a
    byte-identical value string (180 vs 180.5 vs 179.8 are three distinct Counter keys, each count
    1), so most_common(1) silently picked whichever document happened to be scanned/inserted first
    -- verified directly against this exact case (3 real documents, 3 real close-but-different
    lengths) before this fix: value="180" purely because doc 1 was crawled first, with a "high"
    confidence badge next to it despite the pick being uncorrelated with which value is actually
    most representative. Now: the representative value is the NUMERIC MEDIAN of every value in the
    group that parses as a number (weighted by how many rows shared that exact string -- expanded
    from `counter`, which is already retained for the non-numeric fallback below, so this doesn't
    reintroduce the O(total rows) list finding #25 specifically eliminated; it's bounded by this
    ONE group's own row count at finalization time, not the whole corpus). Falls back to the old
    mode-on-string pick only when NOTHING in the group parses as a number at all (e.g. a thread-
    size/MIL-STD callout from specparse.py, which isn't a magnitude to average in the first
    place -- median has no meaning there, mode is still the right answer)."""
    n = sum(counter.values())
    if not n:
        return "", "", "", 0
    numeric = []
    for v, c in counter.items():
        nv = _num(v)
        if nv is not None:
            numeric.extend([nv] * c)
    rep = ("%g" % statistics.median(numeric)) if numeric else counter.most_common(1)[0][0]
    low_s = ("%g" % low) if low is not None else ""
    high_s = ("%g" % high) if high is not None else ""
    return rep, low_s, high_s, n


def _canonical(vals):
    """Given a list of value strings for one (subject,type,unit,origin): representative value (most common), plus the
    numeric low/high span and the count. Returns (value, low, high, n). Kept as a public, list-based
    convenience wrapper around _canonical_core() -- build() below calls _canonical_core() directly
    against its incrementally-aggregated Counter instead of materializing a list to pass here."""
    vals = [v for v in vals if v not in (None, "")]
    counter = Counter(vals)
    nums = [x for x in (_num(v) for v in vals) if x is not None]
    low = min(nums) if nums else None
    high = max(nums) if nums else None
    return _canonical_core(counter, low, high)


def build(db_path, measures_db, enrich_db, master_db, md_path=None, pageqa_db=None):
    """Consolidate corpus + external + (optional) vlm-verified into master_db (+ optional Markdown export).
    Returns a summary dict. `pageqa_db` is a new, OPTIONAL, keyword-only-by-convention param appended after
    `md_path` specifically so every existing positional call site (build_masterfile.py, every test in this
    repo's suite) keeps working unchanged -- omitting it (or passing None / a path that doesn't exist yet)
    degrades exactly like omitting measures_db/enrich_db already does: that source simply contributes
    nothing, never raises (plan item 13's explicit ask: match the established missing-sidecar degrade
    contract, don't invent a new one).

    Medium finding #25: streams both sources directly into master_raw + an incremental (subject,
    type,unit,origin)->Counter aggregator instead of first materializing EVERY measurement row
    (including its free-text context field) into one flat Python list -- unlike build_tables.py's
    per-document streaming, this had no bound, and at 85GB/~40k-file corpus scale the accumulated
    list could grow arbitrarily large before a single byte was written. Peak Python-side memory is
    now O(distinct (subject,type,unit,origin,value) combinations feeding master_filtered), not
    O(total measurement rows) -- except transiently per-group at finalization, when a numeric
    group's distinct values are expanded back out for the median calc (_canonical_core(); bounded
    by that ONE group's own row count, not the whole corpus). Output is exactly equivalent to the
    prior list-based implementation for the null/empty-value edge case (a group whose only rows had
    val in (None,"") still yields an n=0/""/""/"" row) -- the representative-value TIE-BREAK is
    deliberately NOT preserved (see _canonical_core()'s own docstring: it's now a numeric median,
    not Counter.most_common(1)'s arbitrary first-seen pick).

    Masterfile comparison audit (architecture-alignment finding): builds into a temp file via
    safeguard.atomic_sqlite_build() and only swaps it into master_db on a clean exit -- master_db
    itself is never touched by the DROP/CREATE/INSERT sequence below, matching kg.py's build() /
    dedup.py's build() (the exact crash-safety pattern kg.py's own comments describe adopting after
    finding the same bare-DROP-then-late-commit pattern this function used to have could leave
    kg.db permanently half-written on a crash mid-build)."""
    import safeguard
    with safeguard.atomic_sqlite_build(master_db) as (con, _tmp):
        con.executescript(SCHEMA)   # CREATE TABLE IF NOT EXISTS -- the temp file starts empty, no DROP needed

        # subject label map from the authoritative DB
        # v1.13.4: v/m/e=None + finally for all three optional-source connections below -- each used to
        # close() only at the end of its try block, so an execute()/iteration throwing partway (e.g. against
        # a corrupted or partially-written measures.db/enrich.db, left mid-write by a previously killed
        # build -- exactly the scenario safeguard.py's whole premise designs around elsewhere) leaked the
        # connection, which can then block a subsequent rebuild or snapshot/replace targeting the same path.
        doc_veh = {}
        doc_tm = {}
        v = None
        try:
            v = sqlite3.connect("file:%s?mode=ro" % db_path, uri=True)
            for did, veh in v.execute("SELECT id, COALESCE(vehicle,'') FROM documents"):
                doc_veh[did] = (veh or "").strip()
            # Masterfile comparison audit (corroboration-count fix): tm_number, best-effort -- older/
            # synthetic DBs without the column fall back to per-document identity below, never raise.
            try:
                for did, tm in v.execute("SELECT id, COALESCE(tm_number,'') FROM documents"):
                    doc_tm[did] = (tm or "").strip().lower()
            except sqlite3.OperationalError:
                pass
        except Exception:
            pass
        finally:
            if v is not None:
                v.close()

        raw_buf = []                       # small rolling buffer -- flushed periodically, never holds the whole corpus
        groups = defaultdict(Counter)      # (subj,ty,unit,origin) -> Counter({value: count}), None/"" never counted
        bounds = {}                        # (subj,ty,unit,origin) -> (min_numeric, max_numeric) running span
        labels = {}                        # also doubles as the distinct-subjects set (labels.keys())
        corpus_have = defaultdict(set)
        dedup_seen = set()                 # (key, tm-or-doc identity, page) already counted -- see accumulate()
        n_raw = corpus_raw = external_raw = vlmqa_raw = 0
        FLUSH_AT = 2000

        def flush():
            if raw_buf:
                con.executemany(
                    "INSERT INTO master_raw(subject,subject_label,doc,page,type,unit,value,value2,tolerance,context,origin) "
                    "VALUES(?,?,?,?,?,?,?,?,?,?,?)", raw_buf)
                raw_buf.clear()

        def accumulate(subj, label, doc, page, ty, unit, val, val2, tol, ctx, origin, tm=None):
            nonlocal n_raw, corpus_raw, external_raw, vlmqa_raw
            raw_buf.append((subj, label, doc, page, ty, unit, val, val2, tol, ctx, origin))
            if len(raw_buf) >= FLUSH_AT:
                flush()
            labels[subj] = label; n_raw += 1
            if origin == "corpus": corpus_raw += 1
            elif origin == "vlm-verified": vlmqa_raw += 1
            else: external_raw += 1
            key = (subj, ty, unit, origin)
            # Masterfile comparison audit (corroboration-count fix): the corpus holds confirmed
            # duplicate ingestions of the same manual (same pattern procedures_feature.py already
            # dedupes by tm_number, not doc id, for this exact reason) -- and viewer_ingest.py's OCR
            # dedup cache means a re-scanned duplicate page reuses the identical (possibly wrong)
            # cached text. Without this, two duplicate ingestions of one misread page could earn
            # "high -- cited & corroborated", the safest-looking badge in the system, off a single
            # uncorrected error. Count each (TM edition or, absent tm_number, document) x page pair
            # into the group's Counter/bounds only ONCE -- every row still lands in master_raw
            # unchanged, so the raw audit view stays complete; only the FILTERED corroboration count
            # is deduped. External rows have no doc/tm identity worth deduping this way.
            # plan item 13: 'vlm-verified' rows are ALSO doc/page-cited to a real document row (same
            # documents.id/tm_number identity corpus rows use -- build_pageqa.py's pageqa_extractions
            # is keyed on document_id, not tm_number), so the exact same duplicate-ingestion risk
            # applies (two document rows sharing one tm_number, each independently sampled/verified by
            # build_pageqa.py) -- reuses this SAME guard rather than inventing a parallel one.
            if origin in ("corpus", "vlm-verified"):
                ident = tm or ("doc%s" % doc)
                dkey = (key, ident, page)
                if dkey in dedup_seen:
                    return
                dedup_seen.add(dkey)
            counter = groups[key]        # touch the group even for a null/empty value -- matches the
            if val not in (None, ""):    # original's unconditional groups[key].append(val) + _canonical's
                counter[val] += 1        # later filtering, so an all-null group still yields an n=0 row
                n = _num(val)
                if n is not None:
                    lo, hi = bounds.get(key, (n, n))
                    bounds[key] = (min(lo, n), max(hi, n))

        # (1) CORPUS measurements (authoritative), page-cited to the real TM files
        if measures_db and os.path.exists(measures_db):
            m = None
            try:
                m = sqlite3.connect("file:%s?mode=ro" % measures_db, uri=True)
                for doc, page, ty, unit, val, val2, tol, ctx in m.execute(
                        "SELECT doc,page,type,unit,value,value2,tolerance,context FROM meas"):
                    label = doc_veh.get(doc, "") or ("doc%s" % doc)
                    subj = label.strip().lower()
                    corpus_have[subj].add(ty)   # must be complete before the enrich loop below reads it
                    accumulate(subj, label, doc, page, ty, unit, val, val2, tol, ctx, "corpus",
                               tm=doc_tm.get(doc, ""))
            except Exception:
                pass
            finally:
                if m is not None:
                    m.close()

        # (2) EXTERNAL gap-fills (supplemental) -- NO url carried into the Masterfile; only where corpus is silent
        if enrich_db and os.path.exists(enrich_db):
            e = None
            try:
                e = sqlite3.connect("file:%s?mode=ro" % enrich_db, uri=True)
                for subj, label, ty, unit, val, val2, tol, ctx in e.execute(
                        "SELECT subject,subject_label,type,unit,value,value2,tolerance,context FROM ext_meas"):
                    subj = (subj or "").strip().lower()
                    if ty in corpus_have.get(subj, ()):   # corpus wins -> skip
                        continue
                    accumulate(subj, label or subj, None, None, ty, unit, val, val2, tol, ctx, "external")
            except Exception:
                pass
            finally:
                if e is not None:
                    e.close()

        # (3) VLM-VERIFIED page-qa extractions (corroborating), page-cited to the real TM files -- plan
        # item 13. build_pageqa.py (Phase 2's batch driver) writes ONLY verified=True rows to pageqa.db --
        # self-grounded via vlm.ground() AND fuzzy-matched against this page's own already-trusted stored
        # OCR text (pageqa.py's structured/strict path) -- so `WHERE verified=1` below is defense-in-depth,
        # not the only gate (R13: never trust a row's presence alone as proof it was actually verified).
        # Degrades EXACTLY like the measures_db/enrich_db sources above: pageqa_db missing entirely (the
        # common case on a fresh checkout, or before BUILD-PAGEQA.bat has ever been run) or None simply
        # contributes nothing -- same os.path.exists() gate, same try/except/finally shape, no new contract.
        if pageqa_db and os.path.exists(pageqa_db):
            p = None
            try:
                p = sqlite3.connect("file:%s?mode=ro" % pageqa_db, uri=True)
                for doc, page, ty, unit, val, val2, ctx in p.execute(
                        "SELECT document_id,page_number,type,unit,value,value2,source_text "
                        "FROM pageqa_extractions WHERE verified=1"):
                    label = doc_veh.get(doc, "") or ("doc%s" % doc)
                    subj = label.strip().lower()
                    accumulate(subj, label, doc, page, ty, unit, val, val2, None, ctx, "vlm-verified",
                               tm=doc_tm.get(doc, ""))
            except Exception:
                pass
            finally:
                if p is not None:
                    p.close()

        flush()

        # FILTERED layer: one canonical row per (subject,type,unit,origin)
        filt = []
        for (subj, ty, unit, origin), counter in groups.items():
            lo, hi = bounds.get((subj, ty, unit, origin), (None, None))
            rep, low, high, n = _canonical_core(counter, lo, hi)
            auth = 1 if origin == "corpus" else 0
            note = "authoritative (corpus)" if auth else "external reference — unconfirmed"
            filt.append((subj, labels.get(subj, subj), ty, unit, rep, low, high, n, origin, auth, note))
        con.executemany(
            "INSERT INTO master_filtered(subject,subject_label,type,unit,value,low,high,n,origin,authoritative,note) "
            "VALUES(?,?,?,?,?,?,?,?,?,?,?)", filt)

        meta = {"built_ts": str(time.time()), "n_subjects": str(len(labels)), "n_raw": str(n_raw),
                "n_filtered": str(len(filt)), "corpus_raw": str(corpus_raw), "external_raw": str(external_raw),
                "vlmqa_raw": str(vlmqa_raw)}
        con.executemany("INSERT OR REPLACE INTO master_meta(k,v) VALUES(?,?)", list(meta.items()))
        con.commit()

    if md_path:
        _export_md(master_db, md_path, meta)
    # Deliberately NOT adding a "vlm_verified" key here (unlike the meta table's own vlmqa_raw entry
    # above): test_medium_fixes.py's masterfile_streaming_equivalent_to_original_10_trials diff-oracle
    # compares this exact return dict against a from-scratch reference dict via plain `!=` -- an extra
    # key here would break that comparison for every trial even when every value it DOES share matches,
    # for a count that oracle never claimed to compute. The vlm-verified raw count is fully available
    # via master_meta (k='vlmqa_raw') and via master_filtered/master_raw's own origin='vlm-verified'
    # rows -- no information is actually lost, only kept out of this one dict's shape.
    return {"subjects": len(labels), "raw": n_raw, "filtered": len(filt),
            "corpus": corpus_raw, "external": external_raw}


def _export_md(master_db, md_path, meta):
    con = sqlite3.connect("file:%s?mode=ro" % master_db, uri=True); con.row_factory = sqlite3.Row
    subs = [r[0] for r in con.execute("SELECT DISTINCT subject FROM master_filtered ORDER BY subject")]
    lines = ["# THE VIEWER — MASTERFILE (consolidated measurement & dimensional data)", "",
             "One congruent view of every measured value in the project: the corpus's **authoritative** figures "
             "(cited to the manual page) merged with **external** supplemental values that only fill gaps the manuals "
             "leave open. No external links are shown — external provenance is kept internally for audit.", "",
             "Built: %s · subjects: %s · raw values: %s (corpus %s / external %s) · filtered rows: %s" % (
                 meta.get("built_ts", ""), meta.get("n_subjects", ""), meta.get("n_raw", ""),
                 meta.get("corpus_raw", ""), meta.get("external_raw", ""), meta.get("n_filtered", "")), "", "---", ""]
    for subj in subs:
        lbl = con.execute("SELECT subject_label FROM master_filtered WHERE subject=? LIMIT 1", (subj,)).fetchone()
        lines.append("## %s" % (lbl[0] if lbl else subj))
        for r in con.execute("SELECT type,unit,value,low,high,n,origin,note FROM master_filtered "
                             "WHERE subject=? ORDER BY authoritative DESC, type", (subj,)):
            span = (" (range %s–%s)" % (r["low"], r["high"])) if r["low"] and r["high"] and r["low"] != r["high"] else ""
            tag = "" if r["origin"] == "corpus" else "  _[external — unconfirmed]_"
            lines.append("- **%s**: %s %s%s  · n=%s%s" % (r["type"], r["value"], r["unit"], span, r["n"], tag))
        lines.append("")
    con.close()
    open(md_path, "w", encoding="utf-8").write("\n".join(lines) + "\n<!-- END OF FILE -->\n")


def for_subject(master_db, q, limit=400):
    """Read the Masterfile for one subject -- NO links. Returns {query, filtered, raw, counts} where filtered and raw
    are lists of measurement rows.

    Masterfile comparison audit (architecture-alignment finding): the os.path.exists() gate below
    already matched kg.neighbors()'s/dedup.editions_for()'s "sidecar not built yet -> empty result"
    contract, but a master_db that EXISTS in a mid-build/torn state (a real reachable state before
    the atomic-write fix above) used to raise sqlite3.OperationalError straight out of this
    function, uncaught, and leak the connection -- kg.py/dedup.py both guard exactly this case
    (\"a db from before this schema existed, or mid-build -- degrade, never 500\"). Matched here too."""
    q = (q or "").strip()
    if not master_db or not os.path.exists(master_db) or len(q) < 2:
        return {"query": q, "filtered": [], "raw": [], "counts": {}}
    subj = q.lower()
    con = sqlite3.connect("file:%s?mode=ro" % master_db, uri=True); con.row_factory = sqlite3.Row
    try:
        filt = [dict(r) for r in con.execute(
            "SELECT type,unit,value,low,high,n,origin,authoritative,note,subject_label FROM master_filtered "
            "WHERE subject=? OR subject LIKE ? ORDER BY authoritative DESC, type LIMIT ?",
            (subj, "%" + subj + "%", limit))]
        raw = [dict(r) for r in con.execute(
            "SELECT type,unit,value,value2,tolerance,context,doc,page,origin FROM master_raw "
            "WHERE subject=? OR subject LIKE ? ORDER BY origin, type LIMIT ?",
            (subj, "%" + subj + "%", limit))]
    except sqlite3.OperationalError:
        return {"query": q, "filtered": [], "raw": [], "counts": {}}
    finally:
        con.close()
    counts = {"corpus": sum(1 for r in raw if r["origin"] == "corpus"),
              "external": sum(1 for r in raw if r["origin"] == "external"),
              "vlm-verified": sum(1 for r in raw if r["origin"] == "vlm-verified")}
    # add a page pointer to the authoritative file -- corpus rows AND vlm-verified rows both carry a real
    # doc/page citation (pageqa.py's structured/strict path only ever writes a row after self-grounding it
    # AND cross-checking it against that exact page's own stored OCR text, see build()'s v1.2.0 note above),
    # so a reader can click through and visually confirm either one; 'external' rows have no doc/page at
    # all (a Wayback-sourced value, cited by URL instead) and correctly get no internal page reference.
    for r in raw:
        r["page_url"] = ("/deepzoom?doc=%s&page=%s" % (r["doc"], r["page"])) \
            if r["origin"] in ("corpus", "vlm-verified") and r["doc"] else ""
    # enrich filtered rows at READ time (no rebuild): dual-unit display + a wide-variance flag
    try:
        import units
    except Exception:
        units = None
    for f in filt:
        f["alt"] = units.dual(f.get("value"), f.get("unit")) if units else ""
        f["system"] = units.system_of(f.get("unit")) if units else ""
        f["spread"] = _spread(f)
        f["confidence"] = _confidence(f)
    return {"query": q, "filtered": filt, "raw": raw, "counts": counts}


def _confidence(f):
    """A pragmatic trust score per dimension (no per-method tracking needed): authoritative + multiple agreeing samples
    = high; authoritative single sample = medium; sources disagree widely = review; external = low. Returns one of
    'high' | 'medium' | 'review' | 'low'."""
    if not f.get("authoritative"):
        return "low"                      # external reference, unconfirmed
    if f.get("spread") == "wide":
        return "review"                   # corpus values disagree -> needs a human check
    return "high" if (f.get("n") or 0) >= 2 else "medium"


def _spread(f):
    """Flag a filtered row whose sampled values disagree widely (high-low span > 25% of the representative). Signals a
    dimension where sources/variants differ and the reader should check which one applies. Returns '' or 'wide'."""
    try:
        lo = float(str(f.get("low")).replace(",", "")); hi = float(str(f.get("high")).replace(",", ""))
        rep = float(str(f.get("value")).replace(",", "")) or 1.0
        if hi > lo and (hi - lo) > 0.25 * abs(rep) and (f.get("n") or 0) > 1:
            return "wide"
    except Exception:
        pass
    return ""


def coverage(master_db, limit=2000):
    """Gap dashboard: for every subject in the Masterfile, how many dimension types are covered and which of the 13 are
    still MISSING (no value at all). Read-only, no links. Returns a list of
    {subject,label,n,corpus,external,missing} dicts where missing is the list of dimension types with no value."""
    dims = ("length", "area", "angle", "weight", "force", "torque", "pressure",
            "capacity", "electrical", "temperature", "flow", "speed", "rotation")
    out = []
    if not master_db or not os.path.exists(master_db):
        return out
    # Masterfile comparison audit (architecture-alignment finding): same OperationalError/finally
    # guard as for_subject() above, for the same reason -- a mid-build/torn master_db must degrade
    # to an empty list here too, not raise/leak, matching kg.py's/dedup.py's read-side contract.
    con = sqlite3.connect("file:%s?mode=ro" % master_db, uri=True); con.row_factory = sqlite3.Row
    try:
        subs = con.execute("SELECT DISTINCT subject, subject_label FROM master_filtered ORDER BY subject").fetchall()
        for s in subs[:limit]:
            rows = con.execute("SELECT type, origin, authoritative FROM master_filtered WHERE subject=?",
                               (s["subject"],)).fetchall()
            have = {r["type"] for r in rows}
            out.append({"subject": s["subject"], "label": s["subject_label"],
                        "n": len(have), "corpus": sum(1 for r in rows if r["authoritative"]),
                        "external": sum(1 for r in rows if not r["authoritative"]),
                        "missing": [d for d in dims if d not in have]})
    except sqlite3.OperationalError:
        return []
    finally:
        con.close()
    return out


if __name__ == "__main__":
    import tempfile
    d = tempfile.mkdtemp()
    dbp = os.path.join(d, "viewer.db"); mdb = os.path.join(d, "measures.db")
    edb = os.path.join(d, "enrich.db"); mf = os.path.join(d, "masterfile.db")
    # authoritative DB
    a = sqlite3.connect(dbp)
    a.execute("CREATE TABLE documents(id INTEGER PRIMARY KEY, vehicle TEXT, tm_number TEXT)")
    a.executemany("INSERT INTO documents VALUES(?,?,?)", [
        (1, "HMMWV", "TM9-2320-280-24-1"), (2, "HMMWV", "TM9-2320-280-24-2"),
        (3, "HMMWV", "TM9-2320-280-24-3"), (4, "HMMWV", "TM9-2320-280-24-4"),
        (5, "HMMWV", "TM9-2320-280-24-5"),
        # docs 6/7: two SEPARATE document rows (two ingestions) of the SAME manual edition -- the
        # real scenario the corroboration-count fix targets, distinct from the doc-1-referenced-twice
        # case below.
        (6, "HMMWV", "TM9-2320-280-24-6"), (7, "HMMWV", "TM9-2320-280-24-6")])
    a.commit(); a.close()
    # corpus measures: HMMWV has length + weight (authoritative)
    m = sqlite3.connect(mdb)
    m.execute("CREATE TABLE meas(doc INT,page INT,type TEXT,unit TEXT,value TEXT,value2 TEXT,tolerance TEXT,context TEXT)")
    m.executemany("INSERT INTO meas VALUES(?,?,?,?,?,?,?,?)", [
        (1, 12, "length", "in", "180", None, None, "Overall length 180 in"),
        (1, 12, "length", "in", "180", None, None, "len 180 in (dup)"),
        (1, 20, "weight", "lb", "7700", None, None, "Curb weight 7700 lb"),
        # torque: 4 genuinely different real values, deliberately NOT all-distinct (100 appears
        # twice) so the OLD mode-on-string pick and the NEW numeric-median pick provably diverge --
        # mode would pick "100" (count=2, the only repeated value); median of [100,100,105,200]
        # sorted is (100+105)/2 = 102.5, a real statistical center none of the four rows even states.
        (2, 5, "torque", "ft-lb", "100", None, None, "Torque 100 ft-lb (doc 2)"),
        (3, 5, "torque", "ft-lb", "100", None, None, "Torque 100 ft-lb (doc 3, repeat)"),
        (4, 5, "torque", "ft-lb", "105", None, None, "Torque 105 ft-lb (doc 4)"),
        (5, 5, "torque", "ft-lb", "200", None, None, "Torque 200 ft-lb (doc 5, outlier)"),
        # pressure: docs 6 and 7 are two DISTINCT document rows sharing one tm_number -- a duplicate
        # ingestion of the same manual reporting the identical (possibly misread) value. Pre-fix this
        # would count n=2 and earn "high -- cited & corroborated"; post-fix it dedupes to n=1.
        (6, 30, "pressure", "psi", "40", None, None, "Tire pressure 40 psi"),
        (7, 30, "pressure", "psi", "40", None, None, "Tire pressure 40 psi (duplicate ingestion)")])
    m.commit(); m.close()
    # external enrich: capacity (gap) + weight (corpus already has -> must be dropped)
    e = sqlite3.connect(edb)
    e.execute("CREATE TABLE ext_meas(subject TEXT,subject_label TEXT,type TEXT,unit TEXT,value TEXT,value2 TEXT,"
              "tolerance TEXT,context TEXT,source TEXT,source_url TEXT,orig_url TEXT,wayback_ts TEXT,fetched_ts REAL,"
              "confidence REAL,status TEXT)")
    e.executemany("INSERT INTO ext_meas(subject,subject_label,type,unit,value,context,source_url) VALUES(?,?,?,?,?,?,?)", [
        ("hmmwv", "HMMWV", "capacity", "gal", "25", "Fuel 25 gal", "http://web.archive.org/x"),
        ("hmmwv", "HMMWV", "weight", "lb", "9999", "bogus weight", "http://web.archive.org/y")])
    e.commit(); e.close()

    summ = build(dbp, mdb, edb, mf, md_path=os.path.join(d, "MASTERFILE.md"))
    print("summary:", summ)
    res = for_subject(mf, "HMMWV")
    ftypes = {(f["type"], f["origin"]) for f in res["filtered"]}
    assert ("length", "corpus") in ftypes and ("weight", "corpus") in ftypes, "corpus rows missing"
    assert ("capacity", "external") in ftypes, "external gap-fill missing"
    assert ("weight", "external") not in ftypes, "corpus-authoritative filter failed (external weight leaked)"
    # no links exposed in filtered/raw payloads
    blob = repr(res["filtered"]) + repr([{k: v for k, v in r.items() if k != "page_url"} for r in res["raw"]])
    assert "http://" not in blob and "web.archive" not in blob, "a link leaked into the Masterfile view"
    # corpus rows point to the authoritative file (internal page ref), external rows do not
    assert any(r["page_url"] for r in res["raw"] if r["origin"] == "corpus"), "corpus page ref missing"
    assert all(not r["page_url"] for r in res["raw"] if r["origin"] == "external"), "external row must have no ref"
    # Masterfile comparison audit (data-consistency fix): the representative value is now a real
    # numeric median, not an arbitrary first-seen-string tiebreak -- torque's 4 rows (100,100,105,200)
    # median to 102.5, a number NONE of the 4 individual manuals even states, proving this isn't
    # just "whichever document got scanned first" (the old algorithm would have picked "100").
    torque = next(f for f in res["filtered"] if f["type"] == "torque")
    assert torque["value"] == "102.5", ("median fix regressed -- got %r, want '102.5'" % torque["value"], torque)
    assert torque["low"] == "100" and torque["high"] == "200" and torque["n"] == 4, torque
    # a group with only ONE distinct value (length: "180" x2) is unaffected -- median of a single
    # repeated value is trivially that value, same as the old mode pick would have given.
    length = next(f for f in res["filtered"] if f["type"] == "length")
    assert length["value"] == "180", length
    # Masterfile comparison audit (corroboration-count fix): the length rows are the SAME document
    # (doc 1) referenced twice -- dedupes to n=1, not the raw row count of 2.
    assert length["n"] == 1, ("corroboration-count fix regressed for same-doc duplicate rows", length)
    # the pressure rows are TWO DIFFERENT document rows (docs 6/7) sharing one tm_number -- a real
    # duplicate ingestion of the same manual edition. Pre-fix this earned n=2 / "high -- cited &
    # corroborated" off a single value repeated by one re-scanned manual; post-fix it dedupes to n=1
    # and drops to "medium" (authoritative single sample), which is the honest read.
    pressure = next(f for f in res["filtered"] if f["type"] == "pressure")
    assert pressure["n"] == 1, ("corroboration-count fix regressed for cross-doc same-tm_number "
                                 "duplicate ingestion", pressure)
    assert pressure["confidence"] == "medium", ("a duplicate ingestion must not earn 'high' off one "
                                                 "uncorroborated value", pressure)

    # --------------------------------------------------------------------------------------------- #
    # plan item 13: pageqa.db as a new, OPTIONAL corroborating source (tagged origin='vlm-verified'). #
    # --------------------------------------------------------------------------------------------- #

    def _vlmqa_raw_meta(master_db_path):
        # master_meta's own 'vlmqa_raw' entry (written alongside n_subjects/corpus_raw/etc.) -- the raw
        # vlm-verified count is deliberately NOT added to build()'s own return dict (see build()'s own
        # comment just above its `return` -- test_medium_fixes.py's diff-oracle compares that exact dict
        # via plain `!=` against a from-scratch reference that predates pageqa.db and would break on any
        # extra key), so this self-test reads the count the same way any OTHER real caller would: from
        # master_meta, or by counting origin='vlm-verified' rows directly (both exercised below).
        c = sqlite3.connect(master_db_path)
        try:
            r = c.execute("SELECT v FROM master_meta WHERE k='vlmqa_raw'").fetchone()
            return int(r[0]) if r else None
        finally:
            c.close()

    # pageqa_db never passed at all (`summ` above) -- the common case on a fresh checkout, before this
    # kwarg existed for any caller -- must contribute nothing and must not change any prior behavior.
    assert _vlmqa_raw_meta(mf) == 0, ("pageqa_db omitted must contribute nothing", _vlmqa_raw_meta(mf))
    assert not any(f["origin"] == "vlm-verified" for f in res["filtered"]), \
        "no vlm-verified rows should exist when pageqa_db was never passed"

    # pageqa_db passed but pointing at a path that doesn't exist yet (BUILD-PAGEQA.bat never run) --
    # same os.path.exists() gate measures_db/enrich_db already use -- must ALSO degrade cleanly, never
    # raise. Different code path than simply omitting the kwarg (above): pageqa_db is truthy here.
    build(dbp, mdb, edb, mf, pageqa_db=os.path.join(d, "nope_pageqa.db"))
    assert _vlmqa_raw_meta(mf) == 0, \
        ("a missing pageqa.db path must contribute nothing, not raise", _vlmqa_raw_meta(mf))

    # pageqa.db PRESENT with a real verified row -- must show up as its OWN corroborating origin,
    # never silently merged into or overriding the 'corpus' group's own count/note/confidence badge.
    pqdb = os.path.join(d, "pageqa.db")
    pq = sqlite3.connect(pqdb)
    pq.execute("""CREATE TABLE pageqa_extractions(
        id INTEGER PRIMARY KEY, document_id INTEGER, page_number INTEGER, type TEXT, value TEXT,
        value2 TEXT, unit TEXT, region_x0 REAL, region_y0 REAL, region_x1 REAL, region_y1 REAL,
        source_text TEXT, answer_text TEXT, verified INTEGER, backend TEXT, extracted_at REAL)""")
    pq.executemany(
        "INSERT INTO pageqa_extractions(document_id,page_number,type,value,value2,unit,source_text,"
        "answer_text,verified,backend,extracted_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)", [
            # doc 1 (HMMWV) -- a dimension type (capacity) the corpus's own measures.db never
            # extracted on this page: the common real case build_pageqa.py's own candidate sampling
            # targets (a page measures.py/tables.py/RPSTL found nothing on).
            (1, 40, "capacity", "40", None, "qt", "Coolant capacity is 40 qt.",
             "Coolant capacity is 40 qt.", 1, "fake_vlm_backend", 1000.0),
            # docs 6/7 (HMMWV) -- the SAME duplicate-ingestion scenario the pressure rows above already
            # prove for 'corpus': two document rows sharing one tm_number, each independently verified
            # by build_pageqa.py on their own page_number -- must dedupe to n=1, not n=2.
            (6, 50, "electrical", "12", None, "V", "System voltage is 12V.",
             "System voltage is 12V.", 1, "fake_vlm_backend", 1000.0),
            (7, 50, "electrical", "12", None, "V", "System voltage is 12V. (duplicate ingestion)",
             "System voltage is 12V. (duplicate ingestion)", 1, "fake_vlm_backend", 1000.0),
            # an UNVERIFIED row (verified=0) -- must NEVER be picked up. build_pageqa.py itself never
            # actually writes one (only verified=True rows are ever inserted), so this is
            # defense-in-depth on masterfile.py's own `WHERE verified=1` filter, not a re-test of
            # build_pageqa.py's own write gate.
            (1, 41, "weight", "99999", None, "lb", "Bogus unverified weight claim.",
             "Bogus unverified weight claim.", 0, "fake_vlm_backend", 1000.0)])
    pq.commit(); pq.close()

    build(dbp, mdb, edb, mf, md_path=os.path.join(d, "MASTERFILE2.md"), pageqa_db=pqdb)
    assert _vlmqa_raw_meta(mf) == 3, ("expected 3 raw vlm-verified rows (1 capacity + 2 electrical, "
                                       "unverified excluded)", _vlmqa_raw_meta(mf))
    res2 = for_subject(mf, "HMMWV")
    ftypes2 = {(f["type"], f["origin"]) for f in res2["filtered"]}
    assert ("capacity", "vlm-verified") in ftypes2, "vlm-verified capacity row missing"
    assert ("electrical", "vlm-verified") in ftypes2, "vlm-verified electrical row missing"
    assert ("weight", "vlm-verified") not in ftypes2, \
        "an unverified (verified=0) pageqa row must never reach the Masterfile"
    # corpus's own torque/length/weight groups are completely unaffected by pageqa.db's presence --
    # 'vlm-verified' is its own group, never merged into 'corpus'.
    assert ("length", "corpus") in ftypes2 and ("weight", "corpus") in ftypes2, \
        "adding pageqa.db must not disturb the existing corpus groups"
    capacity_vlm = next(f for f in res2["filtered"] if f["type"] == "capacity" and f["origin"] == "vlm-verified")
    assert capacity_vlm["value"] == "40" and capacity_vlm["unit"] == "qt", capacity_vlm
    electrical_vlm = next(f for f in res2["filtered"] if f["type"] == "electrical" and f["origin"] == "vlm-verified")
    assert electrical_vlm["n"] == 1, ("duplicate-ingestion dedup must apply to vlm-verified rows too, "
                                       "exactly like it already does for corpus rows", electrical_vlm)
    # no link ever leaks in from a vlm-verified row either, same invariant as the corpus/external check.
    blob2 = repr(res2["filtered"])
    assert "http://" not in blob2, "a link leaked into a vlm-verified Masterfile row"

    # adversarial-review finding (found live): a vlm-verified row IS page-cited to a real document/page --
    # build_pageqa.py only ever writes one after self-grounding + an OCR cross-check against that exact
    # page (pageqa.py's own structured/strict path) -- so it deserves the same deep-link click-through a
    # corpus row gets, exactly the kind of "go check it yourself" affordance R13 wants for an AI-sourced
    # tier. for_subject() originally only built page_url for origin=='corpus', silently leaving every
    # vlm-verified row un-clickable despite carrying a perfectly real doc/page; fixed to include both.
    assert any(r["page_url"] for r in res2["raw"] if r["origin"] == "vlm-verified"), \
        "vlm-verified rows are page-cited exactly like corpus rows -- page_url must not be silently empty"
    vlm_ref = next(r for r in res2["raw"] if r["origin"] == "vlm-verified")
    assert vlm_ref["page_url"] == "/deepzoom?doc=%s&page=%s" % (vlm_ref["doc"], vlm_ref["page"]), vlm_ref
    # counts must tally vlm-verified rows too, not silently omit them from a "N corpus / M external"-style
    # summary the way the pre-fix dict shape would have (counts only ever had "corpus"/"external" keys).
    assert res2["counts"]["vlm-verified"] == 3, ("counts must tally raw vlm-verified rows too", res2["counts"])

    print("masterfile self-test OK (merge, corpus-authoritative, no links surfaced, authoritative page "
          "refs kept, numeric-median representative value, duplicate-ingestion corroboration-count fix, "
          "vlm-verified pageqa.db source: absent/missing degrades cleanly, present contributes its own "
          "corroborating origin without disturbing corpus groups, unverified rows excluded, cross-doc "
          "same-tm_number duplicate ingestion deduped exactly like corpus rows already are, page_url + "
          "counts correctly include vlm-verified rows alongside corpus)")
# END OF FILE
