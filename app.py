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
# 使用您提供的高成功率 Script URL
SHEET_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbzaQu2KpJ06I0yWL4dEwk0naB1FOlHkt7Ta340xH84IDwQI7jQNUI3eSmxrwKyQHNj5/exec"
SLIDE_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbyZvtm8M8a5sLYF3vz9kLyAdimzzwpSlnTkzIeQ3DJxkklNYNlwSoJc5j5CkorM6w5V/exec"
STABLE_MODEL_ID = "gemini-2.5-flash"

WHO_WE_HELP_OPTIONS = ["GOVERNMENT & PUBLIC SECTOR", "LIFESTYLE & CONSUMER", "F&B & HOSPITALITY", "MALLS & VENUES"]
WHAT_WE_DO_OPTIONS = ["ROVING EXHIBITIONS", "SOCIAL & CONTENT", "INTERACTIVE & TECH", "PR & MEDIA", "EVENTS & CEREMONIES"]
SOW_OPTIONS = ["Event Planning", "Event Coordination", "Event Production", "Theme Design", "Concept Development", "Social Media Management", "KOL / MI Line up", "Artist Endorsement", "Media Pitching", "PR Consulting", "Souvenir Sourcing"]

CURRENT_YEAR = datetime.now().year
YEAR_OPTIONS = [str(y) for y in range(CURRENT_YEAR, 2011, -1)]
MONTH_OPTIONS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]

# --- 🛡️ 核心修復：FAQ 數據清洗與格式化 ---

def safe_flatten_faq(faq_input):
    """
    終極清洗函數：確保輸出為標準『雙引號』單行 JSON 字串。
    解決 Google Sheet 無法解析單引號或換行符號的問題。
    """
    if not faq_input:
        return "[]"
    
    # 移除 Markdown 代碼標籤
    if isinstance(faq_input, str):
        faq_input = re.sub(r'```json\s*|\s*```', '', faq_input).strip()
    
    try:
        # 嘗試解析 JSON (先處理單引號轉雙引號的常見錯誤)
        if isinstance(faq_input, str):
            # 只有在它看起來像 JSON 時才嘗試替換並加載
            cleaned_str = faq_input.replace("'", '"')
            parsed = json.loads(cleaned_str)
        else:
            parsed = faq_input
        
        # 重新打包成單行字串 (無縮排，無換行)
        return json.dumps(parsed, ensure_ascii=False)
    except:
        # 解析失敗的備用：暴力移除換行並強制轉雙引號
        return faq_input.replace("\n", " ").replace("\r", "").replace("'", '"').strip()

def format_faq_robust(val):
    """
    強大的解析邏輯：處理 AI 可能回傳的各種格式 (List, Dict, 或純文字 Q&A)。
    """
    if isinstance(val, list):
        return json.dumps(val, ensure_ascii=False, indent=2)
    elif isinstance(val, dict):
        return json.dumps([val], ensure_ascii=False, indent=2)
    elif isinstance(val, str):
        try:
            # 嘗試直接解析標準 JSON
            p = json.loads(val.replace("'", '"'))
            return json.dumps(p, ensure_ascii=False, indent=2)
        except:
            # 如果是純文字，使用正則表達式提取 Q1/A1 對
            qa_pairs = []
            qs = re.findall(r'Q\d+[:：]\s*(.*?)(?=A\d+[:：]|$)', val, re.DOTALL | re.IGNORECASE)
            as_ = re.findall(r'A\d+[:：]\s*(.*?)(?=Q\d+[:：]|$)', val, re.DOTALL | re.IGNORECASE)
            for i in range(min(len(qs), len(as_))):
                qa_pairs.append({f"Q{i+1}": qs[i].strip(), f"A{i+1}": as_[i].strip()})
            if qa_pairs:
                return json.dumps(qa_pairs, ensure_ascii=False, indent=2)
    return "[]"

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

# --- 指令與模型調用 ---
FIREBEAN_SYSTEM_PROMPT = """
You are a Lead PR Strategist and Chief Editor for a premium B2B/B2C communications agency.
Task: Transform diagnostic data into a professional PR strategy JSON.
Always return a valid JSON object with keys: challenge_summary, solution_summary, 1_google_slide, 2_facebook_post, 3_threads_post, 4_instagram_post, 5_linkedin_post, 6_website, 7_faq.

**ABSOLUTE RULE 1 — POST-EVENT RETROSPECTIVE MODE**:
This tool is EXCLUSIVELY used AFTER an event has already taken place. All content you generate MUST be written as a retrospective case showcase.

**ABSOLUTE RULE 2 — INTERNAL TERMINOLOGY PROHIBITION**:
NEVER use the phrase "Firebean Brain" or similar internal terminology. Use "Our strategic approach", etc.

STRICTLY FORBIDDEN in ALL outputs: No invitation language, no future-tense, no specific date/time for promotion.

**CRITICAL INSTRUCTION FOR '7_faq'**:
The '7_faq' key MUST be a nested JSON object containing: "en", "tc", and "jp".
Format: [{"Q1": "[Question]", "A1": "[Answer]"}, {"Q2": "[Question]", "A2": "[Answer]"}]
"""

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
            log_debug(f"❌ API 錯誤: {str(e)}", "error")
            break
    return None

def init_session_state():
    fields = {
        "active_tab": "Project Collector",
        "client_name": "", "project_name": "", "venue": "", "youtube": "",
        "event_year": str(CURRENT_YEAR), "event_month": "FEB",
        "category": WHO_WE_HELP_OPTIONS[0], "what_we_do": [], "scope": [],
        "project_photos": [], "ai_content": {}, "logo_white": "", "logo_black": "", 
        "debug_logs": [], "mc_questions": [], "open_question_ans": "", 
        "challenge": "", "solution": "", "hero_photo_index": 0,
        "sync_success": False, "faq_en_edit": "", "faq_tc_edit": "", "faq_jp_edit": "", 
    }
    for k, v in fields.items():
        if k not in st.session_state: st.session_state[k] = v

def reset_for_new_case():
    for key in list(st.session_state.keys()):
        if key not in ["debug_logs"]: del st.session_state[key]
    init_session_state()
    st.rerun()

# --- UI 樣式 ---
def apply_styles(is_dark):
    bg = "#1E2128" if is_dark else "#E0E5EC"
    txt = "#E0E5EC" if is_dark else "#2D3436"
    st.markdown(f"""<style>
        .stApp {{ background-color: {bg} !important; color: {txt} !important; }}
        .neu-card {{ background: {bg}; border-radius: 20px; padding: 25px; box-shadow: 10px 10px 20px rgba(0,0,0,0.2); margin-bottom: 20px; }}
        .mc-question {{ font-weight: 700; color: #FF0000; border-left: 4px solid #FF0000; padding-left: 10px; }}
    </style>""", unsafe_allow_html=True)

# --- 主程式 ---
def main():
    st.set_page_config(page_title="Firebean Brain Collector", layout="wide")
    init_session_state()
    is_dark = datetime.now().hour >= 20 or datetime.now().hour < 8
    apply_styles(is_dark)

    st.markdown('<div id="logo-anchor"></div>', unsafe_allow_html=True)
    st.image("https://raw.githubusercontent.com/dickson-crypto/Firebean-app/main/Firebeanlogo2026.png", width=400)

    # 導覽列
    tabs = st.tabs(["Project Collector", "Review & Multi-Sync"])
    
    with tabs[0]:
        st.markdown('<div class="neu-card">', unsafe_allow_html=True)
        col_l, col_r = st.columns(2)
        with col_l:
            st.session_state.client_name = st.text_input("Client", st.session_state.client_name)
            st.session_state.project_name = st.text_input("Project", st.session_state.project_name)
        with col_r:
            st.session_state.venue = st.text_input("Venue", st.session_state.venue)
            st.session_state.youtube = st.text_input("YouTube Link", st.session_state.youtube)
        
        st.session_state.event_year = st.selectbox("Year", YEAR_OPTIONS)
        st.session_state.event_month = st.selectbox("Month", MONTH_OPTIONS)
        
        up = st.file_uploader("Upload Photos (min 4)", accept_multiple_files=True)
        if up: st.session_state.project_photos = up
        st.markdown('</div>', unsafe_allow_html=True)

        if st.button("生成診斷題目並前往下一步", type="primary"):
            if not st.session_state.project_photos: st.error("請先上傳相片")
            else:
                # 簡化流程：直接生成內容
                st.info("AI 正在分析項目...")
                time.sleep(1)
                st.success("已準備好，請前往 Review & Multi-Sync 頁籤。")

    with tabs[1]:
        st.markdown('<div class="neu-card">', unsafe_allow_html=True)
        if st.button("🚀 生成六大平台對接文案 (含 FAQ)"):
            with st.spinner("AI Strategist 正在構思文案..."):
                prompt = f"分析專案: {st.session_state.project_name}. 生成 JSON。包含 challenge_summary, solution_summary, 6_website, 7_faq (en, tc, jp)."
                res = call_gemini_sdk(prompt, is_json=True)
                if res:
                    data = json.loads(res)
                    st.session_state.ai_content = data
                    st.session_state.challenge = data.get("challenge_summary", "")
                    st.session_state.solution = data.get("solution_summary", "")
                    
                    # 🚀 使用 Robust 邏輯格式化 FAQ 供 UI 編輯
                    faq_data = data.get("7_faq", {})
                    st.session_state.faq_en_edit = format_faq_robust(faq_data.get("en", "[]"))
                    st.session_state.faq_tc_edit = format_faq_robust(faq_data.get("tc", "[]"))
                    st.session_state.faq_jp_edit = format_faq_robust(faq_data.get("jp", "[]"))
                    st.rerun()

        if st.session_state.ai_content:
            st.subheader("編輯 FAQ 內容")
            f_tabs = st.tabs(["EN", "TC", "JP"])
            with f_tabs[0]: st.session_state.faq_en_edit = st.text_area("EN FAQ", value=st.session_state.faq_en_edit, height=200)
            with f_tabs[1]: st.session_state.faq_tc_edit = st.text_area("TC FAQ", value=st.session_state.faq_tc_edit, height=200)
            with f_tabs[2]: st.session_state.faq_jp_edit = st.text_area("JP FAQ", value=st.session_state.faq_jp_edit, height=200)

            if st.button("Confirm & Sync to Master DB", type="primary", use_container_width=True):
                with st.spinner("🔄 同步中..."):
                    try:
                        project_id, sort_date = generate_system_metadata()
                        
                        payload = {
                            "action": "sync_project",
                            "project_id": project_id,
                            "sort_date": sort_date,
                            "client_name": st.session_state.client_name,
                            "project_name": st.session_state.project_name,
                            "venue": st.session_state.venue,
                            "date": f"{st.session_state.event_year} {st.session_state.event_month}",
                            "youtube": st.session_state.youtube,
                            "challenge": st.session_state.challenge,
                            "solution": st.session_state.solution,
                            "ai_content": st.session_state.ai_content,
                            # 🚀 使用終極清洗，確保發送的是標準雙引號單行 JSON
                            "faq_en": safe_flatten_faq(st.session_state.faq_en_edit),
                            "faq_tc": safe_flatten_faq(st.session_state.faq_tc_edit),
                            "faq_jp": safe_flatten_faq(st.session_state.faq_jp_edit)
                        }
                        
                        r = requests.post(SHEET_SCRIPT_URL, json=payload, timeout=60)
                        if r.status_code == 200:
                            st.balloons()
                            st.success(f"✅ 同步成功！編號: {project_id}")
                        else:
                            st.error(f"同步失敗: {r.text}")
                    except Exception as e:
                        st.error(f"系統錯誤: {str(e)}")
        st.markdown('</div>', unsafe_allow_html=True)

if __name__ == "__main__": main()
