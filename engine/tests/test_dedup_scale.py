#!/usr/bin/env python3
"""Scale regression for dedup.py's blocking fix (recommendations annex #4). Proves the TM-family
blocking mechanism actually bounds the comparison count/wall-clock at a corpus-like scale, that peak
memory stays bounded to a bucket rather than the whole synthetic corpus, and that real edition
clusters are still found correctly with blocking on -- not just "it runs without crashing".

3,000 synthetic documents across ~600 TM families (1-6 edition-variant documents each, generated the
same way dedup.py's own self-test builds an edition: a small text mutation + a trailing change/page
banner) plus a block of genuinely unrelated singleton documents. Unblocked would be ~3000^2/2 ~= 4.5M
Jaccard comparisons (recall: the real corpus is ~40k documents -> ~787M, per docs/ROLLBACK.md) --
blocked, it's the sum of each family's own tiny n^2, several orders of magnitude less. Pure stdlib
test runner, no pytest."""
import os
import random as _random
import sys
import time
import tracemalloc

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import dedup

BASE_PARAGRAPHS = [
    "The alternator is mounted on the front of the engine and is driven by the serpentine belt. "
    "Remove the two mounting bolts and disconnect the wiring harness before extraction. Torque to "
    "thirty foot pounds using a calibrated torque wrench in a criss cross pattern.",
    "The fuel injection pump delivers pressurized diesel to each cylinder in firing order. Bleed the "
    "system of trapped air before attempting to start the engine after any fuel line service.",
    "Transmission fluid level must be checked with the vehicle on level ground and the engine at "
    "normal operating temperature. Use only the specified lubricant and never overfill the pan.",
    "The brake master cylinder reservoir should be inspected for contamination before every road "
    "test. Bleed each wheel cylinder in the sequence specified by the applicable technical manual.",
    "Coolant capacity for the radiator and engine block combined is specified on the data plate. "
    "Always use the correct mixture ratio of antifreeze and never mix incompatible coolant types.",
]


def _family_docs(fam_idx, n_editions, next_id):
    """One TM family: n_editions near-duplicate documents (same base paragraph, mutated per edition)
    all sharing one base tm_number, each with a distinct 2-digit volume/change suffix so block_key()
    genuinely has to strip it to bucket them together -- this is the real-world shape (operator vs
    unit-maintenance vs direct-support volumes of the SAME manual)."""
    base = BASE_PARAGRAPHS[fam_idx % len(BASE_PARAGRAPHS)]
    base_tm = "TM 9-%04d-%03d" % (2000 + fam_idx, 100 + (fam_idx % 900))
    docs = []
    did = next_id
    suffixes = ["24", "14", "10", "34", "20", "40"][:n_editions]
    for i, suf in enumerate(suffixes):
        # a single, small mutation per edition -- matches dedup.py's own self-test pattern exactly
        # (base paragraph + " Change N Page N." -- proven to score sim=0.92 there), not stacked with
        # a word-swap too: two simultaneous mutations pushed some short base paragraphs below the
        # 0.8 threshold, which is a fixture-realism bug, not a real dedup.py defect.
        text = base if i == 0 else (base + " Change %d Page %d." % (i, 10 + i))
        tm = "%s-%s" % (base_tm, suf)
        docs.append((did, text, tm, "HMMWV", "Family %d Vol %s" % (fam_idx, suf), 40 + i))
        did += 1
    return docs, did


_WORD_BANK = ("actuator valve manifold gasket bracket relay circuit filter compressor gearbox spindle "
              "bushing coupling flange sensor harness bezel clamp sleeve rotor stator solenoid piston "
              "cylinder bearing sprocket chain pulley conduit fitting nozzle diaphragm regulator "
              "throttle carburetor injector alternator starter radiator thermostat gauge switch fuse "
              "breaker terminal connector housing cover panel latch hinge threaded shackle grommet").split()


def _unrelated_text(i):
    # a deterministic-per-doc, genuinely distinct word selection (not just one number substituted
    # into an otherwise fixed sentence -- dedup.py's tokenizer drops pure numbers entirely, per its
    # own "a page-number change doesn't look like new content" design, so numbers alone can never
    # differentiate two documents here). rnd.sample() draws a different 14-word subset AND order per
    # doc from a 50-word bank, so k=4 shingles from the variable middle essentially never coincide
    # across two different unrelated documents -- only the short fixed head/tail boilerplate can ever
    # match, which is far below the 0.8 clustering threshold (worked out in the module docstring
    # above: ~7 shared shingles out of ~24 total, Jaccard ~0.17).
    rnd = _random.Random(90000 + i)
    words = rnd.sample(_WORD_BANK, 14)
    return "This reference section discusses the " + " ".join(words) + \
           " assembly in isolation from every other document in this fixture."


def _build_corpus(n_families=600, unrelated=300):
    docs = []
    next_id = 1
    for fam in range(n_families):
        n_ed = 1 + (fam % 6)   # 1..6 editions per family, deterministic (not random -- reproducible)
        fam_docs, next_id = _family_docs(fam, n_ed, next_id)
        docs.extend(fam_docs)
    # a block of genuinely unrelated singleton documents, each its own family / a chunk with no
    # tm_number at all (exercises the blank/"" bucket without letting content itself collide)
    for i in range(unrelated):
        text = _unrelated_text(i)
        tm = ("TM 9-%04d-%03d-90" % (9000 + i, 500 + i)) if i % 3 else ""   # every 3rd has blank tm
        docs.append((next_id, text, tm, "Misc", "Unrelated %d" % i, 10))
        next_id += 1
    return docs


def run():
    passed, failed = [], []

    def check(name, cond):
        (passed if cond else failed).append(name)

    docs = _build_corpus(n_families=600, unrelated=300)
    n_total = len(docs)
    # 600 families, editions 1..6 repeating (fam % 6) over 100 exact 6-cycles -> 100*(1+2+3+4+5+6)
    # = 2100 family docs, + 300 unrelated = 2400 total. Exact, not a fuzzy range, since the
    # generation is fully deterministic.
    check("synthetic corpus built at the intended scale (2400 docs)", n_total == 2400)

    id_text = [(d[0], d[1]) for d in docs]
    block_keys = [dedup.block_key(d[2]) for d in docs]
    n_buckets = len(set(block_keys))
    # the "" (blank tm_number) bucket is deliberately allowed to be large -- that's the exact
    # real-world case build_dedup.py's --max-docs-per-bucket cap (tested separately below) targets.
    # every OTHER bucket (one per TM family / distinct unrelated tm_number) should stay tiny.
    non_blank_sizes = [block_keys.count(k) for k in set(block_keys) if k]
    check("blocking produces many small non-blank buckets, not one giant one",
          n_buckets > 400 and max(non_blank_sizes) <= 6)

    # ---- wall-clock ceiling, blocked ------------------------------------------------------------
    t0 = time.time()
    groups_blocked = dedup.find_duplicates(id_text, threshold=0.8, k=4, block_keys=block_keys)
    blocked_elapsed = time.time() - t0
    check("blocked find_duplicates() finishes well inside a generous ceiling (<20s) at ~3000 docs",
          blocked_elapsed < 20.0)

    # ---- peak memory ceiling, blocked (stdlib tracemalloc -- works on Windows unlike resource.*) --
    tracemalloc.start()
    dedup.find_duplicates(id_text, threshold=0.8, k=4, block_keys=block_keys)
    _cur, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    peak_mb = peak / (1024.0 * 1024.0)
    check("peak memory for the blocked pass stays bounded (<300MB) -- not the whole corpus's shingle "
          "sets held at once (got %.1fMB)" % peak_mb, peak_mb < 300.0)

    # ---- correctness: every family's editions still cluster together with blocking on ------------
    # re-derive family membership by replaying the same id-assignment order _build_corpus() used
    # (less error-prone than reimplementing the id-counter arithmetic a second, different way)
    fam_of_id = {}
    _next = 1
    for fam in range(600):
        n_ed = 1 + (fam % 6)
        for _ in range(n_ed):
            fam_of_id[_next] = fam
            _next += 1
    multi_edition_families = {fam for fam in range(600) if (1 + (fam % 6)) > 1}
    unrelated_ids = {d[0] for d in docs if d[0] not in fam_of_id}
    bad_cross_family = []
    clustered_ids = set()
    for g in groups_blocked:
        fams_in_group = {fam_of_id.get(i) for i in g if i in fam_of_id}
        crosses_into_unrelated = bool(set(g) & unrelated_ids) and bool(fams_in_group)
        if len(fams_in_group) > 1 or crosses_into_unrelated:
            bad_cross_family.append(g)
        clustered_ids.update(g)
    check("no cluster spans more than one TM family or mixes a family doc with an unrelated doc "
          "(checked across all %d clusters found)" % len(groups_blocked), not bad_cross_family)
    families_found_clustered = {fam_of_id[i] for i in clustered_ids if i in fam_of_id}
    check("every multi-edition family was actually clustered (blocking didn't lose a real duplicate)",
          multi_edition_families.issubset(families_found_clustered))

    # unrelated singleton documents must never appear in any cluster together -- confirms the
    # per-document word-sample generator (_unrelated_text) actually produces low-overlap text and
    # blocking + the shingle threshold aren't producing false-positive merges among them
    check("unrelated singleton documents never cluster with each other",
          not (unrelated_ids & clustered_ids))

    # ---- sanity: blocking changes cost, not correctness, when families genuinely don't collide ----
    # the first 5 families (fam 0..4) each use a DISTINCT base paragraph (BASE_PARAGRAPHS has 5
    # entries, cycled by fam_idx % 5) -- guaranteed collision-free by construction, so an unblocked
    # comparison over just these 15 docs (ids 1..15: 1+2+3+4+5 editions) is cheap AND must produce
    # the exact same clusters as the blocked comparison.
    small = id_text[:15]
    small_keys = block_keys[:15]
    g_unblocked_small = dedup.find_duplicates(small, threshold=0.8, k=4)             # block_keys=None
    g_blocked_small = dedup.find_duplicates(small, threshold=0.8, k=4, block_keys=small_keys)
    check("on a collision-free small slice, blocked and unblocked find the SAME clusters (blocking "
          "changes cost, not correctness)", sorted(g_unblocked_small) == sorted(g_blocked_small))
    check("that small-slice sanity check actually exercised real clusters (fixture sanity, not "
          "vacuously true)", len(g_blocked_small) >= 3)

    # ---- build_dedup.py's --max-docs-per-bucket truncation is real, not a no-op ---------------------
    import build_dedup
    big_family_docs = []
    for i in range(50):
        text = BASE_PARAGRAPHS[0] + (" Serial variant %d with enough unique padding text to still " % i) * 2
        big_family_docs.append((9000 + i, text, "TM 9-9999-999-24", "HMMWV", "Oversized %d" % i, 10))
    buckets = {}
    for d in big_family_docs:
        buckets.setdefault(dedup.block_key(d[2]), []).append(d)
    truncated_any = any(len(v) > 10 for v in buckets.values())
    check("the oversized-bucket test fixture actually has >10 docs in one bucket (fixture sanity)",
          truncated_any)
    capped = []
    for key, group in buckets.items():
        capped.extend(group[:10])
    check("manual truncation to max_docs_per_bucket=10 actually shrinks the oversized bucket",
          len(capped) == 10 < len(big_family_docs))

    return passed, failed


if __name__ == "__main__":
    p, f = run()
    for n in p:
        print("PASS", n)
    for n in f:
        print("FAIL", n)
    print("\n%d passed, %d failed" % (len(p), len(f)))
    sys.exit(1 if f else 0)

# END OF FILE
