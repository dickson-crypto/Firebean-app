# VERSION: v18.8.2 (Frontend UI Retouch)
# TIMESTAMP: 2026-04-06 07:00:00 HKT

import streamlit as st
import requests
import json
from datetime import datetime

# Import modular engines from your GitHub repository
try:
    from inputs_module import InputEngine
    from progress_logic import ProgressGate
    from ai_diagnostics import AIDiagnostic
    from synthesis_sync import SynthesisSync
except Exception as e:
    st.error(f"Module Loading Error: {e}. Please ensure your Python files do not contain markdown formatting.")
    st.stop()

class FirebeanPortal:
    def __init__(self):
        self.VERSION = "v18.8.2 (Production Release)"
        self.MODELS = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro"]
        self.init_session()
        self.apply_ui_theme()

    def init_session(self):
        if 'page' not in st.session_state: st.session_state.page = 1
        if 'form_data' not in st.session_state: st.session_state.form_data = {}
        if 'mc_questions' not in st.session_state: st.session_state.mc_questions = []
        if 'hero_index' not in st.session_state: st.session_state.hero_index = 0
        if 'terminal_logs' not in st.session_state: 
            st.session_state.terminal_logs = [f"> System Boot: {self.VERSION}", "> Logic Engines Synced."]
        if 'ai_status' not in st.session_state: st.session_state.ai_status = "🟡 INITIALIZING"
        if 'active_model' not in st.session_state: st.session_state.active_model = "NONE"
        if 'apiKey' not in st.session_state: st.session_state.apiKey = ""
        
        if 'apiKeys' not in st.session_state:
            keys_raw = st.secrets.get("GEMINI_API_KEYS", [])
            if not keys_raw:
                single = st.secrets.get("GEMINI_API_KEY", "")
                if single: keys_raw = [single]
            st.session_state.apiKeys = [k.replace('"', '').replace("'", "").strip() for k in keys_raw if k]

    def verify_ai(self):
        if not st.session_state.apiKeys:
            st.session_state.ai_status = "🔴 OFFLINE (No Keys Found)"
            self.log("CRITICAL: No API keys found in Streamlit Secrets.")
            return
        
        working_key = None
        for idx, key in enumerate(st.session_state.apiKeys):
            safe_key_name = f"Key {idx+1} (...{key[-4:]})"
            self.log(f"Probe: Testing {safe_key_name}")
            
            for model in self.MODELS:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
                try:
                    payload = {"contents": [{"role": "user", "parts": [{"text": "System Ping. Respond with OK."}]}]}
                    res = requests.post(url, json=payload, timeout=5)
                    if res.status_code == 200:
                        st.session_state.ai_status = "🟢 ONLINE"
                        st.session_state.active_model = model
                        st.session_state.apiKey = key 
                        self.log(f"SUCCESS: {safe_key_name} locked onto {model}")
                        working_key = key
                        break 
                    elif res.status_code == 429:
                        self.log(f"Skip {safe_key_name}: 429 Quota Exceeded.")
                        break 
                    else:
                        self.log(f"Skip {model}: Status {res.status_code}")
                except Exception as e:
                    self.log(f"Network Error on {model}")
            if working_key: break 

        if not working_key:
            st.session_state.ai_status = "🔴 OFFLINE (All Quotas Empty)"
            self.log("CRITICAL: All keys exhausted or models failed.")

    def apply_ui_theme(self):
        S_RED, S_DARK, S_BG_DARK = "#E2231A", "#2A2A2A", "#121212"
        is_dark = st.session_state.get('dark_mode', False)
        bg = S_BG_DARK if is_dark else "#FFFFFF"
        txt = "#FFFFFF" if is_dark else "#121212"
        
        # Adaptive background colors for the text boxes
        dropzone_bg = "#2A2A2A" if is_dark else "#F0F2F6"
        dropzone_border = "#444444" if is_dark else "#CCCCCC"
        
        st.markdown(f"""
            <style>
                @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@300;400;700;900&display=swap');
                .stApp {{ background-color: {bg} !important; color: {txt} !important; font-family: 'Montserrat', sans-serif; }}
                
                [data-testid="stMarkdownContainer"] p, [data-testid="stMarkdownContainer"] h1, [data-testid="stMarkdownContainer"] h2, [data-testid="stMarkdownContainer"] h3, [data-testid="stWidgetLabel"] p, [data-testid="stWidgetLabel"] span, [data-baseweb="checkbox"] label p {{ color: {txt} !important; -webkit-text-fill-color: {txt} !important; }}
                .stApp p, .stApp label, .stApp span, .stApp div, .stApp h1, .stApp h2, .stApp h3 {{ color: {txt}; }}
                
                /* Icon/Text Alignment for Buttons */
                .stButton button p, .stButton button span, .stButton button div {{ 
                    color: #FFFFFF !important; 
                    -webkit-text-fill-color: #FFFFFF !important; 
                    font-weight: 600 !important; 
                    display: flex !important;
                    align-items: center !important;
                    justify-content: center !important;
                    margin: 0 !important;
                }}
                
                /* CHROME & SAFARI TEXT BOX FIX */
                .stTextInput input, .stTextArea textarea, .stSelectbox div[data-baseweb="select"] {{
                    background-color: {dropzone_bg} !important;
                    border: 1px solid {dropzone_border} !important;
                    color: {txt} !important;
                    -webkit-text-fill-color: {txt} !important;
                }}
                
                .stApp [data-testid="stFileUploadDropzone"] {{ background-color: {dropzone_bg} !important; border: 1px dashed {dropzone_border} !important; }}
                .stApp [data-testid="stFileUploadDropzone"] div, .stApp [data-testid="stFileUploadDropzone"] span, .stApp [data-testid="stFileUploadDropzone"] small, .stApp [data-testid="stFileUploadDropzone"] p, .stApp [data-testid="stFileUploadDropzone"] button {{ color: {txt} !important; -webkit-text-fill-color: {txt} !important; }}
                .stApp [data-testid="stFileUploadDropzone"] svg {{ fill: {txt} !important; }}
                div[data-testid="stCheckbox"] label p {{ color: {txt} !important; -webkit-text-fill-color: {txt} !important; font-weight: 600 !important; }}
                .hero-title {{ font-size: 84px !important; font-weight: 900 !important; line-height: 0.85 !important; letter-spacing: -4px !important; margin: 0 !important; color: {txt} !important; -webkit-text-fill-color: {txt} !important; }}
                .sec-header {{ font-size: 16px; font-weight: 900; color: {S_RED} !important; -webkit-text-fill-color: {S_RED} !important; text-transform: uppercase; letter-spacing: 2px; margin-top: 25px; }}
                .terminal-box {{ background: #000; color: #FFFFFF !important; font-family: 'Courier New', monospace; padding: 15px; border-radius: 8px; font-size: 11px; line-height: 1.5; border-left: 4px solid {S_RED}; height: 180px; overflow-y: auto; text-shadow: 0 0 1px rgba(255,255,255,0.2); }}
                .terminal-box p {{ color: #FFFFFF !important; -webkit-text-fill-color: #FFFFFF !important; margin: 0; }}
                
                button[kind="primary"] {{ background-color: {S_RED} !important; color: white !important; border: 1px solid {S_RED} !important; height: 45px !important; border-radius: 8px !important; display: flex !important; justify-content: center !important; align-items: center !important; }}
                button[kind="primary"] p {{ font-size: 14px !important; font-weight: 600 !important; }}
                
                [data-testid="stHorizontalBlock"] {{ align-items: center !important; }}
                [data-testid="stSidebar"] {{display: none;}}
                header, footer {{visibility: hidden;}}
            </style>
        """, unsafe_allow_html=True)

    def log(self, msg):
        ts = datetime.now().strftime("%H:%M:%S")
        st.session_state.terminal_logs.append(f"[{ts}] {msg}")
        if len(st.session_state.terminal_logs) > 12: st.session_state.terminal_logs.pop(0)

if __name__ == "__main__":
    st.set_page_config(page_title="Firebean Portal", page_icon="🔥", layout="wide")
    
    portal = FirebeanPortal()
    inputs = InputEngine()
    logic = ProgressGate()
    ai_mc = AIDiagnostic()
    sync = SynthesisSync()

    if st.session_state.ai_status == "🟡 INITIALIZING":
        portal.verify_ai()

    if st.session_state.page == 1:
        # ADJUSTED LOGO RATIO (1.8 width to auto-enlarge logo flush with text)
        h1, h2 = st.columns([1.8, 8.2])
        with h1: 
            st.image("https://raw.githubusercontent.com/dickson-crypto/Firebean-app/main/Firebeanlogo2026.png", use_container_width=True)
        with h2: 
            st.markdown('<h1 class="hero-title" style="margin-bottom: 15px !important;">Project<br>Collector.</h1>', unsafe_allow_html=True)
            
            # EVENLY DISTRIBUTED TAB BUTTONS
            b1, b2, b3 = st.columns(3)
            
            # Clean up AI status text to strip emojis for the clean line-icon
            status_text = st.session_state.ai_status.replace("🟢 ", "").replace("🟡 ", "").replace("🔴 ", "")
            
            with b1: 
                # Primary button acting as a status indicator
                st.button(f"○ STATUS: {status_text}", key="btn_status", type="primary", use_container_width=True)
            with b2:
                if st.button("↻ HANDSHAKE", key="header_handshake", type="primary", help="Retry connection", use_container_width=True):
                    portal.log("Manual Handshake Triggered.")
                    st.session_state.ai_status = "🟡 INITIALIZING"; st.rerun()
            with b3:
                if st.button("◑ MODE", key="btn_mode", type="primary", use_container_width=True):
                    st.session_state.dark_mode = not st.session_state.get('dark_mode', False); st.rerun()

        st.markdown('<hr style="border:0; border-bottom:1px dotted #555; margin-top: 20px;">', unsafe_allow_html=True)

        client, project, venue, year, month = inputs.render_identity()
        sel_cat, sel_wwd, sel_sow = inputs.render_framework()
        logo_b, logo_w, photos, encoded_photos = inputs.render_assets()
        
        st.markdown('<div class="sec-header">Strategic Core</div>', unsafe_allow_html=True)
        youtube = st.text_input("YouTube URL (Optional)")
        open_q = st.text_area("Event Brief & Strategic Review", value=st.session_state.form_data.get("open_question", ""), height=120)

        current_data = {"client": client, "project": project, "venue": venue, "year": year, "month": month, "category": sel_cat, "what_we_do": sel_wwd, "scope": sel_sow, "open_question": open_q}
        assets_ok = (bool(logo_b or logo_w) and bool(photos))
        
        mc_answered = 0
        if st.session_state.mc_questions:
            for i, q in enumerate(st.session_state.mc_questions):
                if any(st.session_state.get(f"ans_{i}_{j}", False) for j in range(len(q.get('opts', [])))):
                    mc_answered += 1
        mc_ok = len(st.session_state.mc_questions) > 0 and mc_answered == len(st.session_state.mc_questions)
        percent = logic.calculate(current_data, assets_ok, mc_ok)
        st.markdown(f'<div style="position:fixed; top:25px; right:40px; z-index:1000; width:90px; height:90px; background:#fff; border-radius:50%; display:flex; align-items:center; justify-content:center; box-shadow:0 10px 30px rgba(0,0,0,0.1); border:2px solid #E2231A"><span style="font-size:22px; font-weight:900; color:#E2231A !important; -webkit-text-fill-color:#E2231A !important;">{percent}%</span></div>', unsafe_allow_html=True)

        st.markdown('<div class="sec-header">AI Strategic Diagnostics</div>', unsafe_allow_html=True)
        if percent >= 90:
            if st.button("Analysis photo for 15 MC", type="primary", use_container_width=True):
                with st.status(f"Analyzing with {st.session_state.active_model}..."):
                    res = ai_mc.get_questions(st.session_state.apiKey, st.session_state.active_model, project, open_q, encoded_photos)
                    if res: 
                        st.session_state.mc_questions = res; st.rerun()
                    else: portal.log("Diagnostics Generator Failed. Check Logs.")
            
            if st.session_state.mc_questions:
                st.markdown(f"**Diagnostics Progress: {mc_answered} / {len(st.session_state.mc_questions)} Answered**")
                for i, q in enumerate(st.session_state.mc_questions):
                    st.markdown(f"**Q{i+1}. {q.get('q', '')}**")
                    c_opts = st.columns(len(q.get('opts', [])))
                    for j, opt in enumerate(q.get('opts', [])): c_opts[j].checkbox(opt, key=f"ans_{i}_{j}")
        else: st.info(f"Progress: {percent}% - Complete inputs to unlock AI analysis.")

        if percent >= 100:
            if st.button("PROCEED TO REVIEW 👉", type="primary", use_container_width=True):
                if logo_b: logo_b.seek(0)
                if logo_w: logo_w.seek(0)
                if photos:
                    for p in photos: p.seek(0)
                
                st.session_state.full_assets = {
                    "logo_black": inputs.process_for_db(logo_b, is_logo=True), 
                    "logo_white": inputs.process_for_db(logo_w, is_logo=True), 
                    "photos": [inputs.process_for_db(p, is_logo=False) for p in photos[:8]], 
                    "hero_index": st.session_state.hero_index
                }
                st.session_state.form_data.update(current_data); st.session_state.form_data['youtube'] = youtube
                st.session_state.page = 2; st.rerun()

        st.markdown(f'<div class="terminal-box">' + "".join([f"<p>{log}</p>" for log in st.session_state.terminal_logs]) + '</div>', unsafe_allow_html=True)

    elif st.session_state.page == 2:
        h_l, h_t = st.columns([1, 4])
        h_l.image("https://raw.githubusercontent.com/dickson-crypto/Firebean-app/main/Firebeanlogo2026.png", width=120)
        h_t.markdown('<h1 class="hero-title" style="font-size:72px !important;">Content<br>Review.</h1>', unsafe_allow_html=True)
        if st.button("← BACK"): st.session_state.page = 1; st.rerun()
        
        if not st.session_state.get('generated_content'):
            with st.status(f"Synthesizing Content with {st.session_state.active_model}..."):
                res = sync.generate_ai_content(st.session_state.apiKey, st.session_state.active_model, st.session_state.form_data)
                if res: 
                    st.session_state.generated_content = res; st.rerun()
                else: st.error("Synthesis failed. Please try again.")
        
        if st.session_state.generated_content:
            st.markdown('<div class="sec-header">Logo Previews</div>', unsafe_allow_html=True)
            logo_col1, logo_col2 = st.columns(2)
            
            with logo_col1:
                st.markdown("**Logo Black**")
                if st.session_state.full_assets and st.session_state.full_assets.get("logo_black"):
                    b64_black = st.session_state.full_assets["logo_black"]["data"]
                    mime_b = st.session_state.full_assets["logo_black"].get("mimeType", "image/png")
                    st.markdown(f'<img src="data:{mime_b};base64,{b64_black}" style="max-height: 80px; object-fit: contain;">', unsafe_allow_html=True)
                else: st.caption("No Black Logo uploaded")
                    
            with logo_col2:
                st.markdown("**Logo White**")
                if st.session_state.full_assets and st.session_state.full_assets.get("logo_white"):
                    b64_white = st.session_state.full_assets["logo_white"]["data"]
                    mime_w = st.session_state.full_assets["logo_white"].get("mimeType", "image/png")
                    st.markdown(f'<div style="background-color: #333; padding: 10px; border-radius: 8px; display: inline-block;">'
                                f'<img src="data:{mime_w};base64,{b64_white}" style="max-height: 80px; object-fit: contain;">'
                                f'</div>', unsafe_allow_html=True)
                else: st.caption("No White Logo uploaded")
            
            st.markdown("<br>", unsafe_allow_html=True)
            sync.render_ui(st.session_state.generated_content)
            
            if st.button("🚀 EXECUTE MASTER SYNC", type="primary", use_container_width=True):
                with st.status("Syncing to Master DB..."):
                    if sync.push_to_gas(st.session_state.form_data, st.session_state.generated_content, st.session_state.get('full_assets')):
                        st.success("SYNC SUCCESSFUL"); st.session_state.clear(); st.rerun()
                    else: st.error("GAS Synchronization Failed.")
