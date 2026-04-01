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
APP_VERSION = "v12.8.0"

st.set_page_config(
    page_title=f"Firebean Brain Collector {APP_VERSION}",
    page_icon="🔥",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ==========================================
# 2. STATE & THEME ENGINE (Full Screen Change)
# ==========================================
if 'page' not in st.session_state: st.session_state.page = 1
if 'form_data' not in st.session_state: st.session_state.form_data = {}
if 'mc_questions' not in st.session_state: st.session_state.mc_questions = []
if 'mock_assets' not in st.session_state: st.session_state.mock_assets = False
if 'dark_mode' not in st.session_state: st.session_state.dark_mode = True

theme = {
    "bg": "#121418" if st.session_state.dark_mode else "#e0e5ec",
    "card": "#1e2128" if st.session_state.dark_mode else "#f0f2f6",
    "text": "#ffffff" if st.session_state.dark_mode else "#2d3436",
    "shadow": "8px 8px 16px #0b0d10, -4px -4px 12px #272b34" if st.session_state.dark_mode else "10px 10px 20px #a3b1c6, -10px -10px 20px #ffffff",
    "input": "#262932" if st.session_state.dark_mode else "#ffffff",
    "border": "#2d323b" if st.session_state.dark_mode else "#d1d9e6"
}

st.markdown(f"""
    <style>
        .stApp {{ background-color: {theme['bg']}; color: {theme['text']}; transition: all 0.5s ease; }}
        h1, h2, h3, h4, h5, h6, p, span, label, div {{ color: {theme['text']} !important; }}
        [data-testid="stSidebar"] {{display: none;}}
        #MainMenu {{visibility: hidden;}}
        footer {{visibility: hidden;}}
        header {{visibility: hidden;}}

        .progress-hub {{ position: fixed; top: 25px; right: 40px; z-index: 1000; }}
        
        .neu-card {{
            border-radius: 24px; padding: 35px; margin-bottom: 30px;
            background: {theme['card']};
            box-shadow: {theme['shadow']};
            border: 1px solid {theme['border']};
            transition: all 0.5s ease;
        }}

        .stTextInput input, .stTextArea textarea {{
            background-color: {theme['input']} !important;
            color: {theme['text']} !important;
            border: 1px solid {theme['border']} !important;
            border-radius: 12px !important;
        }}

        .sec-header {{
            color: #FF4B4B !important; font-weight: 900; text-transform: uppercase; letter-spacing: 2px;
            border-left: 5px solid #FF4B4B; padding-left: 15px; margin: 25px 0 15px 0; font-size: 0.95rem;
        }}

        .terminal-box {{
            background: #000; color: #39ff14; font-family: 'Courier New', monospace;
            padding: 15px; border-radius: 12px; font-size: 12px; line-height: 1.6;
            border: 1px solid #333; box-shadow: inset 0 0 10px #000;
        }}

        @keyframes neonPulse {{
            0% {{ filter: drop-shadow(0 0 2px #FF0000); opacity: 0.8; }}
            50% {{ filter: drop-shadow(0 0 12px #FF0000); opacity: 1; }}
            100% {{ filter: drop-shadow(0 0 2px #FF0000); opacity: 0.8; }}
        }}
        .neon-svg {{ animation: neonPulse 2.5s infinite ease-in-out; }}
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 3. UTILITIES
# ==========================================
def render_neon_progress(percent):
    circum = 282.7 
    offset = circum * (1 - percent / 100)
    st.markdown(f"""
    <div class="progress-hub">
        <div style="position:relative; width:110px; height:110px; display:flex; align-items:center; justify-content:center;">
            <svg width="110" height="110" class="neon-svg">
                <circle stroke="rgba(255,0,0,0.1)" stroke-width="10" fill="transparent" r="45" cx="55" cy="55"/>
                <circle stroke="#FF0000" stroke-width="10" stroke-dasharray="{circum}" stroke-dashoffset="{offset}" 
                        stroke-linecap="round" fill="transparent" r="45" cx="55" cy="55" 
                        style="transition: stroke-dashoffset 1s; transform: rotate(-90deg); transform-origin: center;"/>
            </svg>
            <div style="position:absolute; font-size:24px; font-weight:900; color:#FF0000; text-shadow: 0 0 8px rgba(255,0,0,0.6);">{percent}%</div>
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

# Expanded SOW Guidelines
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
        "client": "Firebean HQ", "project": "Strategic Neumorphic Hub", "venue": "Cyberport",
        "category": ["LIFESTYLE & CONSUMER"], "what_we_do": ["INTERACTIVE & TECH"],
        "scope": ["Concept Development", "Interactive Installation", "Technical Support"],
        "open_question": "How to utilize AI to transform static PR data into a 24/7 lead generation engine?"
    }
    st.session_state.mock_assets = True
    st.rerun()

# ==========================================
# 4. PAGE 1: SMART COLLECTOR
# ==========================================
STRATEGIC_REQUIRED = ["client", "project", "venue", "category", "what_we_do", "scope", "open_question"]

if st.session_state.page == 1:
    points = sum(1 for k in STRATEGIC_REQUIRED if st.session_state.form_data.get(k))
    if st.session_state.mock_assets: points += 2
    else:
        if st.session_state.get('uploaded_logo'): points += 1
        if st.session_state.get('uploaded_photos'): points += 1
    
    percent = int((points / 9) * 100) 
    render_neon_progress(min(percent, 100))

    top_l, top_r = st.columns([4, 1])
    with top_l: st.image("https://raw.githubusercontent.com/dickson-crypto/Firebean-app/main/Firebeanlogo2026.png", width=340)
    with top_r:
        label = "☀️ Light" if st.session_state.dark_mode else "🌙 Dark"
        if st.button(label, use_container_width=True):
            st.session_state.dark_mode = not st.session_state.dark_mode
            st.rerun()

    if st.button("🚀 BOSS TEST MODE", use_container_width=True): run_boss_test()

    st.markdown('<div class="neu-card">', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    with c1: client = st.text_input("Client", value=st.session_state.form_data.get("client", ""), placeholder="e.g. Levi's")
    with c2: project = st.text_input("Project Name", value=st.session_state.form_data.get("project", ""), placeholder="e.g. Pop-up Store")
    with c3: venue = st.text_input("Venue", value=st.session_state.form_data.get("venue", ""), placeholder="e.g. Times Square")
    
    st.markdown("---")
    g1, g2, g3 = st.columns(3)
    with g1:
        st.markdown('<div class="sec-header">Who we help</div>', unsafe_allow_html=True)
        sel_cat = [o for o in CAT_OPTS if st.checkbox(o, key=f"c_{o}", value=(o in st.session_state.form_data.get("category", [])))]
    with g2:
        st.markdown('<div class="sec-header">What we do</div>', unsafe_allow_html=True)
        sel_wwd = [o for o in WWD_OPTS if st.checkbox(o, key=f"w_{o}", value=(o in st.session_state.form_data.get("what_we_do", [])))]
    with g3:
        st.markdown('<div class="sec-header">Scope of Work</div>', unsafe_allow_html=True)
        sel_sow = [o for o in SOW_OPTS if st.checkbox(o, key=f"s_{o}", value=(o in st.session_state.form_data.get("scope", [])))]

    st.markdown("---")
    st.markdown('<div class="sec-header">Visual Assets</div>', unsafe_allow_html=True)
    a1, a2, a3 = st.columns([1, 1, 2])
    with a1:
        logo_b = st.file_uploader("Logo Black", key="logo_b")
        if logo_b: st.session_state.uploaded_logo = True
    with a2:
        logo_w = st.file_uploader("Logo White", key="logo_w")
        if logo_w: st.session_state.uploaded_logo = True
    with a3:
        photos = st.file_uploader("Gallery", accept_multiple_files=True, key="photos")
        if photos: 
            st.session_state.uploaded_photos = True
            img_list = []
            for p in photos[:4]:
                img_list.append(base64.b64encode(p.read()).decode('utf-8'))
            st.session_state.photos_for_ai = img_list

    st.markdown("---")
    u1, u2 = st.columns([1, 2])
    with u1: youtube = st.text_input("YouTube URL (Optional)", value=st.session_state.form_data.get("youtube", ""))
    with u2: open_q = st.text_area("核心戰略概念？", value=st.session_state.form_data.get("open_question", ""), height=80)
    st.markdown("</div>", unsafe_allow_html=True)

    if percent >= 100:
        if st.button("Unlock AI Diagnostic Suite 👉", type="primary", use_container_width=True):
            st.session_state.form_data.update({"client":client,"project":project,"venue":venue,"category":sel_cat,"what_we_do":sel_wwd,"scope":sel_sow,"open_question":open_q,"youtube":youtube})
            st.session_state.page = 2; st.rerun()
    else:
        st.warning(f"Incomplete: {percent}%")

# ==========================================
# 5. PAGE 2: DIAGNOSTIC & SYNC
# ==========================================
elif st.session_state.page == 2:
    st.title("Step 2: Multimodal Diagnostics")
    if st.button("← Back"): st.session_state.page = 1; st.rerun()

    l, r = st.columns([1.2, 1])
    with l:
        st.markdown('<div class="neu-card">', unsafe_allow_html=True)
        if st.button("📝 生成 15 題專業 PR 診斷"):
            with st.spinner("AI is analyzing Brand + SOW + Photos..."):
                sys = "Output JSON array of 15 diagnostic questions. Guidelines: Analyze PHOTOS for visual quality, SOW for operational depth, and Brand for positioning. Format: [{'q':'...', 'opts':['A','B','C']}]"
                ctx = f"Brand: {st.session_state.form_data['client']}. SOW: {', '.join(st.session_state.form_data['scope'])}. Concept: {st.session_state.form_data['open_question']}"
                res = call_gemini_ai(ctx, sys, st.session_state.get('photos_for_ai'))
                if res: st.session_state.mc_questions = json.loads(res.replace("```json", "").replace("```", ""))
        if st.session_state.mc_questions:
            for i, q in enumerate(st.session_state.mc_questions):
                st.markdown(f'<div class="sec-header">Q{i+1}. {q["q"]}</div>', unsafe_allow_html=True)
                for opt in q["opts"]: st.checkbox(opt, key=f"mc_{i}_{opt}")
        st.markdown("</div>", unsafe_allow_html=True)

    with r:
        st.markdown('<div class="neu-card">', unsafe_allow_html=True)
        st.markdown('<div class="sec-header">Strategic Terminal</div>', unsafe_allow_html=True)
        log = st.empty()
        if st.button("🚀 EXECUTE MASTER SYNC", type="primary", use_container_width=True):
            log.markdown('<div class="terminal-box">> Analysis Complete.<br>> Syncing Expanded SOW to Master DB...</div>', unsafe_allow_html=True)
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
                log.markdown('<div class="terminal-box">> SYNC SUCCESSFUL.<br>> Data Mapped to Column 8.<br>> GitHub Sync Ready.</div>', unsafe_allow_html=True)
                st.balloons()
            else: st.error("Sync Failed.")
        st.markdown("</div>", unsafe_allow_html=True)

st.markdown(f"<p style='text-align: center; color: grey; font-size: 10px;'>Firebean Limited | Multimodal Strategic Hub {APP_VERSION}</p>", unsafe_allow_html=True)
