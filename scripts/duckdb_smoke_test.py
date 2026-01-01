import sys
import os

# Ensure project root is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.storage.duckdb_client import connect

def main():
    print("Running DuckDB Smoke Test...")
    
    try:
        con = connect(read_only=False)
        
        # Create test table
        con.sql("CREATE TABLE IF NOT EXISTS smoke_test(id INT, name TEXT)")
        
        # Insert test row
        con.sql("DELETE FROM smoke_test WHERE id = 1")
        con.sql("INSERT INTO smoke_test VALUES (1, 'hello')")
        
        # Select and verify
        result = con.sql("SELECT * FROM smoke_test").fetchall()
        print(f"Output: {result}")
        
        con.close()
        
        if result == [(1, 'hello')]:
            print("[OK] Smoke test passed!")
            sys.exit(0)
        else:
            print("[ERROR] Smoke test failed: output mismatch")
            sys.exit(1)
            
    except Exception as e:
        print(f"[ERROR] Smoke test failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
