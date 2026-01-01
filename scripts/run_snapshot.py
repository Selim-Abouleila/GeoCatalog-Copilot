import argparse
import sys
import os

# Ensure project root is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.storage.duckdb_client import ensure_db_initialized, connect
from src.services.arcgis_client import get_gis
from src.pipeline.snapshot import run_snapshot

def main():
    parser = argparse.ArgumentParser(description="Run ArcGIS Snapshot Pipeline")
    parser.add_argument("--max-items", type=int, default=50, help="Max items to fetch")
    parser.add_argument("--query", type=str, default=None, help="ArcGIS search query")
    parser.add_argument("--item-types", type=str, default=None, help="Comma-separated item types")
    parser.add_argument("--no-history", action="store_true", help="Disable SCD2 history")
    parser.add_argument("--no-scores", action="store_true", help="Disable quality scores")
    parser.add_argument("--no-health", action="store_true", help="Disable health checks")
    
    args = parser.parse_args()
    
    try:
        # 1. Init DB
        ensure_db_initialized()
        
        # 2. Connect GIS
        print("Connecting to ArcGIS...")
        gis = get_gis()
        print(f"Connected to: {gis.url}")
        
        # 3. Parse types
        item_types_list = [t.strip() for t in args.item_types.split(",")] if args.item_types else None
        
        # 4. Run Pipeline
        print(f"Starting snapshot (max_items={args.max_items})...")
        con = connect()
        
        run_snapshot(
            con, 
            gis, 
            max_items=args.max_items,
            query=args.query,
            item_types=item_types_list,
            enable_history=not args.no_history,
            enable_scores=not args.no_scores,
            enable_health=not args.no_health
        )
        
        con.close()
        print("[OK] Snapshot complete")
        sys.exit(0)
        
    except Exception as e:
        print(f"[ERROR] Snapshot failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
