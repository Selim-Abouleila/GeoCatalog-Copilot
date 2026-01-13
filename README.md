# GeoCatalog Copilot

## Local Catalog Warehouse (DuckDB)

This project uses DuckDB as a local metadata warehouse. It stores metadata snapshots, quality scores, and run history locally, avoiding the need for an external database server during development.

### Setup and Initialization

1.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

2.  **Initialize the database:**
    This command will create the database file at `data/catalog.duckdb` and set up the required schema (tables for runs, items, history, scores, etc.).
    ```bash
    python scripts/init_duckdb.py
    ```
    *Output should indicate success (✅) and list the created tables.*

### Smoke Test

To verify that the database is writable and working correctly:

```bash
python scripts/duckdb_smoke_test.py
```
*Output should be: `✅ Smoke test passed!`*

### Configuration

By default, the database is stored at `data/catalog.duckdb`. You can override this location using an environment variable:

```bash
export GEOCATALOG_DB_PATH=/path/to/my_catalog.duckdb
```
(Or set it in your `.env` file).

## Snapshot Pipeline (Step 2)

The snapshot pipeline pulls metadata from ArcGIS, normalizes it, and loads it into the local DuckDB warehouse.

### Configuration (Optional)
Supported environment variables for authentication:
- `ARCGIS_URL` (default: `https://www.arcgis.com`)
- `ARCGIS_TOKEN` (for token-based auth)
- `ARCGIS_USERNAME` & `ARCGIS_PASSWORD` (for user/pass auth)

### Running a Snapshot
To fetch items (default 50) and update the local database:
```bash
python scripts/run_snapshot.py --max-items 50
```
*Supports anonymous access by default if no credentials are provided.*

### Verification
To check database counts and governance samples:
```bash
python scripts/verify_snapshot.py
```

## Catalog Health Report (Step 3)

The catalog health report generates offline insights from the DuckDB warehouse, including quality trends, broken services, and stale items.

### Generating a Report
```bash
python scripts/generate_catalog_report.py
```
This produces:
- A Markdown summary (`reports/catalog_health_*.md`)
- Detailed CSV exports (`reports/catalog_health_*_missing_tags.csv`, etc.)

### Options
- `--verify`: Run preflight checks and logic tests without writing files.
- `--run-id <UUID>`: Generate report for a specific snapshot run.
- `--out-dir <path>`: Specify output directory (default: `reports/`).

### Verification
To verify that reports are generated correctly:
```bash
python scripts/verify_step3.py
```

## Feature Layer Tools (Step 5)

Data scientists can now inspect layers directly from the Copilot chat.

### Capabilities
- **Row Counts**: accurate counts for layers and tables.
- **Map Preview**: visualize a subset of features on the map.


### How to use
In the Copilot chat, type:
- "count rows for [Item ID or URL]"
- "visualize [Item ID or URL]"

**Or click the "👁️ Visualize" button directly on any Feature Layer result card.**

### Verification
```bash
python scripts/verify_visualize_geojson.py --item-id <id>
```

## Count Rows (Feature Layer)
You can count the number of records (rows) in a Feature Service or Feature Layer without downloading the data.
- **From UI**: Click the `🔢 Count` button on any Feature Layer/Service result card.
- **From Chat**: Ask "count rows for <Item ID>" or "how many records in <URL>".
- **Note**: This tool uses `return_count_only=True` for efficiency. If a service has multiple layers or tables, it will attempt to count all of them and provide a detailed breakdown.

### Verification
```bash
python scripts/verify_count_rows.py --input <url_or_id>
```

## Remediation Pack (Step 4A)
Generate CSV packs to fix metadata issues offline.

```bash
python scripts/generate_remediation_pack.py
```
This produces CSVs in `reports/` with prioritized actions:
- `remediation_YYYY-MM-DD_missing_tags.csv`
- `remediation_YYYY-MM-DD_missing_description.csv`
- `remediation_YYYY-MM-DD_stale_items.csv`
- `remediation_YYYY-MM-DD_broken_services.csv`

### Verification
```bash
python scripts/verify_step4_remediation_pack.py
```
