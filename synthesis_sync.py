import streamlit as st
import requests
import json

class SynthesisSync:
    def __init__(self):
        self.GAS_URL = "https://script.google.com/macros/s/AKfycbyCfSfjgYi7yQFpqBDshjYQ1Zye4VjaT-U4_0nfF9c5oYF1Pr0CrGI38Is4BS3KigIz/exec"

    def generate(self, model, key, form_data):
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
        sys_msg = """
        Role: Firebean Content Director. Focus: Event Brief & Strategic Review.
        Platform Rules v2.2:
        - LinkedIn: Pro English, ROI, 200-300 words.
        - Facebook: Cantonese (唔,係,嘅), ~300 chars.
        - Threads: Independent 100-200 chars reflection.
        - Instagram: 2 lines hook + 20 tags.
        - Web Content: 3-4 Paragraphs, H2 headers, Bold Slogan at end.
        - FAQ: Multi-lingual JSON.
        Output: Clean JSON.
        """
        ctx = f"Client: {form_data['client']}. Core: {form_data['open_question']}"
        try:
            res = requests.post(url, json={"contents": [{"role": "user", "parts": [{"text": ctx}]}], "systemInstruction": {"parts": [{"text": sys_msg}]}, "generationConfig": {"responseMimeType": "application/json"}}, timeout=90)
            if res.status_code == 200:
                raw = res.json()['candidates'][0]['content']['parts'][0]['text']
                return json.loads(raw.replace("```json", "").replace("```", ""))
        except: return None

    def render_preview(self, gc):
        sm = gc.get('SocialMedia', {})
        t1, t2, t3 = st.tabs(["Social Suite", "Web Articles", "Strategic FAQ"])
        with t1:
            st.text_area("LinkedIn", sm.get('LI', ''), height=150)
            st.text_area("Facebook (Cantonese)", sm.get('FB', ''), height=100)
            st.text_area("Threads (Sharp Reflection)", sm.get('TR', ''), height=100)
        with t2:
            st.markdown(gc.get('Web', {}).get('EN', ''), unsafe_allow_html=True)
            with st.expander("TC"): st.markdown(gc.get('Web', {}).get('TC', ''), unsafe_allow_html=True)
        with t3: st.json(gc.get('FAQ', {}))

    def sync_to_db(self, form, ai, assets):
        payload = {
            **form,
            "category": ", ".join(form['category']),
            "what_we_do": ", ".join(form['what_we_do']),
            "scope": "\n".join(form['scope']),
            "ai_content": ai,
            "assets": assets
        }
        try:
            res = requests.post(self.GAS_URL, json=payload)
            return res.status_code == 200
        except: return False
