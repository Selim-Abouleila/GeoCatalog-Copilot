import sys
import os
import pandas as pd
from pathlib import Path

# Ensure project root is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

try:
    from src.services.catalog_store import get_status, admin_queries, get_latest_run_id
    from src.services.report_store import list_reports, read_text, list_report_csvs
    from scripts.generate_catalog_report import generate_catalog_report
    print("[OK] Modules imported successfully.")
except ImportError as e:
    print(f"[ERROR] Import failed: {e}")
    sys.exit(1)

def main():
    print("Verifying Streamlit Integration (Headless)...")
    
    # 1. Check Catalog Store Status
    print("Checking Catalog Store Status...")
    status = get_status()
    print(f"Status: {status}")
    
    if not status['ok']:
        print(f"[WARN] Store status not OK: {status.get('error')}")
        # If DB is broken, we can't test much else, but typically we assume Step 2 ran.
        if "Missing tables" in str(status.get('error')):
            print("DB missing tables. Please run init/snapshot first.")
            sys.exit(1)
            
    if status.get('has_runs'):
        run_id = status['latest_run']['run_id']
        print(f"Latest Run: {run_id}")
        
        # 2. Check Admin Queries
        print("Running Admin Queries...")
        dfs = admin_queries(run_id)
        for key, df in dfs.items():
            print(f" - {key}: {type(df)} with {len(df)} rows")
            if not isinstance(df, pd.DataFrame):
                print(f"[ERROR] {key} is not a DataFrame!")
                sys.exit(1)
    else:
        print("[WARN] No runs found. Skipping admin query verification.")

    # 3. Check Report Store
    print("Checking Report Store...")
    reports = list_reports()
    print(f"Found {len(reports)} reports.")
    
    if reports:
        report_path = reports[0]
        content = read_text(report_path)
        print(f"Read {report_path} ({len(content)} chars)")
        if not content:
            print("[ERROR] Report content empty.")
            sys.exit(1)
            
        csvs = list_report_csvs(report_path)
        print(f"Found {len(csvs)} related CSVs.")
    
    # 4. Optional: Generate Report Check
    # (Only if runs exist)
    if status.get('has_runs'):
        print("Testing Report Generator Call...")
        res = generate_catalog_report(run_id=None, out_dir="reports")
        if res['ok']:
            print(f"[OK] Report generated at {res['md_path']}")
        else:
            print(f"[ERROR] Report generation failed: {res.get('error')}")
            sys.exit(1)

    print("[OK] Integration verification passed.")
    sys.exit(0)

if __name__ == "__main__":
    main()
