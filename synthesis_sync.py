# VERSION: v18.7.3
# TIMESTAMP: 2026-04-04 16:30:00 HKT

import streamlit as st
import requests
import json

class SynthesisSync:
    def __init__(self):
        self.GAS_URL = "https://script.google.com/macros/s/AKfycbyCfSfjgYi7yQFpqBDshjYQ1Zye4VjaT-U4_0nfF9c5oYF1Pr0CrGI38Is4BS3KigIz/exec"

    def generate_ai_content(self, key, active_model, form_data):
        if not active_model or active_model == "NONE":
            active_model = "gemini-1.5-flash"
            
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{active_model}:generateContent?key={key}"
        
        # FIX FOR ISSUE 4: Highly strict JSON prompt template forces AI to fill in every field accurately.
        sys_msg = """Role: Firebean Content Director.
        Output strictly as RAW JSON matching this exact structure:
        {
          "SocialMedia": {
            "LI": "LinkedIn post focusing on ROI and business impact...",
            "FB": "Facebook post with emojis, written in Cantonese tone...",
            "TR": "Threads post, sharp and short...",
            "IG": "Instagram caption starting with a hook, followed by 20 hashtags..."
          },
          "Web": {
            "EN": "<h2>...</h2><p>...</p>",
            "TC": "<h2>...</h2><p>...</p>",
            "JP": "<h2>...</h2><p>...</p>"
          },
          "FAQ": {
            "EN": [{"q":"Question?", "a":"Answer."}],
            "TC": [{"q":"Question?", "a":"Answer."}],
            "JP": [{"q":"Question?", "a":"Answer."}]
          }
        }
        Rules: Web must be 3-4 Paragraphs, 2 H2 tags, and a Bold Slogan at the end. FAQ must be exactly 3 Q&As per language."""
        
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
        # Extremely robust dictionary fallback in case AI renames the JSON keys
        sm = gc.get('SocialMedia') or gc.get('social_media') or gc.get('socialMedia') or {}
        web = gc.get('Web') or gc.get('web') or {}
        faq = gc.get('FAQ') or gc.get('faq') or {}

        # FIX FOR ISSUE 4: Render UI fully opened vertically, without using tabs or drip-downs
        st.markdown('<div class="sec-header">Social Media Suite</div>', unsafe_allow_html=True)
        st.text_area("LinkedIn (English/ROI)", sm.get('LI', ''), height=150)
        st.text_area("Facebook (粵語口吻)", sm.get('FB', ''), height=150)
        st.text_area("Threads (Sharp)", sm.get('TR', ''), height=100)
        st.text_area("Instagram (Hook+Tags)", sm.get('IG', ''), height=100)
        st.markdown("<br>", unsafe_allow_html=True)

        st.markdown('<div class="sec-header">Web Articles</div>', unsafe_allow_html=True)
        st.markdown("**English (EN)**")
        st.markdown(f"<div style='background:#121212; padding:20px; border-radius:8px; border:1px solid #333;'>{web.get('EN', '')}</div>", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("**Trad. Chinese (TC)**")
        st.markdown(f"<div style='background:#121212; padding:20px; border-radius:8px; border:1px solid #333;'>{web.get('TC', '')}</div>", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)

        st.markdown('<div class="sec-header">Strategic FAQ</div>', unsafe_allow_html=True)
        st.json(faq)

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
