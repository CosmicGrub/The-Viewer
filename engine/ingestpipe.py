"""ingestpipe.py -- BULK folder ingestion pipeline (roadmap Vol.2 #96; brief-req E: 'any additional files
should be easily added without a sweat'). Point it at a folder and it scans every supported document, hashes
each to detect duplicates already in the corpus, and produces an ingestion PLAN (new / duplicate / unsupported)
that the host-side ingest + OCR queue then processes. Read-only over the source folder; never touches the corpus
here (the plan is executed by the existing ingest step).

scan_folder() and plan() are pure and unit-testable. The corpus stays read-only (R6)."""

from __future__ import annotations
import hashlib, os

SUPPORTED = (".pdf", ".txt", ".html", ".htm", ".xml", ".csv", ".md", ".tiff", ".tif", ".png", ".jpg", ".jpeg")


def supported(path):
    return os.path.splitext(path)[1].lower() in SUPPORTED


def quick_hash(path, head=1 << 20):
    """A fast content fingerprint: size + sha1 of the first 1 MB. Enough to spot duplicate manuals cheaply."""
    try:
        size = os.path.getsize(path)
        h = hashlib.sha1(); h.update(str(size).encode())
        with open(path, "rb") as f:
            h.update(f.read(head))
        return h.hexdigest()[:16]
    except Exception:
        return None


def scan_folder(root, recursive=True, cap=100000):
    """-> [{path, name, ext, size, hash}] for every SUPPORTED file under root. Sorted, deduped by path."""
    out = []
    if not root or not os.path.isdir(root):
        return out
    # v1.13.4: `break` here only exited the INNER per-directory loop -- os.walk() (the outer loop) kept
    # being pulled from regardless, so it walked every remaining directory in the tree (each contributing
    # one more file past the cap) instead of actually stopping. `cap` exists specifically so a user
    # pointing this at a large drive root can't hang the endpoint; a `return` exits both loops at once,
    # which also stops advancing the os.walk() generator -- it does no further directory traversal once
    # we stop pulling from it, unlike `break` which only stopped consuming its already-yielded files.
    walker = os.walk(root) if recursive else [(root, [], os.listdir(root))]
    for dirpath, _dirs, files in walker:
        for fn in files:
            p = os.path.join(dirpath, fn)
            if not (os.path.isfile(p) and supported(p)):
                continue
            try:
                out.append({"path": p, "name": fn, "ext": os.path.splitext(fn)[1].lower(),
                            "size": os.path.getsize(p), "hash": quick_hash(p)})
            except Exception:
                continue
            if len(out) >= cap:
                out.sort(key=lambda x: x["path"])
                return out
    out.sort(key=lambda x: x["path"])
    return out


def plan(found, known_hashes=None, known_names=None):
    """Split a scan into new / duplicate / (unsupported handled at scan time). known_hashes / known_names are
    what's already in the corpus. A file is a duplicate if its hash OR its name is already present."""
    kh = set(known_hashes or [])
    kn = {(n or "").lower() for n in (known_names or [])}
    new, dup, seen = [], [], set()
    for f in found or []:
        fh = f.get("hash")
        # de-dup within the scan too (same file copied twice in the folder)
        sig = fh or f["path"]
        if sig in seen:
            dup.append({**f, "reason": "duplicate in folder"}); continue
        seen.add(sig)
        if (fh and fh in kh) or (f["name"].lower() in kn):
            dup.append({**f, "reason": "already in corpus"})
        else:
            new.append(f)
    total_mb = round(sum(f["size"] for f in new) / 1e6, 1)
    return {"new": new, "duplicate": dup, "counts": {"new": len(new), "duplicate": len(dup)},
            "new_mb": total_mb, "note": "run the ingest + OCR queue to process the 'new' files"}


# --------------------------------------------------------------------------- #
# self-test: `python ingestpipe.py`                                           #
# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    import tempfile
    d = tempfile.mkdtemp(prefix="ingest_")
    sub = os.path.join(d, "sub"); os.makedirs(sub)
    open(os.path.join(d, "TM-9-2320-280-10.pdf"), "wb").write(b"%PDF-1.4 fake manual A" + b"\x00" * 100)
    open(os.path.join(d, "notes.txt"), "w").write("some notes")
    open(os.path.join(sub, "TM-9-2320-280-20.pdf"), "wb").write(b"%PDF-1.4 fake manual B" + b"\x00" * 100)
    open(os.path.join(d, "photo.gif"), "wb").write(b"GIF89a")           # unsupported -> ignored
    open(os.path.join(d, "copy.pdf"), "wb").write(b"%PDF-1.4 fake manual A" + b"\x00" * 100)  # dup content of A

    found = scan_folder(d)
    exts = {f["ext"] for f in found}
    assert ".gif" not in exts, exts                          # unsupported skipped
    assert len(found) == 4, [f["name"] for f in found]       # 3 pdf + 1 txt (gif excluded)
    print("scan_folder OK -> %d supported files (recursive): %s" % (len(found), sorted(f["name"] for f in found)))

    # nothing known yet -> the two identical PDFs collapse to one 'new'
    p = plan(found)
    assert p["counts"]["duplicate"] == 1, p["counts"]        # copy.pdf == TM...10 content
    assert p["counts"]["new"] == 3, p["counts"]              # A, B, notes.txt
    print("plan (fresh) OK -> new=%d, duplicate=%d, %s MB" % (p["counts"]["new"], p["counts"]["duplicate"], p["new_mb"]))

    # now say manual B is already in the corpus (by name) -> it becomes a duplicate
    p2 = plan(found, known_names=["TM-9-2320-280-20.pdf"])
    assert any(x["name"] == "TM-9-2320-280-20.pdf" for x in p2["duplicate"]), p2
    assert p2["counts"]["new"] == 2, p2["counts"]
    print("plan (with known corpus) OK -> new=%d" % p2["counts"]["new"])
    assert scan_folder("/no/such/dir") == []
    print("ingestpipe self-test PASS")

# END OF FILE
