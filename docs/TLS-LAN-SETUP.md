# HTTPS on the LAN — self-signed TLS (`--tls`)

**Applies only when you deliberately expose THE VIEWER beyond loopback** (`--host 0.0.0.0` or a LAN
IP — see `docs/SYSTEM-REQUIREMENTS.md`'s "Security / exposure" section for `VIEWER_ALLOWED_HOSTS`
and `VIEWER_AUTH_TOKEN`, which this feature complements). The default deployment (`127.0.0.1`, no
`--tls`) is completely unaffected and unchanged by any of this.

## What this is

`--tls` serves the app over HTTPS instead of plain HTTP, using a **self-signed** certificate you
generate once, on the machine that runs the server. Self-signed means there's no public Certificate
Authority behind it — you're vouching for the cert yourself, which is normal and fine for a private
LAN deployment, but it does mean every browser that connects will show a warning the first time.

## 1. Generate a certificate (one time, on the server machine)

```
cd engine
python -m pip install cryptography      REM one-time; only needed for this step, not to run the app
python gen_cert.py
```

This writes `engine\certs\viewer-cert.pem` and `engine\certs\viewer-key.pem`, valid for 10 years,
covering `localhost`, `127.0.0.1`, and any LAN IP(s) the script can auto-detect on this machine. If
the mechanics' devices reach the server at a hostname or IP the script didn't find automatically
(e.g. a static IP assigned later, or a friendly DNS name), add it explicitly:

```
python gen_cert.py --san 192.168.1.50 --san viewer.mybase.lan
```

`engine\certs\` is git-ignored — the private key never leaves this machine and is never committed.

**Don't have (or don't want) `cryptography` installed?** If you already have `openssl` available
(e.g. via Git for Windows, WSL, or a standalone install), this one-liner produces an equivalent
cert/key pair without installing anything:

```
openssl req -x509 -newkey rsa:2048 -keyout engine\certs\viewer-key.pem ^
  -out engine\certs\viewer-cert.pem -days 3650 -nodes -subj "/CN=viewer.lan" ^
  -addext "subjectAltName=DNS:localhost,IP:127.0.0.1,IP:<your-lan-ip>"
```

## 2. Run the server with `--tls`

```
python viewer_app.py --host 0.0.0.0 --tls
```

By default this looks for `engine\certs\viewer-cert.pem` / `viewer-key.pem` (the output of step 1).
To use a cert/key pair stored somewhere else, pass `--cert` / `--key` explicitly:

```
python viewer_app.py --host 0.0.0.0 --tls --cert C:\path\viewer-cert.pem --key C:\path\viewer-key.pem
```

If `--tls` is passed and no cert/key pair resolves (neither `--cert`/`--key` nor the default
`engine\certs\` pair exist), the server **refuses to start** with a clear message pointing at
`gen_cert.py` — it never silently falls back to plaintext when you explicitly asked for TLS.

Without `--tls`, nothing about the server's behavior changes at all — same plain HTTP as always,
byte-for-byte, whether or not a cert has ever been generated.

## 3. Trust the certificate on each device that connects

The first time a phone, tablet, or laptop browser visits `https://<server>:8765`, it will show a
warning along the lines of *"Your connection is not private"* / `NET::ERR_CERT_AUTHORITY_INVALID`
(Chrome/Edge/Android) or *"Warning: Potential Security Risk"* (Firefox) or *"This Connection Is Not
Private"* (Safari/iOS). **This is expected** — it's the same warning any self-signed cert produces,
and it does not mean anything is broken.

- **Quick path (per-device, per-browser):** click through the warning once (Chrome/Edge: "Advanced" →
  "Proceed to `<host>` (unsafe)"; Firefox: "Advanced" → "Accept the Risk and Continue"; Safari/iOS:
  "Show Details" → "visit this website"). Most browsers remember this per site and won't ask again on
  that device.
- **Cleaner path (no warning at all, any number of devices):** copy `engine\certs\viewer-cert.pem` to
  each device and import it into that device's trust store (Windows: `certmgr.msc` → Trusted Root
  Certification Authorities → Import; Android: Settings → Security → Encryption & credentials →
  Install a certificate; iOS: AirDrop/email the file, then Settings → General → VPN & Device
  Management → install the profile, then Settings → General → About → Certificate Trust Settings →
  enable full trust for it). Only worth doing for a semi-permanent field deployment with several
  regular devices.

## What this does and doesn't protect against

**Does protect against:** passive eavesdropping on the LAN — anyone else on the same network segment
sniffing traffic (Wi-Fi, a hub, a compromised switch) can no longer read the `X-Viewer-Token` header,
search queries, TM/parts/NSN content, or any other request/response in plaintext. This is the same
threat this app's existing `VIEWER_ALLOWED_HOSTS`/`VIEWER_AUTH_TOKEN` hardening already documents and
defends the *authentication* side of (see `docs/SYSTEM-REQUIREMENTS.md`) — `--tls` defends the
*transport* side.

**Does NOT protect against:**
- **An active on-LAN attacker**, unless you actually verify the certificate (or import it into a
  trust store as above) rather than just clicking through the browser warning. Clicking past the
  warning does **not** distinguish the real server's cert from an attacker's own self-signed cert
  impersonating it on the same network — a warning you're trained to dismiss is exactly what a
  man-in-the-middle attack looks like too. If that threat model matters for your deployment, verify
  the cert fingerprint out-of-band (compare it to what `gen_cert.py` printed on the server) before
  trusting it on a device.
- **Exposure beyond a trusted LAN/VPN.** This is a private, self-signed cert for a private network —
  it is explicitly not a substitute for a real CA-signed certificate (Let's Encrypt with a real
  domain, or an internal CA your organization already runs) if this server is ever made reachable
  from outside a trusted LAN or VPN.

## Files involved

- `engine\gen_cert.py` — the one-time cert-generation CLI (see its own docstring for the dependency
  reasoning: a gated, optional `cryptography` install, not an `openssl` shell-out or hand-rolled
  crypto — matching this repo's existing optional-dependency pattern).
- `engine\certs\viewer-cert.pem` / `viewer-key.pem` — the generated pair (git-ignored).
- `engine\viewer_app.py` — the `--tls`/`--cert`/`--key` flags and the server wiring. `ssl.SSLContext`
  wraps the server's *listening* socket once, at startup; `Handler` and the rest of the request path
  are completely unmodified — accepted connections come back already TLS-terminated.
