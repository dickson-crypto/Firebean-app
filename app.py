import streamlit as st
import requests
import json
import time
import random
from PIL import Image, ImageOps
from datetime import datetime

# 🚀 iPhone HEIC Support
try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
except ImportError:
    pass

# ==========================================
# 1. CONFIGURATION & NEON STYLING
# ==========================================
WEB_APP_URL = "https://script.google.com/macros/s/AKfycbyCfSfjgYi7yQFpqBDshjYQ1Zye4VjaT-U4_0nfF9c5oYF1Pr0CrGI38Is4BS3KigIz/exec"
apiKey = "" 
APP_VERSION = "v12.3.0"

st.set_page_config(
    page_title=f"Firebean Brain Collector {APP_VERSION}",
    page_icon="🔥",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS: Neon Progress + Adaptive Neumorphic UI
st.markdown("""
    <style>
        [data-testid="stSidebar"] {display: none;}
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}

        /* Neon Red Progress Hub (Fixed Top Right) */
        .progress-hub {
            position: fixed;
            top: 25px;
            right: 40px;
            z-index: 1000;
        }

        /* Neumorphic Card Styling */
        .neu-card {
            border-radius: 20px;
            padding: 30px;
            margin-bottom: 25px;
            background: #f0f0f0;
            box-shadow: 12px 12px 24px #bebebe, -12px -12px 24px #ffffff;
            border: 1px solid rgba(255,255,255,0.2);
        }

        @media (prefers-color-scheme: dark) {
            .neu-card {
                background: #1e2128;
                box-shadow: 10px 10px 20px #15171c, -5px -5px 15px #272b34;
            }
        }

        /* Section Headers from Screenshot */
        .sec-header {
            color: #FF4B4B;
            font-weight: 900;
            text-transform: uppercase;
            letter-spacing: 2px;
            border-left: 5px solid #FF4B4B;
            padding-left: 15px;
            margin: 25px 0 15px 0;
            font-size: 0.95rem;
        }

        /* Terminal Box */
        .terminal-box {
            background: #000;
            color: #39ff14;
            font-family: 'Courier New', monospace;
            padding: 15px;
            border-radius: 12px;
            font-size: 12px;
            line-height: 1.6;
            border: 1px solid #333;
            box-shadow: inset 0 0 10px #000;
        }

        /* Neon Circle Pulse */
        @keyframes neonPulse {
            0% { filter: drop-shadow(0 0 2px #FF0000); opacity: 0.8; }
            50% { filter: drop-shadow(0 0 12px #FF0000); opacity: 1; }
            100% { filter: drop-shadow(0 0 2px #FF0000); opacity: 0.8; }
        }
        .neon-svg { animation: neonPulse 2.5s infinite ease-in-out; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. UI UTILITIES
# ==========================================
def render_neon_progress(percent):
    circum = 282.7 # 2 * PI * 45
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

def call_gemini_ai(prompt, sys_prompt):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-09-2025:generateContent?key={apiKey}"
    payload = {"contents": [{"parts": [{"text": prompt}]}], "systemInstruction": {"parts": [{"text": sys_prompt}]}, "generationConfig": {"responseMimeType": "application/json"}}
    try:
        res = requests.post(url, json=payload, timeout=60)
        if res.status_code == 200: return res.json()['candidates'][0]['content']['parts'][0]['text']
    except: pass
    return None

# ==========================================
# 3. APP STATE & BOSS TEST
# ==========================================
if 'page' not in st.session_state: st.session_state.page = 1
if 'form_data' not in st.session_state: st.session_state.form_data = {}
if 'mc_questions' not in st.session_state: st.session_state.mc_questions = []
if 'mock_assets' not in st.session_state: st.session_state.mock_assets = False

CAT_OPTS = ["GOVERNMENT & PUBLIC SECTOR", "LIFESTYLE & CONSUMER", "F&B & HOSPITALITY", "MALLS & VENUES"]
WWD_OPTS = ["ROVING EXHIBITIONS", "SOCIAL & CONTENT", "INTERACTIVE & TECH", "PR & MEDIA", "EVENTS & CEREMONIES"]
SOW_OPTS = ["Event Planning", "Event Production", "Theme Design", "Concept Development", "PR Consulting"]

def run_boss_test():
    st.session_state.form_data = {
        "client": "Firebean HQ", "project": "Strategic Neumorphic Portfolio", "venue": "Digital Hub HK",
        "category": ["LIFESTYLE & CONSUMER", "GOVERNMENT & PUBLIC SECTOR"],
        "what_we_do": ["SOCIAL & CONTENT", "INTERACTIVE & TECH"],
        "scope": ["Event Planning", "Concept Development"],
        "drive_folder": "https://drive.google.com/mock_folder",
        "open_question": "How can we leverage Gemini 2.5 to transform project data into SEO-optimized case studies?"
    }
    st.session_state.mock_assets = True
    st.rerun()

# ==========================================
# 4. PAGE 1: SMART COLLECTOR
# ==========================================
# Mandatory Fields for Progress
STRATEGIC_REQUIRED = ["client", "project", "venue", "category", "what_we_do", "scope", "drive_folder", "open_question"]

if st.session_state.page == 1:
    # 1. Calculate Progress
    points = sum(1 for k in STRATEGIC_REQUIRED if st.session_state.form_data.get(k))
    # Asset points
    if st.session_state.mock_assets: points += 2
    else:
        if st.session_state.get('uploaded_logo'): points += 1
        if st.session_state.get('uploaded_photos'): points += 1
    
    percent = int((points / 10) * 100)
    render_neon_progress(min(percent, 100))

    st.image("https://raw.githubusercontent.com/dickson-crypto/Firebean-app/main/Firebeanlogo2026.png", width=340)
    
    if st.button("🚀 BOSS TEST MODE (1-Click Populate)", use_container_width=True): run_boss_test()

    st.markdown('<div class="neu-card">', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    with c1: client = st.text_input("Client", value=st.session_state.form_data.get("client", ""))
    with c2: project = st.text_input("Project Name", value=st.session_state.form_data.get("project", ""))
    with c3: venue = st.text_input("Venue", value=st.session_state.form_data.get("venue", ""))
    
    st.markdown("---")
    g1, g2, g3 = st.columns(3)
    with g1:
        st.markdown('<div class="sec-header">Category</div>', unsafe_allow_html=True)
        sel_cat = [o for o in CAT_OPTS if st.checkbox(o, key=f"c_{o}", value=(o in st.session_state.form_data.get("category", [])))]
    with g2:
        st.markdown('<div class="sec-header">What We Do</div>', unsafe_allow_html=True)
        sel_wwd = [o for o in WWD_OPTS if st.checkbox(o, key=f"w_{o}", value=(o in st.session_state.form_data.get("what_we_do", [])))]
    with g3:
        st.markdown('<div class="sec-header">Scope of Work</div>', unsafe_allow_html=True)
        sel_sow = [o for o in SOW_OPTS if st.checkbox(o, key=f"s_{o}", value=(o in st.session_state.form_data.get("scope", [])))]

    st.markdown("---")
    d1, d2 = st.columns([2, 1])
    with d1: drive = st.text_input("Google Drive Folder URL (Mandatory)", value=st.session_state.form_data.get("drive_folder", ""))
    with d2: youtube = st.text_input("YouTube URL (Optional)", value=st.session_state.form_data.get("youtube", ""))

    st.markdown('<div class="sec-header">Visual Assets Hub</div>', unsafe_allow_html=True)
    a1, a2 = st.columns([1, 2])
    with a1:
        logo_b = st.file_uploader("Logo Black", key="logo_b")
        logo_w = st.file_uploader("Logo White", key="logo_w")
        if logo_b or logo_w: st.session_state.uploaded_logo = True
    with a2:
        photos = st.file_uploader("Gallery (Up to 8)", accept_multiple_files=True, key="photos")
        if photos: st.session_state.uploaded_photos = True

    st.markdown("---")
    open_q = st.text_area("核心戰略概念？", value=st.session_state.form_data.get("open_question", ""), height=120)
    st.markdown("</div>", unsafe_allow_html=True)

    if percent >= 100:
        if st.button("Unlock Strategic Recap 👉", type="primary", use_container_width=True):
            st.session_state.form_data.update({"client":client,"project":project,"venue":venue,"category":sel_cat,"what_we_do":sel_wwd,"scope":sel_sow,"drive_folder":drive,"open_question":open_q,"youtube":youtube})
            st.session_state.page = 2; st.rerun()
    else:
        st.warning(f"Complete all mandatory inputs to reach 100% ({percent}% reached)")

# ==========================================
# 5. PAGE 2: DIAGNOSTIC & SYNC
# ==========================================
elif st.session_state.page == 2:
    st.title("Step 2: Strategic Recap & Sync")
    if st.button("← Back"): st.session_state.page = 1; st.rerun()

    l, r = st.columns([1.2, 1])
    with l:
        st.markdown('<div class="neu-card">', unsafe_allow_html=True)
        if st.button("📝 生成 15 題專業 PR 診斷"):
            sys = "Output JSON. Generate 15 diagnostic questions. [{'q': '...', 'opts': ['A','B','C']}]"
            res = call_gemini_ai(f"Project: {st.session_state.form_data['project']}", sys)
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
            log.markdown('<div class="terminal-box">> Selected Style: Analytical<br>> Mapping Cols 1-30...</div>', unsafe_allow_html=True)
            time.sleep(1)
            # Sync Payload for existing Handlers.gs
            payload = {
                **st.session_state.form_data, 
                "category": ", ".join(st.session_state.form_data['category']),
                "what_we_do": ", ".join(st.session_state.form_data['what_we_do']),
                "scope": "\n".join(st.session_state.form_data['scope']),
                "date": datetime.now().strftime("%Y %b").upper()
            }
            res = requests.post(WEB_APP_URL, json=payload)
            if res.status_code == 200:
                log.markdown('<div class="terminal-box">> SYNC SUCCESSFUL.<br>> Master DB Updated.</div>', unsafe_allow_html=True)
                st.balloons()
            else: st.error("Sync Failed.")
        st.markdown("</div>", unsafe_allow_html=True)

st.markdown(f"<p style='text-align: center; color: grey; font-size: 10px;'>Firebean Limited | HQ Strategic Hub {APP_VERSION}</p>", unsafe_allow_html=True)
