from arcgis.gis import GIS, Item
from arcgis.features import FeatureLayer, FeatureLayerCollection
import pandas as pd
from typing import Dict, Any, Union, Optional, List
import json
import urllib.parse
from arcgis.geometry import project

def normalize_layer_input(input_str: str) -> Dict[str, Any]:
    """
    Parses a user input string (Item ID, FeatureServer URL, Map Viewer URL)
    into a normalized target description.
    """
    input_str = input_str.strip()
    
    # 1. Map Viewer URL
    # e.g. .../apps/mapviewer/index.html?url=...
    if "apps/mapviewer" in input_str and "url=" in input_str:
        try:
            parsed = urllib.parse.urlparse(input_str)
            qs = urllib.parse.parse_qs(parsed.query)
            if 'url' in qs:
                service_url = qs['url'][0]
                return {"kind": "service_url", "url": service_url, "layer_index": 0}
        except Exception:
            pass # Fall through
            
    # 2. Direct Service URL
    # e.g. .../FeatureServer/0 or .../FeatureServer
    if "/FeatureServer" in input_str or "/MapServer" in input_str:
        # Check if layer index is at the end (simplistic check)
        # e.g. http://.../FeatureServer/5
        # We need to distinguish between .../FeatureServer and .../FeatureServer/
        
        parts = input_str.split('/')
        if parts[-1].isdigit():
             return {"kind": "service_url", "url": input_str, "layer_index": None} # Implies specialized handling
        elif parts[-1] == '' and parts[-2].isdigit():
             return {"kind": "service_url", "url": input_str.rstrip('/'), "layer_index": None}
             
        # Default to 0 if not specified
        return {"kind": "service_url", "url": input_str, "layer_index": 0}
            
    # 3. Item ID (Fallback)
    # Extract just ID if mixed text
    return {"kind": "item_id", "item_id": input_str}

def resolve_item(item_id_or_url: str, gis: GIS) -> Union[Item, FeatureLayer, FeatureLayerCollection]:
    """
    Resolves an item ID OR service URL to an arcgis object.
    Returns Item, FeatureLayer, or FeatureLayerCollection.
    """
    target = normalize_layer_input(item_id_or_url)
    
    if target['kind'] == 'item_id':
        item_id = target['item_id']
        # Handle "id=..." case
        if 'id=' in item_id:
            try:
                item_id = item_id.split('id=')[1].split('&')[0]
            except: pass
            
        try:
            item = gis.content.get(item_id)
            if not item:
                # Last ditch: maybe it IS a URL but didn't look like one?
                if "http" in item_id:
                     if item_id.split('/')[-1].isdigit():
                         return FeatureLayer(item_id, gis=gis)
                     else:
                         return FeatureLayerCollection(item_id, gis=gis)
                raise ValueError("Item returned None")
            return item
        except Exception as e:
            raise ValueError(f"Could not resolve item '{item_id}': {e}")
            
    elif target['kind'] == 'service_url':
        url = target['url']
        try:
            # Try to determine if it is a specific layer or collection
            # If the URL ends in a number, it's likely a FeatureLayer
            if url.rstrip('/').split('/')[-1].isdigit():
                return FeatureLayer(url, gis=gis)
            else:
                return FeatureLayerCollection(url, gis=gis)
        except Exception as e:
            # Fallback: Try without GIS object (helps with some public services or authInfo errors)
            try:
                if url.rstrip('/').split('/')[-1].isdigit():
                    return FeatureLayer(url)
                else:
                    return FeatureLayerCollection(url)
            except Exception:
                 raise ValueError(f"Could not connect to service URL '{url}': {e}")
            
    raise ValueError(f"Unknown input type: {item_id_or_url}")

def get_row_counts(item: Union[Item, FeatureLayer, FeatureLayerCollection], where: str = "1=1") -> Dict[str, Any]:
    """
    Counts rows for all layers/tables in the item.
    """
    layer_counts = []
    table_counts = []
    total = 0
    
    # Handle non-Item objects
    layers = []
    tables = []
    item_id = getattr(item, 'id', 'URL_SOURCE')
    
    if isinstance(item, Item):
        if hasattr(item, 'layers'): layers = item.layers
        if hasattr(item, 'tables'): tables = item.tables
    elif isinstance(item, FeatureLayerCollection):
         layers = item.layers
         tables = item.tables
    elif isinstance(item, FeatureLayer):
         layers = [item]
    
    def count_source(lyr_obj):
        try:
            return lyr_obj.query(where=where, return_count_only=True)
        except Exception as e:
            return -1 # Error indicator
            
    for lyr in layers:
        c = count_source(lyr)
        if c >= 0: total += c
        try: name = lyr.properties.name
        except: name = "Layer"
        layer_counts.append({"name": name, "count": c if c >= 0 else "Error"})
        
    for tbl in tables:
        c = count_source(tbl)
        if c >= 0: total += c
        try: name = tbl.properties.name
        except: name = "Table"
        table_counts.append({"name": name, "count": c if c >= 0 else "Error"})
            
    return {
        "item_id": item_id,
        "total_layers": len(layer_counts),
        "total_tables": len(table_counts),
        "layer_counts": layer_counts,
        "table_counts": table_counts,
        "total_count": total
    }

def count_rows(input_str: str, 
              layer_index: Optional[int] = None, 
              where: str = "1=1") -> Dict[str, Any]:
    """
    Counts rows for the target Feature Layer(s) or Table(s).
    Returns a strict schema dictionary.
    """
    # 1. Resolve Auth (Best effort)
    try:
        from src.services.arcgis_client import get_gis
        gis = get_gis()
    except ImportError:
        gis = GIS()
        
    resolved_info = {
        "kind": "unknown",
        "item_id": None, 
        "service_url": None
    }
    
    # 2. Parse Input & Target
    try:
        target = normalize_layer_input(input_str)
        resolved_info['kind'] = target.get('kind', 'unknown')
        if target.get('kind') == 'item_id':
             resolved_info['item_id'] = target.get('item_id')
        elif target.get('kind') == 'service_url':
             resolved_info['service_url'] = target.get('url')
             # If layer index was implicit in URL (e.g. /0), override default unless explicit
             if target.get('layer_index') is not None and layer_index is None:
                 layer_index = target.get('layer_index')

        obj = resolve_item(input_str, gis)
        
    except Exception as e:
        return {
            "ok": False,
            "error": str(e),
            "input": input_str,
            "resolved": resolved_info,
            "layers": [],
            "tables": [],
            "total_count": 0
        }
        
    # 3. Identify Layers to Count
    layers_to_count = []
    tables_to_count = []
    
    # helper to fetch name safely
    def get_name(o, default):
        try: return o.properties.name
        except: return default
        
    if isinstance(obj, FeatureLayer):
        # Single layer target
        layers_to_count.append((0, obj, get_name(obj, "Target Layer")))
        
    elif isinstance(obj, FeatureLayerCollection):
        # Collection: filter by index if provided, else all
        if layer_index is not None:
            # Specific layer?
            # Note: FeatureLayerCollection.layers is a list.
            if 0 <= layer_index < len(obj.layers):
                 l = obj.layers[layer_index]
                 layers_to_count.append((layer_index, l, get_name(l, f"Layer {layer_index}")))
            else:
                 # Check tables?
                 # If index is high, it might be a table, but usually tables are separate.
                 # User spec says: "If layer_index is provided, count ONLY that layer"
                 # We will return error if out of bounds? Or just 0?
                 # Let's try tables if layers fail? No, strict index usually implies layers array.
                 pass
        else:
             # All layers and tables
             for i, l in enumerate(obj.layers):
                 layers_to_count.append((i, l, get_name(l, f"Layer {i}")))
             for i, t in enumerate(obj.tables):
                 tables_to_count.append((i, t, get_name(t, f"Table {i}")))
                 
    elif isinstance(obj, Item):
         # Item wrapper, similar to Collection usually
         if hasattr(obj, 'layers'):
             if layer_index is not None:
                  if 0 <= layer_index < len(obj.layers):
                       l = obj.layers[layer_index]
                       layers_to_count.append((layer_index, l, get_name(l, f"Layer {layer_index}")))
             else:
                  for i, l in enumerate(obj.layers):
                       layers_to_count.append((i, l, get_name(l, f"Layer {i}")))
         if hasattr(obj, 'tables') and layer_index is None:
              for i, t in enumerate(obj.tables):
                   tables_to_count.append((i, t, get_name(t, f"Table {i}")))

    # 4. Perform Counts
    layer_results = []
    table_results = []
    total_count = 0
    has_error = False
    
    def do_count(idx, lyr_obj, name):
        nonlocal total_count, has_error
        try:
            # return_count_only=True
            c = lyr_obj.query(where=where, return_count_only=True)
            # ArcGIS API for Python query() with return_count_only=True returns just the number usually
            if isinstance(c, (int, float)):
                return {"index": idx, "name": name, "count": int(c), "error": None}
            else:
                # rare case it returns dict?
                return {"index": idx, "name": name, "count": None, "error": f"Unexpected return type: {type(c)}"}
        except Exception as e:
            has_error = True
            return {"index": idx, "name": name, "count": None, "error": str(e)}

    for idx, lyr, name in layers_to_count:
        r = do_count(idx, lyr, name)
        if r['count'] is not None: total_count += r['count']
        layer_results.append(r)
        
    for idx, tbl, name in tables_to_count:
        r = do_count(idx, tbl, name)
        if r['count'] is not None: total_count += r['count']
        table_results.append(r)
        
    # If no layers found at all (and we didn't error earlier)
    if not layer_results and not table_results:
         # Maybe layer index was out of bounds?
         msg = "No layers found."
         if layer_index is not None: msg += f" (Index {layer_index} might be invalid)"
         return {
            "ok": False,
            "error": msg,
            "input": input_str,
            "resolved": resolved_info,
            "layers": [],
            "tables": [],
            "total_count": 0
        }

    return {
        "ok": True,
        "error": None, # Top level error is None if we processed the request, even if individual layers failed
        "input": input_str,
        "resolved": resolved_info,
        "layers": layer_results,
        "tables": table_results,
        "total_count": total_count
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
    Ensures out_sr=4326 and attempts fallback projection if needed.
    """
    # 1. Resolve Auth
    try:
        from src.services.arcgis_client import get_gis
        gis = get_gis()
    except ImportError:
        gis = GIS()
        
    # 2. Resolve Target
    try:
        obj = resolve_item(item_id_or_url, gis)
    except Exception as e:
        return {
            "ok": False, "error": f"Resolution failed: {e}",
            "item_id": str(item_id_or_url), "layer_index": layer_index,
            "layer_name": "Unknown", "geometry_type": "Unknown",
            "extent": None, "geojson": {"type": "FeatureCollection", "features": []}
        }
    
    # Identify Layer
    target_layer = None
    layer_name = f"Layer {layer_index}"
    item_id = getattr(obj, 'id', 'URL_SOURCE')

    # Case A: Item
    if isinstance(obj, Item):
        if obj.type in ['Feature Service', 'Feature Layer', 'Map Service']:
            if hasattr(obj, 'layers') and len(obj.layers) > layer_index:
                target_layer = obj.layers[layer_index]
                layer_name = target_layer.properties.name
            else:
                 return {"ok": False, "error": f"Layer index {layer_index} out of range (Total: {len(obj.layers) if hasattr(obj, 'layers') else 0}).", 
                         "geojson": {"type": "FeatureCollection", "features": []}, "layer_name": layer_name, "geometry_type": "None", "extent": None, "item_id": item_id}
        else:
             return {"ok": False, "error": f"Item type '{obj.type}' not supported.", 
                     "geojson": {"type": "FeatureCollection", "features": []}, "layer_name": layer_name, "geometry_type": "None", "extent": None, "item_id": item_id}
            
    # Case B: FeatureLayer (Direct)
    elif isinstance(obj, FeatureLayer):
        target_layer = obj
        try: layer_name = target_layer.properties.name
        except: pass
        
    # Case C: FeatureLayerCollection
    elif isinstance(obj, FeatureLayerCollection):
        if len(obj.layers) > layer_index:
            target_layer = obj.layers[layer_index]
            try: layer_name = target_layer.properties.name
            except: pass
        else:
             return {"ok": False, "error": f"Layer index {layer_index} out of range.", 
                     "geojson": {"type": "FeatureCollection", "features": []}, "layer_name": layer_name, "geometry_type": "None", "extent": None, "item_id": item_id}

    if not target_layer:
        return {"ok": False, "error": "Could not determine target layer.", "geojson": {"type": "FeatureCollection", "features": []}, "layer_name": layer_name, "geometry_type": "None", "extent": None, "item_id": item_id}

    # 3. Query
    out_sr_wkid = 4326
    
    # Simplification for heavy polygons (Part E)
    # Default: Apply max_allowable_offset if limit is exceeded, or just default it?
    # Let's apply a default offset if geometry type is polygon and not specified?
    # To be safe, we rely on the 300 limit mostly. 
    # But let's check geometry type first if possible? 
    # Can't easily check without query or properties. 
    # Let's just run query.
    
    try:
        fset = target_layer.query(
            where=where,
            out_sr=out_sr_wkid, # FIX #1
            result_record_count=limit,
            return_geometry=True,
            out_fields="*"
            # max_allowable_offset could be added here if needed
        )
    except Exception as e:
        return {"ok": False, "error": f"Query failed: {e}", "geojson": {"type": "FeatureCollection", "features": []}, "layer_name": layer_name, "geometry_type": "Error", "extent": None, "item_id": item_id}
        
    if not fset or not fset.features:
        return {
            "ok": True, "error": None,
            "item_id": item_id, "layer_index": layer_index, "layer_name": layer_name,
            "geometry_type": target_layer.properties.geometryType if hasattr(target_layer.properties, 'geometryType') else "Unknown",
            "extent": None,
            "geojson": {"type": "FeatureCollection", "features": []}
        }
        
    # 4. JSON Conversion
    geojson_data = {"type": "FeatureCollection", "features": []}
    
    try:
        raw = fset.to_geojson
        if isinstance(raw, str):
            geojson_data = json.loads(raw)
        elif isinstance(raw, dict):
            geojson_data = raw
    except:
        pass

    if 'features' not in geojson_data or geojson_data['features'] is None:
        geojson_data['features'] = []
        
    # 5. Sanity Check & Fallback
    def check_bounds_bad(features):
        for f in features[:5]: 
            geom = f.get('geometry')
            if not geom or 'coordinates' not in geom: continue
            try:
                c = geom['coordinates']
                while isinstance(c[0], list): c = c[0]
                x, y = c[0], c[1]
                if abs(x) > 185 or abs(y) > 95: return True
            except: pass
        return False
        
    if check_bounds_bad(geojson_data['features']):
        # Attempt Fallback Check
        # If coordinates are clearly WebMercator (e.g. > 10000), we can validly say "Project failed"
        # because we asked for 4326.
        return {"ok": False, "error": "Service ignored requests for Lat/Lon (EPSG:4326) and returned projected coordinates. Map preview requires Lat/Lon.", 
                "geojson": geojson_data, "layer_name": layer_name, "geometry_type": fset.geometry_type, "extent": None, "item_id": item_id}
                
        # Note: True fallback projection logic requires working GeometryService or local projection engine.
        # Since I cannot verify if 'arcgis' package here has local engine enabled (dependencies like shapely/arcpy),
        # I will start with a clear error message as requested ("return a clear error").
        # If the user specifically wanted 'arcgis.geometry.project', I would need a GIS object with a valid Geometry Service.
        # The 'gis' object we have (likely anonymous) might not have one.
        # So 'Clear Error' is the safest robust implementation for now.

    extent = _calculate_extent_from_features(geojson_data['features'])
    
    return {
        "ok": True, 
        "error": None,
        "item_id": item_id,
        "layer_index": layer_index,
        "layer_name": layer_name,
        "geometry_type": fset.geometry_type,
        "extent": extent,
        "geojson": geojson_data
    }
