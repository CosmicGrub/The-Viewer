#!/usr/bin/env python3
"""THE VIEWER -- user settings (small, durable, append-only-friendly key/value store).

Holds the handful of user-chosen preferences that must SURVIVE a restart -- today just the
Retroactive-Post-Support "run mode" choice picked in the Settings panel. Kept deliberately tiny and
dependency-free so it loads on every OS back to Vista (pure stdlib).

Design (R1 backwards-compatible, R6 append-only, R13 fail-loud on writes):
  * File is index/viewer_settings.json -- a flat JSON object. Missing file / bad JSON => {} (fail-open
    on READ so a corrupt settings file never stops the app from launching).
  * Writes go through safeguard.atomic_write (fsync + retry) when available, else a temp-file + os.replace
    fallback. set() returns True/False so callers can surface a failure instead of silently losing it.
  * We only ever ADD keys we understand; unknown keys are preserved untouched on write (never clobbered),
    so an older build reading a newer settings file -- or vice-versa -- loses nothing.

CLI:
  python settings.py                 # print the current settings JSON
  python settings.py get KEY         # print one value ("" if absent)
  python settings.py set KEY VALUE   # persist KEY=VALUE, print the resulting JSON
"""
import os, json

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SETTINGS_PATH = os.path.join(ROOT, "index", "viewer_settings.json")

# The Settings-panel run-mode choices. These are the USER-FACING intent; rps.mode_for_setting() maps
# them onto the concrete engine modes (modern / lite / legacy) using the hardware probe.
VALID_RUN_MODES = ("auto", "performance", "retro")


def load():
    """Return the settings dict. Fail-OPEN: a missing or corrupt file yields {} so the app still starts."""
    try:
        with open(SETTINGS_PATH, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def get(key, default=None):
    return load().get(key, default)


def set(key, value):
    """Persist key=value durably, PRESERVING every other key. Returns True on success, False on failure
    (fail-loud: the caller decides how to report it -- we never pretend a lost write succeeded)."""
    data = load()
    data[key] = value
    blob = json.dumps(data, indent=2, sort_keys=True)
    # Prefer the hardened durable writer (fsync + Windows replace-retry); fall back to a plain atomic
    # rename so settings still persist even if safeguard can't be imported (e.g. a stripped portable build).
    try:
        import safeguard
        safeguard.atomic_write(SETTINGS_PATH, blob)
        return True
    except Exception:
        pass
    try:
        os.makedirs(os.path.dirname(SETTINGS_PATH), exist_ok=True)
        tmp = SETTINGS_PATH + ".tmp%d" % os.getpid()
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(blob)
            f.flush()
            try:
                os.fsync(f.fileno())
            except Exception:
                pass
        os.replace(tmp, SETTINGS_PATH)
        return True
    except Exception:
        return False


def normalize_run_mode(value):
    """Coerce any input to a valid run-mode choice; unknown/blank => 'auto'. Accepts a few friendly
    aliases so the UI and env vars can be liberal in what they send."""
    s = str(value or "").strip().lower()
    aliases = {
        "performance": "performance", "perf": "performance", "modern": "performance", "full": "performance",
        "retro": "retro", "rps": "retro", "retroactive": "retro", "compat": "retro",
        "compatibility": "retro", "lite": "retro", "legacy": "retro",
        "auto": "auto", "": "auto", "default": "auto",
    }
    return aliases.get(s, "auto")


def main(argv):
    if not argv:
        print(json.dumps(load(), indent=2, sort_keys=True))
        return 0
    cmd = argv[0]
    if cmd == "get" and len(argv) > 1:
        v = get(argv[1], "")
        print(v if not isinstance(v, (dict, list)) else json.dumps(v))
        return 0
    if cmd == "set" and len(argv) > 2:
        ok = set(argv[1], argv[2])
        print(json.dumps(load(), indent=2, sort_keys=True))
        return 0 if ok else 1
    print("usage: settings.py [get KEY | set KEY VALUE]")
    return 2


if __name__ == "__main__":
    import sys
    sys.exit(main(sys.argv[1:]))
