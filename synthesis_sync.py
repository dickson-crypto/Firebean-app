# VERSION: v18.8.4
# TIMESTAMP: 2026-04-04 22:45:00 HKT

import streamlit as st
import requests
import json

class SynthesisSync:
    def __init__(self):
        self.GAS_URL = "https://script.google.com/macros/s/AKfycbycZnD493RrdTPwUJvXBiGNfg6hf0_AHGzo99ZkeeDtlM66TZFbObWbJVuEfOPe-6Fk/exec"

    def get_ci(self, d, default, *keys):
        """Case-insensitive and robust dictionary key lookup."""
        if not isinstance(d, dict): return default
        for k, v in d.items():
            for key in keys:
                if k.lower() == key.lower(): return v
        return default

    def generate_ai_content(self, key, active_model, form_data):
        if not active_model or active_model == "NONE":
            active_model = "gemini-1.5-flash"
            
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{active_model}:generateContent?key={key}"
        
        # UPGRADED PROMPT: Strictly enforces <h1> inclusion for Web Content
        sys_msg = """Role: Firebean Content Director.
        Output strictly as RAW JSON matching this exact structure:
        {
          "Challenge": "Analyze the core problem from the brief in 1 sentence.",
          "Solution": "Outline the creative strategic solution in 1 sentence.",
          "SocialMedia": { "LI": "...", "FB": "...", "TR": "...", "IG": "..." },
          "Web": {
            "EN": "<h1>[Catchy Title]</h1><h2>Strategy & Background</h2><p>...</p><h2>Execution & Review</h2><p>...</p><p><strong>Bold Slogan</strong></p>",
            "TC": "<h1>[引人入勝的標題]</h1><h2>活動策略與背景</h2><p>...</p><h2>執行亮點與事後檢討</h2><p>...</p><p><strong>Bold Slogan</strong></p>",
            "JP": "<h1>[キャッチーなタイトル]</h1><h2>戦略と背景</h2><p>...</p><h2>実行とレビュー</h2><p>...</p><p><strong>Bold Slogan</strong></p>"
          },
          "FAQ": { "EN": [], "TC": [], "JP": [] }
        }
        
        CRITICAL RULES:
        [Web Content]: Every language version MUST start with a <h1> tag containing a creative project title.
        Followed by exactly 3-4 Paragraphs and 2 H2 tags as specified.
        Must end with a <strong>Bold Slogan</strong>."""
        
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
            return None
        except Exception: 
            return None

    def render_ui(self, gc):
        # UI rendering logic...
        sm = gc.get('SocialMedia') or {}
        web = gc.get('Web') or {}
        
        st.markdown('<div class="sec-header">Strategic Analysis</div>', unsafe_allow_html=True)
        st.text_area("Boring Challenge", gc.get('Challenge', ''), height=80)
        st.text_area("Creative Solution", gc.get('Solution', ''), height=80)

        st.markdown('<div class="sec-header">Web Articles</div>', unsafe_allow_html=True)
        for lang in ['EN', 'TC', 'JP']:
            st.markdown(f"**{lang} Preview**")
            st.markdown(self.get_ci(web, '', lang), unsafe_allow_html=True)
            st.markdown("---")

    def push_to_gas(self, form, ai, assets):
        # Push logic remains the same...
        pass
