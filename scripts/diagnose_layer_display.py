import argparse
import sys
import os
import urllib.parse
from arcgis.gis import GIS

# Ensure project root in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.tools.feature_layer_tools import resolve_item, query_preview_geojson, _calculate_extent_from_features

def parse_input(input_str):
    """
    Diagnose input string to determine type and extract valid target.
    Returns: (type, resolved_target, layer_index_hint)
    """
    # 1. Map Viewer URL with ?url=
    if "apps/mapviewer" in input_str and "url=" in input_str:
        try:
            parsed = urllib.parse.urlparse(input_str)
            qs = urllib.parse.parse_qs(parsed.query)
            if 'url' in qs:
                service_url = qs['url'][0]
                return "mapviewer_url", service_url, 0 # Default to 0 for URL
        except Exception as e:
            print(f"[WARN] Failed to parse Map Viewer URL: {e}")
    
    # 2. Service URL (FeatureServer/MapServer)
    if "/FeatureServer" in input_str or "/MapServer" in input_str:
        return "service_url", input_str, 0
        
    # 3. Item ID (default assumption if not URL)
    # Simple regex or length check could apply, but let's assume item_id
    if "http" not in input_str and len(input_str) > 10:
        return "item_id", input_str, 0 # Layer index override via arg usually
        
    return "unknown", input_str, 0

def diagnose(input_str, layer_index, limit, max_allowable_offset, out_sr):
    print("==========================================")
    print("       LAYER DISPLAY DIAGNOSTIC           ")
    print("==========================================")
    print(f"Input: {input_str}")
    
    # 1. Parse Input
    in_type, target, default_idx = parse_input(input_str)
    print(f"Resolved Type: {in_type}")
    print(f"Target: {target}")
    
    used_layer_index = layer_index 
    
    # 2. Resolve Item / Service
    # Note: feature_layer_tools currently expects item_id or simple URL. 
    # We essentially mock what the UI will pass to it.
    
    print(f"Querying Layer Index: {used_layer_index}")
    print(f"Requesting Out SR: {out_sr}")
    
    # We will use the existing tool function, but we might care about 
    # how it handles the input. For this script, we pass 'target' 
    # which might be a raw URL or item ID.
    
    try:
        # Note: Current query_preview_geojson might fail on raw URLs until we fix it.
        # But this script is also to verify the FIX.
        # For now, let's try to see if it works or fails.
        
        # We manually construct args to emulate potential future args if not present
        # but for now we rely on query_preview_geojson signature
        res = query_preview_geojson(target, layer_index=used_layer_index, limit=limit)
        
        if not res['ok']:
            print(f"[ERROR] Tool returned error: {res['error']}")
            sys.exit(1)
            
        print(f"[SUCCESS] Layer Name: {res['layer_name']}")
        print(f"Geometry Type: {res['geometry_type']}")
        
        geojson = res['geojson']
        features = geojson.get('features', [])
        count = len(features)
        print(f"Feature Count: {count}")
        
        if count == 0:
            print("[WARN] 0 features returned. Cannot verify coordinates.")
            # Not necessarily a failure of the script, but suspicious for display
            sys.exit(0) 
            
        # 3. Coordinate Analysis
        min_x, min_y, max_x, max_y = float('inf'), float('inf'), float('-inf'), float('-inf')
        
        # Check first few features
        sample_size = min(count, 100)
        
        def flatten(c):
            if isinstance(c[0], (int, float)):
                yield c
            else:
                for sub in c:
                    yield from flatten(sub)
                    
        valid_coords = False
        
        for i in range(sample_size):
            geom = features[i].get('geometry')
            if not geom or 'coordinates' not in geom: continue
            
            for pt in flatten(geom['coordinates']):
                x, y = pt[0], pt[1]
                if x < min_x: min_x = x
                if y < min_y: min_y = y
                if x > max_x: max_x = x
                if y > max_y: max_y = y
                valid_coords = True
                
        if not valid_coords:
            print("[ERROR] No valid coordinates found in samples.")
            sys.exit(1)
            
        print(f"Coordinate Range: X[{min_x:.4f}, {max_x:.4f}] Y[{min_y:.4f}, {max_y:.4f}]")
        
        # 4. Projection Check
        is_lat_lon = (-180 <= min_x <= 180) and (-90 <= min_y <= 90)
        if not is_lat_lon:
            print("[FAIL] Coordinates are clearly NOT Lat/Lon (EPSG:4326).")
            print("       Likely WebMercator or local projection.")
            print("       Streamlit Folium will NOT display this correctly without projection.")
            sys.exit(1)
        else:
            print("[PASS] Coordinates look like Lat/Lon.")
            
        sys.exit(0)

    except Exception as e:
        print(f"[FATAL] Script crashed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="Item ID, FeatureServer URL, or MapViewer URL")
    parser.add_argument("--layer-index", type=int, default=0)
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--out-sr", type=int, default=4326)
    parser.add_argument("--max-allowable-offset", type=float, default=None)
    
    args = parser.parse_args()
    
    diagnose(args.input, args.layer_index, args.limit, args.max_allowable_offset, args.out_sr)
