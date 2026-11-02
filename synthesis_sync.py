# VERSION: v20.3.0 (PROVIDER FALLBACK: generation now goes through ai_backend — Google Gemini first, automatic fal.ai fallback when Google has no credit / is rate-limited / the model is retired. Prev v20.2.0)
# TIMESTAMP: 2026-11-02 12:00:00 HKT
# CHANGE: Top-level keys client/project/what_we_do (not *_name/category_what);
#         ai_content = {SocialMedia, Web, FAQ(arrays)}; assets nested under data.assets
#         with key "photos" (not top-level images). Fixes empty Master DB cells,
#         missing Drive folder, and "Project Recap" fallback name.

import streamlit as st
import requests
import json
import ai_backend

try:
    from prompts_library import MAGAZINE_PROMPT, SOCIAL_PROMPT
except ImportError:
    MAGAZINE_PROMPT = ""
    SOCIAL_PROMPT = ""


class SynthesisSync:
    def __init__(self):
        # Using your latest deployment URL
        self.GAS_URL = "https://script.google.com/macros/s/AKfycbw6UuXZqhoFYtEiGYPJmFAWCis9IN-M-NVYN8hEo-Ux6UKKloihhv4yScS6ocGEJ9Em/exec"
        self.last_error = ""  # holds the most recent generation error for display
        self.provider = ""    # "google" or "fal" — which provider actually answered

    def get_ci(self, d, default, *keys):
        """Case-insensitive dictionary lookup to prevent AI key errors."""
        if not isinstance(d, dict): return default
        for k, v in d.items():
            for key in keys:
                if k.lower() == key.lower(): return v
        return default

    def generate_ai_content(self, key, active_model, form_data, mc_answers=None):
        if not active_model or active_model == "NONE":
            active_model = "gemini-flash-latest"  # was gemini-1.5-flash (RETIRED, 404)

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
  "Web": {
    "EN": "<h1>Editorial headline</h1><h2>Subtitle/deck</h2><p>Para 1</p><p>Para 2</p><p>Para 3</p><p>Para 4</p><p><strong>Punchline</strong></p>",
    "TC": "<h1>標題</h1><h2>副標題</h2><p>段落一</p><p>段落二</p><p>段落三</p><p>段落四</p><p><strong>金句結尾</strong></p>",
    "JP": "<h1>見出し</h1><h2>サブタイトル</h2><p>段落1</p><p>段落2</p><p>段落3</p><p>段落4</p><p><strong>パンチライン</strong></p>"
  },
  "SocialMedia": { "LI": "...", "FB": "...", "TR": "...", "IG": "..." },
  "Challenge": "[short SEO summary of the client's pain point]",
  "Solution": "[short ROI summary of Firebean's solution]",
  "FAQ": {
    "EN": [{"q":"...","a":"..."},{"q":"...","a":"..."},{"q":"...","a":"..."}],
    "TC": [{"q":"...","a":"..."},{"q":"...","a":"..."},{"q":"...","a":"..."}],
    "JP": [{"q":"...","a":"..."},{"q":"...","a":"..."},{"q":"...","a":"..."}]
  }
}
FIELD ORDER IS DELIBERATE: emit "Web" FIRST (right after WritingStyleUsed) so the
most important article content is never lost if the response is long. The three Web
languages (EN, TC, JP) are MANDATORY and must each be a non-empty HTML string —
never return an empty Web object.
SocialMedia keys map to: LI=LinkedIn, FB=Facebook, TR=Threads, IG=Instagram. Follow each platform's word count, tone and language rules from the guide above.

WEB FIELD RULE (must match the firebean.net website layout 100%): each Web language value MUST be a valid HTML string that (1) STARTS with one <h1> editorial headline, (2) is followed by one <h2> subtitle/deck, (3) contains AT LEAST 4 standalone <p> paragraphs so the website can insert project photos after the 1st, 2nd and 3rd <p>, and (4) ENDS with the punchline as <p><strong>...</strong></p>. Do NOT include any <img> tags, do NOT put FAQ text in Web, do NOT use Markdown.
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
        
        # The article is long: 3 languages x ~500-word HTML + 4 social posts + 9 FAQ,
        # so the token cap must stay high or the JSON is truncated mid-way
        # (finishReason=MAX_TOKENS -> empty Web). Token cap + thinkingConfig are now
        # handled inside ai_backend.generate() for BOTH providers (Google and fal.ai).

        # Route the SAME request through ai_backend: Google Gemini first, with an
        # AUTOMATIC fallback to fal.ai (fal-ai/any-llm) when Google runs out of
        # prepaid credit (HTTP 402), gets rate-limited (429) or the model is
        # retired (404). The fal key comes from Streamlit Secrets (FAL_KEY) — or
        # from a fal key pasted into the "Gemini API Key" box.
        # MAX_TOKENS note: the article is long (3 languages x ~500-word HTML + 4
        # social posts + 9 FAQ) so the cap stays at 8192, and thinking is disabled
        # inside ai_backend — thinking tokens come out of the same budget and were
        # truncating the JSON (finishReason=MAX_TOKENS, empty Web).
        raw, reason, err, provider = ai_backend.generate(
            key, active_model, sys_msg, ctx,
            images=None, max_tokens=8192, temperature=0.9, json_mode=True,
        )
        self.provider = provider
        if raw is None:
            self.last_error = err or "Unknown generation error."
            return None
        parsed = ai_backend.parse_json_loose(raw)
        if parsed is not None:
            return ai_backend.normalize_content(parsed)
        clean = ai_backend._strip_fences(raw)
        # Most common cause: output truncated mid-JSON (MAX_TOKENS).
        # RESCUE the content so the Web article is never silently lost.
        rescued = self._rescue_json(clean)
        if rescued and (rescued.get("Web") or rescued.get("SocialMedia")):
            note = " (output was truncated — recovered partial content; consider regenerating)" if reason == "MAX_TOKENS" else ""
            self.last_error = f"Model JSON was malformed but content was recovered{note}."
            return rescued
        self.last_error = (
            f"Model returned non-JSON text (finishReason={reason}). "
            f"First 300 chars: {clean[:300]}"
        )
        return None

    def _rescue_json(self, text):
        """Best-effort recovery when the model's JSON is truncated/malformed.
        1) Trim to the last balanced closing brace and parse.
        2) Otherwise regex-extract the Web {EN,TC,JP} blocks from the raw text so the
           Web article is never silently lost. Returns a (possibly partial) dict or None."""
        import re as _re
        if not text:
            return None
        # Strategy 1: balanced-brace trim
        depth = 0
        last_ok = -1
        in_str = False
        esc = False
        for idx, ch in enumerate(text):
            if esc:
                esc = False
                continue
            if ch == "\\":
                esc = True
                continue
            if ch == '"':
                in_str = not in_str
                continue
            if in_str:
                continue
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    last_ok = idx
        if last_ok > 0:
            try:
                return json.loads(text[: last_ok + 1])
            except Exception:
                pass
        # Strategy 2: regex-recover the Web language blocks + simple top-level strings
        out = {}
        web = {}
        for lang in ("EN", "TC", "JP"):
            m = _re.search(r'"' + lang + r'"\s*:\s*"(<h1>.*?)"\s*[,}\]]', text, _re.S)
            if m:
                val = m.group(1).replace('\\"', '"').replace("\\n", "").replace("\\/", "/")
                web[lang] = val
        if web:
            out["Web"] = web
        for fld in ("WritingStyleUsed", "Challenge", "Solution"):
            m = _re.search(r'"' + fld + r'"\s*:\s*"(.*?)"\s*[,}]', text, _re.S)
            if m:
                out[fld] = m.group(1).replace('\\"', '"')
        return out or None

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

        def _faq_arr(*keys):
            """Return FAQ as a clean list of {q, a} dicts (Handler.sanitizeFaq expects arrays)."""
            raw = self.get_ci(faq_data, [], *keys)
            out = []
            if isinstance(raw, list):
                for f in raw:
                    if isinstance(f, dict):
                        q = f.get("q", "") or f.get("Q", "")
                        a = f.get("a", "") or f.get("A", "")
                        if q or a:
                            out.append({"q": q, "a": a})
            return out

        # ai_content keyed EXACTLY as Handler.gs v12.1.0 reads it:
        #   data.ai_content.SocialMedia.{LI,FB,TR,IG}
        #   data.ai_content.Web.{EN,TC,JP}
        #   data.ai_content.FAQ.{EN,TC,JP}  (arrays of {q,a})
        ai_content = {
            "SocialMedia": {
                "LI": self.get_ci(sm_data, "", "LI", "linkedin"),
                "FB": self.get_ci(sm_data, "", "FB", "facebook"),
                "TR": self.get_ci(sm_data, "", "TR", "threads"),
                "IG": self.get_ci(sm_data, "", "IG", "instagram"),
            },
            "Web": {
                "EN": self.get_ci(web_data, "", "EN", "en"),
                "TC": self.get_ci(web_data, "", "TC", "tc"),
                "JP": self.get_ci(web_data, "", "JP", "jp"),
            },
            "FAQ": {
                "EN": _faq_arr("EN", "en"),
                "TC": _faq_arr("TC", "tc"),
                "JP": _faq_arr("JP", "jp"),
            },
        }

        # Assets MUST be nested under data.assets with key "photos".
        # Handler reads data.assets.{logo_black, logo_white, photos[], hero_index}.
        photos = assets.get("photos") or assets.get("images") or []
        assets_block = {
            "logo_black": assets.get("logo_black"),
            "logo_white": assets.get("logo_white"),
            "photos": photos,
            "hero_index": assets.get("hero_index", 0),
        }

        def _join(v):
            return ", ".join(v) if isinstance(v, list) else (v or "")

        payload = {
            "action": "sync_project",
            "project_id": form.get("project_id", ""),

            # Identity (Handler reads data.project / data.client)
            "client": form.get("client", ""),
            "project": form.get("project", ""),
            "venue": form.get("venue", ""),
            "date": event_date,
            "sort_date": sort_date,
            # Project YEAR drives the Project ID: FB<year><seq>. Handler uses this
            # (not the current year) so a 2017 project becomes FB2017XXX.
            "year": str(form.get("year", "")).strip(),

            # Framework (Handler reads data.what_we_do)
            "category": _join(form.get("category")),
            "what_we_do": _join(form.get("what_we_do")),
            # Join multiple scopes with ", " (comma) NOT newlines, so the website shows
            # "Concept Development, Branding Strategy, ..." instead of rendering <br> tags.
            "scope": ", ".join([s for s in form.get("scope", []) if s]) if isinstance(form.get("scope"), list) else form.get("scope", ""),
            "youtube": form.get("youtube", ""),
            "open_question": form.get("open_question", ""),

            # Strategy
            "challenge": ai.get("Challenge", "") or ai.get("challenge", ""),
            "solution": ai.get("Solution", "") or ai.get("solution", ""),

            # Nested AI content (SocialMedia / Web / FAQ-arrays)
            "ai_content": ai_content,

            # Nested assets block — triggers Drive folder + photo upload
            "assets": assets_block,
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
