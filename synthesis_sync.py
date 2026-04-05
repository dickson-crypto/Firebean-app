# VERSION: v19.0.9
# TIMESTAMP: 2026-04-05 04:00:00 HKT

import streamlit as st
import requests
import json

class SynthesisSync:
    def __init__(self):
        # Using your latest deployment URL
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
        
        # DEFINITIVE STRATEGIC PROMPT: Randomized 5-Angle Engine + Localized T&M + SEO/AEO
        sys_msg = """Role: You are an expert Chief Editor and B2B/B2C Journalist for a premium online magazine. 
        Objective: Transform project data into a 500-word feature article per language and a platform-specific social media suite.

        ### WRITING PROTOCOL (Diversity Engine):
        RANDOMLY SELECT ONLY ONE writing style for this specific generation. COMMIT 100% to it:
        1. The Thought Leadership Angle: Focus on industry shifts, the visionary blueprint, and why it matters.
        2. The Contrarian / Disruptor Angle: Start with a bold, counter-intuitive hook challenging industry norms.
        3. The Human-Centric / Emotional Angle: Focus on authentic human connection and relief from burnout/stress.
        4. The Analytical Problem-Solver (PAS): Break down the pain point, agitate it, and reveal the solution.
        5. The Insider / Behind-the-Scenes Angle: Exclusive VIP "fly-on-the-wall" perspective.

        ### SOCIAL MEDIA TONE & MANNER (STRICT LOCALIZATION):
        📱 Facebook (FB): ~150 words. Friendly storytelling. Language: Trad. Chinese (HK) with Cantonese slang. Use "you" (你).
        📸 Instagram (IG): < 150 chars. Captivating hook in first 125 chars. Tone: Authentic, "Behind-the-scenes". 20 professional hashtags.
        🧵 Threads (TR): < 50 chars. Humorous/Sharp.地道廣東話/網絡用語. Start with a question or anti-traditional view.
        💼 LinkedIn (LI): 150-300 words. Authoritative B2B English. Emphasis on ROI and industry leadership.

        ### WEB ARTICLE STRUCTURE (SEO/AEO OPTIMIZED):
        - H1 Title: SEO Catchy Headline.
        - Subtitles: Use H2 tags for narrative sections.
        - Word Count: Approx 500 words.
        - Punchline: Final paragraph must be a single, bolded (<strong>) concluding sentence.
        - CRITICAL: DO NOT include FAQ text inside the Web HTML content.

        ### STRATEGIC FAQ (AEO OPTIMIZED):
        - Generate exactly 3 Q&As per language.
        - Use long-tail keyword questions and direct, authoritative answers for AI search engines.

        JSON OUTPUT STRUCTURE:
        {
          "WritingStyleUsed": "[Style]",
          "Challenge": "[SEO Summary]",
          "Solution": "[ROI Summary]",
          "SocialMedia": { "LI": "...", "FB": "...", "TR": "...", "IG": "..." },
          "Web": { "EN": "...", "TC": "...", "JP": "..." },
          "FAQ": { 
            "EN": [{"q":"...", "a":"..."}], 
            "TC": [{"q":"...", "a":"..."}], 
            "JP": [{"q":"...", "a":"..."}] 
          }
        }
        """
        
        ctx = f"Client: {form_data.get('client', '')}. Project: {form_data.get('project', '')}. Date: {form_data.get('date', '')}. Strategic Brief: {form_data.get('open_question', '')}"
        
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
        faq_data = gc.get('FAQ', {})
        
        st.markdown('<div class="sec-header">Strategic Analysis</div>', unsafe_allow_html=True)
        st.text_area("Boring Challenge (SEO Summary)", gc.get('Challenge', ''), height=80)
        st.text_area("Creative Solution (ROI Summary)", gc.get('Solution', ''), height=80)

        st.markdown('<div class="sec-header">Social Media Suite (Localized Tone)</div>', unsafe_allow_html=True)
        t_li, t_fb, t_tr, t_ig = st.tabs(["LinkedIn", "Facebook (HK)", "Threads (HK)", "Instagram (HK)"])
        with t_li: st.text_area("LinkedIn (B2B)", self.get_ci(sm, "", "LI", "linkedin"), height=250)
        with t_fb: st.text_area("Facebook (Story)", self.get_ci(sm, "", "FB", "facebook"), height=200)
        with t_tr: st.text_area("Threads (Slang)", self.get_ci(sm, "", "TR", "threads"), height=100)
        with t_ig: st.text_area("Instagram (BTS)", self.get_ci(sm, "", "IG", "instagram"), height=200)

        st.markdown('<div class="sec-header">Web Magazine Feature (500 Words)</div>', unsafe_allow_html=True)
        for lang in ['EN', 'TC', 'JP']:
            with st.expander(f"Preview {lang} Article", expanded=(lang=='EN')):
                st.markdown(self.get_ci(web, '', lang), unsafe_allow_html=True)
                st.markdown("""
                    <div style="background-color:rgba(226, 35, 26, 0.05); border-left: 4px solid #E2231A; padding: 20px; border-radius: 8px; margin-top: 30px;">
                        <p style="color:#E2231A; font-weight:900; text-transform:uppercase; letter-spacing:1px; margin-bottom:15px; font-size:12px;">🔍 Strategic FAQ (AI Answer Optimized)</p>
                """, unsafe_allow_html=True)
                faqs = faq_data.get(lang, [])
                for f in faqs:
                    st.markdown(f"**Q: {f.get('q', '')}**")
                    st.markdown(f"{f.get('a', '')}")
                    st.markdown('<div style="height:10px"></div>', unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)

    def push_to_gas(self, form, ai, assets):
        """Unified normalization to ensure perfect mapping to GAS Columns."""
        event_date = f"{form.get('year', '')} {form.get('month', '')}".strip()
        
        # NEW: Construct sort_date in YYYY-MM-DD format for database sorting
        month_map = {
            "JAN": "01", "FEB": "02", "MAR": "03", "APR": "04",
            "MAY": "05", "JUN": "06", "JUL": "07", "AUG": "08",
            "SEP": "09", "OCT": "10", "NOV": "11", "DEC": "12"
        }
        yr = form.get('year', '')
        mo_str = form.get('month', '').upper()
        mo_num = month_map.get(mo_str, "01")
        sort_date = f"{yr}-{mo_num}-01" if yr else ""

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
            "sort_date": sort_date, # Pass the YYYY-MM-DD string
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
