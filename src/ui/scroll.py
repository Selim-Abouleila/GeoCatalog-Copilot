import streamlit as st
import streamlit.components.v1 as components

def ensure_scroll_to_top_once():
    """
    Injects a script to scroll to the top of the page on the first load of a session.
    Guarded by session_state to prevent repeated scrolling.
    
    Uses aggressive JS to:
    1. Blur any auto-focused element (like st.chat_input).
    2. Scroll specific Streamlit containers to top.
    3. Retry multiple times to handle race conditions.
    """
    if "did_scroll_to_top" not in st.session_state:
        st.session_state["did_scroll_to_top"] = True
        
        js = """
        <script>
            (function() {
                const parent = window.parent;
                const doc = parent.document;

                function getScrollContainer() {
                    return doc.querySelector('div[data-testid="stAppViewContainer"]')
                        || doc.querySelector('section.main')
                        || doc.querySelector('div[data-testid="stMain"]')
                        || doc.scrollingElement
                        || doc.documentElement
                        || doc.body;
                }

                function blurChatIfFocused() {
                    try {
                        const active = doc.activeElement;
                        if (active && typeof active.blur === "function") active.blur();
                    } catch (e) {}
                }

                function scrollTopNow() {
                    const c = getScrollContainer();
                    try { c.scrollTop = 0; } catch (e) {}
                    try { parent.scrollTo(0, 0); } catch (e) {}
                    try { doc.documentElement.scrollTop = 0; doc.body.scrollTop = 0; } catch (e) {}
                }

                function tick() {
                    blurChatIfFocused();
                    scrollTopNow();
                }

                // Run a few times to beat delayed autofocus/layout
                let n = 0;
                const h = setInterval(() => {
                    tick();
                    n += 1;
                    if (n >= 10) clearInterval(h);
                }, 100);

                setTimeout(tick, 200);
                setTimeout(tick, 600);
            })();
        </script>
        """
        components.html(js, height=0)
