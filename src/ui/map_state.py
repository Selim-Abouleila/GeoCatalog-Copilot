from typing import Dict, Any, List

def init_map_state(state: Dict[str, Any]):
    """Initializes session state variables for map visualization."""
    defaults = {
        "map_mode": "browse",            # browse | layer_view
        "preview_layers": [],            # List[Dict]
        "pending_zoom_extent": None,     # [xmin, ymin, xmax, ymax]
        "map_center": [20, 0],
        "map_zoom": 2
    }
    for k, v in defaults.items():
        if k not in state:
            state[k] = v

def enter_layer_view(state: Dict[str, Any]):
    """Switches map mode to layer_view."""
    state["map_mode"] = "layer_view"

def exit_layer_view(state: Dict[str, Any]):
    """Exits layer view, clears previews, and resets mode to browse."""
    state["map_mode"] = "browse"
    state["preview_layers"] = []
    state["pending_zoom_extent"] = None

def add_preview_layer(state: Dict[str, Any], layer_data: Dict[str, Any]):
    """
    Adds a layer to previews. 
    layer_data expected keys: item_id, layer_index, name, geojson, extent
    """
    # Check for duplicates
    item_id = layer_data.get('item_id')
    layer_idx = layer_data.get('layer_index')
    
    exists = False
    for layer in state["preview_layers"]:
        if layer.get('item_id') == item_id and layer.get('layer_index') == layer_idx:
            exists = True
            break
    
    if not exists:
        state["preview_layers"].append(layer_data)
        
    # Auto-switch mode
    enter_layer_view(state)
    
    # Trigger Zoom if extent exists
    if layer_data.get('extent'):
        set_pending_zoom(state, layer_data['extent'])

def remove_preview_layer(state: Dict[str, Any], index: int):
    """Removes a layer by index."""
    if 0 <= index < len(state["preview_layers"]):
        state["preview_layers"].pop(index)
        
    if not state["preview_layers"]:
        exit_layer_view(state)

def set_pending_zoom(state: Dict[str, Any], extent: List[float]):
    """Sets the pending zoom extent [xmin, ymin, xmax, ymax]."""
    state["pending_zoom_extent"] = extent

def consume_pending_zoom(state: Dict[str, Any]):
    """Returns the pending zoom extent and clears it."""
    extent = state.get("pending_zoom_extent")
    state["pending_zoom_extent"] = None
    return extent
