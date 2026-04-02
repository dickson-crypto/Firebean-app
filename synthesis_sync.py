# VERSION: v18.6.3
# TIMESTAMP: 2026-04-02 10:00:00 HKT

import streamlit as st
import requests
import json

class SynthesisSync:
    def __init__(self):
        self.GAS_URL = "https://script.google.com/macros/s/AKfycbyCfSfjgYi7yQFpqBDshjYQ1Zye4VjaT-U4_0nfF9c5oYF1Pr0CrGI38Is4BS3KigIz/exec"

    def generate_ai_content(self, key, active_model, form_data):
        # Fallback in case active_model wasn't passed correctly
        if not active_model or active_model == "NONE":
            active_model = "gemini-1.5-flash"
            
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{active_model}:generateContent?key={key}"
        sys_msg = "Role: Firebean Content Director. Rules v2.2: LinkedIn (ROI Focus, EN), Facebook (粵語口吻, ~300 chars), Threads (Sharp), Web (3-4 Para, 2 H2, Bold Slogan), FAQ (JSON). Return RAW JSON."
        ctx = f"Client: {form_data.get('client', '')}. Project: {form_data.get('project', '')}. Core Strategy: {form_data.get('open_question', '')}"
        
        payload = {
            "contents": [{"role": "user", "parts": [{"text": ctx}]}],
            "systemInstruction": {"parts": [{"text": sys_msg}]},
            "generationConfig": {"responseMimeType": "application/json"}
        }
        
        try:
            res = requests.post(url, json=payload, timeout=90)
            if res.status_code == 200:
                raw = res.json()['candidates'][0]['content']['parts'][0]['text']
                clean = raw.replace("```json", "").replace("```", "").strip()
                return json.loads(clean)
            else:
                return None
        except Exception: 
            return None

    def render_ui(self, gc):
        sm = gc.get('SocialMedia', {})
        t1, t2, t3 = st.tabs(["Social Suite", "Web Article", "Strategic FAQ"])
        with t1:
            st.text_area("LinkedIn (English/ROI)", sm.get('LI', ''), height=150)
            st.text_area("Facebook (粵語口吻)", sm.get('FB', ''), height=100)
            st.text_area("Threads (Sharp)", sm.get('TR', ''), height=80)
        with t2:
            st.markdown(gc.get('Web', {}).get('EN', ''), unsafe_allow_html=True)
            with st.expander("Trad. Chinese Translation"):
                st.markdown(gc.get('Web', {}).get('TC', ''), unsafe_allow_html=True)
        with t3:
            st.json(gc.get('FAQ', {}))

    def push_to_gas(self, form, ai, assets):
        payload = {
            **form,
            "category": ", ".join(form.get('category', [])),
            "what_we_do": ", ".join(form.get('what_we_do', [])),
            "scope": "\n".join(form.get('scope', [])),
            "ai_content": ai,
            "assets": assets
        }
        try:
            res = requests.post(self.GAS_URL, json=payload)
            return res.status_code == 200
        except Exception: 
            return False
