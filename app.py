# VERSION: v18.9.7 (Production Release - Syntax Fixed)
# TIMESTAMP: 2026-06-18 00:05:00 HKT

import streamlit as st
import requests
import time
from datetime import datetime

class FirebeanPortal:
    def __init__(self):
        if 'terminal_logs' not in st.session_state: 
            st.session_state.terminal_logs = ["> System Boot: Ready."]
        self.sheet_script_url = "https://script.google.com/macros/s/AKfycbw6UuXZqhoFYtEiGYPJmFAWCis9IN-M-NVYN8hEo-Ux6UKKloihhv4yScS6ocGEJ9Em/exec"

    def log(self, msg):
        ts = datetime.now().strftime("%H:%M:%S")
        st.session_state.terminal_logs.append(f"[{ts}] {msg}")
        if len(st.session_state.terminal_logs) > 15: st.session_state.terminal_logs.pop(0)

    def test_sync_to_db(self):
        dummy_data = {
            "client": "TEST_CLIENT_001",
            "project": "DUMMY_PROJECT_SYNC_TEST",
            "date": "2026-06-17",
            "venue": "Test Location",
            "category": "Test Category",
            "what_we_do": "Data Verification",
            "scope": "Connectivity Check",
            "sort_date": "2026-06-01"
        }
        self.log("TEST: Initiating dummy sync...")
        try:
            res = requests.post(self.sheet_script_url, json=dummy_data, timeout=60)
            self.log(f"TEST: Status Code -> {res.status_code}")
            return res.status_code == 200
        except Exception as e:
            self.log(f"TEST CRITICAL: {str(e)}")
            return False

# --- UI Render ---
portal = FirebeanPortal()
st.title("Firebean CMS v18.9.7")

if st.button("🚀 PUSH DUMMY DATA"):
    with st.spinner("Syncing..."):
        portal.test_sync_to_db()

# FIXED: Removed f-string to prevent syntax errors with internal curly braces
logs_html = "".join([f"<p>{log}</p>" for log in st.session_state.terminal_logs])
st.markdown("### System Logs")
st.markdown(
    '<div style="background:#000; color:#0F0; padding:10px; font-family:monospace; height:200px; overflow-y:auto;">' + logs_html + '</div>', 
    unsafe_allow_html=True
)
