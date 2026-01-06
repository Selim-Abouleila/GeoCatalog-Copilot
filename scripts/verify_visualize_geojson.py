import argparse
import sys
import os
import json

# Ensure project root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.tools.feature_layer_tools import query_preview_geojson

def main():
    parser = argparse.ArgumentParser(description="Verify Visualize GeoJSON generation")
    parser.add_argument("--item-id", required=True, help="Target Feature Service Item ID")
    parser.add_argument("--layer-index", type=int, default=0)
    parser.add_argument("--limit", type=int, default=50)
    args = parser.parse_args()
    
    print(f"Testing visualization for Input: {args.item_id}, Layer: {args.layer_index}")
    
    # query_preview_geojson now handles URLs natively
    result = query_preview_geojson(args.item_id, args.layer_index, limit=args.limit)
    
    print(f"OK: {result['ok']}")
    if result.get('error'):
        print(f"Error: {result['error']}")
        sys.exit(1) # Fail fast
        
    print(f"Layer Name: {result.get('layer_name')}")
    print(f"Geometry Type: {result.get('geometry_type')}")
    
    geojson = result.get('geojson')
    print(f"GeoJSON Type: {getattr(geojson, 'get', lambda x: None)('type')}")
    
    features = geojson.get('features') if geojson else None
    
    if features is None:
        print("[FAIL] 'features' is None!")
        sys.exit(1)
        
    if not isinstance(features, list):
        print(f"[FAIL] 'features' is not a list! Got {type(features)}")
        sys.exit(1)
        
    count = len(features)
    print(f"Feature Count: {count}")
    print(f"Computed Extent: {result.get('extent')}")
    
    # Check Coordinates for sanity (Lon/Lat)
    if count > 0:
        def get_pt(c):
            if isinstance(c[0], (int, float)): return c
            return get_pt(c[0])
            
        try:
            pt = get_pt(features[0]['geometry']['coordinates'])
            print(f"Sample Coordinate: {pt}")
            if abs(pt[0]) > 185 or abs(pt[1]) > 95:
                print("[FAIL] Coordinates look projected (not Lat/Lon)!")
                sys.exit(1)
            else:
                print("[PASS] Coordinates look like Lat/Lon.")
        except:
            print("[WARN] Could not parse geometry for check.")
    
    if result['ok'] and count >= 0:
        print("[SUCCESS] GeoJSON generated correctly.")
        sys.exit(0)
    else:
        print("[FAIL] Result not OK.")
        sys.exit(1)

if __name__ == "__main__":
    main()
