# VERSION: v19.2.0 (Near-fullscreen red overlay + animated running-man icon, static text; MC = radio-style multi-select via st.pills)
# TIMESTAMP: 2026-06-19 16:30:00 HKT
#
# FLOW (as specified by Dickson):
#   STAGE 1  Collect + validate ALL inputs (client, project, scope, logo B/W, 1-8 photos, hero pick).
#            The "Generate 15 MC" button stays DISABLED until every required input is present.
#   STAGE 2  Generate 15 MC diagnostic questions (driven by the writing-skill styles + photos).
#            User answers all 15 -> progress climbs -> 15/15 = 100%.
#   STAGE 3  Only at 100% does "Generate AI Content" activate. MC answers steer the content.
#            A BREATHING RED CIRCLE animation plays while the AI is processing.
#   STAGE 4  "Execute Master Sync" stays BLOCKED until inputs + 15 MC + generated content are all done.
#            Sync sends every field with the correct names so no Master DB column is left empty.

import streamlit as st
import re
import time
from datetime import datetime

try:
    from inputs_module import InputEngine
    from progress_logic import ProgressGate
    from ai_diagnostics import AIDiagnostic
    from synthesis_sync import SynthesisSync
except ImportError as e:
    st.error(f"Module Error: {e}")
    st.stop()


class FirebeanPortal:
    def __init__(self):
        self.VERSION = "v19.2.0"
        self.MODELS = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]
        self.init_session()

    def init_session(self):
        ss = st.session_state
        ss.setdefault("page", 1)
        ss.setdefault("terminal_logs", [f"> Boot: {self.VERSION}"])
        ss.setdefault("form_data", {})
        ss.setdefault("assets", {"logo_black": None, "logo_white": None, "photos": [], "hero_index": 0})
        ss.setdefault("hero_index", 0)
        ss.setdefault("mc_questions", None)     # list of {q, opts}
        ss.setdefault("mc_answers", {})         # {index: chosen option}
        ss.setdefault("ai_result", None)        # generated content dict
        ss.setdefault("api_key", "")

    def log(self, msg):
        ts = datetime.now().strftime("%H:%M:%S")
        st.session_state.terminal_logs.append(f"[{ts}] {msg}")
        if len(st.session_state.terminal_logs) > 14:
            st.session_state.terminal_logs.pop(0)


def breathing_overlay(text):
    """Return an st.empty() showing a NEAR-FULLSCREEN red circle overlay.
    The circle's outer glow pulses softly, but the status TEXT is static (no breathing).
    A running-man icon animates inside the circle (above the text)."""
    o = st.empty()
    o.markdown(f"""
        <style>
        /* Soft glow pulse on the circle only — the circle itself does NOT resize, text stays still */
        @keyframes fb-glow {{
            0%   {{ box-shadow: 0 0 40px 10px rgba(226,35,26,0.45); }}
            50%  {{ box-shadow: 0 0 110px 55px rgba(226,35,26,0.65); }}
            100% {{ box-shadow: 0 0 40px 10px rgba(226,35,26,0.45); }}
        }}
        /* Each icon fades in, holds, then fades out. 3 icons => 3.6s loop, staggered
           by 1.2s so exactly one "action" is visible at a time (a working sequence). */
        @keyframes fb-cycle {{
            0%    {{ opacity:0; transform:scale(0.8); }}
            6%    {{ opacity:1; transform:scale(1); }}
            27%   {{ opacity:1; transform:scale(1); }}
            33%   {{ opacity:0; transform:scale(0.8); }}
            100%  {{ opacity:0; transform:scale(0.8); }}
        }}
        .fb-overlay {{ position:fixed; top:0; left:0; width:100vw; height:100vh; background:#121212;
                       z-index:9999; display:flex; flex-direction:column; justify-content:center; align-items:center; }}
        /* Near-fullscreen circle = largest inscribed circle (min of viewport height/width) */
        .fb-circle {{ width:min(92vh, 92vw); height:min(92vh, 92vw); border-radius:50%; background:#E2231A;
                      display:flex; flex-direction:column; justify-content:center; align-items:center;
                      text-align:center; padding:24px; box-sizing:border-box;
                      animation: fb-glow 2s ease-in-out infinite; }}
        /* Icon stack: all icons share the same spot; only one visible per phase.
           Force a fixed 72px so Streamlit's global SVG styles can't blow it up. */
        .fb-iconwrap {{ position:relative; width:72px; height:72px; margin-bottom:26px; }}
        .fb-iconwrap svg.fb-ico {{ width:72px !important; height:72px !important; }}
        .fb-ico {{ position:absolute; top:0; left:0; width:72px; height:72px;
                   opacity:0; animation: fb-cycle 3.6s ease-in-out infinite; }}
        .fb-ico.i1 {{ animation-delay: 0s; }}
        .fb-ico.i2 {{ animation-delay: 1.2s; }}
        .fb-ico.i3 {{ animation-delay: 2.4s; }}
        .fb-circle .fb-label {{ color:#FFFFFF; font-weight:800; letter-spacing:1px;
                                 font-size:clamp(22px, 3.2vw, 38px); line-height:1.25; margin:0; }}
        .fb-circle .fb-sub {{ color:rgba(255,255,255,0.9); font-size:clamp(12px, 1.4vw, 16px); margin-top:14px; }}
        </style>
        <div class="fb-overlay">
            <div class="fb-circle">
                <div class="fb-iconwrap">
                    <!-- Action 1: running man (gathering) -->
                    <svg class="fb-ico i1" width="72" height="72" viewBox="0 0 24 24" fill="#FFFFFF" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
                        <circle cx="13.5" cy="4.5" r="2"/>
                        <path d="M12.9 6.6c-.5-.2-1.1-.1-1.5.3L8.1 10.1c-.3.3-.4.7-.3 1.1l.9 2.9-2.4 4.1c-.3.5-.1 1.1.4 1.4.5.3 1.1.1 1.4-.4l2.6-4.4c.2-.3.2-.7.1-1l-.5-1.7 1.7-1.6.9 2.4c.1.4.5.7.9.7h3.5c.6 0 1-.4 1-1s-.4-1-1-1h-2.8l-1.3-3.6c-.1-.4-.4-.7-.8-.8l.9-.9z"/>
                        <path d="M5.5 8.5l-1.8.6c-.5.2-.8.7-.6 1.3.2.5.7.8 1.3.6l2.2-.7-1.1-1.8z"/>
                    </svg>
                    <!-- Action 2: pencil writing (composing) -->
                    <svg class="fb-ico i2" width="72" height="72" viewBox="0 0 24 24" fill="#FFFFFF" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
                        <path d="M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25z"/>
                        <path d="M20.71 7.04c.39-.39.39-1.02 0-1.41l-2.34-2.34a.9959.9959 0 0 0-1.41 0l-1.83 1.83 3.75 3.75 1.83-1.83z"/>
                    </svg>
                    <!-- Action 3: check / done (finalising) -->
                    <svg class="fb-ico i3" width="72" height="72" viewBox="0 0 24 24" fill="#FFFFFF" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
                        <path d="M9 16.17 4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/>
                    </svg>
                </div>
                <p class="fb-label">{text}</p>
                <p class="fb-sub">AI is processing... please wait</p>
            </div>
        </div>
    """, unsafe_allow_html=True)
    return o


def generate_project_id(year=None, client="", project=""):
    """Provisional Project ID in the final format FB<year><seq>.
    The front-end cannot read the Master DB, so the sequence here is only a
    PLACEHOLDER (derived from the timestamp). The Handler regenerates the real,
    DB-unique sequential ID on sync and returns it; the app then rewrites the
    profile links with that real ID."""
    yr = str(year).strip() if year else ""
    if not re.fullmatch(r"\d{4}", yr):
        yr = datetime.now().strftime("%Y")
    # 3-digit placeholder from the clock so two quick projects don't collide locally.
    seq = datetime.now().strftime("%H%M%S")[-3:]
    return f"FB{yr}{seq}"


def missing_inputs(fd, assets):
    """Return a list of human-readable missing required items."""
    missing = []
    if not fd.get("client"):       missing.append("Client name")
    if not fd.get("project"):      missing.append("Project name")
    if not fd.get("scope"):        missing.append("Scope of Work (tick at least one)")
    if not fd.get("open_question"): missing.append("Brief / context (required — main source for the AI)")
    if not assets.get("logo_black"): missing.append("Logo Black")
    if not assets.get("logo_white"): missing.append("Logo White")
    if not assets.get("photos"):   missing.append("At least 1 photo (up to 8)")
    return missing


# ============================================================
if __name__ == "__main__":
    st.set_page_config(page_title="Firebean Portal", layout="wide")
    portal = FirebeanPortal()
    inputs, gate, diag, sync = InputEngine(), ProgressGate(), AIDiagnostic(), SynthesisSync()
    ss = st.session_state

    st.markdown("""<style>
        .stApp { background-color: #121212; color: white; }
        .sec-header { font-size: 18px; font-weight: 900; color: #E2231A; text-transform: uppercase; letter-spacing: 1px; margin: 20px 0 10px; border-bottom: 1px solid #333; padding-bottom: 6px; }
        .terminal-box { background:#000; padding:15px; border-left:4px solid #E2231A; height:160px; overflow-y:auto; font-family:monospace; font-size:12px; margin-top:25px; }
        .terminal-box p { margin:2px 0; color:#4ade80; }
        .pill-ok { color:#4ade80; } .pill-bad { color:#E2231A; }
    </style>""", unsafe_allow_html=True)

    # --- Header ---
    c1, c2 = st.columns([1, 9])
    with c1:
        st.image("https://raw.githubusercontent.com/dickson-crypto/Firebean-app/main/Firebeanlogo2026.png")
    with c2:
        st.markdown(f"<h1>Project Collector. <span style='font-size:14px;opacity:0.5;'>{portal.VERSION}</span></h1>", unsafe_allow_html=True)

    fd = ss.form_data

    # ========================================================
    # PAGE 1 — COLLECT + VALIDATE + MC + GENERATE
    # ========================================================
    if ss.page == 1:
        # --- AI engine / key ---
        st.markdown('<div class="sec-header">AI Engine</div>', unsafe_allow_html=True)
        secret_key = ""
        try:
            secret_key = st.secrets.get("GEMINI_API_KEYS", "") or st.secrets.get("GEMINI_API_KEY", "")
        except Exception:
            secret_key = ""
        if secret_key:
            st.success("🔐 Gemini API key loaded from Streamlit Secrets.")
        else:
            st.info('No secret found. Paste your key below, or add  GEMINI_API_KEYS = "AIza..."  in Settings → Secrets.')
        k1, k2 = st.columns([2, 1])
        api_key = k1.text_input("Gemini API Key", type="password", value=ss.api_key or secret_key)
        model = k2.selectbox("Model", portal.MODELS, index=0)
        ss.api_key = api_key

        # --- Inputs ---
        client, project, venue, year, month = inputs.render_identity()
        sel_cat, sel_wwd, sel_sow = inputs.render_framework()

        st.markdown('<div class="sec-header">Strategic Brief</div>', unsafe_allow_html=True)
        open_q = st.text_area("Brief / context for the AI — REQUIRED (goal, pain points, results)", value=fd.get("open_question", ""), height=120,
                              help="This is a main source the AI studies to write the MC questions and the final content.")
        youtube = st.text_input("YouTube URL (optional — not counted toward progress)", value=fd.get("youtube", ""))

        lb, lw, ph, encoded = inputs.render_assets()

        # --- Persist everything ---
        ss.form_data = {
            "client": client, "project": project, "venue": venue,
            "year": year, "month": month,
            "category": sel_cat, "what_we_do": sel_wwd, "scope": sel_sow,
            "open_question": open_q, "youtube": youtube,
            "project_id": fd.get("project_id") or generate_project_id(year, client, project),
        }
        fd = ss.form_data

        # IMPORTANT: keep the FULL asset dict {data, mimeType, ext} for every asset.
        # Handler.gs saveFile() reads assetData.data / .mimeType / .ext, so passing a
        # bare base64 string makes saveFile() return "" and the file never uploads.
        # (This is why photos were NOT landing in the Drive folder even though logos did.)
        logo_black = inputs.process_for_db(lb, is_logo=True) if lb else None
        logo_white = inputs.process_for_db(lw, is_logo=True) if lw else None
        photos = []
        if ph:
            for p in ph[:8]:
                pr = inputs.process_for_db(p, is_logo=False)
                if pr and pr.get("data"):
                    photos.append(pr)  # full dict {data, mimeType, ext}
        ss.assets = {
            "logo_black": logo_black if logo_black else None,   # full dict, not just .data
            "logo_white": logo_white if logo_white else None,   # full dict, not just .data
            "photos": photos,                                   # list of full dicts
            "hero_index": ss.hero_index,
        }

        # --- Validation checklist ---
        miss = missing_inputs(fd, ss.assets)
        st.markdown('<div class="sec-header">Readiness Check</div>', unsafe_allow_html=True)
        if miss:
            st.markdown("Missing before you can generate questions:")
            for m in miss:
                st.markdown(f"- <span class='pill-bad'>✗ {m}</span>", unsafe_allow_html=True)
        else:
            st.markdown("<span class='pill-ok'>✓ All required inputs present. You can generate the 15 MC questions.</span>", unsafe_allow_html=True)

        inputs_ready = (len(miss) == 0)

        # ----- STAGE 2: Generate 15 MC questions -----
        st.markdown('<div class="sec-header">Step 1 — Strategic Diagnostic (15 MC)</div>', unsafe_allow_html=True)
        gen_mc = st.button("🧩 GENERATE 15 MC QUESTIONS", disabled=not (inputs_ready and api_key), use_container_width=True)
        if not api_key:
            st.caption("Enter your Gemini API key to enable this.")
        if gen_mc:
            ov = breathing_overlay("GENERATING 15 DIAGNOSTIC QUESTIONS")
            core = f"{fd.get('open_question','')} | Scope: {', '.join(fd.get('scope', []))}"
            qs = diag.get_questions(api_key, model, fd.get("project", ""), core, ss.assets["photos"])
            if not qs and model != "gemini-1.5-flash":
                qs = diag.get_questions(api_key, "gemini-1.5-flash", fd.get("project", ""), core, ss.assets["photos"])
            ov.empty()
            if qs:
                ss.mc_questions = qs[:15]
                ss.mc_answers = {}
                ss.ai_result = None  # reset content if questions regenerated
                portal.log(f"Generated {len(ss.mc_questions)} MC questions.")
            else:
                portal.log("MC generation FAILED.")
                st.error("Could not generate questions. Exact reason from Google:")
                st.code(AIDiagnostic.last_error or "No detail captured.", language="text")

        # ----- Answer the 15 MC (radio-button style, but MORE THAN ONE answer allowed) -----
        answered = 0
        if ss.mc_questions:
            st.markdown("Answer all questions below. Tap the options like radio buttons — **you may select more than one** per question. Progress reaches 100% when every question has at least one answer.")
            for i, item in enumerate(ss.mc_questions):
                q = item.get("q", f"Question {i+1}")
                opts = item.get("opts", [])
                key = f"mc_{i}"
                st.markdown(f"**{i+1}. {q}**")
                # st.pills = radio-button-look clickable options that support multi-select.
                # Fall back to multiselect on older Streamlit versions that lack st.pills.
                if hasattr(st, "pills"):
                    choice = st.pills(
                        label=f"q{i+1}", options=opts, selection_mode="multi",
                        default=None, key=key, label_visibility="collapsed",
                    )
                else:
                    choice = st.multiselect(
                        f"{i+1}. {q}", options=opts, default=None, key=key,
                        placeholder="可選擇一個或多個答案 (select one or more)",
                    )
                # choice is always a list; store it (empty list = unanswered)
                ss.mc_answers[i] = choice or []
            answered = len([v for v in ss.mc_answers.values() if v])
            total = len(ss.mc_questions)
            pct = int((answered / total) * 100) if total else 0
            st.progress(pct / 100, text=f"Content readiness: {answered}/{total} answered ({pct}%)")

        mc_complete = bool(ss.mc_questions) and answered == len(ss.mc_questions) and len(ss.mc_questions) > 0

        # ----- STAGE 3: Generate AI content (only at 100%) -----
        st.markdown('<div class="sec-header">Step 2 — Generate Content</div>', unsafe_allow_html=True)
        gen_content = st.button("🧠 GENERATE AI CONTENT", disabled=not mc_complete, type="primary", use_container_width=True)
        if not mc_complete:
            st.caption("Answer all 15 questions (reach 100%) to enable content generation.")
        if gen_content:
            ov = breathing_overlay("GENERATING CASE STUDY + SOCIAL COPY")
            # Build answered MC list with q + chosen answer
            def _ans_str(v):
                # mc_answers values are now lists (multi-select); join into one readable string
                if isinstance(v, list):
                    return "; ".join(str(x) for x in v)
                return str(v) if v else ""
            mc_payload = [{"q": ss.mc_questions[i].get("q", ""), "a": _ans_str(ss.mc_answers.get(i, []))}
                          for i in range(len(ss.mc_questions))]
            form_ctx = dict(fd)
            form_ctx["date"] = f"{fd.get('year','')} {fd.get('month','')}"
            result = sync.generate_ai_content(api_key, model, form_ctx, mc_payload)
            if not result and model != "gemini-1.5-flash":
                portal.log(f"{model} failed, retrying with gemini-1.5-flash...")
                result = sync.generate_ai_content(api_key, "gemini-1.5-flash", form_ctx, mc_payload)
            ov.empty()
            if result:
                ss.ai_result = result
                portal.log("AI content generated.")
                st.success("AI content ready. Review below, then proceed to sync.")
            else:
                portal.log("AI generation FAILED.")
                st.error("AI generation failed. Exact reason from Google:")
                st.code(sync.last_error or "No detail captured.", language="text")

        # --- Preview generated content ---
        if ss.ai_result:
            st.markdown("---")
            sync.render_ui(ss.ai_result)
            st.markdown("---")
            if st.button("PROCEED TO REVIEW & SYNC →", type="primary", use_container_width=True):
                ss.page = 2
                st.rerun()

    # ========================================================
    # PAGE 2 — REVIEW + GATED SYNC
    # ========================================================
    elif ss.page == 2:
        if st.button("← BACK"):
            ss.page = 1
            st.rerun()

        miss = missing_inputs(fd, ss.assets)
        mc_complete = bool(ss.mc_questions) and len([v for v in ss.mc_answers.values() if v]) == len(ss.mc_questions)
        content_ready = bool(ss.ai_result)
        all_ready = (not miss) and mc_complete and content_ready

        st.markdown('<div class="sec-header">Review</div>', unsafe_allow_html=True)
        st.write({
            "project_id": fd.get("project_id"),
            "client": fd.get("client"), "project": fd.get("project"),
            "venue": fd.get("venue"), "date": f"{fd.get('year','')} {fd.get('month','')}",
            "category": fd.get("category"), "what_we_do": fd.get("what_we_do"),
            "scope_count": len(fd.get("scope", [])),
            "photos": len(ss.assets.get("photos", [])),
            "hero_index": ss.assets.get("hero_index"),
            "logo_black": bool(ss.assets.get("logo_black")),
            "logo_white": bool(ss.assets.get("logo_white")),
            "mc_complete": mc_complete,
            "content_ready": content_ready,
        })

        st.markdown('<div class="sec-header">Sync Gate</div>', unsafe_allow_html=True)
        gate_items = [
            ("All required inputs", not miss),
            ("15 MC answered (100%)", mc_complete),
            ("AI content generated", content_ready),
        ]
        for label, ok in gate_items:
            cls = "pill-ok" if ok else "pill-bad"
            mark = "✓" if ok else "✗"
            st.markdown(f"- <span class='{cls}'>{mark} {label}</span>", unsafe_allow_html=True)
        if miss:
            st.caption("Missing inputs: " + ", ".join(miss))

        do_sync = st.button("🚀 EXECUTE MASTER SYNC", disabled=not all_ready, type="primary")
        if not all_ready:
            st.caption("Sync is blocked until all three gate items are complete.")
        if do_sync:
            ov = breathing_overlay("WRITING TO MASTER DB")
            result = sync.push_to_gas(fd, ss.ai_result or {}, ss.assets or {})
            ov.empty()
            if isinstance(result, dict) and result.get("ok"):
                portal.log(f"Sync OK (HTTP {result.get('status')}).")
                # --- Two-phase Project ID reconciliation ---
                # The Handler assigns the REAL, DB-unique ID (FB<year><seq>) and returns it.
                # If it differs from the provisional one used while generating content,
                # rewrite the profile.html links inside the social copy so they point to
                # the correct project page.
                resp = result.get("response") or {}
                real_id = resp.get("project_id") if isinstance(resp, dict) else None
                old_id = fd.get("project_id")
                if real_id and real_id != old_id:
                    fd["project_id"] = real_id
                    ss.form_data["project_id"] = real_id
                    old_url = f"https://firebean.net/profile.html?id={str(old_id).lower()}"
                    new_url = f"https://firebean.net/profile.html?id={str(real_id).lower()}"
                    sm = (ss.ai_result or {}).get("SocialMedia") or {}
                    for k, v in list(sm.items()):
                        if isinstance(v, str) and old_url in v:
                            sm[k] = v.replace(old_url, new_url)
                    portal.log(f"Project ID assigned by DB: {real_id} (was {old_id}). Profile links updated.")
                    st.info(f"📌 Final Project ID: {real_id} (profile links updated to match).")
                st.success("✅ Sync Complete — written to Master DB. Now run CMS Sync in the Sheet to push to GitHub.")
                st.json(result.get("response"))
            else:
                detail = result.get("response") if isinstance(result, dict) else result
                portal.log("Sync FAILED.")
                st.error("❌ Sync failed. Details below.")
                st.json({"status": result.get("status") if isinstance(result, dict) else None, "detail": detail})

    # --- Terminal ---
    st.markdown('<div class="terminal-box">' +
                "".join([f"<p>{log}</p>" for log in ss.terminal_logs]) +
                '</div>', unsafe_allow_html=True)
