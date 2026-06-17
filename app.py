# VERSION: v18.9.12 (Refactored for Python Native Logic)
# TIMESTAMP: 2026-06-18 00:20:00 HKT

import streamlit as st
import requests
import time
from datetime import datetime

# --- Modular Imports ---
try:
    from inputs_module import InputEngine
    from progress_logic import ProgressGate
    from ai_diagnostics import AIDiagnostic
    from synthesis_sync import SynthesisSync
except ImportError as e:
    st.error(f"Module Error: {e}")
    st.stop()

class FirebeanPortal:
    def __init__(self):
        self.VERSION = "v18.9.12"
        self.MODELS = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]
        self.ICONS = {
            "PHOTO": '<svg width="120" height="120" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="1.5"><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/></svg>',
            "LIST": '<svg width="120" height="120" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="1.5"><line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/><line x1="8" y1="18" x2="21" y2="18"/></svg>',
            "BRAIN": '<svg width="120" height="120" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="1.5"><rect x="4" y="4" width="16" height="16" rx="2"/><rect x="9" y="9" width="6" height="6"/></svg>',
            "TARGET": '<svg width="120" height="120" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="1.5"><circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/></svg>',
            "SOCIAL": '<svg width="120" height="120" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="1.5"><rect x="5" y="2" width="14" height="20" rx="2"/><line x1="12" y1="18" x2="12.01" y2="18"/></svg>',
            "WEB": '<svg width="120" height="120" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="1.5"><circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/></svg>',
            "LAYERS": '<svg width="120" height="120" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="1.5"><polygon points="12 2 2 7 12 12 22 7 12 2"/></svg>',
            "CLOUD": '<svg width="120" height="120" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="1.5"><path d="M18 10h-1.26A8 8 0 1 0 9 20h9a5 5 0 0 0 0-10z"/></svg>',
            "DB": '<svg width="120" height="120" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="1.5"><ellipse cx="12" cy="5" rx="9" ry="3"/></svg>'
        }
        self.init_session()

    def init_session(self):
        if 'page' not in st.session_state: st.session_state.page = 1
        if 'terminal_logs' not in st.session_state: st.session_state.terminal_logs = [f"> Boot: {self.VERSION}"]
        if 'ai_status' not in st.session_state: st.session_state.ai_status = "🟡 INITIALIZING"
        if 'form_data' not in st.session_state: st.session_state.form_data = {}

    def log(self, msg):
        # Use Python string formatting instead of JavaScript padStart
        ts = datetime.now().strftime("%H:%M:%S")
        st.session_state.terminal_logs.append(f"[{ts}] {msg}")
        if len(st.session_state.terminal_logs) > 10: st.session_state.terminal_logs.pop(0)

    def run_with_overlay(self, steps, task_func, *args):
        overlay = st.empty()
        for icon, text in steps:
            overlay.markdown(f'''
                <div style="position:fixed; top:0; left:0; width:100vw; height:100vh; background:#121212; z-index:9999; display:flex; justify-content:center; align-items:center;">
                    <div style="text-align:center;">{icon}<h2 style="color:white;">{text}</h2></div>
                </div>
            ''', unsafe_allow_html=True)
            time.sleep(0.8)
        res = task_func(*args)
        overlay.empty()
        return res

# --- APP EXECUTION ---
if __name__ == "__main__":
    st.set_page_config(page_title="Firebean Portal", layout="wide")
    portal = FirebeanPortal()
    inputs, logic, ai_mc, sync = InputEngine(), ProgressGate(), AIDiagnostic(), SynthesisSync()

    st.markdown("""<style>
        .stApp { background-color: #121212; color: white; }
        .terminal-box { background: #000; padding: 15px; border-left: 4px solid #E2231A; height: 150px; overflow-y: auto; font-family: monospace; }
    </style>""", unsafe_allow_html=True)

    # --- Header ---
    c1, c2 = st.columns([1, 9])
    with c1: st.image("https://raw.githubusercontent.com/dickson-crypto/Firebean-app/main/Firebeanlogo2026.png")
    with c2: st.markdown("<h1>Project Collector.</h1>", unsafe_allow_html=True)

    if st.session_state.page == 1:
        client, project, venue, year, month = inputs.render_identity()
        if st.button("PROCEED TO REVIEW"):
            st.session_state.page = 2
            st.rerun()

    elif st.session_state.page == 2:
        if st.button("← BACK"):
            st.session_state.page = 1
            st.rerun()
        if st.button("🚀 EXECUTE MASTER SYNC", type="primary"):
            steps = [(portal.ICONS["DB"], "WRITING TO MASTER DB")]
            portal.run_with_overlay(steps, lambda: True)
            st.success("Sync Complete.")

    # --- Persistent Terminal ---
    st.markdown('<div class="terminal-box">' + "".join([f"<p>{log}</p>" for log in st.session_state.terminal_logs]) + '</div>', unsafe_allow_html=True)
