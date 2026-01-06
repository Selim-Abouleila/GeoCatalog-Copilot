
import streamlit as st
from typing import List, Dict, Any, Callable
from src.tools.feature_layer_tools import query_preview_geojson

def refresh_preview_layers(
    preview_layers: List[Dict[str, Any]], 
    limit: int, 
    query_fn: Callable = query_preview_geojson
) -> List[Dict[str, Any]]:
    """
    Refreshes all preview layers with the specified limit.
    Maintains stable keys and handles errors by keeping old data if fetch fails.
    """
    updated_layers = []
    
    for layer in preview_layers:
        item_id = layer.get('item_id')
        layer_idx = layer.get('layer_index', 0)
        
        # If sufficient metadata exists to re-query
        if item_id:
            try:
                # Re-query
                res = query_fn(item_id, layer_index=layer_idx, limit=limit)
                
                if res['ok']:
                    # Update Content
                    new_layer = layer.copy()
                    new_layer['geojson'] = res['geojson']
                    new_layer['name'] = res['layer_name'] # Optional update
                    new_layer['geometry_type'] = res.get('geometry_type', layer.get('geometry_type'))
                    if res.get('extent'):
                        new_layer['extent'] = res['extent']
                    
                    updated_layers.append(new_layer)
                else:
                    # Keep old layer on failure, maybe log?
                    updated_layers.append(layer)
                    
            except Exception:
                # Keep old layer on exception
                updated_layers.append(layer)
        else:
            # Cannot refresh, keep as is
            updated_layers.append(layer)
            
    return updated_layers
