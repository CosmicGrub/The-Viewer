#!/usr/bin/env python3
"""THE VIEWER -- EDITION / DUPLICATE DETECTION (v1.3.2, catalog §7.1). The corpus holds many editions of the same TM
(same content, different change number / print date) and outright duplicates. This fingerprints a document's text with
word-shingles and measures Jaccard similarity, so near-identical editions cluster together -- letting the app prefer the
latest edition, de-duplicate search hits, and correlate change history. Pure stdlib; read-only. Corpus authoritative
(nothing is deleted -- duplicates are just linked)."""
import re
import zlib

_WORD = re.compile(r"[a-z]{3,}")


def _tokens(text):
    # lowercase words >=3 letters; drop pure numbers so a page-number change doesn't look like new content
    return _WORD.findall((text or "").lower())


def _stable_hash(s):
    # zlib.crc32, not the builtin hash() -- str hash() is PYTHONHASHSEED-randomized per process
    # by default (medium finding #22, same bug already fixed in embed.py's HASH_ALGO_VERSION
    # path). Currently latent since find_duplicates() has no caller yet, but a shingle set
    # computed in one process and compared/persisted from another would otherwise never agree.
    return zlib.crc32(s.encode("utf-8"))


def shingles(text, k=4):
    """Set of k-word shingles (as hashes) -- the document fingerprint."""
    toks = _tokens(text)
    if len(toks) < k:
        return frozenset(_stable_hash(t) for t in toks)
    return frozenset(_stable_hash(" ".join(toks[i:i + k])) for i in range(len(toks) - k + 1))


def jaccard(a, b):
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    inter = len(a & b)
    return inter / float(len(a) + len(b) - inter)


def similarity(t1, t2, k=4):
    return round(jaccard(shingles(t1, k), shingles(t2, k)), 3)


def find_duplicates(docs, threshold=0.8, k=4):
    """`docs` = [(id, text)]. Returns clusters [[id,...]] of near-duplicate / same-edition documents (similarity >=
    threshold). Singletons are omitted. O(n^2) -- fine for a sidecar builder over the corpus."""
    sigs = [(i, shingles(t, k)) for i, t in docs]
    n = len(sigs)
    parent = {i: i for i, _ in sigs}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]; x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra
    for a in range(n):
        ia, sa = sigs[a]
        for b in range(a + 1, n):
            ib, sb = sigs[b]
            if jaccard(sa, sb) >= threshold:
                union(ia, ib)
    groups = {}
    for i, _ in sigs:
        groups.setdefault(find(i), []).append(i)
    return [sorted(g) for g in groups.values() if len(g) > 1]


if __name__ == "__main__":
    base = ("The alternator is mounted on the front of the engine and is driven by the serpentine belt. "
            "Remove the two mounting bolts and disconnect the wiring harness before extraction. Torque to 30 foot pounds.")
    edition = base.replace("30 foot pounds", "35 foot pounds") + " Change 3 Page 12."   # tiny edit + page banner
    other = ("The transmission fluid should be checked with the vehicle on level ground and the engine at operating "
             "temperature. Use only the specified lubricant grade and do not overfill the reservoir under any condition.")
    s_edit = similarity(base, edition); s_other = similarity(base, other)
    assert s_edit >= 0.7, ("editions should be similar", s_edit)
    assert s_other < 0.2, ("different docs should be dissimilar", s_other)
    groups = find_duplicates([(1, base), (2, edition), (3, other)], threshold=0.6)
    assert groups == [[1, 2]], ("edition cluster wrong", groups)
    print("dedup self-test OK  (edition sim=%.2f, unrelated sim=%.2f, cluster=%s)" % (s_edit, s_other, groups))
# END OF FILE
