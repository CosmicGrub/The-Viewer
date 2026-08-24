#!/usr/bin/env python3
"""Build a small, deterministic fixture index (+ correlations sidecar) for pillar tests.
Mirrors the real schema closely enough to exercise FTS search, NSN routing, parts lookup,
reference enrichment, tech-status derivation, coverage, and the 104th sheet. No real corpus."""
import sqlite3, os, tempfile

def build(dirpath):
    db = os.path.join(dirpath, "viewer.db")
    if os.path.exists(db): os.remove(db)
    c = sqlite3.connect(db)
    c.executescript("""
    CREATE TABLE documents(id INTEGER PRIMARY KEY, path TEXT, rel_path TEXT, fingerprint TEXT,
        type TEXT, tm_number TEXT, nsn TEXT, title TEXT, vehicle TEXT, page_count INT,
        size_bytes INT, mtime REAL, status TEXT, created_at TEXT, updated_at TEXT);
    CREATE TABLE pages(id INTEGER PRIMARY KEY, document_id INT, page_number INT, body_text TEXT,
        char_count INT, source TEXT, ocr_status TEXT, ocr_priority INT, ocr_confidence REAL);
    CREATE VIRTUAL TABLE pages_fts USING fts5(body_text, content='pages', content_rowid='id');
    CREATE TABLE parts(id INTEGER PRIMARY KEY, name TEXT, part_number TEXT, nsn TEXT, document_id INT,
        page INT, vehicle TEXT, nomenclature TEXT, cagec TEXT, smr TEXT, fig_no TEXT, fig_title TEXT,
        uoc TEXT, confidence TEXT, created_at TEXT);
    CREATE TABLE ref_nsn(nsn TEXT PRIMARY KEY, item_name TEXT, description TEXT, gsa_price TEXT,
        source TEXT, source_url TEXT, fetched_at TEXT, official INT, part_no TEXT, cagec TEXT,
        characteristics TEXT, aac TEXT, substitutes TEXT, data_date TEXT, superseded TEXT, alt_parts TEXT);
    CREATE TABLE ref_nsn_log(id INTEGER PRIMARY KEY, nsn TEXT, item_name TEXT, description TEXT,
        gsa_price TEXT, source TEXT, source_url TEXT, fetched_at TEXT, part_no TEXT, cagec TEXT,
        characteristics TEXT, aac TEXT, substitutes TEXT, data_date TEXT, superseded TEXT, alt_parts TEXT);
    CREATE TABLE ref_hardware(id INTEGER PRIMARY KEY, size TEXT, series TEXT, major_in TEXT, major_mm TEXT,
        tpi_or_pitch TEXT, tap_drill TEXT, torque_ref_lbft TEXT, source TEXT, source_url TEXT, fetched_at TEXT);
    CREATE TABLE sessions(id INTEGER PRIMARY KEY, mechanic TEXT, bumper_number TEXT, tm TEXT, uoc TEXT,
        tech_status TEXT, motor_sergeant TEXT, tech_status_suggested TEXT, tech_status_basis TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE faults(id INTEGER PRIMARY KEY, session_id INT, description TEXT);
    CREATE TABLE request_items(id INTEGER PRIMARY KEY, session_id INT, item_name TEXT, nsn TEXT, qty INT,
        fig_no TEXT, part_no TEXT, unit_price TEXT, aac TEXT, arc TEXT, source_document_id INT, source_page INT, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
    """)
    # documents: a vehicle end-item (FSC 2320 = vehicle) + a parts manual
    c.executemany("INSERT INTO documents(id,path,type,tm_number,nsn,title,vehicle,page_count) VALUES(?,?,?,?,?,?,?,?)", [
        (1, "/x/M915 OPERATOR TM-10.pdf", "pdf", "TM 9-2320-363-10", "2320-01-272-5029", "M915A1 Operator", "M915 Truck", 50),
        (2, "/x/M915 RPSTL TM-24P.pdf",   "pdf", "TM 9-2320-363-24P", None, "M915A1 RPSTL", "M915 Truck", 80),
        (3, "/x/Forklift PARTS.pdf",      "pdf", "TM 10-3930-660-24P", None, "Forklift RPSTL", "Forklift", 40),
    ])
    # pages with searchable text incl. a PMCS deadline criterion + an NSN occurrence
    pages = [
        (1, 1, 5, "Operating the brake system. Check air pressure before movement.", "text"),
        (2, 1, 6, "NOT FULLY MISSION CAPABLE IF the service brake is inoperative or air leak exceeds limit.", "text"),
        (3, 2, 12, "FIG 14 brake chamber assembly NSN 2530 01 367 8888 quantity two.", "text"),
        (4, 2, 13, "Bolt, machine 5305 01 674 1467 used on multiple figures. Torque to spec.", "text"),
        (5, 3, 9, "Forklift bolt 5305 01 674 1467 appears here too. Mast assembly.", "ocr"),
        (6, 3, 10, "", "blank"),
        (7, 1, 7, "Valve cover gasket replacement procedure. Inspect the gasket for leaks.", "text"),
    ]
    for pid, doc, pg, txt, src in pages:
        c.execute("INSERT INTO pages(id,document_id,page_number,body_text,char_count,source) VALUES(?,?,?,?,?,?)",
                  (pid, doc, pg, txt, len(txt), src))
    c.execute("INSERT INTO pages_fts(rowid, body_text) SELECT id, body_text FROM pages")
    # parts (RPSTL extraction): same NSN across two vehicles (interchangeability) + a unique one
    c.executemany("INSERT INTO parts(nsn,document_id,page,vehicle,fig_no,fig_title,confidence) VALUES(?,?,?,?,?,?,?)", [
        ("5305-01-674-1467", 2, 13, "M915 Truck", "14", "BOLT, MACHINE", "page"),
        ("5305-01-674-1467", 3, 9,  "Forklift",   "3",  "BOLT, MACHINE", "page"),
        ("2530-01-367-8888", 2, 12, "M915 Truck", "14", "BRAKE CHAMBER", "page"),
    ])
    # reference enrichment (FLIS) + an append-only prior version
    c.execute("INSERT INTO ref_nsn(nsn,item_name,part_no,cagec,characteristics,aac,data_date,superseded) VALUES(?,?,?,?,?,?,?,?)",
              ("5305-01-674-1467", "BOLT, MACHINE", "MS35307-XYZ", "96906", "THREAD 1/4-20; LENGTH 1.5 IN", "D", "2019", ""))
    c.executemany("INSERT INTO ref_nsn_log(nsn,item_name,data_date) VALUES(?,?,?)", [
        ("5305-01-674-1467", "BOLT", "2015"),
        ("5305-01-674-1467", "BOLT, MACHINE", "2019"),
    ])
    c.execute("INSERT INTO ref_hardware(size,series,major_in,tpi_or_pitch,torque_ref_lbft,source) VALUES(?,?,?,?,?,?)",
              ("1/4-20", "UNC", "0.250", "20", "8", "FED-STD-H28"))
    # prior confirmed history for a 'leak' fault -> NMCS
    c.execute("INSERT INTO sessions(id,tech_status) VALUES(1,'NMCS')")
    c.execute("INSERT INTO faults(session_id,description) VALUES(1,'air leak in brake line')")
    c.commit(); c.close()

    # correlations sidecar
    corr = os.path.join(dirpath, "correlations.db")
    if os.path.exists(corr): os.remove(corr)
    cc = sqlite3.connect(corr)
    cc.executescript("""
        CREATE TABLE meta(k TEXT PRIMARY KEY, v TEXT);
        CREATE TABLE nsn_platforms(nsn TEXT PRIMARY KEY, n_vehicles INT, vehicles TEXT, n_docs INT);
        CREATE TABLE niin_aliases(niin TEXT PRIMARY KEY, n INT, variants TEXT);
        CREATE TABLE supersession_held(old_nsn TEXT, current_token TEXT, current_niin TEXT);
    """)
    cc.execute("INSERT INTO nsn_platforms VALUES(?,?,?,?)", ("5305-01-674-1467", 2, "Forklift | M915 Truck", 2))
    cc.execute("INSERT INTO niin_aliases VALUES(?,?,?)", ("016741467", 2, "5303-01-674-1467 | 5305-01-674-1467"))
    cc.execute("INSERT INTO supersession_held VALUES(?,?,?)", ("1005-01-177-2665", "1005-01-129-5768", "011295768"))
    cc.commit(); cc.close()

    # reviews sidecar: a user-confirmed 'interchangeable' decision for NIIN 016741467
    # (its variants 5303-/5305-01-674-1467 are the same item) -> drives the search alias map.
    rev = os.path.join(dirpath, "reviews.db")
    if os.path.exists(rev): os.remove(rev)
    rc = sqlite3.connect(rev)
    rc.execute("CREATE TABLE niin_decisions(id INTEGER PRIMARY KEY, niin TEXT, decision TEXT, canonical_nsn TEXT, note TEXT, decided_by TEXT, decided_at TEXT DEFAULT (datetime('now')))")
    rc.execute("INSERT INTO niin_decisions(niin,decision,canonical_nsn,note,decided_by) VALUES(?,?,?,?,?)",
               ("016741467", "interchangeable", "5305-01-674-1467", "same bolt", "test"))
    rc.commit(); rc.close()
    return db, corr

if __name__ == "__main__":
    d = tempfile.mkdtemp(); print(build(d))
