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

# 🚀 FIX: Added HEIC support for iPhone uploads identified in logs
try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
except ImportError:
    pass

# --- 1. 核心配置 (Updated with 2026 URLs) ---
SHEET_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbxy6JwJpmclJOBerKJO4EJ50oKyL86Ux1Qci2oHx1RQiw8ruL_Um6qVYsWydyEsLawQ/exec"
SLIDE_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbxKP-8Xrvy6hblPqTmtXn76rO3DFOeU6jYQtLw5QDfDP1-adNDk02bhoKihfvp_Xsvy/exec"
STABLE_MODEL_ID = "gemini-1.5-flash" # FIX: Use stable model to resolve 404 errors

WHO_WE_HELP_OPTIONS = ["GOVERNMENT & PUBLIC SECTOR", "LIFESTYLE & CONSUMER", "F&B & HOSPITALITY", "MALLS & VENUES"]
WHAT_WE_DO_OPTIONS = ["ROVING EXHIBITIONS", "SOCIAL & CONTENT", "INTERACTIVE & TECH", "PR & MEDIA", "EVENTS & CEREMONIES"]
SOW_OPTIONS = ["Event Planning", "Event Coordination", "Event Production", "Theme Design", "Concept Development", "Social Media Management", "KOL / MI Line up", "Artist Endorsement", "Media Pitching", "PR Consulting", "Souvenir Sourcing"]

CURRENT_YEAR = datetime.now().year
YEAR_OPTIONS = [str(y) for y in range(CURRENT_YEAR, 2011, -1)]
MONTH_OPTIONS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]

# --- 🛡️ FAQ 扁平化清洗函數 ---
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

# --- 系統自動生成邏輯 ---
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
Retrospective mode. Past tense. No internal terminology like 'Firebean Brain'.
"""

# --- 2. 核心邏輯 ---
def log_debug(msg, type="info"):
    if "debug_logs" not in st.session_state: st.session_state.debug_logs = []
    timestamp = datetime.now().strftime("%H:%M:%S")
    st.session_state.debug_logs.append({"time": timestamp, "msg": msg, "type": type})

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
            log_debug(f"AI Error: {str(e)}", "error")
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
    log_debug("🔄 App Reset.", "success")

def fill_dummy_data():
    # 🚀 FIX: Updated to correctly check checkboxes and populate text areas
    st.session_state.client_name = "Firebean HQ"
    st.session_state.project_name = f"{CURRENT_YEAR} 旗艦同步測試" 
    st.session_state.venue = "香港會議展覽中心"
    st.session_state.category = "LIFESTYLE & CONSUMER"
    st.session_state.what_we_do = ["INTERACTIVE & TECH", "PR & MEDIA"]
    st.session_state.scope = ["Theme Design", "Event Production", "Concept Development"]
    st.session_state.open_question_ans = "將 15 個通用診斷問題轉化為一套連貫、引人入勝且可操作的跨平台策略。"
    # Set MC Questions dummy check
    st.session_state.mc_questions = [{"id": i+1, "question": f"指標 {i+1}", "options": ["戰略優化", "維持"]} for i in range(15)]
    for i in range(1, 16):
        st.session_state[f"ans_{i}"] = ["戰略優化"]
    log_debug("🚀 Boss Fill Complete.", "success")

def apply_styles(is_dark):
    bg = "#1E2128" if is_dark else "#E0E5EC"
    txt = "#E0E5EC" if is_dark else "#2D3436"
    st.markdown(f"""<style>
        .stApp {{ background-color: {bg} !important; color: {txt} !important; font-family: 'Inter', sans-serif; }}
        .neu-card {{ background: {bg}; border-radius: 20px; box-shadow: 9px 9px 16px rgba(0,0,0,0.2), -9px -9px 16px rgba(255,255,255,0.05); padding: 25px; margin-bottom: 20px; }}
        div[data-testid="stElementContainer"]:has(#logo-anchor) + div button {{ background-image: url('https://raw.githubusercontent.com/dickson-crypto/Firebean-app/main/Firebeanlogo2026.png') !important; background-size: contain !important; background-repeat: no-repeat !important; min-height: 180px !important; width: 540px !important; background-color: transparent !important; border: none !important; box-shadow: none !important; cursor: pointer; }}
        .mc-question {{ font-weight: 700; color: #FF0000 !important; border-left: 4px solid #FF0000; padding-left: 10px; margin-top: 15px; }}
        .checkbox-group {{ padding-left: 20px; margin-bottom: 10px; }}
        .debug-terminal {{ background: #0D0F14 !important; color: #00FF88 !important; padding: 15px; border-radius: 10px; height: 300px; overflow-y: scroll; }}
    </style>""", unsafe_allow_html=True)

def main():
    st.set_page_config(page_title="Firebean Brain Collector", layout="wide")
    init_session_state()
    is_dark = datetime.now().hour >= 20 or datetime.now().hour < 8
    apply_styles(is_dark)

    # --- 🚀 LOGO HEADER (Removed separate Home Button) ---
    c1, c2 = st.columns([1, 1])
    with c1:
        st.markdown('<span id="logo-anchor"></span>', unsafe_allow_html=True)
        # Clicking the Logo resets the app
        if st.button("", key="logo_btn"):
            reset_for_new_case()
            st.rerun()
    with c2:
        percent = int((sum([bool(st.session_state.client_name), bool(st.session_state.project_name), len(st.session_state.project_photos)>=4])/3)*100)
        # 🚀 Use 2026 standard for progress display
        st.markdown(f"<div style='text-align: right; font-size: 30px; font-weight: 900;'>{percent}%</div>", unsafe_allow_html=True)

    nav_cols = st.columns(4)
    tabs = ["Project Collector", "Review & Multi-Sync", "Load Project", "老細一鍵填充 (深度內容測試)"]
    for i, t in enumerate(tabs[:3]):
        if nav_cols[i].button(t, use_container_width=True, type="primary" if st.session_state.active_tab == t else "secondary"):
            st.session_state.active_tab = t
            st.rerun()
    if nav_cols[3].button(tabs[3], use_container_width=True):
        fill_dummy_data()
        st.rerun()

    st.markdown("---")

    if st.session_state.active_tab == "Project Collector":
        st.markdown('<div class="neu-card">', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            ub = st.file_uploader("Black Logo", type=['png'], key="l_b")
            if ub: st.session_state.logo_black = base64.b64encode(ub.read()).decode()
        with col2:
            uw = st.file_uploader("White Logo", type=['png'], key="l_w")
            if uw: st.session_state.logo_white = base64.b64encode(uw.read()).decode()

        b1, b2, b3 = st.columns(3)
        st.session_state.client_name = b1.text_input("Client", st.session_state.client_name)
        st.session_state.project_name = b2.text_input("Project", st.session_state.project_name)
        st.session_state.venue = b3.text_input("Venue", st.session_state.venue)

        # --- RESTORED CHECKBOX LAYOUTS ---
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

        cl, cr = st.columns([1.2, 1])
        with cl:
            st.markdown('<div class="neu-card">', unsafe_allow_html=True)
            if st.button("生成 15 題繁中診斷題目"):
                with st.spinner("AI Strategist..."):
                    res = call_gemini_sdk("生成 15 題專業 PR 診斷選擇題 JSON。", image_files=st.session_state.project_photos, is_json=True)
                    if res: st.session_state.mc_questions = json.loads(res)
                    st.rerun()
            
            # 🚀 RESTORED: Bulleted Checkboxes for Diagnostic questions
            if st.session_state.mc_questions:
                for q in st.session_state.mc_questions:
                    st.markdown(f"<div class='mc-question'>Q{q['id']}. {q['question']}</div>", unsafe_allow_html=True)
                    st.markdown("<div class='checkbox-group'>", unsafe_allow_html=True)
                    ans_key = f"ans_{q['id']}"
                    current = st.session_state.get(ans_key, [])
                    new_ans = []
                    for opt in q['options']:
                        if st.checkbox(opt, value=(opt in current), key=f"chk_{q['id']}_{opt}"):
                            new_ans.append(opt)
                    st.session_state[ans_key] = new_ans
                    st.markdown("</div>", unsafe_allow_html=True)
            st.session_state.open_question_ans = st.text_area("最核心的概念？", st.session_state.open_question_ans)
            st.markdown('</div>', unsafe_allow_html=True)

        with cr:
            st.markdown('<div class="neu-card">', unsafe_allow_html=True)
            f_up = st.file_uploader("Upload 4-8 Photos", accept_multiple_files=True)
            if f_up: st.session_state.project_photos = f_up
            if st.session_state.project_photos:
                st.session_state.hero_photo_index = st.radio("Hero Banner:", range(len(st.session_state.project_photos)), horizontal=True)
                g_cols = st.columns(4)
                for i, f in enumerate(st.session_state.project_photos):
                    with g_cols[i%4]:
                        try:
                            if hasattr(f, "seek"): f.seek(0)
                            # 🚀 Updated width parameter for 2026 compatibility
                            st.image(f, width='stretch')
                        except: st.image(f, width='stretch')
            st.markdown('</div>', unsafe_allow_html=True)

    elif st.session_state.active_tab == "Review & Multi-Sync":
        st.markdown('<div class="neu-card">', unsafe_allow_html=True)
        if st.button("Confirm & Sync"):
            with st.spinner("🔄 Syncing (2026 High-Fidelity Fix enabled)..."):
                pid, sdate = generate_system_metadata()
                processed_imgs = []
                for f in st.session_state.project_photos:
                    if hasattr(f, "seek"): f.seek(0)
                    img = Image.open(f).convert("RGB")
                    buf = io.BytesIO()
                    img.save(buf, format="JPEG", quality=85)
                    processed_imgs.append(base64.b64encode(buf.getvalue()).decode())

                payload = {
                    "action": "sync_project", "project_id": pid, "sort_date": sdate,
                    "client_name": st.session_state.client_name, "project_name": st.session_state.project_name,
                    "venue": st.session_state.venue, "images": processed_imgs,
                    "logo_white": st.session_state.logo_white, "faq_en": safe_flatten_faq(st.session_state.faq_en_edit),
                }
                # Seq 1: Master DB
                requests.post(SHEET_SCRIPT_URL, json=payload, timeout=60)
                # Seq 2: Slide Creator
                payload["action"] = "create_slide"
                payload["photos"] = processed_imgs
                payload["logo_white_base64"] = st.session_state.logo_white
                requests.post(SLIDE_SCRIPT_URL, json=payload, timeout=60)
                st.balloons()
                st.success(f"Success: {pid}")

    with st.expander("🛠️ Debug Terminal", expanded=False):
        logs = "".join([f"<div>[{l['time']}] {l['msg']}</div>" for l in reversed(st.session_state.get("debug_logs", []))])
        st.markdown(f"<div class='debug-terminal'>{logs}</div>", unsafe_allow_html=True)

if __name__ == "__main__": main()
