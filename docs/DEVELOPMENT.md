# THE VIEWER — Development & Anti-Truncation Protocol

This program is large and data-heavy, and we **cannot afford to lose progress**. This doc is the
standing routine that keeps every change safe and verifiable. It exists because of one specific
hazard described below.

## The hazard: stale / truncated sandbox reads

When work is done through an AI sandbox, the assistant edits files on the **Windows side** (the real
files), but the sandbox's Linux shell sees those files through a **cached mount**. For a large file
that has grown (e.g. `engine/viewer_app.py`), that mount can cache an **old file size** and return a
**truncated read** — only the first N bytes — even though the real file on disk is complete.

**What this is — and isn't:**
- It is a *read-side* artifact of the sandbox. The real files in `THE VIEWER\` are **complete and
  correct**; they are written by authoritative tools, not the cached mount.
- It is **not** corruption or data loss on disk. The host file is whole.
- The risk it creates is **false validation**: an in-sandbox `python import` or `node --check` can
  fail or pass against a truncated copy, which is misleading. A `git commit` or a `safeguard snapshot`
  run *inside the sandbox* could capture truncated files — so those must run **host-side**.

## Two ironclad rules

1. **Run safeguard and verify on Windows (the host), never in a sandbox.** Host-side reads are
   coherent; sandbox reads may be truncated. `run_safeguard.bat` and `VERIFY-ALL.bat` both say so.
2. **Trust authoritative reads, not sandbox bash reads, when validating.** Confirm code via the
   editor's own file view / `grep` over the real file, and validate logic with **isolation tests**
   (replicate the function's logic on a temp fixture) rather than importing a possibly-truncated
   module.

## The safety net (already built): `safeguard.py`

`engine/safeguard.py` snapshots every critical file with SHA-256, and its `verify` command classifies
damage — **TRUNCATED** (lost a clean prefix), SHRUNK, CORRUPTED, EMPTY, MISSING, MODIFIED — and
`recover` restores any file **byte-for-byte** from the vault. It's covered by `tests/test_truncation.py`.

```
run_safeguard.bat snapshot          # save a versioned copy of every critical file -> backups\vault\SNAP_*
run_safeguard.bat snapshot /withdb  # also store a consistent copy of viewer.db (large)
run_safeguard.bat verify            # check current files vs the latest snapshot (flags TRUNCATED etc.)
run_safeguard.bat recover /all      # restore everything from the latest snapshot
run_safeguard.bat list              # list snapshots
```

## The pre/post-change checklist

Do this around every change session (it takes seconds):

**Before changing anything**
1. `run_safeguard.bat snapshot` — baseline the current known-good state (host-side).
2. Note the snapshot id printed (e.g. `SNAP_20260603_044300`).

**After the change**
3. `VERIFY-ALL.bat` — runs the regression suites **and** `safeguard verify` in one shot. This is
   the fast, routine check for this loop, not the repo root's `VERIFY.bat` (the full pre-release
   gate) — the two aren't competing, they're tiered by cost/occasion: use `VERIFY-ALL.bat` here,
   every time; run `VERIFY.bat` (and `RUN-ALL-VERIFY.bat` for the slower fuzz/mutation passes)
   before a release or milestone. See the repo root `README.md` for the full verify-script tiering.
   A fourth tier now runs with no local action needed: every push and PR to `main` triggers GitHub
   Actions CI (`.github/workflows/ci.yml`), which runs `python tests/verify_all.py --snapshot` on a
   clean checkout — a backstop gate this loop's local `VERIFY-ALL.bat` doesn't replace, since a
   change can still be pushed without anyone having run it by hand.
4. Read the summary line:
   - `ALL GREEN` → suites pass and every protected file matches the vault. Done.
   - Any file shown `TRUNCATED` / `SHRUNK` → the file on disk was damaged; restore it:
     `run_safeguard.bat recover /all`, then re-run `VERIFY-ALL.bat`.
   - A suite `FAIL` → a real regression; fix it (or recover the touched file and retry).
5. If green and the change is a milestone, take a fresh labelled snapshot:
   `run_safeguard.bat snapshot` (and `gc` keeps the last 10).

**One-liners**
```
VERIFY-ALL.bat            # tests + truncation/corruption verify vs latest snapshot
VERIFY-ALL.bat /snapshot  # take a fresh snapshot first, then verify (use on first run)
```

## What's protected

`safeguard.py` `CRITICAL_GLOBS` covers `engine/**/*.py`, `engine/ui/*.{html,js,css}`, `engine/*.bat`,
`engine/migrations/*.sql`, `docs/*.md`, `docs/diagrams/*.{py,svg}`, and the small derived sidecars
(`correlations.db`, `collections.db`, `reviews.db`). The multi-GB `viewer.db` is tracked by size +
SQLite `integrity_check`, and copied consistently only with `snapshot /withdb` (online-backup API, safe
while the app runs). The read-only corpus on `E:\` is source data and is intentionally not snapshotted.

## Keeping files small (the durable fix)

The truncation gets worse the larger a file grows. The long-term mitigation is to keep modules **small**
— `viewer_app.py` is being split into focused feature modules it imports, so each file stays well under
the size where the mount turns flaky and in-sandbox imports/tests become reliable again. New features
should land as their own module where practical rather than growing one giant file.
