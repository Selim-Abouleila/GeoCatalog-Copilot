import sys
import os
import argparse
import pandas as pd
from datetime import datetime, timezone
import pathlib
import duckdb

# Ensure project root is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.storage.duckdb_client import connect, get_db_path

def preflight_or_exit(con):
    """
    Verifies that the database is healthy and has the required schema.
    Exits with error if tables or columns are missing.
    Returns latest run info if successful, else exits 0 if no runs found.
    """
    print("Performing preflight checks...")
    
    # 1. Check Connection (Implicit by being passed 'con')
    
    # 2. Check Tables
    required_tables = ['runs', 'items_current', 'quality_scores', 'health_checks', 'items_history']
    existing_tables_df = con.sql("SELECT table_name FROM information_schema.tables WHERE table_schema='main'").df()
    existing_tables = set(existing_tables_df['table_name'].tolist())
    
    missing_tables = [t for t in required_tables if t not in existing_tables]
    if missing_tables:
        print(f"[ERROR] Missing tables: {missing_tables}")
        print("Run 'python scripts/init_duckdb.py' and 'python scripts/run_snapshot.py'.")
        sys.exit(1)
        
    # 3. Check Columns (Sampling key columns)
    required_cols = {
        'runs': ['run_id', 'started_at', 'finished_at'],
        'items_current': ['item_id', 'title', 'owner', 'item_type', 'modified_at', 'tags_count', 'has_description', 'has_extent'],
        'quality_scores': ['run_id', 'item_id', 'score'],
        'health_checks': ['run_id', 'item_id', 'ok', 'status_code', 'checked_url', 'error_message', 'checked_at'],
        'items_history': ['item_id', 'valid_from', 'content_hash', 'title', 'owner', 'item_type', 'first_seen_run_id']
    }
    
    for table, cols in required_cols.items():
        table_info_df = con.sql(f"PRAGMA table_info('{table}')").df()
        existing_cols = set(table_info_df['name'].tolist())
        missing_cols = [c for c in cols if c not in existing_cols]
        if missing_cols:
            # Flexible check for items_history 'first_seen_run_id' as it might be 'valid_from' focused logic in older schema versions
            # But per user spec, we must check it. 
            print(f"[ERROR] Table '{table}' missing columns: {missing_cols}")
            sys.exit(1)
            
    # 4. Detect Latest Run
    runs_df = con.sql("SELECT run_id, started_at, finished_at FROM runs ORDER BY started_at DESC LIMIT 1").df()
    
    if runs_df.empty:
        print("No runs found. Run 'python scripts/run_snapshot.py' first.")
        sys.exit(0)
        
    print("[OK] Preflight checks passed.")
    return runs_df.iloc[0].to_dict()

def get_run(con, run_id):
    df = con.sql(f"SELECT * FROM runs WHERE run_id = '{run_id}'").df()
    if df.empty:
        return None
    return df.iloc[0].to_dict()

def query_df(con, sql, params=None):
    try:
        if params:
            return con.execute(sql, params).df()
        return con.sql(sql).df()
    except Exception as e:
        print(f"[ERROR] Query failed: {sql}\nError: {e}")
        raise e

def render_df_markdown(df, limit=50):
    if df.empty:
        return "_No rows found._"
    
    # Truncate for markdown display
    display_df = df.head(limit).copy()
    return display_df.to_markdown(index=False)

def generate_report(con, run_id_str, output_dir, verify_only=False):
    # Setup
    if not os.path.exists(output_dir) and not verify_only:
        os.makedirs(output_dir)
        
    run_info = get_run(con, run_id_str)
    if not run_info:
        print(f"[ERROR] Run ID {run_id_str} not found.")
        sys.exit(1)
        
    run_short = str(run_id_str)[:8]
    date_str = pd.to_datetime(run_info['started_at']).strftime('%Y-%m-%d')
    output_base = f"{output_dir}/catalog_health_{date_str}_{run_short}"
    md_path = f"{output_base}.md"
    
    print(f"Generating report for Run {run_short} ({date_str})...")
    
    report_sections = []
    
    # Header
    report_sections.append(f"# Catalog Health Report: {date_str}")
    report_sections.append(f"**Run ID:** `{run_id_str}`")
    report_sections.append(f"**Started:** {run_info['started_at']}")
    report_sections.append(f"**Finished:** {run_info['finished_at']}")
    
    # A) Snapshot Summary
    summary_sql = f"""
    SELECT 
        (SELECT COUNT(*) FROM items_current) as total_items,
        (SELECT COUNT(*) FROM quality_scores WHERE run_id = '{run_id_str}') as scored_items,
        (SELECT COUNT(*) FROM health_checks WHERE run_id = '{run_id_str}') as checked_urls
    """
    summary_df = query_df(con, summary_sql)
    report_sections.append("## Snapshot Summary")
    report_sections.append(render_df_markdown(summary_df))
    
    # B) Quality Stats
    qual_sql = f"""
    SELECT 
        AVG(score) as avg_score, 
        MIN(score) as min_score, 
        MAX(score) as max_score,
        COUNT(CASE WHEN score >= 70 THEN 1 END) as count_high_quality,
        COUNT(CASE WHEN score < 50 THEN 1 END) as count_low_quality
    FROM quality_scores 
    WHERE run_id = '{run_id_str}'
    """
    qual_df = query_df(con, qual_sql)
    report_sections.append("## Quality Stats")
    report_sections.append(render_df_markdown(qual_df))

    # C) Top Issues
    issues_map = {
        'missing_tags': "SELECT item_id, title, owner FROM items_current WHERE COALESCE(tags_count,0)=0",
        'missing_description': "SELECT item_id, title, owner FROM items_current WHERE COALESCE(has_description,false)=false",
        'missing_extent': "SELECT item_id, title, owner FROM items_current WHERE COALESCE(has_extent,false)=false",
        'stale_items': "SELECT item_id, title, owner, modified_at FROM items_current WHERE modified_at < (now() - INTERVAL '2 years')",
        'broken_services': f"""
            SELECT i.title, i.owner, h.checked_url, h.status_code, h.error_message 
            FROM health_checks h 
            JOIN items_current i ON h.item_id = i.item_id 
            WHERE h.run_id = '{run_id_str}' AND h.ok = false
        """
    }
    
    report_sections.append("## Top Issues")
    
    for name, sql in issues_map.items():
        print(f" - Running check: {name}")
        df = query_df(con, sql)
        
        # Markdown section
        report_sections.append(f"### {name.replace('_', ' ').title()}")
        report_sections.append(render_df_markdown(df, limit=10))
        
        # CSV Export
        if not verify_only:
            csv_path = f"{output_base}_{name}.csv"
            df.to_csv(csv_path, index=False, encoding='utf-8')
            print(f"   -> Wrote {csv_path} ({len(df)} rows)")

    # D) By-Owner Aggregations
    owner_sql = """
    SELECT 
        owner,
        COUNT(*) as total_items,
        COUNT(CASE WHEN COALESCE(tags_count,0)=0 THEN 1 END) as missing_tags,
        COUNT(CASE WHEN COALESCE(has_description,false)=false THEN 1 END) as missing_description,
        COUNT(CASE WHEN modified_at < (now() - INTERVAL '2 years') THEN 1 END) as stale
    FROM items_current
    GROUP BY owner
    ORDER BY total_items DESC
    LIMIT 20
    """
    print(" - Aggregating by owner")
    owner_df = query_df(con, owner_sql)
    report_sections.append("## Owner Summary (Top 20)")
    report_sections.append(render_df_markdown(owner_df))
    if not verify_only:
        owner_csv = f"{output_base}_owner_summary.csv"
        owner_df.to_csv(owner_csv, index=False, encoding='utf-8')
        print(f"   -> Wrote {owner_csv} ({len(owner_df)} rows)")

    # E) History / Changes
    # Find header for history
    # For now, simple logic: Find prev run.
    prev_run_df = con.sql(f"SELECT run_id FROM runs WHERE start_time < (SELECT started_at FROM runs WHERE run_id='{run_id_str}') ORDER BY started_at DESC LIMIT 1").df() \
                  if 'start_time' in con.sql("PRAGMA table_info('runs')").df()['name'].tolist() else \
                  con.sql(f"SELECT run_id FROM runs WHERE started_at < (SELECT started_at FROM runs WHERE run_id='{run_id_str}') ORDER BY started_at DESC LIMIT 1").df()

    report_sections.append("## Changes Since Previous Run")
    
    if prev_run_df.empty:
        report_sections.append("_No previous run to compare._")
    else:
        # Changed Items (Logic: First seen in this run, but items_history has older entries?)
        # Or simpler: Just list items where first_seen_run_id == this_run_id
        # This covers NEW items and UPDATED items (because SCD2 logic inserts new version with first_seen_run_id=this_run? 
        # Wait, usually first_seen_run_id tracks when the ITEM ID was first seen. 
        # If we updated items_history logic correctly, a new version of an existing item would keep original first_seen_run_id?
        # Let's check schema. items_history has first_seen_run_id.
        # If I change an item, I insert a new history row. 
        # In snapshot.py:
        # INSERT INTO items_history (..., first_seen_run_id, ...) SELECT ..., ? as first_seen_run_id 
        # FROM stg_items LEFT JOIN items_history ... WHERE h.item_id IS NULL
        # This implies first_seen_run_id is set to CURRENT run for new rows.
        # So "first_seen_run_id = current_run" means "This version was created in this run".
        # To distinguish NEW item vs CHANGED item:
        # NEW item: all history rows for this item_id have first_seen_run_id = current_run (only 1 row usually, or multiple if crazy churn)
        # CHANGED item: there exist other history rows for this item_id with first_seen_run_id != current_run.
        
        changes_sql = f"""
        SELECT 
            h.item_id, h.title, h.owner, h.item_type,
            CASE 
                WHEN (SELECT COUNT(*) FROM items_history h2 WHERE h2.item_id = h.item_id AND h2.first_seen_run_id != '{run_id_str}') > 0 
                THEN 'Modified' 
                ELSE 'New' 
            END as change_type
        FROM items_history h
        WHERE h.first_seen_run_id = '{run_id_str}'
        LIMIT 20
        """
        changes_df = query_df(con, changes_sql)
        report_sections.append(render_df_markdown(changes_df))

    # Write Markdown
    if not verify_only:
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write("\n\n".join(report_sections))
        print(f"Report generated: {md_path}")
    else:
        print("[OK] Verification mode: Report generation logic passed.")


def main():
    parser = argparse.ArgumentParser(description="Generate Catalog Health Report")
    parser.add_argument("--run-id", help="Run ID to report on (defaults to latest)")
    parser.add_argument("--out-dir", default="reports", help="Output directory")
    parser.add_argument("--verify", action="store_true", help="Run checks only, do not write files")
    args = parser.parse_args()
    
    con = connect(read_only=True)
    try:
        # Preflight
        latest_run = preflight_or_exit(con)
        
        # Determine Run ID
        target_run_id = args.run_id if args.run_id else str(latest_run['run_id'])
        
        # Generate
        generate_report(con, target_run_id, args.out_dir, verify_only=args.verify)
        
    finally:
        con.close()

if __name__ == "__main__":
    main()
