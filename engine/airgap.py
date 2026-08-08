"""airgap.py -- SIGNED update package for air-gapped transfer (roadmap Vol.2 #95; brief-req E + security). A
field machine is disconnected. To add manuals to it, you carry them on removable media -- and you must be
able to PROVE, on the receiving side, that the bundle is exactly what the authoring side produced and hasn't
been tampered with. This builds a manifest of the files (name + size + SHA-256) and signs it with an HMAC
over a canonical serialization; the receiver re-hashes every file and re-checks the signature before anything
is ingested. Fail-closed: any missing file, changed byte, or bad signature -> reject.

Stdlib only (hashlib + hmac). Pure and unit-testable. The corpus/index are never modified here."""

from __future__ import annotations
import hashlib, hmac, json, os, time


def _sha256(path, chunk=1 << 20):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(chunk), b""):
            h.update(b)
    return h.hexdigest()


def _canonical(manifest):
    """Stable bytes to sign: the files list + meta, sorted, without the signature field."""
    m = {k: v for k, v in manifest.items() if k != "signature"}
    return json.dumps(m, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sign(manifest, secret):
    """Attach an HMAC-SHA256 signature (hex) over the canonical manifest. `secret` is bytes or str."""
    if isinstance(secret, str):
        secret = secret.encode("utf-8")
    manifest = dict(manifest)
    manifest["signature"] = hmac.new(secret, _canonical(manifest), hashlib.sha256).hexdigest()
    return manifest


def make_manifest(root, files, secret, label="viewer-update"):
    """Build + sign a manifest for `files` (paths relative to root). Skips missing files (reported)."""
    entries, missing = [], []
    for rel in files:
        p = os.path.join(root, rel)
        if not os.path.isfile(p):
            missing.append(rel); continue
        entries.append({"name": rel.replace("\\", "/"), "size": os.path.getsize(p), "sha256": _sha256(p)})
    entries.sort(key=lambda e: e["name"])
    manifest = {"label": label, "created": int(time.time()), "count": len(entries),
                "algo": "hmac-sha256", "files": entries}
    if missing:
        manifest["missing_at_build"] = sorted(missing)
    return sign(manifest, secret)


def signature_valid(manifest, secret):
    if isinstance(secret, str):
        secret = secret.encode("utf-8")
    sig = manifest.get("signature")
    if not sig:
        return False
    expect = hmac.new(secret, _canonical(manifest), hashlib.sha256).hexdigest()
    return hmac.compare_digest(sig, expect)


def verify(manifest, root, secret):
    """Fail-closed verification on the receiving side. Returns a dict with keys ok, signature_valid,
    files (each name/present/match), missing (list of names), and tampered (list of names).
    ok is True only if the signature is valid AND every listed file is present and hash-matches."""
    sig_ok = signature_valid(manifest, secret)
    rows, missing, tampered = [], [], []
    for e in manifest.get("files", []):
        p = os.path.join(root, e["name"])
        present = os.path.isfile(p)
        match = bool(present and _sha256(p) == e.get("sha256"))
        rows.append({"name": e["name"], "present": present, "match": match})
        if not present:
            missing.append(e["name"])
        elif not match:
            tampered.append(e["name"])
    ok = sig_ok and not missing and not tampered
    return {"ok": ok, "signature_valid": sig_ok, "files": rows,
            "missing": missing, "tampered": tampered,
            "verdict": ("ACCEPT" if ok else "REJECT")}


# --------------------------------------------------------------------------- #
# self-test: `python airgap.py`                                               #
# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    import tempfile, shutil
    src = tempfile.mkdtemp(prefix="airgap_src_")
    open(os.path.join(src, "TM-A.pdf"), "wb").write(b"%PDF-1.4 alpha" + b"\x00" * 500)
    open(os.path.join(src, "TM-B.pdf"), "wb").write(b"%PDF-1.4 bravo" + b"\x01" * 500)
    SECRET = "unit-shared-key-2026"

    man = make_manifest(src, ["TM-A.pdf", "TM-B.pdf", "gone.pdf"], SECRET)
    assert man["count"] == 2 and man.get("missing_at_build") == ["gone.pdf"], man
    assert signature_valid(man, SECRET), "signature should validate"
    print("make_manifest + sign OK -> %d files, signed" % man["count"])

    # receiver side: copy the bundle, verify -> ACCEPT
    dst = tempfile.mkdtemp(prefix="airgap_dst_")
    for f in ("TM-A.pdf", "TM-B.pdf"):
        shutil.copy(os.path.join(src, f), os.path.join(dst, f))
    v = verify(man, dst, SECRET)
    assert v["ok"] and v["verdict"] == "ACCEPT", v
    print("verify (clean transfer) OK -> %s" % v["verdict"])

    # tamper a byte -> REJECT (hash mismatch)
    with open(os.path.join(dst, "TM-B.pdf"), "r+b") as f:
        f.seek(20); f.write(b"\xff\xff")
    vt = verify(man, dst, SECRET)
    assert not vt["ok"] and vt["tampered"] == ["TM-B.pdf"], vt
    print("verify (tampered file) OK -> REJECT, tampered=%s" % vt["tampered"])

    # wrong key -> signature invalid -> REJECT even if files are fine
    shutil.copy(os.path.join(src, "TM-B.pdf"), os.path.join(dst, "TM-B.pdf"))   # restore
    vw = verify(man, dst, "attacker-key")
    assert not vw["ok"] and vw["signature_valid"] is False, vw
    print("verify (wrong key) OK -> REJECT, signature_valid=False")

    # forged manifest (edit a hash without re-signing) -> signature invalid
    forged = dict(man); forged["files"] = [dict(e) for e in man["files"]]
    forged["files"][0]["sha256"] = "0" * 64
    assert not signature_valid(forged, SECRET), "forged manifest must fail signature"
    print("forged-manifest detection OK")
    print("airgap self-test PASS")

# END OF FILE
