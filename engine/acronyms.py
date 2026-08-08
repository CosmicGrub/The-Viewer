#!/usr/bin/env python3
"""THE VIEWER -- ACRONYM / ABBREVIATION EXPANDER (v1.2.3, catalog §3.10). Every TM ships a 'LIST OF ABBREVIATIONS /
ACRONYMS' table; this parses it into a per-manual glossary and expands the short forms that appear in the body, so a
search for 'CTIS' or 'GVWR' resolves to its meaning and a mechanic isn't stuck decoding jargon. Pure stdlib regex;
read-only; feeds search synonyms + the dossier. Corpus authoritative."""
import re

# a glossary line: ABBR (2-8 mostly-caps chars) + separator (>=2 spaces, tab, dash, or colon) + Title-case expansion
_GLOSS = re.compile(r"^[ \t>*|]*(?P<ab>[A-Z][A-Z0-9./&-]{1,7})\s*(?:[-–:]|\s{2,})\s*(?P<full>[A-Za-z][A-Za-z0-9 ,/()&.\-]{3,80})\s*$")
_ACR = re.compile(r"\b([A-Z][A-Z0-9]{1,7})\b")
_STOP = {"THE", "AND", "FOR", "WARNING", "CAUTION", "NOTE", "DANGER", "FIGURE", "TABLE", "NSN", "TM",
         "USA", "US", "WWW", "HTTP", "PDF", "II", "III", "IV"}


def extract_glossary(text):
    """Parse an abbreviations/acronyms list -> {ABBR: full-form}. Only keeps plausible glossary lines."""
    gl = {}
    if not text:
        return gl
    for line in text.splitlines():
        m = _GLOSS.match(line.strip())
        if not m:
            continue
        ab = m.group("ab").strip()
        full = re.sub(r"\s+", " ", m.group("full")).strip(" .-")
        # expansion should look like real words (contain a lowercase letter and a space, or be multi-word)
        if len(ab) < 2 or ab in _STOP or full.upper() == ab:
            continue
        if not re.search(r"[a-z]", full):
            continue
        gl[ab] = full[:80]
    return gl


def expand(text, glossary, cap=200):
    """Which glossary acronyms actually appear in `text` -> [{abbr, full, count}] (most frequent first)."""
    if not text or not glossary:
        return []
    counts = {}
    for m in _ACR.finditer(text):
        a = m.group(1)
        if a in glossary and a not in _STOP:
            counts[a] = counts.get(a, 0) + 1
    out = [{"abbr": a, "full": glossary[a], "count": n} for a, n in counts.items()]
    out.sort(key=lambda r: -r["count"])
    return out[:cap]


def find_for_doc(db_path, doc_id):
    """Build the glossary for one document from its pages, then list the acronyms used in that doc, expanded.
    Returns {doc, n_glossary, glossary, used:[{abbr,full,count}]}. Read-only."""
    import sqlite3
    try:
        con = sqlite3.connect("file:%s?mode=ro" % db_path, uri=True)
        rows = con.execute("SELECT body_text FROM pages WHERE document_id=? ORDER BY page_number", (doc_id,)).fetchall()
        con.close()
    except Exception as e:
        return {"doc": doc_id, "n_glossary": 0, "glossary": {}, "used": [], "error": str(e)}
    full_text = "\n".join((r[0] or "") for r in rows)
    gl = extract_glossary(full_text)
    return {"doc": doc_id, "n_glossary": len(gl), "glossary": gl, "used": expand(full_text, gl)}


if __name__ == "__main__":
    sample = (
        "LIST OF ABBREVIATIONS/ACRONYMS\n"
        "CTIS    Central Tire Inflation System\n"
        "GVWR - Gross Vehicle Weight Rating\n"
        "PMCS:  Preventive Maintenance Checks and Services\n"
        "NATO    North Atlantic Treaty Organization\n"
        "THE     the word the should be ignored\n"      # stopword abbr
        "X1      Ab\n"                                    # expansion too short -> skip
        "\n"
        "Body: Set the CTIS to highway. Observe GVWR limits. Perform PMCS daily. CTIS again.\n")
    gl = extract_glossary(sample)
    assert "CTIS" in gl and gl["CTIS"].startswith("Central Tire"), gl
    assert "GVWR" in gl and "PMCS" in gl and "NATO" in gl, gl
    assert "THE" not in gl and "X1" not in gl, "stopword / short expansion not filtered"
    used = expand(sample, gl)
    assert used[0]["abbr"] == "CTIS" and used[0]["count"] >= 2, used   # glossary def + body uses
    assert any(u["abbr"] == "GVWR" for u in used)
    print("acronyms self-test OK  (%d glossary entries, %d used; top=%s)" % (len(gl), len(used), used[0]["abbr"]))
# END OF FILE
