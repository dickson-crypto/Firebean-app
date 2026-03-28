import streamlit as st
import google.generativeai as genai
import io
import base64
import time
import json
import requests
import re
from PIL import Image, ImageDraw, ImageOps
from datetime import datetime

# --- 1. 核心配置 (Updated with your New URLs) ---
# This is for Master DB (Log data & fetch drafts)
SHEET_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbxy6JwJpmclJOBerKJO4EJ50oKyL86Ux1Qci2oHx1RQiw8ruL_Um6qVYsWydyEsLawQ/exec"
# This is for the Slide Creator (High-Fidelity centered crop)
SLIDE_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbxKP-8Xrvy6hblPqTmtXn76rO3DFOeU6jYQtLw5QDfDP1-adNDk02bhoKihfvp_Xsvy/exec"

STABLE_MODEL_ID = "gemini-2.0-flash"

WHO_WE_HELP_OPTIONS = ["GOVERNMENT & PUBLIC SECTOR", "LIFESTYLE & CONSUMER", "F&B & HOSPITALITY", "MALLS & VENUES"]
WHAT_WE_DO_OPTIONS = ["ROVING EXHIBITIONS", "SOCIAL & CONTENT", "INTERACTIVE & TECH", "PR & MEDIA", "EVENTS & CEREMONIES"]
SOW_OPTIONS = ["Event Planning", "Event Coordination", "Event Production", "Theme Design", "Concept Development", "Social Media Management", "KOL / MI Line up", "Artist Endorsement", "Media Pitching", "PR Consulting", "Souvenir Sourcing"]

CURRENT_YEAR = datetime.now().year
YEAR_OPTIONS = [str(y) for y in range(CURRENT_YEAR, 2011, -1)]
MONTH_OPTIONS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]

# --- 🛡️ FAQ Cleaning ---
def safe_flatten_faq(faq_input):
    if not faq_input: return "[]"
    if isinstance(faq_input, (list, dict)):
        return json.dumps(faq_input, ensure_ascii=False)
    if isinstance(faq_input, str):
        faq_input = faq_input.strip()
        try:
            parsed = json.loads(faq_input)
            return json.dumps(parsed, ensure_ascii=False)
        except:
            return faq_input.replace("\n", " ").replace("\r", "").strip()
    return "[]"

# --- System Metadata ---
def generate_system_metadata():
    month_map = {m: str(i+1).zfill(2) for i, m in enumerate(MONTH_OPTIONS)}
    m_num = month_map.get(st.session_state.event_month, "01")
    sort_date = f"{st.session_state.event_year}-{m_num}-01"
    try:
        count_res = requests.get(SHEET_SCRIPT_URL + "?action=get_row_count", timeout=5)
        next_index = int(count_res.text) + 1 if count_res.status_code == 200 else 100
    except:
        next_index = 999 
    project_id = f"FB{st.session_state.event_year}{str(next_index).zfill(3)}"
    return project_id, sort_date

FIREBEAN_SYSTEM_PROMPT = """
You are a Lead PR Strategist and Chief Editor. Transform diagnostic data into a professional PR strategy JSON.
Keys: challenge_summary, solution_summary, 1_google_slide, 2_facebook_post, 3_threads_post, 4_instagram_post, 5_linkedin_post, 6_website, 7_faq.
Written in past tense retrospective mode. No internal terms like 'Firebean Brain'.
"""

# --- Debug Logging ---
def log_debug(msg, type="info"):
    if "debug_logs" not in st.session_state: st.session_state.debug_logs = []
    timestamp = datetime.now().strftime("%H:%M:%S")
    st.session_state.debug_logs.append({"time": timestamp, "msg": msg, "type": type})

# --- Gemini SDK ---
def call_gemini_sdk(prompt, image_files=None, is_json=False, max_retries=2):
    secret_key = st.secrets.get("GEMINI_API_KEY", "")
    if not secret_key: return None
    for attempt in range(max_retries):
        try:
            genai.configure(api_key=secret_key)
            model = genai.GenerativeModel(model_name=STABLE_MODEL_ID, system_instruction=FIREBEAN_SYSTEM_PROMPT)
            contents = [prompt]
            if image_files:
                for f in image_files:
                    if hasattr(f, "seek"): f.seek(0)
                    img = Image.open(f)
                    img = ImageOps.exif_transpose(img)
                    img.thumbnail((800, 800))
                    contents.append(img)
            response = model.generate_content(contents, generation_config={"response_mime_type": "application/json" if is_json else "text/plain", "temperature": 0.2})
            if response and response.text:
                text = response.text.strip()
                if not is_json: return text
                match = re.search(r'(\{.*\})|(\[.*\])', text, re.DOTALL)
                json_str = match.group(0) if match else text
                return json_str
        except Exception as e:
            log_debug(f"Gemini Error: {str(e)}", "error")
    return None

def init_session_state():
    fields = {
        "active_tab": "Project Collector", "client_name": "", "project_name": "", "venue": "", "youtube": "",
        "event_year": str(CURRENT_YEAR), "event_month": "FEB", "category": WHO_WE_HELP_OPTIONS[0],
        "what_we_do": [], "scope": [], "project_photos": [], "ai_content": {}, "logo_white": "", "logo_black": "", 
        "debug_logs": [], "mc_questions": [], "open_question_ans": "", "challenge": "", "solution": "", 
        "hero_photo_index": 0, "sync_success": False, "draft_project_id": "", "loaded_image_urls": [],
        "faq_en_edit": "", "faq_tc_edit": "", "faq_jp_edit": "", 
    }
    for k, v in fields.items():
        if k not in st.session_state: st.session_state[k] = v

def reset_for_new_case():
    init_session_state()
    for i in range(1, 16):
        if f"ans_{i}" in st.session_state: del st.session_state[f"ans_{i}"]
    st.session_state.active_tab = "Project Collector"

def apply_styles(is_dark):
    bg_color = "#1E2128" if is_dark else "#E0E5EC"
    text_color = "#E0E5EC" if is_dark else "#2D3436"
    shadow_dark = "#14161C" if is_dark else "#bec3c9"
    shadow_light = "#282C38" if is_dark else "#ffffff"
    st.markdown(f"""<style>
        .stApp {{ background-color: {bg_color} !important; color: {text_color} !important; }}
        .neu-card {{ background: {bg_color}; border-radius: 20px; box-shadow: 9px 9px 16px {shadow_dark}, -9px -9px 16px {shadow_light}; padding: 25px; margin-bottom: 20px; }}
        .stButton > button {{ border-radius: 14px !important; box-shadow: 6px 6px 12px {shadow_dark}, -6px -6px 12px {shadow_light} !important; }}
        div[data-testid="stElementContainer"]:has(#logo-anchor) + div button {{ background-image: url('https://raw.githubusercontent.com/dickson-crypto/Firebean-app/main/Firebeanlogo2026.png') !important; background-size: contain !important; background-repeat: no-repeat !important; min-height: 180px !important; width: 540px !important; background-color: transparent !important; border: none !important; box-shadow: none !important; }}
        .mc-question {{ font-weight: 700; color: #FF0000 !important; border-left: 4px solid #FF0000; padding-left: 10px; margin-top: 15px; }}
    </style>""", unsafe_allow_html=True)

def main():
    st.set_page_config(page_title="Firebean Brain Collector", layout="wide")
    init_session_state()
    is_dark = datetime.now().hour >= 20 or datetime.now().hour < 8
    apply_styles(is_dark)

    # --- Header & Logo ---
    c1, c2 = st.columns([1, 1])
    with c1:
        st.markdown('<span id="logo-anchor"></span>', unsafe_allow_html=True)
        if st.button("HOME", key="logo_btn"):
            reset_for_new_case()
            st.rerun()
    with c2:
        percent = int((sum([bool(st.session_state.client_name), bool(st.session_state.project_name), len(st.session_state.project_photos)>=4])/3)*100)
        st.write(f"### Progress: {percent}%")

    nav_cols = st.columns(4)
    tabs = ["Project Collector", "Review & Multi-Sync", "Load Project", "老細一鍵填充"]
    for i, t in enumerate(tabs[:3]):
        if nav_cols[i].button(t, use_container_width=True, type="primary" if st.session_state.active_tab == t else "secondary"):
            st.session_state.active_tab = t
            st.rerun()

    st.markdown("---")

    # --- TAB: Project Collector ---
    if st.session_state.active_tab == "Project Collector":
        st.markdown('<div class="neu-card">', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            ub = st.file_uploader("Black Logo (PNG)", type=['png'], key="ub")
            if ub: st.session_state.logo_black = base64.b64encode(ub.read()).decode()
        with col2:
            uw = st.file_uploader("White Logo (PNG)", type=['png'], key="uw")
            if uw: st.session_state.logo_white = base64.b64encode(uw.read()).decode()

        b1, b2, b3 = st.columns(3)
        st.session_state.client_name = b1.text_input("Client", st.session_state.client_name)
        st.session_state.project_name = b2.text_input("Project", st.session_state.project_name)
        st.session_state.venue = b3.text_input("Venue", st.session_state.venue)

        # --- CATEGORY / WHAT WE DO / SOW ---
        ca, cb, cc = st.columns(3)
        with ca:
            st.markdown("##### Who we help")
            st.session_state.category = st.radio("Category", WHO_WE_HELP_OPTIONS, index=WHO_WE_HELP_OPTIONS.index(st.session_state.category), label_visibility="collapsed")
        with cb:
            st.markdown("##### What we do")
            st.session_state.what_we_do = [o for o in WHAT_WE_DO_OPTIONS if st.checkbox(o, key=f"w_{o}", value=(o in st.session_state.what_we_do))]
        with cc:
            st.markdown("##### Scope of work")
            st.session_state.scope = [o for o in SOW_OPTIONS if st.checkbox(o, key=f"s_{o}", value=(o in st.session_state.scope))]
        st.markdown('</div>', unsafe_allow_html=True)

        # --- DIAGNOSTIC & PHOTOS ---
        cl, cr = st.columns([1.2, 1])
        with cl:
            st.markdown('<div class="neu-card">', unsafe_allow_html=True)
            if st.button("生成 15 題繁中診斷題目"):
                with st.spinner("AI Analysis..."):
                    res = call_gemini_sdk("生成 15 題專業 PR 診斷 MC 題目 JSON 格式。", image_files=st.session_state.project_photos, is_json=True)
                    if res: st.session_state.mc_questions = json.loads(res)
                    st.rerun()
            if st.session_state.mc_questions:
                for q in st.session_state.mc_questions:
                    st.markdown(f"<div class='mc-question'>Q{q['id']}. {q['question']}</div>", unsafe_allow_html=True)
                    st.session_state[f"ans_{q['id']}"] = st.multiselect("Select:", q['options'], key=f"sel_{q['id']}")
            st.session_state.open_question_ans = st.text_area("最核心的概念？", st.session_state.open_question_ans)
            st.markdown('</div>', unsafe_allow_html=True)

        with cr:
            st.markdown('<div class="neu-card">', unsafe_allow_html=True)
            f_up = st.file_uploader("Upload 4-8 Photos", accept_multiple_files=True)
            if f_up: st.session_state.project_photos = f_up
            if st.session_state.project_photos:
                st.session_state.hero_photo_index = st.radio("Select Hero Banner:", range(len(st.session_state.project_photos)), horizontal=True)
                g_cols = st.columns(4)
                for i, f in enumerate(st.session_state.project_photos):
                    with g_cols[i%4]: st.image(f, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

    # --- TAB: Review & Sync ---
    elif st.session_state.active_tab == "Review & Multi-Sync":
        st.markdown('<div class="neu-card">', unsafe_allow_html=True)
        if st.button("生成六大平台對接文案"):
            with st.spinner("Gemini Strategizing..."):
                res = call_gemini_sdk("撰寫雜誌文案與社群 Post JSON。", is_json=True)
                if res: st.session_state.ai_content = json.loads(res)
        
        if st.session_state.ai_content:
            st.json(st.session_state.ai_content)
            if st.button("Confirm & Sync (All Platforms)", type="primary", use_container_width=True):
                with st.spinner("Syncing to Master DB and Slide Creator..."):
                    pid, sdate = generate_system_metadata()
                    processed_imgs = []
                    for f in st.session_state.project_photos:
                        if hasattr(f, "seek"): f.seek(0)
                        img = Image.open(f).convert("RGB")
                        img.thumbnail((1600, 1600))
                        buf = io.BytesIO()
                        img.save(buf, format="JPEG", quality=85)
                        processed_imgs.append(base64.b64encode(buf.getvalue()).decode())

                    # Reorder for Hero Banner
                    hero = processed_imgs.pop(st.session_state.hero_photo_index)
                    processed_imgs.insert(0, hero)

                    payload = {
                        "action": "sync_project", "project_id": pid, "sort_date": sdate,
                        "client_name": st.session_state.client_name, "project_name": st.session_state.project_name,
                        "venue": st.session_state.venue, "date": f"{st.session_state.event_year} {st.session_state.event_month}",
                        "category": st.session_state.category, "scope": ", ".join(st.session_state.scope),
                        "images": processed_imgs, "logo_white": st.session_state.logo_white,
                    }
                    
                    # Target 1: Master DB
                    requests.post(SHEET_SCRIPT_URL, json=payload, timeout=60)
                    # Target 2: Slide Creator
                    payload["action"] = "create_slide"
                    payload["photos"] = processed_imgs
                    payload["logo_white_base64"] = st.session_state.logo_white
                    requests.post(SLIDE_SCRIPT_URL, json=payload, timeout=60)
                    
                    st.success("Synced Successfully!")
        st.markdown('</div>', unsafe_allow_html=True)

if __name__ == "__main__": main()
