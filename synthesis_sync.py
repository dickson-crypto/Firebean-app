# VERSION: v19.0.5
# TIMESTAMP: 2026-04-05 01:00:00 HKT

import streamlit as st
import requests
import json

class SynthesisSync:
    def __init__(self):
        # Your latest deployment URL
        self.GAS_URL = "https://script.google.com/macros/s/AKfycbycZnD493RrdTPwUJvXBiGNfg6hf0_AHGzo99ZkeeDtlM66TZFbObWbJVuEfOPe-6Fk/exec"

    def get_ci(self, d, default, *keys):
        """Case-insensitive dictionary lookup to prevent AI key errors."""
        if not isinstance(d, dict): return default
        for k, v in d.items():
            for key in keys:
                if k.lower() == key.lower(): return v
        return default

    def generate_ai_content(self, key, active_model, form_data):
        if not active_model or active_model == "NONE":
            active_model = "gemini-1.5-flash"
            
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{active_model}:generateContent?key={key}"
        
        # SEO & AEO OPTIMIZED PROMPT + EDITORIAL STYLE ENGINE
        sys_msg = """Role: Chief Editor and B2B/B2C Specialist focused on SEO/AEO.
        Objective: Transform project data into a 500-word feature article and localized social suite.

        ### WRITING PROTOCOL (Diversity Engine):
        RANDOMLY SELECT ONLY ONE: Thought Leadership, Contrarian, Human-Centric, Analytical (PAS), or Insider VIP.

        ### SOCIAL MEDIA TONE & MANNER:
        - FB: ~150 words. Friendly storytelling. Trad. Chinese (HK) + Cantonese slang. Use "you" (你).
        - IG: < 150 chars. Hook in first 125 chars. "Behind-the-scenes" vibe. Cantonese nuances. Exactly 20 professional hashtags.
        - TR: < 50 chars. Humorous/Sharp.地道廣東話. Start with a question/anti-traditional view.
        - LI: 150-300 words. Authoritative B2B English. ROI focused.

        ### WEB ARTICLE STRUCTURE:
        - H1 Title: SEO Headline.
        - Subtitles: H2 tags for narrative sections.
        - Word Count: ~500 words.
        - Punchline: One bold memborable concluding sentence in <strong>.
        - FAQ: Exactly 3 AEO-optimized Q&As at the end.

        JSON OUTPUT STRUCTURE:
        {
          "WritingStyleUsed": "[Style]",
          "Challenge": "[Summary]",
          "Solution": "[ROI Summary]",
          "SocialMedia": { "LI": "...", "FB": "...", "TR": "...", "IG": "..." },
          "Web": { "EN": "...", "TC": "...", "JP": "..." },
          "FAQ": { "EN": [], "TC": [], "JP": [] }
        }
        """
        
        ctx = f"Client: {form_data.get('client', '')}. Project: {form_data.get('project', '')}. Strategic Brief: {form_data.get('open_question', '')}"
        
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
        except Exception: return None

    def render_ui(self, gc):
        style = gc.get('WritingStyleUsed', 'Standard')
        st.success(f"🎨 Editorial Style: {style} | 🚀 SEO & AEO Optimized")
        sm = gc.get('SocialMedia') or {}
        web = gc.get('Web') or {}
        
        st.markdown('<div class="sec-header">Strategic Analysis</div>', unsafe_allow_html=True)
        st.text_area("Boring Challenge", gc.get('Challenge', ''), height=80)
        st.text_area("Creative Solution", gc.get('Solution', ''), height=80)

        st.markdown('<div class="sec-header">Social Media Suite</div>', unsafe_allow_html=True)
        t_li, t_fb, t_tr, t_ig = st.tabs(["LinkedIn", "Facebook (HK)", "Threads (HK)", "Instagram (HK)"])
        with t_li: st.text_area("LI Copy", self.get_ci(sm, "", "LI", "linkedin"), height=250)
        with t_fb: st.text_area("FB Copy", self.get_ci(sm, "", "FB", "facebook"), height=200)
        with t_tr: st.text_area("TR Copy", self.get_ci(sm, "", "TR", "threads"), height=100)
        with t_ig: st.text_area("IG Copy", self.get_ci(sm, "", "IG", "instagram"), height=200)

        st.markdown('<div class="sec-header">Web Magazine Feature</div>', unsafe_allow_html=True)
        for lang in ['EN', 'TC', 'JP']:
            with st.expander(f"Preview {lang} Article", expanded=(lang=='EN')):
                st.markdown(self.get_ci(web, '', lang), unsafe_allow_html=True)

    def push_to_gas(self, form, ai, assets):
        """Unified normalization to ensure perfect mapping to GAS Columns."""
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
                "EN": self.get_ci(web_data, "", "EN", "en"),
                "TC": self.get_ci(web_data, "", "TC", "tc"),
                "JP": self.get_ci(web_data, "", "JP", "jp")
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
        except Exception: return False
