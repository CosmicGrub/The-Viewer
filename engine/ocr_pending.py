#!/usr/bin/env python3
"""Print the number of pages still needing OCR (pending + running). Used by run_ocr_auto.bat to
decide whether to keep looping. Usage: python ocr_pending.py [--db PATH]"""
import sqlite3, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
db = os.path.join(HERE, "..", "index", "viewer.db")
a = sys.argv[1:]
for i, x in enumerate(a):
    if x == "--db" and i+1 < len(a): db = a[i+1]
try:
    c = sqlite3.connect("file:%s?mode=ro" % db, uri=True)
    print(c.execute("SELECT COUNT(*) FROM pages WHERE ocr_status IN ('pending','running')").fetchone()[0])
except Exception:
    print(-1)
