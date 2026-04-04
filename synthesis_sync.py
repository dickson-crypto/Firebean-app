# VERSION: v18.8.5
# TIMESTAMP: 2026-04-04 23:15:00 HKT

import streamlit as st
import requests
import json

class SynthesisSync:
    def __init__(self):
        # Using your latest deployment URL
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
        
        # RESTORED & UPGRADED PROMPT: Re-injecting social media rules (v1.9 Guidelines)
        sys_msg = """Role: Firebean Content Director.
        Output strictly as RAW JSON matching this exact structure:
        {
          "Challenge": "Analyze the core problem from the brief in 1 sentence.",
          "Solution": "Outline the creative strategic solution in 1 sentence.",
          "SocialMedia": { "LI": "...", "FB": "...", "TR": "...", "IG": "..." },
          "Web": {
            "EN": "<h1>[Catchy Title]</h1><h2>Strategy & Background</h2><p>...</p><h2>Execution & Review</h2><p>...</p><p><strong>Bold Slogan</strong></p>",
            "TC": "<h1>[引人入勝的標題]</h1><h2>活動策略與背景</h2><p>...</p><h2>執行亮點與事後檢討</h2><p>...</p><p><strong>Bold Slogan</strong></p>",
            "JP": "<h1>[キャッチーなタイトル]</h1><h2>戦略と背景</h2><p>...</p><h2>執行與回顧</h2><p>...</p><p><strong>Bold Slogan</strong></p>"
          },
          "FAQ": { "EN": [], "TC": [], "JP": [] }
        }
        
        CRITICAL CONTENT RULES:
        [LinkedIn (LI)]: 200-300 words. Tone: Authoritative B2B/ROI. Language: English.
        [Facebook (FB)]: ~300 Characters. Tone: Friendly storytelling. Language: Traditional Chinese (HK) with conversational Cantonese slang.
        [Threads (TR)]: 100-200 Characters. Tone: Humorous/Sharp. Language: Authentic HK Cantonese slang. Start with a Hook.
        [Instagram (IG)]: Max 150 Characters. First 2 lines are the slogan. Language: Traditional Chinese (HK). Exactly 20 professional hashtags at the end.
        [Web Content]: Every language version MUST start with a <h1> tag. Followed by 3-4 Paragraphs and 2 H2 tags. End with a <strong>Bold Slogan</strong>.
        [FAQ]: 3 SEO-optimized Q&As per language."""
        
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
        sm = gc.get('SocialMedia') or gc.get('social_media') or {}
        web = gc.get('Web') or gc.get('web') or {}
        
        st.markdown('<div class="sec-header">Strategic Analysis</div>', unsafe_allow_html=True)
        st.text_area("Boring Challenge", gc.get('Challenge', ''), height=80)
        st.text_area("Creative Solution", gc.get('Solution', ''), height=80)

        st.markdown('<div class="sec-header">Social Media Suite</div>', unsafe_allow_html=True)
        st.text_area("LinkedIn", self.get_ci(sm, "", "LI", "linkedin"), height=150)
        st.text_area("Facebook (HK Cantonese)", self.get_ci(sm, "", "FB", "facebook"), height=100)
        st.text_area("Threads (HK Cantonese)", self.get_ci(sm, "", "TR", "threads"), height=100)
        st.text_area("Instagram", self.get_ci(sm, "", "IG", "instagram"), height=100)

        st.markdown('<div class="sec-header">Web Articles</div>', unsafe_allow_html=True)
        for lang in ['EN', 'TC', 'JP']:
            st.markdown(f"**{lang} Preview**")
            st.markdown(self.get_ci(web, '', lang), unsafe_allow_html=True)
            st.markdown("---")

    def push_to_gas(self, form, ai, assets):
        """Normalizes payload and pushes to Google Apps Script Handlers."""
        event_date = f"{form.get('year', '')} {form.get('month', '')}".strip()
        
        web_data = ai.get("Web") or ai.get("web") or {}
        faq_data = ai.get("FAQ") or ai.get("faq") or {}
        sm_data = ai.get("SocialMedia") or ai.get("social_media") or {}

        normalized_ai = {
            "Challenge": ai.get("Challenge", ""),
            "Solution": ai.get("Solution", ""),
            "SocialMedia": {
                "LI": self.get_ci(sm_data, "", "LI", "linkedin"),
                "FB": self.get_ci(sm_data, "", "FB", "facebook"),
                "TR": self.get_ci(sm_data, "", "TR", "threads"),
                "IG": self.get_ci(sm_data, "", "IG", "instagram")
            },
            "Web": {
                "EN": self.get_ci(web_data, "", "EN", "en", "English"),
                "TC": self.get_ci(web_data, "", "TC", "tc", "Traditional Chinese"),
                "JP": self.get_ci(web_data, "", "JP", "jp", "Japanese")
            },
            "FAQ": {
                "EN": self.get_ci(faq_data, [], "EN", "en"),
                "TC": self.get_ci(faq_data, [], "TC", "tc"),
                "JP": self.get_ci(faq_data, [], "JP", "jp")
            }
        }

        payload = {
            **form,
            "date": event_date,
            "category": ", ".join(form.get('category', [])),
            "what_we_do": ", ".join(form.get('what_we_do', [])),
            "scope": "\n".join(form.get('scope', [])),
            "ai_content": normalized_ai,
            "assets": assets if assets else {"logo_black": None, "logo_white": None, "photos": [], "hero_index": 0},
            "challenge": normalized_ai["Challenge"],
            "solution": normalized_ai["Solution"]
        }
        
        try:
            res = requests.post(self.GAS_URL, json=payload, timeout=90)
            return res.status_code == 200
        except Exception: 
            return False
