# VERSION: v18.7.6
# TIMESTAMP: 2026-04-04 19:00:00 HKT

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
        
        # UPGRADED PROMPT: Added Challenge and Solution generation logic based on the core strategy brief.
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
        # Fallback bindings
        challenge = gc.get('Challenge', '')
        solution = gc.get('Solution', '')
        sm = gc.get('SocialMedia') or gc.get('social_media') or gc.get('socialMedia') or {}
        web = gc.get('Web') or gc.get('web') or {}
        faq = gc.get('FAQ') or gc.get('faq') or {}

        # NEW: Display Challenge & Solution
        st.markdown('<div class="sec-header">Strategic Analysis</div>', unsafe_allow_html=True)
        st.text_area("Boring Challenge", challenge, height=80)
        st.text_area("Creative Solution", solution, height=80)
        st.markdown("<br>", unsafe_allow_html=True)

        st.markdown('<div class="sec-header">Social Media Suite</div>', unsafe_allow_html=True)
        st.text_area("LinkedIn (B2B Thought Leadership)", sm.get('LI', ''), height=200)
        st.text_area("Facebook (廣泛觸及與資訊大本營)", sm.get('FB', ''), height=150)
        st.text_area("Threads (實時客廳與觀點碰撞)", sm.get('TR', ''), height=100)
        st.text_area("Instagram (視覺衝擊與真實幕後花絮)", sm.get('IG', ''), height=150)
        st.markdown("<br>", unsafe_allow_html=True)

        st.markdown('<div class="sec-header">Web Articles</div>', unsafe_allow_html=True)
        st.markdown("**English (EN)**")
        st.markdown(f"{web.get('EN', '')}", unsafe_allow_html=True)
        st.markdown("---")
        st.markdown("**Trad. Chinese (TC)**")
        st.markdown(f"{web.get('TC', '')}", unsafe_allow_html=True)
        st.markdown("---")

        st.markdown('<div class="sec-header">Strategic FAQ</div>', unsafe_allow_html=True)
        st.json(faq)

    def push_to_gas(self, form, ai, assets):
        # FIX: Combine year and month into the exact "date" format the Master DB expects (e.g., "2026 APR")
        event_date = f"{form.get('year', '')} {form.get('month', '')}".strip()
        
        # Send everything, including the new correctly formatted "date"
        payload = {
            **form,
            "date": event_date,
            "category": ", ".join(form.get('category', [])),
            "what_we_do": ", ".join(form.get('what_we_do', [])),
            "scope": "\n".join(form.get('scope', [])),
            "ai_content": ai,
            "assets": assets,
            "challenge": ai.get("Challenge", ""),
            "solution": ai.get("Solution", "")
        }
        try:
            res = requests.post(self.GAS_URL, json=payload)
            return res.status_code == 200
        except Exception: 
            return False
