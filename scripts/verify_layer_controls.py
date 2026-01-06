
import sys
import os

# Add src to path
sys.path.append(os.path.join(os.getcwd()))

from src.ui.map_state import (
    init_map_state, 
    add_preview_layer, 
    remove_preview_layer, 
    clear_preview_layers,
    get_layer_key
)

def test_layer_controls():
    print("Testing Layer Controls...")
    
    # Mock State
    state = {}
    init_map_state(state)
    
    # Test Data
    l1 = {
        "item_id": "item1",
        "layer_index": 0,
        "name": "Layer 1",
        "geojson": {},
        "extent": [0,0,1,1]
    }
    l2 = {
        "item_id": "item2",
        "layer_index": 1,
        "name": "Layer 2",
        "geojson": {},
        "extent": [0,0,1,1]
    }
    
    # 1. Add Layers
    add_preview_layer(state, l1)
    add_preview_layer(state, l2)
    
    assert len(state["preview_layers"]) == 2, f"Expected 2 layers, got {len(state['preview_layers'])}"
    assert state["map_mode"] == "layer_view", "Should be in layer_view"
    
    print("[OK] Layers added")
    
    # 2. Check Keys
    key1 = get_layer_key("item1", 0)
    assert state["preview_layers"][0]["key"] == key1, "Layer key mismatch"
    
    # 3. Remove Layer 1
    remove_preview_layer(state, key1)
    assert len(state["preview_layers"]) == 1, "Expected 1 layer remaining"
    assert state["preview_layers"][0]["item_id"] == "item2", "Wrong layer removed"
    
    print("[OK] Layer removal")
    
    # 4. Remove Last Layer (Auto Exit)
    key2 = get_layer_key("item2", 1)
    remove_preview_layer(state, key2)
    assert len(state["preview_layers"]) == 0, "Expected 0 layers"
    assert state["map_mode"] == "browse", "Should revert to browse mode"
    
    print("[OK] Auto-exit layer view")
    
    # 5. Clear All
    add_preview_layer(state, l1)
    clear_preview_layers(state)
    assert len(state["preview_layers"]) == 0
    assert state["map_mode"] == "browse"
    
    print("[OK] Clear all")
    
    return True

if __name__ == "__main__":
    try:
        if test_layer_controls():
            print("\n[OK] Verification Passed")
            sys.exit(0)
    except Exception as e:
        print(f"\n[FAIL] Verification Failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
