from typing import Dict, Any, List, Optional

def init_map_state(state: Dict[str, Any]):
    """Initializes session state variables for map visualization."""
    defaults = {
        "map_mode": "browse",            # browse | layer_view
        "preview_layers": [],            # List[Dict]
        "pending_zoom_extent": None,     # [xmin, ymin, xmax, ymax]
        "map_center": [20, 0],
        "map_zoom": 2,
        "map_html_cache": None,          # Cache for static map HTML
        "map_signature": None            # Hash/Tuple to detect changes
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
    state["map_html_cache"] = None
    state["map_signature"] = None

def get_layer_key(item_id: str, layer_index: int) -> str:
    """Generates a consistent key for a layer."""
    return f"{item_id}:{layer_index}"

def add_preview_layer(state: Dict[str, Any], layer_data: Dict[str, Any]):
    """
    Adds a layer to previews. 
    layer_data expected keys: item_id, layer_index, name, geojson, extent
    """
    item_id = layer_data.get('item_id')
    layer_idx = layer_data.get('layer_index')
    
    # Ensure key exists
    if 'key' not in layer_data:
        layer_data['key'] = get_layer_key(item_id, layer_idx)
    
    # Check for duplicates by key
    exists = any(l.get('key') == layer_data['key'] for l in state["preview_layers"])
    
    if not exists:
        state["preview_layers"].append(layer_data)
        
    # Auto-switch mode
    enter_layer_view(state)
    
    # Trigger Zoom if extent exists
    if layer_data.get('extent'):
        set_pending_zoom(state, layer_data['extent'])

def remove_preview_layer(state: Dict[str, Any], layer_key: str):
    """Removes a layer by its unique key."""
    initial_len = len(state["preview_layers"])
    state["preview_layers"] = [l for l in state["preview_layers"] if l.get('key') != layer_key]
    
    if len(state["preview_layers"]) < initial_len:
        # Clear cache if something changed
        state["map_html_cache"] = None
        state["map_signature"] = None
        
    if not state["preview_layers"]:
        exit_layer_view(state)

def clear_preview_layers(state: Dict[str, Any]):
    """Clears all preview layers."""
    state["preview_layers"] = []
    exit_layer_view(state)

def set_pending_zoom(state: Dict[str, Any], extent: List[float]):
    """Sets the pending zoom extent [xmin, ymin, xmax, ymax]."""
    state["pending_zoom_extent"] = extent

def consume_pending_zoom(state: Dict[str, Any]):
    """Returns the pending zoom extent and clears it."""
    extent = state.get("pending_zoom_extent")
    state["pending_zoom_extent"] = None
    return extent
