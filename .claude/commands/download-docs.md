# Download Normative Documents for RAG

This skill manages the pipeline for downloading normative construction documents (СП, ГОСТ, СНиП, ТР) into the RAG system.

## Sources
- **Стройкомплекс.РФ/RNTD** — registry of all normative-technical documents in construction
- **protect.gost.ru TR-54** — documents under Technical Regulation on Building Safety (ФЗ-384)
- **docs.cntd.ru** — full document text source (free access: 20:00–24:00 МСК)

## Scripts
All scripts run from the **project root**. Output goes to `data/`.

| Script | Purpose | Output |
|--------|---------|--------|
| `scripts/01_list_rntd.py` | List docs from Стройкомплекс.РФ | `data/rntd/rntd_list.json` |
| `scripts/02_list_gost_tr54.py` | List docs from protect.gost.ru | `data/gost_tr54/gost_tr54_list.json` |
| `scripts/03_download_cntd.py` | Download full text from docs.cntd.ru | `data/cntd_docs/**/*.md` |

## Instructions

The user may pass arguments: $ARGUMENTS

Based on the arguments and the current state, do the following:

### If no arguments or "status":
1. Check which JSON list files exist:
   - `data/rntd/rntd_list.json` — count entries
   - `data/gost_tr54/gost_tr54_list.json` — count entries
   - `data/merged_doc_list.json` — count entries
2. Check download progress:
   - `data/cntd_docs/progress.json` — count downloaded IDs
   - `data/cntd_docs/failed_downloads.json` — count failures
   - Count `.md` files in `data/cntd_docs/` by subdirectory
3. Report status clearly with counts and next recommended action.

### If argument is "list-rntd" or step 1:
Run script 01 to enumerate RNTD documents:
```bash
python scripts/01_list_rntd.py
```
- This probes the ГИСОГД REST API first, falls back to Playwright if needed.
- Playwright requires `playwright install chromium` (one-time setup).
- Output: `data/rntd/rntd_list.json`
- After completion, report how many documents were found and their type breakdown.

### If argument is "list-gost" or step 2:
Run script 02 to enumerate TR-54 documents from protect.gost.ru:
```bash
python scripts/02_list_gost_tr54.py
```
- Uses ASP.NET ViewState pagination (~870 documents, ~9 pages).
- Takes ~3–5 minutes (polite crawl delays).
- Output: `data/gost_tr54/gost_tr54_list.json`
- After completion, report document count and type breakdown.

### If argument is "download" or step 3:
Check the current time (UTC) before proceeding.
- docs.cntd.ru free window: **17:00–21:00 UTC** (= 20:00–24:00 МСК)
- If inside the window, run immediately.
- If outside the window, warn the user and offer to run with `--no-time-check` for testing.

```bash
# With automatic time window check (recommended for production):
python scripts/03_download_cntd.py

# For testing outside free window (downloads may be restricted):
python scripts/03_download_cntd.py --no-time-check

# Skip ID resolution via search (faster, but misses docs without known CNTD ID):
python scripts/03_download_cntd.py --no-id-resolve
```
- Downloads are resumable — progress saved in `data/cntd_docs/progress.json`
- Failed docs saved in `data/cntd_docs/failed_downloads.json`
- After completion (or interruption), report downloaded count, failed count, total size.

### If argument is "all" or "run-all":
Run all three steps sequentially:
1. `python scripts/01_list_rntd.py`
2. `python scripts/02_list_gost_tr54.py`
3. `python scripts/03_download_cntd.py` (with time window check)

### If argument is "install" or "setup":
Install required dependencies:
```bash
uv sync
playwright install chromium
```
Confirm that `beautifulsoup4`, `lxml`, `playwright`, `html2text` are installed.

### If argument is "failed":
Show the contents of `data/cntd_docs/failed_downloads.json` and categorize by reason:
- `no_cntd_id` — designation not found on docs.cntd.ru (needs manual lookup)
- `download_failed` — network error
- `access_restricted` — paywall (retry during 20:00–24:00 МСК)
- `empty_text` — parsing failed (CSS selectors may need updating)

Suggest fixes for each category.

## Important Notes
- Always run scripts from the **project root**, not from `scripts/`.
- The `data/cntd_docs/` directory structure: `СП/`, `ГОСТ/`, `СНиП/`, `ТР/`, `OTHER/`
- Each downloaded `.md` file has metadata comments at the top: `designation`, `cntd_id`, `doc_type`
- To add documents to FAISS, a rebuild of `faiss_index/` is needed (separate task).
