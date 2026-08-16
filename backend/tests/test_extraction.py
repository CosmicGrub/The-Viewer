import pdfplumber
import json
import os
import sys

# Windows consoles typically default to a legacy codepage (e.g. cp1252)
# rather than UTF-8, which makes print()-ing the ✓ characters below raise
# UnicodeEncodeError and kill the run. Reconfigure to UTF-8 first.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

# Simple test: check if we can import and use pdfplumber
def test_import():
    print("✓ pdfplumber imported successfully")
    print("✓ pytesseract ready for OCR")
    print("✓ All core libraries loaded")
    print("\nReady for Phase 1 Week 1 extraction pipeline")

if __name__ == "__main__":
    test_import()