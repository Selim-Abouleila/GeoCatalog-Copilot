import argparse
import os
import sys
import pandas as pd
import duckdb
from datetime import datetime

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from src.storage.duckdb_client import connect

def get_latest_run_id(con):
    try:
        df = con.sql("SELECT run_id FROM runs ORDER BY started_at DESC LIMIT 1").df()
        if not df.empty:
            return str(df.iloc[0]['run_id'])
    except Exception:
        pass
    return None

def generate_remediation_pack(run_id=None, out_dir="reports"):
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)

    con = connect(read_only=True)
    try:
        # 1. Resolve Run ID
        if not run_id:
            run_id = get_latest_run_id(con)
            if not run_id:
                print("[ERROR] No run_id found.")
                return False
        
        print(f"Generating Remediation Pack for Run ID: {run_id}")
        
        # 2. Base Query Logic (Common Columns)
        # We join items_current with quality_scores and health_checks
        # We calculate priority dynamically
        
        base_sql = f"""
        WITH health AS (
            SELECT item_id, ok, status_code, error_message, checked_url
            FROM health_checks 
            WHERE run_id = '{run_id}'
        ),
        scores AS (
            SELECT item_id, score
            FROM quality_scores
            WHERE run_id = '{run_id}'
        )
        SELECT 
            i.item_id,
            i.title,
            i.item_type,
            i.owner,
            i.url,
            i.modified_at,
            i.tags_count,
            i.has_description,
            s.score as quality_score,
            h.ok as health_ok,
            h.status_code,
            h.error_message,
            h.checked_url
        FROM items_current i
        LEFT JOIN scores s ON i.item_id = s.item_id
        LEFT JOIN health h ON i.item_id = h.item_id
        """
        
        df_base = con.sql(base_sql).df()
        
        # Helper to calc priority
        def calc_priority(row, issue_type):
            base_p = 100 - (row['quality_score'] if pd.notnull(row['quality_score']) else 50)
            weight = 0
            if issue_type == 'broken_services': weight = 30
            elif issue_type == 'missing_description': weight = 15
            elif issue_type == 'missing_tags': weight = 10
            elif issue_type == 'stale_items': weight = 10
            
            p = base_p + weight
            return max(0, min(100, p))

        date_str = datetime.now().strftime('%Y-%m-%d')
        
        # 3. Generate Categories
        
        # A. Missing Tags
        # Definition: tags_count is null or 0
        mask_tags = (df_base['tags_count'].fillna(0) == 0)
        df_tags = df_base[mask_tags].copy()
        if not df_tags.empty:
            df_tags['recommended_action'] = 'ADD_TAGS'
            df_tags['priority'] = df_tags.apply(lambda r: calc_priority(r, 'missing_tags'), axis=1)
            # Sort
            df_tags = df_tags.sort_values('priority', ascending=False)
            
        # Write
        path_tags = os.path.join(out_dir, f"remediation_{date_str}_missing_tags.csv")
        # Ensure columns
        final_cols = ['item_id', 'title', 'item_type', 'owner', 'priority', 'recommended_action', 'url', 'quality_score', 'modified_at']
        df_tags.to_csv(path_tags, index=False, columns=[c for c in final_cols if c in df_tags.columns])
        print(f" -> {path_tags} ({len(df_tags)} rows)")

        # B. Missing Description
        mask_desc = (df_base['has_description'] == False)
        df_desc = df_base[mask_desc].copy()
        if not df_desc.empty:
            df_desc['recommended_action'] = 'ADD_DESCRIPTION'
            df_desc['priority'] = df_desc.apply(lambda r: calc_priority(r, 'missing_description'), axis=1)
            df_desc = df_desc.sort_values('priority', ascending=False)
            
        path_desc = os.path.join(out_dir, f"remediation_{date_str}_missing_description.csv")
        df_desc.to_csv(path_desc, index=False, columns=[c for c in final_cols if c in df_desc.columns])
        print(f" -> {path_desc} ({len(df_desc)} rows)")
        
        # C. Stale Items (> 2 years)
        # Need to parse modified_at if it's string, or ensure duckdb returned datetime
        now = pd.Timestamp.now()
        # Ensure modified_at is datetime
        df_base['modified_at'] = pd.to_datetime(df_base['modified_at'])
        
        mask_stale = (df_base['modified_at'] < (now - pd.DateOffset(years=2)))
        df_stale = df_base[mask_stale].copy()
        if not df_stale.empty:
            df_stale['recommended_action'] = 'REVIEW_STALE'
            df_stale['priority'] = df_stale.apply(lambda r: calc_priority(r, 'stale_items'), axis=1)
            df_stale = df_stale.sort_values('priority', ascending=False)
            
        path_stale = os.path.join(out_dir, f"remediation_{date_str}_stale_items.csv")
        df_stale.to_csv(path_stale, index=False, columns=[c for c in final_cols if c in df_stale.columns])
        print(f" -> {path_stale} ({len(df_stale)} rows)")

        # D. Broken Services
        mask_broken = (df_base['health_ok'] == False)
        df_broken = df_base[mask_broken].copy()
        if not df_broken.empty:
            df_broken['recommended_action'] = 'FIX_SERVICE_URL'
            df_broken['priority'] = df_broken.apply(lambda r: calc_priority(r, 'broken_services'), axis=1)
            df_broken = df_broken.sort_values('priority', ascending=False)
            
        path_broken = os.path.join(out_dir, f"remediation_{date_str}_broken_services.csv")
        broken_cols = final_cols + ['status_code', 'error_message', 'checked_url']
        # Filter just what we have
        actual_broken_cols = [c for c in broken_cols if c in df_broken.columns]
        df_broken.to_csv(path_broken, index=False, columns=actual_broken_cols)
        print(f" -> {path_broken} ({len(df_broken)} rows)")

        # E. Owner Summary
        # We can aggregate from df_base using pandas or SQL. SQL is cleaner for "counts".
        owner_sql = f"""
        WITH health AS (
            SELECT item_id, ok FROM health_checks WHERE run_id = '{run_id}'
        )
        SELECT 
            i.owner,
            COUNT(*) as total_items,
            COUNT(CASE WHEN COALESCE(i.tags_count,0)=0 THEN 1 END) as missing_tags_count,
            COUNT(CASE WHEN i.has_description=False THEN 1 END) as missing_description_count,
            COUNT(CASE WHEN i.modified_at < (now() - INTERVAL '2 years') THEN 1 END) as stale_items_count,
            COUNT(CASE WHEN h.ok=False THEN 1 END) as broken_services_count
        FROM items_current i
        LEFT JOIN health h ON i.item_id = h.item_id
        GROUP BY i.owner
        ORDER BY broken_services_count DESC, missing_description_count DESC, missing_tags_count DESC
        """
        df_owner = con.sql(owner_sql).df()
        path_owner = os.path.join(out_dir, f"remediation_{date_str}_owner_summary.csv")
        df_owner.to_csv(path_owner, index=False)
        print(f" -> {path_owner} ({len(df_owner)} rows)")
        
        print("[OK] Remediation Pack Generated.")
        return True

    except Exception as e:
        print(f"[ERROR] {e}")
        return False
    finally:
        con.close()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", help="Target Run ID")
    parser.add_argument("--out-dir", default="reports", help="Output directory")
    args = parser.parse_args()
    
    success = generate_remediation_pack(args.run_id, args.out_dir)
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()
