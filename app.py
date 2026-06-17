import streamlit as st
import io
import base64
import time
import requests
import re
from datetime import datetime

# --- YOUR EXISTING IMPORTS ---
# Ensure these modules exist in your GitHub root
try:
    from inputs_module import InputEngine
    from progress_logic import ProgressGate
    from ai_diagnostics import AIDiagnostic
    from synthesis_sync import SynthesisSync
except:
    pass

class FirebeanPortal:
    def __init__(self):
        self.init_session()
        self.apply_ui_theme()
        # [Icons omitted for brevity - same as before]

    def init_session(self):
        if 'terminal_logs' not in st.session_state: 
            st.session_state.terminal_logs = ["> System Boot: Ready."]
        if 'sheet_script_url' not in st.session_state:
            st.session_state.sheet_script_url = "https://script.google.com/macros/s/AKfycbw6UuXZqhoFYtEiGYPJmFAWCis9IN-M-NVYN8hEo-Ux6UKKloihhv4yScS6ocGEJ9Em/exec"

    def log(self, msg):
        ts = datetime.now().strftime("%H:%M:%S")
        st.session_state.terminal_logs.append(f"[{ts}] {msg}")
        # Automatically scroll by keeping last 15 entries
        if len(st.session_state.terminal_logs) > 15: st.session_state.terminal_logs.pop(0)

    def push_to_gas_custom(self, form_data, generated_content, full_assets):
        """
        Debug-enhanced sync method.
        """
        self.log("DEBUG: Preparing Payload structure...")
        
        # Construct simplified payload for debugging
        payload = {
            "client": form_data.get("client", ""),
            "project": form_data.get("project", ""),
            "assets": full_assets
        }
        
        try:
            self.log(f"DEBUG: Connecting to GAS endpoint...")
            # Added timeout=60 to prevent indefinite hanging
            res = requests.post(st.session_state.sheet_script_url, json=payload, timeout=60)
            
            self.log(f"DEBUG: Response Code -> {res.status_code}")
            self.log(f"DEBUG: Server says -> {res.text[:50]}")
            
            if res.status_code == 200:
                self.log("SUCCESS: Data received by Master DB.")
                return True
            else:
                self.log(f"ERROR: Server returned {res.status_code}")
                return False
        except Exception as e:
            self.log(f"CRITICAL ERROR: {str(e)}")
            return False

    def apply_ui_theme(self):
        # Your existing CSS styles
        st.markdown("""
            <style>
                .terminal-box { background: #000; color: #0F0; font-family: monospace; padding: 10px; border-radius: 5px; height: 200px; overflow-y: auto; }
            </style>
        """, unsafe_allow_html=True)

# Main Execution Flow
if __name__ == "__main__":
    portal = FirebeanPortal()
    
    st.title("Firebean CMS Portal")
    
    # UI logic to trigger the sync
    if st.button("EXECUTE MASTER SYNC"):
        # The logic that previously got you stuck:
        with st.spinner("Writing to Master DB..."):
            # This triggers the debug logs to appear in the terminal box below
            success = portal.push_to_gas_custom({"client": "test"}, {}, {})
            if success:
                st.success("Synced!")
    
    # Persistent Terminal Box for debugging
    st.markdown("### System Logs")
    st.markdown('<div class="terminal-box">' + "".join([f"<p>{log}</p>" for log in st.session_state.terminal_logs]) + '</div>', unsafe_allow_html=True)
