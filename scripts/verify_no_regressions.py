import sys
import os

# Ensure project root is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

def main():
    print("Verifying No Regressions...")
    
    try:
        # 1. Verify Imports of Key Service Modules
        from src.services.arcgis_client import get_gis
        from src.services.catalog_store import get_status
        from src.services.report_store import list_reports
        print("[OK] Service modules imported.")
        
        # 2. Verify Imports of New Tools
        from src.tools.feature_layer_tools import resolve_item, get_row_counts
        from src.ui.map_overlays import add_geojson_overlay
        print("[OK] New Feature/UI tools imported.")
        
        # 3. Verify App Logic (Minimal)
        # We can't easily import app.py because it runs streamlit commands on top level
        # But we can check if key files exist
        if not os.path.exists("app.py"):
            raise FileNotFoundError("app.py missing")
            
        print("[OK] app.py exists.")
        
    except ImportError as e:
        print(f"[ERROR] Import failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] Logic check failed: {e}")
        sys.exit(1)
        
    print("[OK] Regression check passed.")

if __name__ == "__main__":
    main()
