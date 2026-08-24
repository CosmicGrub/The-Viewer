#!/usr/bin/env python3
"""THE VIEWER -- check the 3-D / part-imagery prerequisites and report what each one enables.

The 3-D VIEWER itself (WebGL parametric models, materials, the parametric CAD panel) needs NOTHING -- it's
browser JavaScript and already runs offline. These dependencies are for the IMAGERY pipeline that feeds it:
  PyMuPDF (fitz)  -> render/crop the cited figure (breakdown image) from the PDF      [REQUIRED]
  Pillow (PIL)    -> image handling for the crop + OCR pass                            [REQUIRED]
  numpy           -> the row ink-density fallback that tightens scanned-page crops     [recommended]
  pytesseract     -> OCR word-boxes for the precise caption / item-callout crop        [optional]
  tesseract (exe) -> the engine pytesseract drives (a separate Windows install)        [optional]

Exit 0 if the REQUIRED ones are present, else 1.
"""
import importlib, shutil, sys

CHECKS = [
    ("pymupdf", "PyMuPDF", True, "render + crop the cited figure (breakdown image)"),
    ("PIL", "Pillow", True, "image handling for crops + OCR"),
    ("numpy", "numpy", False, "row ink-density fallback for scanned-page crops"),
    ("pytesseract", "pytesseract", False, "OCR word-boxes for the precise caption / callout crop"),
]


def main():
    print("=== THE VIEWER -- 3-D / imagery prerequisites ===\n")
    missing_required = []
    for mod, name, required, what in CHECKS:
        try:
            m = importlib.import_module(mod)
            ver = getattr(m, "__version__", "") or getattr(m, "version", "")
            print("  [ OK ] %-12s %-10s -> %s" % (name, ("v" + str(ver)) if ver else "", what))
        except Exception:
            tag = "MISS*" if required else "miss "
            print("  [%s] %-12s %-10s -> %s" % (tag, name, "", what))
            if required:
                missing_required.append(name)
    # the tesseract binary (not a pip package)
    tpath = shutil.which("tesseract")
    if tpath:
        print("  [ OK ] %-12s %-10s -> %s" % ("tesseract", "", "OCR engine (%s)" % tpath))
    else:
        print("  [miss ] %-12s %-10s -> %s" % ("tesseract", "", "optional OCR engine -- see install note"))

    print()
    if missing_required:
        print("RESULT: missing REQUIRED: %s" % ", ".join(missing_required))
        print("  Install with:  python -m pip install pymupdf pillow numpy pytesseract")
        return 1
    print("RESULT: required prerequisites present -- figure crops will work.")
    if not tpath:
        print("  (optional) Tesseract not found. The precise caption/callout crop uses it; without it the")
        print("  density fallback still tightens scanned crops, or set VIEWER_FIGCROP_OCR=0 to skip OCR.")
        print("  Windows installer: https://github.com/UB-Mannheim/tesseract/wiki")
    return 0


if __name__ == "__main__":
    sys.exit(main())
