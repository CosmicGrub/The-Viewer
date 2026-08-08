# PUB LOG one-time fill from the FLIS Reading Room (quickstart)

**Good news:** you do **not** need the PUB LOG Windows app or any Batch/SQL export. The DLA **FLIS Data
Electronic Reading Room** publishes the data as **direct, monthly-updated CSV files** (zipped), in a
"format that can be consumed by most DB applications." Download a few, extract, point the tool at the
folder. The engine never goes online; this is a one-time step on a connected machine. Append-only & cited (R6).

Reading Room: <https://www.dla.mil/Information-Operations/FLIS-Data-Electronic-Reading-Room/>

## Step 1 — Download the files you want (free, no CAC)
From the FLIS Data table, grab the ZIPs that fill our gaps (each has a Record Layout PDF):

| File | Fills |
|------|-------|
| `Identification.zip` | NSN → item name / identification |
| `H-Series.zip` (H6) | approved item names |
| `Reference.zip` | **part number + CAGE** per NSN |
| `Characteristics.zip` | **decoded size / thread / material** (Tier 2.5) |
| `Management.zip` | management data incl. **AAC**, I&S substitutes |
| `CAGE.zip` | manufacturer name/address per CAGE |
| `History.zip` | **inactive / cancelled NSNs** (kept, per R6) |

Start with **Identification + Reference + Characteristics** if you want the essentials; add the rest anytime.

## Step 2 — Extract into one folder
Unzip them all into a single folder, e.g. `C:\publog\` (CSV files side by side). No conversion needed.

## Step 3 — Load into the offline index (one command)
- Drag the **folder is not draggable**, so run:
  `python engine\viewer_ingest.py enrich --publog-dir "C:\publog"`
- or use the launcher for a single file: drag one CSV onto `engine\run_enrich.bat`.

The tool reads every CSV in the folder, keeps **only the NSNs already in your index**, and **merges**
each NSN's fields across files **without clobbering** (Identification gives the name, Reference gives the
part#, Characteristics gives the size, etc.). Every version is appended to `ref_nsn_log` and kept (R6).
Then copy the index back to the offline machine.

## Notes
- Column headers vary by file; the ingester already recognizes the common PUB LOG names (NSN or FSC+NIIN,
  ITEM_NAME, PART_NUMBER/REFERENCE_NUMBER, CAGE, CHARACTERISTICS/CLEAR_TEXT_REPLY, AAC, I&S). If a file
  uses different headers, send me one and I'll add the mapping in minutes.
- These files are large (the full federal catalog), so the download is the only heavy part — the ingest
  itself is fast because it keeps only your NSNs.
- Everything stays offline after this one-time load; nothing about the running engine changes.
