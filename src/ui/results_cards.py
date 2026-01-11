
import streamlit as st
from src.utils.text import clean_html_to_text
from src.ui.map_state import set_pending_zoom
from src.tools.feature_layer_tools import query_preview_geojson
from src.ui.map_state import add_preview_layer
# We import handle_visualize related logic? 
# Better to pass a callback or keep visualization logic simple here.
# But `handle_visualize` is in `app.py`. 
# To avoid circular imports, `render_result_card` should return an action or 
# we inject the callback. Or we assume `app.py` handles the logic 
# and we just render buttons. 
# But the user asked to extract UI. 
# Let's keep `handle_visualize` logic inside the component using a callback if possible, 
# OR just replicate the simple call if dependencies allow.

# Wait, `handle_visualize` is complex (toast, spinner). 
# Let's define `render_result_card` to take a `on_visualize` callback.

def render_result_card(item, current_selected_id, preview_limit, on_visualize_click, on_count_click=None):
    """
    Renders a single result card with correct link behavior.
    
    Args:
        item (dict): The result item.
        current_selected_id (str): Currently selected item ID (unused for selection but kept for compatibility if needed).
        preview_limit (int): Limit for preview.
        on_visualize_click (callable): Function(item_id) -> None.
        on_count_click (callable, optional): Function(item_id) -> None.
    """
    score = item.get('quality_score', 0)
    bclass = "score-badge-high" if score > 70 else "score-badge-med"
    
    with st.container(border=True):
        # 1. Title Link (ALWAYS CLICKABLE)
        # Use simple markdown link
        st.markdown(f"**[{item['title']}]({item['url']})**")
        
        # 2. Metadata
        st.caption(f"{item['type']} • {item['owner']}")
        
        # 3. Score
        c1, c2 = st.columns([1,3])
        c1.markdown(f"<span class='{bclass}'>{score}</span>", unsafe_allow_html=True)
        c2.progress(score/100)
        
        # 4. Buttons Row
        # [Open] [Visualize] [Count]
        b1, b2, b3 = st.columns([0.8, 1.2, 1])
        
        with b1:
             # Explicit Open
             st.markdown(f"[Open]({item['url']})")
        
        with b2:
             # Visualize
             if item['type'] in ['Feature Service', 'Feature Layer', 'Map Service']:
                 if st.button("👁️ Visualize", key=f"viz_{item['id']}"):
                     on_visualize_click(item['id'])
        
        with b3:
             # Count Rows
             if item['type'] in ['Feature Service', 'Feature Layer']:
                 if st.button("🔢 Count", key=f"cnt_{item['id']}", help="Count records in this service"):
                     if on_count_click: on_count_click(item['id'])
                     
        with st.expander("Details"):
             st.write(clean_html_to_text(item.get('snippet')))
             st.text_input("ID", value=item['id'], key=f"id_{item['id']}", disabled=True)
