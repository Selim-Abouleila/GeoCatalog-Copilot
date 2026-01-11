import argparse
import sys
import os
import json

# Ensure project root is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.services.arcgis_client import get_gis
from src.tools.feature_layer_tools import resolve_item, get_row_counts, query_preview_geojson

def main():
    parser = argparse.ArgumentParser(description="Verify Feature Layer Tools")
    parser.add_argument("--item-id", default="bda3db242d644d64a91b5b1ecb781e6f", help="Target Item ID")
    parser.add_argument("--limit", type=int, default=50, help="Preview limit")
    args = parser.parse_args()
    
    print(f"Connecting to ArcGIS...")
    gis = get_gis()
    
    print(f"Resolving item {args.item_id}...")
    try:
        item = resolve_item(args.item_id, gis)
        print(f"[OK] Found: {item.title} ({item.type})")
    except Exception as e:
        print(f"[ERROR] Resolve failed: {e}")
        sys.exit(1)
        
    print("\nCounting rows...")
    try:
        counts = get_row_counts(item)
        print(json.dumps(counts, indent=2))
        
        if counts['total_count'] < 0: # Some error
             print("[WARN] Total count is negative or zero, might be empty or restricted.")
    except Exception as e:
        print(f"[ERROR] Count rows failed: {e}")
        sys.exit(1)
        
    print(f"\nQuerying preview (limit={args.limit})...")
    try:
        # Try layer 0
        preview = query_preview_geojson(item, layer_index=0, limit=args.limit)
        
        if not preview['ok']:
             print(f"[ERROR] Preview failed: {preview.get('error')}")
             sys.exit(1)
             
        feat_len = len(preview['geojson'].get('features', []))
        print(f"[OK] Got {feat_len} features")
        print(f"GeoJSON Type: {preview['geojson'].get('type')}")
        
        if feat_len == 0 and counts['total_count'] > 0:
            print("[WARN] Preview returned 0 features but count > 0. Extent issue?")
            
    except Exception as e:
        print(f"[ERROR] Preview query failed: {e}")
        sys.exit(1)
        
    print("\n[OK] all verifications passed.")

if __name__ == "__main__":
    main()
