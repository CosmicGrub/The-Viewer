#!/usr/bin/env python3
"""Regression tests for v1.43.0 TLS support (engine/viewer_app.py's --tls/--cert/--key, the listening-
socket wrap in main(), and engine/gen_cert.py's certificate generation).

Exercises the real scenarios this feature exists for, with a REAL socket and a REAL self-signed
certificate (generated fresh into a temp dir via gen_cert.generate() -- no network, no external
openssl dependency):

  1. gen_cert.generate() produces a cert/key pair that stdlib `ssl.SSLContext.load_cert_chain()`
     accepts without error, with the expected subjectAltName entries (localhost, 127.0.0.1).
  2. A server whose LISTENING socket is wrapped exactly the way viewer_app.main() wraps it (same
     ssl.SSLContext construction, same minimum TLS version, same wrap_socket() call against the
     bound socket) answers a real `https://` GET with a normal 200 JSON response, through a real
     TLS handshake -- not a mock.
  3. A plain `http://` request to that SAME port (no TLS) fails -- the raw HTTP bytes are not a
     valid TLS ClientHello, so the handshake fails and the connection is refused/reset, exactly the
     "refuse plaintext on a TLS-only port" behavior an operator relies on.
  4. The existing plain-HTTP path is completely unaffected when --tls is not requested: an ordinary
     (unwrapped) ThreadingHTTPServer + Handler answers a normal `http://` GET, unchanged.
  5. viewer_app.main() fails fast (returns without ever binding a socket) when --tls is passed but
     no cert/key pair resolves -- it never silently falls back to serving plaintext when TLS was
     explicitly requested. Exercised by actually invoking main() with a patched sys.argv pointed at
     an empty --cert/--key path, not by reading source.
  6. safe_public_base() emits an `https://` URL when TLS is active and `http://` when it is not
     (the QR-code / deep-link scheme an operator-facing page embeds must match what the server is
     actually serving).

RUN ON WINDOWS / a coherent env -- it imports viewer_app and gen_cert. Pure stdlib runner (gen_cert's
own `cryptography` dependency is optional at the APP level, but this test suite -- like the rest of
this repo's optional-dependency tests -- skips its cert-generation-dependent checks gracefully if
`cryptography` is not installed, matching e.g. test_embed_checkpoint.py's sentence-transformers
skip convention)."""
import io
import json
import os
import socket
import ssl
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
ENGINE = os.path.dirname(HERE)
sys.path.insert(0, ENGINE); sys.path.insert(0, HERE)
import fixture                                                    # noqa: E402

try:
    import cryptography                                            # noqa: F401
    HAVE_CRYPTOGRAPHY = True
except ImportError:
    HAVE_CRYPTOGRAPHY = False


def _free_port():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]; s.close()
    return port


def _wrap_like_main(srv, cert_path, key_path):
    """Mirrors viewer_app.main()'s TLS wiring exactly: same context type, same minimum version,
    same wrap_socket() call against the server's already-bound listening socket."""
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.minimum_version = ssl.TLSVersion.TLSv1_2
    ctx.load_cert_chain(certfile=cert_path, keyfile=key_path)
    srv.socket = ctx.wrap_socket(srv.socket, server_side=True)


def _client_ctx_trusting(cert_path):
    """A client-side SSL context that trusts our self-signed test cert specifically (not a bare
    CERT_NONE skip -- this proves the handshake genuinely validates against OUR cert, not just
    that verification was disabled)."""
    ctx = ssl.create_default_context(cafile=cert_path)
    return ctx


def main():
    tests = []
    if not HAVE_CRYPTOGRAPHY:
        print("SKIP: 'cryptography' not installed -- gen_cert.py / TLS tests skipped "
              "(matches this repo's optional-dependency test convention).")
        print("\n0 passed, 0 failed")
        return 0

    import gen_cert
    import viewer_app as V

    tmp = tempfile.mkdtemp(prefix="viewer_tls_")
    db, _corr = fixture.build(tmp)
    cert_dir = os.path.join(tmp, "certs")

    V.DB_PATH = db; V.INDEX_DIR = os.path.dirname(db)

    # ---- 1. gen_cert produces a cert stdlib ssl accepts, with the right SAN entries ----------------
    cert_path, key_path, hosts, ips = gen_cert.generate(out_dir=cert_dir, days=30)
    tests.append(("gen_cert wrote a cert file", os.path.exists(cert_path)))
    tests.append(("gen_cert wrote a key file", os.path.exists(key_path)))
    tests.append(("SAN DNS entries include localhost", "localhost" in hosts))
    tests.append(("SAN IP entries include 127.0.0.1", "127.0.0.1" in ips))
    try:
        probe_ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        probe_ctx.load_cert_chain(certfile=cert_path, keyfile=key_path)
        tests.append(("stdlib ssl.SSLContext.load_cert_chain accepts the generated cert/key", True))
    except Exception as e:
        tests.append(("stdlib ssl.SSLContext.load_cert_chain accepts the generated cert/key (%s)" % e, False))

    # gen_cert refuses to clobber an existing pair without --force
    try:
        gen_cert.generate(out_dir=cert_dir, days=30, force=False)
        tests.append(("gen_cert refuses to overwrite an existing pair without force=True", False))
    except RuntimeError:
        tests.append(("gen_cert refuses to overwrite an existing pair without force=True", True))

    # ---- 2 + 3. a REAL TLS-wrapped server: https:// works, http:// on the same port fails ----------
    tls_port = _free_port()
    tls_srv = ThreadingHTTPServer(("127.0.0.1", tls_port), V.Handler)
    _wrap_like_main(tls_srv, cert_path, key_path)
    t = threading.Thread(target=tls_srv.serve_forever, daemon=True); t.start()
    time.sleep(0.3)
    try:
        client_ctx = _client_ctx_trusting(cert_path)
        try:
            with urllib.request.urlopen("https://127.0.0.1:%d/healthz" % tls_port, timeout=10,
                                        context=client_ctx) as r:
                status = r.status
                body = json.loads(r.read().decode("utf-8"))
            tests.append(("https:// request to the TLS-wrapped server succeeds (200)", status == 200))
            tests.append(("https:// response is real JSON from the app", isinstance(body, dict) and "version" in body))
        except Exception as e:
            tests.append(("https:// request to the TLS-wrapped server succeeds (200) [%s]" % e, False))

        # A plain http:// request to the SAME port: raw HTTP bytes are not a valid TLS ClientHello,
        # so the handshake fails and the request must NOT get a normal 200 response.
        try:
            with urllib.request.urlopen("http://127.0.0.1:%d/healthz" % tls_port, timeout=5) as r:
                tests.append(("plain http:// to the TLS-only port is rejected, not served (200 was WRONG)",
                              r.status != 200))
        except Exception:
            tests.append(("plain http:// to the TLS-only port is rejected (connection failed, as expected)", True))

        # A client that does NOT trust our self-signed cert (default system trust store) must
        # reject the handshake -- this is the "self-signed" warning behavior a real browser shows.
        try:
            untrusting_ctx = ssl.create_default_context()
            with urllib.request.urlopen("https://127.0.0.1:%d/healthz" % tls_port, timeout=5,
                                        context=untrusting_ctx) as r:
                tests.append(("a client that doesn't trust the self-signed cert is rejected (200 was WRONG)",
                              False))
        except ssl.SSLCertVerificationError:
            tests.append(("a client that doesn't trust the self-signed cert is rejected (cert verification failed, as expected)", True))
        except urllib.error.URLError as e:
            tests.append(("a client that doesn't trust the self-signed cert is rejected (%s, as expected)" % e,
                          isinstance(e.reason, ssl.SSLCertVerificationError) or "CERTIFICATE_VERIFY_FAILED" in str(e.reason)))
    finally:
        tls_srv.shutdown(); tls_srv.server_close()

    # ---- 4. the existing plain-HTTP path is completely unaffected when --tls is not requested ------
    plain_port = _free_port()
    plain_srv = ThreadingHTTPServer(("127.0.0.1", plain_port), V.Handler)
    t2 = threading.Thread(target=plain_srv.serve_forever, daemon=True); t2.start()
    time.sleep(0.3)
    try:
        with urllib.request.urlopen("http://127.0.0.1:%d/healthz" % plain_port, timeout=10) as r:
            status = r.status
            body = json.loads(r.read().decode("utf-8"))
        tests.append(("plain http:// request works completely unchanged with no --tls involved", status == 200 and "version" in body))
    except Exception as e:
        tests.append(("plain http:// request works completely unchanged with no --tls involved (%s)" % e, False))
    finally:
        plain_srv.shutdown(); plain_srv.server_close()

    # ---- 5. main() fails fast (never binds a socket) when --tls is requested but no cert resolves --
    empty_dir = os.path.join(tmp, "no_certs_here")
    os.makedirs(empty_dir, exist_ok=True)
    missing_cert = os.path.join(empty_dir, "nope-cert.pem")
    missing_key = os.path.join(empty_dir, "nope-key.pem")
    argv_port = _free_port()
    old_argv = sys.argv
    old_tls_enabled = V.TLS_ENABLED
    captured = io.StringIO()
    old_stdout = sys.stdout
    try:
        sys.argv = ["viewer_app.py", "--db", db, "--host", "127.0.0.1", "--port", str(argv_port),
                    "--tls", "--cert", missing_cert, "--key", missing_key]
        sys.stdout = captured
        V.main()   # must return (not raise, not block in serve_forever) when the cert is missing
        sys.stdout = old_stdout
        out = captured.getvalue()
        tests.append(("main() with --tls and a missing cert prints a clear refusal message",
                      "Refusing to start in plaintext" in out))
        tests.append(("main() with --tls and a missing cert never flips TLS_ENABLED on",
                      V.TLS_ENABLED is False))
        # confirm no socket actually got bound on that port (main() returned before construction)
        probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        bindable = True
        try:
            probe.bind(("127.0.0.1", argv_port))
        except OSError:
            bindable = False
        finally:
            probe.close()
        tests.append(("main() with --tls and a missing cert never bound the port (port still free)", bindable))
    finally:
        sys.stdout = old_stdout
        sys.argv = old_argv
        V.TLS_ENABLED = old_tls_enabled

    # ---- 6. safe_public_base() scheme follows TLS_ENABLED ------------------------------------------
    old_host, old_port, old_tls = V.HOST, V.PORT, V.TLS_ENABLED
    try:
        V.HOST, V.PORT = "127.0.0.1", 8765
        V.TLS_ENABLED = False
        tests.append(("safe_public_base() emits http:// when TLS is off",
                      V.safe_public_base("127.0.0.1:8765").startswith("http://")))
        V.TLS_ENABLED = True
        tests.append(("safe_public_base() emits https:// when TLS is on",
                      V.safe_public_base("127.0.0.1:8765").startswith("https://")))
    finally:
        V.HOST, V.PORT, V.TLS_ENABLED = old_host, old_port, old_tls

    fails = [n for n, ok in tests if not ok]
    for n, ok in tests:
        print(("PASS " if ok else "FAIL ") + n)
    print("\n%d passed, %d failed" % (len(tests) - len(fails), len(fails)))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
