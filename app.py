import streamlit as st
import requests
import json
import time
import random
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

# ==========================================
# 1. CONFIGURATION & VERSIONING
# ==========================================
WEB_APP_URL = "https://script.google.com/macros/s/AKfycbyCfSfjgYi7yQFpqBDshjYQ1Zye4VjaT-U4_0nfF9c5oYF1Pr0CrGI38Is4BS3KigIz/exec"
apiKey = "" 
APP_VERSION = "v13.2.0"

st.set_page_config(
    page_title=f"Firebean Brain Collector {APP_VERSION}",
    page_icon="🔥",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ==========================================
# 2. SPEEDUP THEME ENGINE (v2)
# ==========================================
if 'page' not in st.session_state: st.session_state.page = 1
if 'form_data' not in st.session_state: st.session_state.form_data = {}
if 'mc_questions' not in st.session_state: st.session_state.mc_questions = []
if 'mock_assets' not in st.session_state: st.session_state.mock_assets = False
if 'dark_mode' not in st.session_state: st.session_state.dark_mode = False # Default to Light for Profile Card visibility
if 'hero_index' not in st.session_state: st.session_state.hero_index = 0

# SpeedUp Specification Palette
S_RED = "#E2231A"
S_DARK = "#2A2A2A"
S_WHITE = "#FFFFFF"
S_GREY = "#F2F2F2"
S_BG_DARK = "#141414"

t = {
    "bg": S_BG_DARK if st.session_state.dark_mode else S_WHITE,
    "card": "#1E1E1E" if st.session_state.dark_mode else S_GREY,
    "text": "#FFFFFF" if st.session_state.dark_mode else S_DARK,
    "muted": "#999999" if st.session_state.dark_mode else "#666666",
    "border": "#333333" if st.session_state.dark_mode else "transparent",
    "input_bg": "#1A1A1A" if st.session_state.dark_mode else "#FFFFFF"
}

st.markdown(f"""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@300;400;700;900&display=swap');
        
        .stApp {{ 
            background-color: {t['bg']}; 
            color: {t['text']}; 
            font-family: 'Montserrat', sans-serif;
            transition: background-color 0.6s ease;
        }}

        h1, h2, h3, p, span, label, div, .stMarkdown {{ 
            color: {t['text']} !important; 
        }}

        /* Header Layout: Logo + Title */
        .header-container {{
            display: flex;
            align-items: center;
            gap: 35px;
            margin-bottom: 50px;
            padding: 20px 0;
        }}

        .hero-title {{
            font-size: 68px !important;
            font-weight: 900 !important;
            line-height: 0.9 !important;
            letter-spacing: -3px !important;
            margin: 0 !important;
        }}

        /* Progress Hub - SpeedUp Style */
        .progress-hub {{ 
            position: fixed; top: 40px; right: 60px; z-index: 1000; 
        }}

        /* Rounded Profile Card Concept */
        .fb-card {{
            background: {t['card']};
            border-radius: 32px;
            padding: 50px;
            margin-bottom: 30px;
            border: 1px solid {t['border']};
            transition: all 0.4s ease;
        }}

        /* Section Headlines - SpeedUp Accent */
        .sec-header {{
            font-size: 14px;
            font-weight: 900;
            color: {S_RED} !important;
            text-transform: uppercase;
            letter-spacing: 3px;
            margin-bottom: 30px;
            display: flex;
            align-items: center;
            gap: 15px;
        }}
        .sec-header svg {{ stroke: {S_RED}; }}

        /* Large Form Control overrides */
        .stTextInput input, .stTextArea textarea {{
            background-color: {t['input_bg']} !important;
            border: 2px solid {t['input_bg']} !important;
            border-radius: 16px !important;
            padding: 18px !important;
            font-size: 16px !important;
        }}
        
        .stButton button {{
            border-radius: 100px !important;
            padding: 15px 40px !important;
            font-weight: 900 !important;
            text-transform: uppercase;
            letter-spacing: 2px;
            background-color: {S_RED} !important;
            color: white !important;
            border: none !important;
        }}

        .thumb-container {{
            background: {t['input_bg']};
            border-radius: 20px;
            padding: 10px;
            text-align: center;
            border: 1px solid {t['border']};
        }}

        [data-testid="stSidebar"] {{display: none;}}
        header {{visibility: hidden;}}
        footer {{visibility: hidden;}}
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 3. UTILITIES & VECTOR ICONS
# ==========================================
def icon_svg(name):
    icons = {
        "user": '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path><circle cx="12" cy="7" r="4"></circle></svg>',
        "globe": '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="2" y1="12" x2="22" y2="12"></line><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"></path></svg>',
        "briefcase": '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="7" width="20" height="14" rx="2" ry="2"></rect><path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"></path></svg>',
        "image": '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect><circle cx="8.5" cy="8.5" r="1.5"></circle><polyline points="21 15 16 10 5 21"></polyline></svg>'
    }
    return icons.get(name, "")

def render_speedup_progress(percent):
    circum = 251.3
    offset = circum * (1 - percent / 100)
    st.markdown(f"""
    <div class="progress-hub">
        <div style="position:relative; width:110px; height:110px; display:flex; align-items:center; justify-content:center;">
            <svg width="110" height="110">
                <circle stroke="{S_RED}22" stroke-width="4" fill="transparent" r="40" cx="55" cy="55"/>
                <circle stroke="{S_RED}" stroke-width="4" stroke-dasharray="{circum}" stroke-dashoffset="{offset}" 
                        stroke-linecap="round" fill="transparent" r="40" cx="55" cy="55" 
                        style="transition: stroke-dashoffset 1s ease-out; transform: rotate(-90deg); transform-origin: center;"/>
            </svg>
            <div style="position:absolute; font-size:28px; font-weight:300; color:{t['text']};">{percent}%</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

def call_gemini_ai(prompt, sys_prompt, image_blobs=None):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-09-2025:generateContent?key={apiKey}"
    parts = [{"text": prompt}]
    if image_blobs:
        for b in image_blobs[:4]:
            parts.append({"inline_data": {"mime_type": "image/png", "data": b}})
    payload = {"contents": [{"parts": parts}], "systemInstruction": {"parts": [{"text": sys_prompt}]}, "generationConfig": {"responseMimeType": "application/json"}}
    try:
        res = requests.post(url, json=payload, timeout=60)
        return res.json()['candidates'][0]['content']['parts'][0]['text']
    except: return None

# Options Setup
CAT_OPTS = ["GOVERNMENT & PUBLIC SECTOR", "LIFESTYLE & CONSUMER", "F&B & HOSPITALITY", "MALLS & VENUES"]
WWD_OPTS = ["ROVING EXHIBITIONS", "SOCIAL & CONTENT", "INTERACTIVE & TECH", "PR & MEDIA", "EVENTS & CEREMONIES"]
SOW_OPTS = [
    "Concept Development", "Branding Strategy", "PR Consulting", "Media Relations",
    "Theme Design", "Visual Identity", "UI/UX Design", "Social Media Content",
    "Influencer Seeding", "Video Production", "Motion Graphics", "Interactive Installation",
    "Event Planning", "Event Production", "RSVP Management", "Talent Management",
    "On-site Operation", "Technical Support"
]

def run_boss_test():
    st.session_state.form_data = {
        "client": "Firebean HQ", "project": "Strategic Neumorphic Portfolio", "venue": "Global Cyberport",
        "category": ["LIFESTYLE & CONSUMER"], "what_we_do": ["INTERACTIVE & TECH"],
        "scope": ["Concept Development", "Interactive Installation", "Technical Support"],
        "open_question": "Utilize AI and premium typography to create an evergreen B2B portfolio."
    }
    st.session_state.mock_assets = True
    st.rerun()

# ==========================================
# 4. PAGE 1: STRATEGIC COLLECTOR
# ==========================================
STRATEGIC_REQUIRED = ["client", "project", "venue", "category", "what_we_do", "scope", "open_question"]

if st.session_state.page == 1:
    # Progress Calculation
    pts = sum(1 for k in STRATEGIC_REQUIRED if st.session_state.form_data.get(k))
    if st.session_state.mock_assets: pts += 2
    else:
        if st.session_state.get('uploaded_logo'): pts += 1
        if st.session_state.get('uploaded_photos'): pts += 1
    
    percent = int((pts / 9) * 100) 
    render_speedup_progress(min(percent, 100))

    # Header with Logo & Title side-by-side
    st.markdown(f"""
        <div class="header-container">
            <img src="https://raw.githubusercontent.com/dickson-crypto/Firebean-app/main/Firebeanlogo2026.png" width="220">
            <h1 class="hero-title">Project<br>Collector.</h1>
        </div>
    """, unsafe_allow_html=True)

    # Mode Toggle
    mt1, mt2 = st.columns([6, 1])
    with mt2:
        if st.button("🌓 MODE", use_container_width=True):
            st.session_state.dark_mode = not st.session_state.dark_mode
            st.rerun()

    if st.button("🚀 BOSS TEST MODE", use_container_width=True): run_boss_test()

    # --- CARD 1: IDENTITY ---
    st.markdown('<div class="fb-card">', unsafe_allow_html=True)
    st.markdown(f'<div class="sec-header">{icon_svg("user")} Brand Identity</div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    with c1: client = st.text_input("Client", value=st.session_state.form_data.get("client", ""), placeholder="e.g. Levi's")
    with c2: project = st.text_input("Project Name", value=st.session_state.form_data.get("project", ""), placeholder="e.g. Pop-up")
    with c3: venue = st.text_input("Venue", value=st.session_state.form_data.get("venue", ""), placeholder="Location")
    st.markdown('</div>', unsafe_allow_html=True)

    # --- CARD 2: STRATEGY (Who/What/Scope) ---
    st.markdown('<div class="fb-card">', unsafe_allow_html=True)
    st.markdown(f'<div class="sec-header">{icon_svg("globe")} Strategic Framework</div>', unsafe_allow_html=True)
    
    st.write("**Who we help**")
    cat_cols = st.columns(4)
    sel_cat = []
    for i, opt in enumerate(CAT_OPTS):
        with cat_cols[i % 4]:
            if st.checkbox(opt, key=f"c_{opt}", value=(opt in st.session_state.form_data.get("category", []))): sel_cat.append(opt)
    
    st.write("<br>**What we do**", unsafe_allow_html=True)
    wwd_cols = st.columns(3)
    sel_wwd = []
    for i, opt in enumerate(WWD_OPTS):
        with wwd_cols[i % 3]:
            if st.checkbox(opt, key=f"w_{opt}", value=(opt in st.session_state.form_data.get("what_we_do", []))): sel_wwd.append(opt)

    st.write("<br>**Scope of Work**", unsafe_allow_html=True)
    sow_cols = st.columns(3)
    sel_sow = []
    for i, opt in enumerate(SOW_OPTS):
        with sow_cols[i % 3]:
            if st.checkbox(opt, key=f"s_{opt}", value=(opt in st.session_state.form_data.get("scope", []))): sel_sow.append(opt)
    st.markdown('</div>', unsafe_allow_html=True)

    # --- CARD 3: VISUAL ASSETS (Thumbnails & Hero Picker) ---
    st.markdown('<div class="fb-card">', unsafe_allow_html=True)
    st.markdown(f'<div class="sec-header">{icon_svg("image")} Visual Assets Hub</div>', unsafe_allow_html=True)
    
    l1, l2 = st.columns(2)
    with l1:
        logo_b = st.file_uploader("Logo Black", key="logo_b")
        if logo_b: st.session_state.uploaded_logo = True
    with l2:
        logo_w = st.file_uploader("Logo White", key="logo_w")
        if logo_w: st.session_state.uploaded_logo = True

    st.write("**Project Gallery** (Designate 1 Hero)")
    photos = st.file_uploader("Upload Project Photos", accept_multiple_files=True, key="photos")
    
    if photos:
        st.session_state.uploaded_photos = True
        cols = st.columns(4)
        img_previews = []
        for idx, p in enumerate(photos[:8]):
            with cols[idx % 4]:
                img = Image.open(p)
                st.image(img, use_container_width=True)
                if st.checkbox("Hero Photo", key=f"hero_{idx}", value=(st.session_state.hero_index == idx)):
                    st.session_state.hero_index = idx
                # Store for AI
                img_byte_arr = io.BytesIO()
                img.save(img_byte_arr, format='PNG')
                img_previews.append(base64.b64encode(img_byte_arr.getvalue()).decode('utf-8'))
        st.session_state.photos_for_ai = img_previews

    st.markdown('</div>', unsafe_allow_html=True)

    # --- CARD 4: CORE CONCEPT ---
    st.markdown('<div class="fb-card">', unsafe_allow_html=True)
    st.markdown(f'<div class="sec-header">{icon_svg("briefcase")} Strategic Core</div>', unsafe_allow_html=True)
    u1, u2 = st.columns([1, 2])
    with u1: youtube = st.text_input("YouTube URL (Optional)")
    with u2: open_q = st.text_area("Core Concept?", value=st.session_state.form_data.get("open_question", ""), height=100)
    st.markdown('</div>', unsafe_allow_html=True)

    if percent >= 100:
        if st.button("Generate Strategic Recap 👉", type="primary", use_container_width=True):
            st.session_state.form_data.update({"client":client,"project":project,"venue":venue,"category":sel_cat,"what_we_do":sel_wwd,"scope":sel_sow,"open_question":open_q,"youtube":youtube})
            st.session_state.page = 2; st.rerun()
    else:
        st.warning(f"Project incomplete: {percent}%")

# ==========================================
# 5. PAGE 2: STRATEGIC RECAP
# ==========================================
elif st.session_state.page == 2:
    st.markdown(f"""
        <div class="header-container">
            <img src="https://raw.githubusercontent.com/dickson-crypto/Firebeanlogo2026.png" width="220">
            <h1 class="hero-title">Strategic<br>Recap.</h1>
        </div>
    """, unsafe_allow_html=True)
    if st.button("← Back"): st.session_state.page = 1; st.rerun()

    l, r = st.columns([1.2, 1])
    with l:
        st.markdown('<div class="fb-card">', unsafe_allow_html=True)
        if st.button("📝 GENERATE DIAGNOSTICS"):
            with st.spinner("AI Analysis in progress..."):
                sys = "Output JSON array of 15 diagnostic questions. Format: [{'q':'...', 'opts':['A','B','C']}]"
                ctx = f"Brand: {st.session_state.form_data['client']}. SOW: {', '.join(st.session_state.form_data['scope'])}. Concept: {st.session_state.form_data['open_question']}"
                res = call_gemini_ai(ctx, sys, st.session_state.get('photos_for_ai'))
                if res: st.session_state.mc_questions = json.loads(res.replace("```json", "").replace("```", ""))
        if st.session_state.mc_questions:
            for i, q in enumerate(st.session_state.mc_questions):
                st.markdown(f'<div class="sec-header">Q{i+1}. {q["q"]}</div>', unsafe_allow_html=True)
                for opt in q["opts"]: st.checkbox(opt, key=f"mc_{i}_{opt}")
        st.markdown("</div>", unsafe_allow_html=True)

    with r:
        st.markdown('<div class="fb-card">', unsafe_allow_html=True)
        st.markdown(f'<div class="sec-header">Strategic Terminal</div>', unsafe_allow_html=True)
        log = st.empty()
        if st.button("🚀 EXECUTE MASTER SYNC", type="primary", use_container_width=True):
            log.markdown('<div class="terminal-box">> Analysis Complete.<br>> Master DB Mapping v13...</div>', unsafe_allow_html=True)
            time.sleep(1)
            payload = {**st.session_state.form_data, "category": ", ".join(st.session_state.form_data['category']), "what_we_do": ", ".join(st.session_state.form_data['what_we_do']), "scope": "\n".join(st.session_state.form_data['scope']), "date": datetime.now().strftime("%Y %b").upper()}
            res = requests.post(WEB_APP_URL, json=payload)
            if res.status_code == 200:
                log.markdown('<div class="terminal-box">> SYNC SUCCESSFUL.<br>> Master DB Updated.</div>', unsafe_allow_html=True)
                st.balloons()
            else: st.error("Sync Failed.")
        st.markdown("</div>", unsafe_allow_html=True)

st.markdown(f"<p style='text-align: center; color: grey; font-size: 10px; letter-spacing: 2px;'>FIREBEAN LIMITED | SPEEDUP UI v13.2</p>", unsafe_allow_html=True)
