import sys
import os
import glob
import pandas as pd

def main():
    print("Verifying Step 3 Generated Reports...")
    
    report_dir = "reports"
    if not os.path.exists(report_dir):
        print(f"[ERROR] Directory '{report_dir}' does not exist.")
        sys.exit(1)
        
    # Find latest markdown report
    md_files = glob.glob(os.path.join(report_dir, "*.md"))
    if not md_files:
        print(f"[ERROR] No markdown reports found in '{report_dir}'.")
        sys.exit(1)
        
    latest_md = max(md_files, key=os.path.getmtime)
    print(f"Checking latest report: {latest_md}")
    
    with open(latest_md, 'r', encoding='utf-8') as f:
        content = f.read()
        
    required_headings = ["# Catalog Health Report", "## Snapshot Summary", "## Quality Stats", "## Top Issues"]
    for head in required_headings:
        if head not in content:
            print(f"[ERROR] Markdown missing heading: '{head}'")
            sys.exit(1)
            
    # Check CSVs corresponding to this report
    # Name format: catalog_health_<date>_<shortid>.md
    # CSV format: catalog_health_<date>_<shortid>_<type>.csv
    base_name = os.path.splitext(latest_md)[0]
    
    required_csvs = [
        "missing_tags",
        "missing_description",
        "missing_extent",
        "stale_items",
        "broken_services",
        "owner_summary"
    ]
    
    for csv_type in required_csvs:
        csv_path = f"{base_name}_{csv_type}.csv"
        if not os.path.exists(csv_path):
            print(f"[ERROR] Missing expected CSV: {csv_path}")
            sys.exit(1)
            
        # Verify content
        try:
            df = pd.read_csv(csv_path)
            if df.empty:
                # Headers are still expected
                if len(df.columns) == 0:
                    print(f"[ERROR] CSV {csv_path} is completely empty (no headers).")
                    sys.exit(1)
            # print(f" - {csv_type}: {len(df)} rows")
        except Exception as e:
            print(f"[ERROR] Failed to read CSV {csv_path}: {e}")
            sys.exit(1)
            
    print("[OK] All reports verified.")
    sys.exit(0)

if __name__ == "__main__":
    main()
