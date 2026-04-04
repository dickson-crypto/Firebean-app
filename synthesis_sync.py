# VERSION: v18.8.2
# TIMESTAMP: 2026-04-04 21:00:00 HKT

import streamlit as st
import requests
import json

class SynthesisSync:
    def __init__(self):
        # Updated to the new deployment URL you provided
        self.GAS_URL = "https://script.google.com/macros/s/AKfycbycZnD493RrdTPwUJvXBiGNfg6hf0_AHGzo99ZkeeDtlM66TZFbObWbJVuEfOPe-6Fk/exec"

    def get_ci(self, d, default, *keys):
        """Case-insensitive and robust dictionary key lookup to prevent AI formatting errors."""
        if not isinstance(d, dict): return default
        for k, v in d.items():
            for key in keys:
                if k.lower() == key.lower(): return v
        return default

    def generate_ai_content(self, key, active_model, form_data):
        if not active_model or active_model == "NONE":
            active_model = "gemini-1.5-flash"
            
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{active_model}:generateContent?key={key}"
        
        sys_msg = """Role: Firebean Content Director.
        Output strictly as RAW JSON matching this exact structure:
        {
          "Challenge": "Analyze the core problem or 'boring challenge' from the brief in 1-2 professional sentences.",
          "Solution": "Outline the creative strategic solution in 1-2 professional sentences.",
          "SocialMedia": {
            "LI": "...",
            "FB": "...",
            "TR": "...",
            "IG": "..."
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
        
        CRITICAL CONTENT RULES:
        [Challenge & Solution]: Language MUST be in English. Be sharp, strategic, and professional.
        [SocialMedia.FB (Facebook)]: ~100-250 words. Tone: Friendly, storytelling, use "you". Language: Traditional Chinese (Hong Kong) with conversational Cantonese slang. Focus on pain points/solutions and MUST include a clear Call-To-Action (CTA) for event signup/details.
        [SocialMedia.IG (Instagram)]: MAX 150 words. First 125 characters MUST be a strong hook. Tone: Visual, authentic, "behind-the-scenes" insider perspective. Language: Traditional Chinese (Hong Kong). MUST use many emojis and conclude with exactly 20 professional hashtags.
        [SocialMedia.TR (Threads)]: MAX 50 words. Tone: Humorous, casual, conversational, slightly critical/meme-potential. Language: Highly authentic Hong Kong Cantonese slang. Start with a question or anti-traditional view to spark debate. NO broadcast/PR language.
        [SocialMedia.LI (LinkedIn)]: ~150-300 words. Tone: Authoritative B2B, consulting style. Highlight data, ROI, thought leadership, and networking value. Explain WHY this matters to the industry. Language: English or Traditional Chinese (based on context).
        [Web]: 3-4 Paragraphs, 2 H2 tags, and a Bold Slogan at the end.
        [FAQ]: Exactly 3 SEO/AEO optimized Q&As per language, use conversational long-tail keyword questions and direct ROI-focused answers."""
        
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
        challenge = gc.get('Challenge', '')
        solution = gc.get('Solution', '')
        sm = gc.get('SocialMedia') or gc.get('social_media') or gc.get('socialMedia') or {}
        web = gc.get('Web') or gc.get('web') or {}
        faq = gc.get('FAQ') or gc.get('faq') or {}

        st.markdown('<div class="sec-header">Strategic Analysis</div>', unsafe_allow_html=True)
        st.text_area("Boring Challenge", challenge, height=80)
        st.text_area("Creative Solution", solution, height=80)
        st.markdown("<br>", unsafe_allow_html=True)

        st.markdown('<div class="sec-header">Social Media Suite</div>', unsafe_allow_html=True)
        st.text_area("LinkedIn (B2B Thought Leadership)", self.get_ci(sm, "", "LI", "LinkedIn", "li"), height=200)
        st.text_area("Facebook (廣泛觸及與資訊大本營)", self.get_ci(sm, "", "FB", "Facebook", "fb"), height=150)
        st.text_area("Threads (實時客廳與觀點碰撞)", self.get_ci(sm, "", "TR", "Threads", "tr"), height=100)
        st.text_area("Instagram (視覺衝擊與真實幕後花絮)", self.get_ci(sm, "", "IG", "Instagram", "ig"), height=150)
        st.markdown("<br>", unsafe_allow_html=True)

        st.markdown('<div class="sec-header">Web Articles</div>', unsafe_allow_html=True)
        st.markdown("**English (EN)**")
        st.markdown(f"{self.get_ci(web, '', 'EN', 'English', 'en')}", unsafe_allow_html=True)
        st.markdown("---")
        st.markdown("**Trad. Chinese (TC)**")
        st.markdown(f"{self.get_ci(web, '', 'TC', 'Traditional Chinese', 'tc')}", unsafe_allow_html=True)
        st.markdown("---")
        st.markdown("**Japanese (JP)**")
        st.markdown(f"{self.get_ci(web, '', 'JP', 'Japanese', 'jp')}", unsafe_allow_html=True)
        st.markdown("---")

        st.markdown('<div class="sec-header">Strategic FAQ</div>', unsafe_allow_html=True)
        st.json(faq)

    def push_to_gas(self, form, ai, assets):
        event_date = f"{form.get('year', '')} {form.get('month', '')}".strip()
        
        web_data = ai.get("Web") or ai.get("web") or {}
        faq_data = ai.get("FAQ") or ai.get("faq") or {}
        sm_data = ai.get("SocialMedia") or ai.get("social_media") or ai.get("socialMedia") or {}

        # EXTREME NORMALIZATION: Forces AI output to exactly match Google Apps Script Keys
        normalized_ai = {
            "Challenge": ai.get("Challenge", ""),
            "Solution": ai.get("Solution", ""),
            "SocialMedia": {
                "LI": self.get_ci(sm_data, "", "LI", "LinkedIn", "li"),
                "FB": self.get_ci(sm_data, "", "FB", "Facebook", "fb"),
                "TR": self.get_ci(sm_data, "", "TR", "Threads", "tr"),
                "IG": self.get_ci(sm_data, "", "IG", "Instagram", "ig")
            },
            "Web": {
                "EN": self.get_ci(web_data, "", "EN", "English", "en"),
                "TC": self.get_ci(web_data, "", "TC", "Traditional Chinese", "tc"),
                "JP": self.get_ci(web_data, "", "JP", "Japanese", "jp")
            },
            "FAQ": {
                "EN": self.get_ci(faq_data, [], "EN", "English", "en"),
                "TC": self.get_ci(faq_data, [], "TC", "Traditional Chinese", "tc"),
                "JP": self.get_ci(faq_data, [], "JP", "Japanese", "jp")
            }
        }

        # SAFETY FALLBACK: Guarantee assets is a valid object so GAS always triggers Folder Creation
        safe_assets = assets if assets else {"logo_black": None, "logo_white": None, "photos": [], "hero_index": 0}

        payload = {
            **form,
            "date": event_date,
            "category": ", ".join(form.get('category', [])),
            "what_we_do": ", ".join(form.get('what_we_do', [])),
            "scope": "\n".join(form.get('scope', [])),
            "ai_content": normalized_ai,
            "assets": safe_assets,
            "challenge": normalized_ai["Challenge"],
            "solution": normalized_ai["Solution"]
        }
        try:
            res = requests.post(self.GAS_URL, json=payload)
            return res.status_code == 200
        except Exception: 
            return False
