import streamlit as st
import requests
import json
import time
import base64
import io
from PIL import Image, ImageOps
from datetime import datetime

# 🚀 iPhone HEIC Support
try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
except ImportError:
    pass

# ==============================================================================
# [ SECTION 1: SYSTEM CONFIGURATION & GLOBAL CONSTANTS ]
# ==============================================================================
WEB_APP_URL = "https://script.google.com/macros/s/AKfycbyCfSfjgYi7yQFpqBDshjYQ1Zye4VjaT-U4_0nfF9c5oYF1Pr0CrGI38Is4BS3KigIz/exec"
apiKey = st.secrets.get("GEMINI_API_KEY", "")
APP_VERSION = "v16.4.0"

# Strategic Model Tiering (Pro Account Priority)
MODELS_TO_TEST = [
    "gemini-3-flash",         # Next-Gen Fast
    "gemini-2.5-flash",       # High Performance
    "gemini-2.5-pro",         # Strategic Reasoning
    "gemini-2.0-flash"        # Stable Standard
]

# 18-Point Scope of Work Matrix (Guideline v2.2)
SOW_OPTS = [
    "Concept Development", "Branding Strategy", "PR Consulting", "Media Relations", 
    "Theme Design", "Visual Identity", "UI/UX Design", "Social Media Content", 
    "Influencer Seeding", "Video Production", "Motion Graphics", "Interactive Installation", 
    "Event Planning", "Event Production", "RSVP Management", "Talent Management", 
    "On-site Operation", "Technical Support"
]

st.set_page_config(
    page_title=f"Firebean Hub {APP_VERSION}",
    page_icon="🔥",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ==============================================================================
# [ SECTION 2: STATE MANAGEMENT & OPERATIONS LOGS ]
# ==============================================================================
if 'page' not in st.session_state: st.session_state.page = 1
if 'form_data' not in st.session_state: st.session_state.form_data = {}
if 'mc_questions' not in st.session_state: st.session_state.mc_questions = []
if 'mock_assets' not in st.session_state: st.session_state.mock_assets = False
if 'dark_mode' not in st.session_state: st.session_state.dark_mode = False 
if 'hero_index' not in st.session_state: st.session_state.hero_index = 0
if 'generated_content' not in st.session_state: st.session_state.generated_content = None
if 'sync_complete' not in st.session_state: st.session_state.sync_complete = False
if 'full_assets' not in st.session_state: st.session_state.full_assets = None
if 'ai_status' not in st.session_state: st.session_state.ai_status = "🟡 INITIALIZING"
if 'active_model' not in st.session_state: st.session_state.active_model = MODELS_TO_TEST[0]
if 'terminal_logs' not in st.session_state: 
    st.session_state.terminal_logs = [f"> System Initialized: v{APP_VERSION}", "> Handshaking with Pro Engines..."]

def add_log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    st.session_state.terminal_logs.append(f"[{ts}] {msg}")
    if len(st.session_state.terminal_logs) > 15:
        st.session_state.terminal_logs.pop(0)

# ==============================================================================
# [ SECTION 3: AI CONNECTION & HEARTBEAT ]
# ==============================================================================
def verify_ai_connection():
    if not apiKey:
        st.session_state.ai_status = "🔴 OFFLINE (Key Missing)"
        add_log("Security: GEMINI_API_KEY missing from Streamlit Secrets.")
        return
    for model_name in MODELS_TO_TEST:
        add_log(f"Probe: Testing {model_name}...")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={apiKey}"
        payload = {"contents": [{"role": "user", "parts": [{"text": "hi"}]}], "generationConfig": {"maxOutputTokens": 1}}
        try:
            res = requests.post(url, json=payload, timeout=8)
            if res.status_code == 200:
                st.session_state.ai_status = "🟢 ONLINE"
                st.session_state.active_model = model_name
                add_log(f"Success: Connected to {model_name}.")
                return
            elif res.status_code == 429:
                st.session_state.ai_status = "🔴 BUSY (429)"
                add_log("Congestion: Pro limit reached.")
                return 
        except: add_log(f"Network: {model_name} unreachable.")
        time.sleep(1.0)
    st.session_state.ai_status = "🔴 OFFLINE"; add_log("Critical: Handshake Failed.")

if st.session_state.ai_status == "🟡 INITIALIZING": verify_ai_connection()

# ==============================================================================
# [ SECTION 4: CSS STYLING (Swiss SpeedUp Design Spec) ]
# ==============================================================================
S_RED, S_DARK, S_WHITE, S_BG_DARK = "#E2231A", "#2A2A2A", "#FFFFFF", "#121212"
theme = {
    "bg": S_BG_DARK if st.session_state.dark_mode else S_WHITE,
    "text": "#FFFFFF" if st.session_state.dark_mode else S_DARK,
    "border": "#333333" if st.session_state.dark_mode else "#DDDDDD",
    "input_bg": "#1A1A1A" if st.session_state.dark_mode else "#FFFFFF",
}

st.markdown(f"""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@300;400;700;900&display=swap');
        .stApp {{ background-color: {theme['bg']}; color: {theme['text']}; font-family: 'Montserrat', sans-serif; transition: all 0.5s ease; }}
        h1, h2, h3, p, span, label, div, .stMarkdown {{ color: {theme['text']} !important; }}
        .header-container {{ display: flex; align-items: center; gap: 35px; padding: 20px 0; margin-bottom: 5px; }}
        .hero-title {{ font-size: 84px !important; font-weight: 900 !important; line-height: 0.85 !important; letter-spacing: -4px !important; margin: 0 !important; text-align: left !important; }}
        .dotted-sep {{ border-bottom: 1px dotted {theme['border']}; margin: 25px 0; width: 100%; }}
        .stTextInput input, .stTextArea textarea, .stSelectbox div[data-baseweb="select"] {{
            background-color: {theme['input_bg']} !important; border: 1px solid {theme['border']} !important; border-radius: 6px !important; color: {theme['text']} !important;
        }}
        .sec-header {{ font-size: 16px; font-weight: 900; color: {S_RED} !important; text-transform: uppercase; letter-spacing: 2px; margin-bottom: 15px; }}
        .progress-hub {{ position: fixed; top: 25px; right: 40px; z-index: 1000; }}
        .stButton button {{ background-color: {S_RED} !important; color: white !important; border-radius: 50px !important; padding: 10px 25px !important; font-weight: 700 !important; text-transform: uppercase; letter-spacing: 1px; border: none !important; }}
        .terminal-box {{ 
            background: #000; 
            color: #FFFFFF !important; 
            font-family: 'Courier New', monospace; 
            padding: 15px; 
            border-radius: 8px; 
            font-size: 11px; 
            line-height: 1.5; 
            border-left: 4px solid {S_RED}; 
            height: 200px; 
            overflow-y: auto;
            text-shadow: 0 0 1px rgba(255,255,255,0.2);
        }}
        .status-badge {{ background: {S_RED}; color: white; padding: 4px 12px; border-radius: 4px; font-size: 9px; font-weight: 900; letter-spacing: 1px; margin-bottom: 10px; display: inline-block; }}
        [data-testid="stSidebar"] {{display: none;}}
        header, footer {{visibility: hidden;}}
    </style>
""", unsafe_allow_html=True)

# ==============================================================================
# [ SECTION 5: UTILITIES (Progress, JSON Cleaning, Image Processing) ]
# ==============================================================================
def render_progress(percent):
    circum = 251.3
    offset = circum * (1 - percent / 100)
    st.markdown(f"""<div class="progress-hub"><div style="position:relative; width:90px; height:90px; display:flex; align-items:center; justify-content:center;"><svg width="90" height="90"><circle stroke="{theme['border']}" stroke-width="1" fill="transparent" r="35" cx="45" cy="45"/><circle stroke="{S_RED}" stroke-width="2" stroke-dasharray="{circum}" stroke-dashoffset="{offset}" stroke-linecap="round" fill="transparent" r="35" cx="45" cy="45" style="transition: stroke-dashoffset 0.8s ease-out; transform: rotate(-90deg); transform-origin: center;"/></svg><div style="position:absolute; font-size:22px; font-weight:300; color:{theme['text']};">{percent}%</div></div></div>""", unsafe_allow_html=True)

def clean_json_response(raw_text):
    """Robust utility to strip markdown and extract raw JSON content."""
    if not raw_text: return None
    text = raw_text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        if lines[0].startswith("
