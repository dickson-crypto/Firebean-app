# VERSION: v18.10.2 (Surface real Gemini API errors + model auto-retry)
# TIMESTAMP: 2026-06-19 12:23:00 HKT
#
# WHAT CHANGED vs v18.9.12:
#   - v18.9.12's "EXECUTE MASTER SYNC" button ran `run_with_overlay(steps, lambda: True)`
#     and then printed "Sync Complete" WITHOUT ever calling sync.push_to_gas().
#     The sync was a no-op. Nothing was ever sent to the Master DB.
#   - It also never stored the form inputs into session_state, never collected a
#     Gemini API key, never ran AI generation, and never collected the assets.
#   - This version wires the full pipeline back together and calls the REAL
#     synthesis_sync.SynthesisSync.push_to_gas(form, ai, assets), whose payload now
#     matches the deployed doPost handler (apps-script/sync-to-github.gs).

import streamlit as st
import requests
import time
import re
from datetime import datetime

# --- Modular Imports ---
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
        self.VERSION = "v18.10.2"
        self.MODELS = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]
        self.ICONS = {
            "DB": '<svg width="120" height="120" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="1.5"><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/></svg>',
            "BRAIN": '<svg width="120" height="120" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="1.5"><rect x="4" y="4" width="16" height="16" rx="2"/><rect x="9" y="9" width="6" height="6"/></svg>',
            "CLOUD": '<svg width="120" height="120" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="1.5"><path d="M18 10h-1.26A8 8 0 1 0 9 20h9a5 5 0 0 0 0-10z"/></svg>',
        }
        self.init_session()

    def init_session(self):
        if 'page' not in st.session_state:
            st.session_state.page = 1
        if 'terminal_logs' not in st.session_state:
            st.session_state.terminal_logs = [f"> Boot: {self.VERSION}"]
        if 'form_data' not in st.session_state:
            st.session_state.form_data = {}
        if 'hero_index' not in st.session_state:
            st.session_state.hero_index = 0
        if 'ai_result' not in st.session_state:
            st.session_state.ai_result = None
        if 'assets' not in st.session_state:
            st.session_state.assets = {"logo_black": None, "logo_white": None, "photos": [], "hero_index": 0}

    def log(self, msg):
        ts = datetime.now().strftime("%H:%M:%S")
        st.session_state.terminal_logs.append(f"[{ts}] {msg}")
        if len(st.session_state.terminal_logs) > 12:
            st.session_state.terminal_logs.pop(0)

    def run_with_overlay(self, steps, task_func, *args):
        """Show a fullscreen overlay while task_func runs, then return its result."""
        overlay = st.empty()
        for icon, text in steps:
            overlay.markdown(f'''
                <div style="position:fixed; top:0; left:0; width:100vw; height:100vh; background:#121212; z-index:9999; display:flex; justify-content:center; align-items:center;">
                    <div style="text-align:center;">{icon}<h2 style="color:white;">{text}</h2></div>
                </div>
            ''', unsafe_allow_html=True)
            time.sleep(0.6)
        res = task_func(*args)
        overlay.empty()
        return res


def generate_project_id(client, project):
    """Lightweight FB-prefixed ID. The handler upper-cases and matches on this."""
    base = re.sub(r'[^A-Za-z0-9]', '', f"{client}{project}").upper()[:8]
    stamp = datetime.now().strftime("%y%m%d%H%M")
    return f"FB{stamp}{base}" if base else f"FB{stamp}"


# --- APP EXECUTION ---
if __name__ == "__main__":
    st.set_page_config(page_title="Firebean Portal", layout="wide")
    portal = FirebeanPortal()
    inputs, gate, ai_mc, sync = InputEngine(), ProgressGate(), AIDiagnostic(), SynthesisSync()

    st.markdown("""<style>
        .stApp { background-color: #121212; color: white; }
        .sec-header { font-size: 18px; font-weight: 900; color: #E2231A; text-transform: uppercase; letter-spacing: 1px; margin: 20px 0 10px; border-bottom: 1px solid #333; padding-bottom: 6px; }
        .terminal-box { background: #000; padding: 15px; border-left: 4px solid #E2231A; height: 160px; overflow-y: auto; font-family: monospace; font-size: 12px; margin-top: 25px; }
        .terminal-box p { margin: 2px 0; color: #4ade80; }
    </style>""", unsafe_allow_html=True)

    # --- Header ---
    c1, c2 = st.columns([1, 9])
    with c1:
        st.image("https://raw.githubusercontent.com/dickson-crypto/Firebean-app/main/Firebeanlogo2026.png")
    with c2:
        st.markdown(f"<h1>Project Collector. <span style='font-size:14px;opacity:0.5;'>{portal.VERSION}</span></h1>", unsafe_allow_html=True)

    fd = st.session_state.form_data

    # ============================================================
    # PAGE 1 — COLLECT EVERYTHING
    # ============================================================
    if st.session_state.page == 1:
        # --- API key + model (required for AI generation) ---
        st.markdown('<div class="sec-header">AI Engine</div>', unsafe_allow_html=True)

        # Read the key from Streamlit Secrets (Settings -> Secrets -> GEMINI_API_KEYS).
        # Falls back to manual entry if the secret is not set.
        secret_key = ""
        try:
            secret_key = st.secrets.get("GEMINI_API_KEYS", "") or st.secrets.get("GEMINI_API_KEY", "")
        except Exception:
            secret_key = ""

        if secret_key:
            st.success("🔐 Gemini API key loaded from Streamlit Secrets.")
        else:
            st.info("No secret found. Paste your Gemini API key below, or add it in "
                    "Settings → Secrets as  GEMINI_API_KEYS = \"AIza...\"")

        k1, k2 = st.columns([2, 1])
        api_key = k1.text_input("Gemini API Key", type="password",
                                value=st.session_state.get("api_key", "") or secret_key,
                                help="Loaded from Secrets if set. You can override it here for this session.")
        model = k2.selectbox("Model", portal.MODELS, index=0)
        st.session_state.api_key = api_key

        # --- Identity ---
        client, project, venue, year, month = inputs.render_identity()

        # --- Framework ---
        sel_cat, sel_wwd, sel_sow = inputs.render_framework()

        # --- Strategic brief ---
        st.markdown('<div class="sec-header">Strategic Brief</div>', unsafe_allow_html=True)
        open_q = st.text_area("Brief / context for the AI (the project's goal, pain points, results)",
                              value=fd.get("open_question", ""), height=120)
        youtube = st.text_input("YouTube URL (optional)", value=fd.get("youtube", ""))

        # --- Assets ---
        lb, lw, ph, encoded = inputs.render_assets()

        # --- Persist EVERYTHING to session_state.form_data ---
        st.session_state.form_data = {
            "client": client, "project": project, "venue": venue,
            "year": year, "month": month,
            "category": sel_cat, "what_we_do": sel_wwd, "scope": sel_sow,
            "open_question": open_q, "youtube": youtube,
            "project_id": fd.get("project_id") or generate_project_id(client, project),
        }

        # --- Process assets to base64 dicts the handler expects ---
        logo_black = inputs.process_for_db(lb, is_logo=True) if lb else None
        logo_white = inputs.process_for_db(lw, is_logo=True) if lw else None
        photos = []
        if ph:
            for p in ph[:8]:
                processed = inputs.process_for_db(p, is_logo=False)
                if processed:
                    photos.append(processed["data"])  # base64 string
        st.session_state.assets = {
            "logo_black": logo_black["data"] if logo_black else None,
            "logo_white": logo_white["data"] if logo_white else None,
            "photos": photos,
            "hero_index": st.session_state.hero_index,
        }

        score = gate.calculate(st.session_state.form_data,
                               assets_ready=bool(photos),
                               mc_ready=bool(st.session_state.ai_result))
        st.progress(score / 100, text=f"Readiness: {score}%")

        col_a, col_b = st.columns([1, 1])
        # --- Generate AI content ---
        if col_a.button("🧠 GENERATE AI CONTENT", use_container_width=True):
            if not api_key:
                st.error("Enter your Gemini API Key first.")
            elif not (client and project):
                st.error("Client and Project are required.")
            else:
                form_ctx = dict(st.session_state.form_data)
                form_ctx["date"] = f"{year} {month}"
                steps = [(portal.ICONS["BRAIN"], "GENERATING CASE STUDY + SOCIAL COPY")]
                result = portal.run_with_overlay(steps, sync.generate_ai_content, api_key, model, form_ctx)

                # Auto-retry once with the most reliably available model if the chosen one fails
                if not result and model != "gemini-1.5-flash":
                    portal.log(f"{model} failed, retrying with gemini-1.5-flash...")
                    result = portal.run_with_overlay(
                        [(portal.ICONS["BRAIN"], "RETRYING WITH gemini-1.5-flash")],
                        sync.generate_ai_content, api_key, "gemini-1.5-flash", form_ctx)

                if result:
                    st.session_state.ai_result = result
                    portal.log("AI content generated.")
                    st.success("AI content ready. Review below, then proceed.")
                else:
                    portal.log("AI generation FAILED.")
                    st.error("AI generation failed. Exact reason from Google's API below:")
                    st.code(sync.last_error or "No error detail captured.", language="text")

        if col_b.button("PROCEED TO REVIEW & SYNC →", type="primary", use_container_width=True):
            st.session_state.page = 2
            st.rerun()

        # --- Show AI preview if available ---
        if st.session_state.ai_result:
            st.markdown("---")
            sync.render_ui(st.session_state.ai_result)

    # ============================================================
    # PAGE 2 — REVIEW + REAL SYNC
    # ============================================================
    elif st.session_state.page == 2:
        if st.button("← BACK"):
            st.session_state.page = 1
            st.rerun()

        f = st.session_state.form_data
        st.markdown('<div class="sec-header">Review</div>', unsafe_allow_html=True)
        st.write({
            "project_id": f.get("project_id"),
            "client": f.get("client"), "project": f.get("project"),
            "venue": f.get("venue"), "date": f"{f.get('year','')} {f.get('month','')}",
            "category": f.get("category"), "what_we_do": f.get("what_we_do"),
            "scope_count": len(f.get("scope", [])),
            "photos": len(st.session_state.assets.get("photos", [])),
            "hero_index": st.session_state.assets.get("hero_index"),
            "ai_content_ready": bool(st.session_state.ai_result),
        })

        if not st.session_state.ai_result:
            st.warning("No AI content generated yet. You can still sync the raw data, "
                       "but social/web/FAQ columns will be empty. Go BACK to generate first.")

        if st.button("🚀 EXECUTE MASTER SYNC", type="primary"):
            if not (f.get("client") and f.get("project")):
                st.error("Client and Project are required before sync.")
            else:
                steps = [(portal.ICONS["DB"], "WRITING TO MASTER DB")]
                ai_payload = st.session_state.ai_result or {}
                assets = st.session_state.assets or {}
                # THE REAL CALL — this is what v18.9.12 was missing.
                result = portal.run_with_overlay(steps, sync.push_to_gas, f, ai_payload, assets)

                if isinstance(result, dict) and result.get("ok"):
                    portal.log(f"Sync OK (HTTP {result.get('status')}).")
                    st.success("✅ Sync Complete — data written to Master DB. "
                               "Now run the CMS Sync in the Sheet to push to GitHub.")
                    st.json(result.get("response"))
                else:
                    detail = result.get("response") if isinstance(result, dict) else result
                    portal.log("Sync FAILED.")
                    st.error("❌ Sync failed. Details below.")
                    st.json({"status": result.get("status") if isinstance(result, dict) else None,
                             "detail": detail})

    # --- Persistent Terminal ---
    st.markdown('<div class="terminal-box">' +
                "".join([f"<p>{log}</p>" for log in st.session_state.terminal_logs]) +
                '</div>', unsafe_allow_html=True)
