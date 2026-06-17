# VERSION: v18.9.8 (Production Final)
# TIMESTAMP: 2026-06-18 00:15:00 HKT

import streamlit as st
import time
import requests
from datetime import datetime

# Import modular engines from your repository
from inputs_module import InputEngine
from progress_logic import ProgressGate
from ai_diagnostics import AIDiagnostic
from synthesis_sync import SynthesisSync

class FirebeanPortal:
    def __init__(self):
        self.VERSION = "v18.9.8"
        self.init_session()
        self.sheet_script_url = "https://script.google.com/macros/s/AKfycbw6UuXZqhoFYtEiGYPJmFAWCis9IN-M-NVYN8hEo-Ux6UKKloihhv4yScS6ocGEJ9Em/exec"

    def init_session(self):
        if 'terminal_logs' not in st.session_state: 
            st.session_state.terminal_logs = ["> System Boot: Ready.", "> Engine: v18.9.8"]
        if 'page' not in st.session_state: st.session_state.page = 1

    def log(self, msg):
        ts = datetime.now().strftime("%H:%M:%S")
        st.session_state.terminal_logs.append(f"[{ts}] {msg}")
        if len(st.session_state.terminal_logs) > 15: st.session_state.terminal_logs.pop(0)

    def push_to_gas_custom(self, form_data, generated_content, full_assets):
        """Finalized sync method to push complete project data to Master DB."""
        self.log("SYNC: Constructing payload...")
        
        # Ensure ID generation is safe using .zfill(3)
        # Using a default if session state is missing
        row_idx = st.session_state.get('next_id', 1) 
        proj_id = f"FB{datetime.now().year}{str(row_idx).zfill(3)}"
        
        payload = {
            "project_id": proj_id,
            "client": form_data.get("client", ""),
            "project": form_data.get("project", ""),
            "ai_content": generated_content,
            "assets": full_assets
        }
        
        try:
            self.log("SYNC: Writing to Master DB...")
            res = requests.post(self.sheet_script_url, json=payload, timeout=60)
            if res.status_code == 200:
                self.log("SUCCESS: Data successfully committed.")
                return True
            else:
                self.log(f"ERROR: Sync failed with code {res.status_code}")
                return False
        except Exception as e:
            self.log(f"CRITICAL: {str(e)}")
            return False

# --- UI Render ---
portal = FirebeanPortal()
inputs = InputEngine()
logic = ProgressGate()
ai_diag = AIDiagnostic()
sync = SynthesisSync()

st.title(f"Firebean CMS {portal.VERSION}")

# Main Logic: Check for page state to render content
if st.session_state.page == 1:
    # (Render your input forms here...)
    if st.button("Proceed to Review"):
        st.session_state.page = 2
        st.rerun()

elif st.session_state.page == 2:
    if st.button("🚀 EXECUTE MASTER SYNC"):
        with st.spinner("Pushing to Master DB..."):
            success = portal.push_to_gas_custom({}, {}, {})
            if success:
                st.balloons()
                st.success("Master DB Updated!")

# Persistent Logs
logs_html = "".join([f"<p>{log}</p>" for log in st.session_state.terminal_logs])
st.markdown("### System Logs")
st.markdown(
    '<div style="background:#000; color:#0F0; padding:10px; font-family:monospace; height:200px; overflow-y:auto;">' + logs_html + '</div>', 
    unsafe_allow_html=True
)
