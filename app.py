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
APP_VERSION = "v13.6.1"

st.set_page_config(
    page_title=f"Firebean Brain Collector {APP_VERSION}",
    page_icon="🔥",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ==========================================
# 2. SPEEDUP THEME ENGINE
# ==========================================
if 'page' not in st.session_state: st.session_state.page = 1
if 'form_data' not in st.session_state: st.session_state.form_data = {}
if 'mc_questions' not in st.session_state: st.session_state.mc_questions = []
if 'mock_assets' not in st.session_state: st.session_state.mock_assets = False
if 'dark_mode' not in st.session_state: st.session_state.dark_mode = False 
if 'hero_index' not in st.session_state: st.session_state.hero_index = 0
if 'generated_content' not in st.session_state: st.session_state.generated_content = None
if 'sync_complete' not in st.session_state: st.session_state.sync_complete = False

# SpeedUp Specification Palette
S_RED = "#E2231A"
S_DARK = "#2A2A2A"
S_WHITE = "#FFFFFF"
S_GREY = "#F9F9F9"
S_BG_DARK = "#121212"

t = {
    "bg": S_BG_DARK if st.session_state.dark_mode else S_WHITE,
    "text": "#FFFFFF" if st.session_state.dark_mode else S_DARK,
    "muted": "#888888" if st.session_state.dark_mode else "#666666",
    "border": "#333333" if st.session_state.dark_mode else "#DDDDDD",
    "input_bg": "#1A1A1A" if st.session_state.dark_mode else "#FFFFFF",
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

        h1, h2, h3, p, span, label, div, .stMarkdown {{ color: {t['text']} !important; }}

        .header-container {{ display: flex; align-items: center; gap: 25px; padding: 20px 0; margin-bottom: 10px; }}
        .hero-title {{ font-size: 56px !important; font-weight: 900 !important; line-height: 0.85 !important; letter-spacing: -3px !important; margin: 0 !important; }}
        .dotted-sep {{ border-bottom: 1px dotted {t['border']}; margin: 25px 0; width: 100%; }}

        .stTextInput input, .stTextArea textarea, .stSelectbox div[data-baseweb="select"] {{
            background-color: {t['input_bg']} !important;
            border: 1px solid {t['border']} !important;
            border-radius: 6px !important;
            padding: 10px 14px !important;
            font-size: 14px !important;
            color: {t['text']} !important;
            box-shadow: none !important;
        }}
        
        .sec-header {{
            font-size: 16px; font-weight: 900; color: {S_RED} !important; text-transform: uppercase;
            letter-spacing: 2px; margin-bottom: 15px; display: flex; align-items: center; gap: 12px;
        }}

        .progress-hub {{ position: fixed; top: 25px; right: 40px; z-index: 1000; }}

        .stButton button {{
            border-radius: 50px !important; padding: 8px 20px !important; font-weight: 700 !important;
            text-transform: uppercase; letter-spacing: 1px; border: none !important; font-size: 11px !important;
        }}
        .boss-btn button {{ background-color: {t['text']} !important; color: {t['bg']} !important; }}
        .next-btn button {{ background-color: {S_RED} !important; color: white !important; font-size: 14px !important; padding: 12px 40px !important; }}
        .success-box {{ padding: 30px; border-radius: 12px; border: 2px solid {S_RED}; text-align: center; background: {t['input_bg']}; }}

        [data-testid="stSidebar"] {{display: none;}}
        header {{visibility: hidden;}}
        footer {{visibility: hidden;}}
        .block-container {{ padding-top: 1rem !important; padding-bottom: 1rem !important; }}
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 3. UTILITIES & VECTOR ICONS
# ==========================================
def icon_svg(name):
    icons = {
        "user": '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path><circle cx="12" cy="7" r="4"></circle></svg>',
        "framework": '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="2" y1="12" x2="22" y2="12"></line><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1 4-10z"></path></svg>',
        "assets": '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect><circle cx="8.5" cy="8.5" r="1.5"></circle><polyline points="21 15 16 10 5 21"></polyline></svg>',
        "core": '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="7" width="20" height="14" rx="2" ry="2"></rect><path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"></path></svg>'
    }
    return icons.get(name, "")

def render_speedup_progress(percent):
    circum = 251.3
    offset = circum * (1 - percent / 100)
    st.markdown(f"""
    <div class="progress-hub">
        <div style="position:relative; width:90px; height:90px; display:flex; align-items:center; justify-content:center;">
            <svg width="90" height="90">
                <circle stroke="{t['border']}" stroke-width="1" fill="transparent" r="35" cx="45" cy="45"/>
                <circle stroke="{S_RED}" stroke-width="2" stroke-dasharray="{circum}" stroke-dashoffset="{offset}" 
                        stroke-linecap="round" fill="transparent" r="35" cx="45" cy="45" 
                        style="transition: stroke-dashoffset 1s ease-out; transform: rotate(-90deg); transform-origin: center;"/>
            </svg>
            <div style="position:absolute; font-size:22px; font-weight:300; color:{t['text']};">{percent}%</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

def call_gemini_ai(prompt, sys_prompt, image_blobs=None):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-09-2025:generateContent?key={apiKey}"
    parts = [{"text": prompt}]
    if image_blobs:
        for b in image_blobs[:4]: parts.append({"inline_data": {"mime_type": "image/png", "data": b}})
    payload = {"contents": [{"parts": parts}], "systemInstruction": {"parts": [{"text": sys_prompt}]}, "generationConfig": {"responseMimeType": "application/json"}}
    try:
        res = requests.post(url, json=payload, timeout=60)
        return res.json()['candidates'][0]['content']['parts'][0]['text']
    except: return None

CAT_OPTS = ["GOVERNMENT & PUBLIC SECTOR", "LIFESTYLE & CONSUMER", "F&B & HOSPITALITY", "MALLS & VENUES"]
WWD_OPTS = ["ROVING EXHIBITIONS", "SOCIAL & CONTENT", "INTERACTIVE & TECH", "PR & MEDIA", "EVENTS & CEREMONIES"]
SOW_OPTS = ["Concept Development", "Branding Strategy", "PR Consulting", "Media Relations", "Theme Design", "Visual Identity", "UI/UX Design", "Social Media Content", "Influencer Seeding", "Video Production", "Motion Graphics", "Interactive Installation", "Event Planning", "Event Production", "RSVP Management", "Talent Management", "On-site Operation", "Technical Support"]

def run_boss_test():
    st.session_state.form_data = {
        "client": "Firebean HQ", "project": "Strategic Digital Hub", "venue": "Cyberport",
        "year": "2026", "month": "APR",
        "category": ["LIFESTYLE & CONSUMER"], "what_we_do": ["INTERACTIVE & TECH"],
        "scope": ["Concept Development", "Interactive Installation"],
        "drive_folder": "https://drive.google.com/drive/folders/mock-folder-id",
        "open_question": "Redefining portfolio culture through AI synthesis."
    }
    st.session_state.mock_assets = True
    st.rerun()

# ==========================================
# 4. PAGE 1: STRATEGIC COLLECTOR
# ==========================================
# Added drive_folder back to mandatory fields to guarantee Main.gs integration
STRATEGIC_REQUIRED = ["client", "project", "venue", "category", "what_we_do", "scope", "drive_folder", "open_question"]

if st.session_state.page == 1:
    # --- PROGRESS CALCULATION (Max 11 points = 100%) ---
    pts = sum(1 for k in STRATEGIC_REQUIRED if st.session_state.form_data.get(k)) # Max 8
    if st.session_state.mock_assets: pts += 2
    else:
        if st.session_state.get('uploaded_logo'): pts += 1
        if st.session_state.get('uploaded_photos'): pts += 1 # Max 10 (90%)

    answered_mc = False
    if st.session_state.mc_questions:
        for i, q in enumerate(st.session_state.mc_questions):
            for opt in q["opts"]:
                if st.session_state.get(f"mc_{i}_{opt}", False): answered_mc = True
    if answered_mc or (st.session_state.mock_assets and st.session_state.mc_questions):
        pts += 1 # Max 11 (100%)
    
    percent = int((pts / 11) * 100) 
    render_speedup_progress(min(percent, 100))

    # Header Row
    h_col1, h_col2, h_col3, h_col4 = st.columns([1.5, 4, 0.8, 0.8])
    with h_col1: st.image("https://raw.githubusercontent.com/dickson-crypto/Firebean-app/main/Firebeanlogo2026.png", use_container_width=True)
    with h_col2: st.markdown('<h1 class="hero-title">Project Collector.</h1>', unsafe_allow_html=True)
    with h_col3:
        st.markdown('<div class="boss-btn">', unsafe_allow_html=True)
        if st.button("🚀 BOSS", use_container_width=True): run_boss_test()
        st.markdown('</div>', unsafe_allow_html=True)
    with h_col4:
        if st.button("☀️" if st.session_state.dark_mode else "🌙", use_container_width=True):
            st.session_state.dark_mode = not st.session_state.dark_mode
            st.rerun()

    st.markdown('<div style="margin-top:20px;"></div>', unsafe_allow_html=True)

    # --- SESSION: IDENTITY ---
    st.markdown(f'<div class="sec-header">{icon_svg("user")} Brand Identity</div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    with c1: client = st.text_input("Client", value=st.session_state.form_data.get("client", ""), placeholder="e.g. Levi's")
    with c2: project = st.text_input("Project", value=st.session_state.form_data.get("project", ""), placeholder="e.g. Pop-up")
    with c3: venue = st.text_input("Venue", value=st.session_state.form_data.get("venue", ""), placeholder="Location")
    
    d1, d2, d3 = st.columns([1, 1, 2])
    current_year = st.session_state.form_data.get("year", "2026")
    current_month = st.session_state.form_data.get("month", datetime.now().strftime("%b").upper())
    months_list = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]
    with d1: year = st.selectbox("Year", [str(y) for y in range(2026, 2011, -1)], index=[str(y) for y in range(2026, 2011, -1)].index(current_year))
    with d2: month = st.selectbox("Month", months_list, index=months_list.index(current_month) if current_month in months_list else 0)

    st.markdown('<div class="dotted-sep"></div>', unsafe_allow_html=True)

    # --- SESSION: FRAMEWORK ---
    st.markdown(f'<div class="sec-header">{icon_svg("framework")} Strategic Framework</div>', unsafe_allow_html=True)
    cat_cols = st.columns(4)
    sel_cat = [opt for i, opt in enumerate(CAT_OPTS) if cat_cols[i%4].checkbox(opt, key=f"c_{opt}", value=(opt in st.session_state.form_data.get("category", [])))]
    st.write("<br>", unsafe_allow_html=True)
    wwd_cols = st.columns(3)
    sel_wwd = [opt for i, opt in enumerate(WWD_OPTS) if wwd_cols[i%3].checkbox(opt, key=f"w_{opt}", value=(opt in st.session_state.form_data.get("what_we_do", [])))]
    st.write("<br>", unsafe_allow_html=True)
    sow_cols = st.columns(3)
    sel_sow = [opt for i, opt in enumerate(SOW_OPTS) if sow_cols[i%3].checkbox(opt, key=f"s_{opt}", value=(opt in st.session_state.form_data.get("scope", [])))]

    st.markdown('<div class="dotted-sep"></div>', unsafe_allow_html=True)

    # --- SESSION: ASSETS ---
    st.markdown(f'<div class="sec-header">{icon_svg("assets")} Visual Assets Hub</div>', unsafe_allow_html=True)
    a1, a2, a3 = st.columns([1, 1, 2])
    with a1:
        logo_b = st.file_uploader("Logo Black", key="logo_b")
        if logo_b: st.session_state.uploaded_logo = True
    with a2:
        logo_w = st.file_uploader("Logo White", key="logo_w")
        if logo_w: st.session_state.uploaded_logo = True
    with a3:
        drive_folder = st.text_input("Drive Folder URL (Required for GitHub Sync)", value=st.session_state.form_data.get("drive_folder", ""), placeholder="https://drive.google.com/drive/folders/...")
        photos = st.file_uploader("Project Photos (Used for AI Analysis)", accept_multiple_files=True, key="photos")
        if photos: 
            st.session_state.uploaded_photos = True
            p_cols = st.columns(4)
            img_previews = []
            for idx, p in enumerate(photos[:8]):
                with p_cols[idx % 4]:
                    img = Image.open(p)
                    st.image(img, use_container_width=True)
                    if st.checkbox("HERO", key=f"hero_{idx}", value=(st.session_state.hero_index == idx)): st.session_state.hero_index = idx
                    buf = io.BytesIO()
                    img.save(buf, format='PNG')
                    img_previews.append(base64.b64encode(buf.getvalue()).decode('utf-8'))
            st.session_state.photos_for_ai = img_previews

    st.markdown('<div class="dotted-sep"></div>', unsafe_allow_html=True)

    # --- SESSION: CORE ---
    st.markdown(f'<div class="sec-header">{icon_svg("core")} Strategic Core</div>', unsafe_allow_html=True)
    u1, u2 = st.columns([1, 2])
    with u1: youtube = st.text_input("YouTube (Optional)", value=st.session_state.form_data.get("youtube", ""))
    with u2: open_q = st.text_area("Concept Goal?", value=st.session_state.form_data.get("open_question", ""), height=80)

    st.markdown('<div class="dotted-sep"></div>', unsafe_allow_html=True)

    # --- SESSION: DIAGNOSTICS (Required for 100%) ---
    st.markdown(f'<div class="sec-header">AI Diagnostics</div>', unsafe_allow_html=True)
    if pts >= 8 or st.session_state.mock_assets:
        if st.button("📝 GENERATE 15 MC FOR ANALYSIS", use_container_width=True):
            with st.spinner("Analyzing Project..."):
                sys = "Output JSON array of 15 diagnostic questions. Format: [{'q':'...', 'opts':['A','B','C']}]"
                ctx = f"Client: {client}. SOW: {', '.join(sel_sow)}. Concept: {open_q}"
                res = call_gemini_ai(ctx, sys, st.session_state.get('photos_for_ai'))
                if res: st.session_state.mc_questions = json.loads(res.replace("```json", "").replace("```", ""))
                st.rerun()

        if st.session_state.mc_questions:
            st.markdown(f"<p style='color:{S_RED};'><b>Answer the diagnostic questions below to reach 100%:</b></p>", unsafe_allow_html=True)
            for i, q in enumerate(st.session_state.mc_questions):
                st.markdown(f'<div style="font-weight:700; margin-top:15px;">Q{i+1}. {q["q"]}</div>', unsafe_allow_html=True)
                for opt in q["opts"]: st.checkbox(opt, key=f"mc_{i}_{opt}")
    else:
        st.info("Complete the Brand Identity, Framework, Assets, and Core sections to unlock AI Diagnostics.")

    # --- PROCEED BUTTON ---
    if percent >= 100:
        st.markdown('<div class="next-btn" style="margin-top:40px;">', unsafe_allow_html=True)
        if st.button("PROCEED TO CONTENT REVIEW 👉", type="primary", use_container_width=True):
            st.session_state.form_data.update({
                "client": client, "project": project, "venue": venue, "year": year, "month": month, "date": f"{year} {month}",
                "category": sel_cat, "what_we_do": sel_wwd, "scope": sel_sow, 
                "drive_folder": drive_folder, "open_question": open_q, "youtube": youtube
            })
            st.session_state.page = 2; st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

# ==========================================
# 5. PAGE 2: CONTENT REVIEW & SYNC
# ==========================================
elif st.session_state.page == 2:
    if not st.session_state.sync_complete:
        st.markdown(f"""
            <div class="header-container">
                <img src="https://raw.githubusercontent.com/dickson-crypto/Firebeanlogo2026.png" width="180">
                <h1 class="hero-title">Content Review.</h1>
            </div>
        """, unsafe_allow_html=True)
        if st.button("← BACK TO COLLECTOR"): st.session_state.page = 1; st.rerun()

        st.markdown('<div class="dotted-sep"></div>', unsafe_allow_html=True)

        def generate_ai_content():
            with st.spinner("AI is synthesizing Social Media & Web Content..."):
                sys = """Output ONLY valid JSON: {
                    "BoringChallenge":"...", "CreativeSolution":"...", 
                    "SocialMedia":{"FB":"...", "LI":"..."}, 
                    "Web":{"EN":"...", "TC":"...", "JP":"..."}, 
                    "FAQ":{"EN":[{"q":"","a":""}],"TC":[],"JP":[]}
                }"""
                ctx = f"Client: {st.session_state.form_data['client']}. SOW: {', '.join(st.session_state.form_data['scope'])}. Concept: {st.session_state.form_data['open_question']}"
                res = call_gemini_ai(ctx, sys)
                if res:
                    try: st.session_state.generated_content = json.loads(res.replace("```json", "").replace("```", ""))
                    except Exception as e: st.error("JSON Error during generation.")

        if st.session_state.generated_content is None:
            generate_ai_content()

        if st.session_state.generated_content:
            gc = st.session_state.generated_content
            
            st.markdown(f'<div class="sec-header">Strategic Angles</div>', unsafe_allow_html=True)
            st.write(f"**Challenge:** {gc.get('BoringChallenge', '')}")
            st.write(f"**Solution:** {gc.get('CreativeSolution', '')}")

            st.markdown(f'<div class="sec-header" style="margin-top:30px;">Social Media Output</div>', unsafe_allow_html=True)
            sm = gc.get('SocialMedia', {})
            st.text_area("LinkedIn", sm.get('LI', ''), height=100)
            st.text_area("Facebook", sm.get('FB', ''), height=100)

            st.markdown(f'<div class="sec-header" style="margin-top:30px;">Web Content</div>', unsafe_allow_html=True)
            web = gc.get('Web', {})
            with st.expander("Web Article (English)"): st.markdown(web.get("EN", ""), unsafe_allow_html=True)
            with st.expander("Web Article (Traditional Chinese)"): st.markdown(web.get("TC", ""), unsafe_allow_html=True)

            st.markdown('<div class="dotted-sep"></div>', unsafe_allow_html=True)

            c1, c2 = st.columns(2)
            with c1:
                st.markdown('<div class="boss-btn">', unsafe_allow_html=True)
                if st.button("🔄 REGENERATE CONTENT", use_container_width=True):
                    generate_ai_content(); st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)
            with c2:
                st.markdown('<div class="next-btn">', unsafe_allow_html=True)
                if st.button("🚀 CONFIRM & MASTER SYNC", type="primary", use_container_width=True):
                    with st.spinner("Executing Master Sync..."):
                        # Perfect mapping to Main.gs requirements
                        payload = {
                            **st.session_state.form_data, 
                            "category": ", ".join(st.session_state.form_data['category']), 
                            "what_we_do": ", ".join(st.session_state.form_data['what_we_do']), 
                            "scope": "\n".join(st.session_state.form_data['scope']), 
                            "challenge": gc.get("BoringChallenge", ""),
                            "solution": gc.get("CreativeSolution", ""),
                            "ai_content": {"Web": gc.get("Web", {}), "FAQ": gc.get("FAQ", {})},
                            "date": st.session_state.form_data.get("date", datetime.now().strftime("%Y %b").upper())
                        }
                        res = requests.post(WEB_APP_URL, json=payload)
                        if res.status_code == 200:
                            st.session_state.sync_complete = True; st.rerun()
                        else: st.error("Database Sync Failed.")
                st.markdown('</div>', unsafe_allow_html=True)

    else:
        # Success & Reset Screen
        st.markdown(f"""
            <div class="success-box" style="margin-top:100px;">
                <h1 style="color:{S_RED} !important; font-size:48px;">SYNC SUCCESSFUL</h1>
                <p>Profile data and AI content have been securely written to the Master DB.</p>
            </div>
        """, unsafe_allow_html=True)
        st.balloons()
        
        st.markdown('<div class="next-btn" style="margin-top:40px;">', unsafe_allow_html=True)
        if st.button("➕ SUBMIT ANOTHER PROFILE", type="primary", use_container_width=True):
            for key in list(st.session_state.keys()): del st.session_state[key]
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

st.markdown(f"<p style='text-align: center; color: grey; font-size: 10px; letter-spacing: 2px; text-transform: uppercase; margin-top: 40px;'>FIREBEAN LIMITED | SPEEDUP UI v13.6.1</p>", unsafe_allow_html=True)
