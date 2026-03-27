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

# --- 1. 核心配置 ---
SHEET_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbzaQu2KpJ06I0yWL4dEwk0naB1FOlHkt7Ta340xH84IDwQI7jQNUI3eSmxrwKyQHNj5/exec"
SLIDE_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbyZvtm8M8a5sLYF3vz9kLyAdimzzwpSlnTkzIeQ3DJxkklNYNlwSoJc5j5CkorM6w5V/exec"
STABLE_MODEL_ID = "gemini-2.5-flash"

WHO_WE_HELP_OPTIONS = ["GOVERNMENT & PUBLIC SECTOR", "LIFESTYLE & CONSUMER", "F&B & HOSPITALITY", "MALLS & VENUES"]
WHAT_WE_DO_OPTIONS = ["ROVING EXHIBITIONS", "SOCIAL & CONTENT", "INTERACTIVE & TECH", "PR & MEDIA", "EVENTS & CEREMONIES"]
SOW_OPTIONS = ["Event Planning", "Event Coordination", "Event Production", "Theme Design", "Concept Development", "Social Media Management", "KOL / MI Line up", "Artist Endorsement", "Media Pitching", "PR Consulting", "Souvenir Sourcing"]

CURRENT_YEAR = datetime.now().year
YEAR_OPTIONS = [str(y) for y in range(CURRENT_YEAR, 2011, -1)]
MONTH_OPTIONS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]

# --- 🛡️ FAQ 扁平化清洗函數 ---
def safe_flatten_faq(faq_input):
    """將文字框內容壓縮成沒有換行符號的單行 JSON 字串，防止 Google Sheet 錯位"""
    if not faq_input:
        return "[]"
    if isinstance(faq_input, (list, dict)):
        return json.dumps(faq_input, ensure_ascii=False)
    if isinstance(faq_input, str):
        faq_input = faq_input.strip()
        if not faq_input: return "[]"
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
You are a Lead PR Strategist and Chief Editor for a premium B2B/B2C communications agency.
Task: Transform diagnostic data into a professional PR strategy JSON.
Always return a valid JSON object with keys: challenge_summary, solution_summary, 1_google_slide, 2_facebook_post, 3_threads_post, 4_instagram_post, 5_linkedin_post, 6_website, 7_faq.

**CRITICAL INSTRUCTION FOR '7_faq'**:
The '7_faq' key MUST be a nested JSON object containing exactly three keys: "en", "tc", and "jp".
Format: [{"Q1": "[Question]", "A1": "[Answer]"}, {"Q2": "[Question]", "A2": "[Answer]"}]
"""

# --- 2. 核心邏輯 ---
def log_debug(msg, type="info"):
    if "debug_logs" not in st.session_state: st.session_state.debug_logs = []
    timestamp = datetime.now().strftime("%H:%M:%S")
    st.session_state.debug_logs.append({"time": timestamp, "msg": msg, "type": type})

def call_gemini_sdk(prompt, image_files=None, is_json=False, max_retries=2):
    secret_key = st.secrets.get("GEMINI_API_KEY", "")
    if not secret_key:
        st.error("🚨 找不到 API Key")
        return None
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
                json.loads(json_str)
                return json_str
        except Exception as e:
            log_debug(f"❌ API 錯誤: {str(e)}", "error")
    return None

def init_session_state():
    fields = {
        "active_tab": "Project Collector", "client_name": "", "project_name": "", "venue": "", "youtube": "",
        "event_year": str(CURRENT_YEAR), "event_month": "FEB", "category": WHO_WE_HELP_OPTIONS[0], "what_we_do": [], "scope": [],
        "project_photos": [], "ai_content": {}, "logo_white": "", "logo_black": "", "debug_logs": [], "mc_questions": [], 
        "open_question_ans": "", "challenge": "", "solution": "", "hero_photo_index": 0, "sync_success": False, 
        "draft_project_id": "", "loaded_image_urls": [], "faq_en_edit": "", "faq_tc_edit": "", "faq_jp_edit": "", 
    }
    for k, v in fields.items():
        if k not in st.session_state: st.session_state[k] = v

def reset_for_new_case():
    init_session_state()
    st.session_state.active_tab = "Project Collector"
    log_debug("🔄 已重置案例。", "success")

# --- 3. UI 樣式 ---
def get_is_dark_mode():
    from datetime import timezone, timedelta
    hk_hour = datetime.now(timezone(timedelta(hours=8))).hour
    return hk_hour >= 20 or hk_hour < 8

def apply_styles(is_dark):
    bg = "#1E2128" if is_dark else "#E0E5EC"
    txt = "#E0E5EC" if is_dark else "#2D3436"
    st.markdown(f"""<style>
        .stApp {{ background-color: {bg} !important; color: {txt} !important; }}
        .neu-card {{ background: {bg}; border-radius: 20px; box-shadow: 9px 9px 16px rgba(0,0,0,0.2); padding: 25px; margin-bottom: 20px; }}
        button[kind="primary"] {{ background-color: #FF2A2A !important; color: white !important; border-radius: 12px !important; }}
    </style>""", unsafe_allow_html=True)

# --- 4. Main App ---
def main():
    st.set_page_config(page_title="Firebean Brain 2026", layout="wide")
    init_session_state()
    apply_styles(get_is_dark_mode())

    # 導航列
    nav = st.tabs(["Project Collector", "Review & Multi-Sync", "📂 Load Project"])
    
    # --- Tab 1: Project Collector ---
    with nav[0]:
        st.markdown('<div class="neu-card">', unsafe_allow_html=True)
        col1, col2, col3 = st.columns(3)
        st.session_state.client_name = col1.text_input("Client", st.session_state.client_name)
        st.session_state.project_name = col2.text_input("Project", st.session_state.project_name)
        st.session_state.venue = col3.text_input("Venue", st.session_state.venue)
        
        f_up = st.file_uploader("Upload Photos", accept_multiple_files=True)
        if f_up: st.session_state.project_photos = f_up
        st.session_state.open_question_ans = st.text_area("核心概念", st.session_state.open_question_ans)
        st.markdown('</div>', unsafe_allow_html=True)

    # --- Tab 2: Review & Multi-Sync (重點修復區) ---
    with nav[1]:
        if st.button("🧠 生成文案與 FAQ", type="primary"):
            with st.spinner("AI 策略師思考中..."):
                prompt = f"分析專案: {st.session_state.project_name}。生成 JSON。"
                res = call_gemini_sdk(prompt, is_json=True)
                if res:
                    data = json.loads(res)
                    st.session_state.ai_content = data
                    faq = data.get("7_faq", {})
                    # 🚀 抽取並格式化 FAQ 給 UI 顯示
                    st.session_state.faq_en_edit = json.dumps(faq.get("en", []), ensure_ascii=False, indent=2)
                    st.session_state.faq_tc_edit = json.dumps(faq.get("tc", []), ensure_ascii=False, indent=2)
                    st.session_state.faq_jp_edit = json.dumps(faq.get("jp", []), ensure_ascii=False, indent=2)
                    st.rerun()

        if st.session_state.ai_content:
            st.markdown("### 💬 編輯 FAQ 內容")
            f_tabs = st.tabs(["EN", "TC", "JP"])
            # 使用 key 直接綁定，不再使用 value 參數
            st.session_state.faq_en_edit = f_tabs[0].text_area("FAQ EN", height=200, key="faq_en_input", value=st.session_state.faq_en_edit)
            st.session_state.faq_tc_edit = f_tabs[1].text_area("FAQ TC", height=200, key="faq_tc_input", value=st.session_state.faq_tc_edit)
            st.session_state.faq_jp_edit = f_tabs[2].text_area("FAQ JP", height=200, key="faq_jp_input", value=st.session_state.faq_jp_edit)

            if st.button("🚀 Confirm & Sync to Google Sheet", use_container_width=True, type="primary"):
                pid, s_date = generate_system_metadata()
                payload = {
                    "action": "sync_project",
                    "project_id": pid,
                    "client_name": st.session_state.client_name,
                    "project_name": st.session_state.project_name,
                    # 🚀 同步前執行扁平化清洗
                    "faq_en": safe_flatten_faq(st.session_state.faq_en_edit),
                    "faq_tc": safe_flatten_faq(st.session_state.faq_tc_edit),
                    "faq_jp": safe_flatten_faq(st.session_state.faq_jp_edit),
                }
                r = requests.post(SHEET_SCRIPT_URL, json=payload, timeout=60)
                if r.status_code == 200:
                    st.success(f"✅ 同步成功！編號: {pid}")
                    st.balloons()

    # --- Tab 3: Load Project ---
    with nav[2]:
        st.info("此功能連接至 Google Sheet 資料庫載入草稿。")

if __name__ == "__main__": main()
