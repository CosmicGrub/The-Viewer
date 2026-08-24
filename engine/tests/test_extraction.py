#!/usr/bin/env python3
"""Regression guard for the v1.1 extraction -> enrichment -> Masterfile pipeline (measures / tables / enrich /
masterfile). Self-contained: temp DBs + fake network, no corpus needed. Runs host-side via VERIFY-099 (in-sandbox the
mount can truncate the grown modules, so run it on the real tree). Exit 0 = all pass."""
import os, sys, json, tempfile, sqlite3

HERE = os.path.dirname(os.path.abspath(__file__))
ENG = os.path.dirname(HERE)
sys.path.insert(0, ENG)

import measures, enrich, masterfile  # noqa: E402
try:
    import tables
except Exception:
    tables = None

FAILS = []


def check(name, cond):
    print(("  ok  " if cond else "  FAIL") + "  " + name)
    if not cond:
        FAILS.append(name)


def test_measures():
    s = ("Torque bolts to 30-35 ft-lb. Pressure 32 psi. Oil 6 qt. Length 180 in, width 85 in. "
         "Curb weight 5,200 lb. Clearance .015 +/- .002 in. 28 VDC at 100 A. Coolant 12 L. "
         "-25 degF to 120 degF. 18 in-lb. 700 rpm. 4 gpm. 15 deg. 45 N-m.")
    rows = measures.extract(s, page=7)
    types = {r["type"] for r in rows}
    for need in ("torque", "pressure", "capacity", "length", "weight", "electrical", "temperature", "rotation",
                 "flow", "angle"):
        check("measures finds %s" % need, need in types)
    check("measures carries page", all(r.get("page") == 7 for r in rows))
    check("measures range captured", any(r["value2"] for r in rows))
    check("measures tolerance captured", any(r["tolerance"] for r in rows))
    check("by_type sums", sum(measures.by_type(s).values()) == len(rows))
    # compound-unit precedence: 'ft-lb' must classify as torque, not length
    check("ft-lb is torque not length", any(r["unit"] == "ft-lb" and r["type"] == "torque" for r in rows))
    check("in-lb is torque not length", any(r["unit"] == "in-lb" and r["type"] == "torque" for r in rows))


def test_measures_bare_temperature():
    # v1.13.5: bare F/C (no deg-word or degree-symbol) -- must extract the real readings AND must NOT
    # collide with military designators (F-15/F-16/C-130/F-A-18 style) or battery C-rate notation, both
    # of which are genuinely common in this corpus.
    s = ("Operating range is -40 F to 120 F. The flight line has 5 F-16 fighters and 2 C-130 transports "
         "plus an F/A-18 on static display. Charge the battery at a 0.5C rate. Storage temp -20 C max.")
    rows = measures.extract(s, page=9)
    temps = [r for r in rows if r["type"] == "temperature"]
    check("bare F -40 extracted", any(r["unit"] == "degF" and r["value"] == "-40" for r in temps))
    check("bare F 120 extracted", any(r["unit"] == "degF" and r["value"] == "120" for r in temps))
    check("bare C -20 extracted", any(r["unit"] == "degC" and r["value"] == "-20" for r in temps))
    check("no designator/C-rate false positives (exactly 3 real readings)", len(temps) == 3)
    # v1.13.5 fix: document callouts are the OTHER high-frequency "<number> <letter>" shape in a TM, and
    # unlike the designator/C-rate forms they put a real space there -- so the whitespace rule above
    # ACCEPTS them. Every one of these extracted a bogus temperature before _CALLOUT was added.
    callouts = ["FIGURE 5 C shows the pump assembly.",
                "Refer to TABLE 3 F for torque values.",
                "Install item 2 C and item 4 F as shown.",
                "Use Grade 8 F bolts throughout.",
                "Class 2 C wiring is required.",
                "DETAIL 7 C, SHEET 2 F"]
    for s in callouts:
        got = [r for r in measures.extract(s) if r["type"] == "temperature"]
        check("callout not read as temperature: %s" % s[:28], not got)
    # ...while genuine readings that merely follow a callout reference still extract.
    real = measures.extract("See FIGURE 5 for the curve. Operating limit is 120 F at sea level.")
    check("real temp after a callout still extracted",
          any(r["unit"] == "degF" and r["value"] == "120" for r in real))


def test_measures_unbroken_digit_run_not_truncated():
    # v1.13.6: _NUM used to cap a comma-less digit run at \d{1,6}. For a longer unbroken run (garbled OCR /
    # an impossible value, e.g. a 9-digit torque figure), the cap didn't reject the number -- finditer just
    # backtracked to a start position mid-run and silently matched that run's OWN trailing 6 digits
    # ("350000000" -> "000000"), so the extracted value looked like a plausible near-zero reading instead of
    # the impossible one that was actually in the source text. The full, untruncated digit string must now
    # reach downstream validation (validate.py already quarantines it correctly -- see test_validate.py-style
    # coverage in validate.py's own self-test).
    rows = measures.extract("Torque the nut to 350000000 ft-lb.")
    check("9-digit unbroken torque value not truncated to a 6-digit suffix",
          any(r["type"] == "torque" and r["value"] == "350000000" for r in rows))
    check("9-digit unbroken torque value is NOT the truncated '000000'",
          not any(r["value"] == "000000" for r in rows))
    # legitimate <=6-digit unbroken numbers and comma-grouped large numbers must still work unchanged
    rows2 = measures.extract("Torque the nut to 123456 ft-lb. Curb weight 1,234,567 lb.")
    check("legit 6-digit unbroken value still extracted", any(r["value"] == "123456" for r in rows2))
    check("comma-grouped large value still extracted whole", any(r["value"] == "1,234,567" for r in rows2))


def test_enrich():
    def fake(url, timeout=20):
        if "wayback/available" in url:
            return json.dumps({"archived_snapshots": {"closest": {
                "available": True, "url": "http://web.archive.org/web/20210101/x", "timestamp": "20210101000000"}}})
        if "web.archive.org/web/" in url:
            return "<html><body><p>Fuel 25 gal.</p><style>a{}</style><script>z()</script></body></html>"
        return ""
    snap = enrich.wayback_snapshot("http://ex/tm", fake)
    check("wayback snapshot parsed", snap and snap["timestamp"] == "20210101000000")
    txt, wurl, wts = enrich.fetch_via_wayback("http://ex/part", fake)
    check("wayback fetch strips html", "Fuel 25 gal" in txt and "<script" not in txt and "z()" not in txt)
    check("wayback ts returned", wts == "20210101000000")
    check("no-snapshot returns none w/o save", enrich.wayback_get_or_save("http://ex", lambda u, timeout=20: "{}") is None)
    # seeds
    d = tempfile.mkdtemp(); sp = os.path.join(d, "seeds.txt")
    open(sp, "w").write("# c\nhttps://g/a\nHMMWV | https://h/specs\n")
    check("seeds global pass", enrich.seed_links(sp) == ["https://g/a", "https://h/specs"])
    check("seeds subject-scoped", enrich.seed_links(sp, subject="HMMWV") == ["https://h/specs"])
    check("web_links empty w/o provider", enrich.web_links("q", None) == [])
    # record gap-only + corpus-authoritative read filter
    edb = os.path.join(d, "enrich.db")
    rows = [{"type": "capacity", "unit": "gal", "value": "25", "value2": None, "tolerance": None,
             "raw": "25 gal", "context": "Fuel 25 gal"},
            {"type": "weight", "unit": "lb", "value": "9999", "value2": None, "tolerance": None,
             "raw": "9999 lb", "context": "bogus"}]
    n = enrich.record(edb, "HMMWV", "HMMWV", rows,
                      {"source": "wayback", "source_url": "http://web.archive.org/web/20210101/x",
                       "orig_url": "http://ex/part", "wayback_ts": "20210101000000"}, only_types={"capacity"})
    check("record keeps only gap type", n == 1)
    res = enrich.external_for_query(edb, "HMMWV", corpus_types={"weight"})
    check("external filtered by corpus types", res["count"] == 1 and "capacity" in res["by_type"]
          and "weight" not in res["by_type"])


def test_masterfile():
    d = tempfile.mkdtemp()
    dbp = os.path.join(d, "viewer.db"); mdb = os.path.join(d, "measures.db")
    edb = os.path.join(d, "enrich.db"); mf = os.path.join(d, "master.db")
    a = sqlite3.connect(dbp)
    a.execute("CREATE TABLE documents(id INTEGER PRIMARY KEY, vehicle TEXT)")
    a.execute("INSERT INTO documents VALUES(1,'HMMWV')"); a.commit(); a.close()
    m = sqlite3.connect(mdb)
    m.execute("CREATE TABLE meas(doc INT,page INT,type TEXT,unit TEXT,value TEXT,value2 TEXT,tolerance TEXT,context TEXT)")
    m.executemany("INSERT INTO meas VALUES(?,?,?,?,?,?,?,?)",
                  [(1, 5, "length", "in", "180", None, None, "len 180 in"),
                   (1, 5, "weight", "lb", "7700", None, None, "wt 7700 lb")])
    m.commit(); m.close()
    e = sqlite3.connect(edb)
    e.execute("CREATE TABLE ext_meas(subject TEXT,subject_label TEXT,type TEXT,unit TEXT,value TEXT,value2 TEXT,"
              "tolerance TEXT,context TEXT,source TEXT,source_url TEXT,orig_url TEXT,wayback_ts TEXT,fetched_ts REAL,"
              "confidence REAL,status TEXT)")
    e.executemany("INSERT INTO ext_meas(subject,subject_label,type,unit,value,context,source_url) VALUES(?,?,?,?,?,?,?)",
                  [("hmmwv", "HMMWV", "capacity", "gal", "25", "Fuel 25 gal", "http://web.archive.org/z"),
                   ("hmmwv", "HMMWV", "weight", "lb", "9999", "bogus", "http://web.archive.org/z2")])
    e.commit(); e.close()
    summ = masterfile.build(dbp, mdb, edb, mf, md_path=os.path.join(d, "MASTERFILE.md"))
    check("masterfile built", summ["subjects"] == 1 and summ["corpus"] == 2 and summ["external"] == 1)
    res = masterfile.for_subject(mf, "HMMWV")
    ft = {(f["type"], f["origin"]) for f in res["filtered"]}
    check("masterfile keeps corpus", ("length", "corpus") in ft and ("weight", "corpus") in ft)
    check("masterfile fills gap", ("capacity", "external") in ft)
    check("masterfile corpus-authoritative", ("weight", "external") not in ft)
    blob = repr(res["filtered"]) + repr([{k: v for k, v in r.items() if k != "page_url"} for r in res["raw"]])
    check("masterfile surfaces NO links", "http://" not in blob and "web.archive" not in blob)
    check("corpus rows cite authoritative page", any(r["page_url"] for r in res["raw"] if r["origin"] == "corpus"))
    check("external rows have no ref", all(not r["page_url"] for r in res["raw"] if r["origin"] == "external"))
    md = open(os.path.join(d, "MASTERFILE.md"), encoding="utf-8").read()
    check("masterfile md has no links", "http" not in md)


def test_tables():
    if tables is None or not tables.available():
        print("  skip  tables (PyMuPDF not installed)"); return
    import pymupdf as fitz
    doc = fitz.open(); pg = doc.new_page(width=400, height=300)
    for i in range(4):
        y = 60 + i * 30; pg.draw_line((40, y), (360, y))
    for j in range(4):
        x = 40 + j * 107; pg.draw_line((x, 60), (x, 150))
    for r, row in enumerate([["ITEM", "DIM", "UNIT"], ["Length", "180", "in"], ["Weight", "5200", "lb"]]):
        for cc, val in enumerate(row):
            pg.insert_text((48 + cc * 107, 78 + r * 30), val, fontsize=9)
    p = os.path.join(tempfile.mkdtemp(), "t.pdf"); doc.save(p); doc.close()
    res = tables.extract_page(p, 1)
    check("tables extracted", res and res[0]["n_rows"] == 3)
    check("tables flags spec (units present)", res and res[0]["spec"] and "length" in res[0]["units"])


if __name__ == "__main__":
    print("== extraction/enrichment/masterfile regression ==")
    test_measures(); test_measures_bare_temperature(); test_measures_unbroken_digit_run_not_truncated()
    test_enrich(); test_masterfile(); test_tables()
    print(("FAILED: " + ", ".join(FAILS)) if FAILS else "ALL EXTRACTION TESTS PASS")
    sys.exit(1 if FAILS else 0)
# END OF FILE
