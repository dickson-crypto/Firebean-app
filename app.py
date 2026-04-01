import streamlit as st
import requests
import json
import time
import random
import base64
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
APP_VERSION = "v13.0.0"

st.set_page_config(
    page_title=f"Firebean Brain Collector {APP_VERSION}",
    page_icon="🔥",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ==========================================
# 2. THEME ENGINE - SPEEDUP SPEC
# ==========================================
if 'page' not in st.session_state: st.session_state.page = 1
if 'form_data' not in st.session_state: st.session_state.form_data = {}
if 'mc_questions' not in st.session_state: st.session_state.mc_questions = []
if 'mock_assets' not in st.session_state: st.session_state.mock_assets = False
if 'dark_mode' not in st.session_state: st.session_state.dark_mode = True

# SpeedUp Color Map
S_RED = "#E2231A"
S_DARK = "#2A2A2A"
S_WHITE = "#FFFFFF"
S_GREY = "#F5F5F5"

t = {
    "bg": "#141414" if st.session_state.dark_mode else S_WHITE,
    "card": "#1E1E1E" if st.session_state.dark_mode else S_GREY,
    "text": "#FFFFFF" if st.session_state.dark_mode else S_DARK,
    "muted": "#999999" if st.session_state.dark_mode else "#666666",
    "border": "#333333" if st.session_state.dark_mode else "#E0E0E0",
}

st.markdown(f"""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@300;400;700;900&display=swap');
        
        .stApp {{ 
            background-color: {t['bg']}; 
            color: {t['text']}; 
            font-family: 'Montserrat', sans-serif;
            transition: all 0.5s ease;
        }}

        h1, h2, h3, p, span, label, div, .stMarkdown {{ 
            color: {t['text']} !important; 
        }}

        /* SpeedUp Oversized Headlines */
        .hero-title {{
            font-size: 64px !important;
            font-weight: 900 !important;
            line-height: 1.1 !important;
            letter-spacing: -2px !important;
            margin-bottom: 20px !important;
        }}

        /* Progress Hub - SpeedUp Style */
        .progress-hub {{ 
            position: fixed; top: 30px; right: 50px; z-index: 1000; 
        }}

        /* Profile Card Concept */
        .fb-card {{
            background: {t['card']};
            border-radius: 24px;
            padding: 45px;
            margin-bottom: 40px;
            border: 1px solid {t['border']};
            transition: transform 0.3s ease;
        }}

        /* Section Headers - High Contrast */
        .sec-header {{
            font-size: 18px;
            font-weight: 700;
            color: {S_RED} !important;
            text-transform: uppercase;
            letter-spacing: 2px;
            margin-bottom: 20px;
            display: flex;
            align-items: center;
        }}
        .sec-header::before {{
            content: '';
            width: 12px;
            height: 12px;
            background: {S_RED};
            border-radius: 50%;
            margin-right: 12px;
        }}

        /* Custom Checkbox Skin */
        .stCheckbox label {{
            font-size: 12px !important;
            font-weight: 400 !important;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}

        /* Strategic Terminal */
        .terminal-box {{
            background: {S_DARK};
            color: {S_WHITE};
            padding: 25px;
            border-radius: 16px;
            font-family: 'Courier New', monospace;
            font-size: 13px;
            line-height: 1.8;
            border-left: 5px solid {S_RED};
        }}

        /* Input Overrides */
        .stTextInput input, .stTextArea textarea {{
            background-color: {t['bg']} !important;
            border: 2px solid {t['border']} !important;
            border-radius: 12px !important;
            padding: 15px !important;
        }}
        
        .stButton button {{
            border-radius: 50px !important;
            padding: 12px 30px !important;
            font-weight: 700 !important;
            text-transform: uppercase;
            letter-spacing: 1px;
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
        "user": '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path><circle cx="12" cy="7" r="4"></circle></svg>',
        "target": '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><circle cx="12" cy="12" r="6"></circle><circle cx="12" cy="12" r="2"></circle></svg>',
        "camera": '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"></path><circle cx="12" cy="13" r="4"></circle></svg>'
    }
    return icons.get(name, "")

def render_speedup_progress(percent):
    circum = 282.7 
    offset = circum * (1 - percent / 100)
    st.markdown(f"""
    <div class="progress-hub">
        <div style="position:relative; width:120px; height:120px; display:flex; align-items:center; justify-content:center;">
            <svg width="120" height="120">
                <circle stroke="{t['border']}" stroke-width="2" fill="transparent" r="45" cx="60" cy="60"/>
                <circle stroke="{S_RED}" stroke-width="3" stroke-dasharray="{circum}" stroke-dashoffset="{offset}" 
                        stroke-linecap="round" fill="transparent" r="45" cx="60" cy="60" 
                        style="transition: stroke-dashoffset 1.2s cubic-bezier(0.4, 0, 0.2, 1); transform: rotate(-90deg); transform-origin: center;"/>
            </svg>
            <div style="position:absolute; font-size:32px; font-weight:300; color:{t['text']};">{percent}%</div>
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

# Guidelines
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
        "client": "Firebean HQ", "project": "Strategic Neumorphic Portfolio", "venue": "Cyberport",
        "category": ["LIFESTYLE & CONSUMER"], "what_we_do": ["INTERACTIVE & TECH"],
        "scope": ["Concept Development", "Interactive Installation", "Technical Support"],
        "open_question": "How to utilize AI to transform static PR data into a 24/7 lead generation engine for event agencies?"
    }
    st.session_state.mock_assets = True
    st.rerun()

# ==========================================
# 4. PAGE 1: STRATEGIC COLLECTOR
# ==========================================
STRATEGIC_REQUIRED = ["client", "project", "venue", "category", "what_we_do", "scope", "open_question"]

if st.session_state.page == 1:
    points = sum(1 for k in STRATEGIC_REQUIRED if st.session_state.form_data.get(k))
    if st.session_state.mock_assets: points += 2
    else:
        if st.session_state.get('uploaded_logo'): points += 1
        if st.session_state.get('uploaded_photos'): points += 1
    
    percent = int((points / 9) * 100) 
    render_speedup_progress(min(percent, 100))

    # Header with Minimal Toggle
    col_l, col_r = st.columns([5, 1])
    with col_l: st.image("https://raw.githubusercontent.com/dickson-crypto/Firebean-app/main/Firebeanlogo2026.png", width=300)
    with col_r:
        if st.button("🌓 MODE", use_container_width=True):
            st.session_state.dark_mode = not st.session_state.dark_mode
            st.rerun()

    st.markdown('<h1 class="hero-title">Project<br>Collector.</h1>', unsafe_allow_html=True)
    
    if st.button("🚀 BOSS TEST MODE", use_container_width=True): run_boss_test()

    # SECTION 1: CORE DATA
    st.markdown('<div class="fb-card">', unsafe_allow_html=True)
    st.markdown(f'<div class="sec-header">{icon_svg("user")} Brand Identity</div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    with c1: client = st.text_input("Client", value=st.session_state.form_data.get("client", ""), placeholder="e.g. Levi's")
    with c2: project = st.text_input("Project Name", value=st.session_state.form_data.get("project", ""), placeholder="e.g. Pop-up")
    with c3: venue = st.text_input("Venue", value=st.session_state.form_data.get("venue", ""), placeholder="e.g. Harbour City")
    
    # ROW 1: WHO WE HELP
    st.markdown('<div class="sec-header">Who we help</div>', unsafe_allow_html=True)
    sel_cat = []
    cat_cols = st.columns(3)
    for i, opt in enumerate(CAT_OPTS):
        with cat_cols[i % 3]:
            if st.checkbox(opt, key=f"c_{opt}", value=(opt in st.session_state.form_data.get("category", []))):
                sel_cat.append(opt)

    # ROW 2: WHAT WE DO
    st.markdown('<div class="sec-header">What we do</div>', unsafe_allow_html=True)
    sel_wwd = []
    wwd_cols = st.columns(3)
    for i, opt in enumerate(WWD_OPTS):
        with wwd_cols[i % 3]:
            if st.checkbox(opt, key=f"w_{opt}", value=(opt in st.session_state.form_data.get("what_we_do", []))):
                sel_wwd.append(opt)

    # ROW 3: SCOPE
    st.markdown('<div class="sec-header">Scope of Work</div>', unsafe_allow_html=True)
    sel_sow = []
    sow_cols = st.columns(3)
    for i, opt in enumerate(SOW_OPTS):
        with sow_cols[i % 3]:
            if st.checkbox(opt, key=f"s_{opt}", value=(opt in st.session_state.form_data.get("scope", []))):
                sel_sow.append(opt)
    st.markdown('</div>', unsafe_allow_html=True)

    # SECTION 2: ASSETS
    st.markdown('<div class="fb-card">', unsafe_allow_html=True)
    st.markdown(f'<div class="sec-header">{icon_svg("camera")} Visual Assets Hub</div>', unsafe_allow_html=True)
    a1, a2, a3 = st.columns([1, 1, 2])
    with a1:
        logo_b = st.file_uploader("Logo Black", key="logo_b")
        if logo_b: st.session_state.uploaded_logo = True
    with a2:
        logo_w = st.file_uploader("Logo White", key="logo_w")
        if logo_w: st.session_state.uploaded_logo = True
    with a3:
        photos = st.file_uploader("Gallery (Min 4)", accept_multiple_files=True, key="photos")
        if photos: 
            st.session_state.uploaded_photos = True
            img_list = []
            for p in photos[:4]: img_list.append(base64.b64encode(p.read()).decode('utf-8'))
            st.session_state.photos_for_ai = img_list

    st.markdown("---")
    u1, u2 = st.columns([1, 2])
    with u1: youtube = st.text_input("YouTube Link", value=st.session_state.form_data.get("youtube", ""))
    with u2: open_q = st.text_area("Strategic Core?", value=st.session_state.form_data.get("open_question", ""), height=80)
    st.markdown("</div>", unsafe_allow_html=True)

    if percent >= 100:
        if st.button("Unlock Strategic Recap 👉", type="primary", use_container_width=True):
            st.session_state.form_data.update({"client":client,"project":project,"venue":venue,"category":sel_cat,"what_we_do":sel_wwd,"scope":sel_sow,"open_question":open_q,"youtube":youtube})
            st.session_state.page = 2; st.rerun()
    else:
        st.warning(f"Project incomplete: {percent}%")

# ==========================================
# 5. PAGE 2: STRATEGIC RECAP
# ==========================================
elif st.session_state.page == 2:
    st.markdown('<h1 class="hero-title">Strategic<br>Recap.</h1>', unsafe_allow_html=True)
    if st.button("← Back"): st.session_state.page = 1; st.rerun()

    l, r = st.columns([1.2, 1])
    with l:
        st.markdown('<div class="fb-card">', unsafe_allow_html=True)
        if st.button("📝 GENERATE 15 MC DIAGNOSTICS"):
            with st.spinner("Analyzing Brand + SOW + Photos..."):
                sys = "Output JSON array of 15 diagnostic questions. Analyze PHOTOS for visual quality and SOW for execution. Format: [{'q':'...', 'opts':['A','B','C']}]"
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
        st.markdown('<div class="sec-header">Strategic Terminal</div>', unsafe_allow_html=True)
        log = st.empty()
        if st.button("🚀 EXECUTE MASTER SYNC", type="primary", use_container_width=True):
            log.markdown('<div class="terminal-box">> Analysis Complete.<br>> Mapping Strategic Directions...</div>', unsafe_allow_html=True)
            time.sleep(1)
            payload = {
                **st.session_state.form_data, 
                "category": ", ".join(st.session_state.form_data['category']),
                "what_we_do": ", ".join(st.session_state.form_data['what_we_do']),
                "scope": "\n".join(st.session_state.form_data['scope']),
                "date": datetime.now().strftime("%Y %b").upper()
            }
            res = requests.post(WEB_APP_URL, json=payload)
            if res.status_code == 200:
                log.markdown('<div class="terminal-box">> SYNC SUCCESSFUL.<br>> Master DB Updated.<br>> Ready for Production.</div>', unsafe_allow_html=True)
                st.balloons()
            else: st.error("Sync Failed.")
        st.markdown("</div>", unsafe_allow_html=True)

st.markdown(f"<p style='text-align: center; color: grey; font-size: 10px; text-transform: uppercase; letter-spacing: 2px;'>Firebean Limited | SpeedUp UI v13.0</p>", unsafe_allow_html=True)
