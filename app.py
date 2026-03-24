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

# --- 1. Core Config ---
SHEET_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbwsg-e1zyG6BW4Mp2AM-RHSfxI4Ooq9y-RR4XBkM6iZjNtL-hqBWlK1sGiIlppbTKin/exec"
STABLE_MODEL_ID = "gemini-2.5-flash"

WHO_WE_HELP_OPTIONS = ["GOVERNMENT & PUBLIC SECTOR", "LIFESTYLE & CONSUMER", "F&B & HOSPITALITY", "MALLS & VENUES"]
WHAT_WE_DO_OPTIONS = ["ROVING EXHIBITIONS", "SOCIAL & CONTENT", "INTERACTIVE & TECH", "PR & MEDIA", "EVENTS & CEREMONIES"]
SOW_OPTIONS = ["Event Planning", "Event Coordination", "Event Production", "Theme Design", "Concept Development", "Social Media Management", "KOL / MI Line up", "Artist Endorsement", "Media Pitching", "PR Consulting", "Souvenir Sourcing"]

CURRENT_YEAR = datetime.now().year
YEAR_OPTIONS = [str(y) for y in range(CURRENT_YEAR, 2011, -1)]
MONTH_OPTIONS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]

# Placeholder base64 image (1x1 transparent PNG)
DUMMY_IMAGE_BASE64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="

def format_faq_to_python_string(faq_list):
    if not faq_list: return "[]"
    if isinstance(faq_list, str): return faq_list if faq_list.strip().startswith('[') else "[]"
    if not isinstance(faq_list, list): return "[]"
    formatted_pairs = []
    for qa_pair in faq_list:
        if not isinstance(qa_pair, dict): continue
        keys = list(qa_pair.keys())
        if len(keys) < 2: continue
        q_key, a_key = keys[0], keys[1]
        question = str(qa_pair[q_key]).replace("\\", "\\\\").replace("'", "\\'")
        answer = str(qa_pair[a_key]).replace("\\", "\\\\").replace("'", "\\'")
        formatted_pairs.append(f"{{'{q_key}': '{question}', '{a_key}': '{answer}'}}")
    return "[" + ", ".join(formatted_pairs) + "]"

def generate_system_metadata():
    month_map = {m: str(i+1).zfill(2) for i, m in enumerate(MONTH_OPTIONS)}
    m_num = month_map.get(st.session_state.event_month, "01")
    sort_date = f"{st.session_state.event_year}-{m_num}-01"
    if st.session_state.get("draft_project_id"):
        return st.session_state.draft_project_id, sort_date
    try:
        count_res = requests.get(SHEET_SCRIPT_URL + "?action=get_row_count", timeout=10)
        next_index = int(count_res.text) + 1 if (count_res.status_code == 200 and count_res.text.isdigit()) else 999
    except:
        next_index = 999
    project_id = f"FB{st.session_state.event_year}{st.session_state.event_month}{str(next_index).zfill(3)}"
    return project_id, sort_date

def log_debug(msg):
    if "debug_logs" not in st.session_state: st.session_state.debug_logs = []
    st.session_state.debug_logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

def init_session_state():
    defaults = {
        "client_name": "", "project_name": "", "venue": "",
        "event_year": str(CURRENT_YEAR), "event_month": "JAN",
        "youtube": "", "category": WHO_WE_HELP_OPTIONS[0],
        "what_we_do": [], "scope": [], "project_photos": [],
        "open_question_ans": "", "ai_content": None, "debug_logs": [],
        "logo_black": None, "logo_white": None, "hero_photo_index": 0
    }
    for k, v in defaults.items():
        if k not in st.session_state: st.session_state[k] = v

def trigger_full_sync():
    try:
        project_id, sort_date = generate_system_metadata()
        display_date = f"{st.session_state.event_month} {st.session_state.event_year}"
        ai = st.session_state.ai_content or {}
        faq = ai.get("7_faq", {})
        
        payload = {
            "action": "sync_project",
            "client_name": st.session_state.client_name,
            "project_name": st.session_state.project_name, # This fills the 'Project' column
            "project_id": project_id,
            "date": display_date,
            "sort_date": sort_date,
            "venue": st.session_state.venue,
            "category": st.session_state.category,
            "category_what": ", ".join(st.session_state.what_we_do),
            "scope": ", ".join(st.session_state.scope),
            "youtube": st.session_state.youtube,
            "open_question": st.session_state.open_question_ans,
            "challenge": ai.get("challenge_summary", ""),
            "solution": ai.get("solution_summary", ""),
            "faq_en": format_faq_to_python_string(faq.get("en", [])),
            "faq_tc": format_faq_to_python_string(faq.get("tc", [])),
            "faq_jp": format_faq_to_python_string(faq.get("jp", [])),
            "ai_content": ai,
            "logo_black": st.session_state.logo_black,
            "logo_white": st.session_state.logo_white,
            "images": [DUMMY_IMAGE_BASE64] * 3 if not st.session_state.project_photos else st.session_state.project_photos
        }
        
        r = requests.post(SHEET_SCRIPT_URL, json=payload, timeout=120)
        return r.status_code == 200
    except Exception as e:
        log_debug(f"Sync error: {str(e)}")
        return False

def fill_dummy_data():
    st.session_state.client_name = "TEST CLIENT"
    st.session_state.project_name = "TEST PROJECT FOLDER NAME"
    st.session_state.venue = "101 Studio"
    st.session_state.event_year = "2026"
    st.session_state.event_month = "MAR"
    st.session_state.youtube = "https://youtube.com/test"
    st.session_state.category = "LIFESTYLE & CONSUMER"
    st.session_state.what_we_do = ["SOCIAL & CONTENT", "PR & MEDIA"]
    st.session_state.scope = ["Event Planning", "Concept Development"]
    st.session_state.open_question_ans = "Dummy open question answer."
    st.session_state.logo_black = DUMMY_IMAGE_BASE64
    st.session_state.logo_white = DUMMY_IMAGE_BASE64
    st.session_state.ai_content = {
        "challenge_summary": "Dummy challenge.",
        "solution_summary": "Dummy solution.",
        "1_google_slide": "https://docs.google.com/presentation/d/1ULmmW5A1zalNtgwFXsG1ldxiiGZjkSEu9JvVkvNIm-g/edit?usp=sharing",
        "2_facebook_post": "Dummy FB",
        "3_threads_post": "Dummy Threads",
        "4_instagram_post": "Dummy IG",
        "5_linkedin_post": "Dummy LinkedIn",
        "6_website": {"en": "<h1>Test</h1>", "tc": "<h1>測試</h1>", "jp": "<h1>テスト</h1>"},
        "7_faq": {"en": [{"Q": "Q?", "A": "A!"}], "tc": [{"Q": "問題？", "A": "回答！"}], "jp": [{"Q": "質問？", "A": "答え！"}]}
    }

def main():
    st.set_page_config(page_title="Firebean Brain Collector", layout="wide")
    init_session_state()
    if st.sidebar.button("Fill Dummy Data"):
        fill_dummy_data()
        st.rerun()
    if st.button("Sync to Master DB"):
        if trigger_full_sync(): st.success("Sync Success!")
        else: st.error("Sync Failed!")

if __name__ == "__main__":
    main()
