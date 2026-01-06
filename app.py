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
from src.tools.feature_layer_tools import resolve_item, get_row_counts, query_preview_geojson
from src.ui.map_state import init_map_state, enter_layer_view, exit_layer_view, add_preview_layer, remove_preview_layer, set_pending_zoom, clear_preview_layers
from src.ui.map_renderer import app_render_map

# Load environment variables
load_dotenv()

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
        add_preview_layer(st.session_state, {
            "item_id": item_id,
            "layer_index": layer_idx,
            "name": res['layer_name'],
            "geometry_type": res['geometry_type'],
            "geojson": res['geojson'],
            "extent": res.get('extent')
        })
        st.toast(f"✅ Loaded: {res['layer_name']}")
    else:
        st.error(f"Visualization Failed: {res.get('error')}")

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
        preview_limit = st.slider("Max Preview Size", 50, 1000, 300)
        # REMOVED Layer Index Input as requested
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
            
            if not st.session_state.messages:
                st.caption("Try: 'count rows for <url>' or 'visualize wildfire data'")
                
            for msg in st.session_state.messages:
                with st.chat_message(msg["role"]): st.markdown(msg["content"])

    if prompt := st.chat_input("Ask..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # Simple Intent Logic
        p_low = prompt.lower()
        is_viz = any(x in p_low for x in ["visualize", "preview", "map this"])
        is_cnt = any(x in p_low for x in ["count rows", "how many rows"])
        tid = get_item_id_from_text(prompt) or st.session_state.selected_item_id
        
        with col_chat:
            with st.status("Thinking...", expanded=True) as box:
                if is_viz or is_cnt:
                    if not tid:
                        box.write("⚠️ Select an item first.")
                        response_text = "Please select an item from the results."
                        box.update(state="error")
                    else:
                        try:
                            gis = get_gis()
                            item = resolve_item(tid, gis)
                            if is_cnt:
                                box.write("🔢 Counting...")
                                c = get_row_counts(item)
                                if c['total_count'] >= 0:
                                    response_text = f"**{item.title}**: {c['total_count']} rows across {c['total_layers']} layers."
                                else: response_text = "Error counting."
                            if is_viz:
                                box.write("🗺️ Loading preview...")
                                handle_visualize(tid, layer_idx_sel, preview_limit)
                                response_text = f"Added **{item.title}** to map."
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
                for item in st.session_state.results:
                    score = item['quality_score']
                    bclass = "score-badge-high" if score > 70 else "score-badge-med"
                    is_sel = st.session_state.selected_item_id == item['id']
                    
                    with st.container(border=True):
                        if is_sel: st.info(f"Selected: {item['title']}")
                        else: st.markdown(f"**[{item['title']}]({item['url']})**")
                        
                        st.caption(f"{item['type']} • {item['owner']}")
                        c1, c2 = st.columns([1,3])
                        c1.markdown(f"<span class='{bclass}'>{score}</span>", unsafe_allow_html=True)
                        c2.progress(score/100)
                        
                        # Buttons
                        b1, b2 = st.columns(2)
                        with b1:
                            if st.button("Use Item", key=f"sel_{item['id']}"):
                                st.session_state.selected_item_id = item['id']
                                st.rerun()
                        with b2:
                            # Visualize Button
                            if item['type'] in ['Feature Service', 'Feature Layer', 'Map Service']:
                                if st.button("👁️ Visualize", key=f"viz_{item['id']}"):
                                    st.session_state.selected_item_id = item['id']
                                    handle_visualize(item['id'], layer_idx_sel, preview_limit)
                                    st.rerun()
                        
                        with st.expander("Details"):
                            st.write(clean_html_to_text(item.get('snippet')))
                            st.text_input("ID", value=item['id'], key=f"id_{item['id']}", disabled=True)
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
elif page == "Catalog Health":
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
