import streamlit as st
import folium
from streamlit_folium import st_folium
import os
from dotenv import load_dotenv

from src.tools.content_search import search_items
from src.tools.geocode import geocode_place
from src.tools.scoring import quality_score
from src.tools.scoring import quality_score
from src.ui.styles import apply_custom_css
from src.utils.text import clean_html_to_text

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
if "map_center" not in st.session_state:
    st.session_state.map_center = [20, 0] # Default: World view
if "map_zoom" not in st.session_state:
    st.session_state.map_zoom = 2

# --- Sidebar ---
with st.sidebar:
    st.markdown("### GeoCatalog Copilot")
    st.caption("ArcGIS content discovery • metadata QA • local LLM")
    st.divider()
    
    st.markdown("**Settings**")
    model_name = st.text_input(
        "🧠 Model", 
        value=os.getenv("OLLAMA_MODEL", "llama3.2:1b"),
        disabled=True,
        help="Model defined in .env"
    )
    
    max_items = st.slider("Max Results", min_value=1, max_value=25, value=5)
    
    item_type = st.selectbox(
        "Item Type",
        ["Feature Layer", "Map Image Layer", "Web Map", "Scene Layer", "Image Service"]
    )
    
    st.divider()
    st.markdown("**Filters & View**")
    sort_by_quality = st.toggle("Rank by Quality Score", value=True)
    show_extent_only = st.toggle("Show only items with extent", value=False)
    debug_mode = st.toggle("Show debug traces", value=False)

# --- Main Layout ---
# 3 Columns: Chat | Results | Map
col_chat, col_results, col_map = st.columns([1, 1.2, 1.2], gap="medium")

# --- Column 1: Chat Interface ---
with col_chat:
    st.markdown("##### 💬 Assistant")
    
    # Message History Container
    chat_container = st.container(height=600)
    with chat_container:
        if not st.session_state.messages:
            st.info("👋 Hi! Ask me to find map data, e.g., 'wildfire California'.")
            
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

# --- Column 3: Map Panel (Rendered early so accessible) ---
# We generally render columns in order, but Map logic usually just reads state.
# Nothing complex here.

# --- Interaction Logic (Global Input) ---
# Streamlit chat input is fixed at bottom. 
# To handle the logic, we check if input exists.
if prompt := st.chat_input("Ask for geospatial content..."):
    # 1. Add user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Force rerun to show user message immediately (optional, or just continue)
    
    with col_chat: # Show status in chat column
        with st.status("Thinking...", expanded=True) as status:
            
            # 2. Geocoding
            status.write("📍 Geocoding location...")
            try:
                place = geocode_place(prompt)
                if place:
                    st.session_state.map_center = [place['lat'], place['lon']]
                    st.session_state.map_zoom = 8
                    loc_msg = f"Focused map on **{place['name']}**"
                    status.write(f"✅ {loc_msg}")
                else:
                    loc_msg = "Global search (no location found)"
                    status.write("🌍 No specific location found.")
            except Exception as e:
                status.write(f"⚠️ Geocoding error: {e}")
                loc_msg = "Geocoding failed"

            # 3. Search
            status.write("🔍 Searching ArcGIS Online...")
            try:
                items = search_items(prompt, item_type=item_type, max_items=max_items)
                scored_items = []
                for item in items:
                    item['quality_score'] = quality_score(item)
                    scored_items.append(item)
                
                # Sort
                if sort_by_quality:
                    scored_items.sort(key=lambda x: x['quality_score'], reverse=True)
                    
                st.session_state.results = scored_items
                status.write(f"✅ Found {len(items)} items.")
            except Exception as e:
                status.write(f"❌ Search error: {e}")
                st.error(f"Search failed: {e}")
            
            status.update(label="Ready", state="complete", expanded=False)
            
    # 4. Add Assistant Response (Summary)
    response_text = f"I found **{len(st.session_state.results)}** results for '{prompt}'. {loc_msg}"
    st.session_state.messages.append({"role": "assistant", "content": response_text})
    st.rerun()

# --- Column 2: Results List ---
with col_results:
    st.markdown(f"##### 📋 Results ({len(st.session_state.results)})")
    
    results_container = st.container(height=600) # Scrollable container
    with results_container:
        if st.session_state.results:
            for item in st.session_state.results:
                # Determine badge class
                score = item['quality_score']
                badge_class = "score-badge-high" if score > 70 else "score-badge-med"
                
                # Card Container
                with st.container(border=True):
                    # Title & Link
                    st.markdown(f"**[{item['title']}]({item['url']})**")
                    
                    # Metadata Line
                    st.caption(f"{item['type']} • {item['owner']}")
                    
                    # Score Bar
                    col_score_label, col_score_bar = st.columns([1, 3])
                    with col_score_label:
                        st.markdown(f"<span class='{badge_class}'>QS: {score}/100</span>", unsafe_allow_html=True)
                    with col_score_bar:
                        st.progress(score / 100)
                    
                    # Snippet
                    if item.get('snippet'):
                        st.markdown(f"<small>{item['snippet']}</small>", unsafe_allow_html=True)
                    
                    # Tags
                    if item.get('tags'):
                        tags_html = "".join([f"<span class='tag-chip'>{tag}</span>" for tag in item['tags'][:4]])
                        st.markdown(tags_html, unsafe_allow_html=True)
                        
                    # Expandable Details
                    with st.expander("Details"):
                        # Description Tabs
                        tab_readable, tab_raw = st.tabs(["Readable", "Raw HTML"])
                        
                        description_raw = item.get('description') or ""
                        snippet_raw = item.get('snippet') or ""
                        
                        with tab_readable:
                            st.markdown("**Snippet:**")
                            st.write(clean_html_to_text(snippet_raw) if snippet_raw else "No snippet.")
                            st.divider()
                            st.markdown("**Description:**")
                            st.write(clean_html_to_text(description_raw) if description_raw else "No description.")

                        with tab_raw:
                            st.markdown("**Snippet (HTML):**")
                            st.code(snippet_raw, language='html')
                            st.markdown("**Description (HTML):**")
                            st.code(description_raw, language='html')

                        st.text_input("Item ID", value=item['id'], key=f"id_{item['id']}", disabled=True)

        else:
            st.markdown(
                """
                <div style="text-align: center; color: #6c757d; padding: 2rem;">
                    No results to display.<br>
                    Try searching for something!
                </div>
                """, 
                unsafe_allow_html=True
            )

# --- Column 3: Map View ---
with col_map:
    st.markdown("##### 🗺️ Map")
    
    map_container = st.container(height=600)
    with map_container:
        m = folium.Map(
            location=st.session_state.map_center, 
            zoom_start=st.session_state.map_zoom,
            control_scale=True
        )
        
        # Add Search Maker
        if st.session_state.map_center != [20, 0]:
             folium.Marker(
                st.session_state.map_center, 
                popup="Focused Location", 
                icon=folium.Icon(color="red", icon="map-marker", prefix='fa')
            ).add_to(m)
            
        # Optional: Add bounding boxes for results (Nice to have, future)
        
        st_folium(m, width="100%", height=550)

# Debug Trace
if debug_mode:
    st.divider()
    st.subheader("🛠️ Debug State")
    st.json(st.session_state)
