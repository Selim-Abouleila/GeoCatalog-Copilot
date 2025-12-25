import streamlit as st

def apply_custom_css():
    st.markdown("""
        <style>
        /* Main App Background - Light Neutral */
        .stApp {
            background-color: #f8f9fa;
        }

        /* Typography */
        h1, h2, h3 {
            font-family: 'Inter', sans-serif;
            color: #1a1a1a;
        }
        
        /* Card Styling for Results */
        div[data-testid="stVerticalBlock"] > div[data-testid="stVerticalBlockBorderWrapper"] {
            background-color: white;
            border-radius: 8px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
            transition: box-shadow 0.2s ease-in-out;
            padding: 1rem;
        }
        
        div[data-testid="stVerticalBlock"] > div[data-testid="stVerticalBlockBorderWrapper"]:hover {
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }

        /* Chat Message Styling */
        .stChatMessage {
            background-color: white;
            border-radius: 8px;
            border: 1px solid #e9ecef;
            padding: 0.5rem;
        }

        /* Tag Chips */
        .tag-chip {
            display: inline-block;
            background-color: #e9ecef;
            color: #495057;
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 0.75rem;
            margin-right: 4px;
            margin-bottom: 4px;
            font-weight: 500;
        }
        
        /* Quality Score Badge */
        .score-badge-high {
            color: #0f5132;
            background-color: #d1e7dd;
            padding: 2px 6px;
            border-radius: 4px;
            font-weight: bold;
            font-size: 0.8rem;
        }
        
        .score-badge-med {
            color: #664d03;
            background-color: #fff3cd;
            padding: 2px 6px;
            border-radius: 4px;
            font-weight: bold;
            font-size: 0.8rem;
        }
        
        /* Sidebar Polish */
        section[data-testid="stSidebar"] {
            background-color: #ffffff;
            border-right: 1px solid #e9ecef;
        }
        
        /* Link styling */
        a {
            color: #0d6efd;
            text-decoration: none;
        }
        a:hover {
            text-decoration: underline;
        }
        </style>
    """, unsafe_allow_html=True)
