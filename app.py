import streamlit as st
import folium
from streamlit_folium import st_folium
import os
import pandas as pd
from dotenv import load_dotenv
import re
import json

from src.tools.content_search import search_items
from src.tools.geocode import geocode_place
from src.tools.scoring import quality_score
from src.ui.styles import apply_custom_css
from src.utils.text import clean_html_to_text

# New Integrations
from src.services.catalog_store import get_status, admin_queries
from src.services.report_store import list_reports, read_text, list_report_csvs
from scripts.generate_catalog_report import generate_catalog_report
from src.services.arcgis_client import get_gis

# Feature Layer Tools integration
from src.tools.feature_layer_tools import resolve_item, count_rows, query_preview_geojson, get_row_counts # Keeping get_row_counts import if needed elsewhere, but we will replace usages
from src.tools.renderer_tools import fetch_layer_renderer
from src.ui.map_state import init_map_state, enter_layer_view, exit_layer_view, add_preview_layer, remove_preview_layer, set_pending_zoom, clear_preview_layers
from src.ui.map_renderer import app_render_map
from src.ui.preview_refresh import refresh_preview_layers
from src.ui.results_cards import render_result_card

# Load environment variables
load_dotenv()

# --- Caching ---
@st.cache_data(ttl=600)
def cached_count_rows(item_id):
    return count_rows(item_id)

# --- Page Config ---
st.set_page_config(
    page_title="GeoCatalog Copilot",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Apply Custom CSS
apply_custom_css()

# --- Session State Initialization ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "results" not in st.session_state:
    st.session_state.results = []
if "selected_item_id" not in st.session_state:
    st.session_state.selected_item_id = None
if "first_load" not in st.session_state:
    st.session_state.first_load = True
if "preview_limit_applied" not in st.session_state:
    st.session_state.preview_limit_applied = 300
if "preview_layers_version" not in st.session_state:
    st.session_state.preview_layers_version = 0

# Initialize Map State (using helper)
init_map_state(st.session_state)

# --- Helper Logic ---

def get_item_id_from_text(text):
    # 1. Check for Map Viewer URL
    if "apps/mapviewer" in text and "url=" in text:
        return text.strip()
    
    # 2. Check for FeatureServer/MapServer URL
    if "/FeatureServer" in text or "/MapServer" in text:
        match = re.search(r'(https?://\S+/(?:FeatureServer|MapServer)(?:/\d+)?)', text)
        if match: return match.group(1)
        # If regex fails but keyword exists, might be simple string
        return text.strip()

    # 3. Item ID
    match = re.search(r'\b[0-9a-f]{32}\b', text)
    if match: return match.group(0)
    match_url = re.search(r'id=([0-9a-f]{32})', text)
    if match_url: return match_url.group(1)
    return None

def handle_visualize(item_id, layer_idx, limit):
    with st.spinner(f"Loading preview for `{item_id}`..."):
        res = query_preview_geojson(item_id, layer_index=layer_idx, limit=limit)
        
    if res['ok']:
        # Fetch Renderer (Symbology)
        renderer = fetch_layer_renderer(item_id, layer_index=layer_idx)
        
        add_preview_layer(st.session_state, {
            "item_id": item_id,
            "layer_index": layer_idx,
            "name": res['layer_name'],
            "geometry_type": res['geometry_type'],
            "geojson": res['geojson'],
            "extent": res.get('extent'),
            "renderer": renderer
        })
        st.toast(f"✅ Loaded: {res['layer_name']}")
    else:
        st.error(f"Visualization Failed: {res.get('error')}")

def handle_count_rows(item_id):
    # Store result in session state to display in assistant or toast
    key = f"count_res_{item_id}"
    with st.spinner("Counting rows..."):
        res = cached_count_rows(item_id)
        
    if res['ok']:
        msg = f"**Total Records**: {res['total_count']}\n\n"
        if res['layers']:
            msg += "| Layer | Count |\n|---|---|\n"
            for l in res['layers']:
                msg += f"| {l['name']} | {l['count']} |\n"
        st.session_state.messages.append({
            "role": "assistant", 
            "content": f"📊 **Count Results for {item_id}**\n\n{msg}"
        })
        st.toast(f"Count Complete: {res['total_count']} records")
    else:
        st.error(f"Count Failed: {res.get('error')}")

# --- Sidebar Navigation & Status ---
with st.sidebar:
    st.markdown("### GeoCatalog Copilot")
    page = st.radio("Navigation", ["Copilot", "Catalog Health", "Reports"], label_visibility="collapsed")
    st.divider()

    if page == "Copilot":
        
        # --- Map Controls (Context Sensitive) ---
        if st.session_state.map_mode == "layer_view":
            st.markdown("#### 🗺️ Layer View")
            if st.button("⬅️ Exit Layer View", use_container_width=True):
                exit_layer_view(st.session_state)
                st.rerun()
            
            st.markdown("active layers:")
            for idx, lyr in enumerate(st.session_state.preview_layers):
                c1, c2, c3 = st.columns([3, 1, 1])
                c1.caption(f"{idx+1}. {lyr['name']}")
                
                # Zoom Button
                if lyr.get('extent'):
                    if c2.button("🔭", key=f"zoom_{lyr.get('key', idx)}", help="Zoom to layer"):
                        set_pending_zoom(st.session_state, lyr['extent'])
                        st.rerun()
                
                # Remove Button
                if c3.button("✖", key=f"rem_{lyr.get('key', idx)}", help="Remove layer"):
                    remove_preview_layer(st.session_state, lyr.get('key'))
                    st.rerun()
            st.divider()

        st.markdown("**Settings**")
        model_name = st.text_input("🧠 Model", value=os.getenv("OLLAMA_MODEL", "llama3.2:1b"), disabled=True)
        max_items = st.slider("Max Results", 1, 25, 5)
        item_type = st.selectbox("Item Type", ["Feature Layer", "Map Image Layer", "Web Map", "Scene Layer", "Image Service"])
        
        st.markdown("**Preview Settings**")
        preview_limit_draft = st.slider("Max Preview Size", 50, 1000, st.session_state.preview_limit_applied)
        
        # Apply Button Logic
        if preview_limit_draft != st.session_state.preview_limit_applied:
            if st.button(f"Apply ({preview_limit_draft})"):
                with st.spinner("Refreshing layers..."):
                    st.session_state.preview_layers = refresh_preview_layers(
                        st.session_state.preview_layers, 
                        preview_limit_draft
                    )
                    st.session_state.preview_limit_applied = preview_limit_draft
                    st.session_state.preview_layers_version += 1
                    st.rerun()
        
        # layer_idx_sel = st.number_input("Layer Index", 0, 100, 0)
        layer_idx_sel = 0 # Forced default
        
        if st.session_state.map_mode == "browse":
            if st.button("Clear Map"):
                clear_preview_layers(st.session_state)
                st.rerun()

        st.markdown("**View**")
        sort_by_quality = st.toggle("Rank by Quality", True)
        debug_mode = st.toggle("Debug", False)
        st.divider()

    st.markdown("##### 📦 Warehouse Status")
    status = get_status()
    if not status['ok']:
        st.error(f"Error: {status.get('error')}")
    else:
        st.caption(f"DB: `{status['db_path']}`")
        if status.get('has_runs'):
            metrics = status['metrics']
            c1, c2 = st.columns(2)
            c1.metric("Items", metrics['items'])
            c2.metric("Scored", metrics['scores'])
            if metrics['broken_services'] > 0: st.error(f"⚠️ {metrics['broken_services']} Broken")
            else: st.success("✅ Healthy")
    if st.button("Refresh"): st.rerun()

# --- Page: Copilot ---
if page == "Copilot":
    col_chat, col_results, col_map = st.columns([1, 1.2, 1.2], gap="medium")
    
    # --- Chat ---
    with col_chat:
        st.markdown("##### 💬 Assistant")
        chat_container = st.container(height=600)
        with chat_container:
            # Removed initial greeting logic
            if not st.session_state.messages and st.session_state.first_load:
                st.session_state.first_load = False
            
            # Removed startup hint
            
            for msg in st.session_state.messages:
                with st.chat_message(msg["role"]): st.markdown(msg["content"])

    if prompt := st.chat_input("Ask..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # Simple Intent Logic
        p_low = prompt.lower()
        is_viz = any(x in p_low for x in ["visualize", "preview", "map this"])
        is_cnt = any(x in p_low for x in ["count rows", "how many rows", "record count", "how many records"])
        tid = get_item_id_from_text(prompt) or st.session_state.selected_item_id
        
        with col_chat:
            with st.status("Thinking...", expanded=True) as box:
                if is_viz or is_cnt:
                    if not tid:
                        box.write("⚠️ Select an item first.")
                        response_text = "Please select an item from the results or paste a standard URL/ID."
                        box.update(state="error")
                    else:
                        try:
                            # We don't need 'gis' or 'resolve_item' here directly anymore, tools handle it
                            # But visualized needs resolve? query_preview_geojson handles it.
                            
                            if is_cnt:
                                box.write("🔢 Counting...")
                                c = cached_count_rows(tid)
                                if c['ok']:
                                    response_text = f"**Total Records**: {c['total_count']}"
                                    if c['layers']:
                                        response_text += "\n\n| Layer | Count |\n|---|---|\n"
                                        for l in c['layers']:
                                            response_text += f"| {l['name']} | {l['count'] if l['count'] is not None else 'Error'} |\n"
                                else: 
                                    response_text = f"Error counting: {c.get('error')}"
                                    
                            if is_viz:
                                box.write("🗺️ Loading preview...")
                                handle_visualize(tid, layer_idx_sel, st.session_state.preview_limit_applied)
                                response_text = f"Added item to map."
                                
                            box.update(state="complete")
                        except Exception as e:
                            response_text = f"Error: {e}"
                            box.update(state="error")
                else:
                    # Default Search
                    box.write("🔍 Searching...")
                    items = search_items(prompt, item_type=item_type, max_items=max_items)
                    scored = []
                    for i in items:
                        i['quality_score'] = quality_score(i)
                        scored.append(i)
                    if sort_by_quality: scored.sort(key=lambda x:x['quality_score'], reverse=True)
                    st.session_state.results = scored
                    response_text = f"Found {len(items)} results."
                    box.update(state="complete")
                    
        st.session_state.messages.append({"role": "assistant", "content": response_text})
        st.rerun()

    # --- Results ---
    with col_results:
        st.markdown(f"##### 📋 Results ({len(st.session_state.results)})")
        with st.container(height=600):
            if st.session_state.results:
                
                # Define callbacks
                def on_viz(tid):
                    # Visualize does NOT set selected_item_id anymore
                    handle_visualize(tid, layer_idx_sel, st.session_state.preview_limit_applied)
                    st.rerun()
                    
                def on_cnt(tid):
                    handle_count_rows(tid)
                    st.rerun()

                for item in st.session_state.results:
                    render_result_card(
                        item, 
                        st.session_state.selected_item_id,
                        st.session_state.preview_limit_applied,
                        on_viz,
                        on_cnt
                    )
            else:
                 st.write("No results.")

    # --- Map ---
    with col_map:
        st.markdown("##### 🗺️ Map")
        with st.container(height=600):
            app_render_map(st.session_state)

    if debug_mode:
        st.divider()
        st.write("Map Mode:", st.session_state.map_mode)
        st.write("Pending Zoom:", st.session_state.get('pending_zoom_extent'))
        st.write("Preview Layers:", len(st.session_state.preview_layers))

# --- Other Pages Unchanged ---
if page == "Catalog Health":
    st.title("📊 Catalog Health")
    if not status['ok']: st.stop()
    run_id = status['latest_run']['run_id']
    data = admin_queries(run_id)
    t1, t2, t3 = st.tabs(["Overview", "Issues", "Owners"])
    with t1: st.metric("Unique Items", status['metrics']['items'])
    with t2:
        for k in ['missing_tags', 'broken_services']:
            df = data.get(k, pd.DataFrame())
            if not df.empty: st.dataframe(df)
    with t3:
        if not data.get('owner_summary', pd.DataFrame()).empty: st.dataframe(data['owner_summary'])

elif page == "Reports":
    st.title("📑 Reports")
    if st.button("Generate"):
        generate_catalog_report()
        st.rerun()
    reports = list_reports()
    if reports:
        sel = st.selectbox("Report", reports, format_func=lambda x:x.name)
        if sel: st.markdown(read_text(sel))
