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
# 1. CONFIGURATION & SECRETS
# ==========================================
WEB_APP_URL = "https://script.google.com/macros/s/AKfycbyCfSfjgYi7yQFpqBDshjYQ1Zye4VjaT-U4_0nfF9c5oYF1Pr0CrGI38Is4BS3KigIz/exec"
apiKey = st.secrets.get("GEMINI_API_KEY", "")
APP_VERSION = "v14.2.0"

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
if 'ai_status' not in st.session_state: st.session_state.ai_status = "🟡 CHECKING"
if 'terminal_logs' not in st.session_state: 
    st.session_state.terminal_logs = [f"> System initialized: {APP_VERSION}"]

def add_log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    st.session_state.terminal_logs.append(f"[{ts}] {msg}")
    if len(st.session_state.terminal_logs) > 12:
        st.session_state.terminal_logs.pop(0)

# ==========================================
# 3. AI CONNECTION CHECKER
# ==========================================
def verify_ai_connection():
    if not apiKey:
        st.session_state.ai_status = "🔴 OFFLINE (Key Missing)"
        add_log("AI Error: GEMINI_API_KEY not found in secrets.")
        return
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-09-2025:generateContent?key={apiKey}"
    payload = {
        "contents": [{"role": "user", "parts": [{"text": "ping"}]}],
        "generationConfig": {"maxOutputTokens": 1}
    }
    
    try:
        t0 = time.time()
        res = requests.post(url, json=payload, timeout=10)
        latency = round((time.time() - t0) * 1000)
        
        if res.status_code == 200:
            st.session_state.ai_status = "🟢 ONLINE"
            add_log(f"AI Handshake Successful: Gemini 2.5 Flash ({latency}ms)")
        else:
            st.session_state.ai_status = f"🔴 OFFLINE (Err {res.status_code})"
            add_log(f"AI Handshake Failed: Status {res.status_code}")
    except Exception as e:
        st.session_state.ai_status = "🔴 OFFLINE (Timeout)"
        add_log(f"AI Connection Exception: {str(e)}")

# Run connection check once per session load
if st.session_state.ai_status == "🟡 CHECKING":
    verify_ai_connection()

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
        .stApp {{ background-color: {t['bg']}; color: {t['text']}; font-family: 'Montserrat', sans-serif; transition: all 0.5s ease; }}
        h1, h2, h3, p, span, label, div, .stMarkdown {{ color: {t['text']} !important; }}
        .header-container {{ display: flex; align-items: center; gap: 35px; padding: 20px 0; margin-bottom: 5px; }}
        .hero-title {{ font-size: 84px !important; font-weight: 900 !important; line-height: 0.85 !important; letter-spacing: -4px !important; margin: 0 !important; text-align: left !important; }}
        .dotted-sep {{ border-bottom: 1px dotted {t['border']}; margin: 25px 0; width: 100%; }}
        .stTextInput input, .stTextArea textarea, .stSelectbox div[data-baseweb="select"] {{
            background-color: {t['input_bg']} !important; border: 1px solid {t['border']} !important;
            border-radius: 6px !important; padding: 10px 14px !important; font-size: 14px !important;
            color: {t['text']} !important; box-shadow: none !important;
        }}
        .sec-header {{ font-size: 16px; font-weight: 900; color: {S_RED} !important; text-transform: uppercase; letter-spacing: 2px; margin-bottom: 15px; display: flex; align-items: center; gap: 12px; }}
        .progress-hub {{ position: fixed; top: 25px; right: 40px; z-index: 1000; }}
        .stButton button {{ background-color: {S_RED} !important; color: white !important; border-radius: 50px !important; padding: 10px 25px !important; font-weight: 700 !important; text-transform: uppercase; letter-spacing: 1px; border: none !important; font-size: 12px !important; white-space: nowrap !important; }}
        .terminal-box {{ background: #000; color: #39ff14; font-family: 'Courier New', monospace; padding: 15px; border-radius: 8px; font-size: 11px; line-height: 1.5; border-left: 4px solid {S_RED}; height: 200px; overflow-y: auto; }}
        .status-badge {{ background: {S_RED}; color: white; padding: 4px 12px; border-radius: 4px; font-size: 10px; font-weight: 900; letter-spacing: 1px; }}
        .success-box {{ padding: 30px; border-radius: 12px; border: 2px solid {S_RED}; text-align: center; background: {t['input_bg']}; }}
        [data-testid="stSidebar"] {{display: none;}}
        header {{visibility: hidden;}}
        footer {{visibility: hidden;}}
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 4. UTILITIES
# ==========================================
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
                        style="transition: stroke-dashoffset 0.8s ease-out; transform: rotate(-90deg); transform-origin: center;"/>
            </svg>
            <div style="position:absolute; font-size:22px; font-weight:300; color:{t['text']};">{percent}%</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

def call_gemini_ai(prompt, sys_prompt, image_blobs=None):
    add_log("Connecting to Gemini-2.5-Flash Strategic Engine...")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-09-2025:generateContent?key={apiKey}"
    
    parts = [{"text": prompt}]
    if image_blobs:
        add_log(f"Multimodal Vision: Analyzing {len(image_blobs)} strategic assets...")
        for b in image_blobs[:4]: 
            parts.append({"inlineData": {"mimeType": "image/png", "data": b}})
    
    payload = {
        "contents": [{"role": "user", "parts": parts}],
        "systemInstruction": {"parts": [{"text": sys_prompt}]},
        "generationConfig": {"responseMimeType": "application/json"}
    }
    
    try:
        res = requests.post(url, json=payload, timeout=60)
        if res.status_code == 200:
            add_log("AI Synthesis Successful.")
            return res.json()['candidates'][0]['content']['parts'][0]['text']
        else:
            add_log(f"AI Connection Error: Status {res.status_code}")
            try: add_log(f"Detail: {res.json()['error']['message']}")
            except: pass
    except Exception as e:
        add_log(f"Fatal System Error: {str(e)}")
    return None

def process_image_for_payload(uploaded_file):
    if not uploaded_file: return None
    try:
        img = Image.open(uploaded_file)
        img = ImageOps.exif_transpose(img)
        img.thumbnail((1200, 1200))
        buf = io.BytesIO()
        img.convert('RGB').save(buf, format='JPEG', quality=75)
        return {"data": base64.b64encode(buf.getvalue()).decode('utf-8'), "mimeType": "image/jpeg", "ext": "jpg"}
    except: return None

CAT_OPTS = ["GOVERNMENT & PUBLIC SECTOR", "LIFESTYLE & CONSUMER", "F&B & HOSPITALITY", "MALLS & VENUES"]
WWD_OPTS = ["ROVING EXHIBITIONS", "SOCIAL & CONTENT", "INTERACTIVE & TECH", "PR & MEDIA", "EVENTS & CEREMONIES"]
SOW_OPTS = ["Concept Development", "Branding Strategy", "PR Consulting", "Media Relations", "Theme Design", "Visual Identity", "UI/UX Design", "Social Media Content", "Influencer Seeding", "Video Production", "Motion Graphics", "Interactive Installation", "Event Planning", "Event Production", "RSVP Management", "Talent Management", "On-site Operation", "Technical Support"]

def run_boss_test():
    add_log("Boss Mode: Simulating high-fidelity strategic project...")
    st.session_state.form_data = {"client": "Firebean HQ", "project": "Strategic Digital Hub", "venue": "Cyberport", "year": "2026", "month": "APR", "category": ["LIFESTYLE & CONSUMER"], "what_we_do": ["INTERACTIVE & TECH"], "scope": ["Concept Development", "Interactive Installation"], "open_question": "Redefining portfolio culture through AI synthesis."}
    st.session_state.mock_assets = True
    st.rerun()

# ==========================================
# 5. PAGE 1: STRATEGIC COLLECTOR
# ==========================================
if st.session_state.page == 1:
    h_col1, h_col2, h_col3, h_col4 = st.columns([1.2, 4.5, 1.8, 1.8])
    with h_col1: st.image("https://raw.githubusercontent.com/dickson-crypto/Firebean-app/main/Firebeanlogo2026.png", use_container_width=True)
    with h_col2: 
        st.markdown('<h1 class="hero-title">Project<br>Collector.</h1>', unsafe_allow_html=True)
        st.markdown(f'<span class="status-badge">AI STATUS: {st.session_state.ai_status}</span>', unsafe_allow_html=True)
    with h_col3:
        st.markdown('<div style="margin-top: 35px;"></div>', unsafe_allow_html=True)
        if st.button("🚀 BOSS MODE", use_container_width=True): run_boss_test()
    with h_col4:
        st.markdown('<div style="margin-top: 35px;"></div>', unsafe_allow_html=True)
        btn_txt = "☀️ LIGHT" if st.session_state.dark_mode else "🌙 DARK"
        if st.button(btn_txt, use_container_width=True):
            st.session_state.dark_mode = not st.session_state.dark_mode
            st.rerun()

    st.markdown('<div class="dotted-sep"></div>', unsafe_allow_html=True)

    # Core Form
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
    cat_cols = st.columns(4)
    sel_cat = [opt for i, opt in enumerate(CAT_OPTS) if cat_cols[i%4].checkbox(opt, key=f"c_{opt}", value=(opt in st.session_state.form_data.get("category", [])))]
    st.write("<br>", unsafe_allow_html=True)
    wwd_cols = st.columns(3)
    sel_wwd = [opt for i, opt in enumerate(WWD_OPTS) if wwd_cols[i%3].checkbox(opt, key=f"w_{opt}", value=(opt in st.session_state.form_data.get("what_we_do", [])))]
    st.write("<br>", unsafe_allow_html=True)
    sow_cols = st.columns(3)
    sel_sow = [opt for i, opt in enumerate(SOW_OPTS) if sow_cols[i%3].checkbox(opt, key=f"s_{opt}", value=(opt in st.session_state.form_data.get("scope", [])))]

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
                st.image(img, use_container_width=True)
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

    # --- PROGRESS TRACKING ---
    pts = sum([bool(client), bool(project), bool(venue), bool(year), bool(month), bool(sel_cat), bool(sel_wwd), bool(sel_sow), bool(open_q)])
    pts += 2 if st.session_state.mock_assets else (bool(logo_b or logo_w) + bool(photos))
    
    ans_mc = False
    if st.session_state.mc_questions:
        for i, q in enumerate(st.session_state.mc_questions):
            for opt in q["opts"]:
                if st.session_state.get(f"mc_{i}_{opt}", False): ans_mc = True
    if ans_mc: pts += 1
    
    percent = int((pts / 12) * 100) 
    render_speedup_progress(min(percent, 100))

    st.markdown('<div class="dotted-sep"></div>', unsafe_allow_html=True)
    st.markdown(f'<div class="sec-header">AI Diagnostics</div>', unsafe_allow_html=True)
    if pts >= 11 or st.session_state.mock_assets:
        # Block button if AI is offline
        if "ONLINE" in st.session_state.ai_status:
            if st.button("📝 GENERATE 15 MC ANALYSIS", use_container_width=True):
                res = call_gemini_ai(f"Client: {client}. Core Strategy: {open_q}", "Output JSON array of 15 diagnostic MC questions [{'q':'...', 'opts':['A','B','C']}]", st.session_state.get('photos_for_ai'))
                if res: 
                    try: st.session_state.mc_questions = json.loads(res.replace("```json", "").replace("```", ""))
                    except: st.error("AI returned invalid JSON. Retrying...")
                st.rerun()
        else:
            st.error("AI Strategic Engine is currently OFFLINE. Cannot generate diagnostics.")

        if st.session_state.mc_questions:
            for i, q in enumerate(st.session_state.mc_questions):
                st.markdown(f'**Q{i+1}. {q["q"]}**')
                for opt in q["opts"]: st.checkbox(opt, key=f"mc_{i}_{opt}")
    else:
        st.info(f"Progress: {percent}% — Complete fields and assets to unlock.")

    if percent >= 100:
        if st.button("PROCEED TO CONTENT REVIEW 👉", type="primary", use_container_width=True):
            add_log("Finalizing data package. Compressing assets...")
            if not st.session_state.mock_assets:
                st.session_state.full_assets = {"logo_black": process_image_for_payload(logo_b), "logo_white": process_image_for_payload(logo_w), "photos": [process_image_for_payload(p) for p in photos[:8]], "hero_index": st.session_state.hero_index}
            st.session_state.form_data.update({"client": client, "project": project, "venue": venue, "year": year, "month": month, "category": sel_cat, "what_we_do": sel_wwd, "scope": sel_sow, "open_question": open_q, "youtube": youtube})
            st.session_state.page = 2; st.rerun()

    st.markdown('<div class="dotted-sep"></div>', unsafe_allow_html=True)
    st.markdown('<div class="sec-header">Strategic Operations Center</div>', unsafe_allow_html=True)
    log_content = "<br>".join(st.session_state.terminal_logs)
    st.markdown(f'<div class="terminal-box">{log_content}</div>', unsafe_allow_html=True)

# ==========================================
# 6. PAGE 2: CONTENT REVIEW
# ==========================================
elif st.session_state.page == 2:
    if not st.session_state.sync_complete:
        h_col1, h_col2 = st.columns([1, 4])
        h_col1.image("https://raw.githubusercontent.com/dickson-crypto/Firebeanlogo2026.png", use_container_width=True)
        h_col2.markdown('<h1 class="hero-title" style="font-size: 72px !important;">Content<br>Review.</h1>', unsafe_allow_html=True)
        
        if st.button("← BACK TO COLLECTOR"): st.session_state.page = 1; st.rerun()
        st.markdown('<div class="dotted-sep"></div>', unsafe_allow_html=True)

        if st.session_state.generated_content is None:
            ctx = f"Project: {st.session_state.form_data['project']}. Core Strategy: {st.session_state.form_data['open_question']}"
            res = call_gemini_ai(ctx, "Output JSON structure: {'BoringChallenge':'...', 'CreativeSolution':'...', 'SocialMedia':{'FB':'...', 'LI':'...'}, 'Web':{'EN':'...', 'TC':'...', 'JP':'...'}, 'FAQ':{'EN':[{'q':'','a':''}]}}")
            if res: st.session_state.generated_content = json.loads(res.replace("```json", "").replace("```", ""))

        if st.session_state.generated_content:
            gc = st.session_state.generated_content
            st.write(f"**Challenge:** {gc.get('BoringChallenge')}")
            st.write(f"**Solution:** {gc.get('CreativeSolution')}")
            sm = gc.get('SocialMedia', {})
            st.text_area("LinkedIn Copy", sm.get('LI'), height=100)
            st.text_area("Facebook Copy", sm.get('FB'), height=100)
            
            c1, c2 = st.columns(2)
            if c1.button("🔄 REGENERATE", use_container_width=True): st.session_state.generated_content = None; st.rerun()
            if c2.button("🚀 EXECUTE MASTER SYNC", type="primary", use_container_width=True):
                add_log("Connecting to Handlers.gs API...")
                payload = {**st.session_state.form_data, "category": ", ".join(st.session_state.form_data['category']), "what_we_do": ", ".join(st.session_state.form_data['what_we_do']), "scope": "\n".join(st.session_state.form_data['scope']), "challenge": gc.get("BoringChallenge"), "solution": gc.get("CreativeSolution"), "ai_content": {"Web": gc.get("Web"), "FAQ": gc.get("FAQ")}, "date": f"{st.session_state.form_data['year']} {st.session_state.form_data['month']}", "assets": st.session_state.full_assets}
                res = requests.post(WEB_APP_URL, json=payload)
                if res.status_code == 200:
                    add_log("SYNC SUCCESSFUL.")
                    st.session_state.sync_complete = True; st.rerun()
                else: add_log(f"Sync Failed: {res.status_code}")

    else:
        st.markdown(f'<div class="success-box" style="margin-top:100px;"><h1 style="color:{S_RED} !important; font-size:48px;">SYNC SUCCESSFUL</h1><p>Master DB Updated. Folder automation complete.</p></div>', unsafe_allow_html=True)
        if st.button("➕ SUBMIT ANOTHER", type="primary", use_container_width=True):
            for key in list(st.session_state.keys()): del st.session_state[key]
            st.rerun()

    st.markdown('<div class="dotted-sep"></div>', unsafe_allow_html=True)
    log_content = "<br>".join(st.session_state.terminal_logs)
    st.markdown(f'<div class="terminal-box">{log_content}</div>', unsafe_allow_html=True)

st.markdown(f"<p style='text-align: center; color: grey; font-size: 10px; letter-spacing: 2px; text-transform: uppercase; margin-top: 40px;'>FIREBEAN LIMITED | SPEEDUP UI v14.2.0</p>", unsafe_allow_html=True)
