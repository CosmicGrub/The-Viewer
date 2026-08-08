# THE VIEWER — Iteration Screenshots (R10)

Per **R10 (amended)**, each iteration's snapshot must be a **literal screenshot of the running app** — the real page
as it renders at `http://127.0.0.1:8765`, exactly as you'd see it using the app. Files here are named
`<version>-<page>.png` (e.g. `0.99.18-jobcard.png`).

## How they get captured
Real screenshots need a browser Claude can drive against the running app. Two ways:

1. **Best — connect the Claude-in-Chrome extension.** Then Claude navigates to each route below and captures a real
   screenshot into this folder automatically, every iteration.
2. **Manual — you bring a page to the foreground** in your browser (e.g. open `http://127.0.0.1:8765/jobcard`) and
   Claude takes a computer-use screenshot of it. (At "read" tier Claude can screenshot but can't navigate itself.)

The app must be running (`RUN-VIEWER.bat`).

## Routes to capture (the core pages / recent features)
| Route | What it shows |
|---|---|
| `/` | Home — search, side chooser, Tools menu, ⌘K pill |
| `/jobcard` | Work Order builder (v0.99.9–0.99.10) — preview + ⚠ look-alike compare |
| `/locate` | Cross-figure part locator (v0.99.6) — 🖨 Figure sheet · 🧾 Work Order |
| `/coverage` | Coverage dashboard (v0.99.6) — OCR / CAD / vectorize / netlists |
| `/deepzoom?doc=<id>&page=<n>` | Deep-zoom + callout hotspots + 🧩 Parts-on-page (v0.99.3/0.99.8) |
| `/partdiff` | Look-Alike Parts recognizer (v0.43) |
| `/dossier` | Unified part dossier (v0.52) |
| `/procedure` | How-to / procedure view (v0.47) |
| `/ingest` | Add documents — drag-drop + Recent paths (v0.99.15) |
| `/circuitlab` | Circuit Lab overlay editor + simulator (v0.42/0.44) |
| `/schematics` · `/3d` | Schematic + 3-D libraries |
| (Ctrl+K on any page) | Command palette with Recent + tag search (v0.99.11/0.99.13) |

<!-- END OF FILE -->
