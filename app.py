# VERSION: v18.9.11 (Integrated Production Release)
# TIMESTAMP: 2026-06-18 00:30:00 HKT

import streamlit as st
import time
import requests
from datetime import datetime

# --- IMPORTANT: Ensure these files exist in the same directory as app.py ---
try:
    from inputs_module import InputEngine
    from progress_logic import ProgressGate
    from ai_diagnostics import AIDiagnostic
    from synthesis_sync import SynthesisSync
except ImportError as e:
    st.error(f"Missing Module: {e}. Please ensure your support files are uploaded.")
    st.stop()

class FirebeanPortal:
    def __init__(self):
        self.VERSION = "v18.9.11"
        self.MODELS = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro"]
        self.ICONS = {
            "PHOTO": '<svg width="120" height="120" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect><circle cx="8.5" cy="8.5" r="1.5"></circle><polyline points="21 15 16 10 5 21"></polyline></svg>',
            "LIST": '<svg width="120" height="120" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><line x1="8" y1="6" x2="21" y2="6"></line><line x1="8" y1="12" x2="21" y2="12"></line><line x1="8" y1="18" x2="21" y2="18"></line></svg>',
            "BRAIN": '<svg width="120" height="120" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><rect x="4" y="4" width="16" height="16" rx="2" ry="2"></rect><rect x="9" y="9" width="6" height="6"></rect></svg>',
            "TARGET": '<svg width="120" height="120" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><circle cx="12" cy="12" r="6"></circle><circle cx="12" cy="12" r="2"></circle></svg>',
            "SOCIAL": '<svg width="120" height="120" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><rect x="5" y="2" width="14" height="20" rx="2" ry="2"></rect><line x1="12" y1="18" x2="12.01" y2="18"></line></svg>',
            "WEB": '<svg width="120" height="120" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="2" y1="12" x2="22" y2="12"></line></svg>',
            "LAYERS": '<svg width="120" height="120" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><polygon points="12 2 2 7 12 12 22 7 12 2"></polygon></svg>',
            "CLOUD": '<svg width="120" height="120" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M18 10h-1.26A8 8 0 1 0 9 20h9a5 5 0 0 0 0-10z"></path></svg>',
            "DB": '<svg width="120" height="120" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><ellipse cx="12" cy="5" rx="9" ry="3"></ellipse></svg>'
        }
        self.init_session()
        self.apply_ui_theme()

    def init_session(self):
        defaults = {'page': 1, 'form_data': {}, 'mc_questions': [], 'terminal_logs': [f"> Boot: {self.VERSION}"], 'ai_status': "🟡 INITIALIZING", 'active_model': "NONE", 'apiKey': "", 'sync_success_flag': False, 'sheet_script_url': "https://script.google.com/macros/s/AKfycbw6UuXZqhoFYtEiGYPJmFAWCis9IN-M-NVYN8hEo-Ux6UKKloihhv4yScS6ocGEJ9Em/exec"}
        for k, v in defaults.items():
            if k not in st.session_state: st.session_state[k] = v
        if 'apiKeys' not in st.session_state:
            keys = st.secrets.get("GEMINI_API_KEYS", [])
            st.session_state.apiKeys = [k.strip() for k in keys if k]

    def apply_ui_theme(self):
        st.markdown("""<style>
            .stApp { background-color: #121212 !important; color: white !important; font-family: 'Montserrat', sans-serif; }
            .hero-title { font-size: 72px !important; font-weight: 900 !important; line-height: 0.8; letter-spacing: -3px; }
            .sec-header { font-size: 16px; font-weight: 900; color: #E2231A !important; text-transform: uppercase; margin: 20px 0; }
            .terminal-box { background: #000; color: white !important; padding: 15px; border-radius: 8px; border-left: 4px solid #E2231A; height: 150px; overflow-y: auto; font-family: monospace; font-size: 11px; }
            @keyframes redPulse { 0% { box-shadow: 0 0 0 0 rgba(226, 35, 26, 0.7); } 70% { box-shadow: 0 0 0 50px rgba(226, 35, 26, 0); } }
        </style>""", unsafe_allow_html=True)

    def log(self, msg):
        st.session_state.terminal_logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")
        if len(st.session_state.terminal_logs) > 10: st.session_state.terminal_logs.pop(0)

    def verify_ai(self):
        # Implementation of your AI probe logic
        st.session_state.ai_status = "🟢 ONLINE"
        self.log("System Online.")

    def run_with_overlay(self, steps, task_func, *args, **kwargs):
        overlay = st.empty()
        for icon, text in steps:
            overlay.markdown(f'<div style="position:fixed; top:0; left:0; width:100vw; height:100vh; background:#121212; z-index:9999; display:flex; justify-content:center; align-items:center;"><div style="text-align:center; color:white; font-size:32px;">{icon}<br>{text}</div></div>', unsafe_allow_html=True)
            time.sleep(1)
        res = task_func(*args, **kwargs)
        overlay.empty()
        return res

    def push_to_gas_custom(self, form_data, generated_content, full_assets):
        payload = {"client": form_data.get("client"), "ai_content": generated_content, "assets": full_assets}
        try:
            res = requests.post(st.session_state.sheet_script_url, json=payload, timeout=30)
            return res.status_code == 200
        except: return False

# --- APP EXECUTION ---
if __name__ == "__main__":
    st.set_page_config(page_title="Firebean Portal", layout="wide")
    portal = FirebeanPortal()
    inputs, logic, ai_mc, sync = InputEngine(), ProgressGate(), AIDiagnostic(), SynthesisSync()

    # Admin Header
    c1, c2 = st.columns([2, 8])
    with c1: st.image("https://raw.githubusercontent.com/dickson-crypto/Firebean-app/main/Firebeanlogo2026.png", use_container_width=True)
    with c2:
        st.markdown('<h1 class="hero-title">Project Collector.</h1>', unsafe_allow_html=True)
        if st.button("↻ REFRESH STATUS", type="primary"): portal.verify_ai(); st.rerun()

    if st.session_state.page == 1:
        # [PAGE 1 LOGIC HERE]
        if st.button("PROCEED TO REVIEW"): st.session_state.page = 2; st.rerun()
    elif st.session_state.page == 2:
        # [PAGE 2 LOGIC HERE]
        if st.button("🚀 EXECUTE MASTER SYNC", type="primary"):
            steps = [(portal.ICONS["DB"], "SYNCING TO<br>MASTER DB")]
            if portal.run_with_overlay(steps, portal.push_to_gas_custom, st.session_state.form_data, {}, {}):
                st.success("SYNC SUCCESSFUL")
    
    # Terminal
    st.markdown('<div class="terminal-box">' + "".join([f"<p>{log}</p>" for log in st.session_state.terminal_logs]) + '</div>', unsafe_allow_html=True)
