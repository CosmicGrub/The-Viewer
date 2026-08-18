# System requirements & adaptive resources

THE VIEWER is built **Windows-11-first** with **COMPLETE backward compatibility down to Windows 7 and
Windows Vista**: every user-facing feature — search, the vehicle hub, the document viewer, the 104th
parts-request sheet, and OCR — works on all of them. The engine **substitutes the right tool per OS**
(PyMuPDF on modern Windows ↔ **Poppler** on legacy; RapidOCR on modern ↔ **Tesseract** on legacy; the
server and search are pure Python standard library + SQLite, which run everywhere).

The **only** thing that is Windows-10+ is **NVIDIA GPU acceleration** — and that's a *speed booster, not
a feature*: CUDA/onnxruntime don't exist for Vista/7, so on those OSes OCR runs on the CPU via Tesseract
and still finishes; the resulting searchable index is identical. On first launch a **capability probe**
detects your machine and picks the right engines + resource budget automatically.

## The probe (`engine\sysprobe.py`)

Run it any time (the autonomous OCR runner runs it for you):
```
python engine\sysprobe.py
```
It detects **OS + build, Python, CPU cores, RAM, GPU (NVIDIA/CUDA), free disk, and laptop/battery**,
then writes `index\hardware_profile.json` with a recommended profile. The launchers read it
automatically (`sysprobe.py --get ocr_workers|ocr_dpi|use_gpu`).

## Capability tiers (how resources are granted)

| Tier | Looks like | OCR | Workers | DPI |
|------|------------|-----|--------:|----:|
| **GPU laptop / workstation** | NVIDIA GPU + CUDA, Win10/11 (e.g. **Acer Nitro 5**) | GPU (PP-OCRv5) | up to 5 (laptop) / 8 | 220 |
| **Strong CPU** | 8+ cores, 16 GB+ | CPU | up to 6 | 200 |
| **Modest CPU** | 4 cores, 8 GB | CPU | 3 | 165 |
| **Legacy / low-power** | 2 cores / <8 GB / Win7-8 | CPU | 1–2 | 130 |

Workers are also capped by RAM (~1.2 GB each), and on a **laptop** they're held back to leave thermal
headroom; on **battery** they drop further (plug in for full speed).

## OS support matrix — complete features, per-OS engines

| Feature | Win 11/10 | Win 8/8.1 | Win 7 | Vista |
|---|:--:|:--:|:--:|:--:|
| Core search · vehicle hub · 104th sheet | ✅ | ✅ | ✅ | ✅ |
| Document viewer · HD · loupe · tilt · zoom | ✅ | ✅ | ✅ | ✅ |
| Page render engine | PyMuPDF | PyMuPDF / Poppler | PyMuPDF / Poppler | **Poppler** |
| **OCR (text recovery)** | RapidOCR PP-OCRv5 | RapidOCR / Tesseract | RapidOCR / Tesseract | **Tesseract** |
| Auto-snapshots (Task Scheduler) | ✅ | ✅ | ✅ | ✅ |
| GPU *acceleration* (speed only) | ✅ | — | — | — |

Every feature works on every listed OS — only the **engine** changes. GPU acceleration is the lone
Win10+ extra (it makes OCR faster; it isn't required to finish OCR).

**Legacy toolchain (Win7 / Vista):**
- **Python:** Win7 → use **Python 3.8** (last to support it). Vista → **Python 3.4**, or simply run a
  **pre-built index** (the portable build) since search/viewer/104th need only the standard library.
- **Page render:** install **Poppler for Windows** and add its `bin\` to PATH — the viewer auto-uses
  `pdftoppm` when PyMuPDF can't be installed.
- **OCR:** install **Tesseract-OCR for Windows** (or OCR once on a newer PC and copy the finished index).
- The probe detects these (`render_backend`, `ocr_backend` in the profile) and tells you what's missing.

## Environment variables

THE VIEWER reads a family of `VIEWER_*` environment variables at startup / ingest time to override
defaults without touching code. **All of them are optional** — every one has a safe default, and an
unset variable reproduces the documented out-of-the-box behavior. None are required for the normal
loopback deployment (`127.0.0.1`, the shipped default); the security-relevant ones only matter once
you deliberately expose the server on a LAN.

**Security / exposure — only relevant when bound beyond loopback (`--host 0.0.0.0` or a LAN IP):**

- **`VIEWER_ALLOWED_HOSTS`** (`viewer_app.py`) — comma-separated allowlist of `host[:port]` values a
  client-supplied `Host` header is allowed to be trusted for, on top of the server's real bind
  address. Empty (`""`) by default — no extra hosts are trusted. This is the fix for finding #16: a
  spoofed `Host` header could otherwise send a mechanic's scanned QR code to an attacker-controlled
  URL, so `safe_public_base()` validates any candidate host against this allowlist before embedding
  it in operator-facing output (QR codes, deep links) and falls back to a safe default for anything
  else. THE VIEWER prints operator instructions about this at startup: binding to a wildcard address
  (`0.0.0.0` or `::`) with no `VIEWER_ALLOWED_HOSTS` set prints

  ```
  [EXPOSURE] Bound to 0.0.0.0 (a wildcard address) -- QR codes / deep links (/api/qr) will
  [EXPOSURE] encode 127.0.0.1 (useless on a scanning phone) until you set
  [EXPOSURE] VIEWER_ALLOWED_HOSTS to the LAN IP/hostname clients actually connect to
  [EXPOSURE] (comma-separated, e.g. VIEWER_ALLOWED_HOSTS=192.168.1.50:8765).
  ```

  Set it to the LAN IP/hostname mechanics' devices actually use, e.g.
  `set VIEWER_ALLOWED_HOSTS=192.168.1.50:8765`.
- **`VIEWER_AUTH_TOKEN`** (`viewer_app.py`) — shared token mutating requests must present on the
  `X-Viewer-Token` header once the server is exposed (constant-time compared via
  `hmac.compare_digest`). Also gates a handful of sensitive GETs when exposed: `/api/audit`,
  `/api/ops`, `/api/status`, `/api/command_status`, `/api/ingest_status`, `/api/provenance`,
  `/api/integrity`. Empty (`""`) by default. If left unset while exposed, all of the above are
  rejected with 401 — the startup banner explains this too:

  ```
  [EXPOSURE] VIEWER_AUTH_TOKEN is NOT set -- ALL mutating POSTs, and the GETs listed
  [EXPOSURE] above (audit/ops/status/command_status/ingest_status/provenance/integrity),
  [EXPOSURE] will be REJECTED (401). Other GETs remain open.
  ```

  Loopback deployments (the default) never need this — auth only gates the network-exposed path.

**Server & runtime:**

- **`VIEWER_DB`** — path to the SQLite index. Default `index\viewer.db` at the repo root (a sibling
  of `engine\`, not inside it — `viewer_app.py`'s `DB_PATH` resolves it as `engine\..\index\viewer.db`).
  Read by `viewer_app.py`'s `--db` default and by every `build_*.py` / `viewer_ingest.py` script; the
  `.bat` launchers set it before invoking Python.
- **`VIEWER_MODE`** — force the runtime performance mode (`modern` | `lite` | `legacy`); the
  highest-precedence override, kept for back-compat with existing launch scripts. Unset by default
  (mode is auto-detected by `sysprobe.py`). `viewer_app.py`.
- **`VIEWER_RUN_MODE`** — the user-facing Settings-panel equivalent (`auto` | `performance` |
  `retro`), persisted across restarts. Precedence: a concrete `VIEWER_MODE` still wins over
  everything; otherwise `VIEWER_RUN_MODE` env > saved settings file > `"auto"`. `viewer_app.py`.
- **`VIEWER_MAX_WORKERS`** — ceiling on concurrent request-handling threads (the bounded semaphore
  that stops an asset burst from thrashing the machine). Default `0`, meaning auto:
  `max(8, min(64, cpu_count * 4))`. `viewer_app.py`.
- **`VIEWER_NO_AUTO_OPTIMIZE`** — set to `1` to skip the startup auto-optimizer (WAL journal mode +
  background missing-index build). Unset/anything but `1` by default (auto-optimize runs).
  `viewer_app.py`.
- **`VIEWER_RELAXED`** — set to `1` to use exclusive-lock / TRUNCATE-journal SQLite mode instead of
  the normal WAL/pooled-connection path — a durability fallback for filesystems (e.g. some
  bridge/network mounts) where the WAL journal corrupted on an interrupted write. Unset/`0` by
  default. Read in `viewer_app.py`, `viewer_ingest.py`, and `core_pillars.py`.

**OCR & ingestion** (`viewer_ingest.py` unless noted):

- **`VIEWER_ROOT`** — default corpus root folder for `viewer_ingest.py crawl` (`--root`). Empty
  (`""`) by default; the `.bat` launchers set it to `..\corpus` relative to `engine\`.
- **`VIEWER_INGEST_ROOTS`** — `os.pathsep`-separated allowlist of folders the `/api/ingest`,
  `/api/ingest_preview`, `/api/ingest_scan`, `/api/airgap_manifest`, and `/api/airgap_verify` routes
  may read from. Empty by default — unset means any local folder is accepted (the original behavior,
  kept for back-compat). `engine/features/ingest_feature.py`.
- **`VIEWER_OCR_PREPROCESS`** — set to `0` to disable the deskew/denoise/binarize pass (`ocrprep.py`)
  before every OCR call. Default on (any value other than `"0"`, including unset, keeps it enabled).
- **`VIEWER_OCR_MAX_MP`** — output-resolution ceiling for OCR rasterization, in megapixels. Default
  `25` (25,000,000 px) — a large foldout page is downscaled to stay under this before OCR.
- **`VIEWER_ADAPTIVE_DPI`** — set to `1` to opt in to lowering render DPI on sparse (mostly-blank)
  pages. Off by default — deliberately opt-in so it can't silently change accuracy.
- **`VIEWER_OCR_PAGE_TIMEOUT`** — per-page OCR wall-clock timeout in seconds, enforced by a watcher
  thread (not `SIGALRM`, which can't preempt an opaque native call). Default `120`. A page that hangs
  past the timeout is abandoned (its thread is leaked, not killed) rather than stalling an entire
  multi-hour `ocrall()` batch.
- **`VIEWER_OCR_LOCK_TIMEOUT`** — separate, smaller timeout (seconds) for acquiring the process-wide
  PyMuPDF render lock specifically, distinct from `VIEWER_OCR_PAGE_TIMEOUT` above. Default `20`. Under
  heavy `--workers` contention a worker can otherwise burn most of its page budget just queued for the
  lock and then get killed by the outer per-page deadline right as it starts real work; this fixed,
  much-smaller floor lets a busy-but-healthy lock fail fast (reported as lock contention) instead of
  being indistinguishable from a genuine render/OCR hang.
- **`VIEWER_OCR_V5`** — set to `0` to skip the RapidOCR PP-OCRv5 engine and go straight to the
  PP-OCRv4 fallback. Default on (`"1"`/unset tries v5 first, self-tests it, and falls back to v4
  automatically if it's unavailable or fails the self-test).
- **`VIEWER_OCR_MAX`** — set to `1` for the "max performance" opt-in on a GPU machine: uses more
  feeder workers and pushes DPI up (never engages on battery). Off by default. Read by
  `engine\sysprobe.py`; also set by `run_ocr_auto.bat /max`.

**Preflight health gate** (`preflight.py`):

- **`VIEWER_MIN_FREE_MB`** — minimum free disk space (MB) on the index drive before `disk_ok()`
  warns/fails. Default `1024` (1 GB).
- **`VIEWER_DEEP_BUDGET_S`** — wall-clock budget (seconds) for the full `PRAGMA quick_check`
  integrity scan (only runs with `--deep`). Default `20` — if exceeded, preflight reports a timeout
  (WARN) instead of hanging.
- **`VIEWER_LARGE_DB_MB`** — size threshold (MB) above which startup uses the fast catalog probe
  instead of a full page-by-page scan. Default `512`.

**Optional feature backends (unconfigured / off by default):**

- **`VIEWER_VLM`** (`vlm.py`) — module name implementing the pluggable vision-language interface's
  `ask(image, question) -> str`. Default `"vlm_backend"`, i.e. `engine/vlm_backend.py` — which
  doesn't ship, so the feature reports "unavailable" until you drop one in.
- **`VIEWER_IMG3D_CMD`** (`image3d_experiment.py`) — command template for the optional local
  image→3D backend (e.g. TripoSR), with `{in}`/`{out}` placeholders. Empty by default (falls back to
  `engine/image3d_backend.txt` if present; otherwise the feature reports "not configured").
- **`VIEWER_FIGCROP_OCR`** (`figures_feature.py`) — set to `0` to disable the on-demand OCR pass that
  locates a scanned page's "FIGURE n" caption so the illustration above it can be cropped. Default
  on.
- **`VIEWER_XREF_ONLINE`** (`xref_online.py`) — set to `1`, together with `VIEWER_XREF_URL`, to
  enable optional online cross-reference enrichment (public NSN-catalog data only, cached, never
  fetched during normal serving). Default `0` (fully disabled). Setup: `docs/XREF-ONLINE-SETUP.md`.
- **`VIEWER_XREF_URL`** (`xref_online.py`) — the public endpoint template for the above, with
  `{nsn}`/`{niin}` placeholders (e.g. `https://example-public-nsn-catalog/api?nsn={nsn}`). Empty by
  default.

## Your machine — Acer Nitro 5

The Nitro 5 line ships with an **NVIDIA GPU** (GTX 1650 → RTX 30/40-series), 6–8 core CPU, 8–32 GB RAM,
and Win10/11 — so it lands in the **GPU laptop** tier: hardware-accelerated PP-OCRv5, ~5 feeder workers
(thermal headroom), 220 dpi. For the long OCR run:

1. **Plug into AC power** and keep vents clear (cooling pad / NitroSense fans high) — the probe tunes
   workers to avoid throttling, but airflow still helps.
2. Run `engine\run_ocr_auto.bat` — it probes, installs the GPU stack, and runs to 100% unattended.
3. `python engine\gpu_check.py` confirms the GPU path is active.

The exact numbers (cores/RAM/GPU model) are read from *your* unit by the probe — it adapts to whatever
your specific Nitro 5 configuration is.
