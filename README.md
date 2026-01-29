# GeoCatalog Copilot
**LLM-assisted ArcGIS catalog governance + feature-layer inspection dashboard**  
Built during my internship at **Esri Saudi Arabia**.

🎥 **Demo (YouTube):** https://www.youtube.com/watch?v=8wIqFAcDndA

[![GeoCatalog Copilot demo video](https://img.youtube.com/vi/8wIqFAcDndA/hqdefault.jpg)](https://www.youtube.com/watch?v=8wIqFAcDndA)

---

## Why this project exists
Large ArcGIS organizations can accumulate **hundreds to thousands of items** (Feature Services, Feature Layers, web maps, etc.). Over time, catalog quality degrades:

- Incomplete metadata (missing **tags**, weak **descriptions**, inconsistent naming)
- **Stale** content that’s no longer maintained
- **Broken** services and dead endpoints
- Hard-to-audit catalogs with no repeatable health checks

**GeoCatalog Copilot** addresses this by combining a local-first catalog warehouse (DuckDB), repeatable snapshot runs, automated health reporting, and “copilot-style” layer inspection tools (row counts + map preview) into a single workflow.

---

## What it does (high level)
### ✅ Catalog governance (offline, repeatable)
- Stores catalog metadata snapshots locally in **DuckDB**
- Tracks **run history** + metadata over time
- Produces **catalog health reports** (Markdown + CSV exports)
- Generates **remediation packs** (CSV) to prioritize metadata clean-up

### ✅ Feature-layer inspection (fast validation)
- **Row counts** for Feature Services/Layers (without downloading data)
- **Map preview** to visualize a subset of features quickly
- Works via UI actions (e.g., `Visualize`, `Count`) and via the Copilot chat prompts

---

## Architecture (simple mental model)
1. **Snapshot** ArcGIS items → normalize metadata  
2. **Store** into a local DuckDB warehouse (`data/catalog.duckdb`)  
3. **Analyze** warehouse → generate health insights + remediation CSV packs  
4. **Interact** through the dashboard to inspect layers (count + preview)  

This design keeps the project:
- **Local-first** (no external DB required during development)
- **Reproducible** (scripted runs + verifications)
- **Audit-ready** (reports and CSV outputs can be attached to governance reviews)

---

## Quickstart
> The steps below are the fastest way to run the end-to-end workflow locally.

### 1) Install dependencies
```bash
pip install -r requirements.txt
```

### 2) Initialize the DuckDB warehouse

Creates the database file at data/catalog.duckdb and sets up schema (runs, items, history, scores, etc.).

```bash
python scripts/init_duckdb.py
```

### 3) Smoke test (recommended)

Verifies the DB is writable and healthy.

```bash
python scripts/duckdb_smoke_test.py
```

Expected:

✅ Smoke test passed!

### 4) Run a metadata snapshot

Fetches items (default: 50) and updates the local warehouse.

```bash
python scripts/run_snapshot.py --max-items 50
```

### 5) Generate a catalog health report

Produces:

Markdown summary: reports/catalog_health_*.md

Detailed CSV exports (missing tags, missing description, etc.)

```bash
python scripts/generate_catalog_report.py
```

### 6) Run the dashboard

If you’re using Streamlit locally:

```bash
streamlit run app.py
```

## Configuration
### DuckDB path

Default:

data/catalog.duckdb

Override with:

```bash
export GEOCATALOG_DB_PATH=/path/to/my_catalog.duckdb
```

(or set it in a .env file)

### ArcGIS authentication (optional)

Anonymous access is supported by default if no credentials are provided.
If you need authenticated access, configure one of the following:

ARCGIS_URL (default: https://www.arcgis.com)

ARCGIS_TOKEN (token-based auth)

ARCGIS_USERNAME and ARCGIS_PASSWORD (user/pass)

## Workflows (CLI scripts)
### Snapshot verification

Checks database counts and governance samples:

```bash
python scripts/verify_snapshot.py
```

### Catalog report verification
```bash
python scripts/verify_step3.py
```

### Remediation pack (prioritized CSV actions)

Generates CSVs in reports/:

remediation_YYYY-MM-DD_missing_tags.csv

remediation_YYYY-MM-DD_missing_description.csv

remediation_YYYY-MM-DD_stale_items.csv

remediation_YYYY-MM-DD_broken_services.csv

```bash
python scripts/generate_remediation_pack.py
```

Verification:

```bash
python scripts/verify_step4_remediation_pack.py
```

### Feature Layer Tools (Copilot-style inspection)

Data scientists and GIS analysts can inspect layers directly from the Copilot experience.

### Capabilities

Row Counts: accurate counts for Feature Services/Layers (and attempts to count multiple layers/tables when present)

Map Preview: visualize a subset of features on the map

### How to use (chat prompts)

In the Copilot chat, try:

count rows for <Item ID or URL>

visualize <Item ID or URL>

Or click the UI buttons on the result cards:

Visualize

Count

### Verification

Map preview verification:

```bash
python scripts/verify_visualize_geojson.py --item-id <id>
```

Count rows verification:

```bash
python scripts/verify_count_rows.py --input <url_or_id>
```

Note: Row counting uses return_count_only=True for efficiency. If a service has multiple layers/tables, the tool attempts a detailed breakdown.

### Outputs

DuckDB warehouse: data/catalog.duckdb

Reports folder: reports/

Markdown summary reports

CSV exports for missing metadata and governance findings

Remediation packs for prioritizing cleanup

## Project structure
.
├── app.py
├── src/
├── scripts/
├── data/
│   └── catalog.duckdb
├── reports/
├── requirements.txt
└── .env.example

## Internship context

This repository represents a project I developed during my internship at Esri Saudi Arabia to explore practical ways to:

streamline ArcGIS catalog governance,

generate audit-ready outputs,

and reduce time spent manually inspecting feature layers.

This is a personal project repository and not an official Esri product.
