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
