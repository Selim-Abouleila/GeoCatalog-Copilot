import duckdb
import pandas as pd
from datetime import datetime, timezone
from typing import Dict, Any, Optional
import sys
import os

# Ensure we can import from src.storage
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from src.storage.duckdb_client import connect, get_db_path

def get_status() -> Dict[str, Any]:
    """
    Performs preflight checks and returns status metrics.
    """
    db_path = get_db_path()
    
    try:
        con = connect(read_only=True)
    except Exception as e:
         return {"ok": False, "error": f"Connection failed: {e}", "hint": "Run 'python scripts/init_duckdb.py'"}

    try:
        # 1. Preflight Checks (Tables)
        required_tables = ['runs', 'items_current', 'quality_scores', 'health_checks', 'items_history']
        existing_tables_df = con.sql("SELECT table_name FROM information_schema.tables WHERE table_schema='main'").df()
        existing_tables = set(existing_tables_df['table_name'].tolist())
        
        missing = [t for t in required_tables if t not in existing_tables]
        if missing:
            con.close()
            return {"ok": False, "error": f"Missing tables: {missing}", "hint": "Run 'python scripts/init_duckdb.py'"}
            
        # 2. Latest Run
        runs_df = con.sql("SELECT run_id, started_at, finished_at FROM runs ORDER BY started_at DESC LIMIT 1").df()
        
        if runs_df.empty:
            con.close()
            return {"ok": True, "has_runs": False, "db_path": str(db_path)}
            
        run = runs_df.iloc[0]
        run_id = str(run['run_id'])
        
        # 3. Counts
        item_count = con.sql("SELECT COUNT(*) FROM items_current").fetchone()[0]
        score_count = con.sql(f"SELECT COUNT(*) FROM quality_scores WHERE run_id = '{run_id}'").fetchone()[0]
        health_count = con.sql(f"SELECT COUNT(*) FROM health_checks WHERE run_id = '{run_id}'").fetchone()[0]
        broken_count = con.sql(f"SELECT COUNT(*) FROM health_checks WHERE run_id = '{run_id}' AND ok = false").fetchone()[0]
        
        con.close()
        
        return {
            "ok": True,
            "has_runs": True,
            "db_path": str(db_path),
            "latest_run": {
                "run_id": run_id,
                "short_id": run_id[:8],
                "started_at": run['started_at'],
                "finished_at": run['finished_at']
            },
            "metrics": {
                "items": item_count,
                "scores": score_count,
                "health_checks": health_count,
                "broken_services": broken_count
            }
        }
        
    except Exception as e:
        con.close()
        return {"ok": False, "error": f"Query error: {e}", "hint": "Check database integrity."}

def get_latest_run_id() -> Optional[str]:
    try:
        con = connect(read_only=True)
        res = con.sql("SELECT run_id FROM runs ORDER BY started_at DESC LIMIT 1").fetchone()
        con.close()
        return str(res[0]) if res else None
    except:
        return None

def admin_queries(run_id: str) -> Dict[str, pd.DataFrame]:
    """
    Returns DataFrames for admin/governance dashboards.
    """
    con = connect(read_only=True)
    results = {}
    
    queries = {
        'missing_tags': "SELECT item_id, title, owner, tags_json FROM items_current WHERE COALESCE(tags_count,0)=0 LIMIT 50",
        'missing_description': "SELECT item_id, title, owner FROM items_current WHERE COALESCE(has_description,false)=false LIMIT 50",
        'missing_extent': "SELECT item_id, title, owner FROM items_current WHERE COALESCE(has_extent,false)=false LIMIT 50",
        'stale_items': "SELECT item_id, title, owner, modified_at FROM items_current WHERE modified_at < (now() - INTERVAL '2 years') LIMIT 50",
        'broken_services': f"""
            SELECT i.title, i.owner, h.checked_url, h.status_code, h.error_message 
            FROM health_checks h 
            JOIN items_current i ON h.item_id = i.item_id 
            WHERE h.run_id = '{run_id}' AND h.ok = false
            LIMIT 50
        """,
        'owner_summary': """
            SELECT 
                owner,
                COUNT(*) as total_items,
                COUNT(CASE WHEN COALESCE(tags_count,0)=0 THEN 1 END) as missing_tags,
                COUNT(CASE WHEN COALESCE(has_description,false)=false THEN 1 END) as missing_desc,
                COUNT(CASE WHEN modified_at < (now() - INTERVAL '2 years') THEN 1 END) as stale
            FROM items_current
            GROUP BY owner
            ORDER BY total_items DESC
            LIMIT 20
        """
    }
    
    for key, sql in queries.items():
        try:
            results[key] = con.sql(sql).df()
        except Exception as e:
            # Return empty DF with error note in a column if needed, or just empty
            print(f"Error in admin_query {key}: {e}")
            results[key] = pd.DataFrame()
            
    con.close()
    return results
