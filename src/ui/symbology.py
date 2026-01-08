
from typing import Dict, Any, Callable
from src.tools.renderer_tools import normalize_esri_color

def build_style_function(renderer: Dict[str, Any], default_style: Dict[str, Any]) -> Callable:
    """
    Constructs a Folium style function from an ArcGIS renderer dictionary.
    Supports 'simple' and 'uniqueValue' types.
    """
    if not renderer:
        return lambda x: default_style

    rtype = renderer.get("type")

    # --- 1. Simple Renderer ---
    if rtype == "simple":
        symbol = renderer.get("symbol", {})
        color_arr = symbol.get("color")
        outline = symbol.get("outline", {})
        outline_color_arr = outline.get("color")
        width = outline.get("width", 1)
        
        fill_hex, fill_uopa = normalize_esri_color(color_arr)
        line_hex, line_opa = normalize_esri_color(outline_color_arr)
        
        style = {
            "fillColor": fill_hex,
            "color": line_hex,
            "weight": width,
            "fillOpacity": fill_uopa,
            "opacity": line_opa
        }
        return lambda x: style

    # --- 2. Unique Value Renderer ---
    elif rtype == "uniqueValue":
        field1 = renderer.get("field1")
        field2 = renderer.get("field2")
        field3 = renderer.get("field3")
        delimiter = renderer.get("fieldDelimiter", ",")
        default_symbol = renderer.get("defaultSymbol")
        
        # Build Lookup
        lookup = {}
        for info in renderer.get("uniqueValueInfos", []):
            val = str(info.get("value"))
            sym = info.get("symbol", {})
            
            fill_hex, fill_opa = normalize_esri_color(sym.get("color"))
            line_hex, line_opa = normalize_esri_color(sym.get("outline", {}).get("color"))
            width = sym.get("outline", {}).get("width", 1)
            
            lookup[val] = {
                "fillColor": fill_hex,
                "color": line_hex,
                "weight": width,
                "fillOpacity": fill_opa,
                "opacity": line_opa
            }
            
        # Default fallback style
        fallback = default_style
        if default_symbol:
            d_fill, d_opa = normalize_esri_color(default_symbol.get("color"))
            d_line, d_lop = normalize_esri_color(default_symbol.get("outline", {}).get("color"))
            fallback = {
                "fillColor": d_fill, "color": d_line, "weight": 1, "fillOpacity": d_opa, "opacity": d_lop
            }
            
        def style_fn(feature):
            props = feature.get("properties", {})
            # Construct key
            # ArcGIS treats nulls/formatting loosely, but we try basic string match
            val1 = str(props.get(field1, "")) if field1 else ""
            
            # TODO: Add multi-field support if needed, usually field1 is enough
            # Key construction depends on delimiter if multiple fields
            key = val1 
            if field2: key += delimiter + str(props.get(field2, ""))
            if field3: key += delimiter + str(props.get(field3, ""))
            
            return lookup.get(key, fallback)
            
        return style_fn

    # --- Fallback ---
    return lambda x: default_style
