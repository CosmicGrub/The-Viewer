#!/usr/bin/env python3
"""THE VIEWER — hardware/OS capability probe (run before onboarding / first launch).

Detects the OS (Windows 11 down to Windows 7), Python, CPU, RAM, GPU, and free disk, then writes a
resource PROFILE the engine + launchers read so the app uses an appropriate slice of the machine —
from a legacy Win7 box (core features, CPU, conservative) up to a Win11 GPU workstation (full suite).

THE VIEWER is built Windows-11-first with INCOMPLETE/best-effort backward support to Windows 7:
features that can't run on an older OS are disabled gracefully; the core (search, viewer, 104th sheet,
CPU OCR) is kept working as far back as we reasonably can.

CLI:
  python sysprobe.py                 # probe, print a summary, write index/hardware_profile.json
  python sysprobe.py --get KEY       # print one profile value (for .bat scripts); probes if needed
  python sysprobe.py --json          # print the full profile as JSON
"""
import json, os, sys, platform, subprocess, shutil

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PROFILE = os.path.join(ROOT, "index", "hardware_profile.json")

def os_info():
    s = platform.system()
    if s == "Windows":
        try:
            v = sys.getwindowsversion(); b = v.build
            if v.major == 10 and b >= 22000: name = "Windows 11"
            elif v.major == 10: name = "Windows 10"
            elif v.major == 6 and v.minor == 3: name = "Windows 8.1"
            elif v.major == 6 and v.minor == 2: name = "Windows 8"
            elif v.major == 6 and v.minor == 1: name = "Windows 7"
            elif v.major == 6 and v.minor == 0: name = "Windows Vista"
            else: name = "Windows %d.%d" % (v.major, v.minor)
            # rank: 11=110,10=100,8.1=81,8=80,7=70
            rank = {"Windows 11":110,"Windows 10":100,"Windows 8.1":81,"Windows 8":80,"Windows 7":70,"Windows Vista":60}.get(name,50)
            return name, b, rank
        except Exception:
            return platform.platform(), 0, 50
    return "%s (%s)" % (s, platform.release()), 0, 100  # non-Windows: treat as modern for dev/testing

def ram_bytes():
    if os.name == "nt":
        try:
            import ctypes
            class MS(ctypes.Structure):
                _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                            ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                            ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                            ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                            ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]
            m = MS(); m.dwLength = ctypes.sizeof(m)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
            return int(m.ullTotalPhys)
        except Exception:
            return 0
    try:
        return os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES")
    except Exception:
        return 0

def gpu_info():
    name = None; vram = 0; driver = None
    smi = shutil.which("nvidia-smi")
    if smi:
        try:
            out = subprocess.run([smi, "--query-gpu=name,memory.total,driver_version",
                                  "--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=12).stdout.strip()
            if out:
                parts = [p.strip() for p in out.splitlines()[0].split(",")]
                name = parts[0]; vram = int(float(parts[1])) if len(parts) > 1 and parts[1].replace('.','').isdigit() else 0
                driver = parts[2] if len(parts) > 2 else None
        except Exception:
            pass
    cuda = False
    try:
        import onnxruntime as ort
        cuda = "CUDAExecutionProvider" in ort.get_available_providers()
    except Exception:
        pass
    return {"name": name, "vram_mb": vram, "driver": driver, "onnx_cuda": cuda, "present": bool(smi or name)}

def _have_module(name):
    try:
        __import__(name); return True
    except Exception:
        return False

def free_disk_gb(path):
    try:
        return round(shutil.disk_usage(path).free / (1024**3), 1)
    except Exception:
        return None

def power_info():
    """(is_laptop, on_battery) — so we can leave thermal headroom on gaming laptops (e.g. Acer Nitro 5)
    and ease off on battery. Returns (None, None) when it can't tell."""
    if os.name == "nt":
        try:
            import ctypes
            class SPS(ctypes.Structure):
                _fields_ = [("ACLineStatus", ctypes.c_byte), ("BatteryFlag", ctypes.c_byte),
                            ("BatteryLifePercent", ctypes.c_byte), ("SystemStatusFlag", ctypes.c_byte),
                            ("BatteryLifeTime", ctypes.c_ulong), ("BatteryFullLifeTime", ctypes.c_ulong)]
            s = SPS()
            if ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(s)):
                is_laptop = (s.BatteryFlag != 128)        # 128 = no system battery (desktop)
                on_battery = (s.ACLineStatus == 0)        # 0 = offline (running on battery)
                return is_laptop, on_battery
        except Exception:
            pass
    return None, None

def build_profile():
    osname, osbuild, osrank = os_info()
    py = sys.version_info
    cores = os.cpu_count() or 2
    ram = ram_bytes(); ram_gb = round(ram / (1024**3), 1) if ram else 0
    gpu = gpu_info()
    disk = free_disk_gb(os.path.join(ROOT, "index")) or free_disk_gb(ROOT)

    modern_os = osrank >= 100           # Win10/11 — full suite supported
    py_ok = (py.major, py.minor) >= (3, 8)
    # GPU OCR only on a modern OS + working CUDA provider + new enough Python
    use_gpu = bool(gpu["onnx_cuda"] and modern_os and py_ok)

    # OCR worker count: bounded by cores AND usable RAM (~1.2 GB per worker), capped by tier.
    usable_gb = max(1.0, ram_gb - 2.0)            # leave ~2 GB for the OS
    by_ram = max(1, int(usable_gb // 1.2))
    # A strong discrete GPU (RTX / >=4 GB VRAM, e.g. RTX 4050) is the OCR bottleneck, so the CPU's
    # job is just to feed it (render PDF pages) — we can run more feeder workers to keep it saturated.
    gname = (gpu.get("name") or "").upper()
    strong_gpu = bool(use_gpu and (gpu.get("vram_mb", 0) >= 4000 or "RTX" in gname or " A" in gname))
    if use_gpu:           cap = 10 if strong_gpu else 8
    elif cores >= 8 and ram_gb >= 16: cap = 6     # strong CPU
    elif cores >= 4 and ram_gb >= 8:  cap = 3     # modest
    else:                 cap = 2                  # legacy / low
    workers = max(1, min(cores, by_ram, cap))

    # render DPI for OCR + the viewer's full-page HD ceiling, scaled to capability
    if use_gpu:           ocr_dpi, hd_cap = 220, 400
    elif cores >= 8 and ram_gb >= 16: ocr_dpi, hd_cap = 200, 360
    elif cores >= 4 and ram_gb >= 8:  ocr_dpi, hd_cap = 165, 300
    else:                 ocr_dpi, hd_cap = 130, 240

    # Laptop / battery awareness: leave thermal headroom on gaming laptops (GPU is the OCR bottleneck,
    # so fewer CPU feeder workers keeps it cool and stable); ease off further on battery.
    is_laptop, on_battery = power_info()
    if is_laptop and use_gpu:
        workers = min(workers, 8 if strong_gpu else 5)   # strong GPU laptop can feed more (GPU-bound)
    if is_laptop and not use_gpu and cores > 2:
        workers = min(workers, max(2, cores - 2))     # keep cores free so the machine stays responsive
    if on_battery:
        workers = max(1, min(workers, 3))

    # Max-performance opt-in: the user explicitly wants full throughput (GPU in max-perf mode).
    # Use most cores to feed the GPU and push DPI a touch for accuracy. Never on battery.
    perf = os.environ.get("VIEWER_OCR_MAX") == "1"
    if perf and use_gpu and not on_battery:
        workers = max(workers, min(max(2, cores - 1), 12))
        ocr_dpi = max(ocr_dpi, 240)

    if use_gpu: tier = ("GPU laptop" if is_laptop else "GPU workstation")
    elif cores >= 8 and ram_gb >= 16: tier = "Strong CPU"
    elif cores >= 4 and ram_gb >= 8:  tier = "Modest CPU"
    else: tier = "Legacy / low-power"

    # Available engines / tools — THE VIEWER substitutes per OS so every FEATURE works back to Vista.
    has_pymupdf = _have_module("fitz")
    has_pillow = _have_module("PIL")
    has_rapid = _have_module("rapidocr") or _have_module("rapidocr_onnxruntime")
    has_tesseract = bool(shutil.which("tesseract"))
    has_poppler = bool(shutil.which("pdftoppm") or shutil.which("pdftocairo"))
    render_backend = "pymupdf" if has_pymupdf else ("poppler" if has_poppler else "none")
    ocr_backend = ("gpu-rapidocr" if use_gpu and has_rapid else
                   "cpu-rapidocr" if has_rapid else
                   "tesseract" if has_tesseract else "none")

    # COMPLETE feature compatibility, Windows 11 down to Vista. Core features run everywhere via
    # OS-appropriate engines; GPU is an ACCELERATOR (Win10+), not a feature — OCR still completes on
    # Win7/Vista via Tesseract, and pages render via Poppler when PyMuPDF can't be installed.
    can_render = render_backend != "none"
    can_ocr = ocr_backend != "none"
    features = {
        "core_search_viewer_104th": True,                    # pure stdlib + SQLite + browser — universal
        "page_render": can_render,                           # PyMuPDF (modern) or Poppler (legacy)
        "ocr": can_ocr,                                      # RapidOCR (modern) or Tesseract (legacy)
        "gpu_acceleration": use_gpu,                         # Win10+ NVIDIA only — speed, not a feature
        "hd_render_loupe": can_render,
        "auto_snapshots_taskscheduler": True,                # schtasks exists Vista+
        "complete_core_all_os": True,                        # every feature works back to Vista
    }
    warnings = []
    if not modern_os:
        warnings.append("Legacy OS (%s): full feature set runs via the compatibility toolchain — page "
                        "render uses Poppler (pdftoppm) if PyMuPDF can't install, and OCR uses Tesseract "
                        "(CPU). Only NVIDIA *GPU acceleration* is Win10+; everything else works here." % osname)
    if render_backend == "poppler":
        warnings.append("Using Poppler to render pages (PyMuPDF not present) — install Poppler for Windows "
                        "and add its bin\\ to PATH so the viewer can show pages.")
    if render_backend == "none":
        warnings.append("No page renderer found. Install PyMuPDF (modern) OR Poppler for Windows (legacy) "
                        "so the viewer and OCR can rasterise pages.")
    if not has_rapid and has_tesseract:
        warnings.append("OCR will use Tesseract (RapidOCR not installed) — fine on older OS; install "
                        "Tesseract-OCR for Windows and add it to PATH if missing.")
    if not can_ocr:
        warnings.append("No OCR engine found. On Win10/11 the launchers install RapidOCR automatically; "
                        "on Win7/Vista install Tesseract-OCR for Windows (or OCR on a newer PC and copy the "
                        "finished index — the portable build supports this).")
    if not py_ok:
        warnings.append("Python %d.%d is older than 3.8. Win7: use Python 3.8 (the last that supports it). "
                        "Vista: use Python 3.4 + Poppler/Tesseract, or run a pre-built index from the "
                        "portable build (search/viewer/104th need only the standard library)." % (py.major, py.minor))
    if gpu["present"] and not gpu["onnx_cuda"]:
        warnings.append("An NVIDIA GPU was seen but CUDA isn't active in onnxruntime — run gpu_check.py "
                        "for the fix; OCR will use CPU until then.")
    if ram_gb and ram_gb < 4:
        warnings.append("Low RAM (%.1f GB): using minimal workers; close other apps during OCR." % ram_gb)
    if is_laptop:
        warnings.append("Gaming laptop detected: for the long OCR run, plug into AC power and keep vents "
                        "clear (use a cooling pad / max fans). Workers are tuned to leave thermal headroom "
                        "so it won't throttle or overheat.")
    if on_battery:
        warnings.append("Running on battery — OCR is throttled to %d worker(s). Plug in for full speed." % workers)

    prof = {
        "generated": __import__("time").strftime("%Y-%m-%d %H:%M:%S"),
        "os": osname, "os_build": osbuild, "os_rank": osrank, "modern_os": modern_os,
        "python": "%d.%d.%d" % (py.major, py.minor, py.micro), "python_ok": py_ok,
        "cpu_cores": cores, "ram_gb": ram_gb, "free_disk_gb": disk,
        "is_laptop": bool(is_laptop), "on_battery": bool(on_battery),
        "gpu": gpu, "strong_gpu": strong_gpu, "tier": tier, "performance_mode": perf,
        "use_gpu": use_gpu, "ocr_workers": workers, "ocr_dpi": ocr_dpi, "hd_render_cap": hd_cap,
        "render_backend": render_backend, "ocr_backend": ocr_backend,
        "features": features, "warnings": warnings,
    }
    # Recommended Retroactive-Post-Support runtime mode for THIS machine (Performance = full experience on
    # Win10/11 + RTX; the compatibility path on Win7/Vista or weak hardware). Computed by the rps module so
    # the launchers/UI can show a hardware-based recommendation without re-deriving the rule. Additive and
    # fail-open (R1): a missing rps module simply leaves these keys absent.
    try:
        import rps as _rps
        rmode, rreason = _rps.mode_for(prof, None)
        prof["recommended_run_mode"] = rmode
        prof["recommended_run_mode_reason"] = rreason
        prof["run_mode_ui"] = "performance" if rmode == "modern" else "retro"
    except Exception:
        pass
    return prof

def load_or_build():
    if os.path.exists(PROFILE):
        try: return json.load(open(PROFILE, encoding="utf-8"))
        except Exception: pass
    p = build_profile()
    try:
        os.makedirs(os.path.dirname(PROFILE), exist_ok=True)
        json.dump(p, open(PROFILE, "w", encoding="utf-8"), indent=2)
    except Exception: pass
    return p

def main():
    args = sys.argv[1:]
    if args and args[0] == "--get" and len(args) > 1:
        p = load_or_build(); v = p.get(args[1], "")
        print(v if not isinstance(v, bool) else ("1" if v else "0")); return 0
    p = build_profile()
    try:
        os.makedirs(os.path.dirname(PROFILE), exist_ok=True)
        json.dump(p, open(PROFILE, "w", encoding="utf-8"), indent=2)
    except Exception: pass
    if args and args[0] == "--json":
        print(json.dumps(p, indent=2)); return 0
    g = p["gpu"]
    print("=== THE VIEWER — system capability ===")
    print("OS            :", p["os"], "(build %s)" % p["os_build"] if p["os_build"] else "")
    print("Python        :", p["python"], "(ok)" if p["python_ok"] else "(too old — need 3.8+)")
    print("CPU cores     :", p["cpu_cores"], " RAM:", p["ram_gb"], "GB", " Free disk:", p["free_disk_gb"], "GB")
    print("GPU           :", (g["name"] or "none detected"),
          ("| CUDA active" if g["onnx_cuda"] else "| CUDA not active") if g["present"] else "")
    print("-" * 44)
    print("TIER          :", p["tier"])
    print("Render engine :", p["render_backend"], " OCR engine:", p["ocr_backend"])
    print("OCR           :", ("GPU" if p["use_gpu"] else "CPU"), "·", p["ocr_workers"], "workers ·", p["ocr_dpi"], "dpi")
    print("Viewer HD cap :", p["hd_render_cap"], "dpi")
    print("Compatibility : COMPLETE core features Windows 11 -> Vista (GPU acceleration is the only Win10+ extra)")
    if p.get("recommended_run_mode"):
        _lbl = "Performance" if p.get("run_mode_ui") == "performance" else "Retroactive Post-Support"
        print("Run mode      :", _lbl, "(recommended) —", p.get("recommended_run_mode_reason", ""))
    if p["warnings"]:
        print("\nNotes:")
        for w in p["warnings"]: print("  •", w)
    print("\nProfile written to index/hardware_profile.json — the launchers read it automatically.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
