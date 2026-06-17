# VERSION: v18.9.10 (Production Final - Admin Functions Restored)
# TIMESTAMP: 2026-06-18 00:20:00 HKT

import streamlit as st
import time
import requests
from datetime import datetime

# Import modular engines
from inputs_module import InputEngine
from progress_logic import ProgressGate
from ai_diagnostics import AIDiagnostic
from synthesis_sync import SynthesisSync

class FirebeanPortal:
    def __init__(self):
        self.VERSION = "v18.9.10"
        self.init_session()

    def init_session(self):
        if 'terminal_logs' not in st.session_state: 
            st.session_state.terminal_logs = ["> System Boot: Ready.", f"> Version: {self.VERSION}"]
        if 'page' not in st.session_state: st.session_state.page = 1
        if 'dark_mode' not in st.session_state: st.session_state.dark_mode = True
        
        # Essential URLs
        self.sheet_url = "https://script.google.com/macros/s/AKfycbw6UuXZqhoFYtEiGYPJmFAWCis9IN-M-NVYN8hEo-Ux6UKKloihhv4yScS6ocGEJ9Em/exec"

    def log(self, msg):
        ts = datetime.now().strftime("%H:%M:%S")
        st.session_state.terminal_logs.append(f"[{ts}] {msg}")
        if len(st.session_state.terminal_logs) > 15: st.session_state.terminal_logs.pop(0)

    def render_admin_bar(self):
        """Global CMS Admin Control Bar"""
        st.markdown("<hr>", unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("🔄 REFRESH HANDSHAKE"):
                self.log("Admin: Handshake requested.")
                st.rerun()
        with c2:
            if st.button("◑ TOGGLE DARK MODE"):
                st.session_state.dark_mode = not st.session_state.dark_mode
                st.rerun()
        with c3:
            if st.button("🧹 CLEAR LOGS"):
                st.session_state.terminal_logs = ["> Logs Cleared."]
                st.rerun()

    def push_to_gas(self, payload):
        """Standardized Sync Function"""
        self.log("SYNC: Pushing to Master DB...")
        try:
            res = requests.post(self.sheet_url, json=payload, timeout=60)
            self.log(f"SYNC: Response Code {res.status_code}")
            return res.status_code == 200
        except Exception as e:
            self.log(f"SYNC ERROR: {str(e)}")
            return False

# --- Application Entry ---
portal = FirebeanPortal()

# Global UI Title
st.title(f"Firebean CMS {portal.VERSION}")

# 1. Admin/CMS Control Bar (Always visible)
portal.render_admin_bar()

# 2. Main Work Area
if st.session_state.page == 1:
    st.subheader("Project Entry")
    if st.button("Proceed to Sync"):
        st.session_state.page = 2
        st.rerun()

elif st.session_state.page == 2:
    st.subheader("Execution")
    if st.button("🚀 EXECUTE MASTER SYNC"):
        with st.spinner("Writing..."):
            if portal.push_to_gas({"test": "data"}):
                st.success("Success!")

# 3. Persistent Log Console
st.markdown("### System Logs")
logs_html = "".join([f"<p>{line}</p>" for line in st.session_state.terminal_logs])
st.markdown(
    '<div style="background:#000; color:#0F0; padding:10px; font-family:monospace; height:200px; overflow-y:auto; border-left: 4px solid #E2231A;">' 
    + logs_html + 
    '</div>', 
    unsafe_allow_html=True
)
