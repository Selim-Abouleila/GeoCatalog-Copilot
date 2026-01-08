
import folium
import sys

def verify_leaflet_focus_css():
    print("Verifying Leaflet Focus CSS Injection...")
    
    # 1. Simulate map build (simplified)
    m = folium.Map(location=[0, 0], zoom_start=2)
    
    # This is the CSS we expect
    expected_fragment = ".leaflet-interactive:focus { outline: none !important; }"
    
    # 2. Add the CSS (This is what we will implement in the app, but here we just check if the app's logic WOULD add it,
    # or rather, this script is intended to run AFTER we mod the app. 
    # WAIT - this script needs to use the APP code to verify.
    # So we should import build_folium_map.
    
    try:
        sys.path.append(".")
        from src.ui.map_renderer import build_folium_map
    except ImportError:
        print("[FAIL] Could not import build_folium_map")
        sys.exit(1)
        
    # Build map using actual app logic
    m_app = build_folium_map(
        base_center=[0, 0], 
        base_zoom=2, 
        overlays=[], 
        pending_zoom_extent=None
    )
    
    html = m_app.get_root().render()
    
    if expected_fragment in html:
        print("[OK] CSS found in map HTML.")
        sys.exit(0)
    else:
        print("[FAIL] CSS NOT found in map HTML.")
        sys.exit(1)

if __name__ == "__main__":
    verify_leaflet_focus_css()
