import sys
import os
import glob
import pandas as pd
from datetime import datetime

# Add project root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from scripts.generate_remediation_pack import generate_remediation_pack

def verify_remediation_pack():
    print("Verifying Remediation Pack Generation...")
    
    # 1. Run Generation
    success = generate_remediation_pack(out_dir="reports")
    if not success:
        print("[FAIL] Generation script returned False")
        sys.exit(1)
        
    # 2. Check Files Exist
    date_str = datetime.now().strftime('%Y-%m-%d')
    expected_files = [
        f"reports/remediation_{date_str}_missing_tags.csv",
        f"reports/remediation_{date_str}_missing_description.csv",
        f"reports/remediation_{date_str}_stale_items.csv",
        f"reports/remediation_{date_str}_broken_services.csv",
        f"reports/remediation_{date_str}_owner_summary.csv"
    ]
    
    for fpath in expected_files:
        if not os.path.exists(fpath):
            print(f"[FAIL] Missing file: {fpath}")
            sys.exit(1)
        print(f"[OK] Found {fpath}")

    # 3. Check Schemas
    # Common required columns for item-level reports
    required_cols = {'item_id', 'title', 'owner', 'priority', 'recommended_action', 'quality_score'}
    
    item_reports = expected_files[:4] # First 4 are item lists
    for fpath in item_reports:
        try:
            df = pd.read_csv(fpath)
            # Even if empty, columns should be there
            if not required_cols.issubset(df.columns):
                 print(f"[FAIL] {fpath} missing columns: {required_cols - set(df.columns)}")
                 sys.exit(1)
            
            # Check row count sanity (just info)
            print(f"   -> {os.path.basename(fpath)}: {len(df)} rows")
            
            # Check priority is 0-100
            if not df.empty:
                if df['priority'].min() < 0 or df['priority'].max() > 100:
                    print(f"[FAIL] Priority out of range in {fpath}")
                    sys.exit(1)
                    
        except Exception as e:
            print(f"[FAIL] Error reading {fpath}: {e}")
            sys.exit(1)

    # 4. Check Owner Summary Schema
    owner_path = expected_files[4]
    required_owner_cols = {'owner', 'total_items', 'missing_tags_count', 'missing_description_count', 'stale_items_count'}
    try:
        df_owner = pd.read_csv(owner_path)
        if not required_owner_cols.issubset(df_owner.columns):
             print(f"[FAIL] {owner_path} missing columns: {required_owner_cols - set(df_owner.columns)}")
             sys.exit(1)
        print(f"   -> {os.path.basename(owner_path)}: {len(df_owner)} rows")
    except Exception as e:
         print(f"[FAIL] Error reading {owner_path}: {e}")
         sys.exit(1)

    print("[PASS] Remediation pack verification successful.")
    sys.exit(0)

if __name__ == "__main__":
    verify_remediation_pack()
