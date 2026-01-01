import sys
import os

# Ensure project root is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.storage.duckdb_client import ensure_db_initialized, connect, list_tables

def main():
    print("Initializing DuckDB Local Warehouse...")
    
    try:
        db_path = ensure_db_initialized()
        print(f"[OK] DuckDB initialized at {db_path}")
        
        # Open connection to list tables
        con = connect(read_only=True)
        try:
            tables = list_tables(con)
            print("Tables:")
            for table in tables:
                print(f" - {table}")
        finally:
            con.close()
            
        sys.exit(0)
        
    except Exception as e:
        print(f"[ERROR] Initialization failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
