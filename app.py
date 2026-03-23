import streamlit as st
from google import genai
import io
import base64
import time
import json
import requests
import re
from PIL import Image, ImageDraw, ImageOps
from datetime import datetime

# --- 1. Core Configuration ---
SHEET_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbzaQu2KpJ06I0yWL4dEwk0naB1FOlHkt7Ta340xH84IDwQI7jQNUI3eSmxrwKyQHNj5/exec"
SLIDE_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbyZvtm8M8a5sLYF3vz9kLyAdimzzwpSlnTkzIeQ3DJxkklNYNlwSoJc5j5CkorM6w5V/exec"
STABLE_MODEL_ID = "gemini-2.5-flash"

WHO_WE_HELP_OPTIONS = ["GOVERNMENT & PUBLIC SECTOR", "LIFESTYLE & CONSUMER", "F&B & HOSPITALITY", "MALLS & VENUES"]
WHAT_WE_DO_OPTIONS = ["ROVING EXHIBITIONS", "SOCIAL & CONTENT", "INTERACTIVE & TECH", "PR & MEDIA", "EVENTS & CEREMONIES"]
SOW_OPTIONS = ["Event Planning", "Event Coordination", "Event Production", "Theme Design", "Concept Development", "Social Media Management", "KOL / MI Line up", "Artist Endorsement", "Media Pitching", "PR Consulting", "Souvenir Sourcing"]

CURRENT_YEAR = datetime.now().year
YEAR_OPTIONS = [str(y) for y in range(CURRENT_YEAR, 2011, -1)]
MONTH_OPTIONS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]

# --- Helpers ---
def format_faq_to_python_string(faq_list):
    if not faq_list: return "[]"
    formatted_pairs = []
    for qa_pair in faq_list:
        q_key = list(qa_pair.keys())[0]
        a_key = list(qa_pair.keys())[1]
        question = str(qa_pair[q_key]).replace("'", "\\'")
        answer = str(qa_pair[a_key]).replace("'", "\\'")
        formatted_pairs.append(f"{{'{q_key}': '{question}', '{a_key}': '{answer}'}}")
    return f"[" + ", ".join(formatted_pairs) + "]"

def generate_system_metadata():
    try:
        count_res = requests.get(SHEET_SCRIPT_URL + "?action=get_row_count", timeout=5)
        next_index = int(count_res.text) + 1 if count_res.status_code == 200 else 100
    except:
        next_index = 999 
    project_id = f"FB{st.session_state.event_year}{str(next_index).zfill(3)}"
    month_map = {m: str(i+1).zfill(2) for i, m in enumerate(MONTH_OPTIONS)}
    sort_date = f"{st.session_state.event_year}-{month_map.get(st.session_state.event_month, '01')}-01"
    return project_id, sort_date

FIREBEAN_SYSTEM_PROMPT = """
You are a Lead PR Strategist and Chief Editor for a premium B2B/B2C communications agency.
Task: Transform diagnostic data into a professional PR strategy JSON.
Always return a valid JSON object with keys: challenge_summary, solution_summary, 1_google_slide, 2_facebook_post, 3_threads_post, 4_instagram_post, 5_linkedin_post, 6_website, 7_faq.
(Retrospective tone, valid HTML structure <h1>/<h3>/<p>, 500 words for website, 5 FAQ pairs per language)
"""

def log_debug(msg, type="info"):
    ts = datetime.now().strftime("%H:%M:%S")
    if "debug_logs" not in st.session_state: st.session_state.debug_logs = []
    st.session_state.debug_logs.append(f"[{ts}] [{type.upper()}] {msg}")

def clean_field(text):
    if not text: return ""
    noise = ["Basic Info", "Firebean_Master_DB", "100%", "Explore", "Summarize this data"]
    for n in noise: text = text.replace(n, "")
    return text.strip()

def call_gemini_sdk(prompt, image_files=None, is_json=False):
    try:
        client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
        contents = [FIREBEAN_SYSTEM_PROMPT, prompt]
        if image_files:
            for f in image_files:
                if hasattr(f, "seek"): f.seek(0)
                img = Image.open(f).convert('RGB')
                img = ImageOps.exif_transpose(img)
                contents.append(img)
        config = genai.types.GenerateContentConfig(response_mime_type="application/json") if is_json else None
        response = client.models.generate_content(model=STABLE_MODEL_ID, contents=contents, config=config)
        return response.text
    except Exception as e:
        log_debug(f"Gemini API Error: {str(e)}", "error")
        return None

# --- UI Styles ---
def apply_styles(is_dark):
    bg_color = "#21252B" if is_dark else "#E0E5EC"
    text_color = "#FFFFFF" if is_dark else "#31344B"
    card_bg = "#21252B" if is_dark else "#E0E5EC"
    shadow_dark = "#1a1d23" if is_dark else "#a3b1c6"
    shadow_light = "#2a2f38" if is_dark else "#ffffff"
    st.markdown(f"""
    <style>
        html, body, [data-testid="stAppViewContainer"] {{ background-color: {bg_color} !important; color: {text_color} !important; }}
        .neu-card {{ background-color: {card_bg}; border-radius: 20px; padding: 25px; box-shadow: 9px 9px 18px {shadow_dark}, -9px -9px 18px {shadow_light}; margin-bottom: 25px; }}
        .stButton > button {{ border-radius: 14px !important; box-shadow: 6px 6px 12px {shadow_dark}, -6px -6px 12px {shadow_light} !important; }}
    </style>""", unsafe_allow_html=True)

# --- Session State ---
def init_session_state():
    defaults = {
        "active_tab": "Project Collector", "client_name": "", "project_name": "", "venue": "",
        "event_year": str(CURRENT_YEAR), "event_month": "JAN", "youtube": "", "category": WHO_WE_HELP_OPTIONS[0],
        "what_we_do": [], "scope": [], "project_photos": [], "mc_questions": None, "open_question_ans": "",
        "ai_content": None, "debug_logs": [], "draft_project_id": None, "user_dark_mode": None,
        "logo_black": None, "logo_white": None, "hero_photo_index": 0, "sync_success": False,
        "drive_folder": "", "hero_photo_url": ""
    }
    for k, v in defaults.items():
        if k not in st.session_state: st.session_state[k] = v

def reset_for_new_case():
    for k in ["client_name", "project_name", "venue", "youtube", "what_we_do", "scope", "project_photos", "mc_questions", "open_question_ans", "ai_content", "draft_project_id", "sync_success", "drive_folder", "hero_photo_url", "logo_black", "logo_white"]:
        st.session_state[k] = "" if isinstance(st.session_state[k], str) else ([] if isinstance(st.session_state[k], list) else None)
    st.session_state.active_tab = "Project Collector"

def main():
    st.set_page_config(page_title="Firebean Brain Collector v5.0", layout="wide")
    init_session_state()
    is_dark = st.session_state.user_dark_mode if st.session_state.user_dark_mode is not None else (datetime.now().hour >= 19 or datetime.now().hour < 7)
    apply_styles(is_dark)

    # Navigation
    if st.button("🏠 HOME"):
        if st.session_state.sync_success: reset_for_new_case()
        else: st.session_state.active_tab = "Project Collector"
        st.rerun()

    nav_cols = st.columns(3)
    tabs = ["Project Collector", "Review & Multi-Sync", "Load Project"]
    for i, tab in enumerate(tabs):
        if nav_cols[i].button(tab, use_container_width=True, type="primary" if st.session_state.active_tab == tab else "secondary"):
            st.session_state.active_tab = tab
            st.rerun()

    # --- TAB: Project Collector ---
    if st.session_state.active_tab == "Project Collector":
        st.markdown('<div class="neu-card">', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            if st.session_state.logo_black and st.session_state.logo_black.startswith("http"):
                st.success("✅ Using existing Black Logo")
                if st.button("Change Black Logo"): st.session_state.logo_black = None; st.rerun()
            else:
                ub = st.file_uploader("Upload Black Logo", type=['png'])
                if ub: st.session_state.logo_black = base64.b64encode(ub.read()).decode('utf-8')

        with col2:
            if st.session_state.logo_white and st.session_state.logo_white.startswith("http"):
                st.success("✅ Using existing White Logo")
                if st.button("Change White Logo"): st.session_state.logo_white = None; st.rerun()
            else:
                uw = st.file_uploader("Upload White Logo", type=['png'])
                if uw: st.session_state.logo_white = base64.b64encode(uw.read()).decode('utf-8')

        b1, b2, b3 = st.columns(3)
        st.session_state.client_name = clean_field(b1.text_input("Client", value=st.session_state.client_name))
        st.session_state.project_name = clean_field(b2.text_input("Project", value=st.session_state.project_name))
        st.session_state.venue = clean_field(b3.text_input("Venue", value=st.session_state.venue))

        # Additional fields... (Category, What we do, SOW, etc.)
        # Simplified for brevity in this snippet
        
        if st.button("生成 15 題繁中診斷題目"):
            # AI Logic here...
            pass
        st.markdown('</div>', unsafe_allow_html=True)

    # --- TAB: Review & Multi-Sync ---
    elif st.session_state.active_tab == "Review & Multi-Sync":
        if st.button("Sync to Master DB"):
            with st.spinner("Syncing..."):
                payload = {
                    "action": "sync_project",
                    "project_id": st.session_state.draft_project_id or generate_system_metadata()[0],
                    "client_name": st.session_state.client_name,
                    "project_name": st.session_state.project_name,
                    "drive_folder": st.session_state.drive_folder,
                    "logo_black": st.session_state.logo_black,
                    "logo_white": st.session_state.logo_white,
                    "hero_photo": st.session_state.hero_photo_url,
                    # Other fields...
                }
                # Handle FAQ formatting
                if st.session_state.ai_content and "7_faq" in st.session_state.ai_content:
                    faq = st.session_state.ai_content["7_faq"]
                    payload["faq_en"] = format_faq_to_python_string(faq.get("en", []))
                    payload["faq_tc"] = format_faq_to_python_string(faq.get("tc", []))
                    payload["faq_jp"] = format_faq_to_python_string(faq.get("jp", []))
                
                res = requests.post(SHEET_SCRIPT_URL, json=payload).json()
                if res.get("success"):
                    st.session_state.sync_success = True
                    st.success("✅ Synced Successfully!")

    # --- TAB: Load Project ---
    elif st.session_state.active_tab == "Load Project":
        query = st.text_input("Search Project ID or Client")
        if st.button("Search"):
            res = requests.post(SHEET_SCRIPT_URL, json={"action": "get_raw_input_list"}).json()
            if res.get("success"):
                matches = [p for p in res["projects"] if query.lower() in p["project_id"].lower() or query.lower() in p["client"].lower()]
                for m in matches:
                    if st.button(f"Load {m['project_id']}"):
                        details = requests.post(SHEET_SCRIPT_URL, json={"action": "get_raw_input_details", "project_id": m["project_id"]}).json()
                        if details.get("success"):
                            p = details["project"]
                            st.session_state.client_name = p["client"]
                            st.session_state.project_name = p["project_name"]
                            st.session_state.drive_folder = p["drive_folder"]
                            st.session_state.logo_black = p["logo_black"]
                            st.session_state.logo_white = p["logo_white"]
                            st.session_state.hero_photo_url = p["hero_photo"]
                            st.session_state.draft_project_id = p["project_id"]
                            st.success(f"Loaded {m['project_id']}!")

if __name__ == "__main__":
    main()
