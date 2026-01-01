import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.storage.duckdb_client import connect

def main():
    print("Verifying Snapshot Data...")
    try:
        con = connect(read_only=True)
        
        # Counts
        runs = con.sql("SELECT COUNT(*) FROM runs").fetchone()[0]
        items = con.sql("SELECT COUNT(*) FROM items_current").fetchone()[0]
        scores = con.sql("SELECT COUNT(*) FROM quality_scores").fetchone()[0]
        health = con.sql("SELECT COUNT(*) FROM health_checks").fetchone()[0]
        
        print(f"\n[Counts]\nRuns: {runs}\nItems (Current): {items}\nScores: {scores}\nHealth Checks: {health}")
        
        # Governance Checks
        print("\n[Missing Tags (Limit 5)]")
        missing_tags = con.sql("SELECT item_id, title, owner FROM items_current WHERE tags_count = 0 LIMIT 5").fetchall()
        for row in missing_tags:
            print(f" - {row}")
            
        print("\n[Missing Description (Limit 5)]")
        missing_desc = con.sql("SELECT item_id, title, owner FROM items_current WHERE has_description = false LIMIT 5").fetchall()
        for row in missing_desc:
            print(f" - {row}")

        con.close()
        print("\n[OK] Verification Done")
        
    except Exception as e:
        print(f"[ERROR] Verification failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
