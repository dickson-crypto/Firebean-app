# VERSION: v19.5.0 (Inject project-specific firebean.net profile URL into LinkedIn/Facebook posts)
# TIMESTAMP: 2026-06-19 13:30:00 HKT

import streamlit as st
import requests
import json

try:
    from prompts_library import MAGAZINE_PROMPT, SOCIAL_PROMPT
except ImportError:
    MAGAZINE_PROMPT = ""
    SOCIAL_PROMPT = ""


class SynthesisSync:
    def __init__(self):
        # Using your latest deployment URL
        self.GAS_URL = "https://script.google.com/macros/s/AKfycbycZnD493RrdTPwUJvXBiGNfg6hf0_AHGzo99ZkeeDtlM66TZFbObWbJVuEfOPe-6Fk/exec"
        self.last_error = ""  # holds the most recent generation error for display

    def get_ci(self, d, default, *keys):
        """Case-insensitive dictionary lookup to prevent AI key errors."""
        if not isinstance(d, dict): return default
        for k, v in d.items():
            for key in keys:
                if k.lower() == key.lower(): return v
        return default

    def generate_ai_content(self, key, active_model, form_data, mc_answers=None):
        if not active_model or active_model == "NONE":
            active_model = "gemini-1.5-flash"
            
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{active_model}:generateContent?key={key}"

        # Build the project's dedicated website profile link from its project_id.
        # Format requested by Dickson: https://firebean.net/profile.html?id=<lowercased project_id>
        pid = str(form_data.get("project_id", "")).strip()
        profile_url = f"https://firebean.net/profile.html?id={pid.lower()}" if pid else "https://www.firebean.net"

        # DEFINITIVE STRATEGIC PROMPT: PR Agency Centric + Randomized 5-Angle Engine + SEO/AEO
        # Combine the user's two real writing-skill prompts (magazine + social) into one
        # system instruction, plus the strict JSON output contract the app needs.
        # Substitute the {profile_url} placeholder so LinkedIn/Facebook posts carry the
        # project-specific traffic-driving link.
        social_prompt = SOCIAL_PROMPT.replace("{profile_url}", profile_url)
        sys_msg = (
            MAGAZINE_PROMPT
            + "\n\n========== SOCIAL MEDIA PLATFORM GUIDE ==========\n"
            + social_prompt
            + """

========== OUTPUT CONTRACT (STRICT) ==========
Return ONLY a single RAW JSON object (no markdown, no code fences) with EXACTLY this structure:
{
  "WritingStyleUsed": "[which of the 5 magazine angles you picked]",
  "Challenge": "[short SEO summary of the client's pain point]",
  "Solution": "[short ROI summary of Firebean's solution]",
  "SocialMedia": { "LI": "...", "FB": "...", "TR": "...", "IG": "..." },
  "Web": { "EN": "<~500w English article HTML, no FAQ inside>", "TC": "<繁體中文 HK article HTML>", "JP": "<日本語 article HTML>" },
  "FAQ": {
    "EN": [{"q":"...","a":"..."},{"q":"...","a":"..."},{"q":"...","a":"..."}],
    "TC": [{"q":"...","a":"..."},{"q":"...","a":"..."},{"q":"...","a":"..."}],
    "JP": [{"q":"...","a":"..."},{"q":"...","a":"..."},{"q":"...","a":"..."}]
  }
}
SocialMedia keys map to: LI=LinkedIn, FB=Facebook, TR=Threads, IG=Instagram. Follow each platform's word count, tone and language rules from the guide above.
"""
        )
        
        # Inject Firebean's Scope of Work into the context
        scope_data = form_data.get('scope', [])
        scope_str = ", ".join(scope_data) if isinstance(scope_data, list) else str(scope_data)

        ctx = (
            f"[Basic Information]: Client = {form_data.get('client', '')}; "
            f"Project = {form_data.get('project', '')}; "
            f"Firebean's Scope of Work = {scope_str}.\n"
            f"[Event Details]: Date = {form_data.get('date', '')}; "
            f"Venue = {form_data.get('venue', '')}.\n"
            f"[Strategic Brief / Pain Point & Solution context]: {form_data.get('open_question', '')}"
        )

        # Fold the 15 MC answers into the context so content reflects the user's choices
        if mc_answers:
            qa_lines = []
            for i, item in enumerate(mc_answers, 1):
                q = item.get("q", "") if isinstance(item, dict) else ""
                a = item.get("a", "") if isinstance(item, dict) else str(item)
                qa_lines.append(f"{i}. {q} -> 答案: {a}")
            ctx += (
                "\n\n[Strategic Diagnostic — the user's answers to 15 MC questions. "
                "Use these to choose the editorial angle and shape the narrative]:\n"
                + "\n".join(qa_lines)
            )
        
        payload = {
            "contents": [{"role": "user", "parts": [{"text": ctx}]}],
            "systemInstruction": {"parts": [{"text": sys_msg}]},
            "generationConfig": {"responseMimeType": "application/json"}
        }
        
        try:
            res = requests.post(url, json=payload, timeout=90)
            if res.status_code == 200:
                data = res.json()
                # The model can return no candidate if the prompt is blocked (safety/recitation)
                cands = data.get("candidates") or []
                if not cands:
                    self.last_error = f"No candidate returned. Raw response: {json.dumps(data)[:500]}"
                    return None
                parts = cands[0].get("content", {}).get("parts", [])
                if not parts:
                    reason = cands[0].get("finishReason", "UNKNOWN")
                    self.last_error = f"Empty content (finishReason={reason}). Raw: {json.dumps(data)[:500]}"
                    return None
                raw = parts[0].get("text", "")
                clean = raw.replace("```json", "").replace("```", "").strip()
                try:
                    return json.loads(clean)
                except json.JSONDecodeError as je:
                    self.last_error = f"Model returned non-JSON text: {je}. First 300 chars: {clean[:300]}"
                    return None
            else:
                # Surface the actual Google API error (bad key / wrong model / quota)
                self.last_error = f"HTTP {res.status_code} from Gemini: {res.text[:600]}"
                return None
        except Exception as e:
            self.last_error = f"Request exception: {type(e).__name__}: {e}"
            return None

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

    def _faq_to_string(self, faq_list):
        """Flatten a list of {q, a} dicts into a single readable string for the sheet cell."""
        if not faq_list:
            return ""
        if isinstance(faq_list, str):
            return faq_list
        lines = []
        for f in faq_list:
            if isinstance(f, dict):
                q = f.get("q", "") or f.get("Q", "")
                a = f.get("a", "") or f.get("A", "")
                lines.append(f"Q: {q}\nA: {a}")
        return "\n\n".join(lines)

    def push_to_gas(self, form, ai, assets):
        """Build a payload matching the deployed doPost handler (sync-to-github.gs)."""
        ai = ai or {}
        assets = assets or {}
        event_date = f"{form.get('year', '')} {form.get('month', '')}".strip()
        
        # Construct sort_date in YYYY-MM-DD format for database sorting
        month_map = {
            "JAN": "01", "FEB": "02", "MAR": "03", "APR": "04",
            "MAY": "05", "JUN": "06", "JUL": "07", "AUG": "08",
            "SEP": "09", "OCT": "10", "NOV": "11", "DEC": "12"
        }
        yr = form.get('year', '')
        mo_str = str(form.get('month', '')).upper()
        mo_num = month_map.get(mo_str, "01")
        sort_date = f"{yr}-{mo_num}-01" if yr else ""

        web_data = ai.get("Web") or ai.get("web") or {}
        faq_data = ai.get("FAQ") or ai.get("faq") or {}
        sm_data = ai.get("SocialMedia") or ai.get("social_media") or {}

        # AI content keyed EXACTLY as the deployed handler reads it
        ai_content = {
            "1_google_slide": ai.get("google_slide", ""),
            "5_linkedin_post": self.get_ci(sm_data, "", "LI", "linkedin"),
            "2_facebook_post": self.get_ci(sm_data, "", "FB", "facebook"),
            "3_threads_post": self.get_ci(sm_data, "", "TR", "threads"),
            "4_instagram_post": self.get_ci(sm_data, "", "IG", "instagram"),
            "6_website": {
                "en": self.get_ci(web_data, "", "EN", "en"),
                "tc": self.get_ci(web_data, "", "TC", "tc"),
                "jp": self.get_ci(web_data, "", "JP", "jp"),
            },
        }

        # Assets: handler reads logo_black / logo_white / images[] / hero_index at TOP level
        photos = assets.get("photos") or assets.get("images") or []
        logo_black = assets.get("logo_black")
        logo_white = assets.get("logo_white")
        hero_index = assets.get("hero_index", 0)

        def _join(v):
            return ", ".join(v) if isinstance(v, list) else (v or "")

        payload = {
            "action": "sync_project",
            "project_id": form.get("project_id", ""),

            # Identity (handler reads *_name)
            "client_name": form.get("client", ""),
            "project_name": form.get("project", ""),
            "venue": form.get("venue", ""),
            "date": event_date,
            "sort_date": sort_date,

            # Framework
            "category": _join(form.get("category")),
            "category_what": _join(form.get("what_we_do")),
            "scope": "\n".join(form.get("scope", [])) if isinstance(form.get("scope"), list) else form.get("scope", ""),
            "youtube": form.get("youtube", ""),
            "open_question": form.get("open_question", ""),

            # Strategy
            "challenge": ai.get("Challenge", "") or ai.get("challenge", ""),
            "solution": ai.get("Solution", "") or ai.get("solution", ""),

            "ai_content": ai_content,

            # FAQ flattened to flat fields (handler reads faq_en / faq_tc / faq_jp)
            "faq_en": self._faq_to_string(self.get_ci(faq_data, [], "EN", "en")),
            "faq_tc": self._faq_to_string(self.get_ci(faq_data, [], "TC", "tc")),
            "faq_jp": self._faq_to_string(self.get_ci(faq_data, [], "JP", "jp")),

            # Assets at TOP level
            "logo_black": logo_black,
            "logo_white": logo_white,
            "images": photos,
            "hero_index": hero_index,
        }

        try:
            res = requests.post(self.GAS_URL, json=payload, timeout=120)
            ok = res.status_code == 200
            try:
                body = res.json()
            except Exception:
                body = res.text
            return {"ok": ok, "status": res.status_code, "response": body}
        except Exception as e:
            return {"ok": False, "status": None, "response": str(e)}
