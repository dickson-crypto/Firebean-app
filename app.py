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

# --- 🛡️ FAQ 扁平化清洗函數 (確保 Google Sheet 不會因換行符號錯位) ---
def safe_flatten_faq(faq_input):
    """將文字框內容壓縮成沒有換行符號的單行字串 (Flat String)"""
    if not faq_input:
        return "[]"
    try:
        if isinstance(faq_input, str):
            clean_input = faq_input.strip()
            if not clean_input: return "[]"
            # 嘗試解析 JSON 並重新打包成單行
            data = json.loads(clean_input)
            return json.dumps(data, ensure_ascii=False)
        return json.dumps(faq_input, ensure_ascii=False)
    except:
        # 解析失敗則暴力移除所有換行與單引號
        return str(faq_input).replace("\n", " ").replace("\r", " ").replace("'", "\\'").strip()

# --- 系統日誌函數 ---
def log_debug(msg, type="info"):
    if "debug_logs" not in st.session_state: st.session_state.debug_logs = []
    timestamp = datetime.now().strftime("%H:%M:%S")
    st.session_state.debug_logs.append({"time": timestamp, "msg": msg, "type": type})

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

# --- AI 指令集 ---
FIREBEAN_SYSTEM_PROMPT = """
You are a Lead PR Strategist. Always return a valid JSON object with keys: 
challenge_summary, solution_summary, 1_google_slide, 2_facebook_post, 3_threads_post, 4_instagram_post, 5_linkedin_post, 6_website, 7_faq.

**ABSOLUTE RULES**:
1. POST-EVENT Retrospective tone only.
2. NO internal terminology like "Firebean Brain".
3. '6_website' must be a nested JSON with keys 'angle_chosen', 'en', 'tc', 'jp'. Use ONLY <h1>, <h3>, <p>.
4. '7_faq' must be a nested JSON with keys 'en', 'tc', 'jp'. Each MUST be a JSON array of objects: [{"Q1":"...","A1":"..."}].
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
                    img = ImageOps.exif_transpose(Image.open(f))
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
            log_debug(f"Gemini API Error: {str(e)}", "error")
            time.sleep(1)
    return None

def init_session_state():
    fields = {
        "active_tab": "Project Collector", "client_name": "", "project_name": "", "venue": "", "youtube": "",
        "event_year": str(CURRENT_YEAR), "event_month": "FEB", "category": WHO_WE_HELP_OPTIONS[0], "what_we_do": [], "scope": [],
        "project_photos": [], "ai_content": {}, "logo_white": "", "logo_black": "", "debug_logs": [], "mc_questions": [], 
        "open_question_ans": "", "challenge": "", "solution": "", "hero_photo_index": 0, "sync_success": False,
        "faq_en_edit": "", "faq_tc_edit": "", "faq_jp_edit": "" # 關鍵：編輯專用變數
    }
    for k, v in fields.items():
        if k not in st.session_state: st.session_state[k] = v

def reset_for_new_case():
    for k in list(st.session_state.keys()):
        if k != "debug_logs": del st.session_state[k]
    init_session_state()
    st.rerun()

def fill_dummy_data():
    st.session_state.client_name = "Firebean HQ"
    st.session_state.project_name = f"{CURRENT_YEAR} 旗艦同步測試" 
    st.session_state.venue = "香港會議展覽中心"
    st.session_state.open_question_ans = "將 15 個指標轉化為跨平台策略。"
    colors = ["#FF5733", "#33FF57", "#3357FF", "#F333FF", "#33FFF3", "#F3FF33", "#999999", "#222222"]
    st.session_state.project_photos = [create_dummy_image(c, f"P{i+1}") for i, c in enumerate(colors)]
    st.session_state.mc_questions = [{"id": i+1, "question": f"指標 {i+1}？", "options": ["優化", "維持"]} for i in range(15)]
    for i in range(1, 16): st.session_state[f"ans_{i}"] = ["優化"]
    log_debug("🚀 高質量測試數據填充完成。", "success")

def create_dummy_image(color, label):
    img = Image.new('RGB', (800, 600), color=color)
    d = ImageDraw.Draw(img)
    d.text((40, 40), label, fill=(255, 255, 255))
    buf = io.BytesIO(); img.save(buf, format="JPEG"); buf.seek(0)
    return buf

# --- UI 介面實作 ---
def main():
    st.set_page_config(page_title="Firebean Brain Collector", layout="wide")
    init_session_state()
    
    st.markdown("""<style>
        .stApp { background-color: #1E2128 !important; color: #E0E5EC !important; }
        .neu-card { background: #1E2128; border-radius: 20px; box-shadow: 9px 9px 16px #14161C, -9px -9px 16px #282C38; padding: 25px; margin-bottom: 20px; }
        button[kind="primary"] { background-color: #FF2A2A !important; color: white !important; border-radius: 12px !important; }
    </style>""", unsafe_allow_html=True)

    c1, c2 = st.columns([1, 1])
    with c1: 
        if st.button("🏠 HOME"):
            if st.session_state.get("sync_success", False): reset_for_new_case()
            else: st.session_state.active_tab = "Project Collector"; st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)
    nav_cols = st.columns(3)
    if nav_cols[0].button("Project Collector", use_container_width=True): st.session_state.active_tab = "Project Collector"; st.rerun()
    if nav_cols[1].button("Review & Multi-Sync", use_container_width=True): st.session_state.active_tab = "Review & Multi-Sync"; st.rerun()
    if nav_cols[2].button("老細一鍵填充", use_container_width=True): fill_dummy_data(); st.rerun()

    # --- TAB 1: Collector ---
    if st.session_state.active_tab == "Project Collector":
        st.markdown('<div class="neu-card">', unsafe_allow_html=True)
        b1, b2, b3 = st.columns(3)
        st.session_state.client_name = b1.text_input("Client", st.session_state.client_name)
        st.session_state.project_name = b2.text_input("Project", st.session_state.project_name)
        st.session_state.venue = b3.text_input("Venue", st.session_state.venue)
        
        up = st.file_uploader("Upload Photos", accept_multiple_files=True)
        if up: st.session_state.project_photos = up
        
        if st.button("生成診斷題目"):
            with st.spinner("AI 分析中..."):
                res = call_gemini_sdk(f"基於客戶 {st.session_state.client_name} 生成 15 題 PR 診斷 JSON 陣列。", is_json=True, image_files=st.session_state.project_photos)
                if res: st.session_state.mc_questions = json.loads(res); st.rerun()
        
        if st.session_state.mc_questions:
            for q in st.session_state.mc_questions:
                st.session_state[f"ans_{q['id']}"] = st.multiselect(q['question'], q['options'], key=f"sel_{q['id']}")
            st.session_state.open_question_ans = st.text_area("核心概念", st.session_state.open_question_ans)
        
        if st.button("下一步：Review 👉", type="primary", use_container_width=True):
            st.session_state.active_tab = "Review & Multi-Sync"; st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    # --- TAB 2: Review & Sync ---
    elif st.session_state.active_tab == "Review & Multi-Sync":
        st.markdown('<div class="neu-card">', unsafe_allow_html=True)
        if st.button("生成六大平台對接文案"):
            with st.spinner("AI 撰寫中..."):
                prompt = f"分析專案: {st.session_state.project_name}. 生成包含 6_website 與 7_faq (Array) 的 JSON."
                res = call_gemini_sdk(prompt, is_json=True)
                if res:
                    data = json.loads(res)
                    if isinstance(data, list): data = data[0]
                    st.session_state.ai_content = data
                    # 重要：直接更新 Session State 裡的編輯變數
                    faq = data.get("7_faq", {})
                    st.session_state["faq_en_edit"] = json.dumps(faq.get("en", []), ensure_ascii=False, indent=2)
                    st.session_state["faq_tc_edit"] = json.dumps(faq.get("tc", []), ensure_ascii=False, indent=2)
                    st.session_state["faq_jp_edit"] = json.dumps(faq.get("jp", []), ensure_ascii=False, indent=2)
                    st.rerun()

        if st.session_state.ai_content:
            st.json(st.session_state.ai_content)
            st.markdown("### 💬 編輯 FAQ (AB/AC/AD 欄位)")
            t1, t2, t3 = st.tabs(["EN", "TC", "JP"])
            with t1: st.text_area("編輯 FAQ EN", height=200, key="faq_en_edit")
            with t2: st.text_area("編輯 FAQ TC", height=200, key="faq_tc_edit")
            with t3: st.text_area("編輯 FAQ JP", height=200, key="faq_jp_edit")

            if st.button("Confirm & Sync (Sheet + Slide + Drive)", type="primary", use_container_width=True):
                with st.spinner("🚀 全速同步中..."):
                    try:
                        pid, sdate = generate_system_metadata()
                        processed_imgs = []
                        for f in st.session_state.project_photos:
                            if hasattr(f, "seek"): f.seek(0)
                            img = ImageOps.exif_transpose(Image.open(f).convert("RGB"))
                            img.thumbnail((1200, 1200))
                            buf = io.BytesIO(); img.save(buf, format="JPEG", quality=85)
                            processed_imgs.append(base64.b64encode(buf.getvalue()).decode())

                        # 發送給 Google Sheet
                        payload_sheet = {
                            "action": "sync_project",
                            "project_id": pid,
                            "sort_date": sdate,
                            "client_name": st.session_state.client_name,
                            "project_name": st.session_state.project_name,
                            "venue": st.session_state.venue,
                            "date": f"{st.session_state.event_year} {st.session_state.event_month}",
                            "images": processed_imgs,
                            "ai_content": st.session_state.ai_content,
                            # 🛡️ 核心修復：使用 safe_flatten_faq 讀取編輯框內容
                            "faq_en": safe_flatten_faq(st.session_state["faq_en_edit"]),
                            "faq_tc": safe_flatten_faq(st.session_state["faq_tc_edit"]),
                            "faq_jp": safe_flatten_faq(st.session_state["faq_jp_edit"])
                        }
                        
                        # Debug 輸出
                        print(f"DEBUG_SYNC_FAQ_EN: {payload_sheet['faq_en']}")
                        
                        r1 = requests.post(SHEET_SCRIPT_URL, json=payload_sheet, timeout=60)
                        
                        # 發送給 Google Slide (對接 True = 置中裁切)
                        payload_slide = payload_sheet.copy()
                        payload_slide["action"] = "create_slide"
                        requests.post(SLIDE_SCRIPT_URL, json=payload_slide, timeout=60)

                        st.balloons(); st.success(f"全部同步成功！編號: {pid}")
                        st.session_state.sync_success = True
                    except Exception as e: st.error(f"同步失敗: {e}")
        st.markdown('</div>', unsafe_allow_html=True)

if __name__ == "__main__": main()
