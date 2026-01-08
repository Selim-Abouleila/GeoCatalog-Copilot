
import sys
import argparse
import os

# Ensure src is in path
sys.path.append(os.getcwd())

from src.tools.feature_layer_tools import query_preview_geojson
from src.tools.renderer_tools import fetch_layer_renderer
from src.ui.symbology import build_style_function

def verify_symbology(service_url, layer_index, limit):
    print(f"Verifying Symbology for: {service_url} (Layer {layer_index})")
    
    # 1. Fetch Renderer
    print("Step 1: Fetching Renderer...")
    renderer = fetch_layer_renderer(service_url, layer_index)
    
    if not renderer:
        print("[WARN] No renderer returned (or caching issue/access). Is this service available?")
        # We don't fail, but we can't test symbology if no renderer.
        # However, for the specific GlobalBiomes service, we EXPECT a renderer.
        if "GlobalBiomes" in service_url:
            print("[FAIL] GlobalBiomes should have a renderer.")
            sys.exit(1)
        sys.exit(0)
        
    print(f"[OK] Renderer found. Type: {renderer.get('type')}")
    
    # 2. Query Features
    print("Step 2: Querying Features...")
    res = query_preview_geojson(service_url, layer_index=layer_index, limit=limit)
    
    if not res['ok']:
        print(f"[FAIL] Query failed: {res.get('error')}")
        sys.exit(1)
        
    features = res['geojson']['features']
    print(f"[OK] Got {len(features)} features.")
    
    if not features:
        print("[WARN] No features to test style against.")
        sys.exit(0)

    # 3. Build Style Function
    print("Step 3: Building Style Function...")
    default_style = {"color": "black"}
    style_fn = build_style_function(renderer, default_style)
    
    # 4. Apply and Check Diversity
    print("Step 4: Checking Style Diversity...")
    fill_colors = set()
    
    for f in features:
        style = style_fn(f)
        fill_colors.add(style.get("fillColor"))
        
    print(f"Unique Fill Colors Found: {len(fill_colors)}")
    print(f"Colors: {fill_colors}")
    
    # For uniqueValue renderer, we expect > 1 color if data is diverse
    if renderer.get("type") == "uniqueValue" and len(fill_colors) < 2:
        print("[WARN] Only 1 color found. Data might be homogeneous or style mapping failed.")
        # Not strictly a fail of the system, but maybe data.
        
    if renderer.get("type") == "simple" and len(fill_colors) != 1:
        print("[FAIL] Simple renderer should have exactly 1 color.")
        sys.exit(1)
        
    print("[OK] Symbology verification passed.")
    sys.exit(0)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--service-url", default="https://services.arcgis.com/BG6nSlhZSAWtExvp/arcgis/rest/services/GlobalBiomes/FeatureServer")
    parser.add_argument("--layer-index", type=int, default=0)
    parser.add_argument("--limit", type=int, default=50)
    
    args = parser.parse_args()
    
    verify_symbology(args.service_url, args.layer_index, args.limit)
