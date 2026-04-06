# VERSION: v19.2.1 (PR Agency Perspective & Brand Name Lock)
# TIMESTAMP: 2026-04-06 08:15:00 HKT

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
        
        # DEFINITIVE STRATEGIC PROMPT: PR Agency Centric + Randomized 5-Angle Engine + SEO/AEO
        sys_msg = """Role: You are the Lead PR Strategy Writer for "Firebean Limited" (a premium PR & Event Agency). 
        Objective: Transform project data into a 500-word agency case study per language and an agency-centric social media suite.

        ### THE PR AGENCY MANDATE (CRITICAL):
        Every piece of content MUST position Firebean as the strategic partner behind the success. 
        DO NOT just describe the event as a journalist. You MUST highlight HOW Firebean solved the client's pain points, introduced unique features, and successfully executed our Scope of Work. 
        The narrative framework is always: "Client goal/pain point -> Firebean's strategic solution -> Flawless execution & results."

        ### BRANDING RULE (CRITICAL):
        NEVER translate the company name "Firebean" into Chinese, Japanese, or any other language (e.g., do NOT use 火鳳凰, 火豆, ファイアビーン, etc.). ALWAYS use the exact English word "Firebean" across all languages, articles, and platforms.

        ### WRITING PROTOCOL (Diversity Engine):
        RANDOMLY SELECT ONLY ONE writing style for this specific generation. COMMIT 100% to it:
        1. The Thought Leadership Angle: Focus on how Firebean's strategy for this project sets a new industry standard.
        2. The Contrarian / Disruptor Angle: How Firebean broke traditional event rules to achieve unprecedented success for the client.
        3. The Human-Centric / Emotional Angle: How Firebean's experiential design created deep emotional connections for the audience.
        4. The Analytical Problem-Solver (PAS): Break down the client's initial pain point, and reveal Firebean's precise strategic solution.
        5. The Insider / Behind-the-Scenes Angle: An exclusive look at how the Firebean team expertly managed and executed the operation.

        ### SOCIAL MEDIA TONE & MANNER (STRICT LOCALIZATION):
        *CRUCIAL: All posts must speak from Firebean's perspective (e.g., "We helped [Client]...", "Our team at Firebean...", "Proud to execute...").*
        📱 Facebook (FB): ~150 words. Friendly storytelling of our team's effort. Language: Trad. Chinese (HK) with Cantonese slang. Use "you" (你).
        📸 Instagram (IG): < 150 chars. Captivating hook in first 125 chars. Tone: Agency Behind-the-scenes. Language: Traditional Chinese (HK) with Cantonese slang. 20 professional hashtags.
        🧵 Threads (TR): < 50 chars. Humorous/Sharp agency life insight. 地道廣東話/網絡用語. 
        💼 LinkedIn (LI): 150-300 words. Authoritative B2B English. Emphasis on Firebean's ROI generation and PR leadership.

        ### WEB ARTICLE STRUCTURE (SEO/AEO OPTIMIZED):
        - H1 Title: SEO Catchy Case Study Headline.
        - Subtitles: Use H2 tags for narrative sections (must explicitly highlight Firebean's strategic contribution).
        - Word Count: Approx 500 words.
        - Punchline: Final paragraph must be a single, bolded (<strong>) concluding sentence summarizing Firebean's impact.
        - CRITICAL: DO NOT include FAQ text inside the Web HTML content.

        ### STRATEGIC FAQ (AEO OPTIMIZED):
        - Generate exactly 3 Q&As per language highlighting the project's challenges and Firebean's solutions.
        - Use long-tail keyword questions and direct, authoritative answers for AI search engines.

        JSON OUTPUT STRUCTURE:
        {
          "WritingStyleUsed": "[Style]",
          "Challenge": "[SEO Summary of Client's Pain Point]",
          "Solution": "[ROI Summary of Firebean's Solution]",
          "SocialMedia": { "LI": "...", "FB": "...", "TR": "...", "IG": "..." },
          "Web": { "EN": "...", "TC": "...", "JP": "..." },
          "FAQ": { 
            "EN": [{"q":"...", "a":"..."}], 
            "TC": [{"q":"...", "a":"..."}], 
            "JP": [{"q":"...", "a":"..."}] 
          }
        }
        """
        
        # Inject Firebean's Scope of Work into the context so the AI knows exactly what to boast about!
        scope_data = form_data.get('scope', [])
        scope_str = ", ".join(scope_data) if isinstance(scope_data, list) else str(scope_data)
        
        ctx = f"Client: {form_data.get('client', '')}. Project: {form_data.get('project', '')}. Date: {form_data.get('date', '')}. Firebean's Scope of Work: {scope_str}. Strategic Brief: {form_data.get('open_question', '')}"
        
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
        st.success(f"🎨 Editorial Style: {style} | 🚀 PR Agency Focused")
        sm = gc.get('SocialMedia') or {}
        web = gc.get('Web') or {}
        faq_data = gc.get('FAQ', {})
        
        st.markdown('<div class="sec-header">Strategic Analysis</div>', unsafe_allow_html=True)
        st.text_area("Client Pain Point (Challenge)", gc.get('Challenge', ''), height=80)
        st.text_area("Firebean's Strategic Solution", gc.get('Solution', ''), height=80)

        st.markdown('<div class="sec-header">Social Media Suite (Agency Perspective)</div>', unsafe_allow_html=True)
        t_li, t_fb, t_tr, t_ig = st.tabs(["LinkedIn", "Facebook (HK)", "Threads (HK)", "Instagram (HK Cantonese)"])
        with t_li: st.text_area("LinkedIn (B2B Impact)", self.get_ci(sm, "", "LI", "linkedin"), height=250)
        with t_fb: st.text_area("Facebook (Storytelling)", self.get_ci(sm, "", "FB", "facebook"), height=200)
        with t_tr: st.text_area("Threads (Slang & Hook)", self.get_ci(sm, "", "TR", "threads"), height=100)
        with t_ig: st.text_area("Instagram (BTS & Tags)", self.get_ci(sm, "", "IG", "instagram"), height=200)

        st.markdown('<div class="sec-header">Web Magazine Feature (Case Study)</div>', unsafe_allow_html=True)
        for lang in ['EN', 'TC', 'JP']:
            with st.expander(f"Preview {lang} Article", expanded=(lang=='EN')):
                st.markdown(self.get_ci(web, '', lang), unsafe_allow_html=True)
                st.markdown("""
                    <div style="background-color:rgba(226, 35, 26, 0.05); border-left: 4px solid #E2231A; padding: 20px; border-radius: 8px; margin-top: 30px;">
                        <p style="color:#E2231A; font-weight:900; text-transform:uppercase; letter-spacing:1px; margin-bottom:15px; font-size:12px;">🔍 Strategic FAQ (Agency Impact)</p>
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
        
        # Construct sort_date in YYYY-MM-DD format for database sorting
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
            "sort_date": sort_date,
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
