#!/usr/bin/env python3
"""THE VIEWER -- one-time self-signed TLS certificate generator (v1.43.0).

This script is NOT part of the running server. It is a small, operator-run, offline utility that
mints a self-signed cert/key pair ONCE, on whichever machine will run `viewer_app.py --tls`. The
server itself (viewer_app.py) opens and serves that cert with stdlib `ssl` alone -- this script's
dependency (`cryptography`, see below) never touches the request path or the always-on server code,
so the "runs on legacy machines with no third-party deps" promise (see engine/preflight.py's
docstring) is preserved for the SERVER. Only this one-time, skippable, operator-invoked step needs
a third-party package, exactly like the existing optional-dependency convention in this codebase
(sentence-transformers, rapidocr-onnxruntime, pyzbar -- commented out in requirements.txt, printed
as a manual `pip install` suggestion in INSTALL.bat, imported in a try/except so absence degrades a
feature instead of breaking the app).

WHY `cryptography` and not an `openssl` shell-out or a hand-rolled ASN.1/X.509 encoder:
  - `openssl` shelling out was rejected as the PRIMARY path because this app's own documented
    legacy floor (docs/SYSTEM-REQUIREMENTS.md: Win7/Vista, Python 3.8/3.4) has no guaranteed
    `openssl.exe` on PATH -- it would silently fail exactly the audience the app targets. It also
    adds a second, harder-to-diagnose failure surface (locating the binary, OpenSSL 1.1 vs 3.x CLI
    syntax drift, SAN-extension quoting across Windows cmd/PowerShell). It is documented below as a
    FALLBACK for operators who already have openssl and would rather not `pip install` anything.
  - A vendored pure-Python ASN.1/X.509 encoder was rejected outright: hand-rolled crypto/DER code is
    far riskier to maintain than depending on the field's actual standard tool (`cryptography`,
    which itself underpins pyOpenSSL/paramiko/requests -- the same trust boundary this app already
    implicitly relies on via pip's own supply chain for its other dependencies).
  - `cryptography` as a gated OPTIONAL dependency matches this repo's own established pattern and is
    needed for one offline, one-time, operator-run step -- not for the server itself.

Usage:
    python engine\\gen_cert.py [--san HOST_OR_IP ...] [--days N] [--out-dir DIR] [--force]

Output (default): engine/certs/viewer-cert.pem, engine/certs/viewer-key.pem
  - RSA-2048 key, self-signed X.509 cert, CA:FALSE, 10-year validity by default.
  - subjectAltName always includes DNS:localhost, IP:127.0.0.1, plus every LAN IP this script can
    detect via socket.gethostbyname_ex(socket.gethostname()), plus anything passed via --san.
  - Long (10y) validity is deliberate: this is a self-signed LAN cert an operator manually trusts,
    not a publicly-chained cert bound by the CA/Browser Forum's ~398-day lifetime cap. A short expiry
    would only force needless re-generation on a field deployment with no CA to auto-renew from.

If `cryptography` is not installed, this script fails with a clear message giving BOTH remediation
paths: `pip install cryptography` (then re-run this script), or the exact openssl one-liner for
operators who already have openssl available:

    openssl req -x509 -newkey rsa:2048 -keyout engine\\certs\\viewer-key.pem ^
      -out engine\\certs\\viewer-cert.pem -days 3650 -nodes -subj "/CN=viewer.lan" ^
      -addext "subjectAltName=DNS:localhost,IP:127.0.0.1,IP:<lan-ip>"

See docs/TLS-LAN-SETUP.md for the full operator walkthrough (what this does and doesn't protect
against, and how to trust the certificate on each browser/OS).
"""
import argparse
import ipaddress
import os
import socket
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CERT_DIR = os.path.join(HERE, "certs")
DEFAULT_CERT_PATH = os.path.join(DEFAULT_CERT_DIR, "viewer-cert.pem")
DEFAULT_KEY_PATH = os.path.join(DEFAULT_CERT_DIR, "viewer-key.pem")

OPENSSL_FALLBACK_HINT = (
    "openssl req -x509 -newkey rsa:2048 -keyout engine\\certs\\viewer-key.pem "
    "-out engine\\certs\\viewer-cert.pem -days 3650 -nodes -subj \"/CN=viewer.lan\" "
    "-addext \"subjectAltName=DNS:localhost,IP:127.0.0.1,IP:<lan-ip>\""
)


def _detect_lan_ips():
    """Best-effort LAN IP discovery for the cert's subjectAltName. Never raises -- an empty list
    just means the operator should pass --san explicitly (same posture as VIEWER_ALLOWED_HOSTS)."""
    ips = set()
    try:
        hostname = socket.gethostname()
        _name, _aliases, addrs = socket.gethostbyname_ex(hostname)
        for a in addrs:
            if a and a != "127.0.0.1":
                ips.add(a)
    except Exception:
        pass
    try:
        # A second, independent method: opening a UDP "connection" (no packet sent) to a
        # non-routable address reveals which local interface the OS would use -- catches the
        # common case where gethostbyname_ex only returns 127.0.1.1 (Windows can do this too,
        # e.g. behind certain VPN/virtual-adapter setups).
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(("10.255.255.255", 1))
            ip = s.getsockname()[0]
            if ip and ip != "127.0.0.1":
                ips.add(ip)
        finally:
            s.close()
    except Exception:
        pass
    return sorted(ips)


def generate(out_dir=None, san_extra=None, days=3650, force=False, common_name="viewer.lan"):
    """Generate an RSA-2048 self-signed cert/key pair. Returns (cert_path, key_path). Raises
    RuntimeError with a clear, actionable message if `cryptography` isn't installed, or if the
    output files already exist and `force` is False."""
    out_dir = out_dir or DEFAULT_CERT_DIR
    cert_path = os.path.join(out_dir, "viewer-cert.pem")
    key_path = os.path.join(out_dir, "viewer-key.pem")

    if not force and (os.path.exists(cert_path) or os.path.exists(key_path)):
        raise RuntimeError(
            "refusing to overwrite existing cert/key at %s / %s -- pass --force to regenerate "
            "(this will invalidate any browser trust exception granted for the old cert)."
            % (cert_path, key_path)
        )

    try:
        from cryptography import x509
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.x509.oid import NameOID
        import datetime
    except ImportError as e:
        raise RuntimeError(
            "the 'cryptography' package is required to generate a certificate, and is not "
            "installed. This is a ONE-TIME, operator-run step -- not needed to install or run "
            "THE VIEWER itself. Fix with either of:\n"
            "  1) pip install cryptography      (then re-run this script)\n"
            "  2) already have openssl? run this instead (no pip install needed):\n"
            "     %s\n"
            "Original import error: %s" % (OPENSSL_FALLBACK_HINT, e)
        )

    os.makedirs(out_dir, exist_ok=True)

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    san_hosts = ["localhost"]
    san_ips = ["127.0.0.1"] + _detect_lan_ips()
    for extra in (san_extra or []):
        extra = (extra or "").strip()
        if not extra:
            continue
        try:
            ipaddress.ip_address(extra)
            san_ips.append(extra)
        except ValueError:
            san_hosts.append(extra)
    san_hosts = sorted(set(san_hosts))
    san_ips = sorted(set(san_ips))

    san_entries = [x509.DNSName(h) for h in san_hosts]
    san_entries += [x509.IPAddress(ipaddress.ip_address(ip)) for ip in san_ips]

    subject = issuer = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, common_name)])
    now = datetime.datetime.now(datetime.timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(days=1))
        .not_valid_after(now + datetime.timedelta(days=days))
        .add_extension(x509.SubjectAlternativeName(san_entries), critical=False)
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(
            x509.KeyUsage(
                digital_signature=True, key_encipherment=True, content_commitment=False,
                data_encipherment=False, key_agreement=False, key_cert_sign=False,
                crl_sign=False, encipher_only=False, decipher_only=False,
            ),
            critical=True,
        )
        .sign(key, hashes.SHA256())
    )

    with open(key_path, "wb") as f:
        f.write(key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        ))
    with open(cert_path, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))

    return cert_path, key_path, san_hosts, san_ips


def main():
    ap = argparse.ArgumentParser(description="Generate a one-time self-signed TLS cert for THE VIEWER's --tls flag.")
    ap.add_argument("--san", action="append", default=[], metavar="HOST_OR_IP",
                    help="extra hostname or IP to add to the certificate's subjectAltName (repeatable)")
    ap.add_argument("--days", type=int, default=3650, help="validity period in days (default 3650 = ~10 years)")
    ap.add_argument("--out-dir", default=DEFAULT_CERT_DIR, help="output directory (default engine/certs)")
    ap.add_argument("--force", action="store_true", help="overwrite an existing cert/key pair")
    args = ap.parse_args()

    try:
        cert_path, key_path, hosts, ips = generate(
            out_dir=args.out_dir, san_extra=args.san, days=args.days, force=args.force
        )
    except RuntimeError as e:
        print("[gen_cert] ERROR: %s" % e, file=sys.stderr)
        return 1

    print("[gen_cert] wrote %s" % cert_path)
    print("[gen_cert] wrote %s" % key_path)
    print("[gen_cert] subjectAltName DNS: %s" % ", ".join(hosts))
    print("[gen_cert] subjectAltName IP:  %s" % ", ".join(ips))
    print("[gen_cert] valid for %d days" % args.days)
    print("[gen_cert] this is SELF-SIGNED -- browsers will show a warning on first connect.")
    print("[gen_cert] run the server with:  python viewer_app.py --tls --host 0.0.0.0")
    print("[gen_cert] see docs/TLS-LAN-SETUP.md for how to trust the cert on each device.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
