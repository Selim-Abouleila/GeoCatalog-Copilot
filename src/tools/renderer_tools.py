
import streamlit as st
from arcgis.gis import GIS
from arcgis.features import FeatureLayer
from typing import Dict, Any, Optional
from src.tools.feature_layer_tools import resolve_item, normalize_layer_input

@st.cache_data(ttl=3600)
def fetch_layer_renderer(service_url_or_id: str, layer_index: int = 0) -> Optional[Dict[str, Any]]:
    """
    Fetches the drawingInfo.renderer from an ArcGIS Feature Layer.
    Uses st.cache_data to prevent repetitive network calls.
    """
    try:
        # Use a lightweight anonymous GIS if possible, or global one
        # For simple metadata fetching, anonymous usually works for public items.
        # If it fails, one might need 'get_gis()' but let's try anonymous first 
        # to avoid overhead, or just use get_gis if imported.
        from src.services.arcgis_client import get_gis
        try:
            gis = get_gis()
        except:
            gis = GIS()
            
        # Resolve the object
        obj = resolve_item(service_url_or_id, gis)
        
        target_layer = None
        
        # Logic similar to query_preview_geojson to find the specific layer
        if hasattr(obj, 'layers'):
            if len(obj.layers) > layer_index:
                target_layer = obj.layers[layer_index]
        elif isinstance(obj, FeatureLayer):
            target_layer = obj
            
        if target_layer and hasattr(target_layer, 'properties'):
            if hasattr(target_layer.properties, 'drawingInfo'):
                return target_layer.properties.drawingInfo.renderer
            
        return None
        
    except Exception as e:
        # Fail silently/safely as requested
        return None

def normalize_esri_color(color_array) -> tuple:
    """
    Converts [r, g, b, a] to (hex_string, opacity_float).
    """
    if not color_array or len(color_array) < 3:
        return "#3388ff", 0.4
        
    r, g, b = color_array[0], color_array[1], color_array[2]
    a = color_array[3] if len(color_array) > 3 else 255
    
    return f"#{r:02x}{g:02x}{b:02x}", a / 255.0
