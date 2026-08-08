# Local image→3D approximation (EXPERIMENTAL, opt-in)

This is a **scaffold**, off by default. It can turn a part's cited figure crop into a rough 3D mesh using a
**local** model that runs on **your GPU** — shown only in the 3D modal's *Approximation* tab, always
watermarked **"ARTISTIC APPROXIMATION — NOT TO SCALE."**

> ⚠️ **Not authoritative.** AI-generated geometry is an approximation, never engineering-accurate. Do not use
> it for fit, clearance, machining, or any maintenance-critical decision. The authoritative image is the
> **Manual illustration** tab (the manual's own cited figure). Keep this feature off for those decisions.

## How it works
1. You enable the *approximation view* checkbox in the 3D modal.
2. THE VIEWER takes the part's figure crop (`/figcrop`, the same PNG used by the Manual illustration tab).
3. It runs **your configured command** to convert that PNG → an OBJ mesh, cached in `index/mesh3d/<nsn>.obj`
   (sidecar — the index is never written).
4. The mesh loads in the WebGL viewer, watermarked.

## Configure a backend (one of)
- **Environment variable:**
  ```
  set VIEWER_IMG3D_CMD=python C:\models\triposr_run.py "{in}" "{out}"
  ```
- **Or a file** `engine/image3d_backend.txt` containing the same one-line template.

`{in}` is replaced with the input PNG path, `{out}` with the target OBJ path. Your script must read the image
and write a Wavefront **.obj** to `{out}` (v/f lines; triangulated or polygonal — THE VIEWER triangulates).

## Example backends (you install these yourself, locally)
- **TripoSR** (fast single-image→mesh, runs on a 6 GB GPU): wrap its inference in a small script that takes
  `{in}`/`{out}`.
- **InstantMesh / Shap-E / Wonder3D**: same pattern — a CLI that writes an OBJ.
- A trivial **test backend** (no GPU) to prove the pipeline: a script that writes a unit cube OBJ to `{out}`.

## Why it's gated
- Models are large, GPU-specific, and license-varied — not something to bundle.
- It must never be mistaken for accurate CAD. The gating + watermark + "not configured" default keep it honest.

## Endpoints (reference)
- `GET  /api/image3d?nsn=` → `{configured, exists, mesh_url, note, setup}`
- `POST /api/image3d` `{nsn}` → runs the backend (only if configured), returns status
- `GET  /api/image3d_mesh?nsn=` → `{V,F,approx:true}` for the WebGL viewer

If no backend is configured, the Approximation tab simply shows the parametric shape as a placeholder with a
pointer to this document — nothing breaks, and the RPS/legacy build is unaffected (it just stays off).
