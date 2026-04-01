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

# ==========================================
# 1. CONFIGURATION & SECRETS (Pro Account)
# ==========================================
WEB_APP_URL = "https://script.google.com/macros/s/AKfycbyCfSfjgYi7yQFpqBDshjYQ1Zye4VjaT-U4_0nfF9c5oYF1Pr0CrGI38Is4BS3KigIz/exec"
apiKey = st.secrets.get("GEMINI_API_KEY", "")
APP_VERSION = "v15.3.0"

# Updated to match user's Pro Dashboard exactly
MODELS_TO_TEST = [
    "gemini-3-flash",         # Next-Gen Speed
    "gemini-2.5-flash",       # Standard Pro
    "gemini-2.5-pro",         # Deep Strategic Logic
    "gemini-2-flash"          # Stable fallback
]

st.set_page_config(
    page_title=f"Firebean Brain Collector {APP_VERSION}",
    page_icon="🔥",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ==========================================
# 2. STATE & TERMINAL LOGIC
# ==========================================
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
    st.session_state.terminal_logs = [f"> System Boot: {APP_VERSION}", "> Handshaking with Pro Strategic Engines..."]

def add_log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    st.session_state.terminal_logs.append(f"[{ts}] {msg}")
    if len(st.session_state.terminal_logs) > 15:
        st.session_state.terminal_logs.pop(0)

# ==========================================
# 3. AI CONNECTION HANDSHAKE
# ==========================================
def verify_ai_connection():
    if not apiKey:
        st.session_state.ai_status = "🔴 OFFLINE (Key Missing)"
        add_log("Security Error: GEMINI_API_KEY missing from Streamlit Secrets.")
        return
    
    for model_name in MODELS_TO_TEST:
        add_log(f"Probe: Testing {model_name}...")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={apiKey}"
        payload = {
            "contents": [{"role": "user", "parts": [{"text": "hi"}]}],
            "generationConfig": {"maxOutputTokens": 1}
        }
        try:
            res = requests.post(url, json=payload, timeout=10)
            if res.status_code == 200:
                st.session_state.ai_status = "🟢 ONLINE"
                st.session_state.active_model = model_name
                add_log(f"Success: {model_name} link established.")
                return
            elif res.status_code == 429:
                st.session_state.ai_status = "🔴 RATE LIMITED (429)"
                add_log(f"Pro Limit: {model_name} busy. Cooling down...")
                return 
        except:
            add_log(f"Network: {model_name} request failed.")
        time.sleep(1.2)
            
    st.session_state.ai_status = "🔴 OFFLINE"
    add_log("Critical: Handshake failed. Model version mismatch or Invalid Key.")

if st.session_state.ai_status == "🟡 INITIALIZING":
    verify_ai_connection()

# --- SPEEDUP UI STYLING ---
S_RED = "#E2231A"
S_DARK = "#2A2A2A"
S_WHITE = "#FFFFFF"
S_BG_DARK = "#121212"

t = {
    "bg": S_BG_DARK if st.session_state.dark_mode else S_WHITE,
    "text": "#FFFFFF" if st.session_state.dark_mode else S_DARK,
    "border": "#333333" if st.session_state.dark_mode else "#DDDDDD",
    "input_bg": "#1A1A1A" if st.session_state.dark_mode else "#FFFFFF",
}

st.markdown(f"""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@300;400;700;900&display=swap');
        .stApp {{ background-color: {t['bg']}; color: {t['text']}; font-family: 'Montserrat', sans-serif; transition: all 0.5s ease; }}
        h1, h2, h3, p, span, label, div, .stMarkdown {{ color: {t['text']} !important; }}
        .header-container {{ display: flex; align-items: center; gap: 35px; padding: 20px 0; margin-bottom: 5px; }}
        
        .hero-title {{ 
            font-size: 84px !important; 
            font-weight: 900 !important; 
            line-height: 0.85 !important; 
            letter-spacing: -4px !important; 
            margin: 0 !important; 
            text-align: left !important;
        }}
        
        .dotted-sep {{ border-bottom: 1px dotted {t['border']}; margin: 25px 0; width: 100%; }}

        .stTextInput input, .stTextArea textarea, .stSelectbox div[data-baseweb="select"] {{
            background-color: {t['input_bg']} !important; border: 1px solid {t['border']} !important;
            border-radius: 6px !important; color: {t['text']} !important;
        }}
        
        .sec-header {{ font-size: 16px; font-weight: 900; color: {S_RED} !important; text-transform: uppercase; letter-spacing: 2px; margin-bottom: 15px; }}
        .progress-hub {{ position: fixed; top: 25px; right: 40px; z-index: 1000; }}
        
        .stButton button {{ 
            background-color: {S_RED} !important; color: white !important; border-radius: 50px !important; 
            padding: 10px 25px !important; font-weight: 700 !important; text-transform: uppercase; 
            letter-spacing: 1px; border: none !important; font-size: 12px !important;
        }}
        
        .terminal-box {{ 
            background: #000; 
            color: #FFFFFF; /* Fix: Debug box text is now pure white */
            font-family: 'Courier New', monospace; 
            padding: 15px; 
            border-radius: 8px; 
            font-size: 11px; 
            line-height: 1.5; 
            border-left: 4px solid {S_RED}; 
            height: 200px; 
            overflow-y: auto; 
        }}
        
        .status-badge {{ background: {S_RED}; color: white; padding: 4px 12px; border-radius: 4px; font-size: 9px; font-weight: 900; letter-spacing: 1px; margin-bottom: 10px; display: inline-block; }}
        [data-testid="stSidebar"] {{display: none;}}
        header, footer {{visibility: hidden;}}
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 4. CORE UTILITIES
# ==========================================
def render_progress(percent):
    circum = 251.3
    offset = circum * (1 - percent / 100)
    st.markdown(f"""
    <div class="progress-hub">
        <div style="position:relative; width:90px; height:90px; display:flex; align-items:center; justify-content:center;">
            <svg width="90" height="90">
                <circle stroke="{t['border']}" stroke-width="1" fill="transparent" r="35" cx="45" cy="45"/>
                <circle stroke="{S_RED}" stroke-width="2" stroke-dasharray="{circum}" stroke-dashoffset="{offset}" 
                        stroke-linecap="round" fill="transparent" r="35" cx="45" cy="45" 
                        style="transition: stroke-dashoffset 0.8s ease-out; transform: rotate(-90deg); transform-origin: center;"/>
            </svg>
            <div style="position:absolute; font-size:22px; font-weight:300; color:{t['text']};">{percent}%</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

def call_gemini_ai(prompt, sys_prompt, image_blobs=None):
    add_log(f"AI: Querying {st.session_state.active_model}...")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{st.session_state.active_model}:generateContent?key={apiKey}"
    parts = [{"text": prompt}]
    if image_blobs:
        add_log(f"Multimodal: Processing {len(image_blobs)} visual cues.")
        for b in image_blobs[:4]: parts.append({"inlineData": {"mimeType": "image/png", "data": b}})
    payload = {"contents": [{"role": "user", "parts": parts}], "systemInstruction": {"parts": [{"text": sys_prompt}]}, "generationConfig": {"responseMimeType": "application/json"}}
    
    try:
        res = requests.post(url, json=payload, timeout=60)
        if res.status_code == 200:
            add_log("AI: Analysis successful.")
            return res.json()['candidates'][0]['content']['parts'][0]['text']
        else:
            add_log(f"AI Error: {res.status_code}")
    except Exception as e:
        add_log(f"AI Exception: {str(e)}")
    return None

def process_image(uploaded_file):
    if not uploaded_file: return None
    try:
        img = Image.open(uploaded_file)
        img = ImageOps.exif_transpose(img)
        img.thumbnail((1200, 1200))
        buf = io.BytesIO()
        img.convert('RGB').save(buf, format='JPEG', quality=75)
        return {"data": base64.b64encode(buf.getvalue()).decode('utf-8'), "mimeType": "image/jpeg", "ext": "jpg"}
    except: return None

# ==========================================
# 5. PAGE 1: PROJECT DATA COLLECTOR
# ==========================================
if st.session_state.page == 1:
    h_col1, h_col2, h_col3, h_col4 = st.columns([1.2, 4.5, 1.8, 1.8])
    with h_col1: 
        # Stable Logo Path
        st.image("https://raw.githubusercontent.com/dickson-crypto/Firebean-app/main/Firebeanlogo2026.png", width="stretch")
    with h_col2: 
        st.markdown(f'<h1 class="hero-title">Project<br>Collector.</h1>', unsafe_allow_html=True)
        st.markdown(f'<div class="status-badge">SYSTEM HEARTBEAT: {st.session_state.ai_status} | {st.session_state.active_model.upper()}</div>', unsafe_allow_html=True)
    with h_col3:
        st.markdown('<div style="margin-top: 35px;"></div>', unsafe_allow_html=True)
        if st.button("🚀 BOSS MODE", width="stretch"):
            st.session_state.form_data = {"client": "Firebean HQ", "project": "Strategic Digital Hub", "venue": "Cyberport", "year": "2026", "month": "APR", "category": ["LIFESTYLE & CONSUMER"], "what_we_do": ["INTERACTIVE & TECH"], "scope": "Interactive Hub\nStrategic Synthesis", "open_question": "Redefining portfolio culture through AI."}
            st.session_state.mock_assets = True; st.rerun()
    with h_col4:
        st.markdown('<div style="margin-top: 35px;"></div>', unsafe_allow_html=True)
        btn_label = "☀️ LIGHT" if st.session_state.dark_mode else "🌙 DARK"
        if st.button(btn_label, width="stretch"):
            st.session_state.dark_mode = not st.session_state.dark_mode; st.rerun()

    st.markdown('<div class="dotted-sep"></div>', unsafe_allow_html=True)

    # Forms
    st.markdown(f'<div class="sec-header">Brand Identity</div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    client = c1.text_input("Client", value=st.session_state.form_data.get("client", ""), placeholder="e.g. Levi's")
    project = c2.text_input("Project", value=st.session_state.form_data.get("project", ""), placeholder="e.g. Pop-up Store")
    venue = c3.text_input("Venue", value=st.session_state.form_data.get("venue", ""), placeholder="Location")
    
    d1, d2, d3 = st.columns([1, 1, 2])
    yr_opts = [str(y) for y in range(2026, 2011, -1)]
    year = d1.selectbox("Year", yr_opts, index=yr_opts.index(st.session_state.form_data.get("year", "2026")))
    mn_opts = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]
    month = d2.selectbox("Month", mn_opts, index=mn_opts.index(st.session_state.form_data.get("month", "APR")))

    st.markdown('<div class="dotted-sep"></div>', unsafe_allow_html=True)
    st.markdown(f'<div class="sec-header">Strategic Framework</div>', unsafe_allow_html=True)
    cat_opts = ["GOVERNMENT & PUBLIC SECTOR", "LIFESTYLE & CONSUMER", "F&B & HOSPITALITY", "MALLS & VENUES"]
    cat_cols = st.columns(4)
    sel_cat = [opt for i, opt in enumerate(cat_opts) if cat_cols[i%4].checkbox(opt, key=f"c_{opt}", value=(opt in st.session_state.form_data.get("category", [])))]
    wwd_opts = ["ROVING EXHIBITIONS", "SOCIAL & CONTENT", "INTERACTIVE & TECH", "PR & MEDIA", "EVENTS & CEREMONIES"]
    wwd_cols = st.columns(3)
    sel_wwd = [opt for i, opt in enumerate(wwd_opts) if wwd_cols[i%3].checkbox(opt, key=f"w_{opt}", value=(opt in st.session_state.form_data.get("what_we_do", [])))]

    st.markdown('<div class="dotted-sep"></div>', unsafe_allow_html=True)
    st.markdown(f'<div class="sec-header">Visual Assets Hub</div>', unsafe_allow_html=True)
    a1, a2, a3 = st.columns([1, 1, 2])
    logo_b = a1.file_uploader("Logo Black", key="logo_b")
    logo_w = a2.file_uploader("Logo White", key="logo_w")
    photos = a3.file_uploader("Gallery", accept_multiple_files=True, key="photos")
    if photos:
        p_cols = st.columns(4)
        img_previews = []
        for idx, p in enumerate(photos[:8]):
            with p_cols[idx % 4]:
                img = Image.open(p)
                st.image(img, width="stretch")
                if st.checkbox("HERO", key=f"hero_{idx}", value=(st.session_state.hero_index == idx)): st.session_state.hero_index = idx
                buf = io.BytesIO()
                img.save(buf, format='PNG')
                img_previews.append(base64.b64encode(buf.getvalue()).decode('utf-8'))
        st.session_state.photos_for_ai = img_previews

    st.markdown('<div class="dotted-sep"></div>', unsafe_allow_html=True)
    st.markdown(f'<div class="sec-header">Strategic Core</div>', unsafe_allow_html=True)
    u1, u2 = st.columns([1, 2])
    youtube = u1.text_input("YouTube (Optional)")
    open_q = u2.text_area("Concept Goal?", value=st.session_state.form_data.get("open_question", ""), height=80)

    # --- 12-POINT PROGRESS MATH ---
    pts = sum([bool(client), bool(project), bool(venue), bool(year), bool(month), bool(sel_cat), bool(sel_wwd), bool(open_q)])
    pts += 1 # Scope slot (8+1=9)
    pts += 2 if st.session_state.mock_assets else (bool(logo_b or logo_w) + bool(photos))
    
    ans_mc = False
    if st.session_state.mc_questions:
        for i, q in enumerate(st.session_state.mc_questions):
            for opt in q["opts"]:
                if st.session_state.get(f"mc_{i}_{opt}", False): ans_mc = True
    if ans_mc: pts += 1
    
    percent = int((pts / 12) * 100) 
    render_progress(min(percent, 100))

    st.markdown('<div class="dotted-sep"></div>', unsafe_allow_html=True)
    st.markdown(f'<div class="sec-header">AI Diagnostics</div>', unsafe_allow_html=True)
    if pts >= 11 or st.session_state.mock_assets:
        if "ONLINE" in st.session_state.ai_status:
            if st.button("📝 GENERATE 15 MC ANALYSIS", width="stretch"):
                res = call_gemini_ai(f"Client: {client}. Concept: {open_q}", "Output JSON array of 15 diagnostic MC questions [{'q':'...', 'opts':['A','B','C']}]", st.session_state.get('photos_for_ai'))
                if res: 
                    try: st.session_state.mc_questions = json.loads(res.replace("```json", "").replace("```", ""))
                    except: st.error("AI Busy. Try again in 5s.")
                st.rerun()
        else: st.error("AI Strategic Engine Offline.")

        if st.session_state.mc_questions:
            for i, q in enumerate(st.session_state.mc_questions):
                st.markdown(f'**Q{i+1}. {q["q"]}**')
                for opt in q["opts"]: st.checkbox(opt, key=f"mc_{i}_{opt}")
    else: st.info(f"Progress: {percent}% — All textual data and years are required to unlock diagnostics.")

    if percent >= 100:
        if st.button("PROCEED TO CONTENT REVIEW 👉", type="primary", width="stretch"):
            if not st.session_state.mock_assets:
                st.session_state.full_assets = {"logo_black": process_image(logo_b), "logo_white": process_image(logo_w), "photos": [process_image(p) for p in photos[:8]], "hero_index": st.session_state.hero_index}
            st.session_state.form_data.update({"client": client, "project": project, "venue": venue, "year": year, "month": month, "category": sel_cat, "what_we_do": sel_wwd, "open_question": open_q, "youtube": youtube})
            st.session_state.page = 2; st.rerun()

    st.markdown('<div class="dotted-sep"></div>', unsafe_allow_html=True)
    st.markdown('<div class="sec-header">Strategic Operations Center</div>', unsafe_allow_html=True)
    log_content = "<br>".join(st.session_state.terminal_logs)
    st.markdown(f'<div class="terminal-box">{log_content}</div>', unsafe_allow_html=True)
    if st.button("🔄 RETRY HANDSHAKES", width="stretch"):
        st.session_state.ai_status = "🟡 INITIALIZING"
        st.rerun()

# ==========================================
# 6. PAGE 2: CONTENT REVIEW
# ==========================================
elif st.session_state.page == 2:
    if not st.session_state.sync_complete:
        h_col1, h_col2 = st.columns([1, 4])
        h_col1.image("https://raw.githubusercontent.com/dickson-crypto/Firebean-app/main/Firebeanlogo2026.png", width="stretch")
        h_col2.markdown('<h1 class="hero-title" style="font-size: 72px !important;">Content<br>Review.</h1>', unsafe_allow_html=True)
        if st.button("← BACK"): st.session_state.page = 1; st.rerun()
        st.markdown('<div class="dotted-sep"></div>', unsafe_allow_html=True)

        if st.session_state.generated_content is None:
            ctx = f"Project: {st.session_state.form_data['project']}. Strategy: {st.session_state.form_data['open_question']}"
            res = call_gemini_ai(ctx, "Output JSON: {'BoringChallenge':'...', 'CreativeSolution':'...', 'SocialMedia':{'FB':'...', 'LI':'...'}, 'Web':{'EN':'...', 'TC':'...', 'JP':'...'}, 'FAQ':{'EN':[{'q':'','a':''}]}}")
            if res: st.session_state.generated_content = json.loads(res.replace("```json", "").replace("```", ""))

        if st.session_state.generated_content:
            gc = st.session_state.generated_content
            st.write(f"**Challenge:** {gc.get('BoringChallenge', '')}")
            st.write(f"**Solution:** {gc.get('CreativeSolution', '')}")
            st.text_area("LinkedIn", gc.get('SocialMedia', {}).get('LI', ''), height=100)
            st.text_area("Facebook", gc.get('SocialMedia', {}).get('FB', ''), height=100)
            
            c1, c2 = st.columns(2)
            if c1.button("🔄 REGENERATE", width="stretch"): st.session_state.generated_content = None; st.rerun()
            if c2.button("🚀 EXECUTE MASTER SYNC", type="primary", width="stretch"):
                add_log("Sync: Dispatching payload to Master DB...")
                payload = {**st.session_state.form_data, "category": ", ".join(st.session_state.form_data['category']), "what_we_do": ", ".join(st.session_state.form_data['what_we_do']), "challenge": gc.get("BoringChallenge"), "solution": gc.get("CreativeSolution"), "ai_content": {"Web": gc.get("Web"), "FAQ": gc.get("FAQ")}, "date": f"{st.session_state.form_data['year']} {st.session_state.form_data['month']}", "assets": st.session_state.full_assets}
                res = requests.post(WEB_APP_URL, json=payload)
                if res.status_code == 200:
                    add_log("Sync: COMPLETE."); st.session_state.sync_complete = True; st.rerun()
                else: add_log(f"Sync: ERROR ({res.status_code})")

    else:
        st.markdown(f'<div style="text-align:center; margin-top:100px; padding:50px; border-radius:20px; border:2px solid {S_RED};"><h1>SYNC SUCCESSFUL</h1><p>The profile has been written to the Master DB.</p></div>', unsafe_allow_html=True)
        if st.button("➕ START NEW PROFILE", type="primary", width="stretch"):
            for key in list(st.session_state.keys()): del st.session_state[key]
            st.rerun()

    st.markdown('<div class="dotted-sep"></div>', unsafe_allow_html=True)
    log_content = "<br>".join(st.session_state.terminal_logs)
    st.markdown(f'<div class="terminal-box">{log_content}</div>', unsafe_allow_html=True)

st.markdown(f"<p style='text-align: center; color: grey; font-size: 10px; letter-spacing: 2px; text-transform: uppercase; margin-top: 40px;'>FIREBEAN LIMITED | SPEEDUP UI v15.3.0</p>", unsafe_allow_html=True)
