#!/usr/bin/env python3
"""THE VIEWER -- coverage for the seven feature modules that had ZERO test coverage (audit finding #19):
material_feature, rpstl_feature, xref_feature, sides_feature, collections_feature, chapters_feature,
figures_feature. All seven are `core`-injected DI modules (core = the running viewer_app module); here
`core` is a small stub backed by tests/fixture.py's deterministic index (+ a few synthetic rows added
below for cases the shared fixture doesn't cover: a combined -12 manual for chapters_feature, and an
undetermined-classification doc for sides_feature.uncertain()). Self-contained; no real corpus, no
network, no GPU. Run:  python tests/test_seven_modules.py   (exit 0 = all pass)."""
import os, sys, sqlite3, tempfile, json

HERE = os.path.dirname(os.path.abspath(__file__))
ENGINE = os.path.dirname(HERE)
sys.path.insert(0, ENGINE); sys.path.insert(0, HERE)
import fixture

passed, failed = [], []
def ok(name, cond):
    (passed if cond else failed).append(name)


# ---------------------------------------------------------------------------------------------------
# fixture setup: the shared fixture DB + a couple of synthetic rows the shared fixture doesn't carry.
# ---------------------------------------------------------------------------------------------------
D = tempfile.mkdtemp(prefix="seven_mods_")
DB, CORR = fixture.build(D)

con = sqlite3.connect(DB)
# doc 4: a COMBINED (-12) manual with two chapter headings, for chapters_feature.
con.execute("INSERT INTO documents(id,path,type,tm_number,title,vehicle,page_count) VALUES(?,?,?,?,?,?,?)",
            (4, "/x/Combined -12.pdf", "pdf", "TM 9-9999-999-12", "Combined Ops/Maint Manual", "Test Rig", 30))
con.execute("INSERT INTO pages(id,document_id,page_number,body_text,char_count,source) VALUES(?,?,?,?,?,?)",
            (8, 4, 1, "CHAPTER 1 OPERATOR INSTRUCTIONS. General operating information follows.", 70, "text"))
con.execute("INSERT INTO pages(id,document_id,page_number,body_text,char_count,source) VALUES(?,?,?,?,?,?)",
            (9, 4, 20, "CHAPTER 5 UNIT MAINTENANCE. Repair procedures follow.", 55, "text"))
# doc 5: nothing determinable (no tm_number/title/path wording) -> sides_feature 'low' confidence tail.
con.execute("INSERT INTO documents(id,path,type,tm_number,title,vehicle,page_count) VALUES(?,?,?,?,?,?,?)",
            (5, "/x/unknown.pdf", "pdf", "", "", None, 5))
con.commit(); con.close()


class _Core:
    """Minimal stand-in for the injected viewer_app module: DB_PATH + db() + tm_side()."""
    DB_PATH = DB
    @staticmethod
    def db():
        c = sqlite3.connect(DB, timeout=30); c.row_factory = sqlite3.Row; return c
    @staticmethod
    def tm_side(tm_number, title="", path=""):
        import patterns
        return patterns.tm_side(tm_number, title, path)


# =====================================================================================================
# material_feature -- FLIS characteristics/name -> renderable colour + procedural finish
# =====================================================================================================
try:
    import material_feature as MF
    MF.core = _Core

    # pure parse: no recognizable material/colour/finish word -> unresolved, but never crashes and
    # always returns a usable representative finish (the WebGL viewer needs SOMETHING to render).
    r = MF.material_for("THREAD 1/4-20; LENGTH 1.5 IN", "BOLT, MACHINE")
    ok("material_for_unresolved_found_false", r["found"] is False)
    ok("material_for_unresolved_representative", r["label"] == "representative finish" and r["color"] == "#8a9099")

    # pure parse: a recognizable material (stainless/CRES) + an olive-drab colour both resolve, and the
    # colour word wins the swatch (plating/paint override the colour; a bare colour mention does too).
    r2 = MF.material_for("STEEL, CRES; OLIVE DRAB FINISH", "BRACKET")
    ok("material_for_stainless", r2["material"] == "stainless steel" and r2["metal"] == 0.95)
    ok("material_for_olive_drab_color", r2["color"] == "#3b3b22" and r2["color_label"] == "Olive Drab")
    ok("material_for_found_true", r2["found"] is True)

    # DB-backed: part_material() with no characteristics passed resolves them from ref_nsn via core.db().
    pm = MF.part_material("5305-01-674-1467")
    ok("part_material_db_lookup", pm["nsn"] == "5305-01-674-1467" and pm["found"] is False)  # no material word in this NSN's characteristics

    # unknown NSN: no ref_nsn row -> falls through to the same "nothing recognised" default, no crash.
    pm2 = MF.part_material("0000-00-000-0000")
    ok("part_material_unknown_nsn_graceful", pm2["found"] is False and pm2["nsn"] == "0000-00-000-0000")
except Exception as e:
    failed.append("material_feature(%s)" % e)


# =====================================================================================================
# rpstl_feature -- RPSTL parts-list row parser (multi-signal column detection) + sidecar lookup
# =====================================================================================================
try:
    import rpstl_feature as RF
    RF.core = _Core

    ok("norm_pn", RF.norm_pn(" ms35307-xyz ") == "MS35307-XYZ")
    ok("pn_base_drops_variant", RF.pn_base("12420572-010X") == "12420572")
    ok("pn_base_no_variant_unchanged", RF.pn_base("MS35307") == "MS35307")

    row = RF.parse_line("14 PAOZZ 96906 MS35307-123 BOLT,MACHINE HEX HEAD 4")
    ok("parse_line_found_a_row", row is not None)
    if row:
        ok("parse_line_item", row["item"] == 14)
        ok("parse_line_smr", row["smr"] == "PAOZZ")
        ok("parse_line_cagec", row["cagec"] == "96906")
        ok("parse_line_part_no", row["part_no"] == "MS35307-123")
        ok("parse_line_nomenclature", "BOLT,MACHINE" in (row["nomenclature"] or ""))
        ok("parse_line_qty", row["qty"] == 4)
        ok("parse_line_confidence_high", row["confidence"] >= 0.6)

    # a line with neither a part number nor an NSN is not a parts-list row.
    ok("parse_line_rejects_junk", RF.parse_line("NOTES: see appendix B for torque values") is None)
    ok("parse_line_rejects_short", RF.parse_line("x") is None)

    page_rows = RF.parse_page(
        "FIG 14 EXPLODED VIEW\n14 PAOZZ 96906 MS35307-123 BOLT,MACHINE HEX HEAD 4\n"
        "15 PAFZZ 96906 MS51861-45 WASHER,FLAT LOCK 2", doc_id=2, page=13)
    ok("parse_page_two_rows", len(page_rows) == 2)
    ok("parse_page_fig_attached", all(r["fig_no"] == "14" for r in page_rows))
    ok("parse_page_doc_page", all(r["doc_id"] == 2 and r["page"] == 13 for r in page_rows))

    # sidecar not built yet -> lookup/review degrade gracefully instead of raising.
    ok("lookup_no_sidecar", RF.lookup("MS35307-123") == {"found": False, "query": "MS35307-123"})
    rv = RF.review()
    ok("review_no_sidecar", rv["total"] == 0 and "not built yet" in rv["note"])

    # build a tiny real rpstl.db sidecar and confirm lookup/review/save_override round-trip through it.
    rdb = os.path.join(D, "rpstl.db")
    rc = sqlite3.connect(rdb)
    rc.execute("CREATE TABLE parts_rows(pn_norm TEXT, pn_base TEXT, part_no TEXT, cagec TEXT, nsn TEXT, "
               "item INT, nomenclature TEXT, fig_no TEXT, doc_id INT, page INT, confidence REAL)")
    rc.execute("INSERT INTO parts_rows VALUES(?,?,?,?,?,?,?,?,?,?,?)",
               ("MS35307-123", "MS35307-123", "MS35307-123", "96906", None, 14,
                "BOLT,MACHINE HEX HEAD", "14", 2, 13, 0.8))
    rc.commit(); rc.close()

    found = RF.lookup("ms35307-123")
    ok("lookup_sidecar_found", found["found"] is True and found["part_no"] == "MS35307-123")
    ok("lookup_sidecar_image_url", found["image_url"] == "/figcrop?doc=2&page=13&dpi=150")
    ok("lookup_sidecar_callout_url", found["callout_url"] == "/api/callout_crop?doc=2&page=13&item=14")

    rv2 = RF.review(max_conf=0.9)
    ok("review_sidecar_lists_low_conf_row", rv2["total"] == 1 and rv2["items"][0]["part_no"] == "MS35307-123")

    sv = RF.save_override("ms35307-123", {"nomenclature": "BOLT, HEX HD CAP SCR", "nsn": "5305-01-674-1467"}, by="tester")
    ok("save_override_ok", sv["ok"] is True and sv["part_no"] == "MS35307-123")
    found2 = RF.lookup("MS35307-123")
    ok("lookup_override_wins", found2["found"] is True and found2["nomenclature"] == "BOLT, HEX HD CAP SCR"
       and found2["confidence"] == 1.0)
except Exception as e:
    failed.append("rpstl_feature(%s)" % e)


# =====================================================================================================
# xref_feature -- unified, provenance-tracked part record (FLIS + correlations + rpstl sidecar fusion)
# =====================================================================================================
try:
    import xref_feature as XF
    XF.core = _Core

    ok("xf_vehicles_for", set(XF.vehicles_for("5305-01-674-1467")) == {"Forklift", "M915 Truck"})
    inter = XF.interchangeable_for("5305-01-674-1467")
    ok("xf_interchangeable_excludes_self", "5305-01-674-1467" not in inter)
    ok("xf_interchangeable_finds_alias", "5303-01-674-1467" in inter)
    ok("xf_superseded_by", XF.superseded_by("1005-01-177-2665") == "1005-01-129-5768")
    ok("xf_superseded_by_none", XF.superseded_by("5305-01-674-1467") is None)

    rec = XF.part_record("5305-01-674-1467")
    ok("xf_part_record_found", rec["found"] is True)
    ok("xf_part_record_flis_name", rec["nomenclature"] == "BOLT, MACHINE" and rec["provenance"]["nomenclature"] == "flis")
    ok("xf_part_record_part_no_from_flis", rec["part_no"] == "MS35307-XYZ")
    ok("xf_part_record_cagec_from_flis", rec["cagec"] == "96906")
    ok("xf_part_record_vehicles", set(rec["vehicles"]) == {"Forklift", "M915 Truck"})
    ok("xf_part_record_interchangeable", "5303-01-674-1467" in rec["interchangeable"])
    ok("xf_part_record_links", rec["links"]["dossier"] == "/dossier?q=5305-01-674-1467")

    # a well-formed NSN with no data anywhere is still "found" (an NSN was resolved), just sparse.
    rec2 = XF.part_record("1234-56-789-0123")
    ok("xf_part_record_bare_nsn_found", rec2["found"] is True and rec2["nomenclature"] is None
       and rec2["vehicles"] == [])

    ok("xf_part_record_empty_key", XF.part_record("") == {"found": False})
    ok("xf_part_record_blank_key", XF.part_record("   ") == {"found": False})

    # rpstl_feature's test section (runs earlier in this file) already created a real rpstl.db sidecar
    # with one row (nsn NULL, part_no set) -- coverage() now reads it for real instead of degrading.
    cov = XF.coverage()
    ok("xf_coverage_reads_sidecar", cov["built"] is True and cov["rows"] == 1
       and cov["with_nsn"] == 0 and cov["with_part_no"] == 1)
except Exception as e:
    failed.append("xref_feature(%s)" % e)


# =====================================================================================================
# sides_feature -- operator/mechanic classification cache + manual overrides + cover-page corroboration
# =====================================================================================================
try:
    import sides_feature as SF
    SF.core = _Core
    SF._CACHE["sig"] = None  # a prior test module may have primed a module-level cache; force a rebuild

    con2 = _Core.db()
    m, counts = SF.side_map(con2)
    con2.close()
    ok("sides_doc1_operator", m[1]["operator"] is True and m[1]["mechanic"] is False)
    ok("sides_doc2_mechanic_24p", m[2]["operator"] is False and m[2]["mechanic"] is True)
    ok("sides_doc3_mechanic_24p", m[3]["operator"] is False and m[3]["mechanic"] is True)
    ok("sides_doc4_combined", m[4]["operator"] is True and m[4]["mechanic"] is True)
    ok("sides_doc5_low_confidence", m[5]["confidence"] == "low" and m[5]["mechanic"] is True)
    # docs 1-5 all count: 1(-10 operator), 2&3(-24P mechanic), 4(combined -12, both), 5(undetermined, mechanic)
    ok("sides_counts_operator", counts["operator"] == 2)     # doc1 + doc4
    ok("sides_counts_mechanic", counts["mechanic"] == 4)     # doc2,doc3,doc4,doc5
    ok("sides_counts_both", counts["both"] == 1)             # doc4
    ok("sides_counts_documents", counts["documents"] == 5)

    bs_op = SF.by_side("operator")
    ok("by_side_operator_docs", bs_op["total"] == 2 and sorted(r["doc_id"] for r in bs_op["items"]) == [1, 4])

    bs_mech = SF.by_side("mechanic")
    ids = sorted(r["doc_id"] for r in bs_mech["items"])
    ok("by_side_mechanic_docs", ids == [2, 3, 4, 5])

    unc = SF.uncertain()
    ok("uncertain_lists_doc5", any(r["doc_id"] == 5 for r in unc["items"]))

    ov = SF.save_override(1, "mechanic", by="tester")
    ok("save_override_ok", ov["ok"] is True)
    con3 = _Core.db()
    m2, _ = SF.side_map(con3)
    con3.close()
    ok("override_wins_over_classifier", m2[1]["operator"] is False and m2[1]["mechanic"] is True
       and m2[1]["confidence"] == "override")

    cl = SF.classify(1, "TM 9-2320-363-10")
    ok("classify_single_doc_honors_override", cl["mechanic"] is True and cl["confidence"] == "override")

    ok("save_override_rejects_bad_side", SF.save_override(1, "banana")["ok"] is False)

    # doc_id arrives straight from the POST JSON payload (unlike GET routes' registry.qint()-guarded
    # params) -- missing/malformed doc_id must return a clean ok:False, not raise ValueError/TypeError.
    ok("save_override_rejects_missing_doc_id", SF.save_override(None, "mechanic")["ok"] is False)
    ok("save_override_rejects_nonnumeric_doc_id", SF.save_override("not-a-doc", "mechanic")["ok"] is False)
except Exception as e:
    failed.append("sides_feature(%s)" % e)


# =====================================================================================================
# chapters_feature -- chapter-level operator/mechanic routing inside COMBINED (-12/-13/-14) manuals
# =====================================================================================================
try:
    import chapters_feature as CF
    CF.core = _Core

    info1 = CF.chapters(1)  # doc 1 is operator-only (-10), never combined -> whole-book fallback
    ok("chapters_noncombined_falls_back", info1["combined"] is False and info1["ranges"] == [])

    info4 = CF.chapters(4)  # doc 4 is the synthetic combined -12 manual
    ok("chapters_combined_detected", info4["combined"] is True)
    ok("chapters_has_chapters", info4["has_chapters"] is True)
    ok("chapters_operator_page", info4["operator_page"] == 1)
    ok("chapters_mechanic_page", info4["mechanic_page"] == 20)
    sides_seen = {r["side"] for r in info4["ranges"]}
    ok("chapters_ranges_both_sides", sides_seen == {"operator", "mechanic"})

    j_op = CF.jump(4, "operator")
    ok("jump_operator", j_op["page"] == 1 and j_op["combined"] is True)
    j_me = CF.jump(4, "mechanic")
    ok("jump_mechanic", j_me["page"] == 20)

    j_nc = CF.jump(1, "operator")  # non-combined doc -> always page 1, combined flag False
    ok("jump_noncombined", j_nc == {"doc_id": 1, "side": "operator", "page": 1, "combined": False})

    sv = CF.save_override(4, "mechanic", 21)
    ok("chapters_save_override_ok", sv["ok"] is True)
    j_me2 = CF.jump(4, "mechanic")
    ok("chapters_override_wins", j_me2["page"] == 21)
    ok("chapters_save_override_rejects_bad_side", CF.save_override(4, "both", 5)["ok"] is False)
    ok("chapters_save_override_rejects_bad_page", CF.save_override(4, "operator", "not-a-page")["ok"] is False)

    rv = CF.review()
    ok("chapters_review_finds_combined", rv["combined_total"] >= 1
       and any(it["doc_id"] == 4 for it in rv["items"]))
except Exception as e:
    failed.append("chapters_feature(%s)" % e)


# =====================================================================================================
# figures_feature -- crop a part's CITED figure from the manual page (authoritative part imagery)
# =====================================================================================================
try:
    import figures_feature as FF
    FF.core = _Core

    # two rows cite this NSN (doc2 page13, doc3 page9); the lower page number wins (ORDER BY page).
    fi = FF.figure_for("5305-01-674-1467")
    ok("figure_for_picks_lowest_page", fi["found"] is True and fi["doc_id"] == 3 and fi["page"] == 9)
    ok("figure_for_fig_no", fi["fig_no"] == "3")

    fi2 = FF.figure_for("2530-01-367-8888")
    ok("figure_for_single_row", fi2["found"] is True and fi2["doc_id"] == 2 and fi2["page"] == 12)

    ok("figure_for_unknown_nsn", FF.figure_for("0000-00-000-0000") == {"found": False, "nsn": "0000-00-000-0000"})
    ok("figure_for_empty_nsn", FF.figure_for("") == {"found": False})

    pimg = FF.part_image("5305-01-674-1467")
    ok("part_image_url", pimg["found"] is True and pimg["url"] == "/figcrop?doc=3&page=9&dpi=150")
    ok("part_image_unknown", FF.part_image("0000-00-000-0000") == {"found": False, "nsn": "0000-00-000-0000"})

    # real-PDF path via PyMuPDF (skips cleanly if fitz isn't installed in this environment).
    if FF.fitz is not None:
        pdf_path = os.path.join(D, "synthetic_fig_test.pdf")
        d = FF.fitz.open()
        d.new_page(width=400, height=600)
        d.save(pdf_path)
        d.close()

        out_path = os.path.join(D, "extract_test.png")
        okx, detail = FF.extract(pdf_path, 1, 100, out_path)
        ok("extract_blank_page_top_fallback", okx is True and os.path.exists(out_path) and os.path.getsize(out_path) > 0)

        okx2, detail2 = FF.extract(pdf_path, 999, 100, out_path)  # out-of-range page fails, doesn't clamp/crash
        ok("extract_out_of_range_page_fails", okx2 is False and "out of range" in detail2)

        okx3, detail3 = FF.extract("/no/such/file.pdf", 1, 100, out_path)
        ok("extract_missing_pdf", okx3 is False and "not found" in detail3)

        # get_crop(): doc-DB-backed, caches to figcache/<doc>_<page>_<dpi>.png
        con4 = sqlite3.connect(DB)
        con4.execute("INSERT INTO documents(id,path,type,tm_number,title,page_count) VALUES(6,?,?,?,?,1)",
                     (pdf_path, "pdf", "TM 0-0000-000-00", "Synthetic Test Doc"))
        con4.commit(); con4.close()

        crop1 = FF.get_crop(6, 1, 100)
        ok("get_crop_creates_file", crop1 is not None and os.path.exists(crop1) and os.path.getsize(crop1) > 0)
        mtime1 = os.path.getmtime(crop1)
        crop2 = FF.get_crop(6, 1, 100)
        ok("get_crop_cache_hit_same_path", crop2 == crop1 and os.path.getmtime(crop2) == mtime1)

        # callout_crop degrades to None when pytesseract isn't installed (no crash either way).
        cc = FF.callout_crop(6, 1, "1")
        ok("callout_crop_graceful", cc is None or isinstance(cc, str))
    else:
        ok("fitz_unavailable_skip_render_tests", True)
except Exception as e:
    failed.append("figures_feature(%s)" % e)


# =====================================================================================================
# collections_feature -- Smart Collections: saved queries evaluated LIVE against pages_fts
# =====================================================================================================
try:
    import collections_feature as CC
    CC.core = _Core

    lst = CC.smart_collections_list()
    slugs = {c["slug"] for c in lst["collections"]}
    ok("collections_seed_present", {"warnings", "torque", "wiring"} <= slugs)
    torque = next(c for c in lst["collections"] if c["slug"] == "torque")
    ok("collections_torque_hits_fixture_page", torque["count"] >= 1)   # page 4: "...Torque to spec."
    ok("collections_facets_vehicles", set(lst["facets"]["vehicles"]) == {"M915 Truck", "Forklift", "Test Rig"})

    ev = CC.smart_collection_eval("torque")
    ok("collections_eval_returns_items", len(ev["items"]) >= 1)
    ok("collections_eval_item_shape", all("doc_id" in it and "snip" in it for it in ev["items"]))

    sv = CC.smart_collection_save("Brake stuff", "brake")
    ok("collections_save_ok", sv["ok"] is True and sv["slug"] == "brake-stuff")
    ev2 = CC.smart_collection_eval("brake-stuff")
    doc_ids = {it["doc_id"] for it in ev2["items"]}
    # "brake" appears on doc1's two pages (5,6) + doc2's page 12; doc3's pages mention "bolt"/"mast", not brake.
    ok("collections_custom_eval_hits", doc_ids == {1, 2} and len(ev2["items"]) == 3)

    # vehicle-scoped collection: "bolt" restricted to Forklift docs only -> excludes doc2's bolt mention.
    sv2 = CC.smart_collection_save("Forklift bolts", "bolt", vehicle="Forklift")
    ev3 = CC.smart_collection_eval("forklift-bolts")
    ok("collections_vehicle_scoped", all(it["vehicle"] == "Forklift" for it in ev3["items"]) and len(ev3["items"]) >= 1)

    pin = CC.smart_collection_pin("brake-stuff", True)
    ok("collections_pin_ok", pin["ok"] is True and pin["pinned"] == 1)
    lst2 = CC.smart_collections_list()
    ok("collections_pinned_sorts_first", lst2["collections"][0]["slug"] == "brake-stuff")

    dl = CC.smart_collection_delete("brake-stuff")
    ok("collections_delete_custom_ok", dl["ok"] is True and dl["hidden"] is False)
    ev4 = CC.smart_collection_eval("brake-stuff")
    ok("collections_deleted_gone", ev4.get("error") == "no such collection")

    dl2 = CC.smart_collection_delete("torque")   # seed collections are soft-hidden, not deleted
    ok("collections_delete_seed_hides", dl2["ok"] is True and dl2["hidden"] is True)
    lst3 = CC.smart_collections_list()
    ok("collections_hidden_seed_absent", "torque" not in {c["slug"] for c in lst3["collections"]})

    ok("collections_save_requires_name_and_query", CC.smart_collection_save("", "x")["ok"] is False)
except Exception as e:
    failed.append("collections_feature(%s)" % e)


for n in passed: print("PASS", n)
for n in failed: print("FAIL", n)
print("\n%d passed, %d failed (of %d checks across 7 previously-untested feature modules)" %
      (len(passed), len(failed), len(passed) + len(failed)))
sys.exit(1 if failed else 0)

# END OF FILE
