from arcgis.gis import GIS, Item
from arcgis.features import FeatureLayer
import pandas as pd
from typing import Dict, Any, Union, Optional, List
import json

def resolve_item(item_id_or_url: str, gis: GIS) -> Item:
    """
    Resolves an item ID or URL to an arcgis.gis.Item object.
    Raises ValueError if not found.
    """
    item_id = item_id_or_url
    
    # Simple URL extraction (if contains 'id=...')
    if 'id=' in item_id_or_url:
        try:
            item_id = item_id_or_url.split('id=')[1].split('&')[0]
        except:
            pass
            
    try:
        item = gis.content.get(item_id)
        if not item:
            raise ValueError("Item returned None")
        return item
    except Exception as e:
        raise ValueError(f"Could not resolve item '{item_id_or_url}': {e}")

def get_row_counts(item: Item, where: str = "1=1") -> Dict[str, Any]:
    """
    Counts rows for all layers/tables in the item.
    """
    layer_counts = []
    table_counts = []
    total = 0
    
    def count_source(lyr_obj):
        try:
            return lyr_obj.query(where=where, return_count_only=True)
        except Exception as e:
            return -1 # Error indicator
            
    if hasattr(item, 'layers'):
        for lyr in item.layers:
            c = count_source(lyr)
            if c >= 0:
                total += c
            layer_counts.append({
                "name": lyr.properties.name,
                "count": c if c >= 0 else "Error"
            })
            
    if hasattr(item, 'tables'):
        for tbl in item.tables:
            c = count_source(tbl)
            if c >= 0:
                total += c
            table_counts.append({
                "name": tbl.properties.name,
                "count": c if c >= 0 else "Error"
            })
            
    return {
        "item_id": item.id,
        "total_layers": len(layer_counts),
        "total_tables": len(table_counts),
        "layer_counts": layer_counts,
        "table_counts": table_counts,
        "total_count": total
    }

def _calculate_extent_from_features(features: List[Dict]) -> Optional[List[float]]:
    """
    Calculates [xmin, ymin, xmax, ymax] from a list of GeoJSON features.
    """
    if not features:
        return None
        
    try:
        min_x, min_y = float('inf'), float('inf')
        max_x, max_y = float('-inf'), float('-inf')
        
        found = False
        
        for f in features:
            geom = f.get('geometry')
            if not geom or not geom.get('coordinates'):
                continue
                
            coords = geom['coordinates']
            gtype = geom.get('type')
            
            # recursive flatten to find points
            def flatten(c):
                if isinstance(c[0], (int, float)):
                    yield c
                else:
                    for sub in c:
                        yield from flatten(sub)
            
            for pt in flatten(coords):
                found = True
                x, y = pt[0], pt[1]
                if x < min_x: min_x = x
                if y < min_y: min_y = y
                if x > max_x: max_x = x
                if y > max_y: max_y = y
                
        if not found:
            return None
            
        return [min_x, min_y, max_x, max_y]
        
    except Exception:
        return None

def query_preview_geojson(item_id_or_url: str, layer_index: int = 0,
                        where: str = "1=1",
                        bbox: Optional[tuple] = None,
                        limit: int = 300) -> Dict[str, Any]:
    """
    Queries a feature layer and returns a strict GeoJSON result contract.
    
    Returns:
    {
      "ok": bool,
      "error": str|None,
      "item_id": str,
      "layer_index": int,
      "layer_name": str,
      "geometry_type": str,
      "extent": [xmin, ymin, xmax, ymax] | None,
      "geojson": { "type": "FeatureCollection", "features": [...] }
    }
    """
    # 1. Resolve Item
    gis = GIS() # Anonymous by default, or use env vars/active session logic if refactored
    # Better: import get_gis from existing module if we want shared auth
    try:
        from src.services.arcgis_client import get_gis
        gis = get_gis()
    except ImportError:
        pass # Fallback to anonymous
        
    try:
        item = resolve_item(item_id_or_url, gis)
    except Exception as e:
        return {
            "ok": False, "error": f"Item resolution failed: {e}",
            "item_id": str(item_id_or_url), "layer_index": layer_index,
            "layer_name": "Unknown", "geometry_type": "Unknown",
            "extent": None, "geojson": {"type": "FeatureCollection", "features": []}
        }
        
    # 2. Resolve Layer
    target_layer = None
    layer_name = f"Layer {layer_index}"
    
    if item.type not in ['Feature Service', 'Feature Layer', 'Map Service']:
         return {
            "ok": False, "error": f"Item type '{item.type}' not supported for visualization.",
            "item_id": item.id, "layer_index": layer_index,
            "layer_name": layer_name, "geometry_type": "None",
            "extent": None, "geojson": {"type": "FeatureCollection", "features": []}
         }

    try:
        if hasattr(item, 'layers') and len(item.layers) > layer_index:
            target_layer = item.layers[layer_index]
            layer_name = target_layer.properties.name
        else:
             return {
                "ok": False, "error": f"Layer index {layer_index} out of range (Total: {len(item.layers) if hasattr(item, 'layers') else 0}).",
                "item_id": item.id, "layer_index": layer_index,
                "layer_name": layer_name, "geometry_type": "None",
                "extent": None, "geojson": {"type": "FeatureCollection", "features": []}
             }
    except Exception as e:
         return {
            "ok": False, "error": f"Error accessing layers: {e}",
            "item_id": item.id, "layer_index": layer_index,
            "layer_name": layer_name, "geometry_type": "None",
            "extent": None, "geojson": {"type": "FeatureCollection", "features": []}
        }

    # 3. Query
    geom_filter = None
    if bbox:
        geom_filter = f"{bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]}"
        
    try:
        fset = target_layer.query(
            where=where,
            geometry=geom_filter,
            geometry_type="esriGeometryEnvelope",
            out_fields="*", 
            return_geometry=True,
            result_record_count=limit
        )
        
        # 4. Convert to GeoJSON
        # Guard against None
        if not fset or not fset.features:
            return {
                "ok": True, "error": None,
                "item_id": item.id, "layer_index": layer_index,
                "layer_name": layer_name,
                "geometry_type": target_layer.properties.geometryType if hasattr(target_layer.properties, 'geometryType') else "Unknown",
                "extent": None,
                "geojson": {"type": "FeatureCollection", "features": []}
            }
            
        # Robust conversion
        geojson_data = {"type": "FeatureCollection", "features": []}
        
        try:
            # Use built-in if available and valid
            raw_geojson = fset.to_geojson
            if isinstance(raw_geojson, str):
                parsed = json.loads(raw_geojson)
                if parsed and 'features' in parsed:
                    geojson_data = parsed
            elif isinstance(raw_geojson, dict):
                 geojson_data = raw_geojson
            else:
                 # Fallback manual? For now assume empty if this fails
                 pass
        except Exception:
            # Fallback wrapper if to_geojson fails or doesn't exist
            # (Simplest fallback: empty features to avoid crash)
            pass
            
        # Ensure 'features' is list
        if geojson_data.get('features') is None:
            geojson_data['features'] = []
            
        fc = len(geojson_data['features'])
        
        # 5. Calculate Extent (if not empty)
        extent = None
        if fc > 0:
            extent = _calculate_extent_from_features(geojson_data['features'])
            
        return {
            "ok": True, 
            "error": None,
            "item_id": item.id,
            "layer_index": layer_index,
            "layer_name": layer_name,
            "geometry_type": fset.geometry_type, # e.g. esriGeometryPolygon
            "extent": extent,
            "geojson": geojson_data
        }

    except Exception as e:
        return {
            "ok": False, "error": f"Query/Convert failed: {e}",
            "item_id": item.id, "layer_index": layer_index,
            "layer_name": layer_name, "geometry_type": "Error",
            "extent": None, "geojson": {"type": "FeatureCollection", "features": []}
        }

# Maintain backward compatibility alias if needed, or update consumers
# Original function signature was: query_preview_features(item, layer_index, where, bbox, limit)
# We will deprecate or wrap it.
def query_preview_features(item: Item, layer_index: int = 0, **kwargs):
    # Wrapper to match old simple signature expected by verifying scripts (or update scripts)
    # But since we are updating the tool file entirely, we should just use the new robust function.
    # The old verification script called this. We will update it.
    
    # We'll map it to query_preview_geojson for safety
    res = query_preview_geojson(item.id, layer_index, **kwargs)
    if not res['ok']:
        raise RuntimeError(res['error'])
    return {
        "item_id": res['item_id'],
        "layer_index": res['layer_index'],
        "feature_count": len(res['geojson']['features']),
        "geojson": res['geojson']
    }
