import sys
import os

# Ensure project root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.ui.map_state import init_map_state, enter_layer_view, exit_layer_view, add_preview_layer, remove_preview_layer, set_pending_zoom, consume_pending_zoom

def verify_map_state():
    print("Verifying Map State Logic...")
    
    # Mock State
    state = {}
    init_map_state(state)
    
    # 1. Init
    assert state["map_mode"] == "browse"
    assert state["preview_layers"] == []
    print("[OK] Init defaults")
    
    # 2. Add Layer
    layer = {
        "item_id": "123",
        "layer_index": 0,
        "name": "Test Layer",
        "geojson": {},
        "extent": [-10, -10, 10, 10]
    }
    add_preview_layer(state, layer)
    
    assert state["map_mode"] == "layer_view"
    assert len(state["preview_layers"]) == 1
    assert state["pending_zoom_extent"] == [-10, -10, 10, 10]
    print("[OK] Add layer + Auto mode switch + Auto zoom")
    
    # 3. Consume Zoom
    zoom = consume_pending_zoom(state)
    assert zoom == [-10, -10, 10, 10]
    assert state["pending_zoom_extent"] is None
    print("[OK] Consume zoom")
    
    # 4. Remove Layer
    remove_preview_layer(state, 0)
    assert len(state["preview_layers"]) == 0
    assert state["map_mode"] == "browse" # Should exit if empty
    print("[OK] Remove layer + Auto exit")
    
    # 5. Add and Explicit Exit
    add_preview_layer(state, layer)
    exit_layer_view(state)
    assert state["map_mode"] == "browse"
    assert len(state["preview_layers"]) == 0
    print("[OK] Explicit Exit")

    print("[SUCCESS] All map state checks passed.")

if __name__ == "__main__":
    verify_map_state()
