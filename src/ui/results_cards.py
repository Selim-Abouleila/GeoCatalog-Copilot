
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

def render_result_card(item, current_selected_id, preview_limit, on_visualize_click, on_select_click):
    """
    Renders a single result card with correct link behavior.
    
    Args:
        item (dict): The result item.
        current_selected_id (str): Currently selected item ID.
        preview_limit (int): Limit for preview.
        on_visualize_click (callable): Function(item_id) -> None.
        on_select_click (callable): Function(item_id) -> None.
    """
    score = item.get('quality_score', 0)
    bclass = "score-badge-high" if score > 70 else "score-badge-med"
    is_sel = (current_selected_id == item['id'])
    
    with st.container(border=True):
        # 1. Title Link (ALWAYS CLICKABLE)
        # Use simple markdown link
        st.markdown(f"**[{item['title']}]({item['url']})**")
        
        # 2. Selected Status Badge (Non-blocking)
        if is_sel:
            st.caption("✅ Selected for Chat")
        
        # 3. Metadata
        st.caption(f"{item['type']} • {item['owner']}")
        
        # 4. Score
        c1, c2 = st.columns([1,3])
        c1.markdown(f"<span class='{bclass}'>{score}</span>", unsafe_allow_html=True)
        c2.progress(score/100)
        
        # 5. Buttons Row
        # [Open] [Visualize] [Use Item]
        b1, b2, b3 = st.columns([1, 1.2, 1])
        
        with b1:
             # Explicit Open Button (Streamlit >= 1.29 has link_button, assuming available)
             # If not, we already have the title link, but user asked for explicit open.
             try:
                 st.link_button("Open", item['url'])
             except AttributeError:
                 st.markdown(f"[Open]({item['url']})")
        
        with b2:
             # Visualize
             if item['type'] in ['Feature Service', 'Feature Layer', 'Map Service']:
                 if st.button("👁️ Visualize", key=f"viz_{item['id']}"):
                     # ACTION: Call callback
                     on_visualize_click(item['id'])
        
        with b3:
             # Use Item
             # Highlight: Primary if selected?
             lbl = "Selected" if is_sel else "Use Item"
             # If selected, maybe disable? Or keep to allow re-select triggers?
             # User said "Use Item" sets active_item_id.
             if st.button(lbl, key=f"sel_{item['id']}", disabled=is_sel):
                 on_select_click(item['id'])

        with st.expander("Details"):
             st.write(clean_html_to_text(item.get('snippet')))
             st.text_input("ID", value=item['id'], key=f"id_{item['id']}", disabled=True)
