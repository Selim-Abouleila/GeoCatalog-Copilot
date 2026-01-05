import folium
import streamlit as st

def add_geojson_overlay(m: folium.Map, geojson_data: dict, layer_name: str, geometry_type: str = "Unknown"):
    """
    Adds a persistent GeoJSON overlay to the map using FeatureGroup.
    """
    if not geojson_data or not geojson_data.get('features'):
        return

    # Dynamic Style Function
    def style_fn(feature):
        gtype = feature['geometry']['type'] if feature.get('geometry') else geometry_type
        
        # Polygons
        if 'Polygon' in gtype:
            return {
                'fillColor': '#3388ff',
                'color': '#3388ff',
                'weight': 1,
                'fillOpacity': 0.4
            }
        # Lines
        elif 'Line' in gtype:
            return {
                'color': '#ff7800',
                'weight': 3,
                'opacity': 0.8
            }
        # Points (default)
        return {
            'radius': 6,
            'fillColor': '#ff0000',
            'color': '#000',
            'weight': 1,
            'fillOpacity': 0.8
        }

    # Tooltip fields (try to guess useful ones)
    fields = []
    aliases = []
    
    if geojson_data['features']:
        props = geojson_data['features'][0].get('properties', {})
        # Pick first 3 keys that aren't too long
        candidates = [k for k in props.keys() if k.upper() not in ['SHAPE', 'SHAPE_AREA', 'SHAPE_LENGTH']]
        fields = candidates[:3]
        aliases = fields

    # Feature Group allows toggling
    fg = folium.FeatureGroup(name=layer_name, show=True)
    
    folium.GeoJson(
        geojson_data,
        name=layer_name, # Inner name
        style_function=style_fn,
        tooltip=folium.GeoJsonTooltip(fields=fields, aliases=aliases) if fields else None
    ).add_to(fg)
    
    fg.add_to(m)
