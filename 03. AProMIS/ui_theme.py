# ui_theme.py
import streamlit as st

def apply_global_dark_css():
    # (optional) enforce dark UI regardless of picker
    st.markdown("""
    <style>
    :root {
      --bg: #1C1D22;
      --panel: #2A2C32;
      --text: #E6E8EB;
      --muted: #9AA4AF;
    }
    html, body, [data-testid="stAppViewContainer"] {
      background-color: var(--bg) !important; color: var(--text) !important;
    }
    [data-testid="stSidebar"] {
      background-color: var(--panel) !important; color: var(--text) !important;
      border-right: 1px solid #23252A !important;
    }
    [data-testid="stHeader"], [data-testid="stToolbar"] { background: transparent !important; }
    /* inputs */
    .stTextInput input, .stTextArea textarea, .stSelectbox div[data-baseweb="select"],
    .stMultiSelect div[data-baseweb="select"], .stDateInput input {
      background: #1F2026 !important; color: var(--text) !important; border-color: #383B44 !important;
    }
    .stButton button, .stDownloadButton button {
      background: #353945 !important; color: var(--text) !important; border: 1px solid #474C59 !important;
    }
    .stButton button:hover, .stDownloadButton button:hover {
      background: #3E4351 !important; border-color: #5A6070 !important;
    }
    </style>
    """, unsafe_allow_html=True)

def use_plotly_dark():
    try:
        import plotly.io as pio
        pio.templates.default = "plotly_dark"
    except Exception:
        pass