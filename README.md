# The-Viewer
A project/successor to the EMSVIEWER

**THE VIEWER** — an offline technical-manual search & parts-catalog engine (see `docs/ARCHITECTURE.md`
for the full picture).

## Platform

Windows-only, single-user local desktop tool (Windows 7 through 11 — see `docs/SYSTEM-REQUIREMENTS.md`).
All operational tooling is `.bat`; cross-platform (Linux/Mac) support is out of scope by design, not an
oversight — see `docs/PORTING.md` for the (also Windows-to-Windows) porting workflow.

## Getting started

New to this project? Run **`START-HERE.bat`** — it is the single authoritative entry point (option 6
opens `VIEWER-MENU.bat` for the full task menu).

Verification has a deliberate tiering, not four competing scripts:
- **`engine\VERIFY-ALL.bat`** — fast, routine check for the after-every-change edit loop (see
  `docs/DEVELOPMENT.md`). Use this day-to-day.
- **`VERIFY.bat`** — the full, authoritative verification gate. Use before a release/milestone.
- **`VERIFY-099.bat`** — a compatibility forwarder to `VERIFY.bat`, kept only because other
  scripts/docs still reference it by name. Don't add new references to it.
- **`RUN-ALL-VERIFY.bat`** — `VERIFY.bat` plus HTTP fuzz + mutation testing (slower). Use before a
  release, alongside `VERIFY.bat`.
