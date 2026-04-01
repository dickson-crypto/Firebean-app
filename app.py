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
APP_VERSION = "v13.3.0"

st.set_page_config(
    page_title=f"Firebean Brain Collector {APP_VERSION}",
    page_icon="🔥",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ==========================================
# 2. SPEEDUP THEME ENGINE (v3)
# ==========================================
if 'page' not in st.session_state: st.session_state.page = 1
if 'form_data' not in st.session_state: st.session_state.form_data = {}
if 'mc_questions' not in st.session_state: st.session_state.mc_questions = []
if 'mock_assets' not in st.session_state: st.session_state.mock_assets = False
if 'dark_mode' not in st.session_state: st.session_state.dark_mode = False 
if 'hero_index' not in st.session_state: st.session_state.hero_index = 0

# SpeedUp Specification Palette
S_RED = "#E2231A"
S_DARK = "#2A2A2A"
S_WHITE = "#FFFFFF"
S_GREY = "#F5F5F5"
S_BG_DARK = "#141414"

t = {
    "bg": S_BG_DARK if st.session_state.dark_mode else S_WHITE,
    "card": "#1E1E1E" if st.session_state.dark_mode else S_GREY,
    "text": "#FFFFFF" if st.session_state.dark_mode else S_DARK,
    "muted": "#999999" if st.session_state.dark_mode else "#777777",
    "border": "#333333" if st.session_state.dark_mode else "#CCCCCC",
    "input_bg": "#1A1A1A" if st.session_state.dark_mode else "#FFFFFF"
}

st.markdown(f"""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@300;400;700;900&display=swap');
        
        .stApp {{ 
            background-color: {t['bg']}; 
            color: {t['text']}; 
            font-family: 'Montserrat', sans-serif;
            transition: background-color 0.6s ease, color 0.6s ease;
        }}

        h1, h2, h3, p, span, label, div, .stMarkdown {{ 
            color: {t['text']} !important; 
        }}

        /* Header Layout: Logo + Title Side-by-Side */
        .header-container {{
            display: flex;
            align-items: center;
            gap: 40px;
            margin-bottom: 60px;
            padding: 30px 0;
        }}

        .hero-title {{
            font-size: 72px !important;
            font-weight: 900 !important;
            line-height: 0.9 !important;
            letter-spacing: -4px !important;
            margin: 0 !important;
        }}

        /* Progress Hub - SpeedUp Style */
        .progress-hub {{ 
            position: fixed; top: 40px; right: 60px; z-index: 1000; 
        }}

        /* SpeedUp Profile Card */
        .fb-card {{
            background: {t['card']};
            border-radius: 32px;
            padding: 50px;
            margin-bottom: 40px;
            border: none;
            transition: all 0.4s ease;
        }}

        /* Section Headlines with Red Bullet */
        .sec-header {{
            font-size: 13px;
            font-weight: 900;
            color: {S_RED} !important;
            text-transform: uppercase;
            letter-spacing: 4px;
            margin-bottom: 25px;
            display: flex;
            align-items: center;
            gap: 15px;
        }}
        
        /* Dotted Line Separator */
        .dotted-sep {{
            border-bottom: 1px dotted {t['border']};
            margin: 30px 0;
            width: 100%;
        }}

        /* Simplified Input Styles */
        .stTextInput input, .stTextArea textarea {{
            background-color: {t['input_bg']} !important;
            border: 1px solid {t['border']} !important;
            border-radius: 8px !important;
            padding: 12px 15px !important;
            font-size: 15px !important;
            color: {t['text']} !important;
        }}
        
        /* Simplified Button */
        .stButton button {{
            border-radius: 100px !important;
            padding: 12px 35px !important;
            font-weight: 900 !important;
            text-transform: uppercase;
            letter-spacing: 2px;
            background-color: {S_RED} !important;
            color: white !important;
            border: none !important;
            font-size: 13px !important;
        }}

        .thumb-box {{
            text-align: center;
            padding: 10px;
            border-radius: 12px;
            background: {t['input_bg']};
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
        "user": '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path><circle cx="12" cy="7" r="4"></circle></svg>',
        "globe": '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="2" y1="12" x2="22" y2="12"></line><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"></path></svg>',
        "briefcase": '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="7" width="20" height="14" rx="2" ry="2"></rect><path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"></path></svg>',
        "image": '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect><circle cx="8.5" cy="8.5" r="1.5"></circle><polyline points="21 15 16 10 5 21"></polyline></svg>'
    }
    return icons.get(name, "")

def render_speedup_progress(percent):
    circum = 251.3
    offset = circum * (1 - percent / 100)
    st.markdown(f"""
    <div class="progress-hub">
        <div style="position:relative; width:100px; height:100px; display:flex; align-items:center; justify-content:center;">
            <svg width="100" height="100">
                <circle stroke="{t['border']}" stroke-width="1" fill="transparent" r="40" cx="50" cy="50"/>
                <circle stroke="{S_RED}" stroke-width="3" stroke-dasharray="{circum}" stroke-dashoffset="{offset}" 
                        stroke-linecap="round" fill="transparent" r="40" cx="50" cy="50" 
                        style="transition: stroke-dashoffset 1.2s cubic-bezier(0.4, 0, 0.2, 1); transform: rotate(-90deg); transform-origin: center;"/>
            </svg>
            <div style="position:absolute; font-size:26px; font-weight:300; color:{t['text']};">{percent}%</div>
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
        "scope": ["Concept Development", "Interactive Installation"],
        "open_question": "Utilizing Swiss design and AI to redefine event recap culture."
    }
    st.session_state.mock_assets = True
    st.rerun()

# ==========================================
# 4. PAGE 1: STRATEGIC COLLECTOR
# ==========================================
STRATEGIC_REQUIRED = ["client", "project", "venue", "category", "what_we_do", "scope", "open_question"]

if st.session_state.page == 1:
    pts = sum(1 for k in STRATEGIC_REQUIRED if st.session_state.form_data.get(k))
    if st.session_state.mock_assets: pts += 2
    else:
        if st.session_state.get('uploaded_logo'): pts += 1
        if st.session_state.get('uploaded_photos'): pts += 1
    
    percent = int((pts / 9) * 100) 
    render_speedup_progress(min(percent, 100))

    # Header with Logo & Large Title
    st.markdown(f"""
        <div class="header-container">
            <img src="https://raw.githubusercontent.com/dickson-crypto/Firebean-app/main/Firebeanlogo2026.png" width="200">
            <h1 class="hero-title">Project<br>Collector.</h1>
        </div>
    """, unsafe_allow_html=True)

    # Theme Toggle
    m1, m2 = st.columns([7, 1])
    with m2:
        lbl = "☀️ LIGHT" if st.session_state.dark_mode else "🌙 DARK"
        if st.button(lbl, use_container_width=True):
            st.session_state.dark_mode = not st.session_state.dark_mode
            st.rerun()

    if st.button("🚀 BOSS TEST MODE", use_container_width=True): run_boss_test()

    # --- CARD 1: IDENTITY ---
    st.markdown('<div class="fb-card">', unsafe_allow_html=True)
    st.markdown(f'<div class="sec-header">{icon_svg("user")} Brand Identity</div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    with c1: client = st.text_input("Client", value=st.session_state.form_data.get("client", ""), placeholder="e.g. Levi's")
    with c2: project = st.text_input("Project", value=st.session_state.form_data.get("project", ""), placeholder="e.g. Pop-up Store")
    with c3: venue = st.text_input("Venue", value=st.session_state.form_data.get("venue", ""), placeholder="Location")
    
    st.markdown('<div class="dotted-sep"></div>', unsafe_allow_html=True)
    
    # Grid Rows
    st.markdown(f'<div class="sec-header">Who we help</div>', unsafe_allow_html=True)
    cat_cols = st.columns(4)
    sel_cat = []
    for i, opt in enumerate(CAT_OPTS):
        with cat_cols[i % 4]:
            if st.checkbox(opt, key=f"c_{opt}", value=(opt in st.session_state.form_data.get("category", []))): sel_cat.append(opt)

    st.markdown('<div class="dotted-sep"></div>', unsafe_allow_html=True)
    st.markdown(f'<div class="sec-header">What we do</div>', unsafe_allow_html=True)
    wwd_cols = st.columns(3)
    sel_wwd = []
    for i, opt in enumerate(WWD_OPTS):
        with wwd_cols[i % 3]:
            if st.checkbox(opt, key=f"w_{opt}", value=(opt in st.session_state.form_data.get("what_we_do", []))): sel_wwd.append(opt)

    st.markdown('<div class="dotted-sep"></div>', unsafe_allow_html=True)
    st.markdown(f'<div class="sec-header">Scope of Work</div>', unsafe_allow_html=True)
    sow_cols = st.columns(3)
    sel_sow = []
    for i, opt in enumerate(SOW_OPTS):
        with sow_cols[i % 3]:
            if st.checkbox(opt, key=f"s_{opt}", value=(opt in st.session_state.form_data.get("scope", []))): sel_sow.append(opt)
    st.markdown('</div>', unsafe_allow_html=True)

    # --- CARD 2: ASSETS ---
    st.markdown('<div class="fb-card">', unsafe_allow_html=True)
    st.markdown(f'<div class="sec-header">{icon_svg("image")} Visual Assets Hub</div>', unsafe_allow_html=True)
    
    a1, a2 = st.columns(2)
    with a1:
        logo_b = st.file_uploader("Logo Black", key="logo_b")
        if logo_b: st.session_state.uploaded_logo = True
    with a2:
        logo_w = st.file_uploader("Logo White", key="logo_w")
        if logo_w: st.session_state.uploaded_logo = True

    st.markdown('<div class="dotted-sep"></div>', unsafe_allow_html=True)
    st.write("**Project Gallery** (Designate Hero Photo)")
    photos = st.file_uploader("Drop Gallery Files", accept_multiple_files=True, key="photos")
    
    if photos:
        st.session_state.uploaded_photos = True
        cols = st.columns(4)
        img_previews = []
        for idx, p in enumerate(photos[:8]):
            with cols[idx % 4]:
                st.markdown(f'<div class="thumb-box">', unsafe_allow_html=True)
                img = Image.open(p)
                st.image(img, use_container_width=True)
                # Hero Logic
                if st.checkbox("HERO", key=f"hero_{idx}", value=(st.session_state.hero_index == idx)):
                    st.session_state.hero_index = idx
                st.markdown('</div>', unsafe_allow_html=True)
                # Save for AI
                buf = io.BytesIO()
                img.save(buf, format='PNG')
                img_previews.append(base64.b64encode(buf.getvalue()).decode('utf-8'))
        st.session_state.photos_for_ai = img_previews
    st.markdown('</div>', unsafe_allow_html=True)

    # --- CARD 3: CORE ---
    st.markdown('<div class="fb-card">', unsafe_allow_html=True)
    st.markdown(f'<div class="sec-header">{icon_svg("briefcase")} Strategic Core</div>', unsafe_allow_html=True)
    u1, u2 = st.columns([1, 2])
    with u1: youtube = st.text_input("YouTube (Optional)")
    with u2: open_q = st.text_area("Concept Goal?", value=st.session_state.form_data.get("open_question", ""), height=100)
    st.markdown('</div>', unsafe_allow_html=True)

    if percent >= 100:
        if st.button("Generate Strategic Recap 👉", type="primary", use_container_width=True):
            st.session_state.form_data.update({"client":client,"project":project,"venue":venue,"category":sel_cat,"what_we_do":sel_wwd,"scope":sel_sow,"open_question":open_q,"youtube":youtube})
            st.session_state.page = 2; st.rerun()
    else:
        st.warning(f"Incomplete: {percent}%")

# ==========================================
# 5. PAGE 2: STRATEGIC RECAP
# ==========================================
elif st.session_state.page == 2:
    st.markdown(f"""
        <div class="header-container">
            <img src="https://raw.githubusercontent.com/dickson-crypto/Firebeanlogo2026.png" width="200">
            <h1 class="hero-title">Strategic<br>Recap.</h1>
        </div>
    """, unsafe_allow_html=True)
    if st.button("← Back"): st.session_state.page = 1; st.rerun()

    l, r = st.columns([1.2, 1])
    with l:
        st.markdown('<div class="fb-card">', unsafe_allow_html=True)
        if st.button("📝 RUN AI DIAGNOSTICS"):
            with st.spinner("Analyzing Brand + Scope + Visuals..."):
                sys = "Output JSON array of 15 diagnostic questions. Format: [{'q':'...', 'opts':['A','B','C']}]"
                ctx = f"Client: {st.session_state.form_data['client']}. SOW: {', '.join(st.session_state.form_data['scope'])}. Core: {st.session_state.form_data['open_question']}"
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
            log.markdown('<div class="terminal-box">> Initializing SpeedUp Sync v13.3...<br>> Mapping Brand Strategy...</div>', unsafe_allow_html=True)
            time.sleep(1)
            payload = {**st.session_state.form_data, "category": ", ".join(st.session_state.form_data['category']), "what_we_do": ", ".join(st.session_state.form_data['what_we_do']), "scope": "\n".join(st.session_state.form_data['scope']), "date": datetime.now().strftime("%Y %b").upper()}
            res = requests.post(WEB_APP_URL, json=payload)
            if res.status_code == 200:
                log.markdown('<div class="terminal-box">> SYNC SUCCESSFUL.<br>> Master DB Updated.<br>> GitHub Sync Ready.</div>', unsafe_allow_html=True)
                st.balloons()
            else: st.error("Database Sync Failed.")
        st.markdown("</div>", unsafe_allow_html=True)

st.markdown(f"<p style='text-align: center; color: grey; font-size: 10px; letter-spacing: 2px; text-transform: uppercase;'>FIREBEAN LIMITED | SPEEDUP UI v13.3</p>", unsafe_allow_html=True)
