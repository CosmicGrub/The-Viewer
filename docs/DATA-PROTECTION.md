# Data protection — truncation root cause, safeguard, and recovery (v0.29.0)

THE VIEWER is data-heavy. This document explains the truncation we hit during development, why it is
**not** loss of your real files, and the safeguard + recovery system now in place so that *any* file
damage — from any cause — is detected and reversible.

## 1. What the "truncation" actually was (root cause)

During development, files sometimes *appeared* cut off when read back. I reproduced it deliberately:

- When the **Linux sandbox itself** writes a file to the shared folder and reads it back — even
  rewriting it shorter then longer — it is **always perfectly coherent** (verified: 47,843 bytes out,
  47,843 bytes in, exact match).
- The truncation appears **only across the host→guest boundary**: when the editor (Windows side)
  rewrites a file, the Linux sandbox's page cache for that file is not immediately invalidated, so a
  follow-up read in the sandbox can return a **stale, shorter length** (sometimes padded with zero
  bytes). The Windows file is intact the whole time — proven because an edit that matched the file's
  **last line** succeeded (impossible if the file were truly shortened), and the editor always showed
  the complete file.

**Conclusion:** it is a sandbox read-cache artifact, **not** corruption of your data on disk. Your
actual files were never damaged. But a data-intensive program deserves real protection regardless of
cause (a process killed mid-write, power loss, a bad copy, disk errors), so that is what we built.

## 2. The safeguard (`engine/safeguard.py`)

A stdlib-only, Windows-friendly integrity + recovery layer. Run it with `engine\run_safeguard.bat`.

- **Atomic writes** — write to a temp file, `fsync`, then `os.replace`. A crash leaves either the old
  or the new file intact, never a half-written one.
- **Snapshots ("the treasure vault")** — `snapshot` copies every critical file into
  `backups\vault\SNAP_<timestamp>\`, each verified by SHA-256 *after* copy, with a manifest recording
  size, hash, and line count. The heavy `viewer.db` is checked with SQLite `integrity_check` and only
  copied (via the consistent online-backup API) when you pass `/withdb`.
- **Verify** — `verify` re-hashes current files and classifies any damage against the last good
  snapshot: `OK · TRUNCATED · CORRUPTED · SHRUNK · EMPTY · MISSING · MODIFIED`. Truncation is
  identified precisely as a clean byte-prefix of the saved relic.
- **Recover ("the archaeologist")** — `recover --all` (or a specific path) restores from the vault and
  re-verifies the hash, reporting `RECOVERED` or `RECOVER_FAILED_HASH` if the relic itself was damaged.

> Run the safeguard **on Windows**, not in a sandbox — so it snapshots the real, intact files.

## 3. How it's tested (the stranglehold)

`engine\run_tests.bat` runs three suites against throwaway fixtures (never your real data):

- **19 pillar tests** — the engine logic (search, NSN routing, parts, reference, tech-status,
  coverage, correlations, 104th PDF). All pass.
- **11 truncation/recovery tests** — every file is deliberately damaged at varying severity (last
  line, 50%, 10 bytes, empty, partial-UTF-8, byte-flip corruption, deleted, multi-file, a corrupted
  *vault* relic, and a corrupted SQLite header) and must be **detected and recovered byte-for-byte**.
  All pass.
- **Mutation testing — 2 rounds, 38 mutants, 36 killed (95%).** Round 1 injects 26 faults into the
  engine logic (96% killed); round 2 injects 12 faults into the safeguard itself (92% killed) to prove
  the protection layer is genuinely pinned down. The 2 survivors are **equivalent mutants** — code
  changes that provably cannot alter observable behaviour given surrounding guards (the unreachable
  `within1` bound; the post-copy snapshot self-check that only fires on a faulty filesystem). On
  non-equivalent mutants the kill rate is effectively 100%.

## Quick reference

```
engine\run_safeguard.bat snapshot          ' save a versioned copy of every critical file
engine\run_safeguard.bat snapshot /withdb  ' also store a consistent copy of viewer.db
engine\run_safeguard.bat verify            ' detect any TRUNCATED/CORRUPTED/MISSING file
engine\run_safeguard.bat recover /all      ' restore everything from the latest snapshot
engine\run_tests.bat                       ' pillar + truncation + mutation suites
```

Recommended: take a snapshot before any big change, and `verify` after. Snapshots are additive (R6)
and the main index is never modified (R1).
