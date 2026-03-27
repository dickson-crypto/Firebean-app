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
STABLE_MODEL_ID = "gemini-2.0-flash"

WHO_WE_HELP_OPTIONS = ["GOVERNMENT & PUBLIC SECTOR", "LIFESTYLE & CONSUMER", "F&B & HOSPITALITY", "MALLS & VENUES"]
WHAT_WE_DO_OPTIONS = ["ROVING EXHIBITIONS", "SOCIAL & CONTENT", "INTERACTIVE & TECH", "PR & MEDIA", "EVENTS & CEREMONIES"]
SOW_OPTIONS = ["Event Planning", "Event Coordination", "Event Production", "Theme Design", "Concept Development", "Social Media Management", "KOL / MI Line up", "Artist Endorsement", "Media Pitching", "PR Consulting", "Souvenir Sourcing"]

CURRENT_YEAR = datetime.now().year
YEAR_OPTIONS = [str(y) for y in range(CURRENT_YEAR, 2011, -1)]
MONTH_OPTIONS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]

# --- 🛡️ FAQ 扁平化清洗函數 (解決換行與格式崩潰問題) ---
def safe_flatten_faq(faq_input):
    """安全解析文字框內容，並將其壓縮成沒有換行符號的單行字串 (Flat String)"""
    if not faq_input:
        return "[]"
    
    # 如果已經是 list 或 dict，直接轉成無換行的 JSON 字串
    if isinstance(faq_input, (list, dict)):
        return json.dumps(faq_input, ensure_ascii=False)
        
    # 如果是字串，嘗試解析後再壓縮，若失敗則暴力移除換行符號
    if isinstance(faq_input, str):
        faq_input = faq_input.strip()
        if not faq_input:
            return "[]"
        try:
            parsed = json.loads(faq_input)
            return json.dumps(parsed, ensure_ascii=False)
        except Exception as e:
            # 解析失敗的備用方案：直接取代所有換行符號與單引號，確保它是安全的單行字串
            return faq_input.replace("\n", " ").replace("\r", " ").replace("'", "\\'").strip()
    
    return "[]"

# --- 系統日誌函數 ---
def log_debug(msg, type="info"):
    if "debug_logs" not in st.session_state: st.session_state.debug_logs = []
    timestamp = datetime.now().strftime("%H:%M:%S")
    st.session_state.debug_logs.append({"time": timestamp, "msg": msg, "type": type})

# --- 系統自動生成邏輯 (ID 與 日期) ---
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

**ABSOLUTE RULE 1 — POST-EVENT RETROSPECTIVE MODE**:
This tool is EXCLUSIVELY used AFTER an event has already taken place. All content you generate MUST be written as a retrospective case showcase.

**ABSOLUTE RULE 2 — INTERNAL TERMINOLOGY PROHIBITION**:
NEVER use the phrase "Firebean Brain" or similar internal terminology in output. Use "Our strategic approach" or "Our team's expertise".

**CRITICAL HTML STRUCTURE REQUIREMENT FOR '6_website'**:
Use ONLY <h1>, <h3>, and <p> tags. DO NOT include FAQ section inside '6_website'.

**CRITICAL INSTRUCTION FOR '7_faq' (Dedicated FAQ)**:
The '7_faq' key MUST follow this structure exactly: [{"Q1": "[Question]", "A1": "[Answer]"}, {"Q2": "[Question]", "A2": "[Answer]"}]
"""

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

            response = model.generate_content(contents, generation_config={
                "response_mime_type": "application/json" if is_json else "text/plain",
                "temperature": 0.2
            })

            if response and response.text:
                text = response.text.strip()
                if not is_json: return text
                match = re.search(r'(\{.*\})|(\[.*\])', text, re.DOTALL)
                json_str = match.group(0) if match else text
                json.loads(json_str)
                return json_str

        except Exception as e:
            log_debug(f"API Attempt {attempt+1} fail: {str(e)}", "error")
            if attempt < max_retries - 1: time.sleep(1)
            else: break
    return None

def init_session_state():
    fields = {
        "active_tab": "Project Collector",
        "client_name": "", "project_name": "", "venue": "", "youtube": "",
        "event_year": str(CURRENT_YEAR), "event_month": "FEB",
        "category": WHO_WE_HELP_OPTIONS[0], "what_we_do": [], "scope": [],
        "project_photos": [], "ai_content": {}, "logo_white": "", "logo_black": "", 
        "debug_logs": [], "mc_questions": [], "open_question_ans": "", 
        "challenge": "", "solution": "", "visual_facts": "",
        "hero_photo_index": 0, "sync_success": False, "draft_project_id": "", "loaded_image_urls": [],
        "faq_en_edit": "", "faq_tc_edit": "", "faq_jp_edit": ""
    }
    for k, v in fields.items():
        if k not in st.session_state: st.session_state[k] = v

def reset_for_new_case():
    for k in list(st.session_state.keys()):
        if k not in ["debug_logs"]: del st.session_state[k]
    init_session_state()
    st.rerun()

def create_dummy_image(color, label):
    img = Image.new('RGB', (800, 600), color=color)
    d = ImageDraw.Draw(img)
    d.text((40, 40), label, fill=(255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    buf.seek(0)
    return buf

def fill_dummy_data():
    st.session_state.client_name = "Firebean HQ"
    st.session_state.project_name = f"{CURRENT_YEAR} 旗艦同步測試" 
    st.session_state.venue = "香港會議展覽中心"
    st.session_state.open_question_ans = "將 15 個通用診斷問題轉化為一套連貫、引人入勝且可操作的跨平台策略。"
    colors = ["#FF5733", "#33FF57", "#3357FF", "#F333FF", "#33FFF3", "#F3FF33", "#999999", "#222222"]
    st.session_state.project_photos = [create_dummy_image(c, f"P{i+1}") for i, c in enumerate(colors)]
    st.session_state.mc_questions = [{"id": i+1, "question": f"診斷指標 {i+1}？", "options": ["優化", "維持"]} for i in range(15)]
    for i in range(1, 16): st.session_state[f"ans_{i}"] = ["優化"]
    dummy_logo = base64.b64encode(create_dummy_image("#000000", "LOGO").getvalue()).decode()
    st.session_state.logo_black = dummy_logo
    st.session_state.logo_white = dummy_logo
    log_debug("🚀 高質量測試數據填充完成。", "success")

# --- UI Styles ---
def apply_styles():
    st.markdown("""<style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;900&display=swap');
        header {visibility: hidden;} footer {visibility: hidden;}
        .stApp { background-color: #1E2128 !important; color: #E0E5EC !important; font-family: 'Inter', sans-serif; }
        .neu-card { background: #1E2128; border-radius: 20px; box-shadow: 9px 9px 16px #14161C, -9px -9px 16px #282C38; padding: 25px; margin-bottom: 20px; }
        button[kind="primary"] { background-color: #FF2A2A !important; color: white !important; border-radius: 12px !important; box-shadow: 0px 4px 15px rgba(255, 0, 0, 0.35) !important; }
        .debug-terminal { background: #0D0F14 !important; color: #00FF88 !important; padding: 15px; font-size: 11px; border-radius: 10px; height: 200px; overflow-y: scroll; }
    </style>""", unsafe_allow_html=True)

def main():
    st.set_page_config(page_title="Firebean Brain Collector", layout="wide")
    init_session_state()
    apply_styles()

    # --- Header ---
    c1, c2 = st.columns([1, 1])
    with c1: 
        st.markdown('<span id="logo-anchor"></span>', unsafe_allow_html=True)
        if st.button("🏠 HOME"):
            if st.session_state.get("sync_success", False): reset_for_new_case()
            else: st.session_state.active_tab = "Project Collector"; st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)
    nav_cols = st.columns(3)
    if nav_cols[0].button("Project Collector", use_container_width=True, type="primary" if st.session_state.active_tab == "Project Collector" else "secondary"):
        st.session_state.active_tab = "Project Collector"; st.rerun()
    if nav_cols[1].button("Review & Multi-Sync", use_container_width=True, type="primary" if st.session_state.active_tab == "Review & Multi-Sync" else "secondary"):
        st.session_state.active_tab = "Review & Multi-Sync"; st.rerun()
    if nav_cols[2].button("老細一鍵填充 (深度測試)", use_container_width=True):
        fill_dummy_data(); st.rerun()

    # --- TAB: Collector ---
    if st.session_state.active_tab == "Project Collector":
        st.markdown('<div class="neu-card">', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            ub = st.file_uploader("Black Logo (Required)", type=['png'], key="l_b")
            if ub: st.session_state.logo_black = base64.b64encode(ub.read()).decode()
        with col2:
            uw = st.file_uploader("White Logo (Required)", type=['png'], key="l_w")
            if uw: st.session_state.logo_white = base64.b64encode(uw.read()).decode()

        b1, b2, b3 = st.columns(3)
        st.session_state.client_name = b1.text_input("Client", st.session_state.client_name)
        st.session_state.project_name = b2.text_input("Project", st.session_state.project_name)
        st.session_state.venue = b3.text_input("Venue", st.session_state.venue)
        
        ca, cb, cc = st.columns(3)
        with ca: st.session_state.category = st.radio("Category", WHO_WE_HELP_OPTIONS)
        with cb: st.session_state.what_we_do = [o for o in WHAT_WE_DO_OPTIONS if st.checkbox(o, key=f"w_{o}", value=(o in st.session_state.what_we_do))]
        with cc: st.session_state.scope = [o for o in SOW_OPTIONS if st.checkbox(o, key=f"s_{o}", value=(o in st.session_state.scope))]
        st.markdown('</div>', unsafe_allow_html=True)

        cl, cr = st.columns([1.2, 1])
        with cl:
            st.markdown('<div class="neu-card">', unsafe_allow_html=True)
            if st.button("生成 15 題診斷題目"):
                if not st.session_state.project_photos: st.error("請先上傳相片。")
                else:
                    with st.spinner("AI 分析中..."):
                        mc_prompt = f"基於客戶 {st.session_state.client_name} 生成 15 題 PR 診斷 MC。輸出 JSON 陣列格式：[{{'id':1,'question':'...','options':['A','B']}}]"
                        res = call_gemini_sdk(mc_prompt, is_json=True, image_files=st.session_state.project_photos)
                        if res: st.session_state.mc_questions = json.loads(res); st.rerun()

            if st.session_state.mc_questions:
                for q in st.session_state.mc_questions:
                    st.write(f"Q{q['id']}. {q['question']}")
                    st.session_state[f"ans_{q['id']}"] = st.multiselect("選擇結果", q['options'], key=f"sel_{q['id']}")
                st.session_state.open_question_ans = st.text_area("最核心的概念？", st.session_state.open_question_ans)
            st.markdown('</div>', unsafe_allow_html=True)

        with cr:
            st.markdown('<div class="neu-card">', unsafe_allow_html=True)
            f_up = st.file_uploader("Upload 4-8 Photos", accept_multiple_files=True)
            if f_up: st.session_state.project_photos = f_up
            if st.session_state.project_photos:
                st.session_state.hero_photo_index = st.radio("選擇 Hero Banner", range(len(st.session_state.project_photos)), horizontal=True)
                cols = st.columns(4)
                for i, f in enumerate(st.session_state.project_photos):
                    with cols[i%4]: st.image(f, width=100)
            st.markdown('</div>', unsafe_allow_html=True)

        if st.button("準備就緒，前往 Review 👉", type="primary", use_container_width=True):
            st.session_state.active_tab = "Review & Multi-Sync"; st.rerun()

    # --- TAB: Review ---
    elif st.session_state.active_tab == "Review & Multi-Sync":
        st.markdown('<div class="neu-card">', unsafe_allow_html=True)
        if st.button("生成六大平台文案"):
            with st.spinner("AI 撰寫中..."):
                prompt = f"分析專案: {st.session_state.project_name}。生成 JSON。包含 6_website 與 7_faq。FAQ 必須是 Array of Objects。"
                res = call_gemini_sdk(prompt, is_json=True)
                if res:
                    data = json.loads(res)
                    st.session_state.ai_content = data
                    faq = data.get("7_faq", {})
                    st.session_state.faq_en_edit = json.dumps(faq.get("en", []), ensure_ascii=False, indent=2)
                    st.session_state.faq_tc_edit = json.dumps(faq.get("tc", []), ensure_ascii=False, indent=2)
                    st.session_state.faq_jp_edit = json.dumps(faq.get("jp", []), ensure_ascii=False, indent=2)
                    st.rerun()

        if st.session_state.ai_content:
            st.json(st.session_state.ai_content)
            st.markdown("### 💬 Edit Dedicated FAQ")
            t1, t2, t3 = st.tabs(["EN", "TC", "JP"])
            with t1: st.text_area("FAQ EN", height=200, key="faq_en_edit")
            with t2: st.text_area("FAQ TC", height=200, key="faq_tc_edit")
            with t3: st.text_area("FAQ JP", height=200, key="faq_jp_edit")

            if st.button("Confirm & Sync (Sheet + Slide + Drive)", type="primary", use_container_width=True):
                with st.spinner("同步中..."):
                    try:
                        project_id, sort_date = generate_system_metadata()
                        processed_imgs = []
                        for f in st.session_state.project_photos:
                            if hasattr(f, "seek"): f.seek(0)
                            img = Image.open(f).convert("RGB")
                            img = ImageOps.exif_transpose(img)
                            img.thumbnail((1600, 1600))
                            buf = io.BytesIO(); img.save(buf, format="JPEG", quality=85)
                            processed_imgs.append(base64.b64encode(buf.getvalue()).decode())

                        # --- 核心修復：強制扁平化與 Debug ---
                        payload_sheet = {
                            "action": "sync_project",
                            "project_id": project_id,
                            "sort_date": sort_date,
                            "client_name": st.session_state.client_name,
                            "project_name": st.session_state.project_name,
                            "venue": st.session_state.venue,
                            "date": f"{st.session_state.event_year} {st.session_state.event_month}",
                            "category": st.session_state.category,
                            "category_what": ", ".join(st.session_state.what_we_do),
                            "scope": ", ".join(st.session_state.scope),
                            "challenge": st.session_state.ai_content.get("challenge_summary", ""),
                            "solution": st.session_state.ai_content.get("solution_summary", ""),
                            "logo_white": st.session_state.logo_white,
                            "logo_black": st.session_state.logo_black,
                            "images": processed_imgs,
                            "ai_content": st.session_state.ai_content,
                            "faq_en": safe_flatten_faq(st.session_state.faq_en_edit),
                            "faq_tc": safe_flatten_faq(st.session_state.faq_tc_edit),
                            "faq_jp": safe_flatten_faq(st.session_state.faq_jp_edit)
                        }

                        # 向 Logs 面板發送 Debug 證據
                        print(f"DEBUG_FAQ_EN: {payload_sheet['faq_en']}")
                        print(f"DEBUG_FAQ_TC: {payload_sheet['faq_tc']}")

                        r1 = requests.post(SHEET_SCRIPT_URL, json=payload_sheet, timeout=60)
                        
                        payload_slide = payload_sheet.copy()
                        payload_slide["action"] = "create_slide"
                        payload_slide["logo_white_base64"] = st.session_state.logo_white
                        r2 = requests.post(SLIDE_SCRIPT_URL, json=payload_slide, timeout=60)

                        st.balloons(); st.success(f"同步成功！編號: {project_id}")
                        st.session_state.sync_success = True
                    except Exception as e: st.error(f"同步失敗: {e}")
        st.markdown('</div>', unsafe_allow_html=True)

if __name__ == "__main__": main()
