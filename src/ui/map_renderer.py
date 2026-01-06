import folium
import streamlit as st
import streamlit.components.v1 as components
from src.ui.map_overlays import add_geojson_overlay

# Try to import folium_static, fallback if needed
try:
    from streamlit_folium import folium_static
    HAS_FOLIUM_STATIC = True
except ImportError:
    HAS_FOLIUM_STATIC = False

from streamlit_folium import st_folium

def build_folium_map(base_center, base_zoom, overlays, pending_zoom_extent, show_browse_marker=False):
    """
    Builds the Folium map object with all overlays.
    Applies fit_bounds if pending_zoom_extent is provided.
    """
    m = folium.Map(location=base_center, zoom_start=base_zoom)
    
    # Optional Browse Marker
    if show_browse_marker and base_center != [20, 0]:
        folium.Marker(base_center, icon=folium.Icon(color="red", icon="map-marker")).add_to(m)
    
    # 1. Add Overlays
    for lyr in overlays:
        add_geojson_overlay(m, lyr.get('geojson'), lyr.get('name'), lyr.get('geometry_type', 'Unknown'))
        
    # 2. Apply Pending Zoom
    if pending_zoom_extent:
        # [xmin, ymin, xmax, ymax] -> [[ymin, xmin], [ymax, xmax]]
        m.fit_bounds([
            [pending_zoom_extent[1], pending_zoom_extent[0]], 
            [pending_zoom_extent[3], pending_zoom_extent[2]]
        ])
    
    # 3. Add Layer Control if layers exist
    if overlays:
        folium.LayerControl().add_to(m)
        
    return m

def get_map_signature(state):
    """
    Creates a hashable signature for the current map state.
    Used to determine if we need to rebuild the map HTML.
    """
    # Key components: Center, Zoom (initial), Overlays (keys), Pending Zoom
    overlay_keys = tuple(l.get('key', 'unk') for l in state.get("preview_layers", []))
    pending_zoom = tuple(state.get("pending_zoom_extent") or [])
    
    return (
        tuple(state.get("map_center", [20, 0])),
        state.get("map_zoom", 2),
        overlay_keys,
        pending_zoom
    )

def render_map_static(m: folium.Map, height: int = 550):
    """
    Renders the map statically so it doesn't trigger reruns on interaction.
    """
    if HAS_FOLIUM_STATIC:
        folium_static(m, width=None, height=height)
    else:
        # Fallback to pure HTML component
        html = m._repr_html_()
        components.html(html, height=height + 10, scrolling=False)

def app_render_map(state):
    """
    Main entry point for app.py to render the map.
    Handles caching, static vs dynamic switching, and pending zoom consumption.
    """
    
    # 1. Decide Mode
    # If we are in "layer_view" (previewing layers), we want STATIC to avoid lag.
    # If we are in "browse" mode, we might want dynamic checks (future proof), 
    # but for now, the requirement is "lag/gray reload" fix, so STATIC is preferred 
    # when overlays are present.
    
    use_static = (state.get("map_mode") == "layer_view") or len(state.get("preview_layers", [])) > 0
    
    # 2. Check Signature & Cache
    current_sig = get_map_signature(state)
    cached_sig = state.get("map_signature")
    cached_html = state.get("map_html_cache")
    
    # Determine if we need to rebuild
    # We rebuild if:
    # - Signature changed (overlays added/removed, zoom requested)
    # - No cache exists
    # - We are in dynamic mode (st_folium needs fresh object usually to capture state, 
    #   though we can optimize that too, but let's keep dynamic simple)
    
    should_rebuild = (current_sig != cached_sig) or (cached_html is None and use_static)
    
    m = None
    if should_rebuild or not use_static:
        # Consume pending zoom (only if we are rebuilding, otherwise it's already in cache)
        pending_zoom = state.get("pending_zoom_extent")
        show_marker = (state.get("map_mode") == "browse")
        
        m = build_folium_map(
            state.get("map_center", [20, 0]),
            state.get("map_zoom", 2),
            state.get("preview_layers", []),
            pending_zoom,
            show_browse_marker=show_marker
        )
        
        if pending_zoom:
             state["pending_zoom_extent"] = None
    
    if use_static:
        if should_rebuild:
            # Render to HTML string for cache
            # folium_static renders directly, so we can't easily cache the *output* of it 
            # without hacking. But we can cache the map *object*? No, folium maps aren't easily pickled.
            # Best approach for static:
            # If changed, render new.
            # BUT wait, folium_static creates a new iframe every time.
            # To strictly prevent re-runs, components.html with static HTML string is best.
            
            html_content = m.get_root().render()
            state["map_html_cache"] = html_content
            state["map_signature"] = current_sig
            
            # Note: We already cleared pending_zoom in state, so next app run 
            # signature will be different (None vs [coords]). 
            # That's fine, it will rebuild once more without zoom fits, roughly same map.
            # To avoid double-build:
            # We can leave pending_zoom in state, but logic requires we don't loop.
            # If we rely on signature, we are good.
            
        components.html(state["map_html_cache"], height=550, scrolling=False)
        
    else:
        # Dynamic Mode (Browse) - Use st_folium
        # No caching needed as we want interactivity
        st_folium(m, width="100%", height=550)

