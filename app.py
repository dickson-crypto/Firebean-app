# VERSION: v18.9.6 (Production Release - Debug Enabled)
# TIMESTAMP: 2026-06-17 23:58:00 HKT

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
        """Pushes a fixed dummy payload to verify connectivity."""
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
        
        self.log("TEST: Initiating dummy payload sync...")
        try:
            # 60-second timeout ensures the app doesn't hang
            res = requests.post(self.sheet_script_url, json=dummy_data, timeout=60)
            self.log(f"TEST: Status Code -> {res.status_code}")
            self.log(f"TEST: Server Response -> {res.text[:100]}")
            return res.status_code == 200
        except Exception as e:
            self.log(f"TEST CRITICAL: {str(e)}")
            return False

# --- UI Render ---
portal = FirebeanPortal()

st.title("Firebean CMS v18.9.6")

# Dedicated Test Section
with st.expander("🛠️ Developer Tools"):
    if st.button("🚀 PUSH DUMMY DATA TO MASTER DB"):
        with st.spinner("Syncing..."):
            success = portal.test_sync_to_db()
            if success:
                st.success("Dummy data sent! Check your Google Sheet.")
            else:
                st.error("Sync failed. Check terminal logs.")

# Terminal Display
st.markdown("### System Logs")
st.markdown(f'<div style="background:#000; color:#0F0; padding
