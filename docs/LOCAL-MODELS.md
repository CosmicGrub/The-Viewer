# Local 3-D models — drop your own CAD into the viewer

THE VIEWER shows a **representative placeholder** for each part (the parametric / CAD geometry scaled to FLIS
dimensions). If you have a **real model file** for a part, you can drop it in and the 3-D viewer will load *that*
instead — authoritative, not an approximation.

## How to add one

1. Put the file in the sidecar folder (created automatically):

   ```
   index\models3d\<NSN>.obj      (or .stl)
   ```

   Name it by the part's **NSN**, e.g. `index\models3d\5305-01-674-1467.obj`.

2. Open that part in the **3-D library** and click the **◳ Interactive 3-D** tab. Your model loads in place of the
   placeholder, auto-centred and auto-fit. A green **🧩 LOCAL 3-D MODEL** badge appears in the side panel with a
   one-click toggle back to the representative placeholder.

## Supported formats

| Format | Notes |
|--------|-------|
| **OBJ** (`.obj`) | `v` / `f`; n-gons are triangulated; 1-indexed and negative indices supported. |
| **STL** (`.stl`) | Both **ASCII** and **binary** STL. |

- Models are read **on demand** and parsed to `{V,F}` for the WebGL viewer (`gl3d.js`). Faces are capped at 300k
  for responsiveness.
- Units don't matter — the viewer fits the model to the frame. (Materials/colour still come from the FLIS/scan
  record so it matches the rest of the part card.)
- This is a **read-only sidecar** (`index/models3d/`). The corpus and the index are never touched (R1/R6).

## Authoritative vs. approximation

This is the **authoritative** path — your own file, shown without a watermark. It is separate from the
**experimental image→3D "Approximation"** tab (`docs/IMAGE3D-SETUP.md`), which is AI-generated, gated, and always
watermarked "ARTISTIC APPROXIMATION — NOT TO SCALE."

## API (for scripts)

- `GET /api/localmodel?nsn=<NSN>` → `{exists, fmt, mesh_url, filename, dir}`
- `GET /api/localmodel_mesh?nsn=<NSN>` → `{V, F, local:true, fmt, faces, verts}` (404 JSON if none)
